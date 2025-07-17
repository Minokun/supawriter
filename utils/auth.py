import os
import pickle
import streamlit as st
from datetime import datetime, timedelta
import hashlib
import base64
import json
import extra_streamlit_components as stx

# Path to the user database file
USER_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'users.pkl')

# Ensure the data directory exists
os.makedirs(os.path.dirname(USER_DB_PATH), exist_ok=True)

class User:
    def __init__(self, username, password_hash, email=None, created_at=None):
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.created_at = created_at or datetime.now()
        self.last_login = None
    
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

def register_user(username, password, email=None):
    """Register a new user."""
    users = load_users()
    
    # Check if username already exists
    if username in users:
        return False, "用户名已存在"
    
    # Create new user
    password_hash = hash_password(password)
    users[username] = User(username, password_hash, email)
    save_users(users)
    return True, "注册成功"

# Create a cookie manager instance with a unique key
_cookie_manager = None

def get_cookie_manager():
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = stx.CookieManager(key="supawriter_auth_cookies")
    return _cookie_manager

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
    """Check if user is authenticated."""
    # Check if user is in session state
    if "user" in st.session_state and st.session_state.user is not None:
        return True
    
    # If not in session state, try to load from cookie
    try:
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
    except Exception as e:
        # If there's any error parsing the auth token, ignore it
        pass
    
    return False

def get_current_user():
    """Get current authenticated user."""
    if is_authenticated():
        return st.session_state.user
    return None

def logout():
    """Log out the current user."""
    if "user" in st.session_state:
        st.session_state.user = None
    
    # Clear auth token from cookie
    try:
        cookie_manager = get_cookie_manager()
        cookie_manager.delete("auth_token")
    except Exception as e:
        # If there's any error deleting the cookie, ignore it
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
