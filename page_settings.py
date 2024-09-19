import streamlit as st

PAGE_HOME = st.Page(
    "pages/home.py",
    title='首页',
    icon=':material/home:'
)

PAGE_GPTS = st.Page(
    "pages/gpts.py",
    title='应用商店',
    icon=':material/home:'
)

PAGE_DOCUMENT_UTIL = st.Page(
    "pages/document_util.py",
    title='文档处理',
    icon=':material/home:'
)

PAGE_ASR = st.Page(
    "pages/asr.py",
    title='语音识别',
    icon=':material/home:'
)

PAGE_TTS = st.Page(
    "pages/tts.py",
    title='语音合成',
    icon=':material/home:'
)

# ********************应用商店************************、
PAGE_GPTS_AUTOWITER = st.Page(
    "pages/auto_write.py",
    title="超级写手",
    icon=":material/home:"
)

# ******************菜单配置********************
PAGES = {
    "APP": [PAGE_HOME],
    "GPTS": [PAGE_GPTS, PAGE_GPTS_AUTOWITER],
    "Toolkits": [PAGE_DOCUMENT_UTIL, PAGE_ASR, PAGE_TTS]
}