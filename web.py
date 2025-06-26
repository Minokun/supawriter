import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
import page_settings
PAGES = page_settings.PAGES
# 导入隐藏页面
HIDDEN_PAGES = getattr(page_settings, 'HIDDEN_PAGES', [])

import streamlit as st
import importlib.util
import extra_streamlit_components as stx
from utils.auth import is_authenticated, logout, get_cookie_manager

# Set page configuration at the very beginning
st.set_page_config(page_title="超能写手", page_icon="🚀", layout="wide")

# Load the login module from auth_pages
def load_module(path):
    spec = importlib.util.spec_from_file_location("module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

login_module = load_module(os.path.join(current_dir, "auth_pages", "login.py"))

# Initialize cookie manager
cookie_manager = get_cookie_manager()

# Initialize session state for user if not exists
if "user" not in st.session_state:
    st.session_state.user = None

# Setup the app logo
st.logo(image='sources/images/supawriter.jpeg')

# 处理页面查询参数，检查是否需要跳转到HTML查看器页面
query_params = st.query_params
page_id = query_params.get("page_id", None)



# 对于其他页面，检查用户是否已登录
if not is_authenticated():
    # Show login page
    login_module.app()
    # Stop execution if not authenticated
    if not is_authenticated():
        st.stop()
else:
    # User is authenticated
    # Display username in sidebar
    with st.sidebar:
        st.write(f"**当前用户**: {st.session_state.user}")
        if st.button("退出登录"):
            logout()
            # 使用session_state来触发重新加载
            st.session_state['logout_trigger_rerun'] = True
        st.divider()
            
    # 检查是否需要重新加载页面
    if st.session_state.get('logout_trigger_rerun', False):
        # 重置标志
        st.session_state['logout_trigger_rerun'] = False
        st.rerun()
    
    # 已在文件前面处理了HTML查看器页面的加载逻辑
    
    # 显示导航并运行选定页面
    pg = st.navigation(PAGES)
    pg.run()