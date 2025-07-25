import streamlit as st
import sys
import logging
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import load_user_history, save_html_to_user_dir
from utils.playwright_utils import take_webpage_screenshot_sync
from settings import ARTICLE_TRANSFORMATIONS, HISTORY_FILTER_BASE_OPTIONS, HTML_NGINX_BASE_URL
import os
import time

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('history')

@require_auth
def main():
    st.title("历史记录")
    
    # Get current user
    current_user = get_current_user()
    if not current_user:
        st.error("无法获取当前用户信息")
        return
    
    # Load user history
    history = load_user_history(current_user)
    
    if not history:
        st.info("暂无历史记录")
        return

    # Dynamically create history filter options
    transformation_type_names = list(ARTICLE_TRANSFORMATIONS.keys())
    # Ensure '转换后的文章' is not duplicated if it's a specific transformation type name
    # For now, we assume transformation names are distinct from '完成文章' or '所有文章'
    # A more robust approach might be to have '转换后的文章' as a category, then sub-filter by type
    # But for now, we list all transformation types as top-level filters after base options.
    dynamic_filter_options = HISTORY_FILTER_BASE_OPTIONS + transformation_type_names

    history_filter = st.radio(
        "选择查看的文章类型:", 
        dynamic_filter_options, 
        horizontal=True,
        key='history_filter_type'
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
        st.info(f"暂无 {history_filter} 类型的历史记录")
        return

    # Display history in reverse chronological order (newest first)
    for record in reversed(filtered_history):
        with st.expander(f"📝 {record['topic']} - {record['timestamp'][:16].replace('T', ' ')}"):
            # 展示配置信息，单行显示并加粗类别
            st.markdown(f"**模型供应商**: {record.get('model_type', '-')} &nbsp;&nbsp;&nbsp; **模型名称**: {record.get('model_name', '-')} &nbsp;&nbsp;&nbsp; **写作模式**: {record.get('write_type', '-')} &nbsp;&nbsp;&nbsp; **爬取数量**: {record.get('spider_num', '-')} &nbsp;&nbsp;&nbsp; **写作风格**: {record.get('custom_style', '-')}")
            
            if record.get('is_transformed') and record.get('original_article_id') is not None:
                st.markdown(f"**源文章ID**: {record.get('original_article_id')}")
                
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
                st.info(f"这是一个{'Bento风格' if is_bento else ''}网页内容，点击下方链接查看效果")
                
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
                
                # 生成唯一文件名
                html_filename = f"{record.get('topic', 'article').replace(' ', '_')}_{record['id']}.html"
                
                # 检查文件是否已经存在
                user_html_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'html', current_user)
                file_path = os.path.join(user_html_dir, html_filename)
                
                # 如果文件不存在，才保存HTML内容到文件
                if not os.path.exists(file_path):
                    _, url_path = save_html_to_user_dir(current_user, html_content, html_filename)
                else:
                    # 如果文件已存在，只生成URL路径
                    url_path = f"{current_user}/{html_filename}"
                
                # 生成可访问的URL
                base_url = HTML_NGINX_BASE_URL  # 根据nginx配置调整
                article_url = f"{base_url}{url_path}"
                
                # 创建四列布局，分别放置预览链接、下载按钮、截图按钮和删除按钮
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                
                with col1:
                    # 使用Streamlit的按钮来打开预览链接
                    if st.button("👁️ 预览网页", key=f"history_preview_{record['id']}", type="primary", use_container_width=True):
                        # 使用JavaScript打开新标签页
                        js = f"window.open('{article_url}', '_blank').focus();"
                        st.components.v1.html(f"<script>{js}</script>", height=0)
                
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
                # 对于MD内容，使用popover显示
                with st.popover("点击查看文章内容"):
                    st.markdown(content)
                
                # 创建两列布局，分别放置下载按钮和删除按钮
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # 下载按钮
                    st.download_button(
                        label="📥 下载文章" + (" (已编辑)" if has_been_edited else ""),
                        data=content,
                        file_name=f"{record['topic']}{' (已编辑)' if has_been_edited else ''}.md",
                        mime="text/markdown",
                        key=f"download_{record['id']}",
                        use_container_width=True,
                        type="secondary"
                    )
                with col2:
                    # 删除按钮
                    delete_button = st.button("🗑️ 删除记录", key=f"delete_md_{record['id']}", type="secondary", use_container_width=True)
                    if delete_button:
                        from utils.history_utils import delete_history_record
                        delete_history_record(current_user, record['id'])
                        # 使用session_state来触发重新加载
                        st.session_state['history_trigger_rerun'] = True
                
    # 检查是否需要重新加载页面
    if st.session_state.get('history_trigger_rerun', False):
        # 重置标志
        st.session_state['history_trigger_rerun'] = False
        st.rerun()

# Call the main function
main()
