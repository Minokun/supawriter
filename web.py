import sys, os
import base64
from pathlib import Path
from datetime import datetime

# 函数：将图片转换为base64格式
def get_base64_from_image(image_path):
    """将图片转换为base64编码以便在HTML中显示"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error loading image: {e}")
        return ""

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
import page_settings
PAGES = page_settings.PAGES
# 导入隐藏页面
HIDDEN_PAGES = getattr(page_settings, 'HIDDEN_PAGES', [])

import streamlit as st
import importlib.util
import extra_streamlit_components as stx
from utils.auth import is_authenticated, logout, get_cookie_manager, get_user_motto, update_user_motto

# Set page configuration at the very beginning
st.set_page_config(
    page_title="超能写手", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# 全局样式优化
st.markdown("""
<style>
/* 顶部导航样式优化 */
section[data-testid="stSidebarNav"] {
    background-color: white;
    padding: 0.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

/* 侧边栏标题样式 */
.sidebar-header {
    background: linear-gradient(135deg, #4776E6 0%, #8E54E9 100%);
    color: white;
    padding: 0.8rem 0.6rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    position: relative;
    overflow: hidden;
}

.sidebar-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 60%);
    z-index: 1;
}

.sidebar-title {
    font-size: 1.4rem;
    font-weight: 700;
    margin: 0;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    position: relative;
    z-index: 2;
}

.sidebar-subtitle {
    font-size: 0.8rem;
    opacity: 0.9;
    margin-top: 0.3rem;
    position: relative;
    z-index: 2;
}

/* 用户信息卡片样式 */
.user-info-container {
    background-color: white;
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border: 1px solid #f0f0f0;
}

.user-info-header {
    display: flex;
    align-items: center;
    margin-bottom: 0.5rem;
}

.user-avatar {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #4776E6 0%, #8E54E9 100%);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    font-weight: bold;
    margin-right: 0.8rem;
    box-shadow: 0 2px 5px rgba(0,0,0,0.15);
}

.user-name {
    font-weight: 600;
    color: #333;
    margin: 0;
    font-size: 1rem;
}

.user-status {
    font-size: 0.8rem;
    color: #5a67d8;
    margin: 0;
    font-style: italic;
    font-weight: 500;
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
    max-width: 150px;
}

/* 退出按钮样式 */
button:has(div:contains("退出登录")) {
    background: linear-gradient(90deg, #ff758c 0%, #ff7eb3 100%) !important;
    color: white !important;
    border: none !important;
    width: 100% !important;
    margin-top: 0.5rem !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
    transition: all 0.3s ease !important;
}

button:has(div:contains("退出登录")):hover {
    background: linear-gradient(90deg, #ff5252 0%, #ff7676 100%) !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
}

/* 分隔线样式 */
hr {
    margin: 1rem 0;
    border: none;
    height: 1px;
    background-color: #f0f0f0;
}
</style>
""", unsafe_allow_html=True)

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

# We'll handle the logo in the sidebar with custom styling

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
    # 使用logo图片替代文字标题
    logo_path = os.path.join(current_dir, "sources", "images", "logo1.png")
    if os.path.exists(logo_path):
        st.logo(logo_path)
    
    # 获取当前年份用于版权信息
    current_year = datetime.now().year
    
    # 添加联系信息 - 使用适应暗色主题的样式
    st.sidebar.markdown(f"""
    <div style="margin-top: 1rem;">
        <h3 style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-color, #31333F);">关于我们</h3>
        <div style="background-color: var(--background-color, #f8f9fa); padding: 1rem; border-radius: 8px; font-size: 0.9rem; border: 1px solid var(--border-color, rgba(49, 51, 63, 0.1));">
            <p style="margin: 0 0 0.5rem 0; color: var(--text-color, #31333F);">©{current_year} Minokun</p>
            <p style="margin: 0 0 0.5rem 0; color: var(--text-color, #31333F);">📧 邮箱：952718180@qq.com</p>
            <p style="margin: 0 0 0.5rem 0; color: var(--text-color, #31333F);">📍 地址: 四川省成都市</p>
            <p style="margin: 0 0 0.5rem 0; color: var(--text-color, #31333F);">📱 微信公众号: 坤塔</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 使用Streamlit的图片显示功能来显示二维码
    wechat_qr_path = os.path.join(current_dir, "sources", "images", "wechat.png")
    if os.path.exists(wechat_qr_path):
        qr_container = st.sidebar.container()
        with qr_container:
            st.image(wechat_qr_path, caption="微信公众号二维码", use_container_width=True)
    
    # 获取用户座右铭
    user_motto = get_user_motto()
    
    # 使用自定义HTML样式显示用户信息
    st.sidebar.markdown(f"""
    <div class="user-info-container">
        <div class="user-info-header">
            <div class="user-avatar">{st.session_state.user[0].upper()}</div>
            <div>
                <p class="user-name">{st.session_state.user}</p>
                <p class="user-status" title="座右铭">"{user_motto}"</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 退出登录按钮
    # 在点击退出登录按钮时直接执行退出操作
    if st.sidebar.button("退出登录", use_container_width=True):
        logout()
        # 使用experimental_rerun来触发重新加载
        st.experimental_rerun()
    
    st.sidebar.divider()
    
    # 已在文件前面处理了HTML查看器页面的加载逻辑
    
    # 显示导航并运行选定页面
    pg = st.navigation(PAGES, position="top")
    pg.run()