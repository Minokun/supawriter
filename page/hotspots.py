import streamlit as st
import requests
import re
import json
from datetime import datetime
from utils.auth_decorator import require_auth
from utils.article_queue import add_to_queue, SOURCE_HOTSPOTS
import html
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# ============== 缓存数据获取函数 ==============
# 使用 st.cache_data 缓存API数据，TTL=300秒（5分钟）
# 这样在刷新周期内，点击按钮不会重新请求API

CACHE_TTL = 300  # 5分钟缓存

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _get_thepaper_data():
    """获取澎湃新闻数据（缓存）"""
    try:
        url = "https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.thepaper.cn/',
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return {'success': True, 'data': data.get('data', {}).get('hotNews', [])}
    except Exception as e:
        pass
    return {'success': False, 'error': '获取数据失败'}

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _get_36kr_data():
    """获取36Kr数据（缓存）"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    try:
        # 方案1: 今日热榜
        tophub_url = "https://tophub.today/n/Q1Vd5Ko85R"
        response = requests.get(tophub_url, headers=headers, timeout=15)
        if response.status_code == 200 and '安全验证' not in response.text:
            pattern = r'<td[^>]*>(\d+)\.</td>\s*<td[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>\s*</td>\s*<td[^>]*class="ws"[^>]*>([^<]*)</td>'
            items = re.findall(pattern, response.text)
            if items:
                result = []
                for rank, item_url, title, hot in items[:20]:
                    result.append({
                        'title': html.unescape(title.strip()),
                        'url': item_url,
                        'hot': hot.strip()
                    })
                return {'success': True, 'data': result, 'source': 'tophub'}
        
        # 方案2: 36Kr官网
        url = "https://36kr.com/newsflashes"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            links = re.findall(r'href="/newsflashes/(\d+)"[^>]*>([^<]+)</a>', response.text)
            if links:
                result = []
                for item_id, title in links[:20]:
                    title = html.unescape(title.strip())
                    if title and len(title) > 5:
                        result.append({
                            'title': title,
                            'url': f"https://36kr.com/newsflashes/{item_id}",
                            'hot': ''
                        })
                return {'success': True, 'data': result, 'source': '36kr'}
    except Exception:
        pass
    return {'success': False, 'error': '获取数据失败'}

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _get_baidu_data():
    """获取百度热搜数据（缓存）"""
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        json_match = re.search(r'<!--s-data:({.*?})-->', response.text)
        if json_match:
            data = json.loads(json_match.group(1))
            cards = data.get('data', {}).get('cards', [])
            if cards:
                content = cards[0].get('content', [])
                result = []
                for item in content:
                    result.append({
                        'title': item.get('word', ''),
                        'desc': item.get('desc', ''),
                        'url': item.get('url', '') or f"https://www.baidu.com/s?wd={item.get('word', '')}",
                        'hot_score': item.get('hotScore', '')
                    })
                return {'success': True, 'data': result}
    except Exception:
        pass
    return {'success': False, 'error': '获取数据失败'}

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _get_weibo_data():
    """获取微博热搜数据（缓存）"""
    try:
        url = "https://s.weibo.com/top/summary"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Cookie': 'SUB=_2AkMWJ_fdf8NxqwJRmP8SxWjnaY12yQ_EieKkjrMJJRMxHRl-yT9jqmgbtRB6PO6Nc9vS-pTH2Q7q8lW1D4q4e6P4'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            items = re.findall(r'<a href="(/weibo\?q=[^"]+)"[^>]*>(.*?)</a>.*?<span[^>]*>(.*?)</span>', response.text, re.DOTALL)
            if not items:
                items = re.findall(r'<a href="(/weibo\?q=[^"]+)"[^>]*>(.*?)</a>', response.text)
                items = [(x[0], x[1], "") for x in items]
            
            hot_list = []
            seen_titles = set()
            for link, title, heat in items:
                title = html.unescape(title).strip()
                heat = heat.strip()
                if title in ['首页', '发现', '游戏', '注册', '登录', '帮助', '剧集影响力榜', '综艺影响力榜', '更多']:
                    continue
                if title not in seen_titles:
                    seen_titles.add(title)
                    hot_list.append({
                        'title': title,
                        'url': f"https://s.weibo.com{link}",
                        'heat': heat
                    })
            return {'success': True, 'data': hot_list[:30]}
    except Exception:
        pass
    return {'success': False, 'error': '获取数据失败'}

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _get_douyin_data():
    """获取抖音热搜数据（缓存）"""
    try:
        url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.douyin.com/billboard/',
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            word_list = data.get('data', {}).get('word_list', [])
            if word_list:
                result = []
                for item in word_list:
                    result.append({
                        'title': item.get('word', ''),
                        'hot_value': item.get('hot_value', 0)
                    })
                return {'success': True, 'data': result}
    except Exception:
        pass
    return {'success': False, 'error': '获取数据失败'}

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _get_tophub_data(tophub_id: str):
    """通用今日热榜数据获取（缓存）"""
    try:
        url = f"https://tophub.today/n/{tophub_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200 and '安全验证' not in response.text:
            pattern = r'<td[^>]*>(\d+)\.</td>\s*<td[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>\s*</td>\s*<td[^>]*class="ws"[^>]*>([^<]*)</td>'
            items = re.findall(pattern, response.text)
            if items:
                result = []
                for rank, item_url, title, hot in items[:25]:
                    result.append({
                        'title': html.unescape(title.strip()),
                        'url': item_url,
                        'hot': hot.strip()
                    })
                return {'success': True, 'data': result}
    except Exception:
        pass
    return {'success': False, 'error': '获取数据失败'}

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _get_bilibili_data():
    """获取B站热门数据（缓存）"""
    try:
        url = "https://api.bilibili.com/x/web-interface/popular?ps=50&pn=1"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0 and data.get('data', {}).get('list'):
                hot_list = data['data']['list']
                result = []
                for item in hot_list[:30]:
                    stat = item.get('stat', {})
                    view = stat.get('view', 0)
                    view_str = f"{view/10000:.1f}万" if view >= 10000 else str(view)
                    result.append({
                        'title': item.get('title', ''),
                        'owner': item.get('owner', {}).get('name', ''),
                        'tname': item.get('tname', ''),
                        'view_str': view_str,
                        'bvid': item.get('bvid', '')
                    })
                return {'success': True, 'data': result, 'type': 'popular'}
        
        # 备用：搜索热词
        url2 = "https://api.bilibili.com/x/web-interface/search/square?limit=50"
        response2 = requests.get(url2, headers=headers, timeout=10)
        if response2.status_code == 200:
            data2 = response2.json()
            if data2.get('code') == 0 and data2.get('data', {}).get('trending', {}).get('list'):
                hot_list = data2['data']['trending']['list']
                result = []
                for item in hot_list[:30]:
                    keyword = item.get('keyword', item.get('show_name', ''))
                    icon = item.get('icon', '')
                    tag = ""
                    if icon:
                        if 'hot' in icon.lower():
                            tag = "🔥 "
                        elif 'new' in icon.lower():
                            tag = "🆕 "
                    result.append({
                        'keyword': f"{tag}{keyword}",
                        'url': f"https://search.bilibili.com/all?keyword={keyword}"
                    })
                return {'success': True, 'data': result, 'type': 'search'}
    except Exception:
        pass
    return {'success': False, 'error': '获取数据失败'}

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _get_zhihu_data():
    """获取知乎热榜数据（缓存）"""
    # 先尝试今日热榜
    tophub_result = _get_tophub_data("mproPpoq6O")
    if tophub_result['success']:
        return tophub_result
    
    # 备用：知乎API
    try:
        url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.zhihu.com/hot'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            hot_list = data.get('data', [])
            if hot_list:
                result = []
                for item in hot_list[:25]:
                    target = item.get('target', {})
                    result.append({
                        'title': target.get('title', ''),
                        'hot': item.get('detail_text', ''),
                        'url': f"https://www.zhihu.com/question/{target.get('id', '')}" if target.get('id') else "#"
                    })
                return {'success': True, 'data': result, 'source': 'api'}
    except Exception:
        pass
    return {'success': False, 'error': '获取数据失败'}

# ============== 主程序 ==============

@require_auth
def main():
    # 检查是否需要跳转到超级写手页面（由撰写按钮的 on_click 回调设置）
    if st.session_state.get('_goto_auto_write'):
        st.session_state['_goto_auto_write'] = False
        st.switch_page("page/auto_write.py")
        return
    
    # 显示队列操作的提示信息
    if st.session_state.get('_queue_added_success'):
        topic = st.session_state.pop('_queue_added_success')
        st.toast(f"✅ 已加入撰写队列：{topic[:30]}...", icon="📋")
    if st.session_state.get('_queue_added_duplicate'):
        topic = st.session_state.pop('_queue_added_duplicate')
        st.toast(f"⚠️ 该主题已在队列中：{topic[:30]}...", icon="⚠️")
    
    # 自动刷新：每5分钟（300000毫秒）
    count = st_autorefresh(interval=5 * 60 * 1000, key="hotspots_refresh")

    # 页面样式
    st.markdown("""
    <style>
    .hotspot-header {
        text-align: center;
        background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 99%, #fad0c4 100%);
        color: #2c3e50;
        padding: 2.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(255, 154, 158, 0.3);
        position: relative;
    }
    
    .refresh-timer {
        position: absolute;
        top: 1rem;
        right: 1rem;
        background: rgba(255, 255, 255, 0.3);
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        color: #2c3e50;
        backdrop-filter: blur(5px);
        display: flex;
        align-items: center;
        gap: 5px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        z-index: 100;
    }
    
    .refresh-dot {
        width: 8px;
        height: 8px;
        background-color: #2ed573;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(46, 213, 115, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(46, 213, 115, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(46, 213, 115, 0); }
    }

    .hotspot-card {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 0.8rem;
        transition: all 0.3s ease;
        border-left: 4px solid transparent;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .hotspot-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .rank-badge {
        font-size: 1.2rem;
        font-weight: 900;
        width: 40px;
        text-align: center;
        font-style: italic;
    }
    
    .rank-1 { color: #ff4757; }
    .rank-2 { color: #ff6b81; }
    .rank-3 { color: #ffa502; }
    .rank-other { color: #a4b0be; }
    
    .hotspot-content {
        flex: 1;
    }
    
    .hotspot-title {
        font-size: 1.1rem;
        font-weight: bold;
        color: #2f3542;
        margin-bottom: 0.3rem;
    }
    
    .hotspot-meta {
        font-size: 0.85rem;
        color: #747d8c;
    }
    </style>
    """, unsafe_allow_html=True)

    # HTML结构（去掉脚本）
    st.markdown("""
    <div class="hotspot-header">
        <div class="refresh-timer">
            <div class="refresh-dot"></div>
            <span id="refresh-countdown">准备刷新...</span>
        </div>
        <h1>🔥 全网热点追踪</h1>
        <p style="font-size: 1.1rem; margin-top: 0.5rem; opacity: 0.8;">汇聚全网热搜，即时掌握市场动向</p>
    </div>
    """, unsafe_allow_html=True)

    # 使用 components.html 注入 JS
    # 注入 refresh_count 以确保每次自动刷新触发时，iframe 都会被重新加载，从而重置倒计时
    components.html(f"""
    <script>
    (function() {{
        const REFRESH_INTERVAL_SEC = 300; // 5 minutes
        const ELEMENT_ID = 'refresh-countdown';
        // Refresh count from python: {count}
        
        function findElement() {{
            try {{
                return window.parent.document.getElementById(ELEMENT_ID);
            }} catch(e) {{
                return null;
            }}
        }}

        function startTimer() {{
            const display = findElement();
            if (!display) {{
                setTimeout(startTimer, 500);
                return;
            }}
            
            let remaining = REFRESH_INTERVAL_SEC;
            
            const update = () => {{
                // 倒计时结束
                if (remaining < 0) {{
                    display.textContent = "正在刷新...";
                    
                    // 如果卡在"正在刷新..."超过3秒（即 remaining < -3），说明Streamlit的软刷新可能失效或卡顿
                    // 此时强制执行浏览器级刷新作为兜底
                    if (remaining < -3) {{
                         console.log("Force reloading page...");
                         window.parent.location.reload();
                    }}
                    remaining--; // 继续递减以便触发兜底
                    return;
                }}
                
                const m = Math.floor(remaining / 60);
                const s = remaining % 60;
                display.textContent = `刷新倒计时: ${{m}}:${{s.toString().padStart(2, '0')}}`;
                remaining--;
            }};
            
            update();
            setInterval(update, 1000);
        }}

        setTimeout(startTimer, 100);
    }})();
    </script>
    """, height=0)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
        "📰 澎湃热点", "💼 36Kr创投", "🔍 百度热搜", "📱 微博热搜", "🎵 抖音热搜",
        "📕 小红书", "🎬 快手", "📹 B站", "💡 知乎热榜", 
        "📲 今日头条", "🔴 360热搜"
    ])

    with tab1:
        fetch_thepaper_hot()
    
    with tab2:
        fetch_36kr_news()
    
    with tab3:
        fetch_baidu_hot()
        
    with tab4:
        fetch_weibo_hot()
        
    with tab5:
        fetch_douyin_hot()
    
    with tab6:
        fetch_xiaohongshu_hot()
    
    with tab7:
        fetch_kuaishou_hot()
    
    with tab8:
        fetch_bilibili_hot()
    
    with tab9:
        fetch_zhihu_hot()
    
    with tab10:
        fetch_toutiao_hot()
    
    with tab11:
        fetch_360_hot()

def fetch_thepaper_hot():
    """获取澎湃新闻热点"""
    st.markdown("### 澎湃新闻 - 热点要闻")
    
    result = _get_thepaper_data()
    if result['success']:
        hot_news = result['data']
        if hot_news:
            for idx, news in enumerate(hot_news[:20], 1):
                display_thepaper_card(idx, news)
        else:
            st.warning("暂无澎湃热点数据")
    else:
        st.error("获取澎湃热点失败")


def display_thepaper_card(rank, news):
    """显示澎湃新闻热点卡片（带图片）"""
    title = html.escape(news.get('name', '无标题'))
    cont_id = news.get('contId', '')
    article_url = f"https://www.thepaper.cn/newsDetail_forward_{cont_id}" if cont_id else "https://www.thepaper.cn/"
    pub_time = news.get('pubTime', '')
    praise_times = news.get('praiseTimes', '0')
    interaction_num = news.get('interactionNum', '0')
    pic = news.get('smallPic', '') or news.get('pic', '')
    node_name = html.escape(news.get('nodeInfo', {}).get('name', '澎湃新闻'))
    
    # 热度信息
    meta_info = f"👍 {praise_times} · 💬 {interaction_num} · ⏰ {pub_time}"
    
    rank_class = f"rank-{rank}" if rank <= 3 else "rank-other"
    border_color = '#ff4757' if rank <= 3 else '#a4b0be'
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # 带图片的卡片样式
        img_html = ""
        if pic:
            img_html = f'<img src="{html.escape(pic)}" style="width:100px; height:70px; object-fit:cover; border-radius:8px; margin-right:12px; flex-shrink:0;" referrerpolicy="no-referrer" onerror="this.style.display=\'none\'">'
        
        card_html = f'<div class="hotspot-card" style="border-left-color: {border_color}; display:flex; align-items:center;"><div class="rank-badge {rank_class}">{rank}</div>{img_html}<div class="hotspot-content" style="flex:1;"><div class="hotspot-title"><a href="{article_url}" target="_blank" style="text-decoration:none; color: inherit;">{title}</a></div><div class="hotspot-meta" style="margin-top:4px;"><span style="background:#f0f0f0; padding:2px 6px; border-radius:4px; font-size:0.75rem; margin-right:8px;">{node_name}</span>{meta_info}</div></div></div>'
        
        st.markdown(card_html, unsafe_allow_html=True)
    
    with col2:
        # 使用多字段组合生成唯一key
        safe_key = f"thepaper_{rank}_{hash((title, article_url, node_name))}"
        context = f"来源：澎湃新闻热榜第{rank}名\n栏目：{node_name}"
        custom_style = f"请结合当前热点事件「{title}」进行创作。\n{context}"
        
        # 使用 on_click 回调确保状态设置后再跳转
        def go_write_thepaper(t=title, s=custom_style):
            st.session_state['article_topic_prefill'] = t
            st.session_state['custom_style_prefill'] = s
            st.session_state['_goto_auto_write'] = True
        
        # 加入队列的回调
        def add_to_queue_thepaper(t=title, s=custom_style):
            result = add_to_queue(
                topic=t,
                source=SOURCE_HOTSPOTS,
                custom_style=s,
                metadata={'hotspot_source': '澎湃新闻'}
            )
            if result:
                st.session_state['_queue_added_success'] = t
            else:
                st.session_state['_queue_added_duplicate'] = t
        
        st.button("✨ 撰写", key=f"w_{safe_key}", help="跳转到超级写手页面撰写", use_container_width=True, on_click=go_write_thepaper)
        st.button("📋 加入队列", key=f"q_{safe_key}", help="加入撰写队列，稍后自动执行", use_container_width=True, on_click=add_to_queue_thepaper)


def fetch_36kr_news():
    """获取36Kr快讯 (通过今日热榜API)"""
    st.markdown("### 36Kr - 24小时快讯")
    
    result = _get_36kr_data()
    if result['success']:
        for idx, item in enumerate(result['data'], 1):
            display_hotspot_card(
                idx,
                item['title'],
                f"🔥 {item['hot']}" if item['hot'] else "",
                item['url'],
                "36Kr快讯",
                source="36Kr"
            )
    else:
        st.warning("无法解析36Kr数据，请稍后重试")

def fetch_baidu_hot():
    """获取百度热搜"""
    st.markdown("### 百度实时热搜")
    
    result = _get_baidu_data()
    if result['success']:
        for idx, item in enumerate(result['data'], 1):
            display_hotspot_card(
                idx,
                item['title'],
                item['desc'],
                item['url'],
                f"热度指数: {item['hot_score']}",
                source="Baidu"
            )
    else:
        st.warning("未能获取百度热搜数据")

def fetch_weibo_hot():
    """获取微博热搜 (通过HTML解析)"""
    st.markdown("### 微博热搜榜")
    
    result = _get_weibo_data()
    if result['success'] and result['data']:
        for idx, item in enumerate(result['data'], 1):
            heat_display = f"热度: {item['heat']}" if item['heat'] else "置顶/推荐"
            display_hotspot_card(
                idx,
                item['title'],
                heat_display,
                item['url'],
                "微博实时热搜",
                source="Weibo"
            )
    else:
        st.warning("未找到微博热搜数据")

def fetch_douyin_hot():
    """获取抖音热搜"""
    st.markdown("### 抖音热搜榜")
    
    result = _get_douyin_data()
    if result['success'] and result['data']:
        for idx, item in enumerate(result['data'], 1):
            hot_value = item.get('hot_value', 0)
            display_hotspot_card(
                idx,
                item['title'],
                f"热度: {hot_value/10000:.1f}万",
                f"https://www.douyin.com/search/{item['title']}",
                "抖音热搜",
                source="Douyin"
            )
    else:
        st.warning("未找到抖音热搜数据，可能需要更新Cookie")

def fetch_xiaohongshu_hot():
    """获取小红书热搜 - 通过今日热榜"""
    st.markdown("### 小红书热搜榜")
    
    result = _get_tophub_data("L4MdA5ldxD")
    if result['success'] and result['data']:
        for idx, item in enumerate(result['data'][:20], 1):
            display_hotspot_card(
                idx,
                item['title'],
                f"🔥 {item['hot']}" if item['hot'] else "",
                item['url'],
                "小红书热搜",
                source="Xiaohongshu"
            )
    else:
        _show_platform_search_fallback("小红书", "https://www.xiaohongshu.com/explore")

def fetch_kuaishou_hot():
    """获取快手热搜 - 通过今日热榜"""
    st.markdown("### 快手热搜榜")
    
    result = _get_tophub_data("MZd7PrPerO")
    if result['success'] and result['data']:
        for idx, item in enumerate(result['data'][:20], 1):
            search_url = f"https://www.kuaishou.com/search/video?searchKey={item['title']}"
            display_hotspot_card(
                idx,
                item['title'],
                f"🔥 {item['hot']}" if item['hot'] else "",
                search_url,
                "快手热搜",
                source="Kuaishou"
            )
    else:
        _show_platform_search_fallback("快手", "https://www.kuaishou.com/")

def fetch_bilibili_hot():
    """获取B站热门 - 使用官方热门视频API"""
    st.markdown("### B站热门榜")
    
    result = _get_bilibili_data()
    if result['success'] and result['data']:
        if result.get('type') == 'popular':
            for idx, item in enumerate(result['data'], 1):
                item_url = f"https://www.bilibili.com/video/{item['bvid']}" if item['bvid'] else "#"
                display_hotspot_card(
                    idx,
                    item['title'],
                    f"UP: {item['owner']} · {item['tname']} · ▶ {item['view_str']}",
                    item_url,
                    "B站热门视频",
                    source="Bilibili"
                )
        else:  # search type
            st.info("📺 当前显示B站搜索热词")
            for idx, item in enumerate(result['data'], 1):
                display_hotspot_card(
                    idx,
                    item['keyword'],
                    "",
                    item['url'],
                    "B站热搜",
                    source="Bilibili"
                )
    else:
        st.warning("暂无法获取B站数据，请稍后重试")

def fetch_zhihu_hot():
    """获取知乎热榜 - 通过今日热榜"""
    st.markdown("### 知乎热榜")
    
    result = _get_zhihu_data()
    if result['success'] and result['data']:
        for idx, item in enumerate(result['data'], 1):
            hot = item.get('hot', '')
            hot_display = ""
            if hot:
                if "万" in hot:
                    hot_display = f"🔥 {hot}热度"
                else:
                    hot_display = f"🔥 {hot}"
            display_hotspot_card(
                idx,
                item['title'],
                hot_display,
                item['url'],
                "知乎热榜",
                source="Zhihu"
            )
    else:
        _show_platform_search_fallback("知乎", "https://www.zhihu.com/hot")

def fetch_toutiao_hot():
    """获取今日头条热榜 - 通过今日热榜"""
    st.markdown("### 今日头条热榜")
    
    result = _get_tophub_data("x9ozB4KoXb")
    if result['success'] and result['data']:
        for idx, item in enumerate(result['data'], 1):
            display_hotspot_card(
                idx,
                item['title'],
                f"🔥 {item['hot']}" if item['hot'] else "",
                item['url'],
                "今日头条热榜",
                source="Toutiao"
            )
    else:
        _show_platform_search_fallback("今日头条", "https://www.toutiao.com/")

def fetch_360_hot():
    """获取360热搜 - 通过今日热榜"""
    st.markdown("### 360热搜榜")
    
    result = _get_tophub_data("KMZd7x6erO")
    if result['success'] and result['data']:
        for idx, item in enumerate(result['data'], 1):
            search_url = f"https://www.so.com/s?q={item['title']}"
            display_hotspot_card(
                idx,
                item['title'],
                f"🔥 {item['hot']}" if item['hot'] else "",
                search_url,
                "360热搜榜",
                source="360"
            )
    else:
        _show_platform_search_fallback("360搜索", "https://www.so.com/")

def _show_platform_search_fallback(platform_name, search_url):
    """显示平台搜索入口（当API不可用时的备用方案）"""
    st.info(f"""
    📢 **{platform_name}热搜数据暂时无法获取**
    
    您可以直接访问 [{platform_name}]({search_url}) 查看最新热点内容。
    """)
    
    # 提供一些通用热门话题建议
    st.markdown("---")
    st.markdown("**💡 热门话题建议：**")
    
    suggestions = [
        "今日新闻热点",
        "热门娱乐八卦", 
        "科技数码资讯",
        "美食探店分享",
        "旅行攻略推荐"
    ]
    
    cols = st.columns(len(suggestions))
    for i, topic in enumerate(suggestions):
        with cols[i]:
            safe_key = f"{platform_name}_{i}_{hash(topic)}"
            if st.button(f"📝 {topic}", key=f"suggest_{safe_key}", use_container_width=True):
                st.session_state['article_topic_prefill'] = topic
                st.session_state['custom_style_prefill'] = f"请围绕「{topic}」主题，结合{platform_name}平台风格进行创作。"
                st.switch_page("page/auto_write.py")

def display_hotspot_card(rank, title, summary, url, meta, source=""):
    """显示热点卡片"""
    rank_class = f"rank-{rank}" if rank <= 3 else "rank-other"
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown(f"""
        <div class="hotspot-card" style="border-left-color: {'#ff4757' if rank<=3 else '#a4b0be'};">
            <div class="rank-badge {rank_class}">{rank}</div>
            <div class="hotspot-content">
                <div class="hotspot-title">
                    <a href="{url}" target="_blank" style="text-decoration:none; color: inherit;">
                        {title}
                    </a>
                </div>
                <div class="hotspot-meta">{summary}</div>
                <div class="hotspot-meta" style="margin-top:4px; font-size:0.8rem;">{meta}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # 使用source、rank、title和url的hash组合生成唯一key，避免重复标题导致key冲突
        safe_key = f"{source}_{rank}_{hash((title, url, summary))}"
        context = f"来源：{source}热榜第{rank}名\n内容摘要：{summary}"
        custom_style_text = f"请结合当前热点事件「{title}」进行创作。\n{context}"
        
        # 使用 on_click 回调确保状态设置后再跳转
        def go_write(t=title, s=custom_style_text):
            st.session_state['article_topic_prefill'] = t
            st.session_state['custom_style_prefill'] = s
            st.session_state['_goto_auto_write'] = True
        
        # 加入队列的回调
        def add_to_queue_callback(t=title, s=custom_style_text, src=source):
            result = add_to_queue(
                topic=t,
                source=SOURCE_HOTSPOTS,
                custom_style=s,
                metadata={'hotspot_source': src}
            )
            if result:
                st.session_state['_queue_added_success'] = t
            else:
                st.session_state['_queue_added_duplicate'] = t
        
        # 撰写按钮 - 跳转到超级写手页面
        st.button("✨ 撰写", key=f"w_{safe_key}", help="跳转到超级写手页面撰写", use_container_width=True, on_click=go_write)
        # 加入队列按钮 - 直接加入队列不跳转
        st.button("📋 加入队列", key=f"q_{safe_key}", help="加入撰写队列，稍后自动执行", use_container_width=True, on_click=add_to_queue_callback)

if __name__ == "__main__":
    main()
