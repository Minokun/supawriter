import streamlit as st
import requests
import json
import re
from datetime import datetime, timedelta
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.llm_chat import chat
from utils.config_manager import get_config
import utils.prompt_template as pt
from utils.history_utils import (
    add_tweet_topics_record,
    load_tweet_topics_history,
    delete_tweet_topics_record
)
import logging

# 配置日志
logger = logging.getLogger(__name__)

@require_auth
def main():
    # 获取当前用户
    username = get_current_user()
    if not username:
        st.error("无法获取用户信息，请重新登录")
        return
    
    # 页面标题和样式
    st.markdown("""
    <style>
    .topic-header {
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
    
    .topic-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-left: 5px solid #667eea;
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .topic-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.15);
    }
    
    .topic-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    
    .topic-subtitle {
        font-size: 1rem;
        color: #5a6c7d;
        margin-bottom: 1rem;
        font-style: italic;
    }
    
    .topic-meta {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 1rem;
    }
    
    .meta-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .outline-item {
        padding: 0.5rem 0;
        border-bottom: 1px solid #f0f0f0;
    }
    
    .heat-score {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
    }
    
    .score-high {
        color: #e74c3c;
    }
    
    .score-medium {
        color: #f39c12;
    }
    
    .score-low {
        color: #95a5a6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 页面标题
    st.markdown("""
    <div class="topic-header">
        <h1>📝 推文选题生成器</h1>
        <p style="font-size: 1.1rem; margin-top: 0.5rem; opacity: 0.95;">基于热点新闻，智能生成优质公众号推文选题</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 侧边栏：新闻源选择和配置
    with st.sidebar:
        st.markdown("### ⚙️ 配置选项")
        
        # 新闻源选择
        news_source = st.pills(
            "选择新闻源",
            ["机器之心", "SOTA开源项目", "实时新闻"],
            default="机器之心",
            selection_mode="single",
            help="选择要分析的新闻来源"
        )
        
        # 新闻数量
        news_count = st.slider(
            "获取新闻数量",
            min_value=5,
            max_value=30,
            value=15,
            step=5,
            help="获取的新闻条数，越多内容越丰富但处理时间越长"
        )
        
        # 选题数量
        topic_count = st.slider(
            "生成选题数量",
            min_value=3,
            max_value=15,
            value=8,
            step=1,
            help="希望生成的推文选题数量"
        )
    
    # 获取全局模型配置
    config = get_config()
    global_settings = config.get('global_model_settings', {})
    
    # 如果全局设置为空，则使用默认模型
    if not global_settings:
        from settings import LLM_MODEL
        default_provider = list(LLM_MODEL.keys())[0]
        default_model = LLM_MODEL[default_provider]['model'][0] if isinstance(LLM_MODEL[default_provider]['model'], list) else LLM_MODEL[default_provider]['model']
        model_type = default_provider
        model_name = default_model
    else:
        model_type = global_settings.get('provider')
        model_name = global_settings.get('model_name')
    
    # 主要内容区域
    # 显示当前使用的全局模型
    if global_settings:
        st.info(f"📡 当前模型: **{global_settings.get('provider')}/{global_settings.get('model_name')}** | 可在【系统设置】中修改")
    else:
        st.warning("⚠️ 未配置全局模型，将使用默认模型。建议在【系统设置】中配置模型。")
    
    # 创建Tab：生成选题 和 历史记录
    tab1, tab2 = st.tabs(["🚀 生成选题", "📜 历史记录"])
    
    with tab1:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("### 📰 新闻来源")
            st.info(f"当前选择：**{news_source}** | 获取数量：**{news_count}** 条 | 生成选题：**{topic_count}** 个")
        
        with col2:
            generate_button = st.button(
                "🚀 生成选题",
                type="primary",
                use_container_width=True,
                help="点击获取新闻并生成推文选题"
            )
        
        # 处理生成选题逻辑
        if generate_button:
            with st.spinner("🔍 正在获取新闻内容..."):
                # 获取新闻内容
                news_data = fetch_news_by_source(news_source, news_count)
                
                if not news_data:
                    st.error("❌ 未能获取到新闻内容，请检查网络连接或稍后重试")
                    st.stop()
                
                st.success(f"✅ 成功获取 {len(news_data)} 条新闻")
                
                # 显示获取的新闻摘要
                with st.expander("📋 查看获取的新闻内容", expanded=False):
                    for idx, news in enumerate(news_data, 1):
                        st.markdown(f"**{idx}. {news.get('title', '无标题')}**")
                        if news.get('summary'):
                            st.caption(news['summary'][:200] + '...' if len(news.get('summary', '')) > 200 else news.get('summary', ''))
                        st.divider()
            
            # 格式化新闻内容为prompt
            news_content = format_news_for_prompt(news_data)
            
            with st.spinner(f"🤖 正在使用 {model_type}/{model_name} 生成 {topic_count} 个推文选题..."):
                try:
                    # 构建prompt
                    prompt = f"""<news_content>
{news_content}
</news_content>

请基于以上新闻内容，生成 {topic_count} 个优质的公众号推文选题。"""
                    
                    # 调用大模型
                    response = chat(
                        prompt=prompt,
                        system_prompt=pt.TWEET_TOPIC_GENERATOR,
                        model_type=model_type,
                        model_name=model_name
                    )
                    
                    # 解析JSON响应
                    topics_data = parse_llm_response(response)
                    
                    if topics_data and topics_data.get('topics'):
                        st.success(f"✅ 成功生成 {len(topics_data['topics'])} 个推文选题！")
                        
                        # 保存到历史记录
                        try:
                            add_tweet_topics_record(
                                username=username,
                                news_source=news_source,
                                news_count=news_count,
                                topics_data=topics_data,
                                model_type=model_type,
                                model_name=model_name
                            )
                            logger.info(f"已保存推文选题到历史记录")
                        except Exception as e:
                            logger.error(f"保存历史记录失败: {str(e)}")
                        
                        # 显示选题总结
                        if topics_data.get('summary'):
                            st.info(f"📊 **本次选题总结**：{topics_data['summary']}")
                        
                        # 显示热门关键词
                        if topics_data.get('hot_keywords'):
                            keywords_html = " ".join([f"<span class='meta-badge'>#{kw}</span>" 
                                                     for kw in topics_data['hot_keywords']])
                            st.markdown(f"🔥 **热门关键词**：{keywords_html}", unsafe_allow_html=True)
                        
                        st.divider()
                        
                        # 显示每个选题
                        for idx, topic in enumerate(topics_data['topics'], 1):
                            display_topic_card(idx, topic, unique_key_prefix="fresh")
                    else:
                        st.error("❌ 未能成功解析选题结果，请重试")
                        st.code(response, language="text")
                        
                except Exception as e:
                    st.error(f"❌ 生成选题时出错：{str(e)}")
                    logger.error(f"生成选题失败: {str(e)}", exc_info=True)
    
    with tab2:
        display_history_tab(username)


def fetch_news_by_source(source_name, count=15):
    """根据新闻源获取新闻数据"""
    try:
        if source_name == "机器之心":
            return fetch_jiqizhixin_news(count)
        elif source_name == "SOTA开源项目":
            return fetch_sota_projects(count)
        elif source_name == "实时新闻":
            return fetch_chinaz_news(news_type=1, count=count)
        else:
            return []
    except Exception as e:
        logger.error(f"获取新闻失败: {str(e)}")
        return []


def fetch_jiqizhixin_news(count=15):
    """获取机器之心文章"""
    try:
        # 获取昨天和今天的新闻
        yesterday = datetime.now() - timedelta(days=1)
        today = datetime.now()
        
        url = f"https://www.jiqizhixin.com/api/article_library/articles.json?sort=time&page=1&per={count}"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            
            news_list = []
            for article in articles[:count]:
                news_list.append({
                    'title': article.get('title', ''),
                    'summary': article.get('content', ''),
                    'published_at': article.get('publishedAt', ''),
                    'source': '机器之心'
                })
            return news_list
        return []
    except Exception as e:
        logger.error(f"获取机器之心新闻失败: {str(e)}")
        return []


def fetch_sota_projects(count=15):
    """获取SOTA开源项目"""
    try:
        url = f"https://sota.jiqizhixin.com/api/v2/sota/terms?order=generationAt&per={count}&page=1"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            projects = data.get('data', [])
            
            news_list = []
            for project in projects[:count]:
                source = project.get('source', {})
                news_list.append({
                    'title': source.get('name', ''),
                    'summary': source.get('summary', source.get('desc', '')),
                    'published_at': '',
                    'source': 'SOTA开源项目'
                })
            return news_list
        return []
    except Exception as e:
        logger.error(f"获取SOTA项目失败: {str(e)}")
        return []


def fetch_chinaz_news(news_type, count=15):
    """获取站长之家AI新闻"""
    try:
        url = f"https://app.chinaz.com/djflkdsoisknfoklsyhownfrlewfknoiaewf/ai/GetAiInfoList.aspx?flag=zh_cn&type={news_type}&page=1&pagesize={count}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://app.chinaz.com/',
            'Accept': 'application/json, text/plain, */*',
        }
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            news_items = data if isinstance(data, list) else data.get('data', [])
            
            news_list = []
            for item in news_items[:count]:
                news_list.append({
                    'title': clean_html_text(item.get('title', '')),
                    'summary': clean_html_text(item.get('description', item.get('summary', ''))),
                    'published_at': item.get('addtime', ''),
                    'source': item.get('sourcename', '站长之家')
                })
            return news_list
        return []
    except Exception as e:
        logger.error(f"获取站长之家新闻失败: {str(e)}")
        return []


def clean_html_text(text):
    """清理HTML标签和特殊字符"""
    if not text:
        return ''
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', str(text))
    # 解码HTML实体
    import html
    text = html.unescape(text)
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def format_news_for_prompt(news_data):
    """将新闻数据格式化为prompt内容"""
    formatted = []
    for idx, news in enumerate(news_data, 1):
        title = news.get('title', '无标题')
        summary = news.get('summary', '无摘要')
        published_at = news.get('published_at', '')
        source = news.get('source', '')
        
        news_text = f"""【新闻{idx}】
标题：{title}
来源：{source}
时间：{published_at}
内容：{summary}
---"""
        formatted.append(news_text)
    
    return "\n\n".join(formatted)


def parse_llm_response(response):
    """解析大模型返回的JSON响应"""
    try:
        # 尝试直接解析JSON
        data = json.loads(response)
        return data
    except json.JSONDecodeError:
        # 如果直接解析失败，尝试提取JSON部分
        try:
            # 查找JSON代码块
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return data
            
            # 查找大括号包围的JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return data
        except:
            pass
    
    logger.error(f"无法解析LLM响应: {response[:500]}")
    return None


def display_topic_card(index, topic, unique_key_prefix="topic"):
    """显示一个选题卡片"""
    title = topic.get('title', '无标题')
    subtitle = topic.get('subtitle', '')
    angle = topic.get('angle', '')
    target_audience = topic.get('target_audience', '')
    content_outline = topic.get('content_outline', [])
    hook = topic.get('hook', '')
    value_proposition = topic.get('value_proposition', '')
    estimated_words = topic.get('estimated_words', '')
    difficulty = topic.get('difficulty', '')
    heat_score = topic.get('heat_score', 5)
    
    # 热度评分样式
    score_class = 'score-high' if heat_score >= 8 else 'score-medium' if heat_score >= 5 else 'score-low'
    fire_emoji = '🔥' * min(int(heat_score / 2), 5)
    
    st.markdown(f"""
    <div class="topic-card">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div style="flex: 1;">
                <div style="font-size: 1.5rem; color: #667eea; font-weight: bold; margin-bottom: 0.3rem;">
                    #{index}
                </div>
                <div class="topic-title">{title}</div>
                {f'<div class="topic-subtitle">{subtitle}</div>' if subtitle else ''}
            </div>
            <div class="heat-score {score_class}" style="font-size: 1.2rem; font-weight: bold;">
                {fire_emoji} {heat_score}/10
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 元信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**📐 切入角度**")
        st.info(angle if angle else "未指定")
    with col2:
        st.markdown(f"**👥 目标读者**")
        st.info(target_audience if target_audience else "未指定")
    with col3:
        st.markdown(f"**📝 创作难度**")
        difficulty_color = "🟢" if difficulty == "简单" else "🟡" if difficulty == "中等" else "🔴"
        st.info(f"{difficulty_color} {difficulty}" if difficulty else "未指定")
    
    # 内容详情
    with st.expander("📋 查看详细内容", expanded=False):
        if hook:
            st.markdown(f"**🎣 开篇钩子**")
            st.success(hook)
        
        if value_proposition:
            st.markdown(f"**💎 价值主张**")
            st.info(value_proposition)
        
        if content_outline:
            st.markdown(f"**📑 内容大纲**")
            if isinstance(content_outline, list):
                for i, point in enumerate(content_outline, 1):
                    st.markdown(f"{i}. {point}")
            else:
                st.write(content_outline)
        
        if estimated_words:
            st.markdown(f"**📏 预计字数**：{estimated_words}")
    
    # 生成文章按钮
    if st.button("✨ 生成文章", key=f"gen_btn_{unique_key_prefix}_{index}", use_container_width=True):
        # 准备预填数据
        style_parts = []
        if angle: style_parts.append(f"切入角度：{angle}")
        if target_audience: style_parts.append(f"目标读者：{target_audience}")
        if hook: style_parts.append(f"开篇钩子：{hook}")
        if value_proposition: style_parts.append(f"价值主张：{value_proposition}")
        
        style_prompt = "\n".join(style_parts)
        
        # 设置Session State
        st.session_state['article_topic'] = title
        st.session_state['custom_style'] = style_prompt
        
        # 跳转页面
        st.switch_page("page/auto_write.py")
    
    st.divider()


def display_history_tab(username):
    """显示历史记录Tab"""
    st.markdown("### 📜 历史记录")
    
    # 加载历史记录
    history = load_tweet_topics_history(username)
    
    if not history:
        st.info("暂无历史记录。生成推文选题后会自动保存到这里。")
        return
    
    # 按时间倒序排列
    history_sorted = sorted(history, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    st.info(f"共有 **{len(history_sorted)}** 条历史记录")
    
    # 显示每条历史记录
    for record in history_sorted:
        record_id = record.get('id')
        timestamp = record.get('timestamp', '')
        news_source = record.get('news_source', '')
        news_count = record.get('news_count', 0)
        model_type = record.get('model_type', '')
        model_name = record.get('model_name', '')
        topics_data = record.get('topics_data', {})
        
        # 格式化时间
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            time_str = timestamp
        
        # 创建可展开的历史记录卡片
        with st.expander(f"🕐 {time_str} | 📰 {news_source} ({news_count}条) | 🤖 {model_type}/{model_name}", expanded=False):
            # 显示元信息
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("新闻来源", news_source)
            with col2:
                st.metric("新闻数量", f"{news_count}条")
            with col3:
                st.metric("选题数量", f"{len(topics_data.get('topics', []))}个")
            with col4:
                # 删除按钮
                if st.button("🗑️ 删除", key=f"delete_{record_id}", type="secondary"):
                    try:
                        delete_tweet_topics_record(username, record_id)
                        st.success("已删除该记录")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败：{str(e)}")
            
            # 显示选题总结
            if topics_data.get('summary'):
                st.info(f"📊 **选题总结**：{topics_data['summary']}")
            
            # 显示热门关键词
            if topics_data.get('hot_keywords'):
                keywords_html = " ".join([f"<span class='meta-badge'>#{kw}</span>" 
                                         for kw in topics_data['hot_keywords']])
                st.markdown(f"🔥 **热门关键词**：{keywords_html}", unsafe_allow_html=True)
            
            st.divider()
            
            # 显示所有选题
            topics = topics_data.get('topics', [])
            if topics:
                st.markdown(f"**共 {len(topics)} 个选题：**")
                for idx, topic in enumerate(topics, 1):
                    display_topic_card(idx, topic, unique_key_prefix=f"hist_{record_id}")
            else:
                st.warning("该记录中没有选题数据")


if __name__ == "__main__":
    main()
