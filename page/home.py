import streamlit as st
from utils.auth_decorator import require_auth

@require_auth
def main():
    st.sidebar.title("关于")
    st.sidebar.info("""
        ©2024 Minokun 
    """)
    st.sidebar.header("联系我们")
    with st.sidebar:
        st.markdown("""
            邮箱：952718180@qq.com 
            地址: 四川省成都市  
            更多请搜索微信公众号: 坤塔 
        """)
    st.subheader("超能AI助手🌟", divider='rainbow')
    st.caption("""
               超能写手AI一站式平台，致力于提高撰写文章的各个环节效率，包含生成式LLM大模型和相关智能AI工具。
               
               Super Writer AI is a one-stop platform dedicated to improving the efficiency of all aspects of article writing, including generative LLM large models and related intelligent AI tools."""
               )
    st.info("""

        🆕简介：当前页面接入了Chatgpt大模型AI助手，请和我对话吧！

        ⚠️注意：本网站为测试版，部分功能可能存在问题，且会随时关闭！
        """)
    if st.button("清空"):
        st.session_state.messages = []
    # with st.container(height=600):

    from settings import LLM_MODEL
    import openai

    model_type = 'hs-deepseek'
    model_name = LLM_MODEL[model_type]['model'][0]
    model_api_key = LLM_MODEL[model_type]['api_key']
    model_base_url = LLM_MODEL[model_type]['base_url']
    client = openai.OpenAI(api_key=model_api_key, base_url=model_base_url)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            )
            response = st.write_stream(stream)

        # Add user message to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

# Call the main function
main()