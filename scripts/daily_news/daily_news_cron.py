#!/usr/bin/env python3
"""
每日新闻定时任务脚本
适用于cron定时执行，生成每日AI新闻摘要
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scripts.generate_daily_news import generate_daily_news_article
import logging
from datetime import datetime

# 配置日志
log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'daily_news.log')),
        logging.StreamHandler()
    ]
)

def main():
    """定时任务主函数"""
    try:
        logging.info("开始执行每日新闻生成任务")
        
        # 生成每日新闻
        result = generate_daily_news_article()
        
        if result:
            logging.info(f"每日新闻生成成功：{result}")
            return 0
        else:
            logging.error("每日新闻生成失败")
            return 1
            
    except Exception as e:
        logging.error(f"执行每日新闻任务时发生错误：{str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
