#!/bin/bash
# SupaWriter 新架构一键部署脚本（仅前后端分离）
# 使用方法: ./deploy-new.sh

set -e

echo "🚀 SupaWriter 新架构 Docker 部署"
echo "================================"
echo "📦 部署内容："
echo "  - PostgreSQL 数据库"
echo "  - Redis 缓存"
echo "  - FastAPI 后端"
echo "  - Next.js 前端"
echo "  - Nginx 反向代理"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查 Docker
echo "🔍 检查环境..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker 已安装${NC}"
echo -e "${GREEN}✓ Docker Compose 已安装${NC}"
echo ""

# 检查 .env 文件
if [ ! -f "deployment/.env" ]; then
    echo -e "${RED}❌ deployment/.env 文件不存在${NC}"
    exit 1
fi

# 加载环境变量
echo "📝 加载环境变量..."
set -a
source deployment/.env
set +a

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
    exit 1
fi

echo -e "${GREEN}✓ 环境变量检查通过${NC}"
echo ""

# 停止旧容器
echo "🛑 停止旧容器..."
cd deployment
docker-compose -f docker-compose.new.yml down 2>/dev/null || true
echo ""

# 创建必要的目录
echo "📁 创建必要的目录..."
cd ..
mkdir -p deployment/postgres/data
mkdir -p deployment/redis/data
mkdir -p data/chat_history
mkdir -p data/faiss
mkdir -p uploads
echo -e "${GREEN}✓ 目录创建完成${NC}"
echo ""

# 构建并启动服务
echo "🐳 构建并启动 Docker 容器..."
echo "这可能需要几分钟时间..."
echo ""

cd deployment
docker-compose -f docker-compose.new.yml up -d --build

# 等待服务启动
echo ""
echo "⏳ 等待服务启动（30秒）..."
sleep 30
echo ""

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose -f docker-compose.new.yml ps
echo ""

# 等待数据库就绪
echo "⏳ 等待数据库就绪..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose -f docker-compose.new.yml exec -T postgres pg_isready -U ${POSTGRES_USER:-supawriter} > /dev/null 2>&1; then
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

# 健康检查
echo "🏥 执行健康检查..."
services=("postgres" "redis" "backend" "frontend")
all_healthy=true

for service in "${services[@]}"; do
    if docker-compose -f docker-compose.new.yml ps | grep -q "$service.*Up"; then
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
    echo -e "${GREEN}✅ SupaWriter 新架构部署成功！${NC}"
else
    echo -e "${YELLOW}⚠️  部署完成，但部分服务可能未正常启动${NC}"
    echo "请使用以下命令查看日志："
    echo "  docker-compose -f deployment/docker-compose.new.yml logs -f"
fi
echo "================================"
echo ""

# 显示访问信息
echo "📋 服务访问地址："
echo "  ┌─────────────────────────────────────────────┐"
echo "  │ 🌐 Next.js 前端:   http://localhost:3000   │"
echo "  │ 🚀 FastAPI 后端:   http://localhost:8000   │"
echo "  │ 📚 API 文档:       http://localhost:8000/docs │"
echo "  │ 🔄 Nginx 代理:     http://localhost        │"
echo "  └─────────────────────────────────────────────┘"
echo ""

echo "🛠️  常用管理命令："
echo "  查看所有日志:     docker-compose -f deployment/docker-compose.new.yml logs -f"
echo "  查看后端日志:     docker-compose -f deployment/docker-compose.new.yml logs -f backend"
echo "  查看前端日志:     docker-compose -f deployment/docker-compose.new.yml logs -f frontend"
echo "  停止所有服务:     docker-compose -f deployment/docker-compose.new.yml down"
echo "  重启服务:        docker-compose -f deployment/docker-compose.new.yml restart"
echo "  查看服务状态:     docker-compose -f deployment/docker-compose.new.yml ps"
echo ""

echo -e "${GREEN}🎉 部署完成！祝使用愉快！${NC}"
