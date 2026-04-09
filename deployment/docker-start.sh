#!/bin/bash
# SupaWriter Docker 容器启动脚本

set -e

COMPOSE_FILE="docker-compose.yml"
PG_READY_MAX_ATTEMPTS=30

echo "🚀 启动 SupaWriter 容器化服务..."

# 检查 .env 文件
if [ ! -f "deployment/.env" ]; then
    echo "❌ 错误: deployment/.env 文件不存在"
    echo "请复制 deployment/.env.example 并配置环境变量"
    exit 1
fi

# 加载环境变量
source deployment/.env

# 检查必要的环境变量
required_vars=("POSTGRES_PASSWORD" "JWT_SECRET_KEY" "ENCRYPTION_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ 错误: 环境变量 $var 未设置"
        exit 1
    fi
done

# 创建必要的目录
mkdir -p deployment/postgres/data
mkdir -p deployment/redis/data
mkdir -p data
mkdir -p uploads

# 构建应用镜像
echo "🔨 构建应用镜像..."
cd deployment
docker-compose -f "$COMPOSE_FILE" build backend worker frontend trendradar

# 启动基础设施服务
echo "📦 启动基础设施服务..."
docker-compose -f "$COMPOSE_FILE" up -d postgres redis trendradar

# 等待 PostgreSQL 就绪
echo "⏳ 等待 PostgreSQL 就绪..."
pg_ready_attempt=0
while ! docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "${POSTGRES_USER:-supawriter}" > /dev/null 2>&1; do
    pg_ready_attempt=$((pg_ready_attempt + 1))
    if [ "$pg_ready_attempt" -ge "$PG_READY_MAX_ATTEMPTS" ]; then
        echo "❌ 错误: PostgreSQL 在 $(("$PG_READY_MAX_ATTEMPTS" * 2)) 秒内未就绪"
        exit 1
    fi
    sleep 2
done

# 检查基础设施状态
echo "🔍 检查基础设施状态..."
docker-compose -f "$COMPOSE_FILE" ps postgres redis trendradar

# 运行数据库迁移
echo "🗄️  运行数据库迁移..."
docker-compose -f "$COMPOSE_FILE" run --rm backend python /app/deployment/scripts/repair_schema_drift.py
docker-compose -f "$COMPOSE_FILE" run --rm backend python -m alembic -c /app/backend/api/db/migrations/alembic.ini upgrade head
docker-compose -f "$COMPOSE_FILE" run --rm backend python /app/deployment/scripts/init_production_state.py

# 启动应用服务
echo "🚀 启动应用服务..."
docker-compose -f "$COMPOSE_FILE" up -d backend worker frontend nginx

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo "✅ SupaWriter 服务启动完成！"
echo ""
echo "📋 服务访问地址:"
echo "  - Next.js 前端:    http://localhost:3001"
echo "  - FastAPI 后端:    http://localhost:8000"
echo "  - API 文档:        http://localhost:8000/docs"
echo "  - Streamlit 应用:  http://localhost:8501"
echo "  - Nginx 代理:      http://localhost"
echo ""
echo "📊 管理工具:"
echo "  - pgAdmin:         http://localhost:8080"
echo ""
echo "🛠️  常用命令:"
echo "  - 查看日志:   docker-compose -f deployment/docker-compose.yml logs -f [service]"
echo "  - 停止服务:   docker-compose -f deployment/docker-compose.yml down"
echo "  - 重启服务:   docker-compose -f deployment/docker-compose.yml restart [service]"
echo ""
