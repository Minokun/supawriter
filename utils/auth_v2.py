# -*- coding: utf-8 -*-
"""
SupaWriter 认证模块 V2
支持多种登录方式：邮箱密码、Google OAuth、微信OAuth
支持账号绑定：不同登录方式可以绑定到同一个用户
"""

import hashlib
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import logging
import json
import base64
import extra_streamlit_components as stx

from utils.database import Database, User, OAuthAccount

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """密码哈希函数"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    return hash_password(password) == password_hash


# Cookie管理器
_cookie_manager = None

def get_cookie_manager():
    """获取Cookie管理器实例"""
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = stx.CookieManager(key="supawriter_auth_cookies_v2")
    return _cookie_manager


def _has_streamlit_context() -> bool:
    """检查是否在Streamlit上下文中运行"""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except:
        return False


class AuthService:
    """认证服务类"""
    
    @staticmethod
    def register_with_email(
        username: str,
        email: str,
        password: str,
        display_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        使用邮箱和密码注册新用户
        
        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            display_name: 显示名称
        
        Returns:
            (成功标志, 消息)
        """
        # 验证输入
        if not username or len(username) < 3:
            return False, "用户名至少3个字符"
        
        if not email or '@' not in email:
            return False, "请输入有效的邮箱地址"
        
        if not password or len(password) < 8:
            return False, "密码至少8个字符"
        
        # 检查用户名是否已存在
        if User.get_user_by_username(username):
            return False, "用户名已存在"
        
        # 检查邮箱是否已存在
        if User.get_user_by_email(email):
            return False, "邮箱已被注册"
        
        # 创建用户
        password_hash = hash_password(password)
        user_id = User.create_user(
            username=username,
            email=email,
            password_hash=password_hash,
            display_name=display_name or username
        )
        
        if user_id:
            logger.info(f"✅ 新用户注册成功: {username}")
            return True, "注册成功！请登录"
        else:
            return False, "注册失败，请稍后重试"
    
    @staticmethod
    def login_with_email(email: str, password: str, remember_me: bool = False) -> Tuple[bool, str, Optional[Dict]]:
        """
        使用邮箱和密码登录
        
        Args:
            email: 邮箱
            password: 密码
            remember_me: 是否记住登录状态
        
        Returns:
            (成功标志, 消息, 用户信息)
        """
        # 查找用户
        user = User.get_user_by_email(email)
        
        if not user:
            return False, "邮箱或密码错误", None
        
        # 验证密码
        if not user.get('password_hash'):
            return False, "此邮箱使用第三方登录，请使用对应的登录方式", None
        
        if not verify_password(password, user['password_hash']):
            return False, "邮箱或密码错误", None
        
        # 更新最后登录时间
        User.update_last_login(user['id'])
        
        # 设置session
        if _has_streamlit_context():
            st.session_state.user_id = user['id']
            st.session_state.username = user['username']
            st.session_state.login_method = 'email'
            
            # 设置Cookie（记住登录）
            if remember_me:
                AuthService._set_remember_cookie(user['id'])
        
        logger.info(f"✅ 用户登录成功: {user['username']}")
        return True, "登录成功", user
    
    @staticmethod
    def login_with_google(google_user_info: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """
        使用Google账号登录或注册
        
        Args:
            google_user_info: Google用户信息（从st.user获取）
        
        Returns:
            (成功标志, 消息, 用户信息)
        """
        google_sub = google_user_info.get('sub')
        google_email = google_user_info.get('email')
        google_name = google_user_info.get('name')
        google_picture = google_user_info.get('picture')
        
        if not google_sub:
            return False, "无法获取Google用户信息", None
        
        # 查找是否已有OAuth绑定
        oauth_account = OAuthAccount.get_oauth_account('google', google_sub)
        
        if oauth_account:
            # OAuth账号已绑定，直接登录
            user = User.get_user_by_id(oauth_account['user_id'])
            if user:
                User.update_last_login(user['id'])
                
                if _has_streamlit_context():
                    st.session_state.user_id = user['id']
                    st.session_state.username = user['username']
                    st.session_state.login_method = 'google'
                    st.session_state.google_info = google_user_info
                
                logger.info(f"✅ Google用户登录成功: {user['username']}")
                return True, "登录成功", user
        
        # 新用户，检查邮箱是否已被注册
        existing_user = User.get_user_by_email(google_email) if google_email else None
        
        if existing_user:
            # 邮箱已存在，绑定Google账号到现有用户
            oauth_id = OAuthAccount.create_oauth_account(
                user_id=existing_user['id'],
                provider='google',
                provider_user_id=google_sub,
                extra_data=google_user_info
            )
            
            if oauth_id:
                User.update_last_login(existing_user['id'])
                
                if _has_streamlit_context():
                    st.session_state.user_id = existing_user['id']
                    st.session_state.username = existing_user['username']
                    st.session_state.login_method = 'google'
                    st.session_state.google_info = google_user_info
                
                logger.info(f"✅ Google账号已绑定到现有用户: {existing_user['username']}")
                return True, "登录成功，Google账号已绑定", existing_user
        
        # 创建新用户
        username = google_email.split('@')[0] if google_email else f"google_{google_sub[:8]}"
        
        # 确保用户名唯一
        base_username = username
        counter = 1
        while User.get_user_by_username(username):
            username = f"{base_username}_{counter}"
            counter += 1
        
        user_id = User.create_user(
            username=username,
            email=google_email,
            display_name=google_name or username,
            avatar_url=google_picture
        )
        
        if not user_id:
            return False, "创建用户失败", None
        
        # 绑定OAuth账号
        oauth_id = OAuthAccount.create_oauth_account(
            user_id=user_id,
            provider='google',
            provider_user_id=google_sub,
            extra_data=google_user_info
        )
        
        if not oauth_id:
            return False, "绑定Google账号失败", None
        
        # 设置session
        user = User.get_user_by_id(user_id)
        if _has_streamlit_context():
            st.session_state.user_id = user_id
            st.session_state.username = username
            st.session_state.login_method = 'google'
            st.session_state.google_info = google_user_info
        
        logger.info(f"✅ 新用户通过Google注册: {username}")
        return True, "注册并登录成功", user
    
    @staticmethod
    def login_with_wechat(wechat_user_info: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """
        使用微信账号登录或注册
        
        Args:
            wechat_user_info: 微信用户信息
        
        Returns:
            (成功标志, 消息, 用户信息)
        """
        wechat_unionid = wechat_user_info.get('unionid')
        wechat_openid = wechat_user_info.get('openid')
        wechat_nickname = wechat_user_info.get('nickname')
        wechat_headimgurl = wechat_user_info.get('headimgurl')
        
        # 优先使用unionid，如果没有则使用openid
        wechat_id = wechat_unionid or wechat_openid
        
        if not wechat_id:
            return False, "无法获取微信用户信息", None
        
        # 查找是否已有OAuth绑定
        oauth_account = OAuthAccount.get_oauth_account('wechat', wechat_id)
        
        if oauth_account:
            # OAuth账号已绑定，直接登录
            user = User.get_user_by_id(oauth_account['user_id'])
            if user:
                User.update_last_login(user['id'])
                
                if _has_streamlit_context():
                    st.session_state.user_id = user['id']
                    st.session_state.username = user['username']
                    st.session_state.login_method = 'wechat'
                    st.session_state.wechat_user_info = wechat_user_info
                
                logger.info(f"✅ 微信用户登录成功: {user['username']}")
                return True, "登录成功", user
        
        # 新用户，创建账号
        username = f"wechat_{wechat_id[:12]}"
        
        # 确保用户名唯一
        base_username = username
        counter = 1
        while User.get_user_by_username(username):
            username = f"{base_username}_{counter}"
            counter += 1
        
        user_id = User.create_user(
            username=username,
            display_name=wechat_nickname or username,
            avatar_url=wechat_headimgurl
        )
        
        if not user_id:
            return False, "创建用户失败", None
        
        # 绑定OAuth账号
        oauth_id = OAuthAccount.create_oauth_account(
            user_id=user_id,
            provider='wechat',
            provider_user_id=wechat_id,
            extra_data=wechat_user_info
        )
        
        if not oauth_id:
            return False, "绑定微信账号失败", None
        
        # 设置session
        user = User.get_user_by_id(user_id)
        if _has_streamlit_context():
            st.session_state.user_id = user_id
            st.session_state.username = username
            st.session_state.login_method = 'wechat'
            st.session_state.wechat_user_info = wechat_user_info
        
        logger.info(f"✅ 新用户通过微信注册: {username}")
        return True, "注册并登录成功", user
    
    @staticmethod
    def _set_remember_cookie(user_id: int):
        """设置记住登录的Cookie"""
        try:
            expiry = datetime.now() + timedelta(days=30)
            auth_data = {
                "user_id": user_id,
                "expiry": expiry.isoformat()
            }
            auth_token = base64.b64encode(json.dumps(auth_data).encode("utf-8")).decode("utf-8")
            
            cookie_manager = get_cookie_manager()
            cookie_manager.set("auth_token_v2", auth_token, expires_at=expiry)
        except Exception as e:
            logger.error(f"设置Cookie失败: {e}")
    
    @staticmethod
    def check_cookie_auth() -> Optional[Dict]:
        """检查Cookie中的登录信息"""
        if not _has_streamlit_context():
            return None
        
        try:
            cookie_manager = get_cookie_manager()
            auth_token = cookie_manager.get("auth_token_v2")
            
            if not auth_token:
                return None
            
            # 解码token
            auth_data = json.loads(base64.b64decode(auth_token).decode("utf-8"))
            user_id = auth_data.get("user_id")
            expiry = auth_data.get("expiry")
            
            # 检查是否过期
            if expiry and datetime.fromisoformat(expiry) > datetime.now():
                user = User.get_user_by_id(user_id)
                if user:
                    # 恢复session
                    st.session_state.user_id = user['id']
                    st.session_state.username = user['username']
                    st.session_state.login_method = 'cookie'
                    return user
        except Exception as e:
            logger.error(f"Cookie认证失败: {e}")
        
        return None
    
    @staticmethod
    def is_authenticated() -> bool:
        """检查用户是否已登录"""
        if not _has_streamlit_context():
            return False
        
        # 检查session
        if 'user_id' in st.session_state and st.session_state.user_id:
            return True
        
        # 检查Google OAuth
        try:
            if hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
                # 处理Google登录
                google_info = {
                    'sub': getattr(st.user, 'sub', None),
                    'email': getattr(st.user, 'email', None),
                    'name': getattr(st.user, 'name', None),
                    'picture': getattr(st.user, 'picture', None)
                }
                success, msg, user = AuthService.login_with_google(google_info)
                return success
        except:
            pass
        
        # 检查Cookie
        user = AuthService.check_cookie_auth()
        return user is not None
    
    @staticmethod
    def get_current_user() -> Optional[Dict]:
        """获取当前登录用户信息"""
        if not _has_streamlit_context():
            return None
        
        if 'user_id' not in st.session_state:
            return None
        
        user_id = st.session_state.user_id
        return User.get_user_by_id(user_id)
    
    @staticmethod
    def get_user_id() -> Optional[int]:
        """获取当前用户ID"""
        user = AuthService.get_current_user()
        return user['id'] if user else None
    
    @staticmethod
    def get_user_display_name() -> str:
        """获取用户显示名称"""
        user = AuthService.get_current_user()
        if user:
            return user.get('display_name') or user.get('username') or "用户"
        return "用户"
    
    @staticmethod
    def logout():
        """退出登录"""
        if not _has_streamlit_context():
            return
        
        # 清除session
        keys_to_remove = ['user_id', 'username', 'login_method', 'google_info', 'wechat_user_info']
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
        
        # 清除Cookie
        try:
            cookie_manager = get_cookie_manager()
            cookie_manager.delete("auth_token_v2")
        except:
            pass
        
        # Google OAuth登出
        try:
            if hasattr(st, "logout"):
                st.logout()
        except:
            pass
        
        logger.info("✅ 用户已退出登录")
    
    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """修改密码"""
        user = User.get_user_by_id(user_id)
        if not user:
            return False, "用户不存在"
        
        # 验证旧密码
        if not user.get('password_hash'):
            return False, "此账号使用第三方登录，无法修改密码"
        
        if not verify_password(old_password, user['password_hash']):
            return False, "当前密码不正确"
        
        # 更新密码
        new_password_hash = hash_password(new_password)
        if User.update_user(user_id, password_hash=new_password_hash):
            logger.info(f"✅ 用户修改密码成功: {user['username']}")
            return True, "密码修改成功"
        else:
            return False, "密码修改失败"
    
    @staticmethod
    def update_profile(user_id: int, **kwargs) -> Tuple[bool, str]:
        """更新用户资料"""
        if User.update_user(user_id, **kwargs):
            return True, "更新成功"
        else:
            return False, "更新失败"


# 向后兼容的函数
def is_authenticated() -> bool:
    """向后兼容：检查是否已登录"""
    return AuthService.is_authenticated()


def get_current_user():
    """向后兼容：获取当前用户"""
    user = AuthService.get_current_user()
    return user['username'] if user else None


def get_user_id():
    """向后兼容：获取用户ID"""
    user = AuthService.get_current_user()
    return user['username'] if user else None


def get_user_display_name() -> str:
    """向后兼容：获取用户显示名称"""
    return AuthService.get_user_display_name()


def logout():
    """向后兼容：退出登录"""
    AuthService.logout()
