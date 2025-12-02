#!/bin/bash

# SupaWriter PostgreSQL 快速部署脚本
# 一键上传并部署到服务器

set -e

# 默认配置信息
DEFAULT_SERVER_IP="YOUR_SERVER_IP"
DEFAULT_SERVER_USER="YOUR_USERNAME"
REMOTE_DIR="/tmp/supawriter-deployment"
PROJECT_DIR="/opt/supawriter"

# 尝试从配置文件加载服务器信息
load_server_config() {
    local config_file="../servers.conf"
    
    if [ -f "$config_file" ]; then
        print_info "发现服务器配置文件，正在加载..."
        source "$config_file"
        
        # 如果没有通过命令行指定，使用配置文件中的生产环境配置
        if [ "$SERVER_IP" = "$DEFAULT_SERVER_IP" ] && [ -n "$PROD_SERVER_IP" ]; then
            SERVER_IP="$PROD_SERVER_IP"
            SERVER_USER="$PROD_SERVER_USER"
            print_success "使用配置文件中的生产环境: $PROD_SERVER_NAME ($SERVER_IP)"
        fi
    else
        print_warning "未找到服务器配置文件 $config_file"
        print_info "你可以："
        print_info "1. 复制 servers.conf.example 为 servers.conf 并配置"
        print_info "2. 使用命令行参数指定服务器信息"
        print_info "3. 直接修改脚本中的默认配置"
    fi
}

# 初始化服务器配置
SERVER_IP="$DEFAULT_SERVER_IP"
SERVER_USER="$DEFAULT_SERVER_USER"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查本地文件
check_local_files() {
    print_info "检查本地部署文件..."
    
    local required_files=(
        "../docker-compose.yml"
        "../.env"
        "../postgres/config/postgresql.conf"
        "../postgres/config/pg_hba.conf"
        "../postgres/init/01-init.sql"
        "deploy.sh"
        "manage.sh"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "缺少必要文件: $file"
            exit 1
        fi
    done
    
    print_success "本地文件检查完成"
}

# 准备并上传文件到服务器
upload_files() {
    print_info "准备部署文件..."
    
    # 创建本地临时目录，准备所有文件
    local temp_dir="/tmp/supawriter-deploy-$$"
    mkdir -p ${temp_dir}/{postgres/{config,init},scripts}
    
    # 复制所有文件到临时目录
    cp ../docker-compose.yml ${temp_dir}/
    cp ../.env ${temp_dir}/
    cp ../postgres/config/postgresql.conf ${temp_dir}/postgres/config/
    cp ../postgres/config/pg_hba.conf ${temp_dir}/postgres/config/
    cp ../postgres/init/01-init.sql ${temp_dir}/postgres/init/
    cp deploy.sh ${temp_dir}/scripts/
    cp manage.sh ${temp_dir}/scripts/
    
    print_info "上传部署文件到服务器（只需输入一次密码）..."
    
    # 创建远程目录并一次性上传所有文件（包括隐藏文件）
    ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${REMOTE_DIR}" && \
    scp -r ${temp_dir}/. ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/
    
    # 清理本地临时目录
    rm -rf ${temp_dir}
    
    print_success "文件上传完成"
}

# 远程部署
remote_deploy() {
    print_info "开始远程部署..."
    
    ssh ${SERVER_USER}@${SERVER_IP} << EOF
        set -e
        
        # 进入部署目录
        cd ${REMOTE_DIR}/scripts
        
        # 设置执行权限
        chmod +x deploy.sh manage.sh
        
        # 执行部署
        echo "🚀 开始部署 SupaWriter PostgreSQL..."
        sudo ./deploy.sh
        
        # 复制管理脚本到项目目录
        sudo cp manage.sh ${PROJECT_DIR}/
        sudo chmod +x ${PROJECT_DIR}/manage.sh
        
        echo "✅ 部署完成！"
        echo ""
        echo "📊 服务状态："
        cd ${PROJECT_DIR}
        sudo docker-compose ps
        
        echo ""
        echo "🔗 访问信息："
        echo "   PostgreSQL: ${SERVER_IP}:5432"
        echo "   pgAdmin: http://${SERVER_IP}:8080"
        echo "   用户名: supawriter"
        echo "   密码: ^1234qwerasdf$"
        echo ""
        echo "🛠️  管理命令："
        echo "   sudo ${PROJECT_DIR}/manage.sh status    # 查看状态"
        echo "   sudo ${PROJECT_DIR}/manage.sh logs      # 查看日志"
        echo "   sudo ${PROJECT_DIR}/manage.sh backup    # 备份数据库"
        echo "   sudo ${PROJECT_DIR}/manage.sh monitor   # 系统监控"
EOF
    
    if [ $? -eq 0 ]; then
        print_success "远程部署完成！"
    else
        print_error "远程部署失败"
        exit 1
    fi
}

# 清理临时文件
cleanup() {
    print_info "清理服务器临时文件..."
    ssh ${SERVER_USER}@${SERVER_IP} "rm -rf ${REMOTE_DIR}"
    print_success "清理完成"
}

# 测试连接
test_connection() {
    print_info "测试数据库连接..."
    
    # 等待服务完全启动
    sleep 10
    
    # 测试PostgreSQL连接
    if command -v psql >/dev/null 2>&1; then
        echo "测试 PostgreSQL 连接..."
        PGPASSWORD='^1234qwerasdf$' psql -h ${SERVER_IP} -p 5432 -U supawriter -d supawriter -c "SELECT version();" >/dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            print_success "PostgreSQL 连接测试成功"
        else
            print_warning "PostgreSQL 连接测试失败（可能是防火墙或网络问题）"
        fi
    else
        print_warning "本地未安装 psql，跳过连接测试"
    fi
    
    # 测试pgAdmin访问
    print_info "pgAdmin 访问地址: http://${SERVER_IP}:8080"
    print_info "登录邮箱: admin@supawriter.com"
    print_info "登录密码: ^1234qwerasdf$"
}

# 显示帮助
show_help() {
    echo "SupaWriter PostgreSQL 快速部署脚本"
    echo ""
    echo "用法: $0 [options]"
    echo ""
    echo "选项："
    echo "  --server-ip IP       指定服务器IP (默认: $SERVER_IP)"
    echo "  --server-user USER   指定服务器用户 (默认: $SERVER_USER)"
    echo "  --no-test           跳过连接测试"
    echo "  --help              显示此帮助信息"
    echo ""
    echo "配置方式："
    echo "  1. 使用配置文件（推荐）："
    echo "     cp ../servers.conf.example ../servers.conf"
    echo "     vim ../servers.conf  # 配置服务器信息"
    echo "     $0                   # 自动使用配置文件中的生产环境"
    echo ""
    echo "  2. 使用命令行参数："
    echo "     $0 --server-ip 192.168.1.100 --server-user root"
    echo ""
    echo "  3. 直接修改脚本默认配置"
    echo ""
    echo "示例："
    echo "  $0                                    # 使用配置文件或默认配置"
    echo "  $0 --server-ip 192.168.1.100         # 指定服务器IP"
    echo "  $0 --server-user root                 # 指定服务器用户"
    echo ""
    echo "💡 提示："
    echo "  1. 配置SSH密钥认证避免多次输入密码："
    echo "     ./setup-ssh-key.sh"
    echo "  2. 使用配置文件管理多个服务器："
    echo "     cp ../servers.conf.example ../servers.conf"
    echo ""
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --server-ip)
                SERVER_IP="$2"
                shift 2
                ;;
            --server-user)
                SERVER_USER="$2"
                shift 2
                ;;
            --no-test)
                SKIP_TEST=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 主函数
main() {
    echo "🚀 SupaWriter PostgreSQL 快速部署"
    echo "=================================="
    
    # 加载服务器配置
    load_server_config
    
    echo "服务器: ${SERVER_USER}@${SERVER_IP}"
    echo ""
    
    # 检查SSH连接
    print_info "测试SSH连接..."
    
    # 检查是否配置了SSH密钥认证
    if ssh -o ConnectTimeout=10 -o BatchMode=yes ${SERVER_USER}@${SERVER_IP} "echo 'SSH密钥认证成功'" >/dev/null 2>&1; then
        print_success "SSH密钥认证连接成功（无需密码）"
        SSH_KEY_AUTH=true
    elif ssh -o ConnectTimeout=10 ${SERVER_USER}@${SERVER_IP} "echo 'SSH连接成功'" >/dev/null 2>&1; then
        print_success "SSH连接测试成功（需要密码认证）"
        print_warning "建议配置SSH密钥认证以避免多次输入密码："
        print_info "  ssh-keygen -t rsa -b 4096"
        print_info "  ssh-copy-id ${SERVER_USER}@${SERVER_IP}"
        SSH_KEY_AUTH=false
    else
        print_error "无法连接到服务器 ${SERVER_USER}@${SERVER_IP}"
        print_info "请检查："
        print_info "1. 服务器IP地址是否正确"
        print_info "2. SSH密钥或密码是否正确"
        print_info "3. 网络连接是否正常"
        exit 1
    fi
    
    # 执行部署步骤
    check_local_files
    upload_files
    remote_deploy
    cleanup
    
    if [ "$SKIP_TEST" != "true" ]; then
        test_connection
    fi
    
    echo ""
    print_success "🎉 部署完成！"
    echo ""
    print_info "📋 后续操作："
    print_info "1. 配置防火墙开放端口 5432 和 8080"
    print_info "2. 在应用中配置数据库连接字符串"
    print_info "3. 定期备份数据库"
    print_info "4. 监控服务运行状态"
}

# 解析参数并执行
parse_args "$@"
main
