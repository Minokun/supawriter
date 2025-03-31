import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
import page_settings
PAGES = page_settings.PAGES
import streamlit as st
import importlib.util
from utils.auth import is_authenticated, logout

# Set page configuration at the very beginning
st.set_page_config(page_title="超能写手", page_icon="🚀", layout="wide")

# Load the login module from auth_pages
def load_module(path):
    spec = importlib.util.spec_from_file_location("module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

login_module = load_module(os.path.join(current_dir, "auth_pages", "login.py"))

# Initialize session state for user if not exists
if "user" not in st.session_state:
    st.session_state.user = None

# Setup the app logo
st.logo(image='sources/images/supawriter.jpeg')

# Check if user is authenticated
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
            st.rerun()
        st.divider()
    
    # Show navigation and run the selected page
    pg = st.navigation(PAGES)
    pg.run()