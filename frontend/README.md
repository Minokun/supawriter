# 超能写手前端 - 温暖色调版本

基于 React + Next.js + Tailwind CSS 的现代化前端应用。

## 技术栈

- **框架**: Next.js 14 (App Router)
- **UI**: React 18 + TypeScript
- **样式**: Tailwind CSS
- **图标**: Lucide React
- **HTTP客户端**: Axios
- **工具**: clsx

## 设计系统

### 色彩方案（温暖色调）
- 主色: `#DC2626` (红色)
- 辅助色: `#F87171` (浅红)
- CTA按钮: `#CA8A04` (金色)
- 背景: `#FEF2F2` (浅粉)
- 文字: `#450A0A` (深红棕)

### 字体
- 标题: Fredoka (Google Fonts)
- 正文: Nunito (Google Fonts)

## 快速开始

### 安装依赖

```bash
npm install
# 或
yarn install
# 或
pnpm install
```

### 配置环境变量

复制 `.env.local.example` 为 `.env.local` 并配置：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=超能写手
```

### 开发模式

```bash
npm run dev
```

访问 [http://localhost:3000](http://localhost:3000)

### 生产构建

```bash
npm run build
npm run start
```

## 项目结构

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router 页面
│   │   ├── workspace/          # 创作空间
│   │   ├── inspiration/        # 灵感发现
│   │   ├── writer/             # 超能写手
│   │   ├── ai-assistant/       # AI助手
│   │   ├── rewrite/            # 文章再创作
│   │   ├── knowledge/          # 知识库
│   │   ├── profile/            # 个人信息
│   │   ├── layout.tsx          # 根布局
│   │   └── globals.css         # 全局样式
│   ├── components/
│   │   ├── ui/                 # 通用UI组件
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── TextArea.tsx
│   │   │   ├── Select.tsx
│   │   │   └── Badge.tsx
│   │   └── layout/             # 布局组件
│   │       ├── Navigation.tsx
│   │       └── MainLayout.tsx
│   └── lib/
│       └── api.ts              # API集成层
├── public/                     # 静态资源
├── tailwind.config.ts          # Tailwind配置
├── tsconfig.json               # TypeScript配置
└── package.json

```

## 页面说明

### 1. 创作空间 (`/workspace`)
- 展示3个主要功能卡片
- 灵感发现预览区
- 快速导航到各个功能

### 2. 灵感发现 (`/inspiration`)
- 全网热点列表
- 多源筛选（36Kr、百度、微博、抖音）
- 一键创作功能

### 3. 超能写手 (`/writer`)
- 文章类型选择
- 主题输入
- 特殊要求配置
- 一键生成文章

### 4. AI助手 (`/ai-assistant`)
- 智能对话界面
- 实时消息展示
- 上下文理解

### 5. 文章再创作 (`/rewrite`)
- URL输入
- 操作类型选择（改写/扩写/缩写）
- 快速处理

### 6. 知识库 (`/knowledge`)
- 文档上传管理
- 搜索功能
- 文档列表展示

### 7. 个人信息 (`/profile`)
- 用户资料管理
- 历史记录查看
- 系统设置

## API集成

所有API调用都通过 `src/lib/api.ts` 进行，包括：

- 文章生成
- 文章改写
- 热点获取
- 知识库管理
- 历史记录

## 开发规范

### 组件开发
- 使用 TypeScript 进行类型定义
- 遵循 React Hooks 最佳实践
- 组件应保持单一职责

### 样式规范
- 使用 Tailwind CSS 工具类
- 遵循设计系统的颜色和间距规范
- 避免内联样式

### 代码风格
- 使用 ESLint 进行代码检查
- 遵循 Airbnb JavaScript Style Guide
- 提交前运行 `npm run lint`

## 部署

### Vercel (推荐)

```bash
vercel
```

### Docker

```bash
docker build -t supawriter-frontend .
docker run -p 3000:3000 supawriter-frontend
```

## 后端对接

确保后端API运行在配置的 `NEXT_PUBLIC_API_URL` 地址上。

前端会自动处理：
- 请求拦截（添加认证token）
- 响应拦截（处理错误）
- 超时处理

## License

MIT
