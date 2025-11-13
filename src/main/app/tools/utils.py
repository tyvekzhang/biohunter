# SPDX-License-Identifier: MIT
import os
import sys
import contextlib
import scanpy as sc
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


@contextlib.contextmanager
def redirect_output_to_log(log_file_path: str):
    """将标准输出和标准错误重定向到日志文件"""
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    # 确保日志文件目录存在
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    try:
        # 打开日志文件
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            # 重定向输出到文件
            sys.stdout = log_file
            sys.stderr = log_file

            # 写入开始标记
            log_file.write(f"=== scVI Training Log - {datetime.now()} ===\n")
            log_file.flush()

            yield log_file_path

    finally:
        # 恢复原始输出
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def create_output_directories(
    output_dir: str, tool_name: str, figures: bool = True
):
    """
    创建输出目录和图像目录

    Args:
        output_dir: 输出目录路径
        tool_name: 工具名称
        figures: 是否创建图像目录

    Returns:
        tuple: (输出目录路径, 图像目录路径)
    """
    # 绝对路径作为输出目录，避免后续因工作目录变动导致找不到文件
    base_output_dir = os.path.abspath(output_dir)

    # 创建主输出目录
    try:
        os.makedirs(base_output_dir, exist_ok=True)
        output_dir = os.path.join(base_output_dir, "output", tool_name)
        # 再次转换为绝对路径确保万无一失
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        os.chmod(output_dir, 0o755)  # 确保目录可写
        # 创建图像目录
        if figures:
            try:
                figure_path = os.path.abspath(
                    os.path.join(output_dir, "figures")
                )
                os.makedirs(figure_path, exist_ok=True)
                os.chmod(figure_path, 0o755)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to create figure directory: {str(e)}"
                )
        else:
            figure_path = None
    except Exception as e:
        raise RuntimeError(f"Failed to create output directory: {str(e)}")

    return output_dir, (figure_path if figures else None)


def generate_pdf_report(data, output_file):
    """PDF报告生成函数"""
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    for section, content in data.items():
        story.append(Paragraph(section, styles["Heading2"]))
        if isinstance(content, dict):
            for key, value in content.items():
                # 将 key 加粗显示，value 使用默认样式
                story.append(
                    Paragraph(f"<b>{key}</b>: {value}", styles["BodyText"])
                )
        else:
            story.append(Paragraph(str(content), styles["BodyText"]))
        story.append(Spacer(1, 0.2 * inch))

    doc.build(story)


def preflight(
    file: str, groupby: str, candidate_groupby: set = None
) -> tuple[sc.AnnData, str]:
    """验证输入文件并做一些必要的处理"""

    # 校验文件格式
    if not file.endswith(".h5ad"):
        raise ValueError("Input file must be in .h5ad format")

    # 校验文件存在性
    if not os.path.exists(file):
        raise FileNotFoundError(f"Input file {file} does not exist")

    # 加载数据
    adata = sc.read_h5ad(file)
    adata.var_names_make_unique()

    if groupby in adata.obs.columns:
        adata.obs[groupby] = adata.obs[groupby].astype(str)
        return adata, groupby

    if candidate_groupby is None:
        raise ValueError(
            f"Data lacks {groupby} column, please check the input file to make sure the column name is correct."
        )

    # 否则从候选列表中查找
    for candidate in candidate_groupby:
        if candidate in adata.obs.columns:
            adata.obs[groupby] = adata.obs[groupby].astype(str)
            return adata, candidate

    # 如果都找不到，抛出异常
    raise ValueError(
        f"'{groupby}' is not a valid column of `adata.obs`. "
        "Also tried to find from "
        f"{candidate_groupby}, but none of them exists."
    )
