import streamlit as st
import openai
import sys
import logging
import datetime
import re
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from settings import LLM_MODEL, LLM_PROVIDERS
from utils.config_manager import get_config
from utils.history_utils import (
    list_chat_sessions, create_chat_session, load_chat_session, 
    save_chat_session, update_chat_title, delete_chat_session
)

@require_auth
def main():
    # 获取当前用户
    current_user = get_current_user()
    if not current_user:
        st.error("请先登录")
        return
        
    # 初始化聊天相关的会话状态
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = None
        
    if "chat_title" not in st.session_state:
        st.session_state.chat_title = "新对话"
        
    # 自动更新聊天标题函数
    def update_chat_title_from_content():
        if st.session_state.messages and len(st.session_state.messages) > 0:
            # 获取第一条用户消息的内容
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    content = msg["content"]
                    # 截取前10个字符作为标题
                    new_title = content[:10] + ('...' if len(content) > 10 else '')
                    # 更新标题
                    if new_title != st.session_state.chat_title:
                        st.session_state.chat_title = new_title
                        if st.session_state.active_chat_id:
                            update_chat_title(current_user, st.session_state.active_chat_id, new_title)
                    break

    def handle_delete_session(session_id):
        delete_chat_session(current_user, session_id)
        # 如果删除的是当前活动聊天，重置状态
        if st.session_state.active_chat_id == session_id:
            st.session_state.active_chat_id = None
            st.session_state.messages = []
            st.session_state.chat_title = "新对话"
        st.rerun()
        
    def convert_conversation_to_markdown():
        """将当前对话转换为Markdown格式"""
        if not st.session_state.messages:
            return "# 空对话\n\n当前没有对话内容。"
            
        markdown_content = f"# {st.session_state.chat_title}\n\n"
        markdown_content += f"*生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        
        for idx, msg in enumerate(st.session_state.messages):
            if msg["role"] == "user":
                markdown_content += f"## 👤 用户\n\n{msg['content']}\n\n"
            else:  # assistant
                # 如果有 thinking 内容，也包含在导出中
                if msg.get('thinking'):
                    markdown_content += f"## 🤖 AI助手\n\n### 💭 思考过程\n\n{msg['thinking']}\n\n### 📝 回复内容\n\n{msg['content']}\n\n"
                else:
                    markdown_content += f"## 🤖 AI助手\n\n{msg['content']}\n\n"
                
        return markdown_content
    
    
    # 在侧边栏添加模型选择和清空按钮
    with st.sidebar:
        # 聊天历史部分
        st.header("聊天历史")
        
        # 使用默认按钮样式
        
        # 新建聊天按钮
        if st.button("➕ 新建聊天", key="new_chat", type="primary", use_container_width=True):
            # 保存当前聊天（如果有且消息数量大于等于2条）
            if st.session_state.active_chat_id and len(st.session_state.messages) >= 2:
                save_chat_session(
                    current_user, 
                    st.session_state.active_chat_id, 
                    st.session_state.messages,
                    st.session_state.chat_title
                )
            
            # 重置内存状态以开始新聊天，而不是立即创建持久化记录
            st.session_state.active_chat_id = None
            st.session_state.messages = []
            st.session_state.chat_title = "新对话"
            st.rerun()
        
        # 获取聊天历史列表
        chat_sessions = list_chat_sessions(current_user)
        
        # 显示当前活动聊天的标题
        if st.session_state.active_chat_id and st.session_state.chat_title != "新对话":
            st.caption(f"当前对话: {st.session_state.chat_title[:15] + ('...' if len(st.session_state.chat_title) > 15 else '')}")
        
        # 使用可折叠的历史对话列表
        with st.expander("历史对话列表", expanded=False):
            if not chat_sessions:
                st.info("暂无聊天记录")
            else:
                # 显示历史对话数量
                st.caption(f"共 {len(chat_sessions)} 条对话记录")
                
                # 添加CSS样式，专注于“新建聊天”按钮
                st.markdown("""
                <style>
                /* --- “新建聊天”按钮 --- */
                div.stButton > button:has(div:contains("新建聊天")) {
                    background-color: #007AFF !important;
                    color: white !important;
                    border-radius: 20px !important;
                    border: none !important;
                    font-weight: bold !important;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # 使用st.container和st.columns构建清晰的卡片布局
                for session in chat_sessions:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
                        
                        with col1:
                            # 格式化日期和标题
                            try:
                                updated_at = datetime.datetime.fromisoformat(session['updated_at'])
                                date_str = updated_at.strftime("%Y-%m-%d %H:%M")
                            except:
                                date_str = "未知时间"
                            display_title = session['title'][:20] + ('...' if len(session['title']) > 20 else '')
                            
                            # 使用Markdown正确渲染HTML标签
                            st.markdown(f"**{display_title}**<br><small>{date_str} - {session['message_count']} 条消息</small>", unsafe_allow_html=True)

                        with col2:
                            if st.button(":material/open_in_new:", key=f"open_{session['id']}", help="打开对话"):
                                if st.session_state.active_chat_id and len(st.session_state.messages) >= 2:
                                    save_chat_session(current_user, st.session_state.active_chat_id, st.session_state.messages, st.session_state.chat_title)
                                chat_data = load_chat_session(current_user, session['id'])
                                if chat_data:
                                    st.session_state.active_chat_id = session['id']
                                    st.session_state.messages = chat_data['messages']
                                    st.session_state.chat_title = chat_data['title']
                                    st.rerun()
                        
                        with col3:
                            st.button(":material/delete_forever:", key=f"delete_{session['id']}", help="删除该对话", on_click=handle_delete_session, args=(session['id'],))
        
        # 清空对话按钮
        if st.button("🚮 清空当前对话", type="secondary", use_container_width=True):
            # 清空消息
            st.session_state.messages = []
            # 如果有活动聊天ID，不需要保存空对话
            # 直接重新加载页面
            st.rerun()
            
        # 下载当前对话按钮
        if st.session_state.messages and len(st.session_state.messages) > 0:
            markdown_content = convert_conversation_to_markdown()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"对话_{st.session_state.chat_title[:10]}_{timestamp}.md"
            st.download_button(
                label="📥 下载当前对话",
                data=markdown_content,
                file_name=filename,
                mime="text/markdown",
                type="secondary",
                use_container_width=True
            )
        
        # 添加分隔线
        st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("超能AI助手🌟", divider='rainbow')
    st.caption("""
               超能写手AI一站式平台，致力于提高撰写文章的各个环节效率，包含生成式LLM大模型和相关智能AI工具。
               
               Super Writer AI is a one-stop platform dedicated to improving the efficiency of all aspects of article writing, including generative LLM large models and related intelligent AI tools."""
               )
    # st.info(f"""
    #     🆕简介：当前页面接入了大模型AI助手，请和我对话吧！

    #     ⚠️注意：本网站为测试版，部分功能可能存在问题，且会随时关闭！
    #     """)
    # 删除清空按钮，将在模型信息旁边显示
    # with st.container(height=600):

    from settings import LLM_MODEL
    import openai
    import logging
    import sys

    # 配置日志
    logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                      handlers=[logging.StreamHandler(sys.stdout)])
    logger = logging.getLogger('home')

    # 使用全局模型设置
    try:
        # 从配置管理器获取全局模型设置
        config = get_config()
        global_settings = config.get('global_model_settings', {})
        
        if not global_settings:
            # 如果全局设置不存在，使用第一个可用模型作为后备
            model_type = list(LLM_MODEL.keys())[0]
            model_name = LLM_MODEL[model_type]['model'][0] if isinstance(LLM_MODEL[model_type]['model'], list) else LLM_MODEL[model_type]['model']
            st.warning(f"全局模型未配置，已自动选择: {model_type}/{model_name}", icon="⚠️")
        else:
            model_type = global_settings.get('provider')
            model_name = global_settings.get('model_name')
        
        model_api_key = LLM_MODEL[model_type]['api_key']
        model_base_url = LLM_MODEL[model_type]['base_url']
        
        logger.info(f"使用模型: {model_type} - {model_name}")
        client = openai.OpenAI(api_key=model_api_key, base_url=model_base_url)
    except Exception as e:
        st.error(f"模型配置错误: {str(e)}")
        logger.error(f"模型配置错误: {str(e)}")
        client = None

    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # 创建简洁的顶部标题区域
    with st.container():
        # 使用两列布局：标题和当前模型信息
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("### 💬 AI 助手对话")
            
        # 显示当前聊天标题（只读）
        if st.session_state.active_chat_id and st.session_state.chat_title != "新对话":
            st.caption(f"当前对话: {st.session_state.chat_title}")
        
        with col2:
            # 显示当前使用的全局模型
            st.info(f"{model_type} - {model_name}", icon="📡")
    
    # 添加轻量级分隔线
    st.markdown("<hr style='margin: 0.5em 0; opacity: 0.3'>", unsafe_allow_html=True)

    # 修复 chat_input 在长文本时高度无限增长的问题：限制最大高度并启用滚动
    st.markdown(
        """
        <style>
        /* 限制聊天输入框的最大高度，超出部分滚动显示 */
        div[data-testid="stChatInput"] textarea,
        div[data-baseweb="textarea"] textarea {
            max-height: 140px !important;
            overflow: auto !important;
            resize: none !important;
        }
        /* 容器也限制高度，防止整体被撑大 */
        div[data-testid="stChatInput"] > div {
            max-height: 160px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 直接显示聊天消息，不使用固定高度容器
    if not st.session_state.messages:
        # 如果消息为空，显示简洁的欢迎信息
        st.info("欢迎使用 AI 助手！请在下方输入框中提问。")
    else:
        # 显示所有聊天消息
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                # 如果是助手消息且包含 thinking 内容，使用可折叠显示
                if message["role"] == "assistant" and message.get("thinking"):
                    with st.expander("💭 查看思考过程", expanded=False):
                        st.markdown(message["thinking"])
                    st.markdown(message["content"])
                else:
                    st.markdown(message["content"])
    
    # 添加轻量级分隔线和空间，使输入区域更明显
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    
    # 优化输入区域提示
    if prompt := st.chat_input("输入您的问题，按回车发送..."):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 自动更新聊天标题
        update_chat_title_from_content()
        
        if client is None:
            with st.chat_message("assistant"):
                st.error("无法连接到AI模型，请检查配置")
            st.session_state.messages.append({"role": "assistant", "content": "无法连接到AI模型，请检查配置"})
        else:
            try:
                with st.chat_message("assistant"):
                    thinking_placeholder = st.empty()
                    message_placeholder = st.empty()
                    full_response = ""
                    thinking_content = ""
                    
                    # 创建消息列表，确保格式正确（只包含 content，不包含 thinking）
                    messages = []
                    for m in st.session_state.messages:
                        if m["role"] == "assistant":
                            messages.append({"role": "assistant", "content": m["content"]})
                        else:  # user
                            messages.append({"role": "user", "content": m["content"]})
                    
                    try:
                        # 确保在使用前定义变量，避免未赋值引用
                        stream = None
                        if model_type == 'openai':
                            stream = client.chat.completions.create(
                                model=model_name,
                                messages=messages,
                                stream=True,
                                max_completion_tokens=8000,
                            )
                        else:
                            stream = client.chat.completions.create(
                                model=model_name,
                                messages=messages,
                                stream=True,
                                max_tokens=8000,
                            )
                        
                        # 处理流式响应
                        for chunk in stream:
                            if chunk.choices and len(chunk.choices) > 0:
                                delta = chunk.choices[0].delta
                                
                                # 检查是否有 reasoning_content 字段（deepseek、o1 等模型）
                                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                                    thinking_content += delta.reasoning_content
                                    # 实时显示思考过程
                                    with thinking_placeholder.container():
                                        with st.expander("💭 思考过程（实时）", expanded=True):
                                            st.markdown(thinking_content + "▌")
                                
                                # 处理常规内容
                                content = delta.content
                                if content is not None:
                                    full_response += content
                                    message_placeholder.markdown(full_response + "▌")
                        
                        # 从响应中提取可能的 XML 格式的 thinking 标签
                        # 支持 <think>、<thinking>、<thought> 等标签
                        if not thinking_content and full_response:
                            think_patterns = [
                                r'<think>(.*?)</think>',
                                r'<thinking>(.*?)</thinking>',
                                r'<thought>(.*?)</thought>'
                            ]
                            for pattern in think_patterns:
                                matches = re.findall(pattern, full_response, re.DOTALL)
                                if matches:
                                    thinking_content = '\n\n'.join(matches)
                                    # 从响应中移除 thinking 标签
                                    full_response = re.sub(pattern, '', full_response, flags=re.DOTALL).strip()
                                    break
                        
                        # 清空占位符并显示最终内容
                        thinking_placeholder.empty()
                        message_placeholder.empty()
                        
                        # 如果有 thinking 内容，使用可折叠显示
                        if thinking_content:
                            with thinking_placeholder.container():
                                with st.expander("💭 查看思考过程", expanded=False):
                                    st.markdown(thinking_content)
                        
                        # 显示最终响应
                        message_placeholder.markdown(full_response)
                        
                        # 添加下载按钮，用于保存单条回复
                        if full_response:
                            # 为文件名生成一个唯一的时间戳
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            download_content = full_response
                            if thinking_content:
                                download_content = f"## 💭 思考过程\n\n{thinking_content}\n\n## 📝 回复内容\n\n{full_response}"
                            st.download_button(
                                label="📥 保存此条回复",
                                data=download_content,
                                file_name=f"ai_response_{timestamp}.md",
                                mime="text/markdown",
                                key=f"download_{timestamp}" # 使用唯一key避免冲突
                            )
                    except Exception as e:
                        error_msg = f"AI响应错误: {str(e)}"
                        logger.error(error_msg)
                        thinking_placeholder.empty()
                        message_placeholder.error(error_msg)
                        full_response = error_msg
                        
                # 添加助手回复到历史记录（包含 thinking 内容）
                message_data = {"role": "assistant", "content": full_response}
                if thinking_content:
                    message_data["thinking"] = thinking_content
                st.session_state.messages.append(message_data)
                
                # --- 延迟创建和保存逻辑 ---
                # 只有当对话至少有一轮（用户提问+AI回答）时才保存
                if len(st.session_state.messages) >= 2:
                    # 如果这是一个全新的、还未保存的对话
                    if not st.session_state.active_chat_id:
                        # 先创建持久化记录，获取ID
                        new_chat = create_chat_session(current_user, st.session_state.chat_title)
                        st.session_state.active_chat_id = new_chat['id']
                        # 立即保存第一轮对话
                        save_chat_session(
                            current_user,
                            st.session_state.active_chat_id,
                            st.session_state.messages,
                            st.session_state.chat_title
                        )
                        st.rerun() # 重新运行以更新侧边栏的历史记录
                    else:
                        # 对于已存在的对话，直接更新
                        save_chat_session(
                            current_user,
                            st.session_state.active_chat_id,
                            st.session_state.messages,
                            st.session_state.chat_title
                        )
            except Exception as e:
                st.error(f"处理对话时出错: {str(e)}")
                logger.error(f"处理对话时出错: {str(e)}")
                st.session_state.messages.append({"role": "assistant", "content": f"处理对话时出错: {str(e)}"})


# Call the main function
main()