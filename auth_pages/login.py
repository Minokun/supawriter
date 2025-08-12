import streamlit as st
from utils.auth import is_authenticated, logout

def app():
    st.title("欢迎使用 SupaWriter")

    # If already authenticated (OAuth or legacy), show status and logout
    if is_authenticated():
        try:
            if hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
                display_name = getattr(st.user, "name", None) or getattr(st.user, "email", "已登录")
                st.success(f"已登录为: {display_name}")
            else:
                st.success("已登录")
        except Exception:
            st.success("已登录")

        if st.button("退出登录"):
            logout()
            st.rerun()
        return True

    # Not authenticated: show OAuth login button
    st.info("使用第三方账号登录以继续")
    if st.button("使用账号登录", type="primary"):
        try:
            # Use Streamlit OAuth2 login
            st.login("google")
        except Exception as e:
            st.error(f"登录失败: {e}")

    return False
