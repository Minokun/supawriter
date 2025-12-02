import streamlit as st
import requests
from datetime import datetime
from utils.auth_decorator import require_auth
import json
import re
import html


@require_auth
def main():
    # 自定义CSS样式 - 科技感设计
    st.markdown("""
    <style>
    .news-header {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        color: white;
        padding: 2.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.4);
        animation: gradient 3s ease infinite;
        background-size: 200% 200%;
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .news-item {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border-left: 4px solid #667eea;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
        display: flex;
        gap: 1rem;
        align-items: flex-start;
    }
    
    .news-item:hover {
        transform: translateX(4px);
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.2);
        border-left-color: #764ba2;
    }
    
    .news-image {
        width: 160px;
        height: 120px;
        object-fit: cover;
        border-radius: 8px;
        flex-shrink: 0;
    }
    
    .news-content {
        flex: 1;
        min-width: 0;
    }
    
    .news-item-simple {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border-left: 3px solid #667eea;
        transition: all 0.3s ease;
        margin-bottom: 0.8rem;
    }
    
    .news-item-simple:hover {
        transform: translateX(4px);
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.15);
        border-left-color: #764ba2;
    }
    
    .news-title {
        font-size: 1.1rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 0.5rem;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .news-summary {
        font-size: 0.9rem;
        color: #5a6c7d;
        line-height: 1.5;
        margin-bottom: 0.8rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .news-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
        color: #95a5a6;
        margin-top: 0.5rem;
    }
    
    .news-source {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 600;
    }
    
    .news-button {
        display: inline-block;
        padding: 0.5rem 1.2rem;
        margin-top: 0.8rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        text-decoration: none;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }
    
    .news-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
        text-decoration: none;
        color: white;
    }
    
    .category-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-right: 0.5rem;
        margin-bottom: 0.3rem;
    }
    
    .loading-spinner {
        text-align: center;
        padding: 3rem;
        color: #667eea;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 12px;
        padding: 12px 24px;
        border: 2px solid transparent;
        transition: all 0.3s ease;
        color: #2c3e50 !important;
    }
    
    /* Dark主题支持 */
    [data-theme="dark"] .stTabs [data-baseweb="tab"],
    .stApp[data-testid="stAppViewContainer"][class*="dark"] .stTabs [data-baseweb="tab"] {
        background: linear-gradient(145deg, #2d3748 0%, #1a202c 100%);
        color: #e2e8f0 !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        border-color: #667eea;
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 页面标题
    st.markdown("""
    <div class="news-header">
        <h1>🚀 AI新闻资讯中心</h1>
        <p style="font-size: 1.1rem; margin-top: 0.5rem; opacity: 0.95;">实时追踪人工智能领域最新动态</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 创建分类标签页
    tab1, tab2, tab3 = st.tabs([
        "📰 澎湃科技", 
        "⭐ 开源项目", 
        "🔥 实时新闻"
    ])
    
    # 澎湃科技
    with tab1:
        st.markdown("### 澎湃新闻 - 科技频道")
        fetch_thepaper_tech()
    
    # 最新开源项目
    with tab2:
        st.markdown("### SOTA开源项目")
        fetch_sota_projects()
    
    # 实时新闻
    with tab3:
        st.markdown("### 实时AI新闻")
        fetch_chinaz_news(news_type=1, title="实时新闻")


def fetch_thepaper_tech():
    """获取澎湃新闻科技频道文章"""
    try:
        url = "https://api.thepaper.cn/contentapi/nodeCont/getByChannelId"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Referer': 'https://www.thepaper.cn/',
            'Origin': 'https://www.thepaper.cn',
        }
        
        # 科技频道 channelId: 119908
        payload = {
            "channelId": "119908",
            "excludeContIds": [],
            "listRecommendIds": [],
            "province": None,
            "pageSize": 15,
            "startTime": None,
            "pageNum": 1
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('data', {}).get('list', [])
            
            if articles:
                for article in articles:
                    display_thepaper_tech_card(article)
            else:
                st.info("暂无文章数据")
                _fetch_fallback_ai_news()
        else:
            st.warning(f"获取澎湃科技新闻失败，状态码：{response.status_code}")
            _fetch_fallback_ai_news()
    except Exception as e:
        st.warning(f"获取澎湃科技新闻失败：{str(e)[:100]}")
        _fetch_fallback_ai_news()


def _fetch_fallback_ai_news():
    """备用新闻源：使用站长之家AI新闻"""
    st.info("💡 已切换到站长之家AI新闻")
    try:
        url = "https://app.chinaz.com/djflkdsoisknfoklsyhownfrlewfknoiaewf/ai/GetAiInfoList.aspx?flag=zh_cn&type=1&page=1&pagesize=12"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://app.chinaz.com/',
            'Accept': 'application/json, text/plain, */*',
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            news_list = data if isinstance(data, list) else data.get('data', [])
            
            if news_list:
                for idx, news in enumerate(news_list):
                    display_chinaz_card(news, 1, idx)
            else:
                st.warning("暂无新闻数据")
        else:
            st.error(f"获取备用新闻失败，状态码：{response.status_code}")
    except Exception as e:
        st.error(f"获取备用新闻失败：{str(e)[:100]}")


def display_thepaper_tech_card(article):
    """显示澎湃科技文章列表项"""
    title = html.escape(article.get('name', '无标题'))
    cont_id = article.get('contId', '')
    article_url = f"https://www.thepaper.cn/newsDetail_forward_{cont_id}" if cont_id else "https://www.thepaper.cn/"
    pub_time = article.get('pubTime', '')
    praise_times = article.get('praiseTimes', '0')
    interaction_num = article.get('interactionNum', '')
    pic = article.get('smallPic', '') or article.get('pic', '')
    node_name = html.escape(article.get('nodeInfo', {}).get('name', '澎湃科技'))
    
    # 获取标签
    tag_list = article.get('tagList', [])
    tags_html = ''
    if tag_list:
        tags = [html.escape(tag.get('tag', '')) for tag in tag_list[:3] if tag.get('tag')]
        if tags:
            tags_html = ' '.join([f'<span class="category-badge" style="font-size:0.7rem; padding:2px 6px;">{tag}</span>' for tag in tags])
    
    # 显示列表项（图文式）
    img_html = ''
    if pic:
        img_html = f'<img src="{html.escape(pic)}" class="news-image" referrerpolicy="no-referrer" onerror="this.style.display=\'none\'">'
    
    # 互动信息
    interaction_html = ''
    if interaction_num:
        interaction_html = f' · 💬 {interaction_num}'
    
    card_html = f'''<div class="news-item">{img_html}<div class="news-content"><div style="margin-bottom: 0.5rem;"><span style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color:white; padding:3px 10px; border-radius:6px; font-size:0.75rem; font-weight:600; display:inline-block;">{node_name}</span> {tags_html}</div><div class="news-title">{title}</div><div class="news-meta" style="margin-top: 0.5rem;"><span>⏰ {pub_time}</span><span>· 👍 {praise_times}{interaction_html}</span></div><a href="{article_url}" target="_blank" class="news-button">📖 阅读全文</a></div></div>'''
    
    st.markdown(card_html, unsafe_allow_html=True)


def fetch_sota_projects():
    """获取SOTA开源项目"""
    try:
        url = "https://sota.jiqizhixin.com/api/v2/sota/terms?order=generationAt&per=8&page=1"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            projects = data.get('data', [])
            
            if projects:
                # 使用单列列表展示
                for project in projects:
                    display_sota_card(project)
            else:
                st.info("暂无项目数据")
        else:
            st.error(f"获取数据失败，状态码：{response.status_code}")
    except Exception as e:
        st.error(f"获取开源项目失败：{str(e)}")


def display_sota_card(project):
    """显示SOTA项目列表项"""
    # 项目信息在source字段中
    source = project.get('source', {})
    title = source.get('name', '无标题')
    desc_full = source.get('summary', source.get('desc', '暂无描述'))
    description = desc_full[:200] + ('...' if len(desc_full) > 200 else '')  # 截取前200字符
    slug = source.get('slug', '')
    url = f"https://sota.jiqizhixin.com/project/{slug}"
    # 获取类别信息
    category = source.get('category', [])
    category_text = category[0] if category else '开源项目'
    
    # 显示列表项
    st.markdown(f"""
    <div class="news-item">
        <div class="news-content">
            <span class="category-badge">{category_text}</span>
            <div class="news-title">{title}</div>
            <div class="news-summary">{description}</div>
            <div class="news-meta">
                <span class="news-source">SOTA项目</span>
                <span>💻 {slug}</span>
            </div>
            <a href="{url}" target="_blank" class="news-button">🔗 查看项目</a>
        </div>
    </div>
    """, unsafe_allow_html=True)


def fetch_chinaz_news(news_type, title):
    """获取站长之家AI新闻"""
    try:
        url = f"https://app.chinaz.com/djflkdsoisknfoklsyhownfrlewfknoiaewf/ai/GetAiInfoList.aspx?flag=zh_cn&type={news_type}&page=1&pagesize=20"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://app.chinaz.com/',
            'Accept': 'application/json, text/plain, */*',
        }
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # 站长之家API直接返回数组，不是包含data字段的对象
            if isinstance(data, list):
                news_list = data
            else:
                news_list = data.get('data', [])
            
            if news_list:
                # 使用单列简单列表展示
                for idx, news in enumerate(news_list):
                    display_chinaz_card(news, news_type, idx)
            else:
                st.info(f"暂无{title}数据")
        else:
            st.error(f"获取数据失败，状态码：{response.status_code}")
    except Exception as e:
        st.error(f"获取{title}失败：{str(e)}")


def display_chinaz_card(news, news_type, idx=0):
    """显示站长之家新闻列表项"""
    
    def clean_text(content):
        if not content:
            return ''
        if isinstance(content, list):
            content = ' '.join(str(item) for item in content)
        # 将内容转为字符串
        content = str(content)
        # 1. 解码JSON中的Unicode转义字符（\u003C -> <, \u003E -> >, 等）
        # 使用正则表达式替换所有\uXXXX格式的Unicode转义
        def decode_unicode_escape(match):
            try:
                return chr(int(match.group(1), 16))
            except:
                return match.group(0)
        content = re.sub(r'\\u([0-9a-fA-F]{4})', decode_unicode_escape, content)
        # 2. 解码HTML实体（&lt; -> <, &gt; -> >, 等）
        content = html.unescape(content)
        # 3. 移除所有HTML标签（包括跨行的）
        content = re.sub(r'<[^>]+>', '', content, flags=re.DOTALL)
        # 4. 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content).strip()
        return content

    title = clean_text(news.get('title', '无标题')) or '无标题'
    description_raw = news.get('description', '')
    summary_raw = news.get('summary', '')
    
    # 清理description和summary
    description = clean_text(description_raw)
    summary = clean_text(summary_raw)
    
    # 卡片中显示description（截断到150字符）
    display_text = description if description else '暂无描述'
    if len(display_text) > 150:
        display_text = display_text[:150] + '...'
    display_text = clean_text(display_text)  # 再次清理，防止截断产生的问题
    
    # summary用于悬浮窗显示（完整内容）
    summary_for_popover = summary if summary else description

    url = news.get('url', '')  # 获取URL字段
    thumb = news.get('thumb', '')  # 获取图片字段
    source_name = clean_text(news.get('sourcename', '站长之家')) or '站长之家'
    addtime = clean_text(news.get('addtime', '最新')) or '最新'
    
    # 类型标签
    type_labels = {
        1: "实时新闻",
        2: "AI产品",
        3: "AI工具",
        4: "AI企业",
        5: "AI创作"
    }
    badge_label = type_labels.get(news_type, "资讯")
    
    # 对所有要插入HTML的文本进行转义，防止HTML注入
    title_escaped = html.escape(title)
    display_text_escaped = html.escape(display_text)
    source_name_escaped = html.escape(source_name)
    addtime_escaped = html.escape(addtime)
    url_escaped = html.escape(url) if url else ''
    
    # 根据是否有图片选择样式
    if thumb:  # 如果有图片，使用图文样式
        img_html = f'''<img src="{html.escape(thumb)}" class="news-image" referrerpolicy="no-referrer" onerror="this.style.display='none'">'''
        
        # 构建摘要按钮HTML - 只作为标记，点击展开下方的expander
        summary_button_html = ''
        if summary_for_popover:
            summary_button_html = f'''<span style="display: inline-block; padding: 0.2rem 0.6rem; background: #667eea; color: white; border-radius: 8px; font-size: 0.7rem; margin-left: 0.5rem;">📝 摘要↓</span>'''
        
        button_html = f'<a href="{url_escaped}" target="_blank" class="news-button">📖 阅读原文</a>' if url else ''
        
        st.markdown(f"""
        <div class="news-item">
            {img_html}
            <div class="news-content">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.8rem;">
                        <span class="category-badge">{badge_label}</span>
                        <span class="news-source" style="font-size: 0.8rem;">{source_name_escaped}</span>
                        <span style="color: #95a5a6; font-size: 0.75rem;">⏰ {addtime_escaped}</span>
                    </div>
                    {summary_button_html}
                </div>
                <div class="news-title">{title_escaped}</div>
                <div class="news-summary">{display_text_escaped}</div>
                <div style="margin-top: 0.8rem;">
                    {button_html}
        """, unsafe_allow_html=True)
        
        # 如果有summary，添加expander展开查看
        if summary_for_popover:
            with st.expander("📝 查看完整摘要", expanded=False):
                st.write(summary_for_popover)
        
    else:  # 如果没有图片，使用简单样式
        # 构建摘要按钮HTML - 只作为标记，点击展开下方的expander
        summary_button_html = ''
        if summary_for_popover:
            summary_button_html = f'''<span style="display: inline-block; padding: 0.2rem 0.6rem; background: #667eea; color: white; border-radius: 8px; font-size: 0.7rem; margin-left: 0.5rem;">📝 摘要↓</span>'''
        
        button_html = f'<a href="{url_escaped}" target="_blank" class="news-button">📖 阅读原文</a>' if url else ''
        
        st.markdown(f"""
        <div class="news-item-simple">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 0.8rem;">
                    <span class="category-badge">{badge_label}</span>
                    <span class="news-source" style="font-size: 0.8rem;">{source_name_escaped}</span>
                    <span style="color: #95a5a6; font-size: 0.75rem;">⏰ {addtime_escaped}</span>
                </div>
                {summary_button_html}
            </div>
            <div class="news-title">{title_escaped}</div>
            <div class="news-summary">{display_text_escaped}</div>
            <div style="margin-top: 0.8rem;">
                {button_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 如果有summary，添加expander展开查看
        if summary_for_popover:
            with st.expander("📝 查看完整摘要", expanded=False):
                st.write(summary_for_popover)


if __name__ == "__main__":
    main()
