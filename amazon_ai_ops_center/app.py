"""Amazon AI Operation Command Center V1.0 Streamlit application."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st
from docx import Document


from services.database import (
    Project,
    ProjectFile,
    add_project_file,
    create_project,
    delete_project,
    delete_project_file,
    get_project,
    initialize_database,
    list_project_files,
    list_projects,
    update_project,
)
from services.project_files import create_project_folders, project_root

APP_TITLE = "Amazon AI Operation Command Center V1.0"
ALLOWED_FILE_TYPES = ["xlsx", "csv", "docx", "pdf", "jpg", "jpeg", "png", "txt"]
IMAGE_FILE_TYPES = {"jpg", "jpeg", "png"}
TEXT_PREVIEW_LIMIT = 2_000
NAV_ITEMS = [
    "项目资料中心",
    "竞品分析",
    "评论VOC分析",
    "Listing生成",
    "合规风控",
    "Listing诊断",
    "PPC分析",
    "新品广告计划",
    "主图A+提示词",
    "导出运营包",
]
SITE_OPTIONS = ["", "US", "CA", "MX", "UK", "DE", "FR", "IT", "ES", "JP", "AU", "AE", "SA"]


st.set_page_config(page_title=APP_TITLE, page_icon="🧭", layout="wide")


@st.cache_data(show_spinner=False)
def load_projects() -> list[Project]:
    """Cached project list for Streamlit reruns."""
    return list_projects()


def refresh_projects() -> None:
    """Clear cached project data after a mutation."""
    load_projects.clear()


def ensure_selected_project(projects: list[Project]) -> str | None:
    """Keep the selected project ID valid across reruns."""
    current_id = st.session_state.get("selected_project_id")
    valid_ids = {project.id for project in projects}
    if current_id in valid_ids:
        return current_id
    if projects:
        st.session_state.selected_project_id = projects[0].id
        return projects[0].id
    st.session_state.selected_project_id = None
    return None


def render_project_controls(projects: list[Project]) -> Project | None:
    """Render sidebar controls for creating, selecting, and deleting projects."""
    st.sidebar.subheader("产品项目")

    with st.sidebar.expander("创建新项目", expanded=not projects):
        with st.form("create_project_form", clear_on_submit=True):
            name = st.text_input("产品名称", placeholder="例如：便携式制冰机")
            site = st.selectbox("站点", SITE_OPTIONS, index=0)
            submitted = st.form_submit_button("创建项目", use_container_width=True)
        if submitted:
            project = create_project(name=name, site=site)
            refresh_projects()
            st.session_state.selected_project_id = project.id
            st.success("项目已创建。")
            st.rerun()

    selected_project_id = ensure_selected_project(projects)
    if not projects:
        st.sidebar.info("请先创建一个产品项目。")
        return None

    project_options = {
        f"{project.name} · {project.site or '未设置站点'} · {project.id[:8]}": project.id
        for project in projects
    }
    labels = list(project_options.keys())
    selected_label = next(
        (label for label, project_id in project_options.items() if project_id == selected_project_id),
        labels[0],
    )
    chosen_label = st.sidebar.selectbox("选择项目", labels, index=labels.index(selected_label))
    st.session_state.selected_project_id = project_options[chosen_label]

    selected_project = get_project(st.session_state.selected_project_id)
    if selected_project:
        create_project_folders(selected_project.id)
        folder = project_root(selected_project.id)
        st.sidebar.caption(f"项目ID：`{selected_project.id}`")
        st.sidebar.caption(f"项目目录：`projects/{folder.name}`")

        with st.sidebar.expander("删除当前项目"):
            st.warning("删除后会移除 SQLite 记录以及该项目 uploads/outputs 文件夹。")
            confirm = st.checkbox("我确认删除当前项目", key=f"confirm_delete_{selected_project.id}")
            if st.button("删除项目", disabled=not confirm, type="primary", use_container_width=True):
                delete_project(selected_project.id)
                refresh_projects()
                st.session_state.selected_project_id = None
                st.success("项目已删除。")
                st.rerun()
    return selected_project


def render_navigation() -> str:
    """Render the first-phase page navigation."""
    st.sidebar.subheader("功能导航")
    default_page = st.session_state.get("current_page", NAV_ITEMS[0])
    page = st.sidebar.radio("选择功能", NAV_ITEMS, index=NAV_ITEMS.index(default_page))
    st.session_state.current_page = page
    return page


def render_project_profile(project: Project | None) -> None:
    """Render the editable project profile center."""
    st.header("项目资料中心")
    st.caption("第二阶段支持上传与解析项目资料，为后续 AI 分析模块提供统一数据来源。")

    if project is None:
        st.info("请在左侧创建或选择一个产品项目。")
        return

    with st.form("project_profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("产品名称", value=project.name)
            site_index = SITE_OPTIONS.index(project.site) if project.site in SITE_OPTIONS else 0
            site = st.selectbox("站点", SITE_OPTIONS, index=site_index)
            brand = st.text_input("品牌", value=project.brand)
            category = st.text_input("类目", value=project.category)
        with col2:
            core_parameters = st.text_area("产品核心参数", value=project.core_parameters, height=120)
            target_audience = st.text_area("目标人群", value=project.target_audience, height=120)
            use_scenarios = st.text_area("使用场景", value=project.use_scenarios, height=120)
            compliance_sensitive_words = st.text_area(
                "合规敏感词",
                value=project.compliance_sensitive_words,
                height=120,
                placeholder="每行一个词，或用逗号分隔。",
            )

        saved = st.form_submit_button("保存项目资料", type="primary")

    if saved:
        update_project(
            project.id,
            {
                "name": name,
                "site": site,
                "brand": brand,
                "category": category,
                "core_parameters": core_parameters,
                "target_audience": target_audience,
                "use_scenarios": use_scenarios,
                "compliance_sensitive_words": compliance_sensitive_words,
            },
        )
        refresh_projects()
        st.success("项目资料已保存到 SQLite。")
        st.rerun()

    st.divider()
    upload_dir = project_root(project.id) / "uploads"
    output_dir = project_root(project.id) / "outputs"
    col1, col2, col3 = st.columns(3)
    col1.metric("当前站点", project.site or "未设置")
    col2.metric("品牌", project.brand or "未设置")
    col3.metric("类目", project.category or "未设置")
    st.code(f"uploads: {upload_dir}\noutputs: {output_dir}", language="text")

    st.divider()
    render_file_upload_center(project)


def sanitize_filename(filename: str) -> str:
    """Return a filesystem-safe filename while preserving a readable stem."""
    path_name = Path(filename).name.strip()
    stem = Path(path_name).stem or "upload"
    suffix = Path(path_name).suffix.lower()
    safe_stem = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", stem).strip("._-")
    return f"{safe_stem or 'upload'}{suffix}"


def relative_display_path(path: Path) -> str:
    """Prefer a project-local relative path in SQLite so paths remain portable."""
    try:
        return str(path.relative_to(Path(__file__).resolve().parent))
    except ValueError:
        return str(path)


def save_uploaded_file(project_id: str, uploaded_file) -> ProjectFile:
    """Persist one Streamlit upload to the project uploads folder and SQLite."""
    upload_dir = project_root(project_id) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    original_name = Path(uploaded_file.name).name
    safe_name = sanitize_filename(original_name)
    file_type = Path(safe_name).suffix.lower().lstrip(".")
    saved_name = f"{uuid4().hex[:12]}_{safe_name}"
    saved_path = upload_dir / saved_name

    with saved_path.open("wb") as destination:
        destination.write(uploaded_file.getbuffer())

    return add_project_file(
        project_id=project_id,
        filename=original_name,
        file_type=file_type,
        saved_path=relative_display_path(saved_path),
    )


def resolve_saved_path(saved_path: str) -> Path:
    """Resolve a SQLite saved path back to a local file path."""
    path = Path(saved_path)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parent / path


def delete_uploaded_file(project_id: str, file_id: str, saved_path: str) -> None:
    """Remove an uploaded file from disk and delete its SQLite metadata row."""
    path = resolve_saved_path(saved_path)
    upload_dir = (project_root(project_id) / "uploads").resolve()
    resolved_path = path.resolve()

    if resolved_path.exists():
        if upload_dir not in resolved_path.parents:
            st.error(f"拒绝删除 uploads 目录之外的文件：{saved_path}")
            return
        resolved_path.unlink()

    deleted_record = delete_project_file(file_id, project_id)
    if deleted_record is None:
        st.warning("未找到该文件记录，可能已经被删除。")
    else:
        st.success(f"已删除上传文件：{deleted_record.filename}")


def read_text_file(path: Path) -> str:
    """Read plain text using common encodings for marketplace exports."""
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def render_file_preview(file_record: ProjectFile) -> None:
    """Render a type-specific preview for an uploaded file."""
    path = resolve_saved_path(file_record.saved_path)
    file_type = file_record.file_type.lower()

    if not path.exists():
        st.warning(f"本地文件不存在：{file_record.saved_path}")
        return

    if file_type == "csv":
        try:
            preview = pd.read_csv(path, nrows=20)
            st.dataframe(preview, use_container_width=True)
        except UnicodeDecodeError:
            preview = pd.read_csv(path, nrows=20, encoding="gb18030")
            st.dataframe(preview, use_container_width=True)
        return

    if file_type == "xlsx":
        preview = pd.read_excel(path, nrows=20)
        st.dataframe(preview, use_container_width=True)
        return

    if file_type == "txt":
        text = read_text_file(path)
        st.text_area("TXT 正文", value=text, height=260, disabled=True)
        return

    if file_type == "docx":
        document = Document(path)
        text = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)
        shown = text[:TEXT_PREVIEW_LIMIT]
        if not shown:
            st.info("未从 DOCX 中提取到正文。")
        else:
            st.text_area("DOCX 正文预览（前 2000 字符）", value=shown, height=300, disabled=True)
        return

    if file_type == "pdf":
        st.info(f"PDF 已保存，暂不解析：{file_record.filename}")
        st.code(file_record.saved_path, language="text")
        return

    if file_type in IMAGE_FILE_TYPES:
        st.image(str(path), caption=file_record.filename, width=220)
        return

    st.info("该文件类型暂不支持预览。")


def render_file_upload_center(project: Project) -> None:
    """Render project file upload area and uploaded file list."""
    st.subheader("文件上传与资料解析")
    st.caption("支持 xlsx、csv、docx、pdf、jpg、jpeg、png、txt。文件会保存到当前项目 uploads 文件夹，并写入 SQLite。")

    with st.form(f"upload_files_{project.id}", clear_on_submit=True):
        uploaded_files = st.file_uploader(
            "上传项目资料",
            type=ALLOWED_FILE_TYPES,
            accept_multiple_files=True,
            help="Excel/CSV 将预览前 20 行；TXT/DOCX 将展示正文；PDF 仅保存；图片展示缩略图。",
        )
        submitted = st.form_submit_button("保存上传文件", type="primary")

    if submitted:
        if not uploaded_files:
            st.warning("请先选择至少一个文件。")
        else:
            saved_files = [save_uploaded_file(project.id, uploaded_file) for uploaded_file in uploaded_files]
            st.success(f"已上传 {len(saved_files)} 个文件。")
            st.rerun()

    files = list_project_files(project.id)
    st.subheader("当前项目已上传文件")
    if not files:
        st.info("当前项目还没有上传文件。")
        return

    st.dataframe(
        [
            {
                "文件名": item.filename,
                "文件类型": item.file_type,
                "保存路径": item.saved_path,
                "上传时间": item.uploaded_at,
            }
            for item in files
        ],
        use_container_width=True,
        hide_index=True,
    )

    for item in files:
        with st.expander(f"{item.filename} · {item.file_type} · {item.uploaded_at}"):
            meta_col, action_col = st.columns([4, 1])
            meta_col.caption(f"保存路径：`{item.saved_path}`")
            if action_col.button("删除文件", key=f"delete_file_{item.id}", type="secondary"):
                delete_uploaded_file(project.id, item.id, item.saved_path)
                st.rerun()

            try:
                render_file_preview(item)
            except Exception as exc:  # noqa: BLE001 - Streamlit should show per-file parsing failures without crashing.
                st.error(f"预览失败：{exc}")


def render_placeholder_page(page_name: str, project: Project | None) -> None:
    """Render an empty but clickable first-phase feature page."""
    st.header(page_name)
    st.info("该模块已接入导航，第一阶段暂不实现复杂 AI 功能。")
    if project is None:
        st.caption("请先在左侧创建或选择产品项目，后续模块会读取项目资料中心的数据。")
    else:
        st.caption(f"当前项目：{project.name}（{project.site or '未设置站点'}）")


def main() -> None:
    """Application entry point."""
    initialize_database()
    st.title(APP_TITLE)
    st.caption("内部运营工具 · 第二阶段文件上传与资料解析")

    projects = load_projects()
    selected_project = render_project_controls(projects)
    page = render_navigation()

    if page == "项目资料中心":
        render_project_profile(selected_project)
    else:
        render_placeholder_page(page, selected_project)


if __name__ == "__main__":
    main()
