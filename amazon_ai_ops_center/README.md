# Amazon AI Operation Command Center V1.0

内部使用的 Streamlit 运营工具。第一阶段只包含项目基础框架、SQLite 项目资料存储、项目文件夹管理，以及可点击的功能导航占位页。

## 功能范围

- 创建、选择、删除产品项目。
- 使用 SQLite 保存项目资料。
- 每个项目自动创建独立目录：
  - `projects/{project_id}/uploads`
  - `projects/{project_id}/outputs`
- 左侧导航包含以下第一阶段占位页面：
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

## 目录结构

```text
amazon_ai_ops_center/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── data/
├── projects/
├── pages/
├── services/
├── utils/
└── prompts/
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
   streamlit run app.py
   ```

浏览器打开 Streamlit 提示的本地地址后，即可创建产品项目并填写项目资料。

## 数据说明

- 默认 SQLite 数据库路径：`data/ops_center.sqlite3`。
- 默认项目文件根目录：`projects/`。
- 可在 `.env` 中通过 `DATABASE_PATH` 和 `PROJECTS_DIR` 覆盖默认路径。
