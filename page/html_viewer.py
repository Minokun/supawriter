import streamlit as st
import sys
import logging
import os
import base64
from PIL import Image
from io import BytesIO
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import load_user_history
from utils.html_generator import wrap_with_dark_theme, fix_gradient_text_for_screenshots
import page_settings

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('html_viewer')

@require_auth
def main():
    st.title("网页预览")
    
    # 1. 从会话状态获取记录ID
    record_id = st.session_state.get("record_id_for_viewer")
    logger.info(f"HTML Viewer: record_id from session state: {record_id}")
    
    # 输出当前会话状态中的所有键
    logger.info(f"Session state keys: {list(st.session_state.keys())}")
    
    if not record_id:
        logger.error("Missing record_id parameter")
        st.error("缺少必要的记录ID参数")
        st.button("返回", on_click=lambda: st.switch_page(page_settings.PAGE_HOME))
        return
        
    # 2. 获取当前用户并加载历史记录
    current_user = get_current_user()
    logger.info(f"Current user: {current_user}")
    history = load_user_history(current_user)
    logger.info(f"History records count: {len(history)}")
    
    # 3. 查找记录
    target_record = None
    record_ids = [str(record.get('id')) for record in history]
    logger.info(f"Available record IDs: {record_ids}")
    
    for record in history:
        if str(record.get('id')) == str(record_id):
            target_record = record
            logger.info(f"Found target record with ID: {record_id}")
            break
            
    if not target_record:
        logger.error(f"Record with ID {record_id} not found in history")
        st.error(f"在您的历史记录中找不到ID为 {record_id} 的记录。")
        st.button("返回", on_click=lambda: st.switch_page(page_settings.PAGE_HOME))
        return
        
    # 4. 提取并显示内容
    content = target_record.get("article_content", "")
    topic = target_record.get("topic", "无标题")
    
    logger.info(f"Topic: {topic}")
    logger.info(f"Content length: {len(content)}")
    logger.info(f"Content preview: {content[:100]}...")
    
    # 检查内容是否为HTML
    is_html = content.strip().startswith('<') and content.strip().endswith('>')
    logger.info(f"Is content HTML? {is_html}")
    
    st.subheader(f"网页预览: {topic}")
    
    # 下载按钮
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.download_button(
            label="下载 HTML",
            data=content,
            file_name=f"{topic}.html",
            mime="text/html",
        ):
            st.success("文件下载成功!")
    
    with col2:
        # 深色主题版本下载按钮
        dark_themed_content = wrap_with_dark_theme(content, title=topic)
        dark_themed_content = fix_gradient_text_for_screenshots(dark_themed_content)
        if st.download_button(
            label="下载深色版",
            data=dark_themed_content,
            file_name=f"{topic}_dark.html",
            mime="text/html",
        ):
            st.success("深色版文件下载成功!")
    
    # 返回按钮
    st.button("返回", on_click=lambda: st.switch_page(page_settings.PAGE_HOME))
    
    # 显示HTML内容
    # 提供多种渲染选项
    render_method = st.radio("选择渲染方式", ["HTML组件", "Markdown", "源代码", "深色主题"], horizontal=True)
    
    if render_method == "HTML组件":
        try:
            logger.info("Attempting to render HTML content with st.components.v1.html")
            # 确保内容是完整的HTML文档
            if not content.strip().startswith('<!DOCTYPE html>') and not content.strip().startswith('<html'):
                # 如果不是完整的HTML文档，添加必要的HTML标签
                wrapped_content = f"""<!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{topic}</title>
                </head>
                <body>
                {content}
                </body>
                </html>"""
                # 修复渐变文字在截图中的显示问题
                wrapped_content = fix_gradient_text_for_screenshots(wrapped_content)
                st.components.v1.html(wrapped_content, height=800, scrolling=True)
            else:
                # 如果是完整的HTML文档，直接渲染
                # 修复渐变文字在截图中的显示问题
                fixed_content = fix_gradient_text_for_screenshots(content)
                st.components.v1.html(fixed_content, height=800, scrolling=True)
            logger.info("HTML rendering completed")
        except Exception as e:
            logger.error(f"Error rendering HTML: {str(e)}")
            st.error(f"渲染HTML内容时出错: {str(e)}")
            st.info("请尝试其他渲染方式")
    
    elif render_method == "Markdown":
        logger.info("Rendering with st.markdown")
        st.markdown(content, unsafe_allow_html=True)
    
    elif render_method == "深色主题":
        try:
            logger.info("Rendering with dark theme")
            # 将内容包裹在深色主题中
            dark_themed_content = wrap_with_dark_theme(content, title=topic)
            # 修复渐变文字在截图中的显示问题
            dark_themed_content = fix_gradient_text_for_screenshots(dark_themed_content)
            st.components.v1.html(dark_themed_content, height=800, scrolling=True)
            logger.info("Dark theme rendering completed")
        except Exception as e:
            logger.error(f"Error rendering dark theme: {str(e)}")
            st.error(f"渲染深色主题时出错: {str(e)}")
            st.info("请尝试其他渲染方式")
    
    else:  # 源代码
        logger.info("Showing raw HTML source code")
        st.subheader("HTML源代码")
        st.code(content, language="html")
        
        # 显示内容长度和类型信息
        st.info(f"内容长度: {len(content)} 字符 | 是否为HTML: {content.strip().startswith('<') and content.strip().endswith('>')}")
        
        # 显示内容开头和结尾
        if len(content) > 100:
            st.text("内容开头: " + content[:100])
            st.text("内容结尾: " + content[-100:])

if __name__ == "__main__":
    main()
