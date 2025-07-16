import streamlit as st
import openai
import sys
import logging
import datetime
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from settings import LLM_MODEL, LLM_PROVIDERS
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
            
            # 创建新聊天
            new_chat = create_chat_session(current_user, "新对话")
            st.session_state.active_chat_id = new_chat['id']
            st.session_state.messages = []
            st.session_state.chat_title = new_chat['title']
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
                
                # 添加CSS样式使历史记录更美观
                st.markdown("""
                <style>
                /* 滚动容器样式 */
                .scroll-container {
                    max-height: 300px;
                    overflow-y: auto;
                    padding-right: 5px;
                    margin-bottom: 10px;
                    border-radius: 4px;
                }
                
                /* 自定义滚动条 */
                .scroll-container::-webkit-scrollbar {
                    width: 4px;
                }
                
                .scroll-container::-webkit-scrollbar-track {
                    background: #f1f1f1;
                    border-radius: 4px;
                }
                
                .scroll-container::-webkit-scrollbar-thumb {
                    background: #c1c1c1;
                    border-radius: 4px;
                }
                
                /* 时间标签样式 */
                .chat-time {
                    font-size: 0.7em;
                    color: #888;
                    margin: 0 0 2px 0;
                    padding: 0;
                }
                
                /* 历史记录按钮样式 */
                div.stButton > button {
                    background-color: #aaa19f;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.75em;
                    line-height: 1.2;
                    text-align: left;
                    white-space: normal;
                    height: auto;
                    min-height: 0;
                    margin: 0;
                }
                
                /* 新建聊天按钮样式 - 确保白色文字 */
                button[data-testid="baseButton-primary"]:has(div:contains("➕ 新建聊天")) {
                    color: white !important;
                }
                
                /* 移除按钮的悬停效果 */
                div.stButton > button:hover {
                    border: none;
                }
                
                /* 删除按钮样式 */
                div.stButton > button[data-testid="baseButton-secondary"] {
                    background-color: transparent;
                    padding: 2px;
                    min-height: 0;
                    height: auto;
                }
                
                /* 分隔线样式 */
                .chat-divider {
                    margin: 2px 0;
                    border-top: 1px solid #eee;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # 创建一个滑动区域来容纳历史对话
                st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
                for idx, session in enumerate(chat_sessions):
                    # 格式化日期时间
                    try:
                        updated_at = datetime.datetime.fromisoformat(session['updated_at'])
                        date_str = updated_at.strftime("%m-%d %H:%M")
                    except:
                        date_str = "未知时间"
                    
                    # 截取前15个字作为显示
                    display_title = session['title'][:15] + ('...' if len(session['title']) > 15 else '')
                    
                    # 使用按钮实现更紧凑的历史记录项
                    col1, col2 = st.columns([0.9, 0.1])
                    
                    with col1:
                        # 显示时间信息
                        st.markdown(f"<p class='chat-time'>{date_str}</p>", unsafe_allow_html=True)
                        
                        # 使用按钮但添加自定义样式
                        button_label = f"{display_title}\n{session['message_count']} 条消息"
                        if st.button(button_label, key=f"chat_{session['id']}", use_container_width=True):
                            
                            # 保存当前聊天（如果有且消息数量大于等于2条）
                            if st.session_state.active_chat_id and len(st.session_state.messages) >= 2:
                                save_chat_session(
                                    current_user, 
                                    st.session_state.active_chat_id, 
                                    st.session_state.messages,
                                    st.session_state.chat_title
                                )
                            
                            # 加载选中的聊天
                            chat_data = load_chat_session(current_user, session['id'])
                            if chat_data:
                                st.session_state.active_chat_id = session['id']
                                st.session_state.messages = chat_data['messages']
                                st.session_state.chat_title = chat_data['title']
                                st.rerun()
                    
                    # 删除按钮
                    with col2:
                        if st.button("🗑️", key=f"delete_{session['id']}", help="删除该对话"):
                            delete_chat_session(current_user, session['id'])
                            # 如果删除的是当前活动聊天，重置状态
                            if st.session_state.active_chat_id == session['id']:
                                st.session_state.active_chat_id = None
                                st.session_state.messages = []
                                st.session_state.chat_title = "新对话"
                            st.rerun()
                    
                    # 添加分隔线，除非是最后一项
                    if idx < len(chat_sessions) - 1:
                        st.markdown("<div class='chat-divider'></div>", unsafe_allow_html=True)
                
                # 关闭滚动容器
                st.markdown('</div>', unsafe_allow_html=True)
        
        # 添加分隔线
        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.header("模型设置")
        
        # 初始化会话状态
        if "selected_provider" not in st.session_state:
            st.session_state.selected_provider = LLM_PROVIDERS[0]
        
        # 选择供应商
        provider_options = LLM_PROVIDERS
        selected_provider = st.selectbox(
            "选择供应商",
            options=provider_options,
            index=provider_options.index(st.session_state.selected_provider) if st.session_state.selected_provider in provider_options else 0,
            key="provider_selector"
        )
        
        # 如果供应商变化，更新会话状态
        if selected_provider != st.session_state.selected_provider:
            st.session_state.selected_provider = selected_provider
            # 重置模型选择
            if "selected_model_index" in st.session_state:
                del st.session_state.selected_model_index
        
        # 获取选定供应商的模型列表
        try:
            available_models = st.secrets[selected_provider]['model']
            if not isinstance(available_models, list):
                available_models = [available_models]
                
            # 初始化选定模型索引
            if "selected_model_index" not in st.session_state:
                st.session_state.selected_model_index = 0
                
            # 选择具体模型
            selected_model_index = st.selectbox(
                "选择模型",
                options=range(len(available_models)),
                format_func=lambda i: available_models[i],
                index=st.session_state.selected_model_index if st.session_state.selected_model_index < len(available_models) else 0,
                key="model_selector"
            )
            
            # 更新选定模型索引
            if selected_model_index != st.session_state.selected_model_index:
                st.session_state.selected_model_index = selected_model_index
                # 重新加载页面以应用新模型
                st.rerun()
                
        except Exception as e:
            st.error(f"无法加载 {selected_provider} 的模型列表: {str(e)}")
            available_models = ["default_model"]
        
        # 清空对话按钮
        if st.button("🚮 清空当前对话", type="secondary", use_container_width=True):
            # 清空消息
            st.session_state.messages = []
            # 如果有活动聊天ID，不需要保存空对话
            # 直接重新加载页面
            st.rerun()
        
        # 添加分隔线
        st.markdown("<hr>", unsafe_allow_html=True)
        
        # 联系信息
        st.sidebar.title("关于")
        st.header("联系我们")
        st.info("""
            ©2024 Minokun
            邮箱：952718180@qq.com 
            地址: 四川省成都市  
            更多请搜索微信公众号: 坤塔 
        """)
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

    # 使用侧边栏中选择的模型
    try:
        # 获取选定的供应商
        provider = st.session_state.get("selected_provider", LLM_PROVIDERS[0])
        
        # 获取选定的模型索引
        model_index = st.session_state.get("selected_model_index", 0)
        
        # 获取模型列表
        available_models = st.secrets[provider]['model']
        if not isinstance(available_models, list):
            available_models = [available_models]
            
        # 确保索引有效
        if model_index >= len(available_models):
            model_index = 0
            
        # 获取具体模型名称
        model_name = available_models[model_index]
        
        # 获取API配置
        model_api_key = st.secrets[provider]['api_key']
        model_base_url = st.secrets[provider]['base_url']
        
        # 记录供应商信息便于显示
        model_type = provider
        
        logger.info(f"使用模型: {model_type} - {model_name}")
        logger.info(f"API基础URL: {model_base_url}")
        
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
            # 显示当前选择的模型信息
            if 'model_name' in locals() and 'model_type' in locals():
                st.info(f"{model_type} - {model_name}", icon="📡")
            else:
                st.info(f"已加载默认模型", icon="📡")
    
    # 添加轻量级分隔线
    st.markdown("<hr style='margin: 0.5em 0; opacity: 0.3'>", unsafe_allow_html=True)

    # 直接显示聊天消息，不使用固定高度容器
    if not st.session_state.messages:
        # 如果消息为空，显示简洁的欢迎信息
        st.info("欢迎使用 AI 助手！请在下方输入框中提问。")
        
        # 如果没有活动聊天，创建一个新聊天
        if not st.session_state.active_chat_id:
            new_chat = create_chat_session(current_user, "新对话")
            st.session_state.active_chat_id = new_chat['id']
            st.session_state.chat_title = new_chat['title']
    else:
        # 显示所有聊天消息
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
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
                    message_placeholder = st.empty()
                    full_response = ""
                    
                    # 创建消息列表，确保格式正确
                    messages = []
                    for m in st.session_state.messages:
                        if m["role"] == "assistant":
                            messages.append({"role": "assistant", "content": m["content"]})
                        else:  # user
                            messages.append({"role": "user", "content": m["content"]})
                    
                    try:
                        stream = client.chat.completions.create(
                            model=model_name,
                            messages=messages,
                            stream=True,
                            max_tokens=8000,
                        )
                        
                        # 处理流式响应
                        for chunk in stream:
                            if chunk.choices and len(chunk.choices) > 0:
                                content = chunk.choices[0].delta.content
                                if content is not None:
                                    full_response += content
                                    message_placeholder.markdown(full_response + "▌")
                        
                        # 显示最终响应
                        message_placeholder.markdown(full_response)
                    except Exception as e:
                        error_msg = f"AI响应错误: {str(e)}"
                        logger.error(error_msg)
                        message_placeholder.error(error_msg)
                        full_response = error_msg
                        
                # 添加助手回复到历史记录
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                # 保存聊天历史（只有当消息数量大于等于2条时才保存）
                if st.session_state.active_chat_id and len(st.session_state.messages) >= 2:
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