# 前端部署指南

## 项目概述

**超能写手前端** - 基于温暖色调UI设计的现代化AI写作平台前端应用。

- **技术栈**: Next.js 14 + React 18 + TypeScript + Tailwind CSS
- **设计系统**: 温暖色调（主色 #DC2626）
- **字体**: Fredoka (标题) + Nunito (正文)

## 本地开发

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置环境变量

```bash
cp .env.local.example .env.local
```

编辑 `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=超能写手
```

### 3. 启动开发服务器

```bash
npm run dev
```

访问: http://localhost:3000

## 生产部署

### Vercel 部署（推荐）

1. 推送代码到 GitHub
2. 在 Vercel 导入项目
3. 配置环境变量
4. 自动部署

### Docker 部署

```bash
# 构建镜像
docker build -t supawriter-frontend .

# 运行容器
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=https://api.yourdomain.com \
  supawriter-frontend
```

### 静态导出

```bash
npm run build
npm run export
```

## 后端对接

### API 配置

所有 API 调用通过 `src/lib/api.ts` 进行，需要后端提供以下接口：

#### 文章相关
- `POST /api/articles/generate` - 生成文章
- `POST /api/articles/rewrite` - 改写文章
- `GET /api/articles/history` - 获取历史记录

#### 热点相关
- `GET /api/hotspots` - 获取热点列表
  - 参数: `source` (可选)

#### 知识库相关
- `POST /api/knowledge/upload` - 上传文档
- `GET /api/knowledge/list` - 获取文档列表
- `DELETE /api/knowledge/:id` - 删除文档

### 认证

前端会自动在请求头中添加 `Authorization: Bearer {token}`

Token 存储在 `localStorage` 中，key 为 `token`

## 项目结构

```
frontend/
├── src/
│   ├── app/                    # 页面路由
│   │   ├── workspace/          # 创作空间
│   │   ├── inspiration/        # 灵感发现
│   │   ├── writer/             # 超能写手
│   │   └── ...
│   ├── components/
│   │   ├── ui/                 # UI组件
│   │   └── layout/             # 布局组件
│   └── lib/
│       └── api.ts              # API集成
├── public/                     # 静态资源
└── tailwind.config.ts          # Tailwind配置
```

## 已实现的页面

✅ 创作空间 (`/workspace`)
✅ 灵感发现 (`/inspiration`)
✅ 超能写手 (`/writer`)
⏳ AI助手 (`/ai-assistant`) - 待实现
⏳ 文章再创作 (`/rewrite`) - 待实现
⏳ 知识库 (`/knowledge`) - 待实现
⏳ 个人信息 (`/profile`) - 待实现

## 性能优化

- ✅ 使用 Next.js App Router 实现代码分割
- ✅ 图片优化（Next.js Image组件）
- ✅ 字体优化（Google Fonts预加载）
- ✅ CSS优化（Tailwind CSS JIT）

## 浏览器支持

- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)

## 故障排查

### 依赖安装失败

```bash
rm -rf node_modules package-lock.json
npm install
```

### 端口被占用

```bash
# 修改端口
PORT=3001 npm run dev
```

### API 连接失败

检查 `.env.local` 中的 `NEXT_PUBLIC_API_URL` 配置

## 下一步开发

1. 完成剩余页面组件（AI助手、文章再创作等）
2. 添加状态管理（Zustand 或 Redux）
3. 实现实时通信（WebSocket）
4. 添加单元测试和E2E测试
5. 优化移动端适配
6. 添加国际化支持

## 联系方式

如有问题，请查看项目 README.md 或提交 Issue。
