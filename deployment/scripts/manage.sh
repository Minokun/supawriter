#!/bin/bash

# SupaWriter PostgreSQL 管理脚本
# 提供启动、停止、重启、备份、监控等功能

PROJECT_DIR="/opt/supawriter"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
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

# 检查项目目录
check_project_dir() {
    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "项目目录 $PROJECT_DIR 不存在，请先运行部署脚本"
        exit 1
    fi
}

# 启动服务
start_services() {
    print_info "启动 SupaWriter 服务..."
    cd $PROJECT_DIR
    docker-compose up -d
    
    if [ $? -eq 0 ]; then
        print_success "服务启动成功"
        sleep 5
        show_status
    else
        print_error "服务启动失败"
        exit 1
    fi
}

# 停止服务
stop_services() {
    print_info "停止 SupaWriter 服务..."
    cd $PROJECT_DIR
    docker-compose down
    
    if [ $? -eq 0 ]; then
        print_success "服务停止成功"
    else
        print_error "服务停止失败"
        exit 1
    fi
}

# 重启服务
restart_services() {
    print_info "重启 SupaWriter 服务..."
    cd $PROJECT_DIR
    docker-compose restart
    
    if [ $? -eq 0 ]; then
        print_success "服务重启成功"
        sleep 5
        show_status
    else
        print_error "服务重启失败"
        exit 1
    fi
}

# 显示服务状态
show_status() {
    print_info "服务状态："
    cd $PROJECT_DIR
    docker-compose ps
    
    echo ""
    print_info "数据库连接测试："
    docker-compose exec -T postgres pg_isready -U supawriter -d supawriter
    
    if [ $? -eq 0 ]; then
        print_success "数据库连接正常"
    else
        print_warning "数据库连接异常"
    fi
}

# 查看日志
show_logs() {
    local service=${1:-""}
    cd $PROJECT_DIR
    
    if [ -z "$service" ]; then
        print_info "显示所有服务日志（按 Ctrl+C 退出）："
        docker-compose logs -f
    else
        print_info "显示 $service 服务日志（按 Ctrl+C 退出）："
        docker-compose logs -f $service
    fi
}

# 备份数据库
backup_database() {
    print_info "开始备份数据库..."
    
    BACKUP_DIR="$PROJECT_DIR/postgres/backups"
    DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="supawriter_backup_$DATE.sql"
    
    cd $PROJECT_DIR
    docker-compose exec -T postgres pg_dump -U supawriter -d supawriter > "$BACKUP_DIR/$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        # 压缩备份文件
        gzip "$BACKUP_DIR/$BACKUP_FILE"
        print_success "备份完成: $BACKUP_FILE.gz"
        
        # 显示备份文件大小
        backup_size=$(du -h "$BACKUP_DIR/$BACKUP_FILE.gz" | cut -f1)
        print_info "备份文件大小: $backup_size"
        
        # 清理30天前的备份
        find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
        print_info "已清理30天前的旧备份"
    else
        print_error "备份失败"
        exit 1
    fi
}

# 恢复数据库
restore_database() {
    local backup_file=$1
    
    if [ -z "$backup_file" ]; then
        print_error "请指定备份文件路径"
        echo "用法: $0 restore <backup_file.sql.gz>"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        print_error "备份文件不存在: $backup_file"
        exit 1
    fi
    
    print_warning "恢复数据库将覆盖现有数据，是否继续？(y/N)"
    read -r confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        print_info "操作已取消"
        exit 0
    fi
    
    print_info "开始恢复数据库..."
    cd $PROJECT_DIR
    
    # 解压并恢复
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" | docker-compose exec -T postgres psql -U supawriter -d supawriter
    else
        docker-compose exec -T postgres psql -U supawriter -d supawriter < "$backup_file"
    fi
    
    if [ $? -eq 0 ]; then
        print_success "数据库恢复完成"
    else
        print_error "数据库恢复失败"
        exit 1
    fi
}

# 系统监控
show_monitor() {
    print_info "=== SupaWriter 系统监控 ==="
    
    echo ""
    print_info "服务状态："
    cd $PROJECT_DIR
    docker-compose ps
    
    echo ""
    print_info "数据库状态："
    docker-compose exec -T postgres pg_isready -U supawriter -d supawriter
    
    echo ""
    print_info "磁盘使用情况："
    df -h $PROJECT_DIR
    
    echo ""
    print_info "内存使用情况："
    free -h
    
    echo ""
    print_info "Docker 容器资源使用："
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
    
    echo ""
    print_info "数据库连接数："
    docker-compose exec -T postgres psql -U supawriter -d supawriter -c "
        SELECT count(*) as connections, state 
        FROM pg_stat_activity 
        WHERE datname = 'supawriter'
        GROUP BY state;
    " 2>/dev/null || print_warning "无法获取数据库连接信息"
    
    echo ""
    print_info "数据库大小："
    docker-compose exec -T postgres psql -U supawriter -d supawriter -c "
        SELECT 
            pg_size_pretty(pg_database_size('supawriter')) as db_size;
    " 2>/dev/null || print_warning "无法获取数据库大小信息"
}

# 更新配置
update_config() {
    print_info "重新加载配置文件..."
    cd $PROJECT_DIR
    
    # 重启服务以应用新配置
    docker-compose restart postgres
    
    if [ $? -eq 0 ]; then
        print_success "配置更新完成"
    else
        print_error "配置更新失败"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "SupaWriter PostgreSQL 管理脚本"
    echo ""
    echo "用法: $0 <command> [options]"
    echo ""
    echo "命令："
    echo "  start                启动所有服务"
    echo "  stop                 停止所有服务"
    echo "  restart              重启所有服务"
    echo "  status               显示服务状态"
    echo "  logs [service]       查看日志 (可选指定服务名)"
    echo "  backup               备份数据库"
    echo "  restore <file>       恢复数据库"
    echo "  monitor              显示系统监控信息"
    echo "  update-config        重新加载配置"
    echo "  help                 显示此帮助信息"
    echo ""
    echo "示例："
    echo "  $0 start             # 启动服务"
    echo "  $0 logs postgres     # 查看PostgreSQL日志"
    echo "  $0 backup            # 备份数据库"
    echo "  $0 restore backup.sql.gz  # 恢复数据库"
    echo ""
}

# 主函数
main() {
    case "$1" in
        start)
            check_project_dir
            start_services
            ;;
        stop)
            check_project_dir
            stop_services
            ;;
        restart)
            check_project_dir
            restart_services
            ;;
        status)
            check_project_dir
            show_status
            ;;
        logs)
            check_project_dir
            show_logs $2
            ;;
        backup)
            check_project_dir
            backup_database
            ;;
        restore)
            check_project_dir
            restore_database $2
            ;;
        monitor)
            check_project_dir
            show_monitor
            ;;
        update-config)
            check_project_dir
            update_config
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
