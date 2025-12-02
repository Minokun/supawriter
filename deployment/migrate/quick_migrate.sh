#!/bin/bash
# SupaWriter 数据快速迁移脚本
# 
# 使用方法:
#   1. 复制 .env.migration.example 为 .env.migration
#   2. 修改 .env.migration 中的 POSTGRES_PASSWORD
#   3. 运行此脚本: ./deployment/migrate/quick_migrate.sh

set -e  # 出错立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SupaWriter 数据迁移工具${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查 .env.migration 文件
ENV_FILE="$SCRIPT_DIR/.env.migration"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}错误: 找不到配置文件 .env.migration${NC}"
    echo ""
    echo "请先创建配置文件:"
    echo "  1. 复制示例文件: cp $SCRIPT_DIR/.env.migration.example $SCRIPT_DIR/.env.migration"
    echo "  2. 编辑配置文件: vim $SCRIPT_DIR/.env.migration"
    echo "  3. 设置数据库密码: POSTGRES_PASSWORD=YOUR_PASSWORD"
    echo ""
    exit 1
fi

# 加载环境变量
echo -e "${YELLOW}加载配置文件...${NC}"
set -a  # 自动导出所有变量
source "$ENV_FILE"
set +a

# 检查必需的环境变量
if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "YOUR_PASSWORD_HERE" ]; then
    echo -e "${RED}错误: 未设置数据库密码${NC}"
    echo ""
    echo "请编辑 $ENV_FILE 文件，设置正确的 POSTGRES_PASSWORD"
    echo ""
    echo "获取密码的方法:"
    echo "  ssh ubuntu@122.51.24.120 'cat /opt/supawriter/.env | grep POSTGRES_PASSWORD'"
    echo ""
    exit 1
fi

# 显示配置信息
echo ""
echo -e "${GREEN}数据库配置:${NC}"
echo "  主机: ${POSTGRES_HOST:-122.51.24.120}"
echo "  端口: ${POSTGRES_PORT:-5432}"
echo "  用户: ${POSTGRES_USER:-supawriter}"
echo "  数据库: ${POSTGRES_DB:-supawriter}"
echo "  密码: ${POSTGRES_PASSWORD:0:4}****"  # 只显示前4个字符
echo ""

# 检查Python环境
if command -v uv &> /dev/null; then
    PYTHON_CMD="uv run python"
    echo -e "${GREEN}使用 uv 运行 Python${NC}"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    echo -e "${YELLOW}使用系统 Python${NC}"
else
    echo -e "${RED}错误: 找不到 Python 环境${NC}"
    exit 1
fi

# 询问用户操作
echo ""
echo "请选择操作:"
echo "  1) 测试数据库连接"
echo "  2) 迁移所有用户数据"
echo "  3) 迁移指定用户数据"
echo "  4) 退出"
echo ""
read -p "请输入选项 [1-4]: " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}正在测试数据库连接...${NC}"
        cd "$PROJECT_DIR"
        $PYTHON_CMD deployment/migrate/migrate_to_pgsql.py --test
        ;;
    2)
        echo ""
        echo -e "${YELLOW}正在迁移所有用户数据...${NC}"
        echo ""
        read -p "确认要迁移所有用户数据吗? [y/N]: " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            cd "$PROJECT_DIR"
            $PYTHON_CMD deployment/migrate/migrate_to_pgsql.py
        else
            echo -e "${YELLOW}已取消迁移${NC}"
        fi
        ;;
    3)
        echo ""
        read -p "请输入用户名: " username
        if [ -z "$username" ]; then
            echo -e "${RED}错误: 用户名不能为空${NC}"
            exit 1
        fi
        echo ""
        echo -e "${YELLOW}正在迁移用户 $username 的数据...${NC}"
        cd "$PROJECT_DIR"
        $PYTHON_CMD deployment/migrate/migrate_to_pgsql.py --username "$username"
        ;;
    4)
        echo -e "${YELLOW}已退出${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}无效的选项${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}操作完成！${NC}"
echo -e "${GREEN}========================================${NC}"
