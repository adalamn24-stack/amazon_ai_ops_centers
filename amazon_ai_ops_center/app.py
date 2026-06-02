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
from services.competitor_service import (
    FILE_PURPOSE_OPTIONS,
    CompetitorAnalysisSettings,
    SelectedCompetitorFile,
    extract_file_context,
    run_competitor_analysis,
)
from services.llm_service import get_openai_api_key, mask_api_key, set_current_project
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


def render_ai_config_check() -> None:
    """Render OpenAI API key configuration status without exposing the full key."""
    st.sidebar.subheader("AI配置检查")
    api_key = get_openai_api_key()
    if not api_key:
        st.sidebar.warning("未检测到 OPENAI_API_KEY，请在 .env 中配置后使用 AI 功能。")
        st.sidebar.code("OPENAI_API_KEY=your_api_key_here", language="text")
    else:
        st.sidebar.success(f"OPENAI_API_KEY 已配置：{mask_api_key(api_key)}")


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



def _non_empty_competitor_rows(rows: object) -> list[dict[str, object]]:
    """Keep competitor rows that contain at least one meaningful value."""
    if isinstance(rows, pd.DataFrame):
        iterable_rows = rows.to_dict(orient="records")
    else:
        iterable_rows = list(rows) if rows is not None else []

    cleaned: list[dict[str, object]] = []
    for row in iterable_rows:
        normalized = {key: ("" if value is None else value) for key, value in row.items()}
        if any(str(value).strip() for value in normalized.values()):
            cleaned.append(normalized)
    return cleaned


def _project_file_options(project: Project) -> dict[str, ProjectFile]:
    """Build labels for current project upload selection."""
    files = [item for item in list_project_files(project.id) if item.file_type.lower() in ALLOWED_FILE_TYPES]
    return {f"{item.filename} · {item.file_type} · {item.uploaded_at}": item for item in files}


def render_competitor_analysis(project: Project | None) -> None:
    """Render the fourth-phase competitor analysis module."""
    st.header("竞品分析")
    st.caption("第4阶段：基于手动输入和当前项目 uploads 文件生成竞品分析、图片/A+分析、机会点与导出文件。")
    st.info("本模块不会自动爬取 Amazon 页面，也不会自动登录 Amazon；请通过手动输入或上传文件提供竞品资料。")

    if project is None:
        st.warning("请先在左侧创建或选择项目。")
        return

    st.subheader("1. 竞品手动输入表")
    default_rows = [
        {
            "ASIN": "",
            "Amazon 链接": "",
            "品牌": "",
            "标题": "",
            "价格": "",
            "星级评分": "",
            "评论数量": "",
            "变体数量": "",
            "核心卖点": "",
            "备注": "",
        }
        for _ in range(3)
    ]
    competitor_rows = st.data_editor(
        default_rows,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"competitor_rows_{project.id}",
        column_config={
            "Amazon 链接": st.column_config.TextColumn(width="medium"),
            "标题": st.column_config.TextColumn(width="large"),
            "核心卖点": st.column_config.TextColumn(width="large"),
            "备注": st.column_config.TextColumn(width="medium"),
        },
    )
    competitors = _non_empty_competitor_rows(competitor_rows)

    st.subheader("2. 选择项目已上传文件")
    file_options = _project_file_options(project)
    selected_labels: list[str] = []
    selected_files: list[SelectedCompetitorFile] = []
    if not file_options:
        st.info("当前项目 uploads 中暂无可用于竞品分析的文件。可先到“项目资料中心”上传 xlsx/csv/txt/docx/jpg/jpeg/png/pdf。")
    else:
        selected_labels = st.multiselect(
            "从当前项目 uploads 文件中选择资料",
            options=list(file_options.keys()),
            help="支持 xlsx、csv、txt、docx、jpg、jpeg、png、pdf。",
            key=f"competitor_selected_files_{project.id}",
        )

        if selected_labels:
            st.subheader("3. 文件用途分类")
            for label in selected_labels:
                item = file_options[label]
                default_index = 0
                lower_name = item.filename.lower()
                if "keyword" in lower_name or "关键词" in lower_name:
                    default_index = FILE_PURPOSE_OPTIONS.index("竞品关键词表")
                elif "a+" in lower_name or "aplus" in lower_name:
                    default_index = FILE_PURPOSE_OPTIONS.index("竞品 A+ 截图")
                elif item.file_type.lower() in IMAGE_FILE_TYPES:
                    default_index = FILE_PURPOSE_OPTIONS.index("竞品主图截图")
                purpose = st.selectbox(
                    f"{item.filename} 的用途",
                    FILE_PURPOSE_OPTIONS,
                    index=default_index,
                    key=f"competitor_purpose_{project.id}_{item.id}",
                )
                selected_files.append(
                    SelectedCompetitorFile(
                        filename=item.filename,
                        file_type=item.file_type,
                        saved_path=item.saved_path,
                        purpose=purpose,
                    )
                )

            context, image_paths, read_errors = extract_file_context(selected_files)
            if read_errors:
                st.error("部分文件读取失败，AI 分析会跳过失败文件。")
                for error in read_errors:
                    st.error(error)

            with st.expander("文件读取预检查", expanded=False):
                st.caption(f"可读取文本/表格摘要长度：{len(context)} 字符；图片数量：{len(image_paths)}")
                if read_errors:
                    st.warning("上方已显示具体文件读取失败原因。")
                else:
                    st.success("已选择文件均可用于分析（PDF 仅记录文件信息，不自动解析正文）。")

    st.subheader("4. 分析设置")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        target_sites = ["US", "UK", "DE", "FR", "IT", "ES", "CA", "JP"]
        default_site_index = target_sites.index(project.site) if project.site in target_sites else 0
        target_site = st.selectbox("目标站点", target_sites, index=default_site_index)
    with col2:
        risk_type = st.selectbox(
            "产品风险类型",
            ["普通产品", "膳食补充剂", "美容个护", "红光LED", "EMS", "宠物用品", "医疗器械高风险"],
        )
    with col3:
        output_language = st.selectbox("输出语言", ["中文说明 + 英文运营表达"])
    with col4:
        analysis_depth = st.selectbox("分析深度", ["标准", "简版", "深度"])

    st.divider()
    api_key = get_openai_api_key()
    if not api_key:
        st.warning("未检测到 OPENAI_API_KEY。请先在 .env 或环境变量中配置 API Key，页面不会崩溃，但 AI 分析按钮将不可用。")

    can_analyze = bool(api_key) and (bool(competitors) or bool(selected_files))
    if not competitors and not selected_files:
        st.info("请至少提供一种竞品资料：填写竞品表，或选择当前项目 uploads 中的文件。")

    if st.button("生成竞品分析报告", type="primary", disabled=not can_analyze, use_container_width=True):
        settings = CompetitorAnalysisSettings(
            target_site=target_site,
            product_risk_type=risk_type,
            output_language=output_language,
            analysis_depth=analysis_depth,
        )
        try:
            with st.spinner("AI 正在生成竞品分析报告，请稍候..."):
                result = run_competitor_analysis(project.id, competitors, selected_files, settings)
            st.session_state[f"competitor_result_{project.id}"] = {
                "markdown": result.markdown,
                "markdown_path": str(result.markdown_path),
                "excel_path": str(result.excel_path),
            }
            st.success("竞品分析报告已生成并保存到当前项目 outputs 文件夹。")
        except Exception as exc:  # noqa: BLE001 - keep Streamlit state and show UI-safe AI/file errors.
            st.error(f"AI 调用或导出失败：{exc}")

    result_state = st.session_state.get(f"competitor_result_{project.id}")
    if result_state:
        st.subheader("分析结果")
        st.caption(f"Markdown：`{result_state['markdown_path']}`")
        st.caption(f"Excel：`{result_state['excel_path']}`")
        st.markdown(result_state["markdown"])

        markdown_path = Path(result_state["markdown_path"])
        excel_path = Path(result_state["excel_path"])
        dl_col1, dl_col2 = st.columns(2)
        if markdown_path.exists():
            dl_col1.download_button(
                "下载 Markdown 报告",
                data=markdown_path.read_bytes(),
                file_name="competitor_analysis.md",
                mime="text/markdown",
                use_container_width=True,
            )
        if excel_path.exists():
            dl_col2.download_button(
                "下载 Excel 报告",
                data=excel_path.read_bytes(),
                file_name="competitor_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

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
    st.caption("内部运营工具 · 第四阶段竞品分析模块")

    projects = load_projects()
    selected_project = render_project_controls(projects)
    set_current_project(selected_project.id if selected_project else None)
    render_ai_config_check()
    page = render_navigation()

    if page == "项目资料中心":
        render_project_profile(selected_project)
    elif page == "竞品分析":
        render_competitor_analysis(selected_project)
    else:
        render_placeholder_page(page, selected_project)


if __name__ == "__main__":
    main()
