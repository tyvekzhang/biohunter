import os
import traceback
from typing import Optional

import numpy as np
import pandas as pd
import scanpy as sc

from src.main.app.agent.context import get_current_message
from src.main.app.schema.chat_schema import ChatMessage
from src.main.app.tools._literature_retrieval_pubmed import (
    TargetMiningConfig,
    TargetMiningTool,
)

from fastlib.logging import logger

from .utils import create_output_directories


def cart_target_mining(
    output_dir: str,
    target_celltype: str,
    surface_path: str,
    Tcell_path: str,
    healthy_path: str,
    drug_path: str,
    query: str,
    positive_path: Optional[str] = None,
    negative_path: Optional[str] = None,
    cell_type_key: str = "cell_type",
    malign_label: str = "cnv_status",
    filter_threshold: float = 2,
    surface_filter: bool = True,
    Tcell_filter: bool = True,
    healthy_filter: bool = True,
    drug_filter: bool = True,
):
    """
    肿瘤细胞CAR-T靶点挖掘的核心实现

    参数：
    positive_path: 阳性参考文件路径（必需），包含已知有效的CAR-T靶点或相关基因
    negative_path: 阴性参考文件路径（必需），包含已知无效或不安全的靶点基因
    output_dir: 输出目录路径
    target_celltype: 用户输入的CAR-T靶点细胞类型
    surface_path: 细胞表面基因参考文件路径，文件名为'CellPhoneDB_CSPA_Surfaceome_HPA.csv'
    Tcell_path: 健康T细胞基因参考文件路径，文件名为'Tcell_genes.csv'
    healthy_path: 健康组织参考文件路径，包含Endothelial cell & smooth muscle cell细胞的表达百分比，文件名为'cross_healthy_processed_expression_df.csv'
    drug_path: 药物靶点基因参考文件路径，文件名为'druggable_proteome_genes.csv'
    query: 用户输入
    malign_label: 恶性细胞标签，存储在单细胞数据的obs中的列名，默认'cnv_status'
    cell_type_key: 健康组织参考文件中细胞类型的标签，默认'cell_type'
    filter_threshold: 健康细胞基因过滤阈值，默认2；低于该阈值的基因才被保留
    surface_filter: 是否进行细胞表面基因过滤，默认True
    Tcell_filter: 是否进行T细胞免疫兼容过滤，默认True
    healthy_filter: 是否进行脱靶毒性规避过滤，默认True
    drug_filter: 是否进行FDA安全评估过滤，默认True

    返回：
    经过多级过滤的CAR-T靶点基因列表，包含每个基因的筛选信息和文献支持证据（如果启用）
    """
    message: ChatMessage = get_current_message()
    result = {
        "Status": "Success",
        "Error": "",
        "OutputAdata_info": "",
        "Result": "",
        "OutputFiles": {"data": "", "figures": ""},
    }

    msg_type = message.type
    try:
        # **********************************************非方法主体*****************************************
        # 对输入做必要的校验
        if positive_path or negative_path:
            if not positive_path.endswith(".h5ad") or not negative_path.endswith(
                ".h5ad"
            ):
                raise ValueError("输入文件必须是 .h5ad 格式")
            if not os.path.exists(positive_path):
                raise FileNotFoundError(f"输入文件 {positive_path} 不存在")
            if not os.path.exists(negative_path):
                raise FileNotFoundError(f"输入文件 {negative_path} 不存在")
        else:
            query = (
                query.replace("\n", " ")
                .replace("  ", " ")
            )

        # 使用新的目录创建函数
        output_dir, figure_path = create_output_directories(
            output_dir, "cart_target_mining"
        )

        # 来自cart文章的tcell基因
        t_genes = pd.read_csv(Tcell_path)["T"].tolist()
        malign_genes = []
        filename = ""
        adata = None
        # ***********************************************方法主体*****************************************
        if msg_type == 1:
            config = TargetMiningConfig()
            tool = TargetMiningTool(config)
            malign_genes, _ = tool.mine_targets(
                query=query,
                output_dir=output_dir,
                medline_file=os.path.join(output_dir, "query_results.medline"),
            )
            filename = "literature_keywords"
            adata = query
        else:
            # 检查是否有细胞类型注释
            adata_base_malign = sc.read_h5ad(positive_path)
            if cell_type_key not in adata_base_malign.obs.columns:
                raise ValueError(
                    f"数据缺少细胞类型注释列：{cell_type_key}，请先进行细胞类型注释 {positive_path}"
                )
            positive_name = os.path.splitext(os.path.basename(positive_path))[0]
            # 进行基础的过滤, 正常情况已经进行过质控
            sc.pp.filter_cells(adata_base_malign, min_genes=200)
            sc.pp.filter_genes(adata_base_malign, min_cells=3)
            adata_base_malign.obs[malign_label] = "malignant"

            adata_normal = sc.read_h5ad(negative_path)
            if cell_type_key not in adata_normal.obs.columns:
                raise ValueError(
                    f"数据缺少细胞类型注释列：{cell_type_key}，请先进行细胞类型注释 {negative_path}"
                )
            negative_name = os.path.splitext(os.path.basename(negative_path))[0]
            filename = negative_name + positive_name
            # 进行基础的过滤, 正常情况已经进行过质控
            sc.pp.filter_cells(adata_normal, min_genes=200)
            sc.pp.filter_genes(adata_normal, min_cells=3)
            adata_normal.obs[malign_label] = "normal"

            adata = sc.concat([adata_base_malign, adata_normal], join="outer")

            # 提取健康T细胞的marker基因
            mask = adata_normal.obs[cell_type_key].str.contains(
                "T", case=True, na=False, regex=False
            )

            adata_normal.obs["T_and_others"] = "other cell"
            adata_normal.obs.loc[mask, "T_and_others"] = "T cell"
            print(adata_normal.obs["T_and_others"].value_counts())
            sc.tl.rank_genes_groups(
                adata_normal,
                groupby="T_and_others",
                groups=["T cell"],
                key_added="healthyT_v_sallhealthy",
                method="wilcoxon",
            )

            df_T = pd.DataFrame(adata_normal.uns["healthyT_v_sallhealthy"]["names"])

            tmp = np.array(
                pd.DataFrame(adata_normal.uns["healthyT_v_sallhealthy"]["pvals_adj"])
            )
            df_T["T_pvals_adj"] = tmp

            tmp = np.array(
                pd.DataFrame(
                    adata_normal.uns["healthyT_v_sallhealthy"]["logfoldchanges"]
                )
            )
            df_T["T_logfoldchanges"] = tmp

            df_T = df_T[df_T["T_pvals_adj"] <= 0.05]
            df_T = df_T[df_T["T_logfoldchanges"] > 2]

            target_T_gene_path = os.path.join(
                output_dir, f"target_T_gene_{filename}.csv"
            )
            df_T.to_csv(target_T_gene_path)

            inner_t_genes = df_T["T cell"].tolist()
            t_genes = list(set(t_genes + inner_t_genes))
            t_genes = np.array(t_genes).astype(str)

            # 提取malign的marker gene
            # 如果 target_celltype 是列表格式
            if isinstance(target_celltype, list):
                target_celltypes = target_celltype
            # 如果是字符串且包含逗号，拆分为列表
            elif isinstance(target_celltype, str) and "," in target_celltype:
                target_celltypes = [ct.strip() for ct in target_celltype.split(",")]
            else:
                # 如果是单个细胞类型，转换为列表
                target_celltypes = [target_celltype]

            # 使用 isin() 筛选多个细胞类型
            adata_target_celltype = adata[
                adata.obs[cell_type_key].isin(target_celltypes)
            ].copy()
            logger.info(
                f"adata_{malign_label}: {set(adata_target_celltype.obs[malign_label])}"
            )
            if malign_label in adata_target_celltype.obs.columns:
                adata_target_celltype.obs[malign_label] = pd.Categorical(
                    adata_target_celltype.obs[malign_label]
                )
                counts = adata_target_celltype.obs[malign_label].value_counts()
                print(f"{malign_label} 分组数量统计:")
                for group, count in counts.items():
                    print(f"  {group}: {count} 个细胞")

                sc.tl.rank_genes_groups(
                    adata_target_celltype,
                    groupby=malign_label,
                    groups=["malignant"],
                    key_added="testing",
                )
            else:
                raise ValueError(f"Column '{malign_label}' not found in adata.obs")
            df1 = pd.DataFrame(adata_target_celltype.uns["testing"]["names"])
            tmp = np.array(
                pd.DataFrame(adata_target_celltype.uns["testing"]["pvals_adj"])[
                    "malignant"
                ]
            )
            df1["malignant_pvals_adj"] = tmp
            tmp = np.array(
                pd.DataFrame(adata_target_celltype.uns["testing"]["logfoldchanges"])[
                    "malignant"
                ]
            )
            df1["malignant_logfoldchanges"] = tmp
            # 过滤条件
            df_filtered = df1[df1["malignant_pvals_adj"] <= 0.05]
            df_filtered = df_filtered[df_filtered["malignant_logfoldchanges"] > 2]

            target_diff_genes_malignant_vs_normal_path = os.path.join(
                output_dir, f"target_diff_genes_malignant_vs_normal_{filename}.csv"
            )
            df_filtered.to_csv(target_diff_genes_malignant_vs_normal_path)

            # filter1： genelist over 2% cells(from the sample)--------------------------------
            malign_genes = np.array(
                df_filtered["malignant"]
            )  # target细胞的恶性高可变基因
            if "n_cells" not in adata_target_celltype.var.columns:
                sc.pp.calculate_qc_metrics(adata_target_celltype, inplace=True)
            df_filter1 = pd.DataFrame(adata_target_celltype[:, malign_genes].copy().var)
            df2 = pd.DataFrame()
            df2["n_cells"] = df_filter1["n_cells_by_counts"].copy()
            df2["n_cells_percent"] = df2["n_cells"] * 100 / adata_target_celltype.n_obs
            malign_genes = df2[df2["n_cells_percent"] > 2].index
            malign_genes = np.array(malign_genes).astype(str)
            print(
                f"已提取{target_celltype}的恶性细胞高表达基因，候选基因数：{len(malign_genes)}"
            )

        # filter2: genelist intersects with surface----------------------------------------------------------------
        # inplaced with CellPhoneDB_CSPA_Surfaceome_HPA.csv
        if surface_filter:
            surface_genes = pd.read_csv(surface_path, sep=",")
            surface_genes = np.array(surface_genes["surfaceome_genes"]).astype(str)
            df_filter2 = np.array(np.intersect1d(malign_genes, surface_genes)).astype(
                str
            )
            print(f"已完成细胞表面基因过滤，剩余候选基因数：{len(df_filter2)}")
        else:
            df_filter2 = malign_genes

        # filter3: genelist excludes Tcell----------------------------------------------------------------
        # inplaced with healthy_T_genes.csv
        if Tcell_filter:
            df_filter3 = np.array(
                df_filter2[np.isin(df_filter2, t_genes, invert=True)]
            ).astype(str)
            print(f"已完成T细胞脱靶基因过滤，剩余候选基因数：{len(df_filter3)}")
        else:
            df_filter3 = df_filter2

        # filter4: genelist less than 2% in healthyOrgan cells -----------------------------------------
        if healthy_filter:
            df_healthy = pd.read_csv(healthy_path, index_col="Unnamed: 0", sep=",")

            df_filter3_filtered = [
                gene for gene in df_filter3 if gene in df_healthy.index
            ]
            df_safe_genes = list(set(df_filter3) - set(df_filter3_filtered))

            df4 = df_healthy.loc[df_filter3_filtered].copy()

            df4["thresholds_passed"] = df4.apply(
                lambda row: sum([(x < filter_threshold) for x in row]), axis=1
            )

            df_filter4 = df4[df4["thresholds_passed"] == 2].index
            set_merge4 = set(df_filter4) | set(df_safe_genes)
            df_filter4 = np.array(list(set_merge4)).astype(str)
            print(f"已完成器官脱靶基因过滤，剩余候选基因数：{len(df_filter4)}")

        else:
            df_filter4 = df_filter3

        # filter5: genes that intersect with druggable gene--------------------------------
        # inplaced with druggable_proteome_genes.csv
        if drug_filter:
            druggable = pd.read_csv(drug_path)
            druggene = np.array(druggable["druggable_proteome_genes"]).astype(str)
            final_candidates = np.array(np.intersect1d(df_filter4, druggene)).astype(
                str
            )
            print(f"已完成药物靶点基因过滤，最终的靶点基因数：{len(final_candidates)}")
        else:
            final_candidates = df_filter4

        # save filtered genes as csv-------------------------------------------------------------------
        cart_result = pd.DataFrame(final_candidates, columns=["gene"])
        cart_final_candidates_path = os.path.join(
            output_dir, f"cart_final_candidates_{filename}.csv"
        )
        cart_result.to_csv(cart_final_candidates_path)

        print(f"已保存{target_celltype}的靶点基因到{cart_final_candidates_path}")

        result["OutputAdata_info"] = str(adata)
        result["Result"] = (
            f"CAR-T靶点挖掘已完成，目标细胞{target_celltype}最终靶点基因数：{len(final_candidates)}，靶点基因：{list(final_candidates)}。"
        )
        result["OutputFiles"]["datas"] = cart_final_candidates_path
        result["OutputFiles"]["figures"] = figure_path
    except Exception as e:
        result["Status"] = "Error"
        result["Error"] = f"CAR-T靶点挖掘失败: {traceback.format_exc()}"

    return result
