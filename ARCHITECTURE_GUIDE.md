# SupaWriter 项目架构指南

## 📋 项目概述

SupaWriter 是一个智能写作平台，目前包含**两套独立的架构**：

1. **Streamlit 架构**（原始版本）- 快速原型和内容创作工具
2. **前后端分离架构**（新版本）- Next.js + FastAPI，适合生产环境

---

## 🏗️ 架构一：Streamlit 单体应用

### 技术栈
- **框架**: Streamlit (Python)
- **端口**: 8501
- **数据库**: PostgreSQL / SQLite
- **认证**: Google OAuth2 + 微信登录 + 本地账号

### 目录结构
```
supawriter/
├── web.py                    # Streamlit 主入口
├── main.py                   # 备用入口
├── page/                     # 页面模块
│   ├── auto_write.py        # 文章生成页面
│   ├── hotspots.py          # 全网热点页面
│   ├── history.py           # 历史记录页面
│   ├── tweet_topics.py      # 推文选题页面
│   └── ...                  # 其他页面
├── utils/                    # 工具模块
│   ├── searxng_utils.py     # 搜索引擎工具
│   ├── llm_chat.py          # LLM 调用
│   ├── database.py          # 数据库操作
│   ├── wechat_converter.py  # 微信格式转换
│   └── ...                  # 其他工具
├── auth_pages/              # 认证页面
│   ├── login_v2.py          # 登录页面
│   ├── profile.py           # 用户资料
│   └── ...
├── components/              # UI 组件
└── .streamlit/              # Streamlit 配置
    └── secrets.toml         # API 密钥配置
```

### 核心功能
- ✅ 智能文章生成（基于搜索引擎 + LLM）
- ✅ 全网热点追踪（36Kr、百度、微博、抖音）
- ✅ 推文选题生成
- ✅ 历史记录管理
- ✅ 微信公众号预览
- ✅ 多模态图片处理
- ✅ 多渠道认证系统

### 启动方式

#### 方式 1：直接启动 Streamlit（推荐）
```bash
# 安装依赖
uv sync
# 或
pip install -r requirements.txt

# 启动应用
streamlit run web.py
# 或
uv run streamlit run web.py

# 访问地址
http://localhost:8501
```

#### 方式 2：使用统一启动脚本
```bash
# 仅启动 Streamlit
uv run python3 start_unified.py

# 同时启动前端和后端（混合模式）
uv run python3 start_unified.py --with-frontend
```

### 配置文件
主要配置文件：`.streamlit/secrets.toml`

```toml
# Google OAuth2 配置
[auth.google]
client_id = "your_google_client_id.apps.googleusercontent.com"
client_secret = "your_google_client_secret"

# 微信开放平台配置
[wechat]
app_id = "your_wechat_app_id"
app_secret = "your_wechat_app_secret"
redirect_uri = "http://localhost:8501"

# AI 模型配置
[openai]
model = "gpt-4-turbo"
base_url = "https://api.openai.com/v1"
api_key = "your_openai_api_key"

# 搜索引擎 API
SERPER_API_KEY = "your_serper_api_key"
```

---

## 🏗️ 架构二：前后端分离架构

### 技术栈
- **前端**: Next.js 14 + React 18 + TypeScript + Tailwind CSS
- **后端**: FastAPI + Python 3.14
- **数据库**: PostgreSQL
- **缓存**: Redis
- **认证**: NextAuth.js (前端) + JWT (后端)

### 目录结构
```
supawriter/
├── frontend/                 # Next.js 前端
│   ├── src/
│   │   ├── app/             # 页面路由
│   │   │   ├── api/auth/    # NextAuth.js 配置
│   │   │   ├── auth/        # 登录页面
│   │   │   ├── workspace/   # 工作空间
│   │   │   └── settings/    # 设置页面
│   │   ├── components/      # React 组件
│   │   ├── lib/             # 工具库
│   │   │   └── api/         # TypeScript SDK
│   │   └── middleware.ts    # 中间件
│   ├── .env.local           # 前端环境变量
│   └── package.json
│
├── backend/                 # FastAPI 后端
│   ├── api/
│   │   ├── main.py          # 主入口
│   │   ├── config/          # 配置
│   │   ├── core/            # 核心模块
│   │   │   ├── encryption.py
│   │   │   └── redis_client.py
│   │   ├── models/          # 数据模型
│   │   ├── routes/          # API 路由
│   │   │   ├── settings.py
│   │   │   ├── articles_enhanced.py
│   │   │   └── hotspots.py
│   │   └── services/        # 业务逻辑
│   ├── tests/               # 测试
│   └── requirements_api.txt
│
└── deployment/              # 部署配置
    ├── docker-compose.full.yml
    ├── nginx/
    └── postgres/
```

### 服务架构图
```
┌─────────────────────────────────────────────────────────┐
│                    用户浏览器                            │
└────────────┬────────────────────────────┬────────────────┘
             │                            │
             │ http://localhost:3000      │ http://localhost:8000
             ↓                            ↓
┌─────────────────────────┐    ┌─────────────────────────┐
│   Next.js 前端服务       │    │   FastAPI 后端服务       │
│   (端口 3000)           │←───│   (端口 8000)           │
│                         │    │                         │
│  - 用户界面             │    │  - Google OAuth 认证    │
│  - NextAuth.js 认证     │    │  - JWT Token 验证       │
│  - Session 管理         │    │  - 业务逻辑 API         │
│  - 页面路由             │    │  - 文章生成             │
└─────────────────────────┘    └────────┬────────────────┘
                                        │
                                        ↓
                            ┌─────────────────────────┐
                            │   PostgreSQL 数据库      │
                            │   Redis 缓存            │
                            └─────────────────────────┘
```

### 启动方式

#### 方式 1：使用 manage.sh 脚本（推荐）
```bash
# 一键启动所有服务（前端 + 后端）
./manage.sh start

# 查看服务状态
./manage.sh status

# 查看日志
./manage.sh logs all          # 所有日志
./manage.sh logs backend      # 后端日志
./manage.sh logs frontend     # 前端日志

# 停止服务
./manage.sh stop

# 重启服务
./manage.sh restart
```

#### 方式 2：手动启动
```bash
# 1. 启动后端
cd backend
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 2. 启动前端（新终端）
cd frontend
npm run dev

# 访问地址
# 前端: http://localhost:3000
# 后端 API: http://localhost:8000/docs
```

#### 方式 3：Docker 部署
```bash
# 配置环境变量
cp deployment/.env.example deployment/.env
vim deployment/.env

# 一键启动
./deploy.sh

# 访问地址
# 前端: http://localhost:3000
# 后端: http://localhost:8000
# Streamlit: http://localhost:8501
```

### 配置文件

#### 前端配置 (frontend/.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=超能写手

# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=生成的随机密钥

# Google OAuth
GOOGLE_CLIENT_ID=你的客户端ID
GOOGLE_CLIENT_SECRET=你的客户端密钥
```

#### 后端配置 (.env)
```env
JWT_SECRET_KEY=与NEXTAUTH_SECRET相同
DATABASE_URL=postgresql://user:password@localhost:5432/supawriter
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## 🆚 两种架构对比

| 特性 | Streamlit 架构 | 前后端分离架构 |
|------|---------------|---------------|
| **适用场景** | 快速原型、内容创作 | 生产环境、大规模部署 |
| **技术栈** | Python + Streamlit | Next.js + FastAPI |
| **并发能力** | 10-20 用户 | 1000+ 用户 |
| **响应速度** | 500ms+ | <100ms |
| **部署难度** | 简单 | 中等 |
| **可扩展性** | 低 | 高 |
| **维护成本** | 低 | 中等 |
| **前后端耦合** | 是 | 否 |
| **API 支持** | 无 | 完整 RESTful API |

---

## 🚀 快速启动指南

### 场景 1：我只想快速使用写作工具
**推荐：Streamlit 架构**

```bash
# 1. 安装依赖
uv sync

# 2. 配置 API 密钥
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
vim .streamlit/secrets.toml  # 填入你的 API 密钥

# 3. 启动应用
streamlit run web.py

# 4. 访问
http://localhost:8501
```

### 场景 2：我要开发新功能或部署到生产环境
**推荐：前后端分离架构**

```bash
# 1. 安装依赖
./manage.sh install

# 2. 配置环境变量
# 前端配置
cp frontend/.env.local.example frontend/.env.local
vim frontend/.env.local

# 后端配置
vim .env

# 3. 启动服务
./manage.sh start

# 4. 访问
# 前端: http://localhost:3000
# 后端 API: http://localhost:8000/docs
```

### 场景 3：我要同时运行两套架构
```bash
# 1. 启动前后端分离架构
./manage.sh start

# 2. 启动 Streamlit（新终端）
streamlit run web.py

# 访问地址
# Streamlit: http://localhost:8501
# Next.js 前端: http://localhost:3000
# FastAPI 后端: http://localhost:8000
```

---

## 📁 重要文件说明

### 核心文档
- `README.md` - 项目总览和功能介绍
- `QUICK_START.md` - 快速启动指南
- `ARCHITECTURE_GUIDE.md` - 本文档，架构说明
- `SERVICE_ARCHITECTURE.md` - 服务架构详细说明
- `FINAL_DELIVERY.md` - 架构迁移交付文档
- `IMPLEMENTATION_SUMMARY.md` - 实施总结

### 配置文件
- `.streamlit/secrets.toml` - Streamlit API 密钥配置
- `frontend/.env.local` - Next.js 前端环境变量
- `.env` - FastAPI 后端环境变量
- `deployment/.env` - Docker 部署环境变量

### 启动脚本
- `web.py` - Streamlit 主入口
- `manage.sh` - 前后端服务管理脚本
- `start_unified.py` - 统一启动脚本
- `deploy.sh` - Docker 一键部署脚本

---

## 🔧 常见问题

### Q1: 我应该使用哪个架构？
- **个人使用、快速原型**: 使用 Streamlit 架构
- **团队协作、生产部署**: 使用前后端分离架构
- **两者都可以**: 可以同时运行，互不干扰

### Q2: 两个架构的数据是共享的吗？
是的，两个架构使用相同的数据库和工具模块，数据完全共享。

### Q3: 如何从 Streamlit 迁移到前后端分离架构？
不需要迁移，两个架构可以并存。前后端分离架构复用了 Streamlit 的核心逻辑。

### Q4: 端口冲突怎么办？
- Streamlit: 8501
- Next.js 前端: 3000
- FastAPI 后端: 8000

如果端口被占用，可以修改配置文件或使用 `./manage.sh stop` 停止服务。

### Q5: 如何查看日志？
```bash
# Streamlit 日志
streamlit run web.py  # 直接在终端显示

# 前后端分离架构日志
./manage.sh logs all
./manage.sh logs backend
./manage.sh logs frontend
```

---

## 📞 获取帮助

- **查看详细文档**: `README.md`
- **快速启动**: `QUICK_START.md`
- **API 文档**: http://localhost:8000/docs
- **服务管理**: `./manage.sh --help`

---

**最后更新**: 2026-02-02
**版本**: 1.0.0
