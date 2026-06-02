"""Export helpers for competitor analysis reports."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

SHEET_NAMES = [
    "竞品基础信息",
    "竞品卖点分析",
    "评论VOC分析",
    "关键词分析",
    "主图分析",
    "A+分析",
    "机会点总结",
    "主图Brief",
    "A+Brief",
]

SECTION_TO_SHEET = {
    "1. 竞品基础信息汇总": "竞品基础信息",
    "2. 竞品卖点分析": "竞品卖点分析",
    "3. 评论 VOC 分析": "评论VOC分析",
    "4. 关键词与流量词分析": "关键词分析",
    "5. 竞品主图分析": "主图分析",
    "6. 竞品 A+ 分析": "A+分析",
    "7. 机会点总结": "机会点总结",
    "8. 图片 Brief": "主图Brief",
}


def save_markdown_report(content: str, output_dir: Path, filename: str = "competitor_analysis.md") -> Path:
    """Save the competitor report to a deterministic Markdown path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def _extract_sections(markdown: str) -> dict[str, str]:
    """Extract top-level numbered sections from the model Markdown."""
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", markdown, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections[title] = markdown[start:end].strip()
    return sections


def _lines_frame(content: str) -> pd.DataFrame:
    """Convert a Markdown section to an Excel-friendly line table."""
    lines = [line.rstrip() for line in content.splitlines()]
    if not lines:
        lines = ["资料不足或 AI 未返回该章节内容。"]
    return pd.DataFrame({"序号": range(1, len(lines) + 1), "内容": lines})


def _safe_sheet_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    """Return a valid, non-empty frame for Excel writing."""
    if frame is None or frame.empty:
        return pd.DataFrame({"提示": ["暂无数据"]})
    return frame.fillna("")


def save_competitor_excel_report(
    markdown: str,
    output_dir: Path,
    competitor_df: pd.DataFrame | None = None,
    filename: str = "competitor_analysis.xlsx",
) -> Path:
    """Save the competitor analysis workbook with required sheets."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    sections = _extract_sections(markdown)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name in SHEET_NAMES:
            if sheet_name == "竞品基础信息":
                frame = _safe_sheet_frame(competitor_df)
            elif sheet_name == "A+Brief":
                brief_content = sections.get("8. 图片 Brief", "")
                marker = "### 8.2 7张 A+ Brief"
                frame = _lines_frame(brief_content.split(marker, 1)[-1].strip() if marker in brief_content else brief_content)
            elif sheet_name == "主图Brief":
                brief_content = sections.get("8. 图片 Brief", "")
                main_marker = "### 8.1 5张主图 Brief"
                aplus_marker = "### 8.2 7张 A+ Brief"
                if main_marker in brief_content:
                    brief_content = brief_content.split(main_marker, 1)[-1]
                if aplus_marker in brief_content:
                    brief_content = brief_content.split(aplus_marker, 1)[0]
                frame = _lines_frame(brief_content.strip())
            else:
                section_title = next((title for title, mapped in SECTION_TO_SHEET.items() if mapped == sheet_name), "")
                frame = _lines_frame(sections.get(section_title, ""))
            frame.to_excel(writer, sheet_name=sheet_name, index=False)

    return path
