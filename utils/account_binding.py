# -*- coding: utf-8 -*-
"""
账号绑定模块
支持将Google、微信等OAuth账号绑定到现有用户
支持为OAuth账号设置邮箱和密码
"""

import logging
from typing import Tuple, List, Dict, Any, Optional
from utils.database import User, OAuthAccount
from utils.auth_v2 import hash_password, verify_password

logger = logging.getLogger(__name__)


class AccountBindingService:
    """账号绑定服务类"""
    
    @staticmethod
    def bind_google_account(user_id: int, google_info: Dict) -> Tuple[bool, str]:
        """
        绑定Google账号到现有用户
        
        Args:
            user_id: 用户ID
            google_info: Google用户信息
        
        Returns:
            (成功标志, 消息)
        """
        google_sub = google_info.get('sub')
        
        if not google_sub:
            return False, "无效的Google账号信息"
        
        # 检查Google账号是否已被其他用户绑定
        existing_oauth = OAuthAccount.get_oauth_account('google', google_sub)
        if existing_oauth:
            if existing_oauth['user_id'] == user_id:
                return False, "此Google账号已绑定到您的账户"
            else:
                return False, "此Google账号已被其他用户绑定"
        
        # 创建绑定
        oauth_id = OAuthAccount.create_oauth_account(
            user_id=user_id,
            provider='google',
            provider_user_id=google_sub,
            extra_data=google_info
        )
        
        if oauth_id:
            logger.info(f"✅ Google账号已绑定到用户ID: {user_id}")
            return True, "Google账号绑定成功"
        else:
            return False, "绑定失败，请稍后重试"
    
    @staticmethod
    def bind_wechat_account(user_id: int, wechat_info: Dict) -> Tuple[bool, str]:
        """
        绑定微信账号到现有用户
        
        Args:
            user_id: 用户ID
            wechat_info: 微信用户信息
        
        Returns:
            (成功标志, 消息)
        """
        wechat_unionid = wechat_info.get('unionid')
        wechat_openid = wechat_info.get('openid')
        wechat_id = wechat_unionid or wechat_openid
        
        if not wechat_id:
            return False, "无效的微信账号信息"
        
        # 检查微信账号是否已被其他用户绑定
        existing_oauth = OAuthAccount.get_oauth_account('wechat', wechat_id)
        if existing_oauth:
            if existing_oauth['user_id'] == user_id:
                return False, "此微信账号已绑定到您的账户"
            else:
                return False, "此微信账号已被其他用户绑定"
        
        # 创建绑定
        oauth_id = OAuthAccount.create_oauth_account(
            user_id=user_id,
            provider='wechat',
            provider_user_id=wechat_id,
            extra_data=wechat_info
        )
        
        if oauth_id:
            logger.info(f"✅ 微信账号已绑定到用户ID: {user_id}")
            return True, "微信账号绑定成功"
        else:
            return False, "绑定失败，请稍后重试"
    
    @staticmethod
    def bind_email_and_password(
        user_id: int, 
        email: str, 
        password: str
    ) -> Tuple[bool, str]:
        """
        为OAuth用户设置邮箱和密码
        
        Args:
            user_id: 用户ID
            email: 邮箱地址
            password: 密码
        
        Returns:
            (成功标志, 消息)
        """
        # 验证输入
        if not email or '@' not in email:
            return False, "请输入有效的邮箱地址"
        
        if not password or len(password) < 8:
            return False, "密码至少8个字符"
        
        # 检查邮箱是否已被其他用户使用
        existing_user = User.get_user_by_email(email)
        if existing_user and existing_user['id'] != user_id:
            return False, "此邮箱已被其他用户使用"
        
        # 更新用户邮箱和密码
        password_hash = hash_password(password)
        success = User.update_user(
            user_id,
            email=email,
            password_hash=password_hash
        )
        
        if success:
            logger.info(f"✅ 用户ID {user_id} 已设置邮箱和密码")
            return True, "邮箱和密码设置成功，现在可以使用邮箱登录"
        else:
            return False, "设置失败，请稍后重试"
    
    @staticmethod
    def unbind_oauth_account(user_id: int, provider: str) -> Tuple[bool, str]:
        """
        解绑OAuth账号
        
        Args:
            user_id: 用户ID
            provider: OAuth提供商（google, wechat）
        
        Returns:
            (成功标志, 消息)
        """
        # 获取用户信息
        user = User.get_user_by_id(user_id)
        if not user:
            return False, "用户不存在"
        
        # 获取用户的所有OAuth账号
        oauth_accounts = OAuthAccount.get_user_oauth_accounts(user_id)
        
        # 检查是否可以解绑
        has_password = bool(user.get('password_hash'))
        oauth_count = len(oauth_accounts)
        
        if not has_password and oauth_count <= 1:
            return False, "至少需要保留一种登录方式，请先设置邮箱和密码"
        
        # 找到要解绑的OAuth账号
        target_oauth = None
        for oauth in oauth_accounts:
            if oauth['provider'] == provider:
                target_oauth = oauth
                break
        
        if not target_oauth:
            return False, f"未找到{provider}账号绑定"
        
        # 删除绑定
        if OAuthAccount.delete_oauth_account(target_oauth['id']):
            provider_name = "Google" if provider == "google" else "微信"
            logger.info(f"✅ 用户ID {user_id} 已解绑{provider_name}账号")
            return True, f"{provider_name}账号解绑成功"
        else:
            return False, "解绑失败，请稍后重试"
    
    @staticmethod
    def get_bound_accounts(user_id: int) -> List[Dict[str, Any]]:
        """
        获取用户已绑定的所有账号
        
        Args:
            user_id: 用户ID
        
        Returns:
            绑定账号列表
        """
        user = User.get_user_by_id(user_id)
        oauth_accounts = OAuthAccount.get_user_oauth_accounts(user_id)
        
        result = []
        
        # 邮箱账号
        if user and user.get('email') and user.get('password_hash'):
            result.append({
                'type': 'email',
                'provider': 'email',
                'identifier': user['email'],
                'display_name': '邮箱登录',
                'can_unbind': len(oauth_accounts) > 0  # 有OAuth账号时可以解绑
            })
        
        # OAuth账号
        for oauth in oauth_accounts:
            provider = oauth['provider']
            extra_data = oauth.get('extra_data', {})
            
            if isinstance(extra_data, str):
                import json
                try:
                    extra_data = json.loads(extra_data)
                except:
                    extra_data = {}
            
            if provider == 'google':
                result.append({
                    'type': 'oauth',
                    'provider': 'google',
                    'identifier': extra_data.get('email', oauth['provider_user_id']),
                    'display_name': 'Google账号',
                    'can_unbind': True
                })
            elif provider == 'wechat':
                result.append({
                    'type': 'oauth',
                    'provider': 'wechat',
                    'identifier': extra_data.get('nickname', oauth['provider_user_id']),
                    'display_name': '微信账号',
                    'can_unbind': True
                })
        
        return result
    
    @staticmethod
    def can_login_with_email(user_id: int) -> bool:
        """检查用户是否可以使用邮箱登录"""
        user = User.get_user_by_id(user_id)
        return bool(user and user.get('email') and user.get('password_hash'))
    
    @staticmethod
    def has_google_binding(user_id: int) -> bool:
        """检查用户是否已绑定Google账号"""
        oauth_accounts = OAuthAccount.get_user_oauth_accounts(user_id)
        return any(oauth['provider'] == 'google' for oauth in oauth_accounts)
    
    @staticmethod
    def has_wechat_binding(user_id: int) -> bool:
        """检查用户是否已绑定微信账号"""
        oauth_accounts = OAuthAccount.get_user_oauth_accounts(user_id)
        return any(oauth['provider'] == 'wechat' for oauth in oauth_accounts)
