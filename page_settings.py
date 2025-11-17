import streamlit as st

PAGE_HOME = st.Page(
    "page/home.py",
    title='超能AI助手',
    icon=':material/home:'
)

PAGE_GPTS = st.Page(
    "page/gpts.py",
    title='导航中心',
    icon=':material/home:'
)

PAGE_DOCUMENT_UTIL = st.Page(
    "page/document_util.py",
    title='文档处理',
    icon=':material/home:'
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
    "auth_pages/profile_v2.py",
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

PAGE_COMMUNITY_MANAGEMENT = st.Page(
    "page/community_management.py",
    title="社区管理",
    icon=":material/cloud_sync:"
)

PAGE_DDGS_SEARCH = st.Page(
    "page/ddgs_search.py",
    title="坤塔搜索",
    icon=":material/search:"
)

PAGE_NEWS = st.Page(
    "page/news.py",
    title="新闻资讯",
    icon=":material/newspaper:"
)

# Chatbot functionality has been integrated into the home page
# PAGE_CHATBOT definition removed

# ******************菜单配置********************
PAGES = {
    "应用": [PAGE_HOME, PAGE_GPTS, PAGE_DDGS_SEARCH, PAGE_NEWS],  # Chatbot functionality integrated into home page
    "内容创作": [PAGE_GPTS_AUTOWITER, PAGE_ARTICLE_RECREATION],
    "工具": [PAGE_DOCUMENT_UTIL, PAGE_ASR, PAGE_TTS],
    "用户": [PAGE_PROFILE, PAGE_HISTORY, PAGE_COMMUNITY_MANAGEMENT, PAGE_SYSTEM_SETTINGS]
}

# 隐藏页面（不在菜单中显示，但可以通过代码跳转）
HIDDEN_PAGES = []