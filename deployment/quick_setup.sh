#!/bin/bash
# SupaWriter 一键部署脚本
# 适用于全新部署或现有数据库升级

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${BLUE}=================================================="
echo "  SupaWriter 数据库一键部署"
echo "==================================================${NC}"
echo ""

# 检查部署模式
echo -e "${YELLOW}请选择部署模式：${NC}"
echo "1) 全新部署（Docker）"
echo "2) 升级现有数据库"
echo "3) 仅迁移历史数据"
echo ""
read -p "请输入选项 (1-3): " DEPLOY_MODE

case $DEPLOY_MODE in
    1)
        echo -e "${GREEN}✓ 选择：全新部署（Docker）${NC}"
        DEPLOY_TYPE="docker"
        ;;
    2)
        echo -e "${GREEN}✓ 选择：升级现有数据库${NC}"
        DEPLOY_TYPE="upgrade"
        ;;
    3)
        echo -e "${GREEN}✓ 选择：仅迁移历史数据${NC}"
        DEPLOY_TYPE="migrate"
        ;;
    *)
        echo -e "${RED}✗ 无效选项${NC}"
        exit 1
        ;;
esac

echo ""

# =============================================================================
# 模式 1: 全新部署（Docker）
# =============================================================================

if [ "$DEPLOY_TYPE" = "docker" ]; then
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}全新部署（Docker）${NC}"
    echo -e "${BLUE}===========================================${NC}"
    echo ""
    
    # 1. 检查Docker
    echo -e "${YELLOW}步骤 1/5: 检查Docker...${NC}"
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ 未安装Docker${NC}"
        echo "请先安装Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker已安装${NC}"
    echo ""
    
    # 2. 检查配置文件
    echo -e "${YELLOW}步骤 2/5: 检查配置...${NC}"
    if [ ! -f "deployment/.env" ]; then
        echo -e "${YELLOW}⚠ 未找到 deployment/.env${NC}"
        read -p "是否自动创建？(y/n) " CREATE_ENV
        if [[ $CREATE_ENV =~ ^[Yy]$ ]]; then
            cp deployment/.env.example deployment/.env
            echo -e "${GREEN}✓ 已创建 deployment/.env${NC}"
            echo -e "${YELLOW}⚠ 请编辑 deployment/.env 设置数据库密码${NC}"
            read -p "按Enter继续..."
        else
            echo -e "${RED}✗ 需要配置文件${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}✓ 配置文件存在${NC}"
    echo ""
    
    # 3. 启动PostgreSQL
    echo -e "${YELLOW}步骤 3/5: 启动PostgreSQL容器...${NC}"
    cd deployment
    docker-compose up -d postgres
    echo -e "${GREEN}✓ PostgreSQL容器已启动${NC}"
    echo ""
    
    # 4. 等待数据库就绪
    echo -e "${YELLOW}步骤 4/5: 等待数据库初始化...${NC}"
    echo "这可能需要10-30秒..."
    sleep 5
    
    MAX_WAIT=60
    WAITED=0
    while [ $WAITED -lt $MAX_WAIT ]; do
        if docker exec supawriter_postgres pg_isready -U supawriter -d supawriter &> /dev/null; then
            echo -e "${GREEN}✓ 数据库已就绪${NC}"
            break
        fi
        echo -n "."
        sleep 2
        WAITED=$((WAITED + 2))
    done
    
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo -e "${RED}✗ 数据库启动超时${NC}"
        echo "请查看日志: docker-compose logs postgres"
        exit 1
    fi
    echo ""
    
    # 5. 验证部署
    echo -e "${YELLOW}步骤 5/5: 验证部署...${NC}"
    cd ..
    
    # 检查表是否创建
    TABLE_COUNT=$(docker exec supawriter_postgres psql -U supawriter -d supawriter -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')
    
    if [ "$TABLE_COUNT" -ge 5 ]; then
        echo -e "${GREEN}✓ 数据库表已创建 (共 $TABLE_COUNT 个表)${NC}"
    else
        echo -e "${RED}✗ 数据库表创建失败${NC}"
        exit 1
    fi
    
    echo ""
    echo -e "${GREEN}=================================================="
    echo "✓ 全新部署完成！"
    echo "==================================================${NC}"
    echo ""
    echo "默认管理员账号："
    echo "  用户名: admin"
    echo "  密码: admin123"
    echo "  ⚠️  请立即修改密码！"
    echo ""
    echo "下一步："
    echo "  1. 启动应用: streamlit run web.py"
    echo "  2. 访问: http://localhost:8501"
    echo "  3. 使用admin/admin123登录"
    echo ""

fi

# =============================================================================
# 模式 2: 升级现有数据库
# =============================================================================

if [ "$DEPLOY_TYPE" = "upgrade" ]; then
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}升级现有数据库${NC}"
    echo -e "${BLUE}===========================================${NC}"
    echo ""
    
    # 1. 检查Python
    echo -e "${YELLOW}步骤 1/5: 检查Python环境...${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}✗ 未找到Python${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python: $($PYTHON_CMD --version)${NC}"
    echo ""
    
    # 2. 安装依赖
    echo -e "${YELLOW}步骤 2/5: 安装依赖...${NC}"
    $PYTHON_CMD -m pip install -q psycopg2-binary
    echo -e "${GREEN}✓ 依赖已安装${NC}"
    echo ""
    
    # 3. 备份数据库
    echo -e "${YELLOW}步骤 3/5: 备份数据库...${NC}"
    read -p "是否备份数据库？(强烈建议) (y/n) " BACKUP
    if [[ $BACKUP =~ ^[Yy]$ ]]; then
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
        echo "备份中..."
        
        # 从.env读取数据库配置
        if [ -f "deployment/.env" ]; then
            source deployment/.env
            pg_dump -h ${POSTGRES_HOST:-localhost} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-supawriter} -d ${POSTGRES_DB:-supawriter} > "$BACKUP_FILE" 2>/dev/null || true
            
            if [ -f "$BACKUP_FILE" ]; then
                echo -e "${GREEN}✓ 备份完成: $BACKUP_FILE${NC}"
            else
                echo -e "${YELLOW}⚠ 备份失败，但将继续${NC}"
            fi
        fi
    fi
    echo ""
    
    # 4. 执行迁移
    echo -e "${YELLOW}步骤 4/5: 执行数据库迁移...${NC}"
    $PYTHON_CMD scripts/migrate_database.py
    echo ""
    
    # 5. 验证迁移
    echo -e "${YELLOW}步骤 5/5: 验证迁移结果...${NC}"
    $PYTHON_CMD scripts/test_auth_system.py
    echo ""
    
    echo -e "${GREEN}=================================================="
    echo "✓ 数据库升级完成！"
    echo "==================================================${NC}"
    echo ""
    echo "新增表："
    echo "  - users (用户表)"
    echo "  - oauth_accounts (OAuth绑定表)"
    echo ""
    echo "默认管理员账号："
    echo "  用户名: admin"
    echo "  密码: admin123"
    echo ""

fi

# =============================================================================
# 模式 3: 迁移历史数据
# =============================================================================

if [ "$DEPLOY_TYPE" = "migrate" ]; then
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}迁移历史数据${NC}"
    echo -e "${BLUE}===========================================${NC}"
    echo ""
    
    # 检查数据目录
    echo -e "${YELLOW}检查数据目录...${NC}"
    
    if [ -f "data/users.pkl" ]; then
        echo -e "${GREEN}✓ 找到用户数据: data/users.pkl${NC}"
        HAS_USER_DATA=true
    else
        echo -e "${YELLOW}⚠ 未找到用户数据${NC}"
        HAS_USER_DATA=false
    fi
    
    if [ -d "data/history" ] && [ "$(ls -A data/history)" ]; then
        echo -e "${GREEN}✓ 找到文章数据: data/history/${NC}"
        HAS_ARTICLE_DATA=true
    else
        echo -e "${YELLOW}⚠ 未找到文章数据${NC}"
        HAS_ARTICLE_DATA=false
    fi
    
    echo ""
    
    # 迁移用户数据
    if [ "$HAS_USER_DATA" = true ]; then
        echo -e "${YELLOW}迁移用户数据...${NC}"
        python scripts/migrate_database.py
        echo ""
    fi
    
    # 迁移文章数据
    if [ "$HAS_ARTICLE_DATA" = true ]; then
        echo -e "${YELLOW}迁移文章数据...${NC}"
        read -p "是否迁移文章数据？(y/n) " MIGRATE_ARTICLES
        if [[ $MIGRATE_ARTICLES =~ ^[Yy]$ ]]; then
            cd deployment/migrate
            if [ ! -f ".env.migration" ]; then
                cp .env.migration.example .env.migration
                echo -e "${YELLOW}⚠ 请配置 deployment/migrate/.env.migration${NC}"
                read -p "按Enter继续..."
            fi
            python migrate_to_pgsql.py
            cd ../..
        fi
        echo ""
    fi
    
    echo -e "${GREEN}=================================================="
    echo "✓ 数据迁移完成！"
    echo "==================================================${NC}"
    echo ""

fi

# 最后提示
echo -e "${BLUE}下一步操作：${NC}"
echo "1. 启动应用: streamlit run web.py"
echo "2. 运行测试: python scripts/test_auth_system.py"
echo "3. 查看文档: deployment/MIGRATION_GUIDE.md"
echo ""
echo -e "${YELLOW}⚠️  重要提醒：${NC}"
echo "- 请立即修改默认管理员密码"
echo "- 定期备份数据库"
echo "- 检查应用日志确认一切正常"
echo ""
