import os
import pickle
import streamlit as st
from datetime import datetime, timedelta
import hashlib
import base64
import json
import extra_streamlit_components as stx
try:
    # Streamlit 1.29+ provides this to detect if we're in a ScriptRunContext
    from streamlit.runtime.scriptrun_context import get_script_run_ctx as _get_src
except Exception:
    _get_src = None

# Path to the user database file
USER_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'users.pkl')

# Ensure the data directory exists
os.makedirs(os.path.dirname(USER_DB_PATH), exist_ok=True)

class User:
    def __init__(self, username, password_hash, email=None, created_at=None, motto=None):
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.created_at = created_at or datetime.now()
        self.last_login = None
        self.motto = motto or "创作改变世界"  # 默认座右铭
    
    def update_last_login(self):
        self.last_login = datetime.now()

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Load users from the database file."""
    if os.path.exists(USER_DB_PATH):
        with open(USER_DB_PATH, 'rb') as f:
            return pickle.load(f)
    return {}

def save_users(users):
    """Save users to the database file."""
    with open(USER_DB_PATH, 'wb') as f:
        pickle.dump(users, f)

def register_user(username, password, email=None, motto=None):
    """Register a new user."""
    users = load_users()
    
    # Check if username already exists
    if username in users:
        return False, "用户名已存在"
    
    # Create new user
    password_hash = hash_password(password)
    users[username] = User(username, password_hash, email, motto=motto)
    save_users(users)
    return True, "注册成功"

# Create a cookie manager instance with a unique key
_cookie_manager = None

def get_cookie_manager():
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = stx.CookieManager(key="supawriter_auth_cookies")
    return _cookie_manager

def _has_streamlit_context() -> bool:
    """Return True if running inside a Streamlit ScriptRunContext.
    Tries both new and legacy locations; never assumes True in unknown cases.
    """
    # Try new API
    try:
        if _get_src is not None:
            return _get_src() is not None
    except Exception:
        pass
    # Try legacy API
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx as _legacy_src  # type: ignore
        return _legacy_src() is not None
    except Exception:
        pass
    return False

def authenticate_user(username, password, remember_me=False):
    """Authenticate a user."""
    users = load_users()
    
    if username not in users:
        return False, "用户名不存在"
    
    user = users[username]
    if user.password_hash != hash_password(password):
        return False, "密码错误"
    
    # Update last login time
    user.update_last_login()
    save_users(users)
    
    # Set persistent login if remember_me is True
    if remember_me:
        # Set expiry to 30 days from now
        expiry = datetime.now() + timedelta(days=30)
        
        # Create auth token
        auth_data = {
            "username": username,
            "expiry": expiry.isoformat()
        }
        
        # Encode auth data as base64
        auth_token = base64.b64encode(json.dumps(auth_data).encode("utf-8")).decode("utf-8")
        
        # Set cookie with auth token
        cookie_manager = get_cookie_manager()
        cookie_manager.set("auth_token", auth_token, expires_at=expiry)
    
    # Set user in session state
    st.session_state.user = username
    
    return True, "登录成功"

def is_authenticated():
    """Check if user is authenticated.

    Priority:
    1) OAuth2 via Streamlit: st.user.is_logged_in
    2) Legacy session/cookie fallback
    """
    # 1) Prefer Streamlit OAuth2 user state if available
    try:
        if _has_streamlit_context() and hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
            return True
    except Exception:
        pass

    # 2) Legacy: Check if user is in session state (only when context exists)
    if _has_streamlit_context():
        if "user" in st.session_state and st.session_state.user is not None:
            return True

    # 3) Legacy: Try to load from cookie
    try:
        # Avoid touching Streamlit components outside context
        if _has_streamlit_context():
            cookie_manager = get_cookie_manager()
            auth_token = cookie_manager.get("auth_token")

            if auth_token:
                # Decode the auth token
                auth_data = json.loads(base64.b64decode(auth_token).decode("utf-8"))
                username = auth_data.get("username")
                expiry = auth_data.get("expiry")

                # Check if token is still valid
                if expiry and datetime.fromisoformat(expiry) > datetime.now():
                    # Set the user in session state
                    st.session_state.user = username
                    return True
    except Exception:
        # If there's any error parsing the auth token, ignore it
        pass

    return False

def get_user_id():
    """Return a stable user ID for storage and paths.

    Priority: OAuth subject (sub) -> email -> legacy session username -> name.
    """
    try:
        if _has_streamlit_context() and hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
            if hasattr(st.user, "sub") and st.user.sub:
                return st.user.sub
            if hasattr(st.user, "email") and st.user.email:
                return st.user.email
            if hasattr(st.user, "name") and st.user.name:
                return st.user.name
    except Exception:
        pass
    # Avoid touching Streamlit state when no context (e.g., background threads)
    if _has_streamlit_context():
        if "user" in st.session_state and st.session_state.user:
            return st.session_state.user
    return None

def get_user_display_name():
    """Return a friendly display name for UI.

    Priority: OAuth name -> email -> legacy session username.
    """
    try:
        if _has_streamlit_context() and hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
            if getattr(st.user, "name", None):
                return st.user.name
            if getattr(st.user, "email", None):
                return st.user.email
    except Exception:
        pass
    if _has_streamlit_context() and "user" in st.session_state and st.session_state.user:
        return st.session_state.user
    return "用户"

def get_current_user():
    """Get current authenticated user identifier (stable ID)."""
    return get_user_id()

def get_user_motto(username=None):
    """Get user's motto. If username is None, get current user's motto."""
    if username is None:
        username = get_current_user()
        if not username:
            return "创作改变世界"  # 默认座右铭
    
    users = load_users()
    if username in users:
        # 兼容旧用户对象可能没有motto属性
        try:
            return users[username].motto or "创作改变世界"
        except AttributeError:
            # 给旧用户对象添加motto属性
            users[username].motto = "创作改变世界"
            save_users(users)  # 保存更新
            return "创作改变世界"
    return "创作改变世界"  # 默认座右铭

def logout():
    """Log out the current user.

    Prefer Streamlit OAuth2 logout; also clear legacy session/cookie.
    """
    # OAuth2 logout if available
    try:
        if _has_streamlit_context() and hasattr(st, "logout"):
            st.logout()
    except Exception:
        pass

    # Legacy session cleanup (only when context exists)
    if _has_streamlit_context() and "user" in st.session_state:
        st.session_state.user = None

    # Clear legacy auth token from cookie
    try:
        if _has_streamlit_context():
            cookie_manager = get_cookie_manager()
            cookie_manager.delete("auth_token")
    except Exception:
        pass

def change_password(username, old_password, new_password):
    """Change user's password."""
    users = load_users()
    
    if username not in users:
        return False, "用户不存在"
    
    user = users[username]
    
    # Verify old password
    if user.password_hash != hash_password(old_password):
        return False, "当前密码不正确"
    
    # Update to new password
    user.password_hash = hash_password(new_password)
    save_users(users)
    
    return True, "密码修改成功"

def update_user_motto(username, motto):
    """Update user's motto."""
    users = load_users()
    
    if username not in users:
        # Create a minimal user record for OAuth accounts to persist motto
        email = None
        try:
            if _has_streamlit_context() and hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
                email = getattr(st.user, "email", None)
        except Exception:
            pass
        users[username] = User(username=username, password_hash="", email=email, motto=motto)
    else:
        users[username].motto = motto

    save_users(users)
    return True, "座右铭更新成功"
