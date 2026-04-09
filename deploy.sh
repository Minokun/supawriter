#!/bin/bash
# SupaWriter 一键部署脚本
# 使用方法: ./deploy.sh

set -e

echo "🚀 SupaWriter 一键 Docker 部署"
echo "================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker 和 Docker Compose
echo "🔍 检查环境..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装，请先安装 Docker${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装，请先安装 Docker Compose${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker 已安装${NC}"
echo -e "${GREEN}✓ Docker Compose 已安装${NC}"
echo ""

# 检查 .env 文件
if [ ! -f "deployment/.env" ]; then
    echo -e "${YELLOW}⚠️  未找到 deployment/.env 文件${NC}"
    echo "正在从模板创建..."
    
    if [ -f "deployment/.env.example" ]; then
        cp deployment/.env.example deployment/.env
        echo -e "${GREEN}✓ 已创建 deployment/.env${NC}"
        echo ""
        echo -e "${YELLOW}请编辑 deployment/.env 文件，配置以下必需项：${NC}"
        echo "  1. POSTGRES_PASSWORD - 数据库密码"
        echo "  2. JWT_SECRET_KEY - JWT 密钥"
        echo "  3. ENCRYPTION_KEY - 加密密钥"
        echo ""
        echo "生成密钥命令："
        echo "  JWT_SECRET_KEY:    openssl rand -base64 32"
        echo "  ENCRYPTION_KEY:    python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        echo ""
        read -p "配置完成后按回车继续..." 
    else
        echo -e "${RED}❌ 未找到 deployment/.env.example 模板文件${NC}"
        exit 1
    fi
fi

# 加载环境变量
echo "📝 加载环境变量..."
source deployment/.env

# 检查必要的环境变量
required_vars=("POSTGRES_PASSWORD" "JWT_SECRET_KEY" "ENCRYPTION_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo -e "${RED}❌ 以下环境变量未设置：${NC}"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "请编辑 deployment/.env 文件并设置这些变量"
    exit 1
fi

echo -e "${GREEN}✓ 环境变量检查通过${NC}"
echo ""

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p deployment/postgres/data
mkdir -p deployment/redis/data
mkdir -p data/chat_history
mkdir -p data/faiss
mkdir -p data/daily_news
mkdir -p uploads
echo -e "${GREEN}✓ 目录创建完成${NC}"
echo ""

# 构建并启动服务
echo "🐳 构建并启动 Docker 容器..."
echo "这可能需要几分钟时间，请耐心等待..."
echo ""

cd deployment
docker-compose -f docker-compose.full.yml up -d --build

# 等待服务启动
echo ""
echo "⏳ 等待服务启动（30秒）..."
for i in {1..30}; do
    echo -n "."
    sleep 1
done
echo ""
echo ""

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose -f docker-compose.full.yml ps
echo ""

# 等待数据库就绪
echo "⏳ 等待数据库就绪..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose -f docker-compose.full.yml exec -T postgres pg_isready -U ${POSTGRES_USER:-supawriter} > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 数据库已就绪${NC}"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ 数据库启动超时${NC}"
    exit 1
fi
echo ""

# 运行数据库迁移
echo "🗄️  运行数据库迁移..."
migration_files=$(ls -1 postgres/migrations/*.sql 2>/dev/null | sort)

if [ -n "$migration_files" ]; then
    for sql_file in $migration_files; do
        filename=$(basename "$sql_file")
        echo "  执行: $filename"
        docker-compose -f docker-compose.full.yml exec -T postgres psql -U ${POSTGRES_USER:-supawriter} -d ${POSTGRES_DB:-supawriter} -f "/docker-entrypoint-initdb.d/migrations/$filename" > /dev/null 2>&1 || true
    done
    echo -e "${GREEN}✓ 数据库迁移完成${NC}"
else
    echo -e "${YELLOW}⚠️  未找到迁移文件${NC}"
fi
echo ""

# 健康检查
echo "🏥 执行健康检查..."
services=("postgres" "redis" "backend")
all_healthy=true

for service in "${services[@]}"; do
    if docker-compose -f docker-compose.full.yml ps | grep -q "$service.*Up"; then
        echo -e "${GREEN}✓ $service 运行正常${NC}"
    else
        echo -e "${RED}✗ $service 未运行${NC}"
        all_healthy=false
    fi
done
echo ""

# 显示部署结果
cd ..
echo "================================"
if [ "$all_healthy" = true ]; then
    echo -e "${GREEN}✅ SupaWriter 部署成功！${NC}"
else
    echo -e "${YELLOW}⚠️  部署完成，但部分服务可能未正常启动${NC}"
    echo "请使用以下命令查看日志："
    echo "  docker-compose -f deployment/docker-compose.full.yml logs -f"
fi
echo "================================"
echo ""

# 显示访问信息
echo "📋 服务访问地址："
echo "  ┌─────────────────────────────────────────────┐"
echo "  │ 🌐 Next.js 前端:   http://localhost:3000   │"
echo "  │ 🚀 FastAPI 后端:   http://localhost:8000   │"
echo "  │ 📚 API 文档:       http://localhost:8000/docs │"
echo "  │ 🎨 Streamlit:      http://localhost:8501   │"
echo "  │ 🔄 Nginx 代理:     http://localhost        │"
echo "  └─────────────────────────────────────────────┘"
echo ""

echo "🛠️  常用管理命令："
echo "  查看所有日志:     docker-compose -f deployment/docker-compose.full.yml logs -f"
echo "  查看特定服务日志:  docker-compose -f deployment/docker-compose.full.yml logs -f backend"
echo "  停止所有服务:     docker-compose -f deployment/docker-compose.full.yml down"
echo "  重启服务:        docker-compose -f deployment/docker-compose.full.yml restart"
echo "  查看服务状态:     docker-compose -f deployment/docker-compose.full.yml ps"
echo ""

echo "📖 更多信息请查看："
echo "  - deployment/DOCKER_DEPLOYMENT.md"
echo "  - FINAL_DELIVERY.md"
echo ""

echo -e "${GREEN}🎉 部署完成！祝使用愉快！${NC}"
