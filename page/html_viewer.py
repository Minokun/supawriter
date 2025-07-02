import streamlit as st
import sys
import logging
import os
import base64
import uuid
import asyncio
from PIL import Image
from io import BytesIO
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import load_user_history, save_html_to_user_dir, save_image_to_user_dir
from utils.html_generator import wrap_with_dark_theme, fix_gradient_text_for_screenshots
import page_settings

# Import playwright for screenshot functionality
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright not available. Screenshot functionality will be disabled.")

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
    
    # 下载按钮和转换为图片按钮
    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
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
            
    with col3:
        # 转换为图片按钮
        if PLAYWRIGHT_AVAILABLE:
            if st.button("转换为图片", key="convert_to_image"):
                try:
                    # 使用工具函数保存HTML到临时文件
                    html_path, _ = save_html_to_user_dir(current_user, content)
                    
                    # 生成图片文件名
                    img_filename = f"{uuid.uuid4().hex}.png"
                    img_path = os.path.join(os.path.dirname(html_path), img_filename)
                    
                    # 使用Playwright截图
                    with st.spinner("正在使用Playwright转换为图片..."):
                        with sync_playwright() as p:
                            browser = p.chromium.launch()
                            page = browser.new_page(viewport={"width": 1200, "height": 800})
                            page.goto(f"file://{html_path}")
                            # 等待页面加载完成
                            page.wait_for_load_state("networkidle")
                            # 截取整个页面
                            page.screenshot(path=img_path, full_page=True)
                            browser.close()
                    
                    # 生成可访问的URL
                    # 读取生成的图片数据
                    with open(img_path, 'rb') as f:
                        img_data = f.read()
                    
                    # 使用工具函数保存图片并获取URL
                    _, img_url = save_image_to_user_dir(current_user, img_data, img_filename)
                    
                    st.success("文章已成功转换为图片！")
                    st.markdown(f"![文章图片]({img_url})")
                    st.markdown(f"[点击查看完整图片]({img_url})")
                    
                except Exception as e:
                    st.error(f"转换图片时出错: {str(e)}")
                    logger.error(f"Error converting to image: {str(e)}")
        else:
            st.warning("Playwright未安装，无法使用截图功能。请安装playwright包。")
    
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

def install_playwright_if_needed():
    """安装Playwright及其依赖"""
    try:
        import playwright
        return True
    except ImportError:
        try:
            import subprocess
            st.info("正在安装Playwright，这可能需要几分钟时间...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            st.success("Playwright安装成功！请刷新页面。")
            return True
        except Exception as e:
            st.error(f"安装Playwright失败: {str(e)}")
            return False

if __name__ == "__main__":
    main()
