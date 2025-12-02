# -*- coding: utf-8 -*-
"""
SupaWriter 登录页面 V2
支持多种登录方式：邮箱密码、Google OAuth、微信OAuth
"""

import streamlit as st
from utils.auth_v2 import AuthService


def show_email_login_form():
    """显示邮箱登录表单"""
    st.markdown("### 📧 邮箱登录")
    
    with st.form("email_login_form", clear_on_submit=False):
        email = st.text_input("邮箱地址", placeholder="your@email.com")
        password = st.text_input("密码", type="password", placeholder="请输入密码")
        remember_me = st.checkbox("记住我（30天内自动登录）", value=True)
        
        submit = st.form_submit_button("🔐 登录", use_container_width=True, type="primary")
        
        if submit:
            if not email or not password:
                st.error("请输入邮箱和密码")
            else:
                success, message, user = AuthService.login_with_email(email, password, remember_me)
                if success:
                    st.success(message)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(message)
    
    # 注册提示
    st.info("💡 如需注册账号，请访问官网进行注册")


def show_oauth_buttons():
    """显示OAuth登录按钮"""
    st.markdown("### 🔐 第三方登录")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Google登录
        if st.button("🔐 Google 登录", type="secondary", use_container_width=True):
            try:
                st.login("google")
            except Exception as e:
                st.error(f"Google 登录失败: {e}")
    
    with col2:
        # 微信登录
        try:
            from utils.wechat_oauth import init_wechat_oauth, wechat_login_flow
            
            wechat_oauth = init_wechat_oauth()
            if wechat_oauth:
                # 检查是否有微信回调
                query_params = st.query_params
                code = query_params.get("code")
                
                if code and 'wechat_user_info' not in st.session_state:
                    # 处理微信登录回调
                    with st.spinner("正在获取微信用户信息..."):
                        success, token_data = wechat_oauth.get_access_token(code)
                        if success:
                            access_token = token_data.get('access_token')
                            openid = token_data.get('openid')
                            success, user_info = wechat_oauth.get_user_info(access_token, openid)
                            
                            if success:
                                # 使用新的认证服务登录
                                success, message, user = AuthService.login_with_wechat(user_info)
                                if success:
                                    st.query_params.clear()
                                    st.success(message)
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error(message)
                
                # 显示微信登录按钮
                if st.button("🔐 微信登录", type="secondary", use_container_width=True):
                    import hashlib
                    import time
                    state = hashlib.md5(str(time.time()).encode()).hexdigest()
                    st.session_state.wechat_state = state
                    auth_url = wechat_oauth.get_authorization_url(state)
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
            else:
                st.button("🔐 微信登录", type="secondary", use_container_width=True, disabled=True)
                st.caption("⚠️ 微信登录未配置")
        except Exception as e:
            st.button("🔐 微信登录", type="secondary", use_container_width=True, disabled=True)
            st.caption(f"❌ 微信登录错误")


def app():
    """登录页面主函数"""
    
    # 添加现代化样式
    st.markdown("""
    <style>
    .login-container {
        max-width: 500px;
        margin: 2rem auto;
        padding: 2rem;
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.15) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 检查是否已登录
    if AuthService.is_authenticated():
        user = AuthService.get_current_user()
        display_name = user.get('display_name') or user.get('username') if user else "用户"
        
        st.success(f"✅ 已登录：{display_name}")
        
        # 显示用户头像（如果有）
        if user and user.get('avatar_url'):
            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(user['avatar_url'], width=80)
            with col2:
                st.write(f"**{display_name}**")
                if user.get('email'):
                    st.caption(f"📧 {user['email']}")
                
                login_method = st.session_state.get('login_method', 'unknown')
                method_icons = {
                    'email': '📧 邮箱账号',
                    'google': '🔐 Google账号',
                    'wechat': '🔐 微信账号',
                    'cookie': '🍪 自动登录'
                }
                st.caption(method_icons.get(login_method, '🔐 已登录'))
        
        if st.button("🚪 退出登录", type="secondary"):
            AuthService.logout()
            st.rerun()
        
        return True
    
    # 未登录，显示登录界面
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        text-align: center;
    ">
        <h1 style="color: white; margin: 0; font-size: 2.5rem;">
            👋 欢迎使用 SupaWriter
        </h1>
        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            AI驱动的智能写作平台
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 显示登录表单
    show_email_login_form()
    
    st.markdown("---")
    
    # OAuth登录按钮
    show_oauth_buttons()
    
    return False


if __name__ == "__main__":
    app()
