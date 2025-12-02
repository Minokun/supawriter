#!/bin/bash

# SupaWriter PostgreSQL Docker 部署脚本
# 适用于腾讯云 4核4G 轻量服务器

set -e

echo "🚀 开始部署 SupaWriter PostgreSQL 环境..."

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com | bash
    systemctl start docker
    systemctl enable docker
    usermod -aG docker $USER
    echo "✅ Docker 安装完成"
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，正在安装..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose 安装完成"
fi

# 创建项目目录
PROJECT_DIR="/opt/supawriter"
echo "📁 创建项目目录: $PROJECT_DIR"
mkdir -p $PROJECT_DIR/{postgres/{data,init,config,backups},redis/data,nginx/{conf.d,ssl},data/html,pgadmin}

# 复制配置文件
echo "📋 复制配置文件..."
# 脚本在 /tmp/supawriter-deployment/scripts/ 目录运行
# 配置文件在 /tmp/supawriter-deployment/ 目录
REMOTE_DEPLOY_DIR="/tmp/supawriter-deployment"
cp $REMOTE_DEPLOY_DIR/docker-compose.yml $PROJECT_DIR/
cp $REMOTE_DEPLOY_DIR/.env $PROJECT_DIR/.env
cp $REMOTE_DEPLOY_DIR/postgres/config/postgresql.conf $PROJECT_DIR/postgres/config/
cp $REMOTE_DEPLOY_DIR/postgres/config/pg_hba.conf $PROJECT_DIR/postgres/config/
cp $REMOTE_DEPLOY_DIR/postgres/init/01-init.sql $PROJECT_DIR/postgres/init/

# 设置权限
echo "🔐 设置目录权限..."
chown -R 999:999 $PROJECT_DIR/postgres/data  # PostgreSQL 用户
chown -R 999:999 $PROJECT_DIR/redis/data      # Redis 用户
chown -R 5050:5050 $PROJECT_DIR/pgadmin       # pgAdmin 用户

# 密码已在配置文件中预设
echo "🔑 使用预设密码..."
echo "✅ 密码配置完成"
echo "📝 PostgreSQL 密码: ^1234qwerasdf$"
echo "📝 pgAdmin 密码: ^1234qwerasdf$"

# 启动服务
cd $PROJECT_DIR
echo "🐳 启动 Docker 服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

# 测试数据库连接
echo "🧪 测试数据库连接..."
if docker-compose exec -T postgres pg_isready -U supawriter -d supawriter; then
    echo "✅ PostgreSQL 连接正常"
else
    echo "❌ PostgreSQL 连接失败"
    exit 1
fi

# 创建备份脚本
echo "💾 创建备份脚本..."
cat > $PROJECT_DIR/backup.sh << 'EOF'
#!/bin/bash
# PostgreSQL 备份脚本

BACKUP_DIR="/opt/supawriter/postgres/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="supawriter_backup_$DATE.sql"

echo "开始备份数据库..."
docker-compose exec -T postgres pg_dump -U supawriter -d supawriter > "$BACKUP_DIR/$BACKUP_FILE"

# 压缩备份文件
gzip "$BACKUP_DIR/$BACKUP_FILE"

echo "备份完成: $BACKUP_FILE.gz"

# 删除30天前的备份
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "清理完成"
EOF

chmod +x $PROJECT_DIR/backup.sh

# 设置定时备份
echo "⏰ 设置定时备份..."
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/supawriter/backup.sh >> /var/log/supawriter_backup.log 2>&1") | crontab -

# 创建监控脚本
cat > $PROJECT_DIR/monitor.sh << 'EOF'
#!/bin/bash
# 服务监控脚本

echo "=== SupaWriter 服务状态 ==="
docker-compose ps

echo -e "\n=== PostgreSQL 状态 ==="
docker-compose exec postgres pg_isready -U supawriter -d supawriter

echo -e "\n=== 磁盘使用情况 ==="
df -h /opt/supawriter

echo -e "\n=== 内存使用情况 ==="
free -h

echo -e "\n=== Docker 容器资源使用 ==="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
EOF

chmod +x $PROJECT_DIR/monitor.sh

# 输出访问信息
echo ""
echo "🎉 部署完成！"
echo ""
echo "📊 服务访问信息："
echo "   PostgreSQL: localhost:5432"
echo "   pgAdmin: http://your-server-ip:8080"
echo "   Redis: localhost:6379"
echo ""
echo "🔐 登录信息："
echo "   pgAdmin 邮箱: admin@supawriter.com"
echo "   pgAdmin 密码: $PGADMIN_PASSWORD"
echo "   PostgreSQL 用户: supawriter"
echo "   PostgreSQL 密码: $POSTGRES_PASSWORD"
echo ""
echo "📁 项目目录: $PROJECT_DIR"
echo "💾 备份脚本: $PROJECT_DIR/backup.sh"
echo "📊 监控脚本: $PROJECT_DIR/monitor.sh"
echo ""
echo "🔧 常用命令："
echo "   查看日志: cd $PROJECT_DIR && docker-compose logs -f"
echo "   重启服务: cd $PROJECT_DIR && docker-compose restart"
echo "   停止服务: cd $PROJECT_DIR && docker-compose down"
echo "   备份数据: $PROJECT_DIR/backup.sh"
echo "   监控状态: $PROJECT_DIR/monitor.sh"
echo ""
echo "✅ 部署完成！请保存好密码信息。"
