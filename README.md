# SupaWriter 超能写手

<p align="center">
  <strong>AI 驱动的智能内容创作平台</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.95+-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js">
  <img src="https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Redis-7+-DC382D?logo=redis" alt="Redis">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

---

SupaWriter 是一个前后端分离的 AI 内容创作平台，集成大语言模型、搜索引擎和多模态技术，覆盖从资料收集、信息整理到内容创作的全流程。

## � 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx (80/443)                       │
│                        反向代理 + SSL                        │
├──────────────┬──────────────────┬───────────────────────────┤
│              │                  │                           │
│   Next.js    │   FastAPI API    │   Streamlit 创作工具       │
│   前端网站    │   后端服务        │   AI 写作 (独立部署)       │
│   :3000      │   :8000          │   :8501                   │
│              │                  │                           │
│  React 18    │  SQLAlchemy 2.0  │  多引擎搜索               │
│  TailwindCSS │  Async ORM      │  图像处理                  │
│  NextAuth    │  Redis 缓存/限流  │  文章生成                  │
│  Tiptap 编辑 │  Prometheus 监控  │  热点追踪                  │
│              │                  │                           │
├──────────────┴──────────────────┴───────────────────────────┤
│                                                             │
│   PostgreSQL 15+          Redis 7+          外部 AI 服务     │
│   主数据存储 :5432         缓存/限流 :6379    OpenAI / GLM    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

| 组件 | 技术栈 | 端口 | 说明 |
|------|--------|------|------|
| **后端 API** | FastAPI + SQLAlchemy 2.0 Async | 8000 | RESTful API、认证、业务逻辑 |
| **前端网站** | Next.js 14 + TailwindCSS | 3000 | 社区网站、文章管理、AI 助手 |
| **创作工具** | Streamlit | 8501 | AI 写作、热点追踪（可独立部署） |
| **数据库** | PostgreSQL 15+ | 5432 | 主数据存储 |
| **缓存** | Redis 7+ | 6379 | 缓存 + 分布式限流（可选） |
| **反向代理** | Nginx | 80/443 | 统一入口、SSL、负载均衡 |

---

## ✨ 核心功能

### 前端网站（Next.js）

- **AI 写作工作台** — Tiptap 富文本编辑器 + AI 辅助写作
- **AI 助手** — 对话式 AI 聊天
- **文章管理** — 创建、编辑、发布文章
- **灵感发现** — 热点话题、推文选题
- **推文选题** — 智能模式 + 手动模式，AI 筛选新闻生成选题
- **新闻聚合** — 多源新闻浏览
- **用户中心** — 个人设置、API Key 管理

### 后端 API（FastAPI）

- **分层架构** — Route → Service → Repository → ORM
- **异步 ORM** — SQLAlchemy 2.0 DeclarativeBase + asyncpg
- **多渠道认证** — JWT + Google OAuth2 + 微信扫码登录
- **Redis 缓存** — 装饰器式缓存，自动降级
- **分布式限流** — Redis ZSET 滑动窗口算法
- **审计日志** — 全链路请求追踪
- **配额管理** — 用户级别的 API/文章配额
- **性能监控** — Prometheus 指标 + Grafana 仪表板

### 创作工具（Streamlit）

- **智能文章生成** — 搜索引擎 + LLM 自动生成高质量文章
- **双引擎搜索** — SearXNG + Serper API 聚合搜索
- **多模态处理** — GLM-4.1v / Qwen-VL 图像理解与匹配
- **全网热点追踪** — 36Kr、百度、微博、抖音热搜聚合
- **公众号预览** — 一键转换为微信公众号格式
- **防盗链优化** — 支持 CSDN、知乎等 9 大网站图片下载

---

## 🔨 系统要求

| 依赖 | 版本 | 必须 | 说明 |
|------|------|------|------|
| **Python** | 3.12+ | ✅ | 后端运行时 |
| **Node.js** | 18+ | ✅ | 前端运行时 |
| **PostgreSQL** | 14+ | ✅ | 主数据库 |
| **Redis** | 6+ | ❌ | 缓存/限流（不装则自动降级） |
| **uv** | 最新 | 推荐 | Python 包管理（比 pip 快 10-100x） |
| **Docker** | 20+ | ❌ | 容器化部署时需要 |

---

## 🚀 快速开始

### 方式一：使用 manage.sh 一键启动（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-org/supawriter.git
cd supawriter

# 2. 一键安装依赖 + 配置环境
./manage.sh install

# 3. 启动全部服务（后端 + 前端）
./manage.sh start

# 4. 查看服务状态
./manage.sh status
```

启动后访问：
- 前端网站：http://localhost:3000
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 方式二：手动启动

#### 1. 安装依赖

```bash
# 后端（推荐使用 uv）
uv sync
# 或使用 pip
pip install -e .

# 前端
cd frontend && npm install && cd ..
```

#### 2. 配置环境变量

```bash
# 后端配置（根目录）
cp .env.example .env
vim .env
```

**必须配置的变量**：

```bash
# 数据库连接（二选一）
DATABASE_URL=postgresql://supawriter:your_password@localhost:5432/supawriter
# 或分开配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=supawriter
POSTGRES_USER=supawriter
POSTGRES_PASSWORD=your_password

# 安全密钥
SECRET_KEY=your-secret-key-change-in-production
SESSION_SECRET_KEY=your-session-secret-key
```

```bash
# 生成随机密钥示例（建议每台机器单独生成）
openssl rand -base64 32
```

```bash
# 前端配置
cp frontend/.env.example frontend/.env.local
vim frontend/.env.local
```

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret
```

#### 3. 初始化数据库

```bash
# 确保 PostgreSQL 已运行
./manage.sh db upgrade
```

#### 4. 启动服务

```bash
# 终端 1 - 后端
uv run uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend

# 终端 2 - 前端
cd frontend && npm run dev
```

### 方式三：Docker 容器化部署

```bash
# 1. 配置环境变量
cd deployment
cp .env.example .env
vim .env  # 设置数据库密码、密钥等

# 2. 生产环境一键部署（返回仓库根目录执行）
cd ..
./deployment/docker-start.sh

# 3. 开发环境（支持热重载）
cd deployment
docker-compose -f docker-compose.dev.yml up --build
```

Docker 部署包含：PostgreSQL、Redis、FastAPI 后端、Next.js 前端、Streamlit 创作工具、Nginx 反向代理。

---

## ⚙️ 配置说明

### 环境变量文件

| 文件 | 用途 | 说明 |
|------|------|------|
| `.env` | 后端主配置 | Pydantic Settings 自动加载 |
| `frontend/.env.local` | 前端配置 | Next.js 自动加载 |
| `.env.example` | 环境变量模板 | 包含所有可配置项及说明 |
| `deployment/.env.example` | Docker 部署模板 | 部署环境变量占位符 |
| `.streamlit/secrets.toml` | Streamlit 配置 | AI 模型密钥、OAuth 配置 |

### 后端关键配置（.env）

```bash
# ===== 应用 =====
DEBUG=true                              # 调试模式
ENVIRONMENT=development                 # 环境标识

# ===== 数据库 =====
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=supawriter
POSTGRES_USER=supawriter
POSTGRES_PASSWORD=your_password
POSTGRES_POOL_SIZE=5                    # 连接池大小
POSTGRES_MAX_OVERFLOW=10                # 最大溢出连接

# ===== Redis（可选）=====
REDIS_HOST=localhost
REDIS_PORT=6379

# ===== 限流 =====
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_USE_REDIS=true               # 使用 Redis 限流

# ===== 缓存 =====
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=300                   # 默认 5 分钟

# ===== 监控 =====
MONITORING_ENABLED=true
MONITORING_PROMETHEUS_ENABLED=true

# ===== OAuth =====
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

> 完整配置项请参考 [.env.example](.env.example)

### 认证系统

支持三种认证方式：

| 方式 | 配置位置 | 说明 |
|------|---------|------|
| **邮箱登录** | `.env` | JWT Token 认证 |
| **Google OAuth2** | `.env` + `frontend/.env.local` | 需要 Google Cloud 凭据 |
| **微信扫码** | `.env` | 需要微信开放平台凭据 |

---

## �️ 服务管理

`manage.sh` 是统一的服务管理脚本，支持以下命令：

### 服务控制

```bash
./manage.sh start                  # 启动全部（后端 + 前端）
./manage.sh start backend          # 仅启动后端
./manage.sh start frontend         # 仅启动前端
./manage.sh stop                   # 停止全部
./manage.sh stop backend           # 停止后端
./manage.sh restart                # 重启全部
./manage.sh restart backend        # 重启后端
./manage.sh status                 # 查看状态（含 PostgreSQL/Redis）
```

### 数据库管理

```bash
./manage.sh db upgrade             # 执行数据库迁移
./manage.sh db downgrade           # 回滚迁移
./manage.sh db history             # 查看迁移历史
./manage.sh db current             # 查看当前版本
```

### 运维工具

```bash
./manage.sh health                 # API 健康检查
./manage.sh logs backend 100       # 查看后端最近 100 行日志
./manage.sh logs frontend          # 查看前端日志
./manage.sh test all               # 运行全部测试
./manage.sh test core              # 运行核心模块测试
./manage.sh test repos             # 运行 Repository 测试
./manage.sh install                # 安装依赖 + 配置环境
./manage.sh clean                  # 清理缓存和临时文件
./manage.sh check                  # 检查基础设施依赖
```

---

## 📁 项目结构

```
supawriter/
├── backend/                        # 后端服务
│   ├── api/
│   │   ├── main.py                 # FastAPI 应用入口
│   │   ├── core/                   # 核心模块
│   │   │   ├── config.py           #   Pydantic Settings 配置
│   │   │   ├── dependencies.py     #   依赖注入
│   │   │   ├── security.py         #   JWT / 密码加密
│   │   │   ├── redis_manager.py    #   Redis 连接管理
│   │   │   ├── cache.py            #   缓存装饰器
│   │   │   └── monitoring.py       #   Prometheus 指标
│   │   ├── db/                     # 数据库层
│   │   │   ├── base.py             #   ORM Base + 引擎
│   │   │   ├── session.py          #   Session 管理
│   │   │   ├── models/             #   ORM 模型
│   │   │   └── migrations/         #   Alembic 迁移
│   │   ├── repositories/           # 数据访问层
│   │   ├── services/               # 业务逻辑层
│   │   ├── middleware/             # 中间件（限流/审计/配额）
│   │   ├── routes/                 # API 路由
│   │   └── models/                 # Pydantic 模型
│   └── tests/                      # 后端测试
├── frontend/                       # Next.js 前端
│   ├── src/app/                    # App Router 页面
│   │   ├── writer/                 #   AI 写作工作台
│   │   ├── ai-assistant/           #   AI 助手
│   │   ├── community/              #   社区
│   │   ├── news/                   #   新闻
│   │   ├── history/                #   历史记录
│   │   ├── settings/               #   用户设置
│   │   └── auth/                   #   认证页面
│   ├── src/components/             # React 组件
│   └── .env.local                  # 前端环境变量
├── page/                           # Streamlit 创作工具页面
├── utils/                          # Streamlit 工具函数
├── deployment/                     # 部署配置
│   ├── docker-compose.yml          #   生产环境编排
│   ├── docker-compose.dev.yml      #   开发环境编排
│   ├── Dockerfile.backend          #   后端镜像
│   ├── Dockerfile.frontend         #   前端镜像
│   ├── Dockerfile.streamlit        #   Streamlit 镜像
│   ├── nginx/                      #   Nginx 配置
│   └── migrate/                    #   数据迁移工具
├── docs/                           # 项目文档
├── monitoring/                     # 监控配置
│   └── grafana-dashboard.json      #   Grafana 仪表板
├── manage.sh                       # 服务管理脚本
├── start-local.sh                  # 混合部署启动脚本
├── pyproject.toml                  # Python 项目配置
├── .env                            # 本地后端环境变量（不提交）
└── .env.example                    # 环境变量模板
```

---

## �️ 部署方案

### 方案对比

| 方案 | 适用场景 | 复杂度 | 说明 |
|------|---------|--------|------|
| **manage.sh** | 本地开发 / 单机部署 | ⭐ | 最简单，直接运行 |
| **混合部署** | 本地开发 | ⭐⭐ | Docker 跑基础设施，本地跑应用 |
| **Docker 全容器** | 生产环境 | ⭐⭐⭐ | 一键部署所有服务 |

### 本地开发（推荐）

```bash
# 1. 启动基础设施（PostgreSQL + Redis）
# 方式 A：本地安装
brew install postgresql redis
brew services start postgresql
brew services start redis

# 方式 B：Docker 启动基础设施
./start-local.sh

# 2. 启动应用
./manage.sh install    # 首次运行
./manage.sh start      # 启动后端 + 前端
```

### 生产部署（Docker）

```bash
cd deployment

# 1. 配置环境变量
cp .env.example .env
vim .env

# 必须修改的配置：
# - POSTGRES_PASSWORD（数据库密码）
# - JWT_SECRET_KEY（JWT 密钥）
# - NEXTAUTH_SECRET（NextAuth 密钥）
# - ENCRYPTION_KEY（加密密钥）

# 2. 构建并启动
cd ..
./deployment/docker-start.sh

# 3. 查看日志
cd deployment
docker-compose logs -f backend
docker-compose logs -f frontend

# 4. 停止服务
docker-compose down
```

### 数据库迁移

```bash
# Alembic 迁移
./manage.sh db upgrade             # 升级到最新
./manage.sh db downgrade -1        # 回滚一步
./manage.sh db history             # 查看历史

# 从旧版 JSON 数据迁移到 PostgreSQL
cd deployment/migrate
cp .env.migration.example .env.migration
./quick_migrate.sh
```

---

## 🎨 前端交互动画

本项目采用温暖友好的动画风格，提升用户体验。

### 动画规范

| 类型 | 时长 | 缓动 | 说明 |
|------|------|------|------|
| 微交互（hover） | 150-200ms | ease-out | 按钮、卡片悬停 |
| 面板展开 | 200ms | ease-out | 下拉菜单、模态框 |
| 页面切换 | 300ms | ease-out | 路由切换 |

### 已实现动画

- **Button**: hover 发光效果 + active 按压缩放
- **Card**: hover 缩放 + 阴影 + 边框颜色变化
- **Modal**: 淡入缩放 + 关闭按钮旋转
- **Navigation**: 下拉菜单淡入 + 依次滑入子项
- **用户头像**: 点击弹跳 + hover 缩放
- **Toast**: 从右侧滑入淡入
- **Input**: 错误抖动动画
- **Skeleton**: 扫光波纹效果
- **LoadingDots**: 点跳动加载动画
- **Writer 页面**: 视图切换淡入过渡
- **页面进度条**: 路由切换顶部进度条

### 测试

访问 `/animations-test` 页面查看所有动画效果。

### 可访问性

所有动画尊重 `prefers-reduced-motion` 设置，自动禁用动画。

## 📡 API 端点

### 主要路由

| 路径 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /health/database` | 数据库健康检查 |
| `GET /health/full` | 完整健康检查 |
| `GET /docs` | Swagger API 文档 |
| `GET /metrics` | Prometheus 指标 |
| `POST /api/v1/auth/login` | 用户登录 |
| `POST /api/v1/auth/register` | 用户注册（仅官网） |
| `GET /api/v1/articles` | 文章列表 |
| `POST /api/v1/articles` | 创建文章 |
| `GET /api/v1/chat/sessions` | 聊天会话 |
| `GET /api/v1/hotspots` | 热点话题 |
| `GET /api/v1/news` | 新闻聚合 |
| `GET /api/v1/tweet-topics/history` | 推文选题历史 |
| `POST /api/v1/tweet-topics/generate` | 手动模式生成选题 |
| `POST /api/v1/tweet-topics/generate-intelligent` | 智能模式生成选题 |
| `GET /api/v1/tweet-topics/user-topics` | 获取用户主题 |
| `POST /api/v1/tweet-topics/user-topics` | 创建用户主题 |
| `DELETE /api/v1/tweet-topics/user-topics/{id}` | 删除用户主题 |
| `WS /api/v1/ws` | WebSocket 连接 |

> 完整 API 文档启动后访问：http://localhost:8000/docs
> 详细 API 文档请参考：[API 文档](docs/API.md)

---

## 🧪 测试

```bash
# 全部测试
./manage.sh test all

# 按模块测试
./manage.sh test core              # 核心模块（配置、缓存）
./manage.sh test models            # ORM 模型
./manage.sh test repos             # Repository 层
./manage.sh test services          # Service 层
./manage.sh test middleware        # 中间件（限流、审计）

# 直接使用 pytest
uv run pytest backend/tests/ -v --tb=short
```

---

## 📈 监控

启用 Prometheus 监控后，可通过以下方式查看：

- **Prometheus 指标**：http://localhost:8000/metrics
- **Grafana 仪表板**：导入 `monitoring/grafana-dashboard.json`

监控指标包括：
- API 请求速率、响应时间、错误率
- 数据库查询延迟、慢查询、连接池状态
- 缓存命中率
- 限流触发次数
- 配额使用情况

---

## � 文档导航

| 文档 | 说明 |
|------|------|
| [系统架构文档](docs/SYSTEM_ARCHITECTURE.md) | 完整技术架构（开发者必读） |
| [API 文档](docs/API.md) | 完整后端 API 接口文档 |
| [环境变量模板](.env.example) | 所有可配置项及说明 |
| [部署指南](deployment/README.md) | Docker 部署详细说明 |
| [数据库配置](docs/guides/database-config.md) | PostgreSQL 配置指南 |
| [认证系统](docs/guides/authentication-v2.md) | 多渠道认证详细说明 |
| [默认账号](docs/guides/default-account.md) | 初始管理员账号信息 |
| [UV 包管理](docs/guides/uv-quickstart.md) | uv 快速入门 |
| [文档中心](docs/README.md) | 完整文档索引 |

---

## � 版本历史

### v3.0 (2026-02) — 当前版本

- ✅ **前后端分离架构** — FastAPI + Next.js + Streamlit 三端分离
- ✅ **SQLAlchemy 2.0 异步 ORM** — DeclarativeBase + asyncpg
- ✅ **Redis 缓存 + 分布式限流** — ZSET 滑动窗口算法
- ✅ **Prometheus 性能监控** — 请求/DB/缓存全链路指标
- ✅ **Pydantic Settings 配置中心** — 环境变量外部化
- ✅ **Docker 容器化部署** — 一键生产部署
- ✅ **manage.sh 服务管理** — 统一的服务生命周期管理

### v2.2 (2025-11)

- ✅ **全网热点追踪** — 36Kr、百度、微博、抖音热搜聚合
- ✅ **创作工作流打通** — 热点话题一键生成文章

### v2.1 (2025-10)

- ✅ **多渠道认证** — Google OAuth2 + 微信扫码 + 本地账号

### v2.0 (2025-10)

- ✅ **双引擎搜索** — SearXNG + Serper API
- ✅ **图片防盗链** — 支持 9 大主流网站

---

##  贡献指南

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add some amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

### 开发规范

- 后端遵循 **Route → Service → Repository** 分层架构
- 新增 API 需同时添加测试
- 使用 `ruff` 格式化代码，行宽 120
- 提交信息使用中文或英文均可

## 📃 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

---
