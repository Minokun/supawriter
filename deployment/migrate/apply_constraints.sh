#!/bin/bash

# 应用唯一约束到现有数据库
# 使用方法: ./apply_constraints.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "应用数据库唯一约束"
echo "========================================"

# 从.env文件加载配置
if [ -f "../../.env" ]; then
    source ../../.env
    echo "✓ 加载配置文件"
else
    echo -e "${RED}错误: 找不到 .env 文件${NC}"
    exit 1
fi

# 数据库连接信息
DB_HOST=${POSTGRES_HOST:-122.51.24.120}
DB_PORT=${POSTGRES_PORT:-5432}
DB_USER=${POSTGRES_USER:-supawriter}
DB_NAME=${POSTGRES_DB:-supawriter}
DB_PASSWORD=${POSTGRES_PASSWORD}

if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}错误: 未设置数据库密码${NC}"
    exit 1
fi

echo ""
echo "数据库配置:"
echo "  主机: $DB_HOST"
echo "  端口: $DB_PORT"
echo "  用户: $DB_USER"
echo "  数据库: $DB_NAME"
echo ""

# 检查是否有重复数据
echo "========================================"
echo "步骤1: 检查重复数据"
echo "========================================"

export PGPASSWORD=$DB_PASSWORD

echo "检查重复的文章..."
DUPLICATE_ARTICLES=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM (
    SELECT username, topic, created_at, COUNT(*) as count
    FROM articles
    GROUP BY username, topic, created_at
    HAVING COUNT(*) > 1
) duplicates;
" | xargs)

echo "检查重复的聊天会话..."
DUPLICATE_SESSIONS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM (
    SELECT username, created_at, COUNT(*) as count
    FROM chat_sessions
    GROUP BY username, created_at
    HAVING COUNT(*) > 1
) duplicates;
" | xargs)

echo ""
echo "重复数据统计:"
echo "  重复的文章组: $DUPLICATE_ARTICLES"
echo "  重复的会话组: $DUPLICATE_SESSIONS"
echo ""

if [ "$DUPLICATE_ARTICLES" -gt 0 ] || [ "$DUPLICATE_SESSIONS" -gt 0 ]; then
    echo -e "${YELLOW}警告: 检测到重复数据！${NC}"
    echo "在添加唯一约束之前，需要先清理重复数据。"
    echo ""
    read -p "是否查看重复数据详情? [y/N]: " show_details
    
    if [[ $show_details =~ ^[Yy]$ ]]; then
        if [ "$DUPLICATE_ARTICLES" -gt 0 ]; then
            echo ""
            echo "重复的文章:"
            psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
            SELECT username, topic, created_at, COUNT(*) as count
            FROM articles
            GROUP BY username, topic, created_at
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10;
            "
        fi
        
        if [ "$DUPLICATE_SESSIONS" -gt 0 ]; then
            echo ""
            echo "重复的聊天会话:"
            psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
            SELECT username, created_at, COUNT(*) as count
            FROM chat_sessions
            GROUP BY username, created_at
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10;
            "
        fi
    fi
    
    echo ""
    echo -e "${RED}无法添加唯一约束，因为存在重复数据。${NC}"
    echo "请先清理重复数据，然后重新运行此脚本。"
    exit 1
fi

echo -e "${GREEN}✓ 没有检测到重复数据${NC}"

# 应用唯一约束
echo ""
echo "========================================"
echo "步骤2: 应用唯一约束"
echo "========================================"

read -p "确认要添加唯一约束吗? [y/N]: " confirm

if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "操作已取消"
    exit 0
fi

echo ""
echo "添加articles表唯一约束..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
ALTER TABLE articles 
    DROP CONSTRAINT IF EXISTS articles_unique_constraint;
ALTER TABLE articles 
    ADD CONSTRAINT articles_unique_constraint 
    UNIQUE (username, topic, created_at);
"

echo "添加chat_sessions表唯一约束..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
ALTER TABLE chat_sessions 
    DROP CONSTRAINT IF EXISTS chat_sessions_unique_constraint;
ALTER TABLE chat_sessions 
    ADD CONSTRAINT chat_sessions_unique_constraint 
    UNIQUE (username, created_at);
"

echo ""
echo -e "${GREEN}✓ 唯一约束应用成功！${NC}"

# 验证约束
echo ""
echo "========================================"
echo "步骤3: 验证约束"
echo "========================================"

echo "验证articles表约束..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'articles'::regclass
AND conname = 'articles_unique_constraint';
"

echo "验证chat_sessions表约束..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'chat_sessions'::regclass
AND conname = 'chat_sessions_unique_constraint';
"

echo ""
echo "========================================"
echo -e "${GREEN}操作完成！${NC}"
echo "========================================"
echo "现在重复迁移数据将被自动忽略。"
