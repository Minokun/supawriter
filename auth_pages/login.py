import streamlit as st
from utils.auth import register_user, authenticate_user, is_authenticated, logout

def app():
    # Initialize session state for login page rerun trigger if not exists
    if "login_trigger_rerun" not in st.session_state:
        st.session_state.login_trigger_rerun = False
        
    if is_authenticated():
        st.success(f"已登录为: {st.session_state.user}")
        if st.button("退出登录"):
            logout()
            st.session_state.login_trigger_rerun = True
        return True
        
    # Check if we need to rerun
    if st.session_state.login_trigger_rerun:
        st.session_state.login_trigger_rerun = False
        st.rerun()
    
    st.title("欢迎使用 SupaWriter")
    
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            remember_me = st.checkbox("记住我", value=True, help="保持登录状态，下次访问无需重新登录")
            submit = st.form_submit_button("登录")
            
            if submit:
                if not username or not password:
                    st.error("请输入用户名和密码")
                else:
                    success, message = authenticate_user(username, password, remember_me=remember_me)
                    if success:
                        st.session_state.user = username
                        st.success(message)
                        # Directly rerun for immediate redirect after form submission
                        st.rerun()
                    else:
                        st.error(message)
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("用户名")
            new_email = st.text_input("邮箱 (可选)")
            new_password = st.text_input("密码", type="password")
            confirm_password = st.text_input("确认密码", type="password")
            submit = st.form_submit_button("注册")
            
            if submit:
                if not new_username or not new_password:
                    st.error("请输入用户名和密码")
                elif new_password != confirm_password:
                    st.error("两次输入的密码不一致")
                else:
                    success, message = register_user(new_username, new_password, new_email)
                    if success:
                        st.success(message)
                        st.info("请前往登录页面登录")
                    else:
                        st.error(message)
    
    return False
