#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SupaWriter 统一启动脚本
整合 Streamlit 后端服务 + Next.js 前端服务
通过不同端口和路由实现前后端分离
"""

import os
import sys
import subprocess
import signal
import time
import logging
import shutil
import socket
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.resolve()

# 服务配置
SERVICES = {
    'streamlit': {
        'name': 'Streamlit 创作工具',
        'port': 8501,
        'command': ['uv', 'run', 'streamlit', 'run', 'web.py', '--server.port=8501'],
        'cwd': PROJECT_ROOT,
        'url': 'http://localhost:8501',
        'enabled': True
    },
    'frontend': {
        'name': 'Next.js 前端',
        'port': 3000,
        'command': ['npm', 'run', 'dev'],
        'cwd': PROJECT_ROOT / 'frontend',
        'url': 'http://localhost:3000',
        'enabled': False  # 默认关闭，可通过参数启用
    }
}

# 进程管理
processes = {}


def _inherit_stdio(stream):
    """Return a real stdio target when the parent stream supports fileno()."""
    return stream if stream is not None and hasattr(stream, "fileno") else None


def check_port_available(port):
    """检查端口是否可用"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def kill_process_on_port(port):
    """杀死占用指定端口的进程"""
    try:
        if sys.platform == 'darwin' or sys.platform == 'linux':
            # macOS/Linux
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        logger.info(f"✅ 已终止占用端口 {port} 的进程 (PID: {pid})")
                    except:
                        pass
                time.sleep(1)
        elif sys.platform == 'win32':
            # Windows
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if len(parts) > 4 and parts[1].endswith(f":{port}"):
                        pid = parts[-1]
                        try:
                            subprocess.run(['taskkill', '/F', '/PID', pid], check=False)
                            logger.info(f"✅ 已终止占用端口 {port} 的进程 (PID: {pid})")
                        except:
                            pass
                time.sleep(1)
    except Exception as e:
        logger.warning(f"⚠️ 无法自动清理端口 {port}: {e}")


def start_service(service_name, config):
    """启动单个服务"""
    if not config['enabled']:
        logger.info(f"⏭️ 跳过服务: {config['name']}")
        return None
    
    # 检查端口
    port = config['port']
    if not check_port_available(port):
        logger.warning(f"⚠️ 端口 {port} 已被占用，尝试清理...")
        kill_process_on_port(port)
        time.sleep(2)
        
        if not check_port_available(port):
            logger.error(f"❌ 端口 {port} 仍被占用，无法启动 {config['name']}")
            return None
    
    # 启动进程
    try:
        logger.info(f"🚀 启动服务: {config['name']} (端口: {port})")
        logger.info(f"   命令: {' '.join(config['command'])}")
        logger.info(f"   目录: {config['cwd']}")
        
        process = subprocess.Popen(
            config['command'],
            cwd=config['cwd'],
            stdout=_inherit_stdio(sys.stdout),
            stderr=_inherit_stdio(sys.stderr)
        )
        
        processes[service_name] = process
        logger.info(f"✅ {config['name']} 启动成功 (PID: {process.pid})")
        logger.info(f"   访问地址: {config['url']}")
        
        return process
        
    except Exception as e:
        logger.error(f"❌ 启动 {config['name']} 失败: {e}")
        return None


def stop_all_services():
    """停止所有服务"""
    logger.info("\n🛑 正在停止所有服务...")
    
    for service_name, process in processes.items():
        try:
            if process and process.poll() is None:
                logger.info(f"   停止 {SERVICES[service_name]['name']}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                logger.info(f"   ✅ {SERVICES[service_name]['name']} 已停止")
        except Exception as e:
            logger.error(f"   ❌ 停止服务失败: {e}")
    
    logger.info("✅ 所有服务已停止")


def signal_handler(sig, frame):
    """处理中断信号"""
    logger.info("\n\n⚠️ 收到中断信号，正在关闭...")
    stop_all_services()
    sys.exit(0)


def check_dependencies():
    """检查依赖是否安装"""
    logger.info("🔍 检查依赖...")
    
    uv_path = shutil.which('uv')
    if uv_path is None:
        logger.error("   ❌ uv 未安装，请先安装 uv")
        return False

    # 在实际启动使用的 uv 环境里检查 Streamlit
    try:
        result = subprocess.run(
            ['uv', 'run', 'python', '-c', 'import streamlit; print(streamlit.__version__)'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip() or result.stderr.strip() or "unknown"
        logger.info(f"   ✅ Streamlit 已安装 (版本: {version})")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("   ❌ 当前 uv 环境中未安装 Streamlit，请先运行 uv sync")
        return False
    
    # 检查前端依赖（如果启用）
    if SERVICES['frontend']['enabled']:
        frontend_dir = PROJECT_ROOT / 'frontend'
        if not (frontend_dir / 'node_modules').exists():
            logger.warning("   ⚠️ 前端依赖未安装")
            logger.info("   正在安装前端依赖...")
            try:
                subprocess.run(
                    ['npm', 'install'],
                    cwd=frontend_dir,
                    check=True
                )
                logger.info("   ✅ 前端依赖安装成功")
            except:
                logger.error("   ❌ 前端依赖安装失败")
                return False
    
    return True


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🚀 SupaWriter 统一启动系统 🚀                    ║
║                                                              ║
║              AI驱动的智能写作平台                             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """主函数"""
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='SupaWriter 统一启动脚本')
    parser.add_argument('--with-frontend', action='store_true', help='同时启动前端服务')
    parser.add_argument('--streamlit-only', action='store_true', help='仅启动 Streamlit 服务')
    args = parser.parse_args()
    
    # 配置服务
    if args.with_frontend:
        SERVICES['frontend']['enabled'] = True
    
    if args.streamlit_only:
        SERVICES['frontend']['enabled'] = False
    
    # 打印横幅
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        logger.error("❌ 依赖检查失败，请先安装必要的依赖")
        sys.exit(1)
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动服务
    logger.info("\n📦 启动服务...")
    logger.info("=" * 60)
    
    for service_name, config in SERVICES.items():
        start_service(service_name, config)
        time.sleep(2)  # 给服务一些启动时间
    
    # 打印访问信息
    logger.info("\n" + "=" * 60)
    logger.info("✅ 所有服务启动完成！")
    logger.info("=" * 60)
    
    enabled_services = [s for s in SERVICES.values() if s['enabled']]
    if enabled_services:
        logger.info("\n📍 访问地址:")
        for service in enabled_services:
            logger.info(f"   • {service['name']}: {service['url']}")
    
    logger.info("\n💡 提示:")
    logger.info("   • 按 Ctrl+C 停止所有服务")
    logger.info("   • 日志将实时显示在下方")
    logger.info("=" * 60 + "\n")
    
    # 监控进程
    try:
        while True:
            time.sleep(1)
            
            # 检查进程是否还在运行
            for service_name, process in list(processes.items()):
                if process.poll() is not None:
                    logger.error(f"❌ {SERVICES[service_name]['name']} 意外退出")
                    # 尝试重启
                    logger.info(f"🔄 尝试重启 {SERVICES[service_name]['name']}...")
                    new_process = start_service(service_name, SERVICES[service_name])
                    if new_process:
                        processes[service_name] = new_process
                    else:
                        del processes[service_name]
    
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == '__main__':
    main()
