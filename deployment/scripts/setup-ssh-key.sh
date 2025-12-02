#!/bin/bash

# SSH 密钥配置脚本
# 帮助用户快速配置SSH密钥认证，避免部署时多次输入密码

set -e

# 默认配置
DEFAULT_SERVER_IP="YOUR_SERVER_IP"
DEFAULT_SERVER_USER="YOUR_USERNAME"

# 尝试从配置文件加载服务器信息
load_server_config() {
    local config_file="../servers.conf"
    
    if [ -f "$config_file" ]; then
        echo "ℹ️  发现服务器配置文件，正在加载..."
        source "$config_file"
        
        # 如果没有通过命令行指定，使用配置文件中的生产环境配置
        if [ "$SERVER_IP" = "$DEFAULT_SERVER_IP" ] && [ -n "$PROD_SERVER_IP" ]; then
            SERVER_IP="$PROD_SERVER_IP"
            SERVER_USER="$PROD_SERVER_USER"
            echo "✅ 使用配置文件中的生产环境: $PROD_SERVER_NAME ($SERVER_IP)"
        fi
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

# 显示帮助
show_help() {
    echo "SSH 密钥配置脚本"
    echo ""
    echo "用法: $0 [options]"
    echo ""
    echo "选项："
    echo "  --server-ip IP       指定服务器IP (默认: $SERVER_IP)"
    echo "  --server-user USER   指定服务器用户 (默认: $SERVER_USER)"
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
    echo "示例："
    echo "  $0                                    # 使用配置文件或默认配置"
    echo "  $0 --server-ip 192.168.1.100         # 指定服务器IP"
    echo "  $0 --server-user root                 # 指定服务器用户"
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

# 检查是否已有SSH密钥
check_existing_key() {
    print_info "检查现有SSH密钥..."
    
    if [ -f ~/.ssh/id_rsa.pub ]; then
        print_success "发现现有SSH公钥: ~/.ssh/id_rsa.pub"
        
        echo ""
        print_info "当前公钥内容："
        cat ~/.ssh/id_rsa.pub
        echo ""
        
        read -p "是否使用现有密钥？(Y/n): " use_existing
        if [[ $use_existing =~ ^[Nn]$ ]]; then
            return 1
        else
            return 0
        fi
    else
        print_info "未发现现有SSH密钥，将生成新密钥"
        return 1
    fi
}

# 生成SSH密钥
generate_ssh_key() {
    print_info "生成SSH密钥对..."
    
    # 备份现有密钥（如果存在）
    if [ -f ~/.ssh/id_rsa ]; then
        backup_file=~/.ssh/id_rsa.backup.$(date +%Y%m%d_%H%M%S)
        print_warning "备份现有私钥到: $backup_file"
        cp ~/.ssh/id_rsa $backup_file
    fi
    
    # 生成新密钥
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "" -C "supawriter-deploy@$(hostname)"
    
    if [ $? -eq 0 ]; then
        print_success "SSH密钥生成成功"
        print_info "私钥: ~/.ssh/id_rsa"
        print_info "公钥: ~/.ssh/id_rsa.pub"
    else
        print_error "SSH密钥生成失败"
        exit 1
    fi
}

# 复制公钥到服务器
copy_key_to_server() {
    print_info "复制公钥到服务器..."
    
    # 检查服务器连接
    print_info "测试服务器连接..."
    if ! ssh -o ConnectTimeout=10 ${SERVER_USER}@${SERVER_IP} "echo 'SSH连接成功'" >/dev/null 2>&1; then
        print_error "无法连接到服务器 ${SERVER_USER}@${SERVER_IP}"
        print_info "请检查服务器IP和用户名是否正确"
        exit 1
    fi
    
    # 使用ssh-copy-id复制公钥
    print_info "复制公钥到服务器（需要输入服务器密码）..."
    ssh-copy-id -i ~/.ssh/id_rsa.pub ${SERVER_USER}@${SERVER_IP}
    
    if [ $? -eq 0 ]; then
        print_success "公钥复制成功"
    else
        print_error "公钥复制失败"
        exit 1
    fi
}

# 测试密钥认证
test_key_auth() {
    print_info "测试SSH密钥认证..."
    
    # 测试无密码连接
    if ssh -o ConnectTimeout=10 -o BatchMode=yes ${SERVER_USER}@${SERVER_IP} "echo 'SSH密钥认证测试成功'" >/dev/null 2>&1; then
        print_success "SSH密钥认证配置成功！"
        print_info "现在可以无密码连接到服务器"
        return 0
    else
        print_error "SSH密钥认证测试失败"
        print_info "可能的原因："
        print_info "1. 服务器SSH配置不允许密钥认证"
        print_info "2. 公钥权限设置不正确"
        print_info "3. 网络连接问题"
        return 1
    fi
}

# 显示配置信息
show_config_info() {
    echo ""
    print_success "🎉 SSH密钥认证配置完成！"
    echo ""
    print_info "📋 配置信息："
    print_info "  服务器: ${SERVER_USER}@${SERVER_IP}"
    print_info "  私钥: ~/.ssh/id_rsa"
    print_info "  公钥: ~/.ssh/id_rsa.pub"
    echo ""
    print_info "🚀 现在可以使用快速部署脚本："
    print_info "  ./quick-deploy.sh"
    echo ""
    print_info "💡 其他有用命令："
    print_info "  ssh ${SERVER_USER}@${SERVER_IP}                    # 无密码登录服务器"
    print_info "  scp file.txt ${SERVER_USER}@${SERVER_IP}:/tmp/     # 无密码传输文件"
    echo ""
}

# 主函数
main() {
    echo "🔑 SSH 密钥认证配置"
    echo "==================="
    
    # 加载服务器配置
    load_server_config
    
    echo "服务器: ${SERVER_USER}@${SERVER_IP}"
    echo ""
    
    # 检查现有密钥
    if ! check_existing_key; then
        generate_ssh_key
    fi
    
    # 复制公钥到服务器
    copy_key_to_server
    
    # 测试密钥认证
    if test_key_auth; then
        show_config_info
    else
        print_warning "SSH密钥认证配置可能存在问题，但公钥已复制到服务器"
        print_info "请检查服务器SSH配置或联系系统管理员"
    fi
}

# 解析参数并执行
parse_args "$@"
main
