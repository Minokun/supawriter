import streamlit as st
import requests
import re
import json
from datetime import datetime
from utils.auth_decorator import require_auth
import html
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

@require_auth
def main():
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

    tab1, tab2, tab3, tab4 = st.tabs(["💼 36Kr创投", "🔍 百度热搜", "📱 微博热搜", "🎵 抖音热搜"])

    with tab1:
        fetch_36kr_news()
    
    with tab2:
        fetch_baidu_hot()
        
    with tab3:
        fetch_weibo_hot()
        
    with tab4:
        fetch_douyin_hot()

def fetch_36kr_news():
    """获取36Kr快讯 (通过HTML解析或RSS)"""
    st.markdown("### 36Kr - 24小时快讯")
    
    try:
        # 尝试直接请求HTML页面
        url = "https://36kr.com/newsflashes"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # 1. 尝试解析 window.initialState
            # 寻找 window.initialState = {...}
            state_match = re.search(r'window\.initialState\s*=\s*({.*?});', response.text, re.DOTALL)
            
            if state_match:
                try:
                    state_json = json.loads(state_match.group(1))
                    # 路径可能变化，通常在 newsflashCatalogData -> data -> itemList
                    # 或者 newsflashList -> flow
                    news_list = []
                    
                    # 尝试从可能的路径中查找
                    if 'newsflashCatalogData' in state_json and 'data' in state_json['newsflashCatalogData']:
                        news_list = state_json['newsflashCatalogData']['data'].get('itemList', [])
                    elif 'newsflashList' in state_json:
                        news_list = state_json['newsflashList'].get('flow', {}).get('itemList', [])
                        
                    if news_list:
                        for idx, item in enumerate(news_list, 1):
                            template = item.get('templateMaterial', {})
                            title = template.get('widgetTitle', '')
                            summary = template.get('widgetContent', '')
                            item_id = item.get('itemId')
                            item_url = f"https://36kr.com/newsflashes/{item_id}" if item_id else "https://36kr.com/newsflashes"
                            
                            display_hotspot_card(
                                idx,
                                title,
                                summary,
                                item_url,
                                "36Kr快讯",
                                source="36Kr"
                            )
                        return # 成功解析则返回
                except Exception as e:
                    pass # 解析失败继续尝试其他方法
            
            # 2. 如果JSON解析失败，尝试正则匹配HTML
            # <a class="item-title" ...>Title</a>
            # <div class="item-desc" ...>Desc</div>
            titles = re.findall(r'<a[^>]+class="item-title"[^>]*>(.*?)</a>', response.text)
            descs = re.findall(r'<div[^>]+class="item-desc"[^>]*>(.*?)</div>', response.text)
            
            # 匹配itemId用于链接
            # href="/newsflashes/252000..."
            links = re.findall(r'href="/newsflashes/(\d+)"', response.text)
            
            if titles:
                count = min(len(titles), len(descs))
                for i in range(count):
                    title = html.unescape(titles[i].strip())
                    desc = html.unescape(descs[i].strip())
                    item_id = links[i] if i < len(links) else ""
                    item_url = f"https://36kr.com/newsflashes/{item_id}" if item_id else "https://36kr.com/newsflashes"
                    
                    display_hotspot_card(
                        i+1,
                        title,
                        desc,
                        item_url,
                        "36Kr快讯",
                        source="36Kr"
                    )
                return

        st.warning("无法解析36Kr数据，请稍后重试")
            
    except Exception as e:
        st.error(f"获取36Kr数据失败: {str(e)}")

def fetch_baidu_hot():
    """获取百度热搜"""
    st.markdown("### 百度实时热搜")
    
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        # 尝试解析JSON数据
        # <!--s-data:{"data":{...}}-->
        json_match = re.search(r'<!--s-data:({.*?})-->', response.text)
        
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                cards = data.get('data', {}).get('cards', [])
                if cards:
                    # 通常第一个card是热搜榜
                    content = cards[0].get('content', [])
                    for idx, item in enumerate(content, 1):
                        title = item.get('word', '')
                        desc = item.get('desc', '')
                        url = item.get('url', '') or f"https://www.baidu.com/s?wd={title}"
                        hot_score = item.get('hotScore', '')
                        
                        display_hotspot_card(
                            idx,
                            title,
                            desc,
                            url,
                            f"热度指数: {hot_score}",
                            source="Baidu"
                        )
                    return
            except:
                pass

        # 降级使用正则匹配HTML
        titles = re.findall(r'<div class="c-single-text-ellipsis">\s*(.*?)\s*</div>', response.text)
        # 过滤非热搜项
        valid_titles = [t.strip() for t in titles if t.strip() and "热搜" not in t][:30]
        
        if valid_titles:
            for idx, title in enumerate(valid_titles, 1):
                title = html.unescape(title)
                display_hotspot_card(
                    idx, title, "", f"https://www.baidu.com/s?wd={title}", "百度热搜", source="Baidu"
                )
        else:
            st.warning("未能获取百度热搜数据")
            
    except Exception as e:
        st.error(f"获取百度热搜失败: {str(e)}")

def fetch_weibo_hot():
    """获取微博热搜 (通过HTML解析)"""
    st.markdown("### 微博热搜榜")
    
    try:
        # 使用不需要登录的HTML页面
        url = "https://s.weibo.com/top/summary"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Cookie': 'SUB=_2AkMWJ_fdf8NxqwJRmP8SxWjnaY12yQ_EieKkjrMJJRMxHRl-yT9jqmgbtRB6PO6Nc9vS-pTH2Q7q8lW1D4q4e6P4' # 尝试使用访客Cookie
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # 解析表格行
            # <td class="td-01 ranktop">1</td>
            # <td class="td-02"><a href="/weibo?q=...">标题</a><span>热度</span></td>
            
            # 使用findall查找所有行
            # 每一行包含rank, link, title, heat
            # 注意：置顶热搜可能没有rank或者rank是icon
            
            # 匹配 rank
            # 匹配内容
            
            # 这里简化处理，直接找所有含有 href="/weibo?q=" 的链接
            # 优化正则：
            # 1. 允许 span 带属性
            # 2. 允许 span 内容不仅仅是数字 (虽然通常是数字)
            # 3. 使用 re.DOTALL (re.S) 确保跨行匹配
            items = re.findall(r'<a href="(/weibo\?q=[^"]+)"[^>]*>(.*?)</a>.*?<span[^>]*>(.*?)</span>', response.text, re.DOTALL)
            
            # 如果上面的没匹配到（比如置顶没有span或者格式不同），尝试宽松匹配
            if not items:
                 items = re.findall(r'<a href="(/weibo\?q=[^"]+)"[^>]*>(.*?)</a>', response.text)
                 # 补全格式
                 items = [(x[0], x[1], "") for x in items]
            
            # 过滤掉"剧集影响力榜"等导航链接 (通常不带热度或者特定关键词)
            # 真正热搜通常带有热度数字，或者是在特定区域
            
            hot_list = []
            for link, title, heat in items:
                title = html.unescape(title).strip()
                heat = heat.strip()
                
                # 排除导航项
                if title in ['首页', '发现', '游戏', '注册', '登录', '帮助', '剧集影响力榜', '综艺影响力榜', '更多']:
                    continue
                
                # 修正链接
                full_url = f"https://s.weibo.com{link}"
                hot_list.append({
                    'title': title,
                    'url': full_url,
                    'heat': heat
                })
            
            if hot_list:
                # 微博置顶项通常在第一个但没有热度，后续有热度
                # 简单去重
                seen_titles = set()
                unique_list = []
                for item in hot_list:
                    if item['title'] not in seen_titles:
                        seen_titles.add(item['title'])
                        unique_list.append(item)
                
                for idx, item in enumerate(unique_list[:30], 1):
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
        else:
            st.error(f"访问微博受限 (Status: {response.status_code})")
            
    except Exception as e:
        st.error(f"获取微博热搜失败: {str(e)}")

def fetch_douyin_hot():
    """获取抖音热搜"""
    st.markdown("### 抖音热搜榜")
    
    try:
        url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.douyin.com/billboard/',
            # 抖音可能需要Cookie才能返回数据，如果为空可能返回空列表
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            word_list = data.get('data', {}).get('word_list', [])
            
            if word_list:
                for idx, item in enumerate(word_list, 1):
                    title = item.get('word', '')
                    hot_value = item.get('hot_value', 0)
                    # 抖音链接
                    url = f"https://www.douyin.com/search/{title}"
                    
                    display_hotspot_card(
                        idx,
                        title,
                        f"热度: {hot_value/10000:.1f}万",
                        url,
                        "抖音热搜",
                        source="Douyin"
                    )
            else:
                st.warning("未找到抖音热搜数据，可能需要更新Cookie")
        else:
            st.error(f"获取抖音数据失败: {response.status_code}")
            
    except Exception as e:
        st.error(f"获取抖音热搜失败: {str(e)}")

def display_hotspot_card(rank, title, summary, url, meta, source=""):
    """显示热点卡片"""
    rank_class = f"rank-{rank}" if rank <= 3 else "rank-other"
    
    col1, col2 = st.columns([5, 1])
    
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
        # 垂直居中按钮
        st.space("medium")
        # 使用source和title生成更唯一的key
        safe_key = f"{source}_{rank}_{hash(title)}"
        if st.button("✨ 写文章", key=safe_key, use_container_width=True):
            # 设置Session State并跳转
            st.session_state['article_topic'] = title
            # 附带一些上下文信息到custom_style
            context = f"来源：{source}热榜第{rank}名\n内容摘要：{summary}"
            st.session_state['custom_style'] = f"请结合当前热点事件「{title}」进行创作。\n{context}"
            st.switch_page("page/auto_write.py")

if __name__ == "__main__":
    main()
