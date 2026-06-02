# amazon_ai_ops_centers

Amazon AI Operation Command Center V1.0 Streamlit 项目。

主要代码位于 `amazon_ai_ops_center/`。当前已完成第四阶段：在第一、二阶段的项目资料中心和文件上传能力、第三阶段 OpenAI 服务封装与 AI 配置检查基础上，新增“竞品分析”模块。该模块基于用户手动输入和上传文件生成竞品基础信息、卖点、评论 VOC、关键词、主图/A+、机会点、图片 Brief，并导出 Markdown 与 Excel。

运行方式：

```bash
cd amazon_ai_ops_center
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，设置 OPENAI_API_KEY=你的真实 API Key
python -m streamlit run app.py
```

使用方式：左侧创建/选择项目后，可在“项目资料中心”上传 xlsx/csv/txt/docx/jpg/jpeg/png/pdf 资料，再进入“竞品分析”填写竞品表、选择上传文件并标记用途，生成 `projects/{project_id}/outputs/competitor_analysis.md` 和 `competitor_analysis.xlsx`。

> 请不要提交真实 API Key；页面只会展示脱敏后的配置状态。未配置 `OPENAI_API_KEY` 时，竞品分析页面会提示先配置，不会崩溃。
