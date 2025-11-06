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
    <div class="search-section" style="background: linear-gradient(145deg, #f8f9fa, #ffffff); border-radius: 15px; padding: 2rem; margin-bottom: 2rem; border: 1px solid #e9ecef; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <div class="section-title" style="background: linear-gradient(90deg, #4776E6, #8E54E9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; font-size: 1.8rem; margin-bottom: 1.5rem;">🔍 智能搜索引擎</div>
        <p style="text-align: center; margin-bottom: 2rem; color: #555; font-size: 1rem;">选择适合您的搜索引擎，获取更精准的创作素材</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 提供多个搜索引擎选项
    search_col1, search_col2, search_col3, search_col4 = st.columns(4)
    
    with search_col1:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #4285F4;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #4285F4;">🔍</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">SearXNG</div>
            <div class="nav-desc" style="height: 40px;">隐私保护元搜索引擎，整合多平台搜索结果</div>
            <a href="http://localhost:8080" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #4285F4, #34A853); font-weight: 700;">打开搜索</a>
        </div>
        """, unsafe_allow_html=True)
        
    with search_col2:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #FF5722;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #FF5722;">🌐</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">秘塔AI搜索</div>
            <div class="nav-desc" style="height: 40px;">国产智能搜索引擎，没有广告，直达结果</div>
            <a href="https://metaso.cn/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #FF5722, #FF9800); font-weight: 700;">打开搜索</a>
        </div>
        """, unsafe_allow_html=True)
        
    with search_col3:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #1e90ff;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #1e90ff;">🏆</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">大模型排行榜</div>
            <div class="nav-desc" style="height: 40px;">领先AI模型排行榜与评测（LM Arena）</div>
            <a href="https://lmarena.ai/leaderboard" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #1e90ff, #00bcd4); font-weight: 700;">打开网站</a>
        </div>
        """, unsafe_allow_html=True)
        
    with search_col4:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #8E54E9;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #8E54E9;">🔎</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">坤塔搜索</div>
            <div class="nav-desc" style="height: 40px;">多功能搜索引擎，支持文本、图片、视频和新闻</div>
            <a href="/ddgs_search" target="_self" class="nav-button" style="background: linear-gradient(45deg, #667eea, #764ba2); font-weight: 700;">打开搜索</a>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 内容平台区域
    st.markdown("""
    <div class="section-title" style="background: linear-gradient(90deg, #11998e, #38ef7d); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; font-size: 1.8rem; margin: 1.5rem 0;">
        📰 内容发布平台
    </div>
    <p style="text-align: center; margin-bottom: 2rem; color: #555; font-size: 1rem;">一键连接主流内容平台，快速发布您的创作成果</p>
    """, unsafe_allow_html=True)
    
    # 第一行：主要平台
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #07C160;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #07C160;">📰</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">微信公众号</div>
            <div class="nav-desc" style="height: 40px;">最大的中文内容平台，覆盖12亿+用户</div>
            <a href="https://mp.weixin.qq.com/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #07C160, #11998e); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #d43d3d;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #d43d3d;">📣</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">头条号</div>
            <div class="nav-desc" style="height: 40px;">今日头条内容创作平台，流量变现能力强</div>
            <a href="https://mp.toutiao.com/profile_v4/index" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #d43d3d, #ff4757); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #1A73E8;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #1A73E8;">🐟</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">大鱼号</div>
            <div class="nav-desc" style="height: 40px;">UC大鱼号内容平台，流量变现能力强</div>
            <a href="https://mp.dayu.com/dashboard/index" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #1A73E8, #6C5CE7); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #9C27B0;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #9C27B0;">🐟</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">企鹅号</div>
            <div class="nav-desc" style="height: 40px;">企鹅号内容平台，流量变现能力强</div>
            <a href="https://om.qq.com/main" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #9C27B0, #BA68C8); font-weight: 700;">打开扩展</a>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 第二行：其他平台
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #2932e1;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #2932e1;">📝</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">百家号</div>
            <div class="nav-desc" style="height: 40px;">百度官方内容平台，搜索引擎直达流量</div>
            <a href="https://baijiahao.baidu.com" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #2932e1, #3b5ee7); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #CA0C16;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #CA0C16;">📚</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">CSDN</div>
            <div class="nav-desc" style="height: 40px;">国内最大的技术内容社区和创作者平台</div>
            <a href="https://www.csdn.net/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #CA0C16, #e74c3c); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col7:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #0066FF;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #0066FF;">📱</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">知乎</div>
            <div class="nav-desc" style="height: 40px;">高质量问答社区，聚集专业内容创作者</div>
            <a href="https://www.zhihu.com/creator" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #0066FF, #0099FF); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col8:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #EA6F5A;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #EA6F5A;">📊</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">简书</div>
            <div class="nav-desc" style="height: 40px;">优质创作社区，聚焦原创文学内容</div>
            <a href="https://www.jianshu.com/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #EA6F5A, #FF7E79); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # AI视频工具区域
    st.markdown("""
    <div class="section-title" style="background: linear-gradient(90deg, #FF416C, #FF4B2B); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; font-size: 1.8rem; margin: 1.5rem 0;">
        🎬 AI视频创作工具
    </div>
    <p style="text-align: center; margin-bottom: 2rem; color: #555; font-size: 1rem;">智能视频生成和编辑工具，轻松创建专业级视频内容</p>
    """, unsafe_allow_html=True)
    
    # AI视频创作工具
    video_col1, video_col2, video_col3 = st.columns(3)
    
    with video_col1:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #00B4DB;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #00B4DB;">🎞️</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">海螺AI视频</div>
            <div class="nav-desc" style="height: 40px;">文本一键生成精美视频，支持多种风格和模板</div>
            <a href="https://hailuoai.com/create" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #00B4DB, #0083B0); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
        
    with video_col2:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #FF6B6B;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #FF6B6B;">🎥</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">即梦</div>
            <div class="nav-desc" style="height: 40px;">字节跳动旗下AI视频生成工具，一键生成高质量视频</div>
            <a href="https://jimeng.jianying.com/ai-tool/home" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #FF6B6B, #FF8E8E); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with video_col3:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #4ECDC4;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #4ECDC4;">🎬</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">剪映</div>
            <div class="nav-desc" style="height: 40px;">专业视频剪辑工具，AI一键生成精美视频内容</div>
            <a href="https://www.jianying.com/ai-creator/start" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #4ECDC4, #26C6DA); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 工具区域
    st.markdown("""
    <div class="section-title" style="background: linear-gradient(90deg, #6a11cb, #2575fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; font-size: 1.8rem; margin: 1.5rem 0;">
        🛠️ 创作工具
    </div>
    <p style="text-align: center; margin-bottom: 2rem; color: #555; font-size: 1rem;">专业内容创作工具，提升您的写作效率与质量</p>
    """, unsafe_allow_html=True)
    
    col9, col10, col11, col12 = st.columns(4)
    
    with col9:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #3498db;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #3498db;">✍️</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">Markdown编辑器</div>
            <div class="nav-desc" style="height: 40px;">本地实时预览Markdown编辑器，支持富文本格式</div>
            <a href="http://localhost:82/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #3498db, #2980b9); font-weight: 700;">打开编辑器</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col10:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #9b59b6;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #9b59b6;">🤖</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">AI写作助手</div>
            <div class="nav-desc" style="height: 40px;">智能内容生成引擎，一键生成高质量文章</div>
            <a href="/auto_write" target="_self" class="nav-button" style="background: linear-gradient(45deg, #9b59b6, #8e44ad); font-weight: 700;">开始写作</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col11:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #e67e22;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #e67e22;">📊</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">数据分析</div>
            <div class="nav-desc" style="height: 40px;">内容数据统计与分析，追踪您的创作进展</div>
            <a href="/history" target="_self" class="nav-button" style="background: linear-gradient(45deg, #e67e22, #d35400); font-weight: 700;">查看历史</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col12:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #3498db;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #3498db;">🎨</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">LiblibAI 生图</div>
            <div class="nav-desc" style="height: 40px;">专业AI图像生成工具，释放创意无限可能</div>
            <a href="https://www.liblib.art/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #3498db, #2980b9); font-weight: 700;">开始创作</a>
        </div>
        """, unsafe_allow_html=True)

    # 新增创作工具：Google AI Studio 与 Runninghub 生图
    st.markdown("<br>", unsafe_allow_html=True)

    tools_col1, tools_col2 = st.columns(2)

    with tools_col1:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #4285F4;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #4285F4;">🧪</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">Google AI Studio</div>
            <div class="nav-desc" style="height: 40px;">谷歌模型与提示创作平台，支持多模型测试与部署</div>
            <a href="https://aistudio.google.com/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #4285F4, #34A853); font-weight: 700;">打开平台</a>
        </div>
        """, unsafe_allow_html=True)

    with tools_col2:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #2ECC71;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #2ECC71;">🖼️</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">Runninghub 生图</div>
            <div class="nav-desc" style="height: 40px;">国内生图平台，支持多风格高质量图像生成</div>
            <a href="https://www.runninghub.cn/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #2ECC71, #27AE60); font-weight: 700;">开始创作</a>
        </div>
        """, unsafe_allow_html=True)

    # AI模型平台区域
    st.markdown("""
    <div class="section-title" style="background: linear-gradient(90deg, #3a1c71, #d76d77, #ffaf7b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; font-size: 1.8rem; margin: 1.5rem 0;">
        🧠 AI模型云平台
    </div>
    """, unsafe_allow_html=True)
    
    # 第一行：AI模型平台
    ai_col1, ai_col2, ai_col3, ai_col4 = st.columns(4)
    
    with ai_col1:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #FF6A00;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #FF6A00;">🔥</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">阿里百炼</div>
            <div class="nav-desc" style="height: 40px;">阿里云全功能AI平台，支持多模型训练与部署</div>
            <a href="https://bailian.console.aliyun.com/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #FF6A00, #ee0979); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with ai_col2:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #C13584;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #C13584;">🚀</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">模力方舟</div>
            <div class="nav-desc" style="height: 40px;">国产开源代码平台Gitee的AI开发与部署平台</div>
            <a href="https://ai.gitee.com/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #C13584, #833AB4); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with ai_col3:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #0078D7;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #0078D7;">🌐</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">魔塔社区</div>
            <div class="nav-desc" style="height: 40px;">阿里达摩院ModelScope开源模型社区</div>
            <a href="https://modelscope.cn/my/overview" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #0078D7, #00B2FF); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with ai_col4:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #FFD21E;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #FFD21E;">🤗</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">HuggingFace</div>
            <div class="nav-desc" style="height: 40px;">全球最大的开源AI模型库与应用社区</div>
            <a href="https://huggingface.co/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #FFD21E, #FF7A00); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 第二行：更多AI模型平台
    ai_col5, ai_col6, ai_col7, ai_col8 = st.columns(4)
    
    with ai_col5:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #6236FF;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #6236FF;">🌙</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">Moonshot AI</div>
            <div class="nav-desc" style="height: 40px;">国产顶级大模型，支持多模态与长上下文</div>
            <a href="https://platform.moonshot.cn/console/account" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #6236FF, #9400D3); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with ai_col6:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #1DB954;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #1DB954;">🧠</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">智谱BIGMODEL</div>
            <div class="nav-desc" style="height: 40px;">ChatGLM系列大模型官方平台，多模态能力强大</div>
            <a href="https://open.bigmodel.cn/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #1DB954, #006400); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with ai_col7:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #00B4DB;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #00B4DB;">🧠</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">ChatGPT</div>
            <div class="nav-desc" style="height: 40px;">全球领先的AI对话平台，提供智能对话与生成能力</div>
            <a href="https://chatgpt.com/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #00B4DB, #0083B0); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with ai_col8:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #3498DB;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #3498DB;">🔎</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">Deepseek</div>
            <div class="nav-desc" style="height: 40px;">强大的代码理解与生成能力，支持多种编程语言</div>
            <a href="https://platform.deepseek.com/usage" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #3498DB, #2980B9); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    # 第三行：新增AI模型平台
    ai_col9, ai_col10, ai_col11, ai_col12 = st.columns(4)
    
    with ai_col9:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #00B894;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #00B894;">💬</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">Qwen Chat</div>
            <div class="nav-desc" style="height: 40px;">通义千问官方对话平台，体验前沿中文大模型</div>
            <a href="https://chat.qwen.ai/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #00B894, #00CEC9); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with ai_col10:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #FF5722;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #FF5722;">🖥️</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">超算互联网</div>
            <div class="nav-desc" style="height: 40px;">算力与AI服务商城，一站式算力资源平台</div>
            <a href="https://www.scnet.cn/ui/mall/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #FF5722, #FF9800); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with ai_col11:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #FF6B35;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #FF6B35;">🎯</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">MiniMax</div>
            <div class="nav-desc" style="height: 40px;">国产领先多模态大模型，支持文本、语音、视频生成</div>
            <a href="https://www.minimaxi.com/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #FF6B35, #F7931E); font-weight: 700;">进入平台</a>
        </div>
        """, unsafe_allow_html=True)
    
    with ai_col12:
        st.markdown("""
        <div class="nav-card" style="background: linear-gradient(145deg, #ffffff, #f0f0f0); border-left: 4px solid #FFD100;">
            <div class="nav-icon" style="font-size: 2.8rem; color: #FFD100;">🐱</div>
            <div class="nav-title" style="font-size: 1.3rem; margin: 0.7rem 0;">LongCat</div>
            <div class="nav-desc" style="height: 40px;">美团AI对话平台，支持多轮对话与智能问答</div>
            <a href="https://longcat.chat/" target="_blank" class="nav-button" style="background: linear-gradient(45deg, #FFD100, #FFA900); font-weight: 700;">进入平台</a>
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