import streamlit as st
from utils.auth_decorator import require_auth
import streamlit.components.v1 as components

@require_auth
def main():
    # 自定义CSS样式
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .nav-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border: 1px solid #e1e5e9;
        transition: all 0.3s ease;
        height: 100%;
        text-align: center;
    }
    
    .nav-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    .nav-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        display: block;
    }
    
    .nav-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    
    .nav-desc {
        font-size: 0.9rem;
        color: #7f8c8d;
        margin-bottom: 1rem;
    }
    
    .nav-button {
        background: linear-gradient(45deg, #4776E6, #8E54E9);
        color: black !important;
        border: none;
        padding: 0.7rem 1.5rem;
        border-radius: 25px;
        text-decoration: none;
        display: inline-block;
        transition: all 0.3s ease;
        font-weight: 600;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        letter-spacing: 0.5px;
    }
    
    .nav-button:hover {
        transform: scale(1.05);
        text-decoration: none;
        color: white !important;
        box-shadow: 0 6px 15px rgba(0,0,0,0.3);
        background: linear-gradient(45deg, #5E85F7, #A169FA);
    }
    
    .search-section {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        border: 1px solid #e9ecef;
    }
    
    .section-title {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .iframe-container {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 页面标题
    st.markdown("""
    <div class="main-header">
        <h1>🚀 内容创作导航中心</h1>
        <p>一站式内容创作工具集合，提升您的创作效率</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 搜索引擎区域
    st.markdown("""
    <div class="search-section">
        <div class="section-title">🔍 智能搜索引擎</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 提供多个搜索引擎选项
    search_col1, search_col2, search_col3 = st.columns(3)
    
    with search_col1:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">🔍</div>
            <div class="nav-title">SearXNG</div>
            <div class="nav-desc">隐私保护搜索引擎</div>
            <a href="http://localhost:8080" target="_blank" class="nav-button">打开搜索</a>
        </div>
        """, unsafe_allow_html=True)
        
    with search_col2:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">🌐</div>
            <div class="nav-title">秘塔AI搜索</div>
            <div class="nav-desc">没有广告，直达结果</div>
            <a href="https://metaso.cn/" target="_blank" class="nav-button">打开搜索</a>
        </div>
        """, unsafe_allow_html=True)
        
    with search_col3:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">🔒</div>
            <div class="nav-title">Google搜索</div>
            <div class="nav-desc">Google搜索引擎</div>
            <a href="https://www.google.com/" target="_blank" class="nav-button">打开搜索</a>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 内容平台导航
    st.markdown('<div class="section-title">📝 内容发布平台</div>', unsafe_allow_html=True)
    
    # 第一行：主要平台
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">💬</div>
            <div class="nav-title">微信公众号</div>
            <div class="nav-desc">微信公众平台管理</div>
            <a href="https://mp.weixin.qq.com/" target="_blank" class="nav-button">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">📰</div>
            <div class="nav-title">头条号</div>
            <div class="nav-desc">今日头条内容发布</div>
            <a href="https://mp.toutiao.com/profile_v4/index" target="_blank" class="nav-button">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">🏠</div>
            <div class="nav-title">百家号</div>
            <div class="nav-desc">百度百家号发布</div>
            <a href="https://baijiahao.baidu.com/" target="_blank" class="nav-button">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">💻</div>
            <div class="nav-title">CSDN</div>
            <div class="nav-desc">技术博客平台</div>
            <a href="https://www.csdn.net/" target="_blank" class="nav-button">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 第二行：其他平台
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">📧</div>
            <div class="nav-title">即梦</div>
            <div class="nav-desc">AI视频创作</div>
            <a href="https://jimeng.jianying.com/ai-tool/home" target="_blank" class="nav-button">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">📱</div>
            <div class="nav-title">剪映</div>
            <div class="nav-desc">AI一键生成视频</div>
            <a href="https://www.jianying.com/ai-creator/start" target="_blank" class="nav-button">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col7:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">🐟</div>
            <div class="nav-title">大鱼号</div>
            <div class="nav-desc">UC大鱼号平台</div>
            <a href="https://mp.dayu.com/dashboard/index" target="_blank" class="nav-button">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col8:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">🔧</div>
            <div class="nav-title">爱贝克助手</div>
            <div class="nav-desc">内容同步工具</div>
            <a href="chrome-extension://jejejajkcbhejfiocemmddgbkdlhhngm/options.html" target="_blank" class="nav-button">打开扩展</a>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 工具区域
    st.markdown('<div class="section-title">🛠️ 创作工具</div>', unsafe_allow_html=True)
    
    col9, col10, col11, col12 = st.columns(4)
    
    with col9:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">✍️</div>
            <div class="nav-title">Markdown编辑器</div>
            <div class="nav-desc">本地Markdown编辑工具</div>
            <a href="http://localhost:82/" target="_blank" class="nav-button">打开编辑器</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col10:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">🤖</div>
            <div class="nav-title">AI写作助手</div>
            <div class="nav-desc">智能内容生成</div>
            <a href="/auto_write" target="_self" class="nav-button">开始写作</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col11:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">📊</div>
            <div class="nav-title">数据分析</div>
            <div class="nav-desc">内容数据统计</div>
            <a href="/history" target="_self" class="nav-button">查看历史</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col12:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-icon">⚙️</div>
            <div class="nav-title">系统设置</div>
            <div class="nav-desc">个人偏好配置</div>
            <a href="/settings" target="_self" class="nav-button">打开设置</a>
        </div>
        """, unsafe_allow_html=True)
    
    # 页脚信息
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; color: #7f8c8d; padding: 2rem; border-top: 1px solid #e9ecef; margin-top: 2rem;">
        <p>🚀 内容创作导航中心 | 让创作更高效 | 2024</p>
        <p style="font-size: 0.8rem;">提示：点击各个平台卡片可直接跳转到对应平台</p>
    </div>
    """, unsafe_allow_html=True)

# Call the main function
main()