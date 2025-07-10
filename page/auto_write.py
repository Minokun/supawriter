import streamlit as st
import sys
import logging
import os
import requests
import uuid
from pathlib import Path
from utils.searxng_utils import Search, llm_task, chat, parse_outline_json
import utils.prompt_template as pt
from utils.image_utils import download_image, get_image_save_directory
import concurrent.futures
import asyncio
import nest_asyncio
from settings import LLM_MODEL, ARTICLE_TRANSFORMATIONS, HTML_NGINX_BASE_URL
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import add_history_record, load_user_history
from page import transform_article
from utils.embedding_utils import create_faiss_index, get_embedding_instance
import streamlit.components.v1 as components
import os

# 配置日志
logger = logging.getLogger(__name__)

@require_auth
def main():


    # 应用nest_asyncio
    nest_asyncio.apply()
    # 切换到ProactorEventLoop
    if st.runtime.exists() and sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 初始化或重置运行状态
    if "run_status" not in st.session_state:
        st.session_state.run_status = False
    
    # 检查是否需要重置run_status（当页面刷新但不是通过rerun触发时）
    if not st.session_state.get('_is_rerun', False):
        st.session_state.run_status = False
        
    # 使用st.cache_resource装饰器来缓存FAISS索引和Embedding实例
    # 添加TTL=10秒，确保索引每10秒刷新一次
    @st.cache_resource(show_spinner="加载FAISS索引和Embedding模型...")
    def get_cached_resources(force_refresh=False):
        """获取缓存的FAISS索引和Embedding实例，优先从磁盘加载
        
        Args:
            force_refresh: 是否强制从磁盘重新加载索引，即使缓存有效
        """
        logger.info(f"调用get_cached_resources，force_refresh={force_refresh}")
        try:
            # 导入函数放在这里，确保它们在使用前已经被正确导入
            from utils.embedding_utils import create_faiss_index, get_embedding_instance
            import time
            
            # 定义索引目录 - 与grab_html_content.py中使用同一目录
            index_dir = 'data/faiss'
            index_path = f"{index_dir}/index.faiss"
            data_path = f"{index_dir}/index_data.pkl"
            
            # 确保目录存在
            import os
            os.makedirs(index_dir, exist_ok=True)
            
            # 第一次加载时，设置清除标志
            if 'first_load' not in st.session_state:
                st.session_state.first_load = True
                st.session_state.should_clear_index = True
                logger.info("首次加载，设置清除索引标志")
            
            # 在以下情况下清除索引：
            # 1. 强制刷新且should_clear_index标志为True
            # 2. 首次加载
            should_delete_files = (force_refresh and st.session_state.get('should_clear_index', False)) or st.session_state.get('first_load', False)
            
            if should_delete_files:
                # 清除当前函数的缓存
                get_cached_resources.clear()
                logger.info("清除FAISS索引缓存")
                
                # 删除磁盘上的索引文件
                if os.path.exists(index_path):
                    logger.info(f"删除现有索引文件: {index_path}")
                    try:
                        os.remove(index_path)
                    except Exception as e:
                        logger.error(f"删除索引文件失败: {str(e)}")
                        
                if os.path.exists(data_path):
                    logger.info(f"删除现有数据文件: {data_path}")
                    try:
                        os.remove(data_path)
                    except Exception as e:
                        logger.error(f"删除数据文件失败: {str(e)}")
                
                # 重置状态标志
                st.session_state.should_clear_index = False
                st.session_state.first_load = False
                logger.info("重置清空索引状态标志")
            elif force_refresh:
                logger.info("请求强制刷新，但should_clear_index标志未设置，仅刷新缓存")
                get_cached_resources.clear()  # 仍然清除缓存，但不删除文件
                
            # 记录当前时间，用于调试缓存刷新机制
            current_time = time.strftime("%H:%M:%S", time.localtime())
            logger.info(f"在 {current_time} 加载FAISS索引")
            
            # 尝试从磁盘加载FAISS索引，或创建新的空索引
            faiss_index = create_faiss_index(load_from_disk=True, index_dir=index_dir)
            embedding_instance = get_embedding_instance()
            
            # 如果索引为空，记录一个警告但仍然使用它
            if faiss_index.get_size() == 0:
                logger.warning("FAISS索引为空，可能没有图片数据或未正确加载")
            else:
                logger.info(f"从磁盘成功加载FAISS索引，包含 {faiss_index.get_size()} 条图片数据")
                
            return faiss_index, embedding_instance
        except Exception as e:
            logger.error(f"初始化FAISS索引失败: {str(e)}")
            st.error(f"初始化FAISS索引失败: {str(e)}")
            return None, None
    
    # 获取缓存的资源
    # 将get_cached_resources函数存储在session_state中，以侾grab_html_content.py可以使用
    st.session_state.get_cached_resources = get_cached_resources
    faiss_index, embedding_instance = get_cached_resources()

    with st.sidebar:
        st.title("超级写手配置项：")
        model_type = st.selectbox('请选择模型供应商', list(LLM_MODEL.keys()), key=1)
        model_name = st.selectbox('请选择模型名称', LLM_MODEL[model_type]['model'], key=0)
        with st.form(key='my_form'):
            text_input = st.text_input(label='请填写文章的主题', help='文章将全部围绕该主题撰写，主题越细，文章也越详细',
                                       value='')
            # 存储文章主题作为标题，用于图片下载目录
            if text_input:
                st.session_state['article_title'] = text_input
                
            # 添加自定义书写风格的输入框
            custom_style = st.text_area(
                label='自定义书写风格和要求', 
                help='在此输入特定的写作风格和要求，如"幽默风趣"、"严谨学术"、"简洁明了"等，将影响整篇文章的风格',
                placeholder='例如：请以幽默风趣的口吻撰写，多使用比喻和生动的例子',
                height=100,
                key='custom_style'
            )
            # 去掉写作模式选项，始终使用详细模式
            spider_num = st.slider(label='爬取网页数量', help='（默认5，数量越多时间越长！)', min_value=1, max_value=25, key=3,
                               value=15)
            # Use the checkbox directly without assigning to session_state
            convert_to_simple = st.checkbox("转换白话文", key="convert_to_simple", value=False)
            convert_to_webpage = st.checkbox("转换为Bento风格网页", key="convert_to_webpage", value=False)

            # 图片分析与插入选项放在表单内最下方
            st.subheader("图片设置")
            col1, col2 = st.columns(2)
            with col1:
                st.session_state['enable_images'] = st.checkbox("自动插入相关图片", value=False)
            
            # 只有当启用图片时才显示下载选项
            with col2:
                st.session_state['download_images'] = st.checkbox("图片下载至本地", value=False)
            st.info("使用多模态模式自动插入相关图片，无需额外设置")
            submit_button = st.form_submit_button(label='执行', disabled=st.session_state.run_status)

    st.caption('SuperWriter by WuXiaokun. ')
    st.subheader("超级写手🤖", divider='rainbow')
    
    # 初始化标签页索引，如果不存在则默认为0（main_tab）
    if 'tab_index' not in st.session_state:
        st.session_state.tab_index = 0
    
    # 定义标签页切换回调函数
    def tab_callback():
        # 更新session_state中的tab_index
        st.session_state.tab_index = st.session_state.tabs
    
    # 使用radio组件模拟tabs，因为它可以保持状态
    # 使用水平排列和最小化样式使其看起来像tabs
    st.session_state.tabs = st.radio(
        "选择功能",
        options=[0, 1],
        format_func=lambda x: "写作" if x == 0 else "文章再创作",
        index=st.session_state.tab_index,
        on_change=tab_callback,
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # 根据选择的标签页显示相应内容
    if st.session_state.tabs != 0:
        # 转换标签页内容
        transform_article.main()
        # 提前返回，不显示主标签页内容
        return

    # 主标签页内容，现在直接放在这里
    st.info("""

            🆕简介：本应用是利用LLM+搜索引擎+爬虫开发的自动撰写文章的机器人，只需要填写文章主题,程序会自动书写大纲并逐一撰写文章。

            ⚠️注意：在左侧填写文章主题后，点击执行按钮，整个过程可能需要5分钟-30分钟不到，点击执行后请不要关闭本页面，等待完成后下载文章，刷新或关闭将不会保存。

            1. 模型默认deepseek，效果最好，速度最快，该选项可以不用修改。
            2. 填写文章主题为你想要撰写的文章主题
            3. 爬取网页数量默认为15，数量越多时间越长！系统会自动搜索并爬取网页内容。

            """)

    # Initialize variables
    search_result = []
    outline_summary = ""
    outline_summary_json = {"title": "", "summary": "", "content_outline": []}
    outlines = ""
    article_content = ''

    if submit_button:
        # 设置运行状态为True，防止重复提交
        st.session_state.run_status = True
        # 使用单独的容器来显示进度信息，避免与其他元素重叠
        st.markdown("### 处理进度")
        progress_container = st.container()
        
        # 初始化已使用图片的集合，用于跟踪已插入的图片
        if 'used_images' not in st.session_state:
            st.session_state.used_images = set()
        else:
            # 每次执行时重置已使用图片集合
            st.session_state.used_images = set()
        
        # 首先删除磁盘上的FAISS索引文件
        try:
            if os.path.exists('data/faiss/index.faiss'):
                os.remove('data/faiss/index.faiss')
                logger.info("已删除FAISS索引文件")
            if os.path.exists('data/faiss/index_data.pkl'):
                os.remove('data/faiss/index_data.pkl')
                logger.info("已删除FAISS数据文件")
        except Exception as e:
            logger.error(f"删除FAISS索引文件失败: {str(e)}")
        
        # 设置强制清空索引的标志
        st.session_state.should_clear_index = True
        
        # 清除缓存并重新创建空索引
        try:
            # 强制清除缓存
            get_cached_resources.clear()
            
            # 获取新的空索引 - 这将触发get_cached_resources中的清除逻辑
            cached_faiss_index, _ = get_cached_resources(force_refresh=True)
            
            # 确保索引为空
            if cached_faiss_index:
                cached_faiss_index.clear()
                logger.info("执行按钮点击：成功清空FAISS索引")
                
                # 验证索引是否真的为空
                index_size = cached_faiss_index.get_size()
                logger.info(f"清空后验证索引大小: {index_size}")
                
                if index_size > 0:
                    logger.warning(f"警告：FAISS索引清空后仍有 {index_size} 个项目")
        except Exception as e:
            logger.error(f"清空FAISS索引失败: {str(e)}")
        
        # 先显示进度条，然后再显示其他内容
        progress_bar = progress_container.progress(0, text="Operation in progress. Please wait.")
        
        # 使用更清晰的布局分割
        col_left, col_right = st.columns([3, 2])
        
        # Left column: crawling, search details, outline generation, outline merging
        with col_left:
            st.subheader("处理过程")
            # Crawl web content
            progress_bar.progress(10, text="Spider in progress. Please wait...")
            with st.status("抓取网页内容"):
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # 检查是否启用图片功能，如果启用则使用多模态模式
                    is_multimodal = st.session_state.get('enable_images', False)
                    future = executor.submit(Search(result_num=spider_num).get_search_result, text_input, is_multimodal=is_multimodal, theme=text_input)
                    for future in concurrent.futures.as_completed([future]):
                        search_result = future.result()
            with st.popover("查看搜索详细..."):
                for item in search_result:
                    st.markdown(f"标题：{item.get('title')}  链接：{item.get('url')}")
            
            # 显示当前FAISS索引中的所有图片
            if st.session_state.get('enable_images', False):
                # 使用缓存的FAISS索引实例，但不强制刷新以避免删除索引
                cached_faiss_index, _ = get_cached_resources(force_refresh=False)
                index_size = cached_faiss_index.get_size()
                
                with st.popover(f"查看已抓取的图片 ({index_size})"):
                    if index_size == 0:
                        st.warning("当前没有可用的图片数据")
                    else:
                        # 从FAISS索引获取所有的图片数据
                        all_data = cached_faiss_index.get_all_data()
                        
                        # 创建三列布局显示图片
                        cols = st.columns(3)
                        for i, item in enumerate(all_data):
                            # 检查数据格式，处理字典结构
                            if isinstance(item, dict):
                                img_url = item.get('image_url', '')
                                description = item.get('description', '')
                            else:
                                # 假设公司可能不一定用完全一样的数据结构
                                # 尝试兼容旧格式
                                try:
                                    img_url, description = item
                                except:
                                    st.warning(f"\u8df3过不兼容的图片数据格式: {str(item)[:100]}")
                                    continue
                            
                            # 用于调试
                            # st.write(f"\u56fe片索引 {i}: {img_url}")
                            
                            # 轮流使用不同列显示图片
                            with cols[i % 3]:
                                try:
                                    # 显示图片
                                    st.image(img_url, width=150)
                                    # 显示描述（截断过长的描述）
                                    max_desc_len = 100
                                    short_desc = description if len(description) <= max_desc_len else f"{description[:max_desc_len]}..."
                                    st.caption(short_desc)
                                except Exception as e:
                                    st.error(f"无法加载图片: {str(e)}")

            # Generate outline
            progress_bar.progress(30, text="Spider Down! Now generate the outline...")
            with st.status("生成大纲"):
                try:
                    outlines = llm_task(search_result, text_input, pt.ARTICLE_OUTLINE_GEN, model_type=model_type, model_name=model_name)
                except ConnectionError as e:
                    st.error(f"错误: {str(e)}")
                    st.stop()

            # Merge outline if needed
            progress_bar.progress(60, text="Integrate article outline...")
            with st.status("融合大纲"):
                try:
                    # 检查是否只有一条大纲数据
                    if isinstance(outlines, str) and outlines.count("title") <= 1:
                        # 只有一条大纲数据，直接使用
                        outline_summary = outlines
                    else:
                        # 有多条大纲数据，进行融合
                        outline_summary = chat(f'<topic>{text_input}</topic> <content>{outlines}</content>', 
                                                pt.ARTICLE_OUTLINE_SUMMARY, 
                                                model_type=model_type, 
                                                model_name=model_name)
                except ConnectionError as e:
                    st.error(f"错误: {str(e)}")
                    st.stop()

            # Parse outline JSON
            outline_summary_json = parse_outline_json(outline_summary, text_input)
            outline_summary_json.setdefault('title', text_input)
            outline_summary_json.setdefault('summary', "")
            outline_summary_json.setdefault('content_outline', [])

        # Right column: outline preview
        with col_right:
            st.subheader("大纲预览")
            if outline_summary_json.get('content_outline'):
                with st.popover("查看大纲"):
                    st.json(outline_summary_json)
                
                # 使用更清晰的格式显示标题和摘要
                st.markdown(f"### {outline_summary_json['title']}")
                st.markdown(f"> {outline_summary_json['summary']}")
                    
                    

        # *************************** 书写文章 *************************
        if 'content_outline' in outline_summary_json and outline_summary_json['content_outline']:
            repeat_num = len(outline_summary_json['content_outline'])
            my_bar_article_start = 100 - repeat_num*2
            progress_bar.progress(my_bar_article_start, text="Writing article...")
        with st.spinner("书写文章..."):
            n = 1
            # Reset article_content if it's already in the submit_button block
            article_content = ''
            if 'content_outline' in outline_summary_json and outline_summary_json['content_outline']:
                for outline_block in outline_summary_json['content_outline']:
                    progress_bar.progress(my_bar_article_start + n*2, text=f"正在撰写  {outline_block['h1']}  {n}/{repeat_num}")
                
                    # 根据抓取的内容资料生成内容
                    # 确定是否需要特殊处理第一章（不包含标题）
                    is_first_chapter = n == 1
                    
                    # 构建问题，第一章特殊处理
                    title_instruction = '，注意不要包含任何标题，直接开始正文内容，有吸引力开头（痛点/悬念），生动形象，风趣幽默！' if is_first_chapter else ''
                    question = f'<完整大纲>{outline_summary}</完整大纲> 请根据上述信息，书写出以下内容 >>> {outline_block} <<<{title_instruction}'
                    
                    # 获取内容块
                    outline_block_content = llm_task(search_result, question=question,
                                                  output_type=pt.ARTICLE_OUTLINE_BLOCK, model_type=model_type, model_name=model_name)
                    
                    # 获取自定义风格并应用到prompt中
                    custom_prompt = pt.ARTICLE_OUTLINE_BLOCK
                    if 'custom_style' in st.session_state and st.session_state.custom_style.strip():
                        # 在原有prompt基础上添加自定义风格要求
                        custom_prompt = custom_prompt.replace('---要求---', f'---要求---\n        - {st.session_state.custom_style}')
                    
                    # 构建最终提示，第一章特殊处理
                    final_instruction = '，注意不要包含任何标题（不要包含h1和h2标题），直接开始正文内容' if is_first_chapter else ''
                    outline_block_content_final = chat(
                        f'<完整大纲>{outline_summary}</完整大纲> <相关资料>{outline_block_content}</相关资料> 请根据上述信息，书写大纲中的以下这部分内容：{outline_block}{final_instruction}',
                        custom_prompt, model_type=model_type, model_name=model_name)
            
                    # 使用单独的容器来显示内容块，避免重叠
                    content_container = st.container()
                    with content_container:
                        with st.expander(f'{outline_block["h1"]} {n}/{repeat_num}', expanded=True):
                            st.markdown(f"""
                            {outline_block_content_final}
                            """)
                    n += 1
                    # 添加分隔线来区分内容块
                    st.markdown("---")
                
                    # 如果启用了多模态图像处理，尝试为当前内容块找到相关图片
                    if st.session_state.get('enable_images', False):
                        try:
                            from utils.embedding_utils import search_similar_text
                            
                            # 使用文章内容块查找相关图片
                            similarity_threshold = 0.15  # 降低阈值以增加匹配成功率
                            
                            # 使用缓存的FAISS索引实例，但不强制刷新以避免删除索引
                            cached_faiss_index, _ = get_cached_resources(force_refresh=False)
                            
                            # 输出索引大小，帮助调试
                            index_size = cached_faiss_index.get_size()
                            logger.info(f"当前FAISS索引大小: {index_size}")
                            
                            if index_size == 0:
                                # 再尝试一次加载，可能在运行过程中有新的图片被处理
                                import time
                                logger.warning("等待3秒并重试加载FAISS索引...")
                                time.sleep(3)  # 等待几秒钟，确保任何正在进行的保存操作都已完成
                                # 仍然不使用force_refresh=True，因为这可能删除索引
                                cached_faiss_index, _ = get_cached_resources(force_refresh=False)
                                index_size = cached_faiss_index.get_size()
                                logger.info(f"重试后的FAISS索引大小: {index_size}")
                                
                                if index_size == 0:
                                    st.warning("FAISS索引中没有图片数据，无法进行图片匹配")
                                    continue
                                
                            # 搜索相似的图片描述
                            # 增加搜索结果数量，提高匹配成功率
                            # 增加k值以获取更多候选图片，因为部分图片可能已被使用
                            # 获取当前大纲的h1和h2组装成字符串进行搜索
                            outline_block_str = outline_block['h1'] + "".join([h2 for h2 in outline_block['h2']]) + outline_block_content_final
                            _, distances, matched_data = search_similar_text(outline_block_str, cached_faiss_index, k=10)
                            
                            # 检查是否找到相关图片
                            if matched_data and len(matched_data) > 0:
                                image_inserted = False
                                inserted_image_count = 0  # 初始化已插入图片计数器
                                
                                # 遍历所有匹配结果，找到第一个有效且未使用的图片
                                for i, (distance, data) in enumerate(zip(distances, matched_data)):
                                    # 检查是否是图片数据
                                    if isinstance(data, dict) and 'image_url' in data:
                                        # 获取图片URL
                                        image_url = data['image_url']
                                        
                                        # 检查图片是否已被使用
                                        if image_url in st.session_state.used_images:
                                            logger.info(f"跳过已使用的图片: {image_url[:50]}...")
                                            continue
                                            
                                        # 计算相似度分数 (1 - 标准化距离)
                                        similarity = 1.0 - min(distance / 2.0, 0.99)  # 标准化并反转
                                        
                                        # 只在相似度超过阈值时插入图片
                                        if similarity >= similarity_threshold:
                                            # 将图片URL添加到已使用集合
                                            st.session_state.used_images.add(image_url)
                                            
                                            # 检查是否需要下载图片到本地
                                            local_image_path = None
                                            if st.session_state.get('download_images', False):
                                                # 获取文章标题作为目录名
                                                article_title = st.session_state.get('article_title', 'untitled')
                                                save_dir = get_image_save_directory(article_title)
                                                
                                                # 下载图片
                                                local_image_path = download_image(image_url, save_dir)
                                           
                                            image_markdown = f"![图片]({image_url})\n\n"
                                            
                                            # 将图片插入到内容块前
                                            outline_block_content_final = image_markdown + outline_block_content_final
                                            logger.info(f"成功匹配图片，相似度: {similarity:.4f}，已使用图片数: {len(st.session_state.used_images)}")
                                            
                                            # 使用一个小的容器来显示信息，避免影响主要内容布局
                                            with st.container():
                                                st.info(f"为当前内容块插入了相关图片 (相似度: {similarity:.2f})")
                                                st.image(image_url)
                                                
                                            image_inserted = True
                                            
                                            # 计数已插入的图片数量
                                            inserted_image_count += 1
                                            
                                            # 如果已经插入了2张图片，则跳出循环
                                            if inserted_image_count >= 2:
                                                logger.info(f"已为当前内容块插入2张图片，停止搜索更多图片")
                                                break
                                            
                                if not image_inserted:
                                    logger.warning(f"未找到合适的未使用图片，已使用图片数: {len(st.session_state.used_images)}")
                                    # 可以选择在这里添加一个提示，告知用户未找到合适的图片
                        except Exception as e:
                            st.warning(f"查找相关图片时出错: {str(e)}")
                    
                    # 添加换行符，确保每个部分之间有适当的分隔
                    article_content += outline_block_content_final + '\n\n'
            # *************************** 自动保存原始文章到历史记录 *************************
            # 更新进度条到100%，表示文章已完成
            progress_bar.progress(100, text="文章生成完成！")
            
            original_article_id = None
            if article_content.strip():
                # 文章生成完成后，重置运行状态，允许再次提交
                st.session_state.run_status = False
                current_user = get_current_user()
                if current_user:
                    custom_style = st.session_state.get('custom_style', '')
                    # Record image parameters if enabled
                    image_enabled = st.session_state.get('enable_images', False)
                    
                    original_record = add_history_record(
                        current_user, 
                        outline_summary_json['title'], 
                        article_content, 
                        summary=outline_summary_json.get('summary', ''), 
                        model_type=model_type, 
                        model_name=model_name, 
                        spider_num=spider_num, 
                        custom_style=custom_style,
                        is_transformed=False,
                        image_enabled=image_enabled,
                    )
                    original_article_id = original_record.get('id')
                    st.success(f"原始文章已自动保存到历史记录中。")
                    # 删除faiss索引
                    try:
                        if os.path.exists('data/faiss/index.faiss'):
                            os.remove('data/faiss/index.faiss')
                        if os.path.exists('data/faiss/index_data.pkl'):
                            os.remove('data/faiss/index_data.pkl')
                        logger.info("文章生成完成后成功删除FAISS索引文件")
                    except Exception as e:
                        logger.error(f"删除FAISS索引文件失败: {str(e)}")

            # *************************** 转换白话文并保存 *************************
            if convert_to_simple and article_content.strip() and original_article_id is not None:
                transformed_article_content = ""
                with st.status("正在转换白话文..."):
                    try:
                        transformed_article_content = chat(article_content, pt.CONVERT_2_SIMPLE, model_type=model_type, model_name=model_name)
                        st.success("白话文转换完成！")
                    except ConnectionError as e:
                        st.error(f"白话文转换错误: {str(e)}")
                    except Exception as e:
                        st.error(f"白话文转换发生未知错误: {str(e)}")
                
                if transformed_article_content.strip(): # Save only if transformation was successful
                    current_user = get_current_user() # Re-get user just in case
                    if current_user:
                        custom_style = st.session_state.get('custom_style', '')
                        # Find the transformation name for CONVERT_2_SIMPLE from settings
                        transformation_name_for_simple = "白话文" # Default fallback
                        for name, prompt_template in ARTICLE_TRANSFORMATIONS.items():
                            if prompt_template == pt.CONVERT_2_SIMPLE:
                                transformation_name_for_simple = name
                                break
                        
                        add_history_record(
                            current_user, 
                            f"{outline_summary_json['title']} ({transformation_name_for_simple})", 
                            transformed_article_content, 
                            summary=f"{outline_summary_json.get('summary', '')} ({transformation_name_for_simple} 版本)", 
                            model_type=model_type, 
                            model_name=model_name, 
                            spider_num=spider_num, 
                            custom_style=custom_style,
                            is_transformed=True,
                            original_article_id=original_article_id
                        )
                        article_content = transformed_article_content # Update article_content to the transformed version for download
                        st.success(f"{transformation_name_for_simple} 版本已自动保存到历史记录中。")
            elif convert_to_simple and not article_content.strip():
                st.warning("原始文章内容为空，无法进行白话文转换。")
            elif convert_to_simple and original_article_id is None:
                st.warning("未能保存原始文章，无法进行白话文转换并关联。")
            
            # *************************** 点击下载文章 *************************
            st.download_button(
                label="下载文章",
                data=article_content,
                file_name=f"{outline_summary_json['title']}.md",
                mime="text/markdown",
                key="download_generated_article"
            )
            
            # *************************** 转换为Bento风格网页并保存 *************************
            if st.session_state.get('convert_to_webpage', False) and article_content.strip() and original_article_id is not None:
                webpage_content = ""
                with st.status("正在转换为Bento风格网页..."):
                    try:
                        # 使用新的Prompt模板生成网页内容
                        webpage_content = chat(f"附件文档内容:\n\n{article_content}", pt.BENTO_WEB_PAGE, model_type=model_type, model_name=model_name)
                        st.success("Bento风格网页转换完成！")
                    except ConnectionError as e:
                        st.error(f"网页转换错误: {str(e)}")
                    except Exception as e:
                        st.error(f"网页转换发生未知错误: {str(e)}")
                
                if webpage_content.strip(): # 仅在转换成功时执行
                    current_user = get_current_user()
                    if current_user:
                        transformation_name_for_webpage = "Bento网页"
                        
                        # 保存到历史记录
                        # 从原始文章记录中获取图片相关参数
                        # 首先加载原始文章的记录
                        history = load_user_history(current_user)
                        original_record = None
                        for record in history:
                            if record.get('id') == original_article_id:
                                original_record = record
                                break
                        
                        # 获取原始文章的图片参数
                        image_enabled = original_record.get('image_enabled', False) if original_record else False
                        # 不再需要记录task_id和阈值，使用默认值
                        image_task_id = None
                        image_similarity_threshold = 0.5 if image_enabled else None
                        image_max_count = 10 if image_enabled else None
                        
                        add_history_record(
                            current_user, 
                            f"{outline_summary_json['title']} ({transformation_name_for_webpage})", 
                            webpage_content, 
                            summary=f"{outline_summary_json.get('summary', '')} ({transformation_name_for_webpage} 版本)", 
                            model_type=model_type, 
                            model_name=model_name, 
                            spider_num=spider_num, 
                            custom_style=custom_style,
                            is_transformed=True,
                            original_article_id=original_article_id,
                            image_task_id=image_task_id,
                            image_enabled=image_enabled,
                            image_similarity_threshold=image_similarity_threshold,
                            image_max_count=image_max_count
                        )
                        st.success(f"{transformation_name_for_webpage} 版本已自动保存到历史记录中。")

                        # 生成唯一文件名
                        html_filename = f"{outline_summary_json['title'].replace(' ', '_')}.html"
                        
                        # 导入保存HTML的函数
                        from utils.history_utils import save_html_to_user_dir
                        
                        # 获取当前用户
                        current_user = get_current_user()
                        
                        # 保存HTML内容到文件并获取URL路径
                        _, url_path = save_html_to_user_dir(current_user, webpage_content, html_filename)
                        
                        # 生成可访问的URL
                        base_url = HTML_NGINX_BASE_URL  # 根据nginx配置调整
                        article_url = f"{base_url}{url_path}"

                        # 显示预览链接
                        st.markdown(f"[点击预览网页效果]({article_url})")

                        # 提供HTML文件下载
                        st.download_button(
                            label="下载网页文件",
                            data=webpage_content,
                            file_name=f"{outline_summary_json['title']}.html",
                            mime="text/html",
                            key="download_generated_webpage"
                        )

            elif st.session_state.get('convert_to_webpage', False) and not article_content.strip():
                st.warning("原始文章内容为空，无法进行网页转换。")
            elif st.session_state.get('convert_to_webpage', False) and original_article_id is None:
                st.warning("未能保存原始文章，无法进行网页转换并关联。")

# Check if we need to rerun
if st.session_state.get('trigger_rerun', False):
    # Reset the flag
    st.session_state['trigger_rerun'] = False
    # 设置rerun标志，用于区分正常页面加载和rerun
    st.session_state['_is_rerun'] = True
    st.rerun()
else:
    # 重置rerun标志
    st.session_state['_is_rerun'] = False
    # Call the main function
    main()