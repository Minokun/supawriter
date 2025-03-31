import os
import pickle
import streamlit as st
from datetime import datetime
import hashlib

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

def authenticate_user(username, password):
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
    return True, "登录成功"

def is_authenticated():
    """Check if user is authenticated."""
    return "user" in st.session_state and st.session_state.user is not None

def get_current_user():
    """Get current authenticated user."""
    if is_authenticated():
        return st.session_state.user
    return None

def logout():
    """Log out the current user."""
    if "user" in st.session_state:
        st.session_state.user = None
