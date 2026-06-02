"""Competitor analysis orchestration and file context extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from docx import Document

from services.llm_service import analyze_images_with_prompt, generate_text
from services.project_files import project_root
from services.report_export_service import save_competitor_excel_report, save_markdown_report
from utils.paths import BASE_DIR

SUPPORTED_COMPETITOR_FILE_TYPES = {"xlsx", "csv", "txt", "docx", "jpg", "jpeg", "png", "pdf"}
IMAGE_FILE_TYPES = {"jpg", "jpeg", "png"}
TEXT_LIMIT_PER_FILE = 4_000
TABLE_ROW_LIMIT = 80

FILE_PURPOSE_OPTIONS = [
    "竞品评论表",
    "竞品关键词表",
    "竞品 Listing 文案",
    "竞品主图截图",
    "竞品 A+ 截图",
    "竞品页面截图",
    "其他资料",
]


@dataclass(frozen=True)
class SelectedCompetitorFile:
    """User-selected project file and its analysis purpose."""

    filename: str
    file_type: str
    saved_path: str
    purpose: str


@dataclass(frozen=True)
class CompetitorAnalysisSettings:
    """Page-level settings for competitor analysis."""

    target_site: str
    product_risk_type: str
    output_language: str
    analysis_depth: str


@dataclass(frozen=True)
class CompetitorAnalysisResult:
    """Generated report paths and content."""

    markdown: str
    markdown_path: Path
    excel_path: Path


def resolve_saved_path(saved_path: str) -> Path:
    """Resolve a project file saved path stored in SQLite."""
    path = Path(saved_path)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def read_text_file(path: Path) -> str:
    """Read a text file with common encodings."""
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def _table_to_markdown(path: Path, file_type: str) -> str:
    """Read a spreadsheet-like file and return a compact Markdown preview."""
    if file_type == "csv":
        try:
            df = pd.read_csv(path, nrows=TABLE_ROW_LIMIT)
        except UnicodeDecodeError:
            df = pd.read_csv(path, nrows=TABLE_ROW_LIMIT, encoding="gb18030")
    else:
        df = pd.read_excel(path, nrows=TABLE_ROW_LIMIT)
    if df.empty:
        return "（表格为空）"
    return df.fillna("").to_markdown(index=False)


def _docx_to_text(path: Path) -> str:
    """Extract paragraph text from a DOCX file."""
    document = Document(path)
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text).strip()


def extract_file_context(files: list[SelectedCompetitorFile]) -> tuple[str, list[Path], list[str]]:
    """Extract text/table context and image paths from selected uploads.

    Returns (context_markdown, image_paths, read_errors). Per-file read failures are collected
    instead of raised so the Streamlit page can keep working.
    """
    context_blocks: list[str] = []
    image_paths: list[Path] = []
    read_errors: list[str] = []

    for item in files:
        file_type = item.file_type.lower()
        path = resolve_saved_path(item.saved_path)
        if file_type not in SUPPORTED_COMPETITOR_FILE_TYPES:
            read_errors.append(f"{item.filename}: 不支持的文件类型 {item.file_type}")
            continue
        if not path.exists():
            read_errors.append(f"{item.filename}: 本地文件不存在 {item.saved_path}")
            continue

        header = f"### 文件：{item.filename}\n用途：{item.purpose}\n类型：{item.file_type}"
        try:
            if file_type in {"xlsx", "csv"}:
                body = _table_to_markdown(path, file_type)
                context_blocks.append(f"{header}\n表格预览（最多前 {TABLE_ROW_LIMIT} 行）：\n{body}")
            elif file_type == "txt":
                body = read_text_file(path)[:TEXT_LIMIT_PER_FILE]
                context_blocks.append(f"{header}\n文本摘要：\n{body or '（未读取到文本）'}")
            elif file_type == "docx":
                body = _docx_to_text(path)[:TEXT_LIMIT_PER_FILE]
                context_blocks.append(f"{header}\nDOCX 摘要：\n{body or '（未读取到正文）'}")
            elif file_type == "pdf":
                context_blocks.append(f"{header}\nPDF 文件已选择，但当前模块不自动解析 PDF 正文；请结合文件名/备注判断，必要时上传 TXT/DOCX/CSV 摘要。")
            elif file_type in IMAGE_FILE_TYPES:
                image_paths.append(path)
                context_blocks.append(f"{header}\n图片路径：{path.name}（将作为视觉输入交给 AI 分析）")
        except Exception as exc:  # noqa: BLE001 - caller needs recoverable per-file error details.
            read_errors.append(f"{item.filename}: {exc}")

    return "\n\n".join(context_blocks).strip(), image_paths, read_errors


def load_prompt_template() -> str:
    """Load the competitor prompt template."""
    return (BASE_DIR / "prompts" / "competitor_analysis_prompt.md").read_text(encoding="utf-8")


def competitor_dataframe(competitors: list[dict[str, object]]) -> pd.DataFrame:
    """Normalize user-entered competitors to an exportable DataFrame."""
    columns = ["ASIN", "Amazon 链接", "品牌", "标题", "价格", "星级评分", "评论数量", "变体数量", "核心卖点", "备注"]
    frame = pd.DataFrame(competitors, columns=columns)
    if frame.empty:
        return pd.DataFrame(columns=columns)
    return frame.fillna("")


def _competitors_markdown(competitors: list[dict[str, object]]) -> str:
    """Convert competitor rows to Markdown for the prompt."""
    frame = competitor_dataframe(competitors)
    if frame.empty:
        return "未提供手动竞品表。"
    return frame.to_markdown(index=False)


def build_competitor_prompt(
    competitors: list[dict[str, object]],
    file_context: str,
    image_analysis: str,
    settings: CompetitorAnalysisSettings,
) -> tuple[str, str]:
    """Build system and user prompts for the final competitor report."""
    system_prompt = load_prompt_template()
    user_prompt = f"""
请根据以下资料生成完整竞品分析报告。

## 分析设置
- 目标站点：{settings.target_site}
- 产品风险类型：{settings.product_risk_type}
- 输出语言：{settings.output_language}
- 分析深度：{settings.analysis_depth}

## 用户手动输入的竞品表
{_competitors_markdown(competitors)}

## 用户选择的上传文件资料摘要
{file_context or '未选择上传文件资料。'}

## 图片/A+视觉分析摘要
{image_analysis or '未提供图片，或未生成独立图片分析摘要。'}

请输出最终报告，并严格保留提示词要求的章节结构。不要输出 JSON。
""".strip()
    return system_prompt, user_prompt


def run_competitor_analysis(
    project_id: str,
    competitors: list[dict[str, object]],
    selected_files: list[SelectedCompetitorFile],
    settings: CompetitorAnalysisSettings,
) -> CompetitorAnalysisResult:
    """Generate competitor analysis and save Markdown/XLSX exports."""
    file_context, image_paths, read_errors = extract_file_context(selected_files)
    image_analysis = ""
    if image_paths:
        image_prompt = (
            "请分析这些由用户上传的 Amazon 竞品图片/A+或页面截图。"
            "输出主图构图、卖点呈现、A+结构、可借鉴点、不建议模仿点和合规风险。"
            "不要声称你访问了 Amazon 页面。"
        )
        image_analysis = analyze_images_with_prompt(image_paths, image_prompt)

    system_prompt, user_prompt = build_competitor_prompt(competitors, file_context, image_analysis, settings)
    markdown = generate_text(system_prompt, user_prompt)
    if read_errors:
        markdown += "\n\n## 文件读取提示\n" + "\n".join(f"- {error}" for error in read_errors)

    output_dir = project_root(project_id) / "outputs"
    markdown_path = save_markdown_report(markdown, output_dir)
    excel_path = save_competitor_excel_report(markdown, output_dir, competitor_dataframe(competitors))
    return CompetitorAnalysisResult(markdown=markdown, markdown_path=markdown_path, excel_path=excel_path)
