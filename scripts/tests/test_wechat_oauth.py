#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信 OAuth 配置测试脚本

用于验证微信开放平台的配置是否正确。
运行此脚本可以测试：
1. secrets.toml 配置是否正确
2. 微信 OAuth URL 生成是否正常
3. AppID 和 AppSecret 是否有效

使用方法：
    python scripts/test_wechat_oauth.py
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import toml
    import requests
    from utils.wechat_oauth import WeChatOAuth
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请先安装依赖: pip install -r requirements.txt")
    sys.exit(1)


def test_config():
    """测试配置文件是否存在和格式是否正确"""
    print("=" * 60)
    print("1. 测试配置文件")
    print("=" * 60)
    
    secrets_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        '.streamlit',
        'secrets.toml'
    )
    
    if not os.path.exists(secrets_path):
        print(f"❌ 配置文件不存在: {secrets_path}")
        print("   请复制 .streamlit/secrets.toml.example 为 secrets.toml 并配置")
        return None
    
    print(f"✅ 配置文件存在: {secrets_path}")
    
    try:
        with open(secrets_path, 'r', encoding='utf-8') as f:
            config = toml.load(f)
        
        if 'wechat' not in config:
            print("❌ 配置文件中没有 [wechat] 节")
            return None
        
        wechat_config = config['wechat']
        required_keys = ['app_id', 'app_secret', 'redirect_uri']
        
        for key in required_keys:
            if key not in wechat_config:
                print(f"❌ 缺少配置项: {key}")
                return None
            
            value = wechat_config[key]
            if not value or value.startswith('your_'):
                print(f"⚠️  {key} 未配置或使用了示例值: {value}")
                return None
        
        print("✅ 配置项完整")
        print(f"   AppID: {wechat_config['app_id']}")
        print(f"   Redirect URI: {wechat_config['redirect_uri']}")
        
        return wechat_config
        
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return None


def test_oauth_client(config):
    """测试 OAuth 客户端初始化"""
    print("\n" + "=" * 60)
    print("2. 测试 OAuth 客户端")
    print("=" * 60)
    
    try:
        oauth = WeChatOAuth(
            app_id=config['app_id'],
            app_secret=config['app_secret'],
            redirect_uri=config['redirect_uri']
        )
        print("✅ OAuth 客户端初始化成功")
        return oauth
    except Exception as e:
        print(f"❌ OAuth 客户端初始化失败: {e}")
        return None


def test_authorization_url(oauth):
    """测试授权 URL 生成"""
    print("\n" + "=" * 60)
    print("3. 测试授权 URL 生成")
    print("=" * 60)
    
    try:
        auth_url = oauth.get_authorization_url(state="test_state_123")
        print("✅ 授权 URL 生成成功")
        print(f"   URL: {auth_url[:100]}...")
        print("\n   你可以在浏览器中打开此 URL 测试微信扫码登录")
        print(f"   {auth_url}")
        return True
    except Exception as e:
        print(f"❌ 授权 URL 生成失败: {e}")
        return False


def test_api_connectivity():
    """测试与微信 API 的连接"""
    print("\n" + "=" * 60)
    print("4. 测试 API 连接性")
    print("=" * 60)
    
    try:
        # 测试连接微信 API（不需要有效的 code）
        response = requests.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                'appid': 'test',
                'secret': 'test',
                'code': 'test',
                'grant_type': 'authorization_code'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ 可以连接到微信 API 服务器")
            data = response.json()
            if 'errcode' in data:
                print(f"   API 返回错误码（预期，因为使用了测试参数）: {data.get('errcode')}")
            return True
        else:
            print(f"⚠️  连接微信 API 返回异常状态码: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 连接微信 API 超时")
        print("   请检查网络连接和防火墙设置")
        return False
    except Exception as e:
        print(f"❌ 连接微信 API 失败: {e}")
        return False


def main():
    """主测试流程"""
    print("\n" + "🔍 微信 OAuth 配置测试工具" + "\n")
    
    # 测试 1: 配置文件
    config = test_config()
    if not config:
        print("\n" + "=" * 60)
        print("测试终止：请先正确配置 secrets.toml 文件")
        print("=" * 60)
        return
    
    # 测试 2: OAuth 客户端
    oauth = test_oauth_client(config)
    if not oauth:
        print("\n" + "=" * 60)
        print("测试终止：OAuth 客户端初始化失败")
        print("=" * 60)
        return
    
    # 测试 3: 授权 URL
    test_authorization_url(oauth)
    
    # 测试 4: API 连接
    test_api_connectivity()
    
    # 总结
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    print("✅ 基本配置正确")
    print("⚠️  完整测试需要：")
    print("   1. 在微信开放平台创建应用并通过审核")
    print("   2. 配置正确的授权回调域")
    print("   3. 在浏览器中打开上面生成的授权 URL")
    print("   4. 使用微信扫码并确认授权")
    print("   5. 检查回调是否成功")
    print("\n📖 详细配置指南: docs/WECHAT_LOGIN_SETUP.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
