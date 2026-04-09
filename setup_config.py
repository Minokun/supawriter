#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SupaWriter 配置初始化脚本
自动检查和修复配置问题
"""

import os
import sys
import secrets
import shutil
from pathlib import Path
import subprocess

PROJECT_ROOT = Path(__file__).parent.resolve()


def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def check_secrets_toml():
    """检查并初始化 secrets.toml"""
    print_section("检查 Streamlit 配置")
    
    secrets_file = PROJECT_ROOT / '.streamlit' / 'secrets.toml'
    template_file = PROJECT_ROOT / '.streamlit' / 'secrets.toml.template'
    
    if not secrets_file.exists():
        if template_file.exists():
            shutil.copy(template_file, secrets_file)
            print(f"✅ 已从模板创建 secrets.toml")
        else:
            print(f"❌ 模板文件不存在: {template_file}")
            return False
    else:
        print(f"✅ secrets.toml 已存在")
    
    # 检查关键配置
    with open(secrets_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    
    # 检查 cookie_secret
    if 'cookie_secret = "xxx"' in content:
        issues.append("cookie_secret 需要设置为随机字符串")
    
    # 检查 Google OAuth
    if 'client_id = ""' in content:
        issues.append("Google OAuth client_id 未配置")
    
    if 'client_secret = ""' in content:
        issues.append("Google OAuth client_secret 未配置")
    
    # 检查 API 密钥
    if 'api_key = "sk-"' in content or 'api_key = ""' in content:
        issues.append("至少需要配置一个 LLM API 密钥")
    
    if issues:
        print(f"\n⚠️  发现配置问题:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    
    print(f"✅ secrets.toml 配置完整")
    return True


def fix_cookie_secret():
    """修复 cookie_secret"""
    print_section("修复 Cookie Secret")
    
    secrets_file = PROJECT_ROOT / '.streamlit' / 'secrets.toml'
    
    with open(secrets_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'cookie_secret = "xxx"' in content:
        new_secret = secrets.token_urlsafe(32)
        content = content.replace('cookie_secret = "xxx"', f'cookie_secret = "{new_secret}"')
        
        with open(secrets_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已生成新的 cookie_secret")
        print(f"   值: {new_secret}")
        return True
    else:
        print(f"✅ cookie_secret 已配置")
        return True


def check_database_config():
    """检查数据库配置"""
    print_section("检查数据库配置")
    
    env_file = PROJECT_ROOT / 'deployment' / '.env'
    
    if not env_file.exists():
        print(f"⚠️  数据库配置文件不存在: {env_file}")
        print(f"   请创建 deployment/.env 文件并配置数据库连接")
        return False
    
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'DATABASE_URL' not in content and 'DB_HOST' not in content:
        print(f"❌ 数据库连接未配置")
        print(f"   请在 deployment/.env 中添加:")
        print(f"   DATABASE_URL=postgresql://user:password@host:5432/dbname")
        return False
    
    print(f"✅ 数据库配置文件存在")
    return True


def test_database_connection():
    """测试数据库连接"""
    print_section("测试数据库连接")
    
    try:
        from utils.database import Database
        
        with Database.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()
                print(f"✅ 数据库连接成功")
                print(f"   版本: {version[0][:50]}...")
                return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print(f"\n💡 解决方案:")
        print(f"   1. 确保 PostgreSQL 已启动")
        print(f"   2. 检查 deployment/.env 中的数据库配置")
        print(f"   3. 运行数据库迁移: python deployment/migrate/migrate_to_postgres.py")
        return False


def check_dependencies():
    """检查 Python 依赖"""
    print_section("检查 Python 依赖")
    
    required_packages = [
        'streamlit',
        'psycopg2',
        'extra_streamlit_components',
        'requests',
        'beautifulsoup4',
        'markdown'
    ]
    
    missing = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  缺少依赖包:")
        for pkg in missing:
            print(f"   • {pkg}")
        print(f"\n💡 运行以下命令安装:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True


def check_frontend():
    """检查前端配置"""
    print_section("检查前端配置")
    
    frontend_dir = PROJECT_ROOT / 'frontend'
    
    if not frontend_dir.exists():
        print(f"⚠️  前端目录不存在")
        return False
    
    if not (frontend_dir / 'package.json').exists():
        print(f"❌ package.json 不存在")
        return False
    
    print(f"✅ 前端目录存在")
    
    if not (frontend_dir / 'node_modules').exists():
        print(f"⚠️  前端依赖未安装")
        print(f"   运行: cd frontend && npm install")
        return False
    
    print(f"✅ 前端依赖已安装")
    return True


def print_google_oauth_guide():
    """打印 Google OAuth 配置指南"""
    print_section("Google OAuth 配置指南")
    
    print("""
📝 配置步骤:

1. 访问 Google Cloud Console
   https://console.cloud.google.com/

2. 创建或选择项目

3. 启用 Google+ API
   导航: APIs & Services > Library > Google+ API > Enable

4. 创建 OAuth 2.0 客户端 ID
   导航: APIs & Services > Credentials > Create Credentials > OAuth client ID
   
   配置:
   • 应用类型: Web application
   • 名称: SupaWriter
   • 授权的重定向 URI: 
     - http://localhost:8501/oauth2callback
     - http://localhost:8501/_stcore/oauth2callback
   
5. 复制 Client ID 和 Client Secret

6. 更新 .streamlit/secrets.toml:
   
   [auth.google]
   client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
   client_secret = "YOUR_CLIENT_SECRET"
   server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

7. 重启 Streamlit 应用
""")


def print_summary(results):
    """打印检查摘要"""
    print_section("配置检查摘要")
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")
    
    if all_passed:
        print(f"\n🎉 所有检查通过！可以启动应用了")
        print(f"\n启动命令:")
        print(f"   python start_unified.py")
    else:
        print(f"\n⚠️  请先修复上述问题，然后重新运行此脚本")
        print(f"\n重新检查:")
        print(f"   python setup_config.py")


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           🔧 SupaWriter 配置检查和修复工具 🔧                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    results = {}
    
    # 1. 检查 secrets.toml
    results['Secrets 配置'] = check_secrets_toml()
    
    # 2. 修复 cookie_secret
    if not results['Secrets 配置']:
        fix_cookie_secret()
    
    # 3. 检查数据库配置
    results['数据库配置'] = check_database_config()
    
    # 4. 测试数据库连接
    if results['数据库配置']:
        results['数据库连接'] = test_database_connection()
    else:
        results['数据库连接'] = False
    
    # 5. 检查依赖
    results['Python 依赖'] = check_dependencies()
    
    # 6. 检查前端
    results['前端配置'] = check_frontend()
    
    # 7. 打印 Google OAuth 指南
    print_google_oauth_guide()
    
    # 8. 打印摘要
    print_summary(results)


if __name__ == '__main__':
    main()
