import streamlit as st
from utils.auth_decorator import require_auth
import json
import time
import asyncio
import nest_asyncio
from urllib.parse import quote_plus, urlparse
import traceback

# 确保在Streamlit环境中可以运行异步代码
try:
    nest_asyncio.apply()
except RuntimeError:
    pass

# 使用工具层封装的DDGS接口，避免页面直接依赖第三方库
from utils.ddgs_utils import search_ddgs as util_search_ddgs

@require_auth
def main():
    # 自定义CSS样式 - 简化版
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #4776E6 0%, #8E54E9 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .search-tab.active {
        background: linear-gradient(45deg, #4776E6, #8E54E9);
        color: white;
    }
    
    .result-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #e1e5e9;
        transition: all 0.3s ease;
    }
    
    .result-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1a0dab;
        margin-bottom: 0.5rem;
    }
    
    .result-url {
        font-size: 0.9rem;
        color: #006621;
        margin-bottom: 0.5rem;
        word-break: break-all;
    }
    
    .result-snippet {
        font-size: 0.95rem;
        color: #545454;
        line-height: 1.5;
    }
    
    .image-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 1rem;
    }
    
    .video-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1.5rem;
    }
    
    .news-card {
        display: flex;
        margin-bottom: 1.5rem;
        background: white;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 页面标题
    st.markdown("""
    <div class="main-header">
        <h1>🔍 坤塔 智能搜索</h1>
        <p>专注隐私保护的搜索引擎</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 初始化会话状态
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ""
    if 'search_type' not in st.session_state:
        st.session_state.search_type = "text"
    if 'tab_results' not in st.session_state:
        st.session_state.tab_results = {}
    if 'page' not in st.session_state:
        st.session_state.page = 1
    
    # 搜索表单
    with st.form(key="search_form"):
        col1, col2 = st.columns([4, 1])
        with col1:
            search_query = st.text_input(
                "搜索关键词",
                value=st.session_state.search_query,
                placeholder="输入关键词搜索..."
            )
        with col2:
            search_type = st.selectbox(
                "搜索类型",
                options=["text", "images", "videos", "news"],
                format_func=lambda x: {"text": "网页", "images": "图片", "videos": "视频", "news": "新闻"}[x],
                index=["text", "images", "videos", "news"].index(st.session_state.search_type)
            )
        
        submit = st.form_submit_button("搜索", use_container_width=True)
        
        if submit and search_query:
            st.session_state.search_query = search_query
            st.session_state.search_type = search_type
            st.session_state.tab_results = {}  # 清空所有标签页的结果
            st.session_state.page = 1
            st.rerun()
    
    # 显示搜索结果
    if st.session_state.search_query:
        # 创建搜索标签页
        tab_options = ["网页", "图片", "视频", "新闻"]
        tab_values = ["text", "images", "videos", "news"]
        
        # 使用键值对存储每个标签页的搜索结果
        if 'tab_results' not in st.session_state:
            st.session_state.tab_results = {}
        
        # 获取当前选择的标签页
        selected_tab = st.radio(
            "搜索类型",
            options=tab_options,
            index=tab_values.index(st.session_state.search_type),
            horizontal=True,
            label_visibility="collapsed"
        )
        
        # 获取选择的搜索类型
        selected_search_type = tab_values[tab_options.index(selected_tab)]
        
        # 如果搜索类型改变，重置页码并清除该类型的结果
        if selected_search_type != st.session_state.search_type:
            st.session_state.search_type = selected_search_type
            st.session_state.page = 1
            if selected_search_type in st.session_state.tab_results:
                del st.session_state.tab_results[selected_search_type]
        
        # 显示正在搜索的类型
        st.markdown(f"<div style='margin-bottom: 15px;'><b>当前搜索：</b> {selected_tab} - '{st.session_state.search_query}'</div>", unsafe_allow_html=True)
        
        # 检查是否需要执行搜索
        if selected_search_type not in st.session_state.tab_results:
            with st.spinner(f"正在搜索 '{st.session_state.search_query}' 的{selected_tab}..."):
                try:
                    results = search_ddgs(
                        st.session_state.search_query,
                        selected_search_type
                    )
                    st.session_state.tab_results[selected_search_type] = results
                except Exception as e:
                    st.error(f"搜索出错: {str(e)}")
                    st.code(traceback.format_exc())
                    st.session_state.tab_results[selected_search_type] = []
        
        # 显示结果
        display_search_results(
            st.session_state.tab_results.get(selected_search_type, []),
            selected_search_type,
            st.session_state.page
        )

def search_ddgs(query, search_type, max_results=30):
    """使用DDGS执行搜索（调用utils封装）"""
    try:
        return util_search_ddgs(query, search_type, max_results=max_results)
    except Exception as e:
        st.error(f"DDGS搜索出错: {str(e)}")
        st.code(traceback.format_exc())
        return []

def display_search_results(results, search_type, page=1):
    """显示搜索结果"""
    if not results:
        st.info("未找到相关结果")
        return
    
    # 分页
    items_per_page = 10
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_results = results[start_idx:end_idx]
    
    # 根据搜索类型显示不同格式的结果
    if search_type == "text":
        display_text_results(page_results)
    elif search_type == "images":
        display_image_results(page_results)
    elif search_type == "videos":
        display_video_results(page_results)
    elif search_type == "news":
        display_news_results(page_results)
    
    # 分页控制
    total_pages = (len(results) + items_per_page - 1) // items_per_page
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if page > 1:
                if st.button("← 上一页", use_container_width=True):
                    st.session_state.page = page - 1
                    st.rerun()
        
        with col2:
            st.markdown(f"<div style='text-align: center; padding: 5px;'><b>第 {page} 页 / 共 {total_pages} 页</b></div>", unsafe_allow_html=True)
        
        with col3:
            if page < total_pages:
                if st.button("下一页 →", use_container_width=True):
                    st.session_state.page = page + 1
                    st.rerun()

def display_text_results(results):
    """显示网页搜索结果"""
    for result in results:
        title = result.get("title", "无标题")
        url = result.get("href", "#")
        snippet = result.get("body", "无描述")
        # 提取来源与时间（不同结果可能字段名不同）
        source = (
            result.get("source")
            or result.get("website")
            or result.get("publisher")
            or result.get("hostname")
        )
        if not source and url and url != "#":
            try:
                source = urlparse(url).netloc
            except Exception:
                source = ""
        date = (
            result.get("date")
            or result.get("published")
            or result.get("published_time")
            or result.get("time")
        )
        
        st.markdown(f"""
        <div class="result-card">
            <a href="{url}" target="_blank" class="result-title">{title}</a>
            <div class="result-url">{url}</div>
            <div class="result-snippet">{snippet}</div>
            <div><small>{(source or '')}{(' · ' + date) if date else ''}</small></div>
        </div>
        """, unsafe_allow_html=True)

def display_image_results(results):
    """显示图片搜索结果"""
    cols = st.columns(4)
    for i, result in enumerate(results):
        image_url = result.get("image", "")
        title = result.get("title", "无标题")
        source_url = result.get("url", "#")
        
        with cols[i % 4]:
            st.image(image_url, caption=title, use_container_width=True)
            st.markdown(f"[查看原图]({source_url})")

def display_video_results(results):
    """显示视频搜索结果"""
    for result in results:
        title = result.get("title", "无标题")
        url = result.get("url", "#")
        thumbnail = result.get("thumbnail", "")
        duration = result.get("duration", "")
        publisher = result.get("publisher", "")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(thumbnail, use_container_width=True)
        with col2:
            st.markdown(f"#### [{title}]({url})")
            st.caption(f"发布者: {publisher} | 时长: {duration}")

def display_news_results(results):
    """显示新闻搜索结果"""
    for result in results:
        title = result.get("title", "无标题")
        url = result.get("url", "#")
        snippet = result.get("body", "无描述")
        source = result.get("source", "")
        date = result.get("date", "")
        
        st.markdown(f"""
        <div class="result-card">
            <a href="{url}" target="_blank" class="result-title">{title}</a>
            <div class="result-snippet">{snippet}</div>
            <div><small>{source} · {date}</small></div>
        </div>
        """, unsafe_allow_html=True)

# 确保页面在Streamlit导航中正确加载
if __name__ == "__main__":
    main()
