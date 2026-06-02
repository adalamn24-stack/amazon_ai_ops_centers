# amazon_ai_ops_centers

Amazon AI Operation Command Center V1.0 Streamlit 项目。

主要代码位于 `amazon_ai_ops_center/`。当前已完成第二阶段：项目资料中心支持上传 `xlsx`、`csv`、`docx`、`pdf`、`jpg`、`jpeg`、`png`、`txt`，文件保存到项目 `uploads` 文件夹，文件元数据写入 SQLite，提供 Excel/CSV/TXT/DOCX/图片预览能力，并支持删除已上传文件。

运行方式：

```bash
cd amazon_ai_ops_center
pip install -r requirements.txt
python -m streamlit run app.py
```
