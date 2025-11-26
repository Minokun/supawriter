import streamlit as st
import sys
import logging
import re
from utils.searxng_utils import llm_task, chat, parse_outline_json
from utils.searxng_utils import Search
import utils.prompt_template as pt
from utils.qiniu_utils import ensure_public_image_url
import concurrent.futures
import asyncio
import nest_asyncio
from settings import LLM_MODEL, DEFAULT_SPIDER_NUM, DEFAULT_ENABLE_IMAGES, DEFAULT_IMAGE_EMBEDDING_METHOD
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import add_history_record
from utils.embedding_utils import (
    create_faiss_index,
    search_similar_text,
)
from utils.config_manager import get_config
from utils.streamlit_thread_helper import create_thread_safe_callback, create_spider_progress_callback
import streamlit.components.v1 as components
import threading
import time
from datetime import datetime
from utils.wechat_converter import markdown_to_wechat_html
# 仅在utils中使用DDGS/requests/base64，这里不直接依赖

# 辅助函数：清理大模型输出中的 thinking 标签
def remove_thinking_tags(content):
    """
    移除大模型输出中的 thinking 标签及其内容
    支持的标签格式：<thinking>、<think>、<thought>
    只移除独立成段的thinking标签，避免误删代码示例中的内容
    """
    if not content or not isinstance(content, str):
        return content
    
    # 只在内容开头或换行后匹配thinking标签，避免误删代码示例
    # 使用更严格的匹配模式：标签前后必须有换行或在字符串开头/结尾
    think_patterns = [
        r'(?:^|\n)\s*<thinking>.*?</thinking>\s*(?:\n|$)',
        r'(?:^|\n)\s*<think>.*?</think>\s*(?:\n|$)',
        r'(?:^|\n)\s*<thought>.*?</thought>\s*(?:\n|$)'
    ]
    
    cleaned_content = content
    for pattern in think_patterns:
        # 使用 DOTALL 标志使 . 匹配包括换行符在内的所有字符
        # 保留匹配前后的换行符，只删除标签本身
        cleaned_content = re.sub(pattern, '\n', cleaned_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 清理可能产生的多余空行（3个或以上换行符减少为2个）
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    
    # 清理首尾多余空行，但保留基本格式
    return cleaned_content.strip('\n')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def generate_article_background(task_state, text_input, model_type, model_name, spider_num, custom_style, enable_images, article_title, username: str, extra_urls: list = None):
    """
    在后台线程中运行的文章生成函数。
    通过更新共享的task_state字典来报告进度。
    """
    # 注意：不要在后台线程中调用任何 Streamlit 的 st.* API
    # 仅更新传入的 task_state 字典，由主线程负责渲染 UI
    
    # 导入所需模块
    import hashlib
    import time
    
    # --- 将log函数定义提升到函数顶层作用域 ---
    def log(level, message):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_message = f"[{timestamp}] [{level.upper()}] {message}"
        task_state['log'].append(log_message)
        
        # 同时输出到终端
        if level.lower() == 'error':
            logger.error(message)
        elif level.lower() == 'warning':
            logger.warning(message)
        else:
            logger.info(message)

    try:
        # 0. 初始化
        task_state['status'] = 'running'
        log('info', "任务初始化...")
        task_state['progress'] = 0
        task_state['progress_text'] = "任务初始化..."
        
        # --- 使用主线程传入的用户信息，避免在子线程中访问 Streamlit 会话 ---
        username = username or "anonymous"
        
        # 生成文章ID（基于标题和时间戳）
        article_hash = hashlib.md5(f"{article_title}_{int(time.time())}".encode()).hexdigest()[:8]
        article_id = f"article_{article_hash}"
        
        # 记录用户和文章ID信息，方便后续调试
        log('info', f"用户: {username}, 文章ID: {article_id}")
        
        # 初始化FAISS索引变量，但不加载索引
        # 索引将在搜索完成后加载，以确保获取最新数据
        faiss_index = None

        # 1. 抓取网页内容
        task_state['progress'] = 10
        task_state['progress_text'] = "正在抓取网页内容 (0/未知)..."
        log('info', "开始抓取网页...")
        
        # 定义线程安全的进度回调函数（支持爬虫和图片embedding两个阶段）
        spider_progress_callback = create_spider_progress_callback(
            task_state=task_state,
            progress_key='progress',
            text_key='progress_text',
            start_percent=10,
            end_percent=25,  # 爬虫阶段 10-25%
            embed_start_percent=25,
            embed_end_percent=30,  # 图片embedding阶段 25-30%
            log_prefix="正在抓取网页内容"
        )

        search_result = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 确定图片嵌入方式
            use_direct_image_embedding = enable_images and (DEFAULT_IMAGE_EMBEDDING_METHOD == 'direct_embedding')
            is_multimodal = enable_images and (DEFAULT_IMAGE_EMBEDDING_METHOD == 'multimodal')
            
            log('info', f"图片处理状态: 启用={enable_images}, 嵌入方式={'none' if not enable_images else DEFAULT_IMAGE_EMBEDDING_METHOD}")
            
            # 确保传递正确的spider_num参数
            log('info', f"设置爬虫数量: {spider_num}")
            
            try:
                future = executor.submit(
                    Search(result_num=spider_num).get_search_result, 
                    text_input, 
                    is_multimodal=is_multimodal,
                    use_direct_image_embedding=use_direct_image_embedding,
                    theme=article_title, 
                    progress_callback=spider_progress_callback, 
                    username=username, 
                    article_id=article_id,
                    model_type=model_type,
                    model_name=model_name
                )
                search_result = future.result()
                log('info', f"搜索成功完成，获取结果数: {len(search_result)}")
            except Exception as e:
                log('error', f"搜索过程出错: {str(e)}")
                task_state['status'] = 'error'
                task_state['progress'] = 0
                task_state['progress_text'] = f"搜索过程出错: {str(e)}"
                return
        
        # 检查搜索结果是否为空
        if not search_result or len(search_result) == 0:
            log('error', "搜索结果为空，无法生成文章。请尝试修改搜索关键词或增加搜索结果数量。")
            task_state['status'] = 'error'
            task_state['progress'] = 0
            task_state['progress_text'] = "搜索结果为空，无法生成文章"
            return
            
        log('info', f"搜索引擎查询完成，获取 {len(search_result)} 个结果")
        task_state['search_result'] = search_result # 保存结果以供预览
        
        # 搜索完成后，加载FAISS索引以获取图片数据
        if enable_images:
            try:
                # 等待一小段时间，确保索引文件写入完成
                time.sleep(1)
                
                # 使用用户和文章特定的索引路径
                expected_index_path = f"data/faiss/{username}/{article_id}/index.faiss"
                log('info', f"尝试加载用户和文章特定的FAISS索引: {expected_index_path}")
                
                # 加载索引
                faiss_index = create_faiss_index(load_from_disk=True, index_dir='data/faiss', username=username, article_id=article_id)
                index_size = faiss_index.get_size()
                log('info', f"加载FAISS索引成功，共 {index_size} 张图片数据。")
                
                # 检查索引是否为空
                if index_size == 0:
                    log('warn', f"警告: FAISS索引为空，可能图片数据未正确保存或未找到相关图片。")
            except Exception as e:
                log('error', f"加载FAISS索引失败: {str(e)}")
                faiss_index = None

        # 取消在此直接调用DDGS索引补充：该逻辑已在utils.searxng_utils.Search.get_search_result内部统一处理
        
        # 处理额外的URL（如果有）
        if extra_urls and len(extra_urls) > 0:
            log('info', f"开始抓取 {len(extra_urls)} 个额外的网页链接...")
            task_state['progress'] = 25
            task_state['progress_text'] = f"正在抓取额外网页 (0/{len(extra_urls)})..."
            
            try:
                # 导入必要的模块
                from utils.grab_html_content import get_main_content
                import asyncio
                
                # 创建额外URL的进度回调
                extra_progress_callback = create_thread_safe_callback(
                    task_state=task_state,
                    progress_key='progress',
                    text_key='progress_text',
                    start_percent=25,
                    end_percent=30,
                    log_prefix="正在抓取额外网页"
                )
                
                # 异步抓取额外的URL
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                extra_results = loop.run_until_complete(
                    get_main_content(
                        extra_urls, 
                        task_id=article_id,
                        is_multimodal=is_multimodal,
                        use_direct_image_embedding=use_direct_image_embedding,
                        theme=article_title,
                        progress_callback=extra_progress_callback,
                        username=username,
                        article_id=article_id
                    )
                )
                
                loop.close()
                
                # 过滤掉抓取失败的结果
                valid_extra_results = []
                for result in extra_results:
                    if result.get('text') and result['text'].strip():
                        # 构造与搜索结果相同的格式
                        formatted_result = {
                            'url': result.get('url', ''),
                            'title': result.get('title', '未命名'),
                            'body': result.get('text', ''),
                            'snippet': result.get('text', '')[:200] + '...' if len(result.get('text', '')) > 200 else result.get('text', ''),
                            'is_extra_url': True  # 标记为额外URL
                        }
                        valid_extra_results.append(formatted_result)
                        log('info', f"成功抓取额外网页: {result.get('url', 'unknown')}")
                    else:
                        log('warn', f"抓取额外网页失败或内容为空: {result.get('url', 'unknown')}")
                
                # 合并到搜索结果中
                if valid_extra_results:
                    search_result.extend(valid_extra_results)
                    log('info', f"成功添加 {len(valid_extra_results)} 个额外网页到搜索结果中，总计 {len(search_result)} 个结果")
                    # 更新task_state中的搜索结果，确保UI显示正确的总数
                    task_state['search_result'] = search_result
                else:
                    log('warn', "没有成功抓取到任何额外网页内容")
                    
            except Exception as e:
                log('error', f"抓取额外网页时出错: {str(e)}")
                import traceback
                log('debug', traceback.format_exc())
        
        # 输出最终的总结果数（包含搜索引擎结果 + 额外URL）
        log('info', f"===== 资料收集完成，共 {len(search_result)} 个网页资料（搜索引擎 + 额外URL）=====")

        # 2. 生成大纲
        task_state['progress'] = 30
        task_state['progress_text'] = "正在生成大纲 (0/未知)..."
        log('info', "开始生成文章大纲...")

        outline_progress_callback = create_thread_safe_callback(
            task_state=task_state,
            progress_key='progress',
            text_key='progress_text',
            start_percent=30,
            end_percent=60,
            log_prefix="正在生成大纲"
        )

        outlines = llm_task(search_result, text_input, pt.ARTICLE_OUTLINE_GEN, model_type=model_type, model_name=model_name, progress_callback=outline_progress_callback)
        outlines = remove_thinking_tags(outlines)  # 清理 thinking 标签
        log('info', "大纲初稿生成完毕。")

        # 3. 融合大纲
        task_state['progress'] = 60
        task_state['progress_text'] = "正在融合和优化大纲..."
        log('info', "开始融合大纲...")
        if isinstance(outlines, str) and outlines.count("title") <= 1:
            outline_summary = outlines
        else:
            outline_summary = chat(f'<topic>{text_input}</topic> <content>{outlines}</content>', pt.ARTICLE_OUTLINE_SUMMARY, model_type=model_type, model_name=model_name)
            outline_summary = remove_thinking_tags(outline_summary)  # 清理 thinking 标签
        
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
                outline_block_content = remove_thinking_tags(outline_block_content)  # 清理 thinking 标签
                
                custom_prompt = pt.ARTICLE_OUTLINE_BLOCK
                if custom_style and custom_style.strip():
                    custom_prompt = custom_prompt.replace('---要求---', f'---要求---\n        - 请围绕这个这个中心主题来编写当前章节内容：{custom_style} \n')
                
                final_instruction = '，注意不要包含任何标题（不要包含h1和h2标题），直接开始正文内容' if is_first_chapter else ''
                outline_block_content_final = chat(
                    f'<完整大纲>{outline_summary}</完整大纲> <相关资料>{outline_block_content}</相关资料> 请根据上述信息，书写大纲中的以下这部分内容：{outline_block}{final_instruction}',
                    custom_prompt, model_type=model_type, model_name=model_name)
                outline_block_content_final = remove_thinking_tags(outline_block_content_final)  # 清理 thinking 标签

                # 图像处理逻辑
                if enable_images and faiss_index and faiss_index.get_size() > 0:
                    try:
                        chapter_title = outline_block.get('h1', '')
                        log('info', f"开始为章节 '{chapter_title}' 搜索图片，当前FAISS索引大小: {faiss_index.get_size()}")
                        
                        # 构建章节内容字符串用于图片匹配
                        outline_block_str = chapter_title + "".join(outline_block.get('h2', [])) + outline_block_content_final
                        
                        # 根据配置确定图片嵌入方式
                        # 查询内容是纯文本，不能按图片URL处理，否则会尝试将整段文本当作URL去下载，导致失败
                        # 因此在检索阶段始终将查询作为文本向量来计算
                        is_image_url_search = False
                        embedding_method_name = '直接图片URL嵌入' if DEFAULT_IMAGE_EMBEDDING_METHOD == 'direct_embedding' else '多模态嵌入'
                        
                        # 设置相似度阈值 - 从配置获取或使用默认值
                        # 可以从settings.py中获取，或在此处设置默认值
                        similarity_threshold = 0  # 提高默认阈值以确保更好的匹配质量
                        
                        # 搜索相似图片
                        _, similarities, matched_data = search_similar_text(
                            outline_block_str, 
                            faiss_index, 
                            k=10, 
                            is_image_url=is_image_url_search
                        )
                        log('info', f"图片搜索完成，找到 {len(matched_data)} 个匹配结果，使用{embedding_method_name}方式")
                        
                        # 处理匹配结果
                        image_inserted = False
                        max_images_per_chapter = 3  # 每个章节最多插入的图片数量
                        images_inserted = 0
                        
                        if matched_data:
                            # 按相似度排序处理匹配结果
                            for similarity, data in zip(similarities, matched_data):
                                if images_inserted >= max_images_per_chapter:
                                    break
                                    
                                if isinstance(data, dict) and 'image_url' in data:
                                    image_url = data['image_url']
                                    # 将百度/CDN等受限链接上传到七牛云，获取可公开访问的URL
                                    public_url = ensure_public_image_url(image_url)
                                    
                                    # 检查图片URL是否已被使用（基于转换后的最终URL）
                                    if public_url not in used_images:
                                        log('info', f"找到相似度为{similarity:.4f}的图片：{image_url}")
                                        
                                        # 检查相似度是否达到阈值
                                        if similarity >= similarity_threshold:
                                            used_images.add(public_url)
                                            
                                            # 根据已插入图片数量决定插入位置
                                            if images_inserted == 0:
                                                # 第一张图片放在章节开头
                                                image_markdown = f"![图片]({public_url})\n\n"
                                                outline_block_content_final = image_markdown + outline_block_content_final
                                            else:
                                                # 后续图片尝试插入到段落之间
                                                paragraphs = outline_block_content_final.split('\n\n')
                                                if len(paragraphs) >= 3:
                                                    # 计算插入位置 - 尝试均匀分布
                                                    insert_position = len(paragraphs) // (max_images_per_chapter) * images_inserted
                                                    # 确保位置有效
                                                    insert_position = min(insert_position, len(paragraphs) - 1)
                                                    insert_position = max(insert_position, 1)  # 至少从第二段开始
                                                    
                                                    # 插入图片
                                                    image_markdown = f"\n\n![图片]({public_url})"
                                                    paragraphs[insert_position] = paragraphs[insert_position] + image_markdown
                                                    outline_block_content_final = '\n\n'.join(paragraphs)
                                                else:
                                                    # 如果段落不够，就添加到末尾
                                                    image_markdown = f"\n\n![图片]({public_url})"
                                                    outline_block_content_final += image_markdown
                                            
                                            log('info', f"为章节 '{chapter_title}' 插入第 {images_inserted+1} 张图片，相似度: {similarity:.4f}")
                                            images_inserted += 1
                                            image_inserted = True
                            
                            # 如果未插入图片，记录警告
                            if not image_inserted:
                                log('warn', f"章节 '{chapter_title}' 未找到符合相似度阈值({similarity_threshold})的未使用图片。")
                    except Exception as e:
                        log('error', f"图片匹配时出错: {str(e)}")
                        # 记录详细的错误堆栈以便调试
                        import traceback
                        log('debug', traceback.format_exc())
                elif enable_images:
                    log('warn', "FAISS索引为空或加载失败，跳过本章节的图片匹配。")

                article_chapters.append(outline_block_content_final)
                
                # 实时更新文章内容，包含summary
                live_article_content = '\n\n'.join(article_chapters)
                if outline_summary_json.get('summary') and outline_summary_json['summary'].strip():
                    summary_text = outline_summary_json['summary'].strip()
                    summary_markdown = f"> **文章概要**\n> {summary_text}\n\n"
                    live_article_content = summary_markdown + live_article_content
                task_state['live_article'] = live_article_content

        # 5. 完成并保存
        task_state['progress'] = 100
        task_state['progress_text'] = "文章生成完成！"
        log('info', "文章已生成，正在保存到历史记录...")
        
        # 组装最终文章，在最前面添加summary
        final_article_content = '\n\n'.join(article_chapters)
        
        # 在文章最前面添加summary（使用markdown引用格式）
        if outline_summary_json.get('summary') and outline_summary_json['summary'].strip():
            summary_text = outline_summary_json['summary'].strip()
            summary_markdown = f"> **文章概要**\n> {summary_text}\n\n"
            final_article_content = summary_markdown + final_article_content
        if final_article_content.strip():
            if username and username != "anonymous":
                try:
                    add_history_record(
                        username, 
                        outline_summary_json['title'], 
                        final_article_content, 
                        summary=outline_summary_json.get('summary', ''), 
                        model_type=model_type, 
                        model_name=model_name, 
                        spider_num=spider_num, 
                        custom_style=custom_style,
                        is_transformed=False,
                        image_enabled=enable_images,
                        tags=outline_summary_json.get('tags', ''),
                        article_topic=text_input,
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

@require_auth
def main():
    # 应用nest_asyncio
    nest_asyncio.apply()
    if st.runtime.exists() and sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # --- 状态检查与智能重置 ---
    # 检查是否有残留的、已死亡的后台任务状态
    if 'article_task' in st.session_state and st.session_state.article_task['status'] == 'running':
        active_threads = [t for t in threading.enumerate() if t.name == 'generate_article_background']
        if not active_threads:
            st.warning("检测到上次任务异常中断，已重置状态。", icon="⚠️")
            del st.session_state.article_task # 重置任务状态

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

        # 显示当前使用的全局模型 - 从配置管理器获取
        config = get_config()
        global_settings = config.get('global_model_settings', {})
        if global_settings:
            st.info(f"当前模型: **{global_settings.get('provider')}/{global_settings.get('model_name')}**")
        else:
            st.warning("尚未配置全局模型，请前往'系统设置'页面配置。")

        st.divider()
        
        # 添加额外网页链接选项（放在分割线下方，表单外部，保持实时交互）
        enable_extra_urls = st.checkbox(
            "添加抓取额外网页链接",
            value=False,
            help="启用后，可以手动添加需要爬取内容的网页URL，这些内容将合并到搜索结果中",
            disabled=(task_state['status'] == 'running')
        )
        
        extra_urls_text = ""
        if enable_extra_urls:
            extra_urls_text = st.text_area(
                label='输入额外的网页链接',
                help='每行输入一个URL，这些网页的内容将被抓取并合并到搜索结果中',
                placeholder='https://example.com/article1\nhttps://example.com/article2',
                height=150,
                key='extra_urls_input',
                disabled=(task_state['status'] == 'running')
            )
            if extra_urls_text:
                # 统计有效的URL数量
                valid_urls = [url.strip() for url in extra_urls_text.strip().split('\n') if url.strip() and url.strip().startswith('http')]
                st.caption(f"已输入 {len(valid_urls)} 个有效URL")

        with st.form(key='my_form'):
            text_input = st.text_input(
                label='请填写文章的主题', 
                help='文章将全部围绕该主题撰写，主题越细，文章也越详细',
                value='',
                key='article_topic',
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
        st.session_state.article_task = {
            "status": "running", "progress": 0, "progress_text": "准备开始...",
            "result": "", "error_message": "", "log": ["任务已启动..."],
            "search_result": [], "outline": {}, "live_article": ""
        }
        
        # 从UI收集所有需要的参数
        article_title = text_input # 使用主题作为标题
        enable_images = DEFAULT_ENABLE_IMAGES
        spider_num = DEFAULT_SPIDER_NUM

        # 在主线程中获取当前用户，作为子线程的只读上下文数据
        current_user = get_current_user()
        username = current_user if current_user else "anonymous"

        # 获取全局模型设置 - 从配置管理器获取
        config = get_config()
        global_settings = config.get('global_model_settings', {})
        # 如果全局设置为空，则使用第一个可用的模型作为后备
        if not global_settings:
            default_provider = list(LLM_MODEL.keys())[0]
            default_model = LLM_MODEL[default_provider]['model'][0] if isinstance(LLM_MODEL[default_provider]['model'], list) else LLM_MODEL[default_provider]['model']
            model_type = default_provider
            model_name = default_model
        else:
            model_type = global_settings.get('provider')
            model_name = global_settings.get('model_name')

        # 解析额外的URL（如果有）
        extra_urls = []
        if 'extra_urls_input' in st.session_state and st.session_state.extra_urls_input:
            extra_urls_text = st.session_state.extra_urls_input.strip()
            if extra_urls_text:
                # 按行分割并过滤有效的URL
                extra_urls = [url.strip() for url in extra_urls_text.split('\n') 
                             if url.strip() and url.strip().startswith('http')]
                logger.info(f"用户添加了 {len(extra_urls)} 个额外URL: {extra_urls}")
        
        # 创建并启动后台线程（不传递 Streamlit 上下文，仅传递必要数据）
        thread = threading.Thread(
            target=generate_article_background,
            name="generate_article_background", # 为线程命名
            args=(
                st.session_state.article_task, text_input, model_type, model_name, 
                spider_num, custom_style, enable_images, article_title, username, extra_urls
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
        
        # 确保faiss_index和enable_images变量可用
        enable_images = DEFAULT_ENABLE_IMAGES
        faiss_index = None
        
        # 尝试从任务状态获取当前用户和文章ID
        current_user = get_current_user()
        username = current_user if current_user else "anonymous"
        
        # 从日志中尝试提取文章ID
        article_id = None
        for log_line in task_state.get('log', []):
            if "FAISS索引加载成功" in log_line and "/article_" in log_line:
                match = re.search(r"\(([^/]+)/(article_[^\)]+)\)", log_line)
                if match and match.group(2):
                    article_id = match.group(2)
                    break
        
        # 加载FAISS索引
        if enable_images and username and article_id:
            try:
                from utils.embedding_utils import create_faiss_index
                faiss_index = create_faiss_index(load_from_disk=True, index_dir='data/faiss', username=username, article_id=article_id)
            except Exception as e:
                logger.error(f"无法加载FAISS索引用于图片显示: {e}")
        
        # 创建四列布局，用于放置按钮
        col1, col2, col3, col4 = st.columns(4)

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
        
        with col4:
            # 显示FAISS索引中的图片
            if enable_images and faiss_index and faiss_index.get_size() > 0:
                with st.popover("查看抓取的图片"):
                    # 从FAISS索引中提取图片数据
                    all_data = faiss_index.get_all_data()
                    image_data = [data for data in all_data if isinstance(data, dict) and 'image_url' in data]
                    
                    if image_data:
                        st.write(f"共找到 {len(image_data)} 张图片：")
                        
                        # 创建三列网格布局显示图片
                        img_cols = st.columns(3)
                        
                        for i, data in enumerate(image_data):
                            # 轮流使用三列中的一列
                            with img_cols[i % 3]:
                                image_url = data.get('image_url')
                                # 显示图片标题和缩略图
                                if image_url:
                                    image_title = data.get('title', '未命名图片')
                                    st.image(image_url, caption=f"{i+1}. {image_title[:20]}...", use_column_width=True)
                    else:
                        st.info("暂无图片数据")

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

        # “编辑/预览”切换
        mode = st.segmented_control(
            "模式选择",
            ["预览模式", "编辑模式", "公众号预览"],
            default="编辑模式" if st.session_state.edit_mode else "预览模式",
            selection_mode="single",
            label_visibility="collapsed"
        )
        st.session_state.edit_mode = (mode == "编辑模式")

        # 根据模式显示不同UI
        if mode == "公众号预览":
            st.markdown("### 📱 公众号样式预览")
            st.info("请直接全选下方内容并复制，然后粘贴到微信公众号编辑器中。")
            
            # 转换为公众号HTML
            wechat_html = markdown_to_wechat_html(st.session_state.edited_full_article)
            
            # 在一个白色背景的容器中显示预览，模拟公众号环境
            st.markdown(
                f"""
                <div style="background-color: white; padding: 20px; border-radius: 5px; border: 1px solid #ddd; max-width: 677px; margin: 0 auto;">
                    {wechat_html}
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        elif st.session_state.edit_mode:
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

        # 添加保存编辑按钮
        if st.button("💾 保存编辑", key="save_edited_article"):
            try:
                # 获取当前用户
                current_user = get_current_user()
                if current_user:
                    # 获取原始记录信息
                    from utils.history_utils import load_user_history, save_user_history
                    history = load_user_history(current_user)
                    
                    # 查找最新的记录（应该是刚刚生成的文章）
                    latest_record = None
                    for record in reversed(history):
                        if record.get('topic') == task_state.get('outline', {}).get('title'):
                            latest_record = record
                            break
                    
                    if latest_record:
                        # 更新文章内容
                        latest_record['article_content'] = st.session_state.edited_full_article
                        # 添加编辑时间戳
                        latest_record['edited_at'] = datetime.now().isoformat()
                        # 保存更新后的历史记录
                        save_user_history(current_user, history)
                        st.success("✅ 编辑已保存到数据库！")
                    else:
                        st.error("❌ 无法找到原始文章记录，请尝试重新生成文章。")
                else:
                    st.error("❌ 无法获取当前用户信息，请重新登录。")
            except Exception as e:
                st.error(f"❌ 保存编辑时出错: {str(e)}")

    # --- UI for Error ---
    elif status == 'error':
        st.error(f"任务执行失败: {task_state['error_message']}")
        with st.expander("查看错误日志", expanded=True):
            log_html = ""
            for line in task_state['log']:
                color = "#FFFFFF"
                if "[ERROR]" in line or "Traceback" in line:
                    color = "#FF4B4B"
                # 先处理换行符替换，再放入 f-string
                formatted_line = line.replace("\n", "<br>")
                log_html += f'<div style="color: {color}; font-family: monospace; font-size: 13px;">{formatted_line}</div>'
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
