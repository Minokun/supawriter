import streamlit as st
import sys
import logging
import os
import uuid
from pathlib import Path
from utils.searxng_utils import Search, llm_task, chat, parse_outline_json
import utils.prompt_template as pt
from utils.image_utils import download_image, get_image_save_directory
import concurrent.futures
import asyncio
import nest_asyncio
from settings import LLM_MODEL, HTML_NGINX_BASE_URL, DEFAULT_SPIDER_NUM, DEFAULT_ENABLE_IMAGES, DEFAULT_DOWNLOAD_IMAGES
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import add_history_record
from utils.embedding_utils import create_faiss_index, get_embedding_instance, search_similar_text
import streamlit.components.v1 as components
import threading
import time

# 配置日志
logger = logging.getLogger(__name__)

from streamlit.runtime.scriptrunner import add_script_run_ctx

def generate_article_background(ctx, task_state, text_input, model_type, model_name, spider_num, custom_style, enable_images, download_images, article_title):
    """
    在后台线程中运行的文章生成函数。
    通过更新共享的task_state字典来报告进度。
    """
    # 将主线程的上下文附加到当前线程
    add_script_run_ctx(threading.current_thread(), ctx)
    
    # 定义一个带时间戳和级别的日志函数
    def log(level, message):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        task_state['log'].append(f"[{timestamp}] [{level.upper()}] {message}")

    try:
        # 0. 初始化
        task_state['status'] = 'running'
        log('info', "任务初始化...")
        task_state['progress'] = 0
        task_state['progress_text'] = "任务初始化..."
        
        # 初始化FAISS索引和Embedding实例
        # 注意：这些资源应该在主线程中创建并传递进来，以避免线程安全问题
        # 这里我们假设资源已经通过某种方式准备好或可以在此安全地初始化
        # 为了简化，我们在这里重新获取，但在大型应用中建议从主线程传入
        faiss_index = create_faiss_index(load_from_disk=True, index_dir='data/faiss')
        embedding_instance = get_embedding_instance()

        # 1. 抓取网页内容
        task_state['progress'] = 10
        task_state['progress_text'] = "正在抓取网页内容 (0/未知)..."
        log('info', "开始抓取网页...")
        
        # 定义进度回调函数
        def spider_progress_callback(completed, total):
            progress_percentage = 10 + int((completed / total) * 20) # 抓取占10%-30%的进度
            task_state['progress'] = progress_percentage
            task_state['progress_text'] = f"正在抓取网页内容 ({completed}/{total})"
            log('info', f"抓取进度: {completed}/{total}")

        search_result = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(Search(result_num=spider_num).get_search_result, text_input, is_multimodal=enable_images, theme=article_title, progress_callback=spider_progress_callback)
            search_result = future.result()
        
        log('info', f"网页抓取完成，共找到 {len(search_result)} 个结果。UI即将更新...")
        task_state['search_result'] = search_result # 保存结果以供预览

        # 2. 生成大纲
        task_state['progress'] = 30
        task_state['progress_text'] = "正在生成大纲 (0/未知)..."
        log('info', "开始生成文章大纲...")

        def outline_progress_callback(completed, total):
            progress_percentage = 30 + int((completed / total) * 30) # 大纲生成占30%-60%的进度
            task_state['progress'] = progress_percentage
            task_state['progress_text'] = f"正在生成大纲 ({completed}/{total})"
            log('info', f"大纲生成进度: {completed}/{total}")

        outlines = llm_task(search_result, text_input, pt.ARTICLE_OUTLINE_GEN, model_type=model_type, model_name=model_name, progress_callback=outline_progress_callback)
        log('info', "大纲初稿生成完毕。")

        # 3. 融合大纲
        task_state['progress'] = 60
        task_state['progress_text'] = "正在融合和优化大纲..."
        log('info', "开始融合大纲...")
        if isinstance(outlines, str) and outlines.count("title") <= 1:
            outline_summary = outlines
        else:
            outline_summary = chat(f'<topic>{text_input}</topic> <content>{outlines}</content>', pt.ARTICLE_OUTLINE_SUMMARY, model_type=model_type, model_name=model_name)
        
        outline_summary_json = parse_outline_json(outline_summary, text_input)
        outline_summary_json.setdefault('title', text_input)
        outline_summary_json.setdefault('summary', "")
        outline_summary_json.setdefault('content_outline', [])
        
        log('info', "大纲融合完成。")
        task_state['outline'] = outline_summary_json # 保存大纲以供预览

        # 4. 逐一书写文章
        article_chapters = []
        if 'content_outline' in outline_summary_json and outline_summary_json['content_outline']:
            repeat_num = len(outline_summary_json['content_outline'])
            base_progress = 70
            
            used_images = set()

            for i, outline_block in enumerate(outline_summary_json['content_outline']):
                n = i + 1
                progress = base_progress + int((n / repeat_num) * 25)
                task_state['progress'] = progress
                task_state['progress_text'] = f"正在撰写: {outline_block.get('h1', '')} ({n}/{repeat_num})"
                log('info', f"撰写章节 {n}/{repeat_num}: {outline_block.get('h1', '')}")

                is_first_chapter = n == 1
                title_instruction = '，注意不要包含任何标题，直接开始正文内容，有吸引力开头（痛点/悬念），生动形象，风趣幽默！' if is_first_chapter else ''
                question = f'<完整大纲>{outline_summary}</完整大纲> 请根据上述信息，书写出以下内容 >>> {outline_block} <<<{title_instruction}'
                
                outline_block_content = llm_task(search_result, question=question, output_type=pt.ARTICLE_OUTLINE_BLOCK, model_type=model_type, model_name=model_name)
                
                custom_prompt = pt.ARTICLE_OUTLINE_BLOCK
                if custom_style and custom_style.strip():
                    custom_prompt = custom_prompt.replace('---要求---', f'---要求---\n        - {custom_style}')
                
                final_instruction = '，注意不要包含任何标题（不要包含h1和h2标题），直接开始正文内容' if is_first_chapter else ''
                outline_block_content_final = chat(
                    f'<完整大纲>{outline_summary}</完整大纲> <相关资料>{outline_block_content}</相关资料> 请根据上述信息，书写大纲中的以下这部分内容：{outline_block}{final_instruction}',
                    custom_prompt, model_type=model_type, model_name=model_name)

                # 图像处理逻辑
                if enable_images:
                    try:
                        faiss_index_reloaded = create_faiss_index(load_from_disk=True, index_dir='data/faiss')
                        if faiss_index_reloaded.get_size() > 0:
                            outline_block_str = outline_block.get('h1', '') + "".join(outline_block.get('h2', [])) + outline_block_content_final
                            _, distances, matched_data = search_similar_text(outline_block_str, faiss_index_reloaded, k=10)
                            
                            image_inserted = False
                            if matched_data:
                                for dist, data in zip(distances, matched_data):
                                    if isinstance(data, dict) and 'image_url' in data:
                                        image_url = data['image_url']
                                        if image_url not in used_images:
                                            similarity = 1.0 - min(dist / 2.0, 0.99)
                                            if similarity >= 0.15:
                                                used_images.add(image_url)
                                                image_markdown = f"![图片]({image_url})\n\n"
                                                outline_block_content_final = image_markdown + outline_block_content_final
                                                log('info', f"为章节 '{outline_block.get('h1', '')}' 插入图片，相似度: {similarity:.2f}")
                                                image_inserted = True
                                                break # 每个章节只插入一张最匹配的
                                if not image_inserted:
                                    log('warn', f"章节 '{outline_block.get('h1', '')}' 未找到合适的未使用图片。")
                        else:
                            log('warn', "FAISS索引为空，跳过图片匹配。")
                    except Exception as e:
                        log('error', f"图片匹配时出错: {str(e)}")

                article_chapters.append(outline_block_content_final)
                task_state['live_article'] = '\n\n'.join(article_chapters) # 实时更新文章内容

        # 5. 完成并保存
        task_state['progress'] = 100
        task_state['progress_text'] = "文章生成完成！"
        log('info', "文章已生成，正在保存到历史记录...")
        
        final_article_content = '\n\n'.join(article_chapters)
        if final_article_content.strip():
            current_user = get_current_user()
            if current_user:
                try:
                    add_history_record(
                        current_user, 
                        outline_summary_json['title'], 
                        final_article_content, 
                        summary=outline_summary_json.get('summary', ''), 
                        model_type=model_type, 
                        model_name=model_name, 
                        spider_num=spider_num, 
                        custom_style=custom_style,
                        is_transformed=False,
                        image_enabled=enable_images,
                    )
                    log('info', "成功保存到历史记录。")
                except Exception as e:
                    error_msg = f"保存历史记录失败: {str(e)}"
                    log('error', error_msg)
                    logger.error(error_msg)

        task_state['result'] = article_chapters
        task_state['status'] = 'completed'

    except BaseException as e:
        import traceback
        full_traceback = traceback.format_exc()
        error_message = f"文章生成过程中发生严重错误: {str(e)}"
        
        # Log to console/file with full traceback
        logger.error(error_message, exc_info=True)

        # Update task state for the UI
        task_state['status'] = 'error'
        task_state['error_message'] = str(e)
        log('error', error_message)
        log('error', full_traceback) # Make traceback visible in UI

def cleanup_faiss_files():
    """删除旧的FAISS索引文件"""
    logger.info("开始清理FAISS索引文件...")
    try:
        index_dir = 'data/faiss'
        os.makedirs(index_dir, exist_ok=True)
        for file_name in ['index.faiss', 'index_data.pkl']:
            file_path = os.path.join(index_dir, file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"已删除旧的FAISS文件: {file_path}")
    except Exception as e:
        logger.error(f"清理FAISS文件失败: {str(e)}")

@require_auth
def main():
    # 应用nest_asyncio
    nest_asyncio.apply()
    if st.runtime.exists() and sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 初始化任务状态
    if "article_task" not in st.session_state:
        st.session_state.article_task = {
            "status": "idle",  # idle, running, completed, error
            "progress": 0,
            "progress_text": "",
            "result": "",
            "error_message": "",
            "log": [],
            "search_result": [],
            "outline": {},
            "live_article": ""
        }
    
    task_state = st.session_state.article_task

    with st.sidebar:
        st.title("超级写手配置项：")

        # 显示当前使用的全局模型
        global_settings = st.session_state.get('global_model_settings', {})
        if global_settings:
            st.info(f"当前模型: **{global_settings.get('provider')}/{global_settings.get('model_name')}**")
        else:
            st.warning("尚未配置全局模型，请前往‘系统设置’页面配置。")

        with st.form(key='my_form'):
            text_input = st.text_input(
                label='请填写文章的主题', 
                help='文章将全部围绕该主题撰写，主题越细，文章也越详细',
                value='',
                disabled=(task_state['status'] == 'running')
            )
            custom_style = st.text_area(
                label='自定义书写风格和要求',
                help='在此输入特定的写作风格和要求...',
                placeholder='例如：请以幽默风趣的口吻撰写...',
                height=100,
                key='custom_style',
                disabled=(task_state['status'] == 'running')
            )
            submit_button = st.form_submit_button(label='执行', disabled=(task_state['status'] == 'running'))

    st.caption('SuperWriter by WuXiaokun.')
    st.subheader("超级写手🤖", divider='rainbow')

    # 主页面UI逻辑
    if submit_button and text_input:
        # 重置状态并开始新任务
        cleanup_faiss_files() # 清理旧文件
        st.session_state.article_task = {
            "status": "running", "progress": 0, "progress_text": "准备开始...",
            "result": "", "error_message": "", "log": ["任务已启动..."],
            "search_result": [], "outline": {}, "live_article": ""
        }
        
        # 从UI收集所有需要的参数
        article_title = text_input # 使用主题作为标题
        enable_images = DEFAULT_ENABLE_IMAGES
        download_images = DEFAULT_DOWNLOAD_IMAGES
        spider_num = DEFAULT_SPIDER_NUM

        # 获取当前线程的上下文
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()

        # 获取全局模型设置
        global_settings = st.session_state.get('global_model_settings', {})
        # 如果全局设置为空，则使用第一个可用的模型作为后备
        if not global_settings:
            default_provider = list(LLM_MODEL.keys())[0]
            default_model = LLM_MODEL[default_provider]['model'][0] if isinstance(LLM_MODEL[default_provider]['model'], list) else LLM_MODEL[default_provider]['model']
            model_type = default_provider
            model_name = default_model
            log('warn', f"未找到全局模型设置，已自动选择第一个可用模型: {model_type}/{model_name}")
        else:
            model_type = global_settings.get('provider')
            model_name = global_settings.get('model_name')
            log('info', f"已加载全局模型设置: {model_type}/{model_name}")

        # 创建并启动后台线程
        thread = threading.Thread(
            target=generate_article_background,
            args=(
                ctx, # 传递上下文
                st.session_state.article_task, text_input, model_type, model_name, 
                spider_num, custom_style, enable_images, download_images, article_title
            )
        )
        thread.start()
        st.rerun()

    # 根据任务状态显示UI
    status = task_state['status']

    # --- UI for Running Task ---
    if status == 'running':
        st.info("任务正在后台执行中... 您可以切换到其他页面，任务不会中断。")
        st.progress(task_state['progress'], text=task_state['progress_text'])
        
        # 创建三列布局，用于放置按钮
        col1, col2, col3 = st.columns(3)

        with col1:
            # 将日志显示也改为Popover，保持UI一致性
            with st.popover("查看实时日志"):
                log_html = ""
                for line in task_state['log']:
                    color = "#FFFFFF" # 默认白色
                    if "[ERROR]" in line:
                        color = "#FF4B4B" # 红色
                    elif "[WARN]" in line:
                        color = "#FFA500" # 橙色
                    elif "[INFO]" in line:
                        color = "#26C485" # 绿色
                    log_html += f'<div style="color: {color}; font-family: monospace; font-size: 13px;">{line}</div>'
                
                components.html(f'''
                    <div style="height: 300px; overflow-y: scroll; background-color: #1E1E1E; border: 1px solid #444; padding: 10px; border-radius: 5px;">
                        {log_html}
                    </div>
                ''', height=320)

        with col2:
            if task_state['search_result']:
                with st.popover("查看抓取结果"):
                    for item in task_state['search_result']:
                        st.markdown(f"- **{item.get('title', 'N/A')}**\n  <small>[{item.get('url', 'N/A')}]</small>", unsafe_allow_html=True)

        with col3:
            if task_state['outline']:
                with st.popover("查看生成的大纲"):
                    st.json(task_state['outline'])

        # 实时文章预览
        if task_state.get('live_article'):
            with st.expander("实时文章预览", expanded=True):
                st.markdown(task_state['live_article'])
        
        # ** 使用服务器端主动刷新机制 **
        time.sleep(3)
        st.rerun()
        
        # 自动刷新
        components.html("<meta http-equiv='refresh' content='3'>", height=0)

    # --- UI for Completed Task ---
    elif status == 'completed':
        st.success("文章生成完成！您可以预览、编辑并下载文章。")
        st.balloons()

        # 初始化编辑模式的session_state
        if 'edit_mode' not in st.session_state:
            st.session_state.edit_mode = False

        # 将生成的章节合并为单篇完整文章，并存入session_state
        # 这样可以确保即使用户刷新页面，编辑的内容也不会丢失
        if 'edited_full_article' not in st.session_state:
            full_article_text = '\n\n---\n\n'.join(task_state['result'])
            st.session_state.edited_full_article = full_article_text

        # “编辑/预览”切换按钮
        if st.button("✍️ 编辑/预览切换", key="toggle_edit_mode"):
            st.session_state.edit_mode = not st.session_state.edit_mode

        # 根据模式显示不同UI
        if st.session_state.edit_mode:
            # --- 编辑模式：双栏布局 ---
            st.info("您已进入编辑模式。左右两栏均为独立滚动区域，方便长文对照编辑。")
            
            # 注入CSS，使两栏高度固定且可滚动
            st.markdown("""
            <style>
            /* 定位到Streamlit生成的水平块的直接子元素，即我们的列 */
            div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"]:nth-child(1),
            div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"]:nth-child(2) {
                height: 70vh; /* 设置一个固定的视窗高度 */
                overflow-y: auto; /* 当内容超出时，显示垂直滚动条 */
                border: 1px solid #444; /* 添加边框以区分 */
                padding: 15px; /* 增加内边距 */
                border-radius: 8px; /* 圆角 */
            }
            </style>
            """, unsafe_allow_html=True)

            edit_col, preview_col = st.columns(2)

            with edit_col:
                st.markdown("#### 📝 编辑区")
                # 创建一个大的文本框用于编辑全文
                edited_text = st.text_area(
                    label="全文内容",
                    value=st.session_state.edited_full_article,
                    height=600, # 这个高度现在会被CSS覆盖，但保留也无妨
                    key="full_article_editor",
                    label_visibility="collapsed"
                )
                # 实时更新session_state中的内容
                st.session_state.edited_full_article = edited_text
            
            with preview_col:
                st.markdown("#### 👁️ 实时预览")
                # 实时渲染编辑区的内容
                st.markdown(st.session_state.edited_full_article, unsafe_allow_html=True)
        
        else:
            # --- 预览模式：单栏显示完整文章 ---
            st.markdown("### 📄 文章预览")
            # 显示当前已编辑的最新版本
            st.markdown(st.session_state.edited_full_article, unsafe_allow_html=True)

        # 下载按钮（始终可见）
        st.download_button(
            label="📥 下载最终文章",
            data=st.session_state.edited_full_article, # 直接使用session_state中的最新内容
            file_name=f"{task_state.get('outline', {}).get('title', 'untitled')}_final.md",
            mime="text/markdown",
            key="download_final_article"
        )

    # --- UI for Error ---
    elif status == 'error':
        st.error(f"任务执行失败: {task_state['error_message']}")
        with st.expander("查看错误日志", expanded=True):
            log_html = ""
            for line in task_state['log']:
                color = "#FFFFFF"
                if "[ERROR]" in line or "Traceback" in line:
                    color = "#FF4B4B"
                log_html += f'<div style="color: {color}; font-family: monospace; font-size: 13px;">{line.replace("\n", "<br>")}</div>'
            components.html(f'''<div style="height: 400px; overflow-y: scroll; background-color: #1E1E1E; border: 1px solid #444; padding: 10px; border-radius: 5px;">{log_html}</div>''', height=420)

    # --- UI for Idle State ---
    else: # idle
        st.caption("""
            **简介：** 这是一个结合了LLM、搜索引擎和网络爬虫的自动化文章写作机器人。您只需在左侧输入文章主题，它就能自动完成资料搜集、生成大纲、并撰写完整的文章。
            
            **工作流程：**
            1.  **输入主题：** 在左侧边栏输入您想写的文章主题，并可自定义写作风格。
            2.  **执行任务：** 点击“执行”按钮。整个过程根据主题复杂度，可能需要3到10分钟。
            3.  **实时监控：** 任务开始后，您可以实时查看运行日志、抓取进度和生成的大纲。任务在后台运行，您可以随时离开页面再回来查看。
            4.  **编辑与下载：** 文章生成后，您可以在“预览/编辑”双模式下对内容进行修改和润色，然后下载最终的Markdown文件。
            
            **⚠️ 注意：** 请在左侧填写文章主题后点击执行。
        """)

main()
