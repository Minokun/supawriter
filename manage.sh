#!/bin/bash

# SupaWriter 服务管理脚本 v3.0
# 全容器化版本 — 所有服务通过 Docker Compose 管理
# 支持：启动、停止、重启、状态查询、日志查看、数据库迁移、健康检查、测试

set -e

# ═══════════════════════════════════════════════════════
# 颜色和基础配置
# ═══════════════════════════════════════════════════════
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$PROJECT_ROOT/deployment"

# DockerHub 镜像仓库配置
DOCKERHUB_USERNAME="${DOCKERHUB_USERNAME:-minokun}"
DOCKERHUB_TAG="${DOCKERHUB_TAG:-latest}"

# 确定使用哪个 compose 文件（默认 dev）
COMPOSE_ENV=${COMPOSE_ENV:-dev}

case "$COMPOSE_ENV" in
    prod|production)
        COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"
        BACKEND_PORT=8000
        FRONTEND_PORT=3001
        TRENDRADAR_PORT=${TRENDRADAR_PORT:-8765}
        ;;
    dev|development|*)
        COMPOSE_FILE="$DEPLOY_DIR/docker-compose.dev.yml"
        BACKEND_PORT=8001
        FRONTEND_PORT=3001
        TRENDRADAR_PORT=${TRENDRADAR_PORT:-8766}
        ;;
esac

# ═══════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════
info()    { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn()    { echo -e "${YELLOW}⚠${NC} $1"; }
error()   { echo -e "${RED}✗${NC} $1"; }

header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_access_urls() {
    echo ""
    header "访问地址"
    echo ""
    echo -e "  ${GREEN}前端界面:${NC}    http://localhost:$FRONTEND_PORT"
    echo -e "  ${GREEN}后端 API:${NC}    http://localhost:$BACKEND_PORT"
    echo -e "  ${GREEN}API 文档:${NC}    http://localhost:$BACKEND_PORT/docs"
    echo -e "  ${GREEN}TrendRadar:${NC}  http://localhost:$TRENDRADAR_PORT"
    echo -e "  ${GREEN}Worker:${NC}       运行中 (热点同步/预警/统计)"
    echo ""
    echo -e "  ${BLUE}./manage.sh status${NC}         查看状态"
    echo -e "  ${BLUE}./manage.sh health${NC}         健康检查"
    echo -e "  ${BLUE}./manage.sh logs frontend${NC}  查看前端日志"
    echo -e "  ${BLUE}./manage.sh logs backend${NC}   查看后端日志"
    echo -e "  ${BLUE}./manage.sh stop${NC}           停止服务"
    echo ""
}

repair_schema_drift() {
    info "修复数据库 schema drift..."
    if dc exec -T backend python /app/deployment/scripts/repair_schema_drift.py; then
        success "数据库 schema drift 修复完成"
    else
        warn "schema drift 修复失败，可稍后手动执行"
    fi
}

get_env_value() {
    local file="$1"
    local key="$2"
    [ -f "$file" ] || return 1
    grep -E "^${key}=" "$file" | tail -1 | cut -d'=' -f2-
}

upsert_env_value() {
    local file="$1"
    local key="$2"
    local value="$3"

    [ -n "$value" ] || return 0

    if grep -q -E "^${key}=" "$file" 2>/dev/null; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
        else
            sed -i "s|^${key}=.*|${key}=${value}|" "$file"
        fi
    else
        echo "${key}=${value}" >> "$file"
    fi
}

sync_shared_env_keys() {
    local root_env="$PROJECT_ROOT/.env"
    local deploy_env="$DEPLOY_DIR/.env"

    [ -f "$root_env" ] || return 0
    [ -f "$deploy_env" ] || return 0

    local jwt_secret
    jwt_secret=$(get_env_value "$root_env" "JWT_SECRET_KEY")
    local encryption_key
    encryption_key=$(get_env_value "$root_env" "ENCRYPTION_KEY")

    if [ -n "$jwt_secret" ] && [ -z "$(get_env_value "$deploy_env" "JWT_SECRET_KEY")" ]; then
        upsert_env_value "$deploy_env" "JWT_SECRET_KEY" "$jwt_secret"
        info "已同步 JWT_SECRET_KEY 到 deployment/.env"
    fi

    if [ -n "$encryption_key" ] && [ -z "$(get_env_value "$deploy_env" "ENCRYPTION_KEY")" ]; then
        upsert_env_value "$deploy_env" "ENCRYPTION_KEY" "$encryption_key"
        info "已同步 ENCRYPTION_KEY 到 deployment/.env"
    fi
}

# Docker Compose 命令封装
dc() {
    local requires_build_retry=0
    local arg
    for arg in "$@"; do
        if [ "$arg" = "build" ] || [ "$arg" = "--build" ]; then
            requires_build_retry=1
            break
        fi
    done

    if [ "$requires_build_retry" -eq 0 ]; then
        docker compose -f "$COMPOSE_FILE" --env-file "$DEPLOY_DIR/.env" "$@"
        return $?
    fi

    local log_file
    log_file=$(mktemp -t supawriter-dc.XXXXXX)

    set +e
    docker compose -f "$COMPOSE_FILE" --env-file "$DEPLOY_DIR/.env" "$@" 2>&1 | tee "$log_file"
    local compose_status=${PIPESTATUS[0]}
    set -e

    if [ "$compose_status" -eq 0 ]; then
        docker_cleanup_after_build
        rm -f "$log_file"
        return 0
    fi

    if grep -Eq 'failed to prepare extraction snapshot|parent snapshot .* does not exist' "$log_file"; then
        warn "检测到 Docker BuildKit snapshot 损坏，自动清理构建缓存后重试一次..."
        docker buildx prune -af >/dev/null 2>&1 || true
        docker builder prune -af >/dev/null 2>&1 || true

        set +e
        docker compose -f "$COMPOSE_FILE" --env-file "$DEPLOY_DIR/.env" "$@" 2>&1 | tee "$log_file"
        compose_status=${PIPESTATUS[0]}
        set -e
    fi

    if [ "$compose_status" -eq 0 ]; then
        docker_cleanup_after_build
    fi

    rm -f "$log_file"
    return "$compose_status"
}

cleanup_orphans() {
    dc down --remove-orphans >/dev/null 2>&1 || true

    local legacy_names=(
        "supawriter_migrate_dev"
    )

    for name in "${legacy_names[@]}"; do
        docker rm -f "$name" >/dev/null 2>&1 || true
    done
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        error "未安装 Docker，请先安装"
        exit 1
    fi
    if ! docker info &> /dev/null; then
        error "Docker 未运行，请先启动 Docker Desktop"
        exit 1
    fi
    success "Docker: $(docker --version 2>&1 | head -1)"
}

docker_cleanup_after_build() {
    info "清理 Docker 构建缓存和悬空资源..."

    # Conservative cleanup: keep active volumes and running-container logs intact.
    docker image prune -f >/dev/null 2>&1 || true
    docker container prune -f >/dev/null 2>&1 || true
    docker builder prune -af >/dev/null 2>&1 || true
    docker buildx prune -af >/dev/null 2>&1 || true

    success "Docker 构建缓存清理完成"
}

check_trendradar() {
    local trendradar_dir="${TRENDRADAR_DIR:-$PROJECT_ROOT/../trendradar}"
    if [ ! -d "$trendradar_dir" ]; then
        error "TrendRadar 目录不存在: $trendradar_dir"
        info "请先克隆 TrendRadar 项目:"
        info "  git clone https://github.com/sansan0/TrendRadar.git $trendradar_dir"
        exit 1
    fi

    if [ ! -f "$trendradar_dir/requirements.txt" ] || [ ! -f "$trendradar_dir/api_server.py" ]; then
        error "TrendRadar 目录不完整: $trendradar_dir"
        info "缺少 requirements.txt 或 api_server.py，无法构建 TrendRadar"
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════
# 依赖检查
# ═══════════════════════════════════════════════════════
check_dependencies() {
    header "检查系统依赖"
    check_docker

    if command -v docker compose &> /dev/null; then
        success "Docker Compose: 插件模式"
    elif command -v docker-compose &> /dev/null; then
        success "Docker Compose: $(docker-compose --version 2>&1)"
    else
        error "未安装 Docker Compose"
        exit 1
    fi

    info "环境: $COMPOSE_ENV"
    info "Compose 文件: $COMPOSE_FILE"
}

# ═══════════════════════════════════════════════════════
# 构建镜像
# ═══════════════════════════════════════════════════════
build_images() {
    header "构建 Docker 镜像"
    check_docker

    # 检查 TrendRadar 目录
    local trendradar_dir="${TRENDRADAR_DIR:-$PROJECT_ROOT/../trendradar}"
    if [ ! -d "$trendradar_dir" ]; then
        warn "TrendRadar 目录不存在，跳过构建 ($trendradar_dir)"
        info "如需使用 TrendRadar，请先克隆:"
        info "  git clone https://github.com/sansan0/TrendRadar.git $trendradar_dir"
    fi

    info "构建所有镜像..."
    dc build
    success "镜像构建完成"
}

# ═══════════════════════════════════════════════════════
# 推送镜像到 DockerHub
# ═══════════════════════════════════════════════════════
push_images() {
    header "构建并推送镜像到 DockerHub ($DOCKERHUB_USERNAME)"
    check_docker

    # 检查 docker login 状态
    if ! docker info 2>/dev/null | grep -q "Registry: https://index.docker.io" 2>/dev/null; then
        if [ -z "$(docker credential list 2>/dev/null | grep 'docker.io' || echo '')" ]; then
            warn "请先登录 DockerHub: docker login -u $DOCKERHUB_USERNAME"
            exit 1
        fi
    fi

    # 构建所有镜像
    info "构建镜像..."
    dc build

    # 推送镜像
    local services="backend worker frontend trendradar"
    for svc in $services; do
        local image_name="$DOCKERHUB_USERNAME/supawriter-${svc}:${DOCKERHUB_TAG}"
        info "推送 ${image_name}..."
        docker push "$image_name" && success "已推送 ${image_name}" || warn "推送失败: ${image_name}"
    done

    success "所有镜像已推送到 DockerHub"
}

# ═══════════════════════════════════════════════════════
# 从 DockerHub 拉取镜像
# ═══════════════════════════════════════════════════════
pull_images() {
    header "从 DockerHub 拉取镜像 ($DOCKERHUB_USERNAME)"
    check_docker

    local services="backend worker frontend trendradar"
    for svc in $services; do
        local image_name="$DOCKERHUB_USERNAME/supawriter-${svc}:${DOCKERHUB_TAG}"
        info "拉取 ${image_name}..."
        docker pull "$image_name" && success "已拉取 ${image_name}" || warn "拉取失败: ${image_name}"
    done

    success "所有镜像拉取完成"
}

# ═══════════════════════════════════════════════════════
# 环境配置（保留本地 .env 初始化）
# ═══════════════════════════════════════════════════════
setup_env() {
    header "配置环境变量"

    # 根目录 .env（JWT 等全局配置）
    if [ ! -f ".env" ]; then
        warn ".env 不存在，创建默认配置..."
        local jwt_key=$(openssl rand -base64 32 2>/dev/null || echo "change-me-in-production")
        local encryption_key=$(openssl rand -base64 32 2>/dev/null | tr '+/' '-_' | tr -d '=')
        cat > .env << EOF
JWT_SECRET_KEY=${jwt_key}
ENCRYPTION_KEY=${encryption_key}
DATABASE_URL=postgresql://supawriter:supawriter@localhost:5432/supawriter
SUPER_ADMIN_EMAILS=wxk952718180@gmail.com
EOF
        success "已创建 .env"
    else
        # 检查是否已有 SUPER_ADMIN_EMAILS，没有则添加默认值
        if ! grep -q "SUPER_ADMIN_EMAILS" .env; then
            echo "SUPER_ADMIN_EMAILS=wxk952718180@gmail.com" >> .env
            info "已添加 SUPER_ADMIN_EMAILS 到 .env"
        fi
        if ! grep -q "ENCRYPTION_KEY" .env; then
            local encryption_key=$(openssl rand -base64 32 2>/dev/null | tr '+/' '-_' | tr -d '=')
            echo "ENCRYPTION_KEY=${encryption_key}" >> .env
            info "已添加 ENCRYPTION_KEY 到 .env"
        fi
        success ".env 已存在"
    fi

    # 部署 .env
    if [ ! -f "$DEPLOY_DIR/.env" ]; then
        if [ -f "$DEPLOY_DIR/.env.example" ]; then
            warn "deployment/.env 不存在，从模板创建..."
            cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"
            success "已创建 deployment/.env（请修改密码）"
        fi
    else
        success "deployment/.env 已存在"
    fi

    sync_shared_env_keys

    # 前端 .env.local
    if [ -d "frontend" ]; then
        if [ ! -f "frontend/.env.local" ]; then
            if [ -f "frontend/.env.local.example" ]; then
                warn "frontend/.env.local 不存在，从模板创建..."
                cp frontend/.env.local.example frontend/.env.local
                local secret=$(openssl rand -base64 32 2>/dev/null || echo "change-me")
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s/your-random-secret-key-here/$secret/" frontend/.env.local 2>/dev/null || true
                else
                    sed -i "s/your-random-secret-key-here/$secret/" frontend/.env.local 2>/dev/null || true
                fi
                success "已创建 frontend/.env.local"
            fi
        else
            success "frontend/.env.local 已存在"
        fi
    fi
}

# ═══════════════════════════════════════════════════════
# 启动服务
# ═══════════════════════════════════════════════════════
start_service() {
    local build_flag=""

    # 解析参数：提取 --build 标志
    local args=()
    for arg in "$@"; do
        if [ "$arg" = "--build" ]; then
            build_flag="--build"
        else
            args+=("$arg")
        fi
    done
    local service="${args[0]:-all}"

    if [ -n "$build_flag" ]; then
        info "将重新构建镜像 (--build)"
    fi

    case "$service" in
        backend|api)
            header "启动后端服务"
            dc up -d $build_flag --remove-orphans backend
            repair_schema_drift
            print_access_urls
            ;;
        frontend|web)
            header "启动前端服务"
            dc up -d $build_flag --remove-orphans frontend
            print_access_urls
            ;;
        worker)
            header "启动 ARQ Worker 服务"
            dc up -d $build_flag --remove-orphans worker
            repair_schema_drift
            print_access_urls
            ;;
        trendradar|hotspots)
            header "启动 TrendRadar API 服务"
            check_trendradar
            dc up -d $build_flag --remove-orphans trendradar
            print_access_urls
            ;;
        all|"")
            header "启动 SupaWriter 全部服务 ($COMPOSE_ENV)"
            check_dependencies
            setup_env
            cleanup_orphans

            # 检查 TrendRadar 目录
            local trendradar_dir="${TRENDRADAR_DIR:-$PROJECT_ROOT/../trendradar}"
            if [ ! -d "$trendradar_dir" ] || [ ! -f "$trendradar_dir/requirements.txt" ] || [ ! -f "$trendradar_dir/api_server.py" ]; then
                warn "TrendRadar 未就绪，跳过启动 ($trendradar_dir)"
                info "启动其他服务..."
                dc up -d $build_flag --remove-orphans postgres redis backend frontend worker
            else
                dc up -d $build_flag --remove-orphans
            fi

            repair_schema_drift
            print_access_urls
            ;;
        *)
            error "未知服务: $service"
            echo "用法: $0 start [--build] [backend|frontend|worker|trendradar|all]"
            exit 1
            ;;
    esac
}

# ═══════════════════════════════════════════════════════
# 停止服务
# ═══════════════════════════════════════════════════════
stop_service() {
    local service="$1"

    case "$service" in
        backend|api)
            dc stop backend && dc rm -f backend
            success "后端服务已停止"
            ;;
        frontend|web)
            dc stop frontend && dc rm -f frontend
            success "前端服务已停止"
            ;;
        worker)
            dc stop worker && dc rm -f worker
            success "Worker 服务已停止"
            ;;
        trendradar|hotspots)
            dc stop trendradar && dc rm -f trendradar
            success "TrendRadar 服务已停止"
            ;;
        all|"")
            dc down --remove-orphans
            success "所有服务已停止"
            ;;
        *)
            error "未知服务: $service"
            exit 1
            ;;
    esac
}

# ═══════════════════════════════════════════════════════
# 重启服务
# ═══════════════════════════════════════════════════════
restart_service() {
    local service="$1"

    case "$service" in
        backend|api)
            header "重启后端服务"
            dc restart backend
            ;;
        frontend|web)
            header "重启前端服务"
            dc restart frontend
            ;;
        worker)
            header "重启 Worker 服务"
            dc restart worker
            ;;
        trendradar|hotspots)
            header "重启 TrendRadar 服务"
            dc restart trendradar
            ;;
        all|"")
            header "重启所有服务"
            dc restart
            ;;
        *)
            error "未知服务: $service"
            exit 1
            ;;
    esac
}

# ═══════════════════════════════════════════════════════
# 服务状态
# ═══════════════════════════════════════════════════════
show_status() {
    header "SupaWriter 服务状态 ($COMPOSE_ENV)"
    echo ""
    dc ps
    echo ""
}

# ═══════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════
health_check() {
    header "健康检查"

    info "后端健康检查..."
    local resp=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$BACKEND_PORT/health 2>/dev/null)
    if [ "$resp" = "200" ]; then
        success "后端健康检查通过 (端口 $BACKEND_PORT)"
        curl -s http://localhost:$BACKEND_PORT/health | python3 -m json.tool 2>/dev/null || true
    else
        error "后端健康检查失败 (HTTP $resp)"
        error "请确认服务已启动: ./manage.sh start"
    fi

    echo ""
    info "TrendRadar 健康检查..."
    resp=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$TRENDRADAR_PORT/health 2>/dev/null)
    if [ "$resp" = "200" ]; then
        success "TrendRadar 健康检查通过 (端口 $TRENDRADAR_PORT)"
    else
        warn "TrendRadar 健康检查失败 (HTTP $resp) — 热点功能将降级为 newsnow API"
    fi
}

# ═══════════════════════════════════════════════════════
# 查看日志
# ═══════════════════════════════════════════════════════
view_logs() {
    local service="${1:-all}"
    local lines="${2:-}"

    local args=("-f")
    [ -n "$lines" ] && args+=("--tail=$lines")

    case $service in
        backend|api)
            dc logs "${args[@]}" backend
            ;;
        frontend|web)
            dc logs "${args[@]}" frontend
            ;;
        worker)
            dc logs "${args[@]}" worker
            ;;
        trendradar|hotspots)
            dc logs "${args[@]}" trendradar
            ;;
        postgres)
            dc logs "${args[@]}" postgres
            ;;
        redis)
            dc logs "${args[@]}" redis
            ;;
        all)
            dc logs "${args[@]}"
            ;;
        *)
            error "未知服务: $service"
            echo "用法: $0 logs [backend|frontend|worker|trendradar|postgres|redis|all] [行数]"
            ;;
    esac
}

# ═══════════════════════════════════════════════════════
# 数据库迁移（在容器内执行）
# ═══════════════════════════════════════════════════════
db_migrate() {
    local action="${1:-upgrade}"

    case "$action" in
        upgrade)
            header "数据库迁移 (upgrade head)"
            dc exec -T backend python -m alembic -c backend/api/db/migrations/alembic.ini upgrade head
            success "数据库迁移完成"
            ;;
        downgrade)
            header "数据库回滚 (downgrade -1)"
            dc exec -T backend python -m alembic -c backend/api/db/migrations/alembic.ini downgrade -1
            success "数据库回滚完成"
            ;;
        history)
            header "迁移历史"
            dc exec -T backend python -m alembic -c backend/api/db/migrations/alembic.ini history
            ;;
        current)
            header "当前迁移版本"
            dc exec -T backend python -m alembic -c backend/api/db/migrations/alembic.ini current
            ;;
        *)
            error "未知迁移操作: $action"
            echo "用法: $0 db [upgrade|downgrade|history|current]"
            ;;
    esac
}

# ═══════════════════════════════════════════════════════
# 运行测试（在容器内执行）
# ═══════════════════════════════════════════════════════
run_tests() {
    header "运行测试"
    local target="${1:-all}"

    case "$target" in
        all)
            info "运行所有测试..."
            dc exec -T backend python -m pytest backend/tests/ -v --tb=short
            ;;
        core)
            dc exec -T backend python -m pytest backend/tests/test_core/ -v --tb=short
            ;;
        models)
            dc exec -T backend python -m pytest backend/tests/test_models/ -v --tb=short
            ;;
        repos|repositories)
            dc exec -T backend python -m pytest backend/tests/test_repositories/ -v --tb=short
            ;;
        services)
            dc exec -T backend python -m pytest backend/tests/test_services/ -v --tb=short
            ;;
        middleware|mw)
            dc exec -T backend python -m pytest backend/tests/test_middleware/ -v --tb=short
            ;;
        *)
            info "运行指定测试: $target"
            dc exec -T backend python -m pytest "$target" -v --tb=short
            ;;
    esac
}

# ═══════════════════════════════════════════════════════
# 管理员管理（本地操作 + 容器内 DB 更新）
# ═══════════════════════════════════════════════════════
admin_add() {
    local email="$1"
    if [ -z "$email" ]; then
        error "请提供邮箱地址"
        echo "用法: $0 admin add <email>"
        exit 1
    fi

    if grep "SUPER_ADMIN_EMAILS" .env 2>/dev/null | grep -q "$email"; then
        warn "$email 已是超级管理员"
        return 0
    fi

    # 追加到 SUPER_ADMIN_EMAILS
    if grep -q "SUPER_ADMIN_EMAILS" .env; then
        local current=$(grep "SUPER_ADMIN_EMAILS" .env | cut -d'=' -f2)
        local new_value="${current},${email}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|SUPER_ADMIN_EMAILS=.*|SUPER_ADMIN_EMAILS=${new_value}|" .env
        else
            sed -i "s|SUPER_ADMIN_EMAILS=.*|SUPER_ADMIN_EMAILS=${new_value}|" .env
        fi
    else
        echo "SUPER_ADMIN_EMAILS=${email}" >> .env
    fi

    # 更新数据库中的 is_superuser（在容器内执行）
    dc exec -T backend python -c "
from backend.api.db.session import get_sync_engine
from sqlalchemy import text
engine = get_sync_engine()
with engine.connect() as conn:
    conn.execute(text('UPDATE users SET is_superuser = true WHERE email = :email'), {'email': '$email'})
    conn.commit()
    print('Database updated')
" 2>/dev/null || warn "数据库更新失败，请手动设置 is_superuser"

    success "已添加 $email 为超级管理员"
    info "请重启后端服务使配置生效: $0 restart backend"
}

admin_remove() {
    local email="$1"
    if [ -z "$email" ]; then
        error "请提供邮箱地址"
        echo "用法: $0 admin remove <email>"
        exit 1
    fi

    if ! grep "SUPER_ADMIN_EMAILS" .env | grep -q "$email"; then
        warn "$email 不是超级管理员"
        return 0
    fi

    local current=$(grep "SUPER_ADMIN_EMAILS" .env | cut -d'=' -f2)
    local new_value=$(echo "$current" | tr ',' '\n' | grep -v "^$email$" | tr '\n' ',' | sed 's/,$//')

    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|SUPER_ADMIN_EMAILS=.*|SUPER_ADMIN_EMAILS=${new_value}|" .env
    else
        sed -i "s|SUPER_ADMIN_EMAILS=.*|SUPER_ADMIN_EMAILS=${new_value}|" .env
    fi

    dc exec -T backend python -c "
from backend.api.db.session import get_sync_engine
from sqlalchemy import text
engine = get_sync_engine()
with engine.connect() as conn:
    conn.execute(text('UPDATE users SET is_superuser = false WHERE email = :email'), {'email': '$email'})
    conn.commit()
    print('Database updated')
" 2>/dev/null || warn "数据库更新失败"

    success "已移除 $email 的超级管理员权限"
}

admin_list() {
    header "超级管理员列表"
    if grep -q "SUPER_ADMIN_EMAILS" .env; then
        local emails=$(grep "SUPER_ADMIN_EMAILS" .env | cut -d'=' -f2)
        echo "$emails" | tr ',' '\n' | while read email; do
            [ -n "$email" ] && echo "  * $email"
        done
    else
        warn "未配置 SUPER_ADMIN_EMAILS"
    fi
}

# ═══════════════════════════════════════════════════════
# 清理
# ═══════════════════════════════════════════════════════
clean_all() {
    header "清理 Docker 资源"
    dc down -v --rmi local --remove-orphans
    success "清理完成（容器、卷、本地镜像已删除）"
}

# ═══════════════════════════════════════════════════════
# 进入容器 shell
# ═══════════════════════════════════════════════════════
shell_into() {
    local service="$1"
    case "$service" in
        backend|api)
            dc exec backend bash
            ;;
        frontend|web)
            dc exec frontend sh
            ;;
        worker)
            dc exec worker bash
            ;;
        *)
            error "未知服务: $service"
            echo "用法: $0 shell [backend|frontend|worker]"
            ;;
    esac
}

# ═══════════════════════════════════════════════════════
# 主命令路由
# ═══════════════════════════════════════════════════════
case "${1:-}" in
    start)
        check_docker
        start_service "${2:-all}" "$3"
        ;;
    stop)
        header "停止 SupaWriter 服务"
        stop_service "${2:-all}"
        ;;
    restart)
        restart_service "${2:-all}"
        ;;
    status)
        show_status
        ;;
    logs)
        view_logs "${2:-all}" "${3:-}"
        ;;
    health)
        health_check
        ;;
    db)
        db_migrate "${2:-upgrade}"
        ;;
    test)
        run_tests "${2:-all}"
        ;;
    admin)
        case "${2:-}" in
            add)
                admin_add "$3"
                ;;
            remove)
                admin_remove "$3"
                ;;
            list)
                admin_list
                ;;
            *)
                echo ""
                echo -e "${BOLD}管理员管理:${NC}"
                echo "  $0 admin add <email>      添加超级管理员"
                echo "  $0 admin remove <email>   移除超级管理员"
                echo "  $0 admin list             列出所有超级管理员"
                echo ""
                echo -e "${BOLD}示例:${NC}"
                echo "  $0 admin add user@example.com"
                ;;
        esac
        ;;
    install)
        check_dependencies
        setup_env
        build_images
        success "安装完成"
        ;;
    build)
        build_images
        ;;
    push)
        push_images
        ;;
    pull)
        pull_images
        ;;
    clean)
        clean_all
        ;;
    shell)
        shell_into "${2:-backend}"
        ;;
    *)
        echo ""
        echo -e "${BOLD}SupaWriter 服务管理脚本 v3.0${NC}"
        echo -e "全容器化版本 — 所有服务通过 Docker Compose 管理"
        echo ""
        echo -e "${BOLD}用法:${NC} $0 <命令> [参数]"
        echo ""
        echo -e "${BOLD}环境切换:${NC}"
        echo "  COMPOSE_ENV=dev  $0 <命令>    开发环境（默认，端口 8001/3001/8766）"
        echo "  COMPOSE_ENV=prod $0 <命令>    生产环境（端口 8000/3001/8765）"
        echo ""
        echo -e "${BOLD}服务管理:${NC}"
        echo "  start [--build] [backend|frontend|worker|trendradar|all]"
        echo "                                  启动服务（默认 all，--build 强制重建镜像）"
        echo "  stop  [backend|frontend|worker|trendradar|all]    停止服务（默认 all）"
        echo "  restart [backend|frontend|worker|trendradar|all]  重启服务（默认 all）"
        echo "  status                          查看所有服务状态"
        echo "  health                          API 健康检查"
        echo ""
        echo -e "${BOLD}开发工具:${NC}"
        echo "  logs [backend|frontend|worker|trendradar|all] [N] 查看日志（默认 all，最近 N 行）"
        echo "  test [all|core|models|repos|services|middleware|<path>]"
        echo "                                  运行测试"
        echo "  db [upgrade|downgrade|history|current]"
        echo "                                  数据库迁移管理"
        echo "  shell [backend|frontend|worker] 进入容器 shell"
        echo ""
        echo -e "${BOLD}环境管理:${NC}"
        echo "  install                         安装依赖 + 配置环境 + 构建镜像"
        echo "  build                           构建 Docker 镜像"
        echo "  push                            构建并推送镜像到 DockerHub"
        echo "  pull                            从 DockerHub 拉取最新镜像"
        echo "  clean                           停止服务 + 清理容器/卷/镜像"
        echo "  admin [add|remove|list]         管理超级管理员"
        echo ""
        echo -e "${BOLD}示例:${NC}"
        echo "  $0 start                  # 启动全部服务（使用缓存镜像）"
        echo "  $0 start --build          # 重新构建并启动全部服务"
        echo "  $0 start backend          # 仅启动后端"
        echo "  COMPOSE_ENV=prod $0 start # 启动全部服务（生产模式）"
        echo "  $0 restart backend        # 重启后端"
        echo "  $0 logs backend 100       # 查看后端最近 100 行日志"
        echo "  $0 test core              # 运行核心模块测试"
        echo "  $0 db upgrade             # 执行数据库迁移"
        echo "  $0 push                   # 构建并推送镜像到 DockerHub"
        echo "  $0 pull                   # 拉取最新镜像"
        echo "  $0 health                 # API 健康检查"
        echo "  $0 shell backend          # 进入后端容器"
        echo ""
        exit 1
        ;;
esac

exit 0
