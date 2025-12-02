#!/bin/bash

# 每日新闻生成脚本
# 用法: ./run_daily_news.sh

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 进入项目根目录
cd "$PROJECT_ROOT"

echo "=========================================="
echo "🚀 每日AI新闻生成器"
echo "=========================================="
echo "项目目录: $PROJECT_ROOT"
echo "执行时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 检查uv环境
if command -v uv &> /dev/null; then
    PYTHON_CMD="uv run python"
    echo "使用uv环境: $PYTHON_CMD"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo "使用系统Python: $PYTHON_CMD"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    echo "使用系统Python: $PYTHON_CMD"
else
    echo "❌ 错误: 未找到Python环境"
    exit 1
fi

# 执行新闻生成脚本
echo "开始生成每日新闻..."
$PYTHON_CMD scripts/generate_daily_news.py

# 检查执行结果
if [ $? -eq 0 ]; then
    echo "✅ 每日新闻生成完成"
else
    echo "❌ 每日新闻生成失败"
    exit 1
fi

echo "=========================================="
echo "任务完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
