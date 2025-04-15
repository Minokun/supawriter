from utils.searxng_utils import auto_run
import streamlit as st
import json, sys
from utils.searxng_utils import Search, llm_task, chat, parse_outline_json
import utils.prompt_template as pt
import concurrent.futures
import asyncio
import nest_asyncio
from settings import LLM_MODEL
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import add_history_record, load_user_history

@require_auth
def main():


    # 应用nest_asyncio
    nest_asyncio.apply()
    # 切换到ProactorEventLoop
    if st.runtime.exists() and sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    if "run_status" not in st.session_state:
        st.session_state.run_status = False

    with st.sidebar:
        st.title("超级写手配置项：")
        model_type = st.selectbox('请选择模型供应商', list(LLM_MODEL.keys()), key=1)
        model_name = st.selectbox('请选择模型名称', LLM_MODEL[model_type]['model'], key=0)
        with st.form(key='my_form'):
            text_input = st.text_input(label='请填写文章的主题', help='文章将全部围绕该主题撰写，主题越细，文章也越详细',
                                       value='')
            col1, col2 = st.columns(2)
            with col1:
                write_type = st.selectbox('写作模式', ['简易', '详细'], key=2)
            with col2:
                spider_num = st.slider(label='爬取网页数量', help='（默认5，数量越多时间越长！)', min_value=1, max_value=25, key=3,
                                   value=15)
            submit_button = st.form_submit_button(label='执行', disabled=st.session_state.run_status)

    st.caption('SuperWriter by WuXiaokun. ')
    st.subheader("超级写手🤖", divider='rainbow')
    
    # Create tabs for main functionality and history
    main_tab, history_tab = st.tabs(["写作", "历史记录"])
    
    # Create placeholders only for the main tab content
    with main_tab:
        placeholder_status = st.container()
        placeholder_progress = st.empty()
        placeholder_preview = st.empty()

    with main_tab:
        st.info("""

            🆕简介：本应用是利用LLM+搜索引擎+爬虫开发的自动撰写文章的机器人，只需要填写文章主题,程序会自动书写大纲并逐一撰写文章。

            ⚠️注意：在左侧填写文章主题后，点击执行按钮，整个过程可能需要5分钟-30分钟不到，点击执行后请不要关闭本页面，等待完成后下载文章，刷新或关闭将不会保存。

            1. 模型默认deepseek，效果最好，速度最快，该选项可以不用修改。
            2. 填写文章主题为你想要撰写的文章主题
            3. 写作模式，简易模式将只搜索，不爬取网页内容。详细模式将搜索并爬取网页内容，爬取网页数量为默认15，数量越多时间越长！

            """)

        # Initialize variables
        search_result = []
        outline_summary = ""
        outline_summary_json = {"title": "", "summary": "", "content_outline": []}
        outlines = ""
        article_content = ''

        if submit_button:
            my_bar = placeholder_status.progress(0, text="Operation in progress. Please wait.")
            # *************************** 搜索引擎开始搜索并抓取网页内容 ***************************
            my_bar.progress(10, text="Spider in progress. Please wait...")
            col1, col2 = st.columns(2)
            with col1:
                st.caption("当前进度：")
                placeholder_progress = st.empty()
            with col2:
                st.caption("过程详情预览：")
                placeholder_preview = st.empty()
            with placeholder_progress.container():
                with st.status("抓取网页内容"):
                    # 开一个线程运行函数
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(Search(result_num=spider_num).get_search_result, text_input, False if write_type == '简易' else True)
                        for future in concurrent.futures.as_completed([future]):
                            search_result = future.result()
            with st.popover("查看搜索详细..."):
                for i in search_result:
                    title = i.get('title')
                    url = i.get('url')
                    st.markdown(f"""
                    标题：{title} 
                    链接：{url}
                    """)
            # *************************** 生成大纲 *************************
            my_bar.progress(30, text="Spider Down! Now generate the outline...")
            with st.status("生成大纲"):
                try:
                    outlines = llm_task(search_result, text_input, pt.ARTICLE_OUTLINE_GEN, model_type=model_type, model_name=model_name)
                except ConnectionError as e:
                    st.error(f"错误: {str(e)}")
                    st.stop()  # 停止程序执行

            # *************************** 融合大纲 *************************
            my_bar.progress(60, text="Integrate article outline...")
            with st.status("融合大纲"):
                try:
                    outline_summary = chat(f'<topic>{text_input}</topic> <content>{outlines}</content>', pt.ARTICLE_OUTLINE_SUMMARY, model_type=model_type, model_name=model_name)
                except ConnectionError as e:
                    st.error(f"错误: {str(e)}")
                    st.stop()  # 停止程序执行
        
            # 使用改进的JSON解析函数
            outline_summary_json = parse_outline_json(outline_summary, text_input)
            # Ensure the required keys exist
            if 'title' not in outline_summary_json:
                outline_summary_json['title'] = text_input
            if 'summary' not in outline_summary_json:
                outline_summary_json['summary'] = ""
            if 'content_outline' not in outline_summary_json:
                outline_summary_json['content_outline'] = []
                
        # Only show outline if it's not empty
        if outline_summary_json.get('title') or outline_summary_json.get('summary') or outline_summary_json.get('content_outline'):
            with placeholder_preview.container():
                with st.popover("查看大纲"):
                    st.json(outline_summary_json)
                st.markdown(f"""
                #### {outline_summary_json['title']} 
        
                > {outline_summary_json['summary']}
                --------------------------
                """)

        # *************************** 书写文章 *************************
        if 'content_outline' in outline_summary_json and outline_summary_json['content_outline']:
            repeat_num = len(outline_summary_json['content_outline'])
            my_bar_article_start = 100 - repeat_num*2
            my_bar.progress(my_bar_article_start, text="Writing article...")
        with st.spinner("书写文章..."):
            n = 1
            # Reset article_content if it's already in the submit_button block
            article_content = ''
            if 'content_outline' in outline_summary_json and outline_summary_json['content_outline']:
                for outline_block in outline_summary_json['content_outline']:
                    my_bar.progress(my_bar_article_start + n*2, text=f"正在撰写  {outline_block['h1']}  {n}/{repeat_num}")
                
                    # 根据抓取的内容资料生成内容
                    if n == 1:
                        # 第一章不要包含h1和h2标题
                        question = f'<完整大纲>{outline_summary}</完整大纲> 请根据上述信息，书写出以下内容 >>> {outline_block} <<<，注意不要包含任何标题，直接开始正文内容',
                        outline_block_content = llm_task(search_result, question=question,
                                                      output_type=pt.ARTICLE_OUTLINE_BLOCK, model_type=model_type, model_name=model_name)
                        outline_block_content_final = chat(
                            f'<完整大纲>{outline_summary}</完整大纲> <相关资料>{outline_block_content}</相关资料> 请根据上述信息，书写大纲中的以下这部分内容：{outline_block}，注意不要包含任何标题（不要包含h1和h2标题），直接开始正文内容',
                            pt.ARTICLE_OUTLINE_BLOCK, model_type=model_type, model_name=model_name)
                    else:
                        question = f'<完整大纲>{outline_summary}</完整大纲> 请根据上述信息，书写出以下内容 >>> {outline_block} <<<',
                        outline_block_content = llm_task(search_result, question=question,
                                                      output_type=pt.ARTICLE_OUTLINE_BLOCK, model_type=model_type, model_name=model_name)
                        outline_block_content_final = chat(
                            f'<完整大纲>{outline_summary}</完整大纲> <相关资料>{outline_block_content}</相关资料> 请根据上述信息，书写大纲中的以下这部分内容：{outline_block}',
                            pt.ARTICLE_OUTLINE_BLOCK, model_type=model_type, model_name=model_name)
            
                    with st.popover(f'{outline_block["h1"]} {n}/{repeat_num}', use_container_width=True):
                        st.markdown(f"""
                        {outline_block_content_final}
                        """)
                    n += 1
                
                    # 添加换行符，确保每个部分之间有适当的分隔
                    article_content += outline_block_content_final + '\n\n'
            # *************************** 自动保存文章到历史记录 *************************
            if article_content.strip():
                current_user = get_current_user()
                if current_user:
                    # Add to history records
                    add_history_record(current_user, text_input, article_content, model_type=model_type, model_name=model_name, write_type=write_type, spider_num=spider_num)
                    st.success(f"文章已自动保存到历史记录中，可在\"历史记录\"标签页查看")
            
                # *************************** 点击下载文章 *************************
                st.download_button(
                    label="下载文章",
                    data=article_content,
                    file_name=f'{text_input}.md',
                    mime="text/markdown",
                    key="download_generated_article"
                )

    # Display history records in the history tab
    with history_tab:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            st.error("无法获取当前用户信息")
        else:
            # Load user history
            history = load_user_history(current_user)
            
            if not history:
                st.info("暂无历史记录")
            else:
                # Display history in reverse chronological order (newest first)
                for record in reversed(history):
                    with st.expander(f"📝 {record['topic']} - {record['timestamp'][:16].replace('T', ' ')}"):
                        # 显示配置信息
                        st.markdown(f"**模型供应商**: {record.get('model_type', '-')}")
                        st.markdown(f"**模型名称**: {record.get('model_name', '-')}")
                        st.markdown(f"**写作模式**: {record.get('write_type', '-')}")
                        st.markdown(f"**爬取数量**: {record.get('spider_num', '-')}")
                        st.markdown("### 文章内容")
                        st.markdown(record["article_content"])

                        # 下载按钮
                        st.download_button(
                            label="下载文章",
                            data=record["article_content"],
                            file_name=f"{record['topic']}.md",
                            mime="text/markdown",
                            key=f"download_history_{record['id']}"
                        )
                        # 删除按钮
                        if st.button("删除此条记录", key=f"delete_{record['id']}"):
                            from utils.history_utils import delete_history_record
                            delete_history_record(current_user, record['id'])
                            st.rerun()

# Call the main function
main()