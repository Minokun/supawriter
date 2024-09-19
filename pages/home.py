import streamlit as st

st.set_page_config(page_title="奇融谷", page_icon="🚀", layout="wide")
st.sidebar.title("关于")
st.sidebar.info("""
    ©2024 苏州奇融谷技术有限责任公司 版权所有 (https://www.apuqi.com/)
""")
st.sidebar.header("联系我们")
with st.sidebar:
    st.markdown("""
        邮箱：apqchina@apuqi.com  
        地址: 苏州市相城区元和街道万里路88号3号楼  
        电话: 400-702-7002  
        ![联系二维码](https://www.apuqi.com/uploads/96bfb1e66d7c1a04f8240d64b7a9b99.jpg)
    """)
st.subheader("Dr.Q 奇博士🌟", divider='rainbow')
st.caption("""
           工业AI一站式平台，致力于提高工业制造中的各个环节效率，包含生成式LLM大模型和相关智能AI工具。
           
           The Industrial AI One-Stop Platform is dedicated to enhancing the efficiency of various industrial manufacturing processes, encompassing generative large language models (LLM) and related intelligent AI tools."""
           )
st.info("""

        🆕简介：当前页面接入了奇融谷AI助手，可以搜索互联网回答你的问题，也可以回答公司公章简介，请和我对话吧！

        ⚠️注意：因为接入了互联网搜索和阿普奇的知识库，搜索和爬取数据需要一些时间，请耐心等待。点击清空按钮重新开始对话。
        """)
if st.button("清空"):
    st.session_state.messages = []
# with st.container(height=600):

from settings import LLM_MODEL
import openai
client = openai.OpenAI(api_key=LLM_MODEL['fastgpt']['api_key'], base_url=LLM_MODEL['fastgpt']['base_url'])

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
            model='qwen1.5-chat',
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )
        response = st.write_stream(stream)

    # Add user message to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})