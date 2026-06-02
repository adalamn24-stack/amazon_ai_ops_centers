# Amazon AI Operation Command Center V1.0

内部使用的 Streamlit 运营工具。当前已完成第二阶段：在项目资料中心支持文件上传、SQLite 文件元数据管理，以及常见资料格式的页面预览。

## 功能范围

- 创建、选择、删除产品项目。
- 使用 SQLite 保存项目基础资料与上传文件信息。
- 每个项目自动创建独立目录：
  - `projects/{project_id}/uploads`
  - `projects/{project_id}/outputs`
- 左侧导航包含以下模块入口：
  - 项目资料中心
  - 竞品分析
  - 评论VOC分析
  - Listing生成
  - 合规风控
  - Listing诊断
  - PPC分析
  - 新品广告计划
  - 主图A+提示词
  - 导出运营包
- 项目资料中心支持填写并保存：产品名称、站点、品牌、类目、产品核心参数、目标人群、使用场景、合规敏感词。
- 项目资料中心新增文件上传与资料解析区域：
  - 支持上传 `xlsx`、`csv`、`docx`、`pdf`、`jpg`、`jpeg`、`png`、`txt`。
  - 上传文件保存到当前项目的 `uploads` 文件夹。
  - 文件元数据写入 SQLite，包括文件名、文件类型、保存路径、上传时间、所属项目 ID。
  - Excel/CSV 使用 pandas 读取，并在页面预览前 20 行。
  - TXT 读取正文并在页面展示。
  - DOCX 提取正文并展示前 2000 字符。
  - PDF 当前只保存，不做正文解析，页面显示文件名和保存路径。
  - JPG/JPEG/PNG 在页面显示缩略图。
  - 当前项目已上传文件会以列表形式展示，并可展开查看预览或删除文件。

## 目录结构

```text
amazon_ai_ops_center/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── data/
├── projects/
│   └── {project_id}/
│       ├── uploads/
│       └── outputs/
├── services/
└── utils/
```

## 本地运行

1. 进入项目目录：

   ```bash
   cd amazon_ai_ops_center
   ```

2. 创建并激活 Python 虚拟环境：

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

4. 按需复制环境变量示例文件：

   ```bash
   cp .env.example .env
   ```

   > `.env.example` 不包含任何真实 API Key。请不要把真实密钥提交到代码仓库。

5. 启动 Streamlit：

   ```bash
   python -m streamlit run app.py
   ```

浏览器打开 Streamlit 提示的本地地址后，即可创建产品项目、填写项目资料、上传项目文件、查看解析预览并删除不需要的上传文件。

## 数据说明

- 默认 SQLite 数据库路径：`data/ops_center.sqlite3`。
- 默认项目文件根目录：`projects/`。
- 上传文件默认保存在：`projects/{project_id}/uploads/`。
- 可在 `.env` 中通过 `DATABASE_PATH` 和 `PROJECTS_DIR` 覆盖默认路径。
- SQLite 表：
  - `projects`：项目基础资料。
  - `project_files`：上传文件元数据，包含 `filename`、`file_type`、`saved_path`、`uploaded_at`、`project_id`。

## 注意事项

- PDF 第二阶段仅做保存与文件名、保存路径展示，暂不做正文解析。
- CSV 默认优先按 UTF-8 读取；若遇到编码问题，会尝试使用 GB18030。
- DOCX 预览仅提取段落文本，不处理复杂表格、图片或批注。
- 依赖版本使用 Python 3.12 兼容范围，避免固定到不兼容版本。
