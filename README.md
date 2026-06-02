# amazon_ai_ops_centers

Amazon AI Operation Command Center V1.0 Streamlit 项目。

主要代码位于 `amazon_ai_ops_center/`。当前已完成第三阶段：在第一、二阶段的项目资料中心和文件上传能力基础上，新增 OpenAI 服务封装模块、`.env` API Key 读取、AI 配置检查，以及将 AI 输出保存为 Markdown 文件的能力。

运行方式：

```bash
cd amazon_ai_ops_center
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，设置 OPENAI_API_KEY=你的真实 API Key
python -m streamlit run app.py
```

> 请不要提交真实 API Key；页面只会展示脱敏后的配置状态。
