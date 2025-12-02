import streamlit as st
import datetime
from utils.auth import get_current_user, load_users, save_users, hash_password, get_user_motto, update_user_motto

def app():
    # 添加现代UI样式
    st.markdown("""
    <style>
    /* 全局样式优化 */
    .main > div:first-child {
        padding-top: 1rem;
    }
    
    /* 卡片容器样式 */
    .profile-card {
        background: white;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid rgba(0,0,0,0.05);
        transition: all 0.3s ease;
        margin-bottom: 1.5rem;
    }
    
    .profile-card:hover {
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        transform: translateY(-2px);
    }
    
    /* 表单样式 */
    .stForm {
        border: none !important;
        padding: 0 !important;
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        padding: 0.75rem 2rem !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
        width: 100% !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
    }
    
    /* 输入框样式 */
    .stTextInput > div > div {
        border-radius: 8px !important;
        border: 1px solid #e0e0e0 !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div:focus-within {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
    }
    
    /* 选择器样式 */
    .stSelectbox > div > div {
        border-radius: 8px !important;
        border: 1px solid #e0e0e0 !important;
    }
    
    /* 标签样式 */
    .stMarkdown p {
        line-height: 1.6;
    }
    
    /* 响应式布局 */
    @media (max-width: 768px) {
        .profile-card {
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state for profile page rerun trigger if not exists
    if "profile_trigger_rerun" not in st.session_state:
        st.session_state.profile_trigger_rerun = False
        
    # Check if we need to rerun
    if st.session_state.profile_trigger_rerun:
        st.session_state.profile_trigger_rerun = False
        st.rerun()
        
    user = get_current_user()
    if not user:
        st.warning("请先登录")
        return

    # If OAuth2 user is logged in, render a simplified OAuth profile and return
    try:
        oauth_logged_in = hasattr(st, "user") and getattr(st.user, "is_logged_in", False)
    except Exception:
        oauth_logged_in = False

    if oauth_logged_in:
        st.subheader("个人信息")
        col1, col2 = st.columns([1, 3])
        with col1:
            try:
                if hasattr(st.user, "picture") and st.user.picture:
                    picture_url = st.user.picture
                    # Prefer HTML img to avoid hotlink/referrer issues some CDNs enforce
                    st.markdown(
                        f'<img src="{picture_url}" width="100" style="border-radius:50%;" referrerpolicy="no-referrer" />',
                        unsafe_allow_html=True,
                    )
                else:
                    st.write("👤")
            except Exception:
                # Fallback to st.image if HTML rendering fails
                try:
                    st.image(getattr(st.user, "picture", None), width=100)
                except Exception:
                    st.write("👤")
        with col2:
            if getattr(st.user, "name", None):
                st.write(f"**名称：** {st.user.name}")
            if getattr(st.user, "email", None):
                st.write(f"**邮箱：** {st.user.email}")
            if getattr(st.user, "sub", None):
                st.write(f"**标识：** {st.user.sub}")

        st.markdown("---")
        st.subheader("个性化设置")
        current_motto = get_user_motto(user)
        new_motto = st.text_input("座右铭", value=current_motto, help="将显示在侧边栏")
        if st.button("保存座右铭"):
            ok, msg = update_user_motto(user, new_motto)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

        st.info("密码与邮箱由第三方账号提供商管理，此处不可修改。")
        return
    
    # 现代标题设计
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.2);
        position: relative;
        overflow: hidden;
    ">
        <div style="
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            transform: rotate(45deg);
        "></div>
        <div style="position: relative; z-index: 1;">
            <h1 style="
                color: white;
                margin: 0;
                font-size: 2.2rem;
                font-weight: 700;
                letter-spacing: -0.5px;
            ">👤 个人信息中心</h1>
            <p style="
                color: rgba(255,255,255,0.9);
                margin: 0.5rem 0 0 0;
                font-size: 1.1rem;
                font-weight: 400;
            ">管理您的账户信息和个性化设置</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    users = load_users()
    current_user = users[user]
    
    # 计算账户年龄
    account_age = (datetime.datetime.now() - current_user.created_at).days
    
    # # 个人信息卡片 - 现代化设计
    
    # 使用列布局创建用户头部
    col1, col2, col3 = st.columns([1, 2, 1])
    
    # 头像列
    with col1:
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
            position: relative;
        ">
            {current_user.username[0].upper()}
            <div style="
                position: absolute;
                bottom: 5px;
                right: 5px;
                width: 20px;
                height: 20px;
                background: #4CAF50;
                border-radius: 50%;
                border: 3px solid white;
            "></div>
        </div>
        """, unsafe_allow_html=True)
    
    # 用户信息列
    with col2:
        st.markdown(f"""
        <div style="text-align: left; padding-left: 1rem;">
            <h2 style="
                margin: 0 0 0.5rem 0;
                font-size: 2rem;
                font-weight: 700;
                color: #2c3e50;
                letter-spacing: -0.5px;
            ">{current_user.username}</h2>
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
                📧 {current_user.email or '未设置邮箱'}
            </div>
            <div style="color: #666; font-size: 0.95rem;">
                📅 注册时间: {current_user.created_at.strftime('%Y年%m月%d日')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 状态列
    with col3:
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
    
    # 添加分隔线
    st.markdown("<hr style='margin: 1rem 0; border: none; height: 1px; background-color: #f0f0f0;'>", unsafe_allow_html=True)
    
    # 获取用户座右铭
    user_motto = get_user_motto(current_user.username)
    last_login = current_user.last_login.strftime('%Y-%m-%d %H:%M:%S') if current_user.last_login else '无记录'
    
    # 基本信息卡片内容
    st.markdown("""
    <h3 style="margin-top: 0.5rem; margin-bottom: 1rem; color: #333; font-size: 1.3rem; font-weight: 600;">
        <span style="
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background: linear-gradient(135deg, #4776E6 0%, #8E54E9 100%);
            margin-right: 8px;
            border-radius: 50%;
            color: white;
            font-size: 0.9rem;
        ">📋</span>
        基本信息
    </h3>
    """, unsafe_allow_html=True)
    
    # 定义信息项
    info_items = [
        ("用户名", current_user.username),
        ("座右铭", f'<span style="font-style:italic;color:#5B86E5;">\'{user_motto}\'</span>'),
        ("邮箱", current_user.email or '<span style="color:#999;">未设置</span>'),
        ("注册时间", current_user.created_at.strftime('%Y-%m-%d %H:%M:%S')),
        ("账户年龄", f'{account_age} 天'),
        ("上次登录", last_login),
    ]
    
    # 直接生成基本信息内容
    st.markdown("<div class='user-info-table'>", unsafe_allow_html=True)
    
    # 逐行生成基本信息行
    for label, value in info_items:
        st.markdown(f"""
        <div style="display: flex; border-bottom: 1px solid #f0f0f0; padding: 10px 0;">
            <div style="width: 120px; font-weight: 500; color: #555;">{label}:</div>
            <div>{value}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 添加分隔线
    st.markdown("<hr style='margin: 1.5rem 0; border: none; height: 1px; background-color: #f0f0f0;'>", unsafe_allow_html=True)
    
    # 创建编辑表单区域
    st.markdown("<h3 style='margin-top: 1rem; margin-bottom: 1.5rem; color: #333; font-size: 1.4rem; font-weight: 600;'>个人设置</h3>", unsafe_allow_html=True)
    
    # 创建两列布局用于座右铭和邮箱
    col_motto, col_email = st.columns(2)
    
    # 第一列 - 编辑座右铭表单
    with col_motto:
        st.markdown("""
            <h3 style="
                margin-top: 0;
                margin-bottom: 1rem;
                color: #333;
                font-size: 1.3rem;
                font-weight: 600;
                display: flex;
                align-items: center;
            ">
                <span style="
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 28px;
                    height: 28px;
                    background: linear-gradient(135deg, #4776E6 0%, #8E54E9 100%);
                    margin-right: 8px;
                    border-radius: 50%;
                    color: white;
                    font-size: 0.9rem;
                ">✏️</span>
                编辑座右铭
            </h3>
        """, unsafe_allow_html=True)
        
        with st.form("edit_motto", clear_on_submit=False, border=False):
            current_motto = get_user_motto(user)
            new_motto = st.text_input("座右铭", value=current_motto, max_chars=20, 
                                   help="座右铭将显示在您的个人信息中，最多20个字符")
            submitted_motto = st.form_submit_button("更新座右铭")
            if submitted_motto:
                update_user_motto(user, new_motto)
                st.success("座右铭已成功更新！")
                st.session_state.profile_trigger_rerun = True
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # 编辑邮箱卡片
    with col_email:
        st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
            <div style="
                display: flex;
                align-items: center;
                justify-content: center;
                width: 40px;
                height: 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 10px;
                margin-right: 12px;
                color: white;
                font-size: 1.2rem;
            ">📧</div>
            <div>
                <h3 style="margin: 0; font-size: 1.3rem; font-weight: 600; color: #2c3e50;">邮箱设置</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("edit_email", clear_on_submit=False, border=False):
            new_email = st.text_input(
                "新邮箱地址", 
                value=current_user.email or "",
                placeholder="请输入您的新邮箱地址",
                help="用于接收重要通知和找回密码"
            )
            
            col_submit, _ = st.columns([1, 2])
            with col_submit:
                submitted_email = st.form_submit_button("💾 更新邮箱")
                
            if submitted_email:
                if new_email and '@' in new_email:
                    current_user.email = new_email
                    users[user] = current_user
                    save_users(users)
                    st.success("✅ 邮箱已成功更新！")
                    st.session_state.profile_trigger_rerun = True
                else:
                    st.error("❌ 请输入有效的邮箱地址")
    
    # 添加分隔线
    st.markdown("<hr style='margin: 1.5rem 0; border: none; height: 1px; background-color: #f0f0f0;'>", unsafe_allow_html=True)
    
    # 修改密码卡片 - 现代化设计
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            border-radius: 10px;
            margin-right: 12px;
            color: white;
            font-size: 1.2rem;
        ">🔐</div>
        <div>
            <h3 style="margin: 0; font-size: 1.3rem; font-weight: 600; color: #2c3e50;">安全设置</h3>
            <p style="margin: 0; color: #666; font-size: 0.9rem;">定期更新密码保障账户安全</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("change_password", clear_on_submit=True, border=False):
        # 密码强度指示器
        password_col1, password_col2 = st.columns(2)
        
        with password_col1:
            old_password = st.text_input(
                "当前密码", 
                type="password",
                placeholder="请输入当前密码",
                help="输入您当前使用的密码"
            )
        
        with password_col2:
            st.empty()  # 占位符
        
        new_password = st.text_input(
            "新密码", 
            type="password", 
            placeholder="请输入新密码",
            help="建议使用包含大小写字母、数字和特殊字符的强密码"
        )
        
        confirm_new_password = st.text_input(
            "确认新密码", 
            type="password",
            placeholder="请再次输入新密码",
            help="确保两次输入的密码一致"
        )
        
        # 密码强度检查
        if new_password:
            if len(new_password) < 8:
                st.warning("⚠️ 密码长度至少8位")
            elif not any(c.isupper() for c in new_password) or not any(c.islower() for c in new_password):
                st.info("💡 建议使用大小写字母组合")
            elif not any(c.isdigit() for c in new_password):
                st.info("💡 建议添加数字")
        
        col_submit, _ = st.columns([1, 2])
        with col_submit:
            submitted_password = st.form_submit_button("🔄 更新密码")

        if submitted_password:
            if not all([old_password, new_password, confirm_new_password]):
                st.error("❌ 所有密码字段都必须填写")
            elif new_password != confirm_new_password:
                st.error("❌ 两次输入的新密码不一致")
            elif len(new_password) < 8:
                st.error("❌ 密码长度至少8位")
            else:
                from utils.auth import change_password
                success, message = change_password(user, old_password, new_password)
                if success:
                    st.success("✅ " + message)
                    st.balloons()
                else:
                    st.error("❌ " + message)
                    
    st.markdown('</div>', unsafe_allow_html=True)

app()
