# SupaWriter 快速启动指南

## 🚀 一键 Docker 部署（推荐）

**最简单的部署方式，只需一条命令！**

### 前置要求
- Docker 20.10+
- Docker Compose 2.0+

### 部署步骤

#### 1. 克隆项目（如果还没有）
```bash
git clone <your-repo-url>
cd supawriter
```

#### 2. 配置环境变量
```bash
# 本地后端配置（根目录）
cp .env.example .env

# Docker 部署配置
cp deployment/.env.example deployment/.env

# 编辑配置文件
vim .env
vim deployment/.env
```

请确保 `.env` 和 `deployment/.env` 仅保留在本地，不要提交到仓库。

**必需配置项**：
```bash
# 数据库密码
POSTGRES_PASSWORD=your_secure_password

# JWT 密钥（生成命令：openssl rand -base64 32）
JWT_SECRET_KEY=your_jwt_secret_key

# 加密密钥（生成命令见下方）
ENCRYPTION_KEY=your_fernet_encryption_key
```

**生成加密密钥**：
```bash
# JWT/通用随机密钥
openssl rand -base64 32

# 方法1：使用 Python
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 方法2：使用 OpenSSL
openssl rand -base64 32
```

#### 3. 一键部署
```bash
./deployment/docker-start.sh
```

就这么简单！脚本会自动：
- ✅ 创建必要目录
- ✅ 构建应用镜像
- ✅ 先启动 PostgreSQL / Redis / TrendRadar 等基础设施
- ✅ 依次运行 schema drift repair、Alembic、production-state init
- ✅ 最后启动 backend / worker / frontend / nginx

#### 4. 访问服务

部署完成后，访问以下地址：

| 服务 | 地址 | 说明 |
|------|------|------|
| 🌐 Next.js 前端 | http://localhost:3001 | 新版前端界面 |
| 🚀 FastAPI 后端 | http://localhost:8000 | API 服务 |
| 📚 API 文档 | http://localhost:8000/docs | Swagger UI |
| 🎨 Streamlit | http://localhost:8501 | 旧版界面（兼容） |
| 🔄 Nginx | http://localhost | 反向代理 |

---

## 📋 常用管理命令

### 查看服务状态
```bash
docker-compose -f deployment/docker-compose.yml ps
```

### 查看日志
```bash
# 所有服务日志
docker-compose -f deployment/docker-compose.yml logs -f

# 特定服务日志
docker-compose -f deployment/docker-compose.yml logs -f backend
docker-compose -f deployment/docker-compose.yml logs -f frontend
```

### 重启服务
```bash
# 重启所有服务
docker-compose -f deployment/docker-compose.yml restart

# 重启特定服务
docker-compose -f deployment/docker-compose.yml restart backend
```

### 停止服务
```bash
docker-compose -f deployment/docker-compose.yml down
```

### 完全清理（包括数据）
```bash
docker-compose -f deployment/docker-compose.yml down -v
```

---

## 🔧 故障排查

### 问题1：端口被占用
```bash
# 检查端口占用
lsof -i :3001
lsof -i :8000
lsof -i :8501

# 修改端口（编辑 deployment/.env）
FRONTEND_PORT=3001
BACKEND_PORT=8001
```

### 问题2：数据库连接失败
```bash
# 检查数据库状态
docker-compose -f deployment/docker-compose.yml exec postgres pg_isready

# 查看数据库日志
docker-compose -f deployment/docker-compose.yml logs postgres
```

### 问题3：后端服务启动失败
```bash
# 查看后端日志
docker-compose -f deployment/docker-compose.yml logs backend

# 进入容器调试
docker-compose -f deployment/docker-compose.yml exec backend bash
```

### 问题4：前端无法连接后端
```bash
# 检查网络
docker network ls
docker network inspect supawriter_supawriter_network

# 检查环境变量
docker-compose -f deployment/docker-compose.yml exec frontend env | grep API
```

---

## 🔄 更新部署

### 拉取最新代码并重新部署
```bash
git pull
./deployment/docker-start.sh
```

### 仅重建特定服务
```bash
cd deployment
docker-compose -f docker-compose.yml up -d --build backend
```

---

## 📊 监控和维护

### 查看资源使用
```bash
docker stats
```

### 备份数据库
```bash
docker-compose -f deployment/docker-compose.yml exec postgres pg_dump -U supawriter supawriter > backup.sql
```

### 恢复数据库
```bash
cat backup.sql | docker-compose -f deployment/docker-compose.yml exec -T postgres psql -U supawriter supawriter
```

---

## 📖 更多文档

- **部署说明**: `deployment/README.md`
- **后端开发文档**: `FINAL_DELIVERY.md`
- **前端开发文档**: `FRONTEND_DEVELOPMENT.md`
- **实施总结**: `IMPLEMENTATION_SUMMARY.md`

---

## ✅ 部署检查清单

- [ ] Docker 和 Docker Compose 已安装
- [ ] 已配置 `deployment/.env` 文件
- [ ] 已生成 JWT_SECRET_KEY
- [ ] 已生成 ENCRYPTION_KEY
- [ ] 已设置 POSTGRES_PASSWORD
- [ ] 端口 3001, 8000, 8501, 5432, 6379 未被占用
- [ ] 运行 `./deployment/docker-start.sh` 成功
- [ ] 可以访问 http://localhost:3001
- [ ] 可以访问 http://localhost:8000/docs

---

**🎉 恭喜！SupaWriter 已成功部署！**

## 🚀 一键启动（推荐）

### 1. 安装依赖

```bash
# 使用 uv 安装所有依赖
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置检查和修复

```bash
# 运行配置检查工具（自动修复常见问题）
uv run python3 setup_config.py
```

### 3. 配置 Google OAuth（可选但推荐）

编辑 `.streamlit/secrets.toml`，添加 Google OAuth 配置：

```toml
[auth.google]
client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
client_secret = "YOUR_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

获取 Google OAuth 凭据：https://console.cloud.google.com/

### 4. 启动应用

```bash
# 方式 1: 仅启动 Streamlit 创作工具（推荐）
uv run streamlit run web.py

# 方式 2: 使用统一启动脚本
uv run python3 start_unified.py

# 方式 3: 同时启动前端和后端
uv run python3 start_unified.py --with-frontend
```

### 5. 访问应用

- **Streamlit 创作工具**: http://localhost:8501
- **Next.js 前端** (如果启用): http://localhost:3000

---

## 🔧 常见问题修复

### 问题 1: Google 登录失败

**症状**: 点击 Google 登录按钮无响应或报错

**解决方案**:

1. 确保 `.streamlit/secrets.toml` 中配置了正确的 Google OAuth 凭据
2. 检查 `redirect_uri` 是否为 `http://localhost:8501/oauth2callback`
3. 在 Google Cloud Console 中添加相同的重定向 URI

### 问题 2: 页面无数据

**症状**: 热点页面、新闻页面显示空白

**可能原因**:
- API 密钥未配置
- 网络连接问题
- 缓存问题

**解决方案**:

```bash
# 1. 检查 secrets.toml 中的 API 配置
cat .streamlit/secrets.toml | grep api_key

# 2. 清除 Streamlit 缓存
rm -rf ~/.streamlit/cache

# 3. 重启应用
```

### 问题 3: 数据库连接失败

**症状**: 无法注册/登录，提示数据库错误

**解决方案**:

```bash
# 1. 检查数据库配置
cat deployment/.env | grep DATABASE

# 2. 测试数据库连接
uv run python3 -c "from utils.database import Database; Database.get_connection_pool()"

# 3. 初始化数据库（如果是首次使用）
uv run python3 deployment/migrate/migrate_to_postgres.py
```

### 问题 4: 页面跳转不工作

**症状**: 点击"一键创作"等按钮无反应

**解决方案**:

这是已知问题，已在最新代码中修复。确保使用最新版本：

```bash
git pull origin main
uv sync
```

### 问题 5: 端口被占用

**症状**: 启动时提示端口 8501 已被占用

**解决方案**:

```bash
# macOS/Linux
lsof -ti:8501 | xargs kill -9

# 或使用统一启动脚本（会自动清理端口）
uv run python3 start_unified.py
```

---

## 📋 完整配置清单

### 必须配置 ✅

- [x] `.streamlit/secrets.toml` - cookie_secret（自动生成）
- [x] `deployment/.env` - 数据库连接（如果使用数据库）
- [x] `.streamlit/secrets.toml` - 至少一个 LLM API 密钥

### 推荐配置 ⭐

- [ ] Google OAuth 凭据（用于第三方登录）
- [ ] Serper API 密钥（用于搜索功能）
- [ ] 七牛云配置（用于图片存储）

### 可选配置 💡

- [ ] 微信 OAuth 配置
- [ ] 其他 LLM API 密钥（DeepSeek, Kimi, GLM 等）

---

## 🧪 测试功能

启动应用后，依次测试以下功能：

### 1. 认证系统
- [ ] 邮箱注册
- [ ] 邮箱登录
- [ ] Google 登录（如已配置）
- [ ] 退出登录

### 2. 核心功能
- [ ] 超能AI助手 - 发送消息
- [ ] 超能写手 - 生成文章
- [ ] 全网热点 - 查看热点列表
- [ ] 历史记录 - 查看已生成内容

### 3. 页面跳转
- [ ] 热点 → 超能写手
- [ ] 推文选题 → 超能写手
- [ ] 导航菜单切换

---

## 🎯 开发模式

### 启动开发环境

```bash
# 1. 激活虚拟环境（uv 自动管理）
uv sync

# 2. 启动 Streamlit（自动重载）
uv run streamlit run web.py --server.runOnSave=true

# 3. 启动前端开发服务器（另一个终端）
cd frontend
npm run dev
```

### 查看日志

```bash
# Streamlit 日志
tail -f ~/.streamlit/logs/streamlit.log

# 应用日志（如果配置了）
tail -f logs/app.log
```

---

## 📞 获取帮助

如果遇到问题：

1. **查看详细错误信息**: `BUG_FIXES.md`
2. **运行诊断工具**: `uv run python3 setup_config.py`
3. **查看日志**: `~/.streamlit/logs/`
4. **联系开发者**: 952718180@qq.com

---

**最后更新**: 2026-01-29
