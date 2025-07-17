import streamlit as st

PAGE_HOME = st.Page(
    "page/home.py",
    title='首页',
    icon=':material/home:'
)

PAGE_GPTS = st.Page(
    "page/gpts.py",
    title='应用商店',
    icon=':material/home:'
)

PAGE_DOCUMENT_UTIL = st.Page(
    "page/document_util.py",
    title='文档处理',
    icon=':material/home:'
)

PAGE_HTML_VIEWER = st.Page(
    "page/html_viewer.py",
    title='网页预览',
    icon=':material/preview:'
)

PAGE_ASR = st.Page(
    "page/asr.py",
    title='语音识别',
    icon=':material/home:'
)

PAGE_TTS = st.Page(
    "page/tts.py",
    title='语音合成',
    icon=':material/home:'
)

PAGE_ARTICLE_RECREATION = st.Page(
    "page/article_recreation.py",
    title="文章再创作",
    icon=":material/edit_document:"
)

# ********************应用商店************************、
PAGE_GPTS_AUTOWITER = st.Page(
    "page/auto_write.py",
    title="超能写手",
    icon=":material/home:"
)

# ********************用户信息************************
PAGE_PROFILE = st.Page(
    "auth_pages/profile.py",
    title="个人信息",
    icon=":material/person:"
)

PAGE_HISTORY = st.Page(
    "page/history.py",
    title="历史记录",
    icon=":material/history:"
)

PAGE_SYSTEM_SETTINGS = st.Page(
    "page/system_settings.py",
    title="系统设置",
    icon=":material/settings:"
)

# Chatbot functionality has been integrated into the home page
# PAGE_CHATBOT definition removed

# HTML查看器页面，但不显示在菜单中
PAGE_HTML_VIEWER = st.Page(
    "page/html_viewer.py",
    title="HTML查看器",
    icon=":material/code:"
)

# ******************菜单配置********************
PAGES = {
    "APP": [PAGE_HOME],  # Chatbot functionality integrated into home page
    "GPTS": [PAGE_GPTS, PAGE_GPTS_AUTOWITER],
        "Toolkits": [PAGE_DOCUMENT_UTIL, PAGE_ASR, PAGE_TTS, PAGE_ARTICLE_RECREATION],
    "用户": [PAGE_PROFILE, PAGE_HISTORY, PAGE_SYSTEM_SETTINGS, PAGE_HTML_VIEWER]
}

# 隐藏页面（不在菜单中显示，但可以通过代码跳转）
HIDDEN_PAGES = [PAGE_HTML_VIEWER]