import streamlit as st
import sys
import logging
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import load_user_history, save_html_to_user_dir, sanitize_filename
from utils.playwright_utils import take_webpage_screenshot_sync
from utils.wechat_converter import markdown_to_wechat_html
from settings import ARTICLE_TRANSFORMATIONS, HISTORY_FILTER_BASE_OPTIONS, HTML_NGINX_BASE_URL
import markdown
import os
import time
from urllib.parse import quote
import re
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('history')

def _fix_bento_html_aos(html: str) -> str:
    """
    Fix AOS (Animate On Scroll) initialization issues in Bento HTML.
    AOS hides elements by default, causing blank pages if not properly initialized.
    """
    if not html or not isinstance(html, str):
        return html
    
    # Only process if AOS is used
    if 'aos.js' not in html.lower() and 'data-aos' not in html.lower():
        return html
    
    # Remove any existing inline AOS.init() calls that might execute too early
    html = re.sub(r'AOS\.init\s*\([^)]*\)\s*;?', '', html, flags=re.IGNORECASE)
    
    # Inject robust initialization script
    init_script = """
    <script>
        // Critical AOS initialization - must run after library loads
        window.addEventListener('load', function() {
            if (typeof AOS !== 'undefined') {
                try {
                    AOS.init({
                        duration: 800,
                        easing: 'ease-out-cubic',
                        once: true,
                        offset: 50,
                        disable: false
                    });
                    console.log('AOS initialized successfully');
                } catch (e) {
                    console.error('AOS init failed:', e);
                    // Fallback: remove data-aos to make content visible
                    document.querySelectorAll('[data-aos]').forEach(el => {
                        el.removeAttribute('data-aos');
                        el.style.opacity = '1';
                        el.style.transform = 'none';
                    });
                }
            } else {
                console.warn('AOS library not loaded, removing animations');
                // Fallback: remove data-aos to make content visible
                document.querySelectorAll('[data-aos]').forEach(el => {
                    el.removeAttribute('data-aos');
                    el.style.opacity = '1';
                    el.style.transform = 'none';
                });
            }
        });
        // Emergency fallback if load event already fired
        if (document.readyState === 'complete') {
            setTimeout(function() {
                if (!window.AOS || !AOS.init) {
                    document.querySelectorAll('[data-aos]').forEach(el => {
                        el.removeAttribute('data-aos');
                        el.style.opacity = '1';
                        el.style.transform = 'none';
                    });
                }
            }, 1000);
        }
    </script>
    """
    if '</body>' in html:
        html = html.replace('</body>', f"{init_script}</body>")
    else:
        html += init_script
    
    return html

@st.dialog("公众号预览", width="large")
def preview_wechat_article(markdown_content):
    """
    Show a modal dialog with the WeChat-formatted article preview.
    """
    if not markdown_content:
        st.warning("文章内容为空")
        return
        
    # Convert Markdown to WeChat HTML
    html_content = markdown_to_wechat_html(markdown_content)
    
    st.caption("💡 提示：内容已转换为微信公众号格式。点击右下角的“一键复制”按钮，即可粘贴到微信编辑器。")
    
    # Inject Copy Button and JS
    html_with_script = f"""
    {html_content}
    <style>
        .copy-btn-container {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
        }}
        .copy-btn {{
            background-color: #07c160;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }}
        .copy-btn:hover {{
            background-color: #06ad56;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.2);
        }}
        .copy-btn:active {{
            transform: translateY(0);
        }}
        .toast {{
            visibility: hidden;
            min-width: 200px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 4px;
            padding: 12px;
            position: fixed;
            z-index: 1001;
            left: 50%;
            bottom: 70px;
            transform: translateX(-50%);
            font-size: 14px;
            opacity: 0;
            transition: opacity 0.3s, bottom 0.3s;
        }}
        .toast.show {{
            visibility: visible;
            opacity: 1;
            bottom: 80px;
        }}
    </style>
    
    <div class="copy-btn-container">
        <button class="copy-btn" onclick="copyToWeChat()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            一键复制
        </button>
    </div>
    <div id="toast" class="toast">✅ 已复制！请直接粘贴到微信编辑器</div>
    
    <script>
    function copyToWeChat() {{
        const content = document.getElementById('wechat-content');
        
        // Select the content
        const range = document.createRange();
        range.selectNode(content);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        
        try {{
            // Execute copy command
            const successful = document.execCommand('copy');
            
            // Show toast
            const toast = document.getElementById("toast");
            toast.className = "toast show";
            setTimeout(function(){{ toast.className = toast.className.replace("show", ""); }}, 3000);
            
        }} catch (err) {{
            console.error('Oops, unable to copy', err);
            alert('复制失败，请手动全选复制');
        }}
        
        // Clear selection
        selection.removeAllRanges();
    }}
    </script>
    """
    
    # Preview container
    # We use a container with height to simulate mobile view scrolling
    st.components.v1.html(html_with_script, height=600, scrolling=True)


@st.dialog("markdown格式预览", width="large")
def preview_markdown_article(markdown_content):
    """
    Show a modal dialog with the standard Markdown rendered preview.
    """
    if not markdown_content:
        st.warning("文章内容为空")
        return
        
    # Convert Markdown to HTML (Standard/GitHub style)
    html_body = markdown.markdown(
        markdown_content, 
        extensions=['fenced_code', 'tables', 'nl2br', 'sane_lists']
    )
    
    # Escape the markdown content for embedding in JavaScript
    escaped_markdown = json.dumps(markdown_content)
    
    # Define clean styles (GitHub-like)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #24292e;
                padding: 20px;
                max-width: 100%;
                margin: 0 auto;
                background-color: #ffffff;
            }}
            h1, h2, h3, h4, h5, h6 {{ margin-top: 24px; margin-bottom: 16px; font-weight: 600; line-height: 1.25; color: #24292e; }}
            h1 {{ font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
            h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
            p {{ margin-top: 0; margin-bottom: 16px; }}
            code {{ background-color: rgba(27,31,35,0.05); border-radius: 3px; padding: 0.2em 0.4em; font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace; font-size: 85%; }}
            pre {{ background-color: #f6f8fa; border-radius: 3px; padding: 16px; overflow: auto; }}
            pre code {{ background-color: transparent; padding: 0; }}
            blockquote {{ border-left: 0.25em solid #dfe2e5; color: #6a737d; padding: 0 1em; margin: 0; }}
            table {{ border-collapse: collapse; border-spacing: 0; width: 100%; margin-bottom: 16px; }}
            table th, table td {{ padding: 6px 13px; border: 1px solid #dfe2e5; }}
            table th {{ font-weight: 600; background-color: #f6f8fa; }}
            table tr:nth-child(2n) {{ background-color: #f6f8fa; }}
            img {{ max-width: 100%; box-sizing: content-box; background-color: #fff; display: block; margin: 0 auto; }}
            
            /* Copy Button Styles */
            .copy-btn-container {{
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1000;
            }}
            .copy-btn {{
                background-color: #0969da;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-weight: 500;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                display: flex;
                align-items: center;
                gap: 6px;
                transition: all 0.2s;
            }}
            .copy-btn:hover {{
                background-color: #0356b7;
                transform: translateY(-1px);
                box-shadow: 0 6px 16px rgba(0,0,0,0.2);
            }}
            .copy-btn:active {{
                transform: translateY(0);
            }}
            .toast {{
                visibility: hidden;
                min-width: 200px;
                background-color: #333;
                color: #fff;
                text-align: center;
                border-radius: 4px;
                padding: 12px;
                position: fixed;
                z-index: 1001;
                left: 50%;
                bottom: 70px;
                transform: translateX(-50%);
                font-size: 14px;
                opacity: 0;
                transition: opacity 0.3s, bottom 0.3s;
            }}
            .toast.show {{
                visibility: visible;
                opacity: 1;
                bottom: 80px;
            }}
        </style>
    </head>
    <body>
        <div id="content">
            {html_body}
        </div>
        
        <div class="copy-btn-container">
            <button class="copy-btn" onclick="copyMarkdown()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                一键复制
            </button>
        </div>
        <div id="toast" class="toast">✅ 已复制Markdown原文！</div>
        
        <script>
        // Store the original markdown content
        const markdownContent = {escaped_markdown};
        
        function copyMarkdown() {{
            // Use modern Clipboard API to copy the original markdown text
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(markdownContent).then(function() {{
                    const toast = document.getElementById("toast");
                    toast.className = "toast show";
                    setTimeout(function(){{ toast.className = toast.className.replace("show", ""); }}, 3000);
                }}).catch(function(err) {{
                    console.error('Clipboard API failed:', err);
                    fallbackCopy();
                }});
            }} else {{
                fallbackCopy();
            }}
        }}
        
        function fallbackCopy() {{
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = markdownContent;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {{
                document.execCommand('copy');
                const toast = document.getElementById("toast");
                toast.className = "toast show";
                setTimeout(function(){{ toast.className = toast.className.replace("show", ""); }}, 3000);
            }} catch (err) {{
                console.error('Unable to copy', err);
                alert('复制失败');
            }}
            document.body.removeChild(textarea);
        }}
        </script>
    </body>
    </html>
    """
    
    st.components.v1.html(html_content, height=600, scrolling=True)


@require_auth
def main():
    # 自定义CSS样式
    st.markdown("""
    <style>
    /* 主标题样式 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(120deg, #f093fb 0%, #f5576c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    /* 统计卡片 */
    .history-stat-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 16px rgba(240, 147, 251, 0.3);
        transition: transform 0.2s;
    }
    
    .history-stat-card:hover {
        transform: translateY(-4px);
    }
    
    .history-stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    
    .history-stat-label {
        font-size: 1rem;
        opacity: 0.95;
        margin-top: 0.5rem;
        font-weight: 500;
    }
    
    /* 文章卡片 */
    .article-card {
        background: white;
        border-radius: 12px;
        padding: 0;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        margin-bottom: 1.2rem;
        border: 1px solid #f0f0f0;
        overflow: hidden;
        transition: all 0.3s;
    }
    
    .article-card:hover {
        box-shadow: 0 4px 20px rgba(0,0,0,0.12);
        transform: translateY(-2px);
    }
    
    /* 过滤器标签 */
    .filter-tag {
        display: inline-block;
        padding: 0.4rem 1rem;
        margin: 0.2rem;
        border-radius: 20px;
        background: #f0f7ff;
        color: #1e40af;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        border: 2px solid transparent;
    }
    
    .filter-tag:hover {
        background: #dbeafe;
        border-color: #3b82f6;
    }
    
    .filter-tag.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* 提示框 */
    .info-banner {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-left: 4px solid #667eea;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 1.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 页面标题
    st.markdown('<h1 class="main-title">📚 文章历史记录</h1>', unsafe_allow_html=True)
    st.markdown("**管理您的所有创作内容，随时查看、编辑和分享**")
    st.divider()
    
    # Get current user
    current_user = get_current_user()
    if not current_user:
        st.error("🔒 无法获取当前用户信息")
        return
    
    # Load user history
    history = load_user_history(current_user)
    
    if not history:
        st.markdown("""
        <div class="info-banner">
            <h3 style="margin:0;">📝 暂无历史记录</h3>
            <p style="margin:0.5rem 0 0 0;">开始您的创作之旅，前往内容创作页面生成第一篇文章！</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 显示统计信息
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="history-stat-card">
            <div class="history-stat-number">{len(history)}</div>
            <div class="history-stat-label">📄 总文章数</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        original_count = len([r for r in history if not r.get('is_transformed', False)])
        st.markdown(f"""
        <div class="history-stat-card">
            <div class="history-stat-number">{original_count}</div>
            <div class="history-stat-label">✨ 原创文章</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        transformed_count = len([r for r in history if r.get('is_transformed', False)])
        st.markdown(f"""
        <div class="history-stat-card">
            <div class="history-stat-number">{transformed_count}</div>
            <div class="history-stat-label">🔄 转换版本</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        total_words = sum(len(r.get('article_content', '')) for r in history)
        st.markdown(f"""
        <div class="history-stat-card">
            <div class="history-stat-number">{total_words:,}</div>
            <div class="history-stat-label">📊 总字数</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 提示用户可以在社区管理页面同步文章
    st.markdown("""
    <div class="info-banner">
        💡 <strong>提示：</strong>可以前往 <strong>社区管理</strong> 页面将本地文章一键发布到PostgreSQL数据库
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    # ==================== 历史记录显示 ====================

    # Dynamically create history filter options
    transformation_type_names = list(ARTICLE_TRANSFORMATIONS.keys())
    dynamic_filter_options = HISTORY_FILTER_BASE_OPTIONS + transformation_type_names

    # 使用标签页代替单选按钮，更现代化
    st.markdown("### 🔍 筛选文章类型")
    history_filter = st.radio(
        "选择查看的文章类型", 
        dynamic_filter_options, 
        horizontal=True,
        key='history_filter_type',
        label_visibility="collapsed"
    )
    
    # Filter history based on selection
    filtered_history = []
    if history_filter == "所有文章":
        filtered_history = history
    elif history_filter == "完成文章":
        filtered_history = [r for r in history if not r.get('is_transformed', False)]
    elif history_filter in transformation_type_names: # Check if it's one of the transformation types
        # Filter for transformed articles that match the selected transformation type by checking the topic suffix
        filtered_history = [r for r in history if r.get('is_transformed', False) and r.get('topic', '').endswith(f" ({history_filter})")]
    else: # Should not happen with current setup, but as a fallback
        filtered_history = history

    if not filtered_history:
        st.markdown(f"""
        <div class="info-banner">
            <h4 style="margin:0;">🔍 暂无 {history_filter} 类型的历史记录</h4>
            <p style="margin:0.5rem 0 0 0;">尝试选择其他类型查看更多内容</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown(f"**共找到 {len(filtered_history)} 篇文章**")
    st.markdown("<br>", unsafe_allow_html=True)

    # Display history in reverse chronological order (newest first)
    for idx, record in enumerate(reversed(filtered_history), 1):
        # 为每篇文章创建视觉分隔
        article_icon = "🎨" if record.get('is_transformed') else "📝"
        timestamp_display = record['timestamp'][:16].replace('T', ' ')
        
        with st.expander(f"{article_icon} **{record['topic']}** · {timestamp_display}", expanded=(idx == 1)):
            # 文章元数据区域 - 使用标签样式
            st.markdown("##### 📋 文章信息")
            
            meta_cols = st.columns([1, 1, 1])
            with meta_cols[0]:
                st.markdown(f"""
                **🤖 AI模型**  
                `{record.get('model_type', '-')}` / `{record.get('model_name', '-')}`
                """)
            with meta_cols[1]:
                st.markdown(f"""
                **✍️ 创作信息**  
                模式: `{record.get('write_type', '-')}`  
                风格: `{record.get('custom_style', '-')}`
                """)
            with meta_cols[2]:
                st.markdown(f"""
                **📊 统计**  
                字数: `{len(record.get('article_content', ''))}` 字  
                ID: `{record.get('id', '-')}`
                """)
            
            # 显示文章标签和原始主题（如果存在）
            if record.get('tags') or record.get('article_topic'):
                st.divider()
                if record.get('tags'):
                    tags = record.get('tags', '').split(',')
                    tag_html = ' '.join([f'<span style="display:inline-block;background:#e0e7ff;color:#4338ca;padding:0.2rem 0.8rem;border-radius:12px;margin:0.2rem;font-size:0.85rem;">🏷️ {tag.strip()}</span>' for tag in tags if tag.strip()])
                    st.markdown(tag_html, unsafe_allow_html=True)
                    
                if record.get('article_topic'):
                    st.markdown(f"**💡 原始主题:** {record.get('article_topic', '-')}")
            
            if record.get('is_transformed') and record.get('original_article_id') is not None:
                st.info(f"🔄 此文章由源文章 ID: `{record.get('original_article_id')}` 转换而来")
            
            st.divider()
                
            # 判断内容是Markdown还是HTML
            content = record["article_content"].strip()
            is_html = content.startswith('<') and content.endswith('>')
            topic_indicates_html = any(keyword in record.get('topic', '').lower() for keyword in ['bento', '网页', 'html', 'web'])

            # 检查是否有编辑过的内容
            has_been_edited = 'edited_at' in record
            if has_been_edited:
                edited_time = record['edited_at'][:16].replace('T', ' ')
                st.info(f"⚠️ 此文章已于 {edited_time} 编辑过")

            if is_html or topic_indicates_html:
                # 对于HTML内容，不直接显示，而是提供预览链接
                is_bento = "Bento" in record.get('topic', '') or "网页" in record.get('topic', '')
                
                # 美化提示信息
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%); 
                     border-left: 4px solid #667eea; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <strong>🌐 {'Bento风格网页' if is_bento else 'HTML网页'}</strong><br>
                    <span style="font-size: 0.9rem; opacity: 0.8;">点击下方按钮预览或下载网页</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 获取HTML内容
                html_content = record["article_content"]
                
                # 确保内容是完整的HTML文档
                if not html_content.strip().startswith('<!DOCTYPE html>') and not html_content.strip().startswith('<html'):
                    # 如果不是完整的HTML文档，添加必要的HTML标签
                    wrapped_content = f"""<!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>{record.get('topic', '无标题')}</title>
                    </head>
                    <body>
                    {html_content}
                    </body>
                    </html>"""
                    html_content = wrapped_content
                
                # 对Bento风格网页应用AOS修复，确保内容可见
                if is_bento and ('aos.js' in html_content.lower() or 'data-aos' in html_content.lower()):
                    html_content = _fix_bento_html_aos(html_content)
                    logger.info(f"已对Bento HTML应用AOS修复: {record['id']}")
                
                # 生成唯一文件名并进行清洗，避免非法字符或路径分隔符
                raw_filename = f"{record.get('topic', 'article').replace(' ', '_')}_{record['id']}.html"
                html_filename = sanitize_filename(raw_filename)
                
                # 检查文件是否已经存在
                user_html_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'html', current_user)
                file_path = os.path.join(user_html_dir, html_filename)
                
                # 检查文件是否需要（重新）保存
                # 文件不存在、文件为空、或者是Bento页面（可能需要应用修复）时都需要保存
                file_needs_save = not os.path.exists(file_path) or os.path.getsize(file_path) < 100 or (is_bento and 'aos.js' in html_content.lower())
                
                if file_needs_save:
                    _, url_path = save_html_to_user_dir(current_user, html_content, html_filename)
                    logger.info(f"已{'重新' if os.path.exists(file_path) else ''}保存HTML文件: {html_filename}")
                else:
                    # 如果文件已存在且有内容，只生成URL路径
                    url_path = f"{current_user}/{html_filename}"
                
                # 生成可访问的URL（对路径进行URL编码，避免%等特殊字符导致的Nginx访问问题）
                base_url = HTML_NGINX_BASE_URL  # 根据nginx配置调整
                safe_url_path = f"{quote(current_user)}/{quote(html_filename)}"
                article_url = f"{base_url}{safe_url_path}"
                
                # 创建四列布局，分别放置预览链接、下载按钮、截图按钮和删除按钮
                st.markdown("##### 🎯 操作选项")
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                
                with col1:
                    # 使用Streamlit的按钮来打开预览链接
                    # 使用原生链接按钮，避免在受限iframe中注入JS导致无效点击
                    st.link_button(
                        label="👁️ 预览网页",
                        url=article_url,
                        use_container_width=True,
                        type="primary",
                        help="在新标签页打开预览"
                    )
                
                with col2:
                    # 下载按钮
                    st.download_button(
                        label="📥 下载网页",
                        data=record["article_content"],
                        file_name=f"{record['topic']}.html",
                        mime="text/html",
                        key=f"download_html_{record['id']}",
                        use_container_width=True,
                        type="secondary"
                    )
                with col3:
                    # 截图按钮 - 仅对Bento风格网页显示
                    if "Bento" in record.get('topic', '') or "网页" in record.get('topic', ''):
                        screenshot_button = st.button("📸 截图下载", key=f"screenshot_{record['id']}", type="secondary", use_container_width=True)
                        if screenshot_button:
                            try:
                                # 显示加载状态
                                with st.spinner("正在生成网页截图..."):
                                    # 生成截图文件名
                                    screenshot_filename = f"{record.get('topic', 'article').replace(' ', '_')}_{record['id']}_screenshot.png"
                                    
                                    # 调用Playwright截图函数
                                    _, screenshot_url_path = take_webpage_screenshot_sync(
                                        article_url, 
                                        current_user, 
                                        filename=screenshot_filename,
                                        full_page=True
                                    )
                                    
                                    # 构建完整的截图URL
                                    screenshot_full_url = f"{HTML_NGINX_BASE_URL}{screenshot_url_path}"
                                    
                                    # 显示成功消息和截图预览
                                    st.success("截图生成成功！")
                                    st.image(screenshot_full_url, caption="网页截图预览", use_container_width=True)
                                    
                                    # 提供下载链接
                                    st.markdown(f"[点击下载截图]({screenshot_full_url})")
                            except Exception as e:
                                st.error(f"生成截图时出错: {str(e)}")
                    else:
                        # 对非Bento网页显示禁用的按钮
                        st.button("📸 截图下载", key=f"screenshot_disabled_{record['id']}", type="secondary", disabled=True, use_container_width=True)
                
                with col4:
                    # 删除按钮
                    delete_button = st.button("🗑️ 删除记录", key=f"delete_html_{record['id']}", type="secondary", use_container_width=True)
                    if delete_button:
                        from utils.history_utils import delete_history_record
                        delete_history_record(current_user, record['id'])
                        # 使用session_state来触发重新加载
                        st.session_state['history_trigger_rerun'] = True
            else:
                # Markdown 内容
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f093fb15 0%, #f5576c15 100%); 
                     border-left: 4px solid #f093fb; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <strong>📝 Markdown文章</strong><br>
                    <span style="font-size: 0.9rem; opacity: 0.8;">查看预览或下载到本地编辑</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 创建四列布局，分别放置Markdown预览、公众号预览、下载按钮和删除按钮
                st.markdown("##### 🎯 操作选项")
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                
                with col1:
                    # Markdown预览按钮
                    if st.button("📄 Markdown预览", key=f"preview_md_{record['id']}", use_container_width=True, type="primary"):
                        preview_markdown_article(content)
                
                with col2:
                    # 公众号预览按钮
                    if st.button("📱 公众号预览", key=f"wechat_preview_{record['id']}", use_container_width=True, type="secondary"):
                        preview_wechat_article(content)

                with col3:
                    # 下载按钮
                    st.download_button(
                        label="📥 下载" + (" (已编辑)" if has_been_edited else ""),
                        data=content,
                        file_name=f"{record['topic']}{' (已编辑)' if has_been_edited else ''}.md",
                        mime="text/markdown",
                        key=f"download_{record['id']}",
                        use_container_width=True,
                        type="secondary"
                    )
                with col4:
                    # 删除按钮
                    delete_button = st.button("🗑️ 删除", key=f"delete_md_{record['id']}", type="secondary", use_container_width=True)
                    if delete_button:
                        from utils.history_utils import delete_history_record
                        delete_history_record(current_user, record['id'])
                        st.success("✅ 文章已删除")
                        time.sleep(1)
                        st.rerun()
                
    # 检查是否需要重新加载页面
    if st.session_state.get('history_trigger_rerun', False):
        # 重置标志
        st.session_state['history_trigger_rerun'] = False
        st.rerun()

# Call the main function
main()
