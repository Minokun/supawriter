#!/bin/bash
# 本地启动脚本（基础服务用 Docker，前后端本地运行）

set -e

echo "🚀 SupaWriter 混合部署启动"
echo "================================"
echo "📦 Docker 服务："
echo "  - PostgreSQL"
echo "  - Redis"
echo "  - Nginx"
echo ""
echo "💻 本地服务："
echo "  - FastAPI 后端 (端口 8000)"
echo "  - Next.js 前端 (端口 3000)"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. 启动 Docker 基础服务
echo "🐳 启动 Docker 基础服务..."
cd deployment
docker-compose -f docker-compose.simple.yml up -d
cd ..

# 等待数据库就绪
echo "⏳ 等待数据库就绪..."
sleep 5

# 2. 启动后端服务
echo ""
echo "🚀 启动 FastAPI 后端..."
echo "在新终端运行以下命令："
echo ""
echo -e "${YELLOW}cd /Users/wxk/Desktop/workspace/supawriter${NC}"
echo -e "${YELLOW}source .venv/bin/activate  # 或 uv venv${NC}"
echo -e "${YELLOW}uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload${NC}"
echo ""

# 3. 启动前端服务
echo "🌐 启动 Next.js 前端..."
echo "在另一个新终端运行以下命令："
echo ""
echo -e "${YELLOW}cd /Users/wxk/Desktop/workspace/supawriter/frontend${NC}"
echo -e "${YELLOW}npm install  # 首次运行${NC}"
echo -e "${YELLOW}npm run dev${NC}"
echo ""

echo "================================"
echo -e "${GREEN}✅ Docker 基础服务已启动！${NC}"
echo ""
echo "📋 服务访问地址："
echo "  - PostgreSQL:  localhost:5432"
echo "  - Redis:       localhost:6379"
echo "  - 后端 API:    http://localhost:8000"
echo "  - API 文档:    http://localhost:8000/docs"
echo "  - 前端界面:    http://localhost:3000"
echo ""
echo "🛠️  管理命令："
echo "  查看 Docker 日志:  docker-compose -f deployment/docker-compose.simple.yml logs -f"
echo "  停止 Docker 服务:  docker-compose -f deployment/docker-compose.simple.yml down"
echo ""
