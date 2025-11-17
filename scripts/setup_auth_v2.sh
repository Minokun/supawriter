#!/bin/bash
# SupaWriter 认证系统 V2 快速部署脚本

set -e

echo "=================================================="
echo "  SupaWriter 认证系统 V2 部署工具"
echo "=================================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "项目目录: $PROJECT_ROOT"
echo ""

# 1. 检查Python环境
echo "📦 检查Python环境..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ 未找到Python，请先安装Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✅ Python版本: $PYTHON_VERSION${NC}"
echo ""

# 2. 检查PostgreSQL
echo "🗄️  检查PostgreSQL..."
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✅ PostgreSQL已安装${NC}"
else
    echo -e "${YELLOW}⚠️  未检测到PostgreSQL客户端${NC}"
    echo "   如果使用Docker，请确保PostgreSQL容器已启动"
fi
echo ""

# 3. 安装Python依赖
echo "📦 安装Python依赖..."
if [ -f "requirements.txt" ]; then
    $PYTHON_CMD -m pip install -q psycopg2-binary
    echo -e "${GREEN}✅ psycopg2-binary 已安装${NC}"
else
    echo -e "${RED}❌ 未找到requirements.txt${NC}"
    exit 1
fi
echo ""

# 4. 检查环境配置
echo "⚙️  检查环境配置..."
if [ -f "deployment/.env" ]; then
    echo -e "${GREEN}✅ 找到 deployment/.env${NC}"
    
    # 加载环境变量
    set -a
    source deployment/.env
    set +a
    
    if [ -z "$DATABASE_URL" ]; then
        echo -e "${YELLOW}⚠️  未找到DATABASE_URL，尝试构建...${NC}"
        if [ -n "$POSTGRES_HOST" ] && [ -n "$POSTGRES_USER" ] && [ -n "$POSTGRES_DB" ]; then
            export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
            echo -e "${GREEN}✅ DATABASE_URL已构建${NC}"
        else
            echo -e "${RED}❌ 缺少必要的数据库配置${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ DATABASE_URL已配置${NC}"
    fi
else
    echo -e "${RED}❌ 未找到 deployment/.env${NC}"
    echo "   请根据 deployment/.env.example 创建配置文件"
    exit 1
fi
echo ""

# 5. 测试数据库连接
echo "🔌 测试数据库连接..."
$PYTHON_CMD -c "
import sys
try:
    from utils.database import Database
    with Database.get_cursor() as cursor:
        cursor.execute('SELECT version();')
        version = cursor.fetchone()
        print('✅ 数据库连接成功')
        print(f'   PostgreSQL版本: {version[\"version\"][:50]}...')
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
    sys.exit(1)
" || {
    echo -e "${RED}❌ 数据库连接失败${NC}"
    echo "   请检查："
    echo "   1. PostgreSQL是否已启动"
    echo "   2. deployment/.env中的数据库配置是否正确"
    echo "   3. 数据库是否已创建"
    exit 1
}
echo ""

# 6. 执行数据库迁移
echo "🔄 执行数据库迁移..."
read -p "是否执行数据库迁移？这将创建表结构并迁移现有用户数据。(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $PYTHON_CMD scripts/migrate_database.py
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 数据库迁移完成${NC}"
    else
        echo -e "${RED}❌ 数据库迁移失败${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⏭️  跳过数据库迁移${NC}"
fi
echo ""

# 7. 运行测试
echo "🧪 运行认证系统测试..."
read -p "是否运行认证系统测试？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $PYTHON_CMD scripts/test_auth_system.py
else
    echo -e "${YELLOW}⏭️  跳过测试${NC}"
fi
echo ""

# 8. 完成提示
echo "=================================================="
echo -e "${GREEN}✅ 认证系统V2部署完成！${NC}"
echo "=================================================="
echo ""
echo "下一步："
echo "1. 启动Streamlit应用:"
echo "   streamlit run web.py"
echo ""
echo "2. 在应用中使用新的登录页面:"
echo "   from auth_pages import login_v2"
echo "   login_v2.app()"
echo ""
echo "3. 查看详细文档:"
echo "   AUTHENTICATION_V2_GUIDE.md"
echo ""
echo "4. 测试账号 (如果运行了迁移):"
echo "   用户名: admin"
echo "   密码: admin123"
echo ""
echo "=================================================="
