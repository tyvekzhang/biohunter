import os
from typing import Optional
from fastmcp import FastMCP

from src.main.app.tools.cart_tumor_target_mining import cart_target_mining

mcp = FastMCP("Biohunter")


# ========== 肿瘤CAR-T靶点挖掘 ==========
@mcp.tool(
    name="scRNA_cart_target_mining",
    description=f"""【肿瘤细胞CAR-T靶点挖掘】使用严谨的过滤策略，挖掘CAR-T细胞靶点基因，确保靶点基因的安全性和有效性。
    参数：
    positive_path: 阳性参考文件路径, 非必填项
    negative_path: 阴性参考文件路径, 非必填项
    target_celltype: 用户输入的CAR-T靶点细胞类型
    surface_path: 细胞表面基因参考文件路径,文件路径为'{os.path.dirname(os.path.abspath(__file__))}/database/CellPhoneDB_CSPA_Surfaceome_HPA.csv'
    Tcell_path: 健康T细胞基因参考文件路径，文件路径为'{os.path.dirname(os.path.abspath(__file__))}/database/Tcell_genes.csv'
    healthy_path:健康组织参考文件路径，.csv;只包含Endothelial cell & smooth muscle cell细胞的表达百分比,文件路径为'{os.path.dirname(os.path.abspath(__file__))}/database/cross_healthy_processed_expression_df.csv'
    drug_path: 药物靶点基因参考文件路径,文件路径为'{os.path.dirname(os.path.abspath(__file__))}/database/druggable_proteome_genes.csv'
    query: 用户输入
    malign_label: 恶性细胞标签，存储在单细胞数据的obs中的列名，默认'cnv_status'
    cell_type_key:健康组织参考文件中细胞类型的标签，默认'cell_type'
    filter_threshold: 健康细胞基因过滤阈值，默认2；低于该阈值的基因才被保留
    surface_filter: 是否进行细胞表面基因过滤，默认True
    Tcell_filter: 是否进行T细胞免疫兼容过滤，默认True 
    healthy_filter: 是否进行脱靶毒性规避过滤，默认True 
    drug_filter:是否进行FDA安全评估过滤，默认True
    返回：
    CAR-T靶点基因，靶点基因分布图，文献支持信息（如果启用）。
    """,
)
def scRNA_cart_target_mining(
    surface_path: str,
    Tcell_path: str,
    healthy_path: str,
    drug_path: str,
    target_celltype: Optional[str] = None,
    positive_path: Optional[str] = None,
    negative_path: Optional[str] = None,
    query: Optional[str] = None,
    cell_type_key: str = "cell_type",
    malign_label: str = "cnv_status",
    filter_threshold: float = 2,
    surface_filter: bool = True,
    Tcell_filter: bool = True,
    healthy_filter: bool = True,
    drug_filter: bool = True,
):
    """肿瘤细胞CAR-T靶点挖掘工具"""

    result = cart_target_mining(
        positive_path=positive_path,
        negative_path=negative_path,
        target_celltype=target_celltype,
        surface_path=surface_path,
        Tcell_path=Tcell_path,
        healthy_path=healthy_path,
        drug_path=drug_path,
        query=query,
        cell_type_key=cell_type_key,
        malign_label=malign_label,
        filter_threshold=filter_threshold,
        surface_filter=surface_filter,
        Tcell_filter=Tcell_filter,
        healthy_filter=healthy_filter,
        drug_filter=drug_filter,
    )
    return result
