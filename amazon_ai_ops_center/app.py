"""Amazon AI Operation Command Center V1.0 Streamlit application."""

from __future__ import annotations

import streamlit as st

from services.database import (
    Project,
    create_project,
    delete_project,
    get_project,
    initialize_database,
    list_projects,
    update_project,
)
from services.project_files import create_project_folders, project_root

APP_TITLE = "Amazon AI Operation Command Center V1.0"
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
    st.caption("第一阶段仅保存项目基础资料，为后续 AI 分析模块提供统一数据来源。")

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
    st.caption("内部运营工具 · 第一阶段基础框架")

    projects = load_projects()
    selected_project = render_project_controls(projects)
    page = render_navigation()

    if page == "项目资料中心":
        render_project_profile(selected_project)
    else:
        render_placeholder_page(page, selected_project)


if __name__ == "__main__":
    main()
