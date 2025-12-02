# -*- coding: utf-8 -*-
"""
微信开放平台 OAuth2 登录模块

使用微信开放平台的网站应用接入方式，实现微信扫码登录功能。
官方文档：https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
"""

import requests
import streamlit as st
from typing import Dict, Optional, Tuple
import json
from urllib.parse import urlencode, quote
import hashlib
import time


class WeChatOAuth:
    """微信开放平台 OAuth2 登录类"""
    
    # 微信开放平台 OAuth2 端点
    AUTHORIZE_URL = "https://open.weixin.qq.com/connect/qrconnect"
    ACCESS_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
    REFRESH_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/refresh_token"
    USER_INFO_URL = "https://api.weixin.qq.com/sns/userinfo"
    
    def __init__(self, app_id: str, app_secret: str, redirect_uri: str):
        """
        初始化微信 OAuth 客户端
        
        Args:
            app_id: 微信开放平台应用的 AppID
            app_secret: 微信开放平台应用的 AppSecret
            redirect_uri: 授权回调地址（需要在微信开放平台配置）
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        生成微信 OAuth 授权 URL（扫码登录页面）
        
        Args:
            state: 用于防止CSRF攻击的随机字符串，会原样返回
            
        Returns:
            授权URL，引导用户扫码登录
        """
        if state is None:
            # 生成一个基于时间戳的 state
            state = hashlib.md5(str(time.time()).encode()).hexdigest()
        
        params = {
            'appid': self.app_id,
            'redirect_uri': quote(self.redirect_uri, safe=''),
            'response_type': 'code',
            'scope': 'snsapi_login',  # 网站应用使用 snsapi_login
            'state': state,
        }
        
        # 微信要求最后添加 #wechat_redirect
        auth_url = f"{self.AUTHORIZE_URL}?{urlencode(params)}#wechat_redirect"
        return auth_url
    
    def get_access_token(self, code: str) -> Tuple[bool, Dict]:
        """
        使用授权码换取 access_token
        
        Args:
            code: 微信授权码
            
        Returns:
            (成功标志, 返回数据字典)
            成功时包含: access_token, expires_in, refresh_token, openid, scope, unionid
        """
        params = {
            'appid': self.app_id,
            'secret': self.app_secret,
            'code': code,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.get(self.ACCESS_TOKEN_URL, params=params, timeout=10)
            data = response.json()
            
            # 检查是否有错误
            if 'errcode' in data:
                return False, {'error': data.get('errmsg', '获取access_token失败')}
            
            return True, data
        except Exception as e:
            return False, {'error': f'请求失败: {str(e)}'}
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, Dict]:
        """
        刷新 access_token（当 access_token 过期时使用）
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            (成功标志, 返回数据字典)
        """
        params = {
            'appid': self.app_id,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        try:
            response = requests.get(self.REFRESH_TOKEN_URL, params=params, timeout=10)
            data = response.json()
            
            if 'errcode' in data:
                return False, {'error': data.get('errmsg', '刷新token失败')}
            
            return True, data
        except Exception as e:
            return False, {'error': f'请求失败: {str(e)}'}
    
    def get_user_info(self, access_token: str, openid: str) -> Tuple[bool, Dict]:
        """
        获取用户个人信息
        
        Args:
            access_token: 访问令牌
            openid: 用户的唯一标识
            
        Returns:
            (成功标志, 用户信息字典)
            包含: openid, nickname, sex, province, city, country, headimgurl, unionid
        """
        params = {
            'access_token': access_token,
            'openid': openid,
            'lang': 'zh_CN'
        }
        
        try:
            response = requests.get(self.USER_INFO_URL, params=params, timeout=10)
            data = response.json()
            
            if 'errcode' in data:
                return False, {'error': data.get('errmsg', '获取用户信息失败')}
            
            return True, data
        except Exception as e:
            return False, {'error': f'请求失败: {str(e)}'}


def init_wechat_oauth() -> Optional[WeChatOAuth]:
    """
    从 Streamlit secrets 初始化微信 OAuth 客户端
    
    Returns:
        WeChatOAuth 实例，如果配置不存在则返回 None
    """
    try:
        app_id = st.secrets.get("wechat", {}).get("app_id")
        app_secret = st.secrets.get("wechat", {}).get("app_secret")
        redirect_uri = st.secrets.get("wechat", {}).get("redirect_uri")
        
        if not all([app_id, app_secret, redirect_uri]):
            return None
        
        return WeChatOAuth(app_id, app_secret, redirect_uri)
    except Exception:
        return None


def wechat_login_flow():
    """
    处理微信登录流程的 Streamlit UI 函数
    
    调用此函数会显示微信登录按钮和处理回调
    """
    oauth = init_wechat_oauth()
    
    if oauth is None:
        st.error("⚠️ 微信登录未配置，请在 secrets.toml 中添加微信应用配置")
        return False
    
    # 从URL参数中获取微信回调的 code
    query_params = st.query_params
    code = query_params.get("code")
    state = query_params.get("state")
    
    # 如果有 code，说明用户已经授权，处理登录
    if code:
        # 验证 state（防止 CSRF）
        if state and 'wechat_state' in st.session_state:
            if state != st.session_state.wechat_state:
                st.error("❌ 状态验证失败，请重新登录")
                return False
        
        with st.spinner("正在获取微信用户信息..."):
            # 获取 access_token
            success, token_data = oauth.get_access_token(code)
            if not success:
                st.error(f"❌ 获取访问令牌失败: {token_data.get('error')}")
                return False
            
            access_token = token_data.get('access_token')
            openid = token_data.get('openid')
            refresh_token = token_data.get('refresh_token')
            
            # 获取用户信息
            success, user_info = oauth.get_user_info(access_token, openid)
            if not success:
                st.error(f"❌ 获取用户信息失败: {user_info.get('error')}")
                return False
            
            # 保存用户信息到 session_state
            st.session_state.user = openid  # 使用 openid 作为用户标识
            st.session_state.wechat_user_info = user_info
            st.session_state.wechat_access_token = access_token
            st.session_state.wechat_refresh_token = refresh_token
            
            # 清除 URL 参数
            st.query_params.clear()
            
            st.success(f"✅ 欢迎回来，{user_info.get('nickname', '用户')}！")
            st.rerun()
            
        return True
    
    # 显示微信登录按钮
    if st.button("🔐 使用微信登录", type="primary", use_container_width=True):
        # 生成 state 并保存
        state = hashlib.md5(str(time.time()).encode()).hexdigest()
        st.session_state.wechat_state = state
        
        # 生成授权 URL
        auth_url = oauth.get_authorization_url(state)
        
        # 重定向到微信授权页面
        st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
        st.info("🔄 正在跳转到微信登录页面...")
    
    return False


def get_wechat_user_display_name() -> str:
    """
    获取微信用户的显示名称
    
    Returns:
        用户昵称或默认值
    """
    if 'wechat_user_info' in st.session_state:
        return st.session_state.wechat_user_info.get('nickname', '微信用户')
    return '用户'


def is_wechat_authenticated() -> bool:
    """
    检查用户是否通过微信登录
    
    Returns:
        True 如果已登录
    """
    return 'wechat_user_info' in st.session_state and st.session_state.get('user') is not None


def wechat_logout():
    """
    退出微信登录
    """
    if 'wechat_user_info' in st.session_state:
        del st.session_state.wechat_user_info
    if 'wechat_access_token' in st.session_state:
        del st.session_state.wechat_access_token
    if 'wechat_refresh_token' in st.session_state:
        del st.session_state.wechat_refresh_token
    if 'wechat_state' in st.session_state:
        del st.session_state.wechat_state
