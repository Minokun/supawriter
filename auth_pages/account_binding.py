# -*- coding: utf-8 -*-
"""
账号绑定管理页面
允许用户绑定或解绑Google、微信等第三方账号
允许为OAuth账号设置邮箱和密码
"""

import streamlit as st
from utils.auth_v2 import AuthService
from utils.account_binding import AccountBindingService


def show_bound_accounts(user_id: int):
    """显示已绑定的账号列表"""
    st.markdown("### 🔗 已绑定账号")
    
    bound_accounts = AccountBindingService.get_bound_accounts(user_id)
    
    if not bound_accounts:
        st.info("暂无绑定账号")
        return
    
    for account in bound_accounts:
        provider = account['provider']
        display_name = account['display_name']
        identifier = account['identifier']
        can_unbind = account['can_unbind']
        
        # 账号图标
        icons = {
            'email': '📧',
            'google': '🔐',
            'wechat': '🔐'
        }
        icon = icons.get(provider, '🔐')
        
        with st.container():
            col1, col2, col3 = st.columns([1, 3, 1])
            
            with col1:
                st.markdown(f"<div style='font-size: 2rem;'>{icon}</div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"**{display_name}**")
                st.caption(identifier)
            
            with col3:
                if can_unbind and account['type'] == 'oauth':
                    if st.button(f"解绑", key=f"unbind_{provider}_{identifier}", type="secondary"):
                        success, message = AccountBindingService.unbind_oauth_account(user_id, provider)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
            
            st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)


def show_bind_email_form(user_id: int):
    """显示邮箱和密码设置表单"""
    if AccountBindingService.can_login_with_email(user_id):
        return  # 已经有邮箱登录
    
    st.markdown("### 📧 设置邮箱登录")
    st.info("设置邮箱和密码后，您可以使用邮箱登录账号")
    
    with st.form("bind_email_form"):
        email = st.text_input("邮箱地址", placeholder="your@email.com")
        
        col1, col2 = st.columns(2)
        with col1:
            password = st.text_input("设置密码", type="password", placeholder="至少8个字符")
        with col2:
            confirm_password = st.text_input("确认密码", type="password", placeholder="再次输入密码")
        
        # 密码强度提示
        if password:
            if len(password) < 8:
                st.warning("⚠️ 密码至少8个字符")
            else:
                st.success("✅ 密码长度符合要求")
        
        submit = st.form_submit_button("💾 保存", use_container_width=True, type="primary")
        
        if submit:
            if not email or not password:
                st.error("请填写所有必填项")
            elif password != confirm_password:
                st.error("两次输入的密码不一致")
            elif len(password) < 8:
                st.error("密码至少8个字符")
            else:
                success, message = AccountBindingService.bind_email_and_password(user_id, email, password)
                if success:
                    st.success(message)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(message)


def show_bind_google_button(user_id: int):
    """显示绑定Google账号按钮"""
    if AccountBindingService.has_google_binding(user_id):
        return  # 已绑定Google
    
    st.markdown("### 🔐 绑定Google账号")
    st.info("绑定Google账号后，您可以使用Google登录")
    
    if st.button("🔐 绑定 Google 账号", type="primary", use_container_width=True):
        # 设置绑定标记
        st.session_state.binding_google = True
        try:
            st.login("google")
        except Exception as e:
            st.error(f"绑定失败: {e}")
            st.session_state.binding_google = False


def show_bind_wechat_button(user_id: int):
    """显示绑定微信账号按钮"""
    if AccountBindingService.has_wechat_binding(user_id):
        return  # 已绑定微信
    
    st.markdown("### 🔐 绑定微信账号")
    st.info("绑定微信账号后，您可以使用微信扫码登录")
    
    try:
        from utils.wechat_oauth import init_wechat_oauth
        
        wechat_oauth = init_wechat_oauth()
        if wechat_oauth:
            # 检查是否有微信回调
            query_params = st.query_params
            code = query_params.get("code")
            
            if code and st.session_state.get('binding_wechat', False):
                # 处理微信绑定回调
                with st.spinner("正在获取微信用户信息..."):
                    success, token_data = wechat_oauth.get_access_token(code)
                    if success:
                        access_token = token_data.get('access_token')
                        openid = token_data.get('openid')
                        success, user_info = wechat_oauth.get_user_info(access_token, openid)
                        
                        if success:
                            # 绑定微信账号
                            success, message = AccountBindingService.bind_wechat_account(user_id, user_info)
                            if success:
                                st.success(message)
                                st.balloons()
                                st.session_state.binding_wechat = False
                                st.query_params.clear()
                                st.rerun()
                            else:
                                st.error(message)
                                st.session_state.binding_wechat = False
            
            if st.button("🔐 绑定微信账号", type="primary", use_container_width=True):
                # 设置绑定标记
                st.session_state.binding_wechat = True
                
                import hashlib
                import time
                state = hashlib.md5(str(time.time()).encode()).hexdigest()
                st.session_state.wechat_state = state
                
                auth_url = wechat_oauth.get_authorization_url(state)
                st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
        else:
            st.button("🔐 绑定微信账号", type="primary", use_container_width=True, disabled=True)
            st.caption("⚠️ 微信登录未配置")
    except Exception as e:
        st.button("🔐 绑定微信账号", type="primary", use_container_width=True, disabled=True)
        st.caption(f"❌ 微信功能错误")


def app():
    """账号绑定管理页面主函数"""
    
    # 检查登录状态
    if not AuthService.is_authenticated():
        st.warning("⚠️ 请先登录")
        return
    
    user = AuthService.get_current_user()
    if not user:
        st.error("❌ 获取用户信息失败")
        return
    
    user_id = user['id']
    
    # 页面标题
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
    ">
        <h1 style="color: white; margin: 0; font-size: 2rem;">
            🔗 账号绑定管理
        </h1>
        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;">
            绑定多种登录方式，灵活选择登录账号
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 显示已绑定的账号
    show_bound_accounts(user_id)
    
    st.markdown("---")
    st.markdown("## ➕ 添加登录方式")
    
    # 创建三列布局
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 邮箱登录设置
        if not AccountBindingService.can_login_with_email(user_id):
            with st.container():
                st.markdown("""
                <div style="
                    padding: 1rem;
                    border: 2px dashed #ddd;
                    border-radius: 12px;
                    text-align: center;
                    min-height: 200px;
                ">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📧</div>
                    <h4>邮箱登录</h4>
                    <p style="color: #666; font-size: 0.9rem;">使用邮箱和密码登录</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("➕ 设置邮箱登录", key="btn_email", use_container_width=True):
                    st.session_state.show_email_form = True
        else:
            st.success("✅ 已设置邮箱登录")
    
    with col2:
        # Google账号绑定
        if not AccountBindingService.has_google_binding(user_id):
            with st.container():
                st.markdown("""
                <div style="
                    padding: 1rem;
                    border: 2px dashed #ddd;
                    border-radius: 12px;
                    text-align: center;
                    min-height: 200px;
                ">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🔐</div>
                    <h4>Google账号</h4>
                    <p style="color: #666; font-size: 0.9rem;">使用Google快速登录</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("➕ 绑定Google账号", key="btn_google", use_container_width=True):
                    st.session_state.binding_google = True
                    try:
                        st.login("google")
                    except Exception as e:
                        st.error(f"绑定失败: {e}")
        else:
            st.success("✅ 已绑定Google账号")
    
    with col3:
        # 微信账号绑定
        if not AccountBindingService.has_wechat_binding(user_id):
            with st.container():
                st.markdown("""
                <div style="
                    padding: 1rem;
                    border: 2px dashed #ddd;
                    border-radius: 12px;
                    text-align: center;
                    min-height: 200px;
                ">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🔐</div>
                    <h4>微信账号</h4>
                    <p style="color: #666; font-size: 0.9rem;">使用微信扫码登录</p>
                </div>
                """, unsafe_allow_html=True)
                
                try:
                    from utils.wechat_oauth import init_wechat_oauth
                    wechat_oauth = init_wechat_oauth()
                    
                    if wechat_oauth:
                        if st.button("➕ 绑定微信账号", key="btn_wechat", use_container_width=True):
                            st.session_state.binding_wechat = True
                            
                            import hashlib
                            import time
                            state = hashlib.md5(str(time.time()).encode()).hexdigest()
                            st.session_state.wechat_state = state
                            
                            auth_url = wechat_oauth.get_authorization_url(state)
                            st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
                    else:
                        st.button("➕ 绑定微信账号", key="btn_wechat", use_container_width=True, disabled=True)
                        st.caption("⚠️ 微信未配置")
                except:
                    st.button("➕ 绑定微信账号", key="btn_wechat", use_container_width=True, disabled=True)
        else:
            st.success("✅ 已绑定微信账号")
    
    # 显示邮箱设置表单（如果需要）
    if st.session_state.get('show_email_form', False):
        st.markdown("---")
        show_bind_email_form(user_id)
        
        if st.button("❌ 取消", key="cancel_email_form"):
            st.session_state.show_email_form = False
            st.rerun()
    
    # 处理Google绑定回调
    if st.session_state.get('binding_google', False):
        try:
            if hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
                google_info = {
                    'sub': getattr(st.user, 'sub', None),
                    'email': getattr(st.user, 'email', None),
                    'name': getattr(st.user, 'name', None),
                    'picture': getattr(st.user, 'picture', None)
                }
                
                success, message = AccountBindingService.bind_google_account(user_id, google_info)
                if success:
                    st.success(message)
                    st.balloons()
                    st.session_state.binding_google = False
                    st.rerun()
                else:
                    st.error(message)
                    st.session_state.binding_google = False
        except:
            pass


if __name__ == "__main__":
    app()
