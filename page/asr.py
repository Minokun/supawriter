import streamlit as st
from utils.auth_decorator import require_auth

@require_auth
def main():

    st.title("语音识别")
    st.markdown("### 语音识别服务")
    
    # 使用iframe嵌入外部网页
    st.components.v1.iframe(
        src="http://10.10.10.96:8080/projects/?page=1",
        height=600,
        scrolling=True
    )
    
    # 显示使用提示
    st.info("如果嵌入页面无法正常显示，您也可以直接访问 [语音识别平台](http://10.10.10.96:8080/user/login/)")


# Call the main function
main()