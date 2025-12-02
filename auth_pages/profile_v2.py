# -*- coding: utf-8 -*-
"""
SupaWriter 个人中心页面 V2
支持新的认证系统和账号绑定管理
"""

import streamlit as st
from datetime import datetime
from utils.auth_v2 import AuthService
from utils.account_binding import AccountBindingService


def show_user_header(user):
    """显示用户头部信息"""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.2);
    ">
        <h1 style="color: white; margin: 0; font-size: 2.2rem; font-weight: 700;">
            👤 个人信息中心
        </h1>
        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            管理您的账户信息和登录方式
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 用户信息卡片
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        # 头像
        if user.get('avatar_url'):
            st.image(user['avatar_url'], width=120)
        else:
            username = user.get('username', 'U')
            st.markdown(f"""
            <div style="
                width: 120px;
                height: 120px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 3rem;
                font-weight: 700;
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
                margin: 0 auto;
            ">
                {username[0].upper()}
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        display_name = user.get('display_name') or user.get('username')
        email = user.get('email') or '未设置'
        
        st.markdown(f"""
        <div style="padding-left: 1rem;">
            <h2 style="margin: 0 0 0.5rem 0; font-size: 2rem; font-weight: 700; color: #2c3e50;">
                {display_name}
            </h2>
            <div style="
                display: inline-flex;
                align-items: center;
                padding: 0.4rem 1rem;
                background: linear-gradient(135deg, #36D1DC 0%, #5B86E5 100%);
                color: white;
                border-radius: 25px;
                font-size: 0.85rem;
                font-weight: 600;
                box-shadow: 0 4px 12px rgba(91,134,229,0.3);
                margin-bottom: 1rem;
            ">
                ✓ 已激活
            </div>
            <div style="color: #666; font-size: 0.95rem; margin-bottom: 0.5rem;">
                📧 {email}
            </div>
            <div style="color: #666; font-size: 0.95rem;">
                🆔 用户名: {user.get('username')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # 账户年龄
        created_at = user.get('created_at')
        if isinstance(created_at, datetime):
            account_age = (datetime.now() - created_at).days
        else:
            account_age = 0
        
        st.markdown(f"""
        <div style="text-align: center;">
            <div style="
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
                padding: 1rem;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(245,87,108,0.3);
                margin-bottom: 0.5rem;
            ">
                <div style="font-size: 1.5rem; font-weight: 700;">{account_age}</div>
                <div style="font-size: 0.8rem; opacity: 0.9;">天</div>
            </div>
            <div style="color: #888; font-size: 0.8rem;">账户年龄</div>
        </div>
        """, unsafe_allow_html=True)


def show_basic_info(user):
    """显示基本信息"""
    st.markdown("### 📋 基本信息")
    
    created_at = user.get('created_at')
    last_login = user.get('last_login')
    motto = user.get('motto') or '创作改变世界'
    
    info_items = [
        ("用户名", user.get('username')),
        ("显示名称", user.get('display_name') or user.get('username')),
        ("座右铭", f'<span style="font-style:italic;color:#5B86E5;">\'{motto}\'</span>'),
        ("邮箱", user.get('email') or '<span style="color:#999;">未设置</span>'),
        ("注册时间", created_at.strftime('%Y-%m-%d %H:%M:%S') if isinstance(created_at, datetime) else '未知'),
        ("上次登录", last_login.strftime('%Y-%m-%d %H:%M:%S') if isinstance(last_login, datetime) else '未知'),
    ]
    
    for label, value in info_items:
        st.markdown(f"""
        <div style="display: flex; border-bottom: 1px solid #f0f0f0; padding: 10px 0;">
            <div style="width: 120px; font-weight: 500; color: #555;">{label}:</div>
            <div>{value}</div>
        </div>
        """, unsafe_allow_html=True)


def show_login_methods(user_id):
    """显示登录方式"""
    st.markdown("### 🔗 登录方式")
    
    bound_accounts = AccountBindingService.get_bound_accounts(user_id)
    
    if not bound_accounts:
        st.info("暂无绑定的登录方式")
        return
    
    # 创建卡片布局
    cols = st.columns(3)
    
    for idx, account in enumerate(bound_accounts):
        with cols[idx % 3]:
            provider = account['provider']
            display_name = account['display_name']
            identifier = account['identifier']
            
            # 图标和颜色
            if provider == 'email':
                icon = '📧'
                color = '#4CAF50'
            elif provider == 'google':
                icon = '🔐'
                color = '#EA4335'
            elif provider == 'wechat':
                icon = '🔐'
                color = '#07C160'
            else:
                icon = '🔐'
                color = '#666'
            
            st.markdown(f"""
            <div style="
                border: 2px solid {color};
                border-radius: 12px;
                padding: 1rem;
                text-align: center;
                margin-bottom: 1rem;
                background: rgba(255,255,255,0.9);
            ">
                <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">{icon}</div>
                <h4 style="margin: 0.5rem 0; color: {color};">{display_name}</h4>
                <p style="color: #666; font-size: 0.85rem; margin: 0; word-break: break-all;">
                    {identifier[:30]}{'...' if len(identifier) > 30 else ''}
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    # 添加更多登录方式的按钮
    st.markdown("---")
    if st.button("➕ 管理登录方式", key="manage_login", use_container_width=True):
        st.session_state.show_account_binding = True


def show_profile_settings(user):
    """显示个人设置"""
    st.markdown("### ⚙️ 个人设置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ✏️ 编辑显示名称")
        with st.form("edit_display_name", clear_on_submit=False):
            new_display_name = st.text_input(
                "显示名称",
                value=user.get('display_name') or user.get('username'),
                help="将显示在您的个人信息中"
            )
            if st.form_submit_button("💾 保存", use_container_width=True):
                success, message = AuthService.update_profile(
                    user['id'],
                    display_name=new_display_name
                )
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    with col2:
        st.markdown("#### 💬 编辑座右铭")
        with st.form("edit_motto", clear_on_submit=False):
            new_motto = st.text_input(
                "座右铭",
                value=user.get('motto') or '创作改变世界',
                max_chars=50,
                help="最多50个字符"
            )
            if st.form_submit_button("💾 保存", use_container_width=True):
                success, message = AuthService.update_profile(
                    user['id'],
                    motto=new_motto
                )
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


def show_security_settings(user):
    """显示安全设置"""
    st.markdown("### 🔐 安全设置")
    
    # 只有邮箱登录用户才能修改密码
    if not user.get('password_hash'):
        st.info("💡 您使用第三方登录，无需设置密码。如需使用邮箱登录，请在'管理登录方式'中设置。")
        return
    
    st.markdown("#### 修改密码")
    
    with st.form("change_password", clear_on_submit=True):
        new_password = st.text_input(
            "新密码",
            type="password",
            placeholder="至少8个字符"
        )
        
        confirm_password = st.text_input(
            "确认新密码",
            type="password",
            placeholder="再次输入新密码"
        )
        
        # 密码强度提示
        if new_password:
            if len(new_password) < 8:
                st.warning("⚠️ 密码长度至少8位")
            else:
                strength = 0
                if any(c.isupper() for c in new_password):
                    strength += 1
                if any(c.islower() for c in new_password):
                    strength += 1
                if any(c.isdigit() for c in new_password):
                    strength += 1
                if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in new_password):
                    strength += 1
                
                if strength >= 3:
                    st.success("✅ 密码强度：强")
                elif strength >= 2:
                    st.info("💡 密码强度：中等")
                else:
                    st.warning("⚠️ 密码强度：弱")
        
        if st.form_submit_button("🔄 更新密码", use_container_width=True, type="primary"):
            if not all([new_password, confirm_password]):
                st.error("❌ 请填写新密码")
            elif new_password != confirm_password:
                st.error("❌ 两次输入的新密码不一致")
            elif len(new_password) < 8:
                st.error("❌ 密码长度至少8位")
            else:
                success, message = AuthService.reset_password(
                    user['id'],
                    new_password
                )
                if success:
                    st.success("✅ " + message)
                    st.balloons()
                else:
                    st.error("❌ " + message)


def app():
    """个人中心主函数"""
    
    # 添加现代化样式
    st.markdown("""
    <style>
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
    
    # 检查登录状态
    if not AuthService.is_authenticated():
        st.warning("⚠️ 请先登录")
        return
    
    user = AuthService.get_current_user()
    if not user:
        st.error("❌ 获取用户信息失败")
        return
    
    # 检查是否要显示账号绑定页面
    if st.session_state.get('show_account_binding', False):
        from auth_pages import account_binding
        
        if st.button("← 返回个人中心", key="back_to_profile"):
            st.session_state.show_account_binding = False
            st.rerun()
        
        st.markdown("---")
        account_binding.app()
        return
    
    # 显示用户头部
    show_user_header(user)
    
    # 显示基本信息
    show_basic_info(user)
    
    st.markdown("---")
    
    # 显示登录方式
    show_login_methods(user['id'])
    
    st.markdown("---")
    
    # 显示个人设置
    show_profile_settings(user)
    
    st.markdown("---")
    
    # 显示安全设置
    show_security_settings(user)


if __name__ == "__main__":
    app()
