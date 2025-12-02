import streamlit as st
from utils.auth import is_authenticated, logout, get_user_display_name

def app():
    st.title("欢迎使用 SupaWriter")

    # If already authenticated (OAuth or legacy), show status and logout
    if is_authenticated():
        display_name = get_user_display_name()
        
        # 显示用户信息和头像（如果是微信用户）
        col1, col2 = st.columns([1, 4])
        with col1:
            try:
                if 'wechat_user_info' in st.session_state:
                    headimgurl = st.session_state.wechat_user_info.get('headimgurl')
                    if headimgurl:
                        st.image(headimgurl, width=80)
                    else:
                        st.write("👤")
                else:
                    st.write("👤")
            except Exception:
                st.write("👤")
        
        with col2:
            st.success(f"已登录为: {display_name}")
            
            # 显示用户来源
            try:
                if 'wechat_user_info' in st.session_state:
                    st.caption("🔐 微信账号")
                elif hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
                    st.caption("🔐 Google 账号")
                else:
                    st.caption("🔐 本地账号")
            except Exception:
                pass

        if st.button("退出登录", type="secondary"):
            logout()
            st.rerun()
        return True

    # Not authenticated: show login options
    st.info("使用第三方账号登录以继续")
    
    # 创建两列布局
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔐 使用 Google 登录", type="primary", use_container_width=True):
            try:
                # Use Streamlit OAuth2 login
                st.login("google")
            except Exception as e:
                st.error(f"Google 登录失败: {e}")
    
    with col2:
        # 微信登录按钮
        try:
            from utils.wechat_oauth import init_wechat_oauth, wechat_login_flow
            
            wechat_oauth = init_wechat_oauth()
            if wechat_oauth:
                # 处理微信登录流程
                wechat_login_flow()
            else:
                # 微信未配置，显示禁用状态
                st.button("🔐 使用微信登录", type="secondary", use_container_width=True, disabled=True)
                st.caption("⚠️ 微信登录未配置")
        except Exception as e:
            st.button("🔐 使用微信登录", type="secondary", use_container_width=True, disabled=True)
            st.caption(f"❌ 微信登录错误: {e}")

    return False
