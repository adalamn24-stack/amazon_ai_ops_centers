# Amazon AI Operation Command Center V1.0

内部使用的 Streamlit 运营工具。当前已完成第四阶段：在保留项目资料中心、文件上传与预览、OpenAI 服务封装和 AI 配置检查能力的基础上，新增“竞品分析”模块，可基于用户手动输入和当前项目上传文件生成竞品分析报告、图片/A+分析、机会点和导出文件。

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
- 项目资料中心支持文件上传与资料解析：
  - 支持上传 `xlsx`、`csv`、`docx`、`pdf`、`jpg`、`jpeg`、`png`、`txt`。
  - 上传文件保存到当前项目的 `uploads` 文件夹。
  - 文件元数据写入 SQLite，包括文件名、文件类型、保存路径、上传时间、所属项目 ID。
  - Excel/CSV 使用 pandas 读取，并在页面预览前 20 行。
  - TXT 读取正文并在页面展示。
  - DOCX 提取正文并展示前 2000 字符。
  - PDF 当前只保存，不做正文解析，页面显示文件名和保存路径。
  - JPG/JPEG/PNG 在页面显示缩略图。
  - 当前项目已上传文件会以列表形式展示，并可展开查看预览或删除文件。
- 页面左侧新增“AI配置检查”：
  - 未检测到 `OPENAI_API_KEY` 时提示用户在 `.env` 中配置。
  - 已检测到 `OPENAI_API_KEY` 时只展示脱敏状态，不显示完整 Key。
- `services/llm_service.py` 封装 OpenAI 调用：
  - `generate_text(system_prompt, user_prompt, model="gpt-4.1-mini")`
  - `analyze_table_with_prompt(df, prompt)`
  - `analyze_text_with_prompt(text, prompt)`
  - `analyze_images_with_prompt(image_paths, prompt)`
- 所有 AI 输出会保存为 Markdown 文件；当页面已选择项目时，输出保存到当前项目的 `projects/{project_id}/outputs/` 文件夹。
- “竞品分析”模块支持：
  - 手动录入多个竞品的 ASIN、Amazon 链接、品牌、标题、价格、评分、评论数、变体数、核心卖点和备注。
  - 从当前项目 `uploads` 文件夹选择 xlsx、csv、txt、docx、jpg、jpeg、png、pdf 资料。
  - 为已选文件标记用途：竞品评论表、竞品关键词表、竞品 Listing 文案、竞品主图截图、竞品 A+ 截图、竞品页面截图、其他资料。
  - 设置目标站点（US/UK/DE/FR/IT/ES/CA/JP）、产品风险类型、输出语言和分析深度。
  - 调用 `services/llm_service.py` 中的文本/图片分析能力生成结构化竞品分析报告。
  - 当未配置 `OPENAI_API_KEY` 时提示先配置 API Key，不崩溃、不触发 AI 调用。
  - 不自动爬取 Amazon 页面，不自动登录 Amazon；资料来源仅为用户手动输入和上传文件。
  - 导出并提供下载：`projects/{project_id}/outputs/competitor_analysis.md` 和 `projects/{project_id}/outputs/competitor_analysis.xlsx`。


## 目录结构

```text
amazon_ai_ops_center/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── data/
├── outputs/
├── projects/
│   └── {project_id}/
│       ├── uploads/
│       └── outputs/
├── services/
│   ├── competitor_service.py
│   ├── database.py
│   ├── llm_service.py
│   ├── project_files.py
│   └── report_export_service.py
├── prompts/
│   └── competitor_analysis_prompt.md
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

4. 复制环境变量示例文件并配置 OpenAI API Key：

   ```bash
   cp .env.example .env
   ```

   在 `.env` 中设置：

   ```text
   OPENAI_API_KEY=your_api_key_here
   ```

   > `.env.example` 不包含任何真实 API Key。请不要把真实密钥提交到代码仓库，也不要在日志、截图或 README 中粘贴真实 Key。

5. 启动 Streamlit：

   ```bash
   python -m streamlit run app.py
   ```

浏览器打开 Streamlit 提示的本地地址后，即可创建产品项目、填写项目资料、上传项目文件、查看解析预览、检查 OpenAI 配置状态，并使用“竞品分析”模块生成和下载竞品报告。

## 第4阶段：竞品分析模块使用方法

1. 在左侧先创建或选择一个产品项目。
2. 如需使用文件资料，先进入“项目资料中心”上传竞品评论表、关键词表、Listing 文案、主图/A+截图或其他资料。
3. 进入左侧“竞品分析”：
   - 在“竞品手动输入表”中录入一个或多个竞品。
   - 在“选择项目已上传文件”中勾选当前项目 uploads 文件。
   - 给每个文件设置用途分类，帮助 AI 区分评论、关键词、Listing、主图、A+、页面截图或其他资料。
   - 设置目标站点、产品风险类型、输出语言和分析深度。
4. 确认已配置 `OPENAI_API_KEY` 后点击“生成竞品分析报告”。如果没有 API Key，页面会提示先配置，按钮不可用。
5. 报告生成后会展示在页面中，并保存到当前项目 outputs 文件夹：
   - Markdown：`projects/{project_id}/outputs/competitor_analysis.md`
   - Excel：`projects/{project_id}/outputs/competitor_analysis.xlsx`
6. 页面底部提供“下载 Markdown 报告”和“下载 Excel 报告”按钮。

Excel 文件包含以下 sheet：竞品基础信息、竞品卖点分析、评论VOC分析、关键词分析、主图分析、A+分析、机会点总结、主图Brief、A+Brief。

注意：PDF 当前仅记录文件信息，不自动解析正文；如需 AI 深度分析 PDF 内容，请把关键内容另存为 TXT/DOCX/CSV 后上传。

## AI 服务封装说明

- `OPENAI_API_KEY` 由项目根目录下的 `.env` 或系统环境变量读取。
- 默认模型为 `gpt-4.1-mini`，可在 `generate_text` 调用时通过 `model` 参数覆盖。
- 表格分析默认将 DataFrame 前 100 行转换为 Markdown 表格发送给模型。
- 文本分析会把业务提示词和待分析文本组合后发送给模型。
- 图片分析会把本地图片转换为 data URL 后发送给支持视觉输入的模型。
- SDK 异常、缺少 API Key、缺少依赖、空输入、空响应等情况会转换为面向页面的错误信息。
- 服务层不会打印或记录完整 API Key。

## 数据说明

- 默认 SQLite 数据库路径：`data/ops_center.sqlite3`。
- 默认项目文件根目录：`projects/`。
- 上传文件默认保存在：`projects/{project_id}/uploads/`。
- AI 输出默认保存在：当前项目的 `projects/{project_id}/outputs/`。
- 可在 `.env` 中通过 `DATABASE_PATH` 和 `PROJECTS_DIR` 覆盖默认路径。
- SQLite 表：
  - `projects`：项目基础资料。
  - `project_files`：上传文件元数据，包含 `filename`、`file_type`、`saved_path`、`uploaded_at`、`project_id`。

## 注意事项

- PDF 当前仅做保存与文件名、保存路径展示，暂不做正文解析。
- CSV 默认优先按 UTF-8 读取；若遇到编码问题，会尝试使用 GB18030。
- DOCX 预览仅提取段落文本，不处理复杂表格、图片或批注。
- `.env.example` 中的 `OPENAI_API_KEY=your_api_key_here` 只是占位符，复制后必须替换为真实 Key 才会显示已配置。
- 依赖版本使用 Python 3.12 兼容范围，避免固定到不兼容版本。
