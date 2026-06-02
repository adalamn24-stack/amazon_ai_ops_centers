"""OpenAI LLM service helpers for AI analysis outputs."""

from __future__ import annotations

import base64
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from services.project_files import project_root
from utils.paths import BASE_DIR, load_env_file

DEFAULT_MODEL = "gpt-4.1-mini"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
_current_project_id: str | None = None


class LLMServiceError(RuntimeError):
    """Raised when an AI request or output persistence step fails."""


def set_current_project(project_id: str | None) -> None:
    """Set the Streamlit-selected project so AI markdown files land in its outputs folder."""
    global _current_project_id
    _current_project_id = project_id or None


def get_openai_api_key() -> str:
    """Return the OpenAI API key from environment or project .env without logging it."""
    load_env_file(BASE_DIR / ".env")
    api_key = os.getenv(OPENAI_API_KEY_ENV, "").strip()
    if api_key in {"", "your_api_key_here"}:
        return ""
    return api_key


def mask_api_key(api_key: str) -> str:
    """Mask an API key for UI display without exposing the complete secret."""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "已配置（密钥较短，已隐藏）"
    return f"{api_key[:3]}...{api_key[-4:]}"


def get_ai_outputs_dir(project_id: str | None = None) -> Path:
    """Return the active outputs directory, preferring the selected project outputs folder."""
    active_project_id = project_id or _current_project_id
    if active_project_id:
        output_dir = project_root(active_project_id) / "outputs"
    else:
        output_dir = BASE_DIR / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_markdown_output(content: str, prefix: str = "ai_output", project_id: str | None = None) -> Path:
    """Persist one AI response as a markdown file in the active outputs directory."""
    output_dir = get_ai_outputs_dir(project_id)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{prefix}_{uuid4().hex[:8]}.md"
    output_path = output_dir / filename
    output_path.write_text(content, encoding="utf-8")
    return output_path


def _create_openai_client():
    """Create an OpenAI client only after confirming a key is configured."""
    api_key = get_openai_api_key()
    if not api_key:
        raise LLMServiceError("未配置 OPENAI_API_KEY，请先在 .env 中配置后重试。")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMServiceError("缺少 openai 依赖，请先运行 pip install -r requirements.txt。") from exc

    return OpenAI(api_key=api_key)


def _extract_response_text(response: Any) -> str:
    """Read text from a Responses API result with a defensive fallback."""
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text).strip()

    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(str(text))
    return "\n".join(parts).strip()


def _request_text(system_prompt: str, user_prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Request a text response from OpenAI without persisting it."""
    if not user_prompt or not user_prompt.strip():
        raise LLMServiceError("user_prompt 不能为空。")

    try:
        client = _create_openai_client()
        response = client.responses.create(
            model=model,
            instructions=system_prompt or "你是一个专业的 Amazon 运营 AI 助手。",
            input=user_prompt,
        )
        output_text = _extract_response_text(response)
        if not output_text:
            raise LLMServiceError("OpenAI 返回为空，请调整提示词后重试。")
        return output_text
    except LLMServiceError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert SDK/runtime errors into UI-safe messages.
        raise LLMServiceError(f"AI 文本生成失败：{exc}") from exc


def generate_text(system_prompt: str, user_prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Generate text with OpenAI and save the AI response to markdown."""
    output_text = _request_text(system_prompt, user_prompt, model)
    save_markdown_output(output_text, prefix="generate_text")
    return output_text


def analyze_table_with_prompt(df: pd.DataFrame, prompt: str) -> str:
    """Analyze a pandas DataFrame with a caller-provided prompt."""
    if df is None or df.empty:
        raise LLMServiceError("表格数据为空，无法分析。")
    table_preview = df.head(100).to_markdown(index=False)
    user_prompt = (
        f"{prompt.strip()}\n\n"
        "以下是表格数据预览（最多前 100 行，Markdown 表格）：\n\n"
        f"{table_preview}"
    )
    output_text = _request_text("你是擅长 Amazon 运营数据分析的 AI 助手，请给出结构化 Markdown 结论。", user_prompt)
    save_markdown_output(output_text, prefix="analyze_table")
    return output_text


def analyze_text_with_prompt(text: str, prompt: str) -> str:
    """Analyze plain text with a caller-provided prompt."""
    if not text or not text.strip():
        raise LLMServiceError("文本内容为空，无法分析。")
    user_prompt = f"{prompt.strip()}\n\n以下是待分析文本：\n\n{text.strip()}"
    output_text = _request_text("你是擅长 Amazon 运营文本分析的 AI 助手，请给出结构化 Markdown 结论。", user_prompt)
    save_markdown_output(output_text, prefix="analyze_text")
    return output_text


def _image_to_data_url(image_path: Path) -> str:
    """Convert a local image path into a data URL accepted by multimodal models."""
    if not image_path.exists() or not image_path.is_file():
        raise LLMServiceError(f"图片文件不存在：{image_path}")
    mime_type, _ = mimetypes.guess_type(image_path.name)
    if mime_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        raise LLMServiceError(f"不支持的图片类型：{image_path.name}")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def analyze_images_with_prompt(image_paths: list[str | Path], prompt: str) -> str:
    """Analyze one or more local images with a caller-provided prompt."""
    if not image_paths:
        raise LLMServiceError("请至少提供一张图片。")

    try:
        client = _create_openai_client()
        content: list[dict[str, str]] = [{"type": "input_text", "text": prompt.strip()}]
        for raw_path in image_paths:
            path = Path(raw_path)
            content.append({"type": "input_image", "image_url": _image_to_data_url(path)})

        response = client.responses.create(
            model=DEFAULT_MODEL,
            instructions="你是擅长 Amazon 商品图片与视觉卖点分析的 AI 助手，请给出结构化 Markdown 结论。",
            input=[{"role": "user", "content": content}],
        )
        output_text = _extract_response_text(response)
        if not output_text:
            raise LLMServiceError("OpenAI 返回为空，请调整提示词或图片后重试。")
        save_markdown_output(output_text, prefix="analyze_images")
        return output_text
    except LLMServiceError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert SDK/runtime errors into UI-safe messages.
        raise LLMServiceError(f"AI 图片分析失败：{exc}") from exc
