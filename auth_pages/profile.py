import streamlit as st
from utils.auth import get_current_user, load_users, save_users, hash_password

def app():
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
    
    st.title("个人信息")
    
    users = load_users()
    current_user = users[user]
    
    # Display user information
    st.subheader("基本信息")
    st.write(f"**用户名**: {current_user.username}")
    st.write(f"**邮箱**: {current_user.email or '未设置'}")
    st.write(f"**注册时间**: {current_user.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if current_user.last_login:
        st.write(f"**上次登录**: {current_user.last_login.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Edit profile section
    st.subheader("编辑邮箱")
    with st.form("edit_email"):
        new_email = st.text_input("新邮箱", value=current_user.email or "")
        submitted_email = st.form_submit_button("更新邮箱")
        if submitted_email:
            current_user.email = new_email
            users[user] = current_user
            save_users(users)
            st.success("邮箱已更新！")
            st.rerun()

    st.subheader("修改密码")
    with st.form("change_password"):
        old_password = st.text_input("当前密码", type="password")
        new_password = st.text_input("新密码", type="password")
        confirm_new_password = st.text_input("确认新密码", type="password")
        submitted_password = st.form_submit_button("确认修改密码")

        if submitted_password:
            if not old_password or not new_password or not confirm_new_password:
                st.warning("所有密码字段都不能为空。")
            elif new_password != confirm_new_password:
                st.error("两次输入的新密码不一致！")
            else:
                from utils.auth import change_password
                success, message = change_password(user, old_password, new_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)

app()
