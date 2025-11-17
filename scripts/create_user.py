#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员工具：手动创建用户
用于管理员直接在数据库中创建用户账号
"""

import sys
import os
from pathlib import Path
import argparse
import getpass

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.auth_v2 import AuthService


def create_user_interactive():
    """交互式创建用户"""
    print("=" * 60)
    print("SupaWriter 用户创建工具（交互式）")
    print("=" * 60)
    print()
    
    # 收集用户信息
    username = input("请输入用户名（至少3个字符）: ").strip()
    email = input("请输入邮箱地址: ").strip()
    display_name = input("请输入显示名称（可选，直接回车跳过）: ").strip()
    
    # 安全输入密码
    password = getpass.getpass("请输入密码（至少8个字符）: ")
    confirm_password = getpass.getpass("请再次输入密码: ")
    
    # 验证密码
    if password != confirm_password:
        print("❌ 两次输入的密码不一致")
        return False
    
    # 创建用户
    return create_user(username, email, password, display_name or username)


def create_user(username, email, password, display_name=None):
    """创建用户"""
    print()
    print("正在创建用户...")
    print(f"  用户名: {username}")
    print(f"  邮箱: {email}")
    print(f"  显示名称: {display_name or username}")
    print()
    
    try:
        success, message = AuthService.register_with_email(
            username=username,
            email=email,
            password=password,
            display_name=display_name or username
        )
        
        if success:
            print(f"✅ {message}")
            print()
            print("用户信息：")
            print(f"  用户名: {username}")
            print(f"  邮箱: {email}")
            print(f"  登录密码: [已加密存储]")
            print()
            print("用户可以使用以下方式登录：")
            print(f"  - 邮箱登录: {email}")
            print(f"  - 密码: [创建时设置的密码]")
            return True
        else:
            print(f"❌ 创建失败: {message}")
            return False
            
    except Exception as e:
        print(f"❌ 创建用户时发生错误: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='SupaWriter 用户创建工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互式创建用户
  python scripts/create_user.py
  
  # 命令行参数创建用户
  python scripts/create_user.py --username john --email john@example.com --password SecurePass123!
  
  # 指定显示名称
  python scripts/create_user.py --username john --email john@example.com --password SecurePass123! --display-name "John Doe"
        """
    )
    
    parser.add_argument('--username', help='用户名（至少3个字符）')
    parser.add_argument('--email', help='邮箱地址')
    parser.add_argument('--password', help='密码（至少8个字符）')
    parser.add_argument('--display-name', dest='display_name', help='显示名称（可选）')
    parser.add_argument('--batch', help='批量创建用户（JSON文件路径）')
    
    args = parser.parse_args()
    
    # 批量创建模式
    if args.batch:
        import json
        print(f"正在从文件批量创建用户: {args.batch}")
        try:
            with open(args.batch, 'r', encoding='utf-8') as f:
                users = json.load(f)
            
            success_count = 0
            fail_count = 0
            
            for user_data in users:
                if create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    display_name=user_data.get('display_name')
                ):
                    success_count += 1
                else:
                    fail_count += 1
                print("-" * 60)
            
            print()
            print(f"批量创建完成: 成功 {success_count} 个, 失败 {fail_count} 个")
            
        except Exception as e:
            print(f"❌ 批量创建失败: {e}")
            sys.exit(1)
        
        sys.exit(0)
    
    # 命令行参数模式
    if args.username and args.email and args.password:
        success = create_user(
            username=args.username,
            email=args.email,
            password=args.password,
            display_name=args.display_name
        )
        sys.exit(0 if success else 1)
    
    # 交互式模式
    elif not any([args.username, args.email, args.password]):
        success = create_user_interactive()
        sys.exit(0 if success else 1)
    
    # 参数不完整
    else:
        print("❌ 错误: 请提供完整的参数（username, email, password）或不提供参数使用交互式模式")
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
