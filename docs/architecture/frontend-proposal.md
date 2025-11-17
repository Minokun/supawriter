# SupaWriter 前端网站方案

## 方案概述

采用 **VitePress 官网 + Streamlit 社区** 混合架构，各司其职：

- **VitePress 部分**：产品介绍、文档、博客（静态内容）
- **Streamlit 部分**：用户社区、文章创作、互动功能（动态应用）

## 架构设计

```
┌─────────────────────────────────────┐
│   VitePress 官网 (supawriter.com)   │
│                                     │
│  - 首页：产品介绍                    │
│  - 功能特性                         │
│  - 使用文档                         │
│  - 开发博客                         │
│  - 精选文章展示                     │
│                                     │
│  [进入社区] 按钮                     │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│ Streamlit 社区 (app.supawriter.com) │
│                                     │
│  - 用户登录/注册                     │
│  - 文章创作工具                     │
│  - 文章列表/详情                     │
│  - 用户主页                         │
│  - 评论互动                         │
│                                     │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│     PostgreSQL 数据库               │
│                                     │
│  - 用户数据                         │
│  - 文章内容                         │
│  - 社区互动                         │
└─────────────────────────────────────┘
```

## VitePress 官网实施方案

### 1. 项目结构

```
supawriter-website/
├── docs/
│   ├── .vitepress/
│   │   ├── config.ts          # VitePress 配置
│   │   └── theme/             # 自定义主题
│   ├── index.md               # 首页
│   ├── guide/                 # 使用指南
│   │   ├── getting-started.md
│   │   ├── features.md
│   │   └── api.md
│   ├── blog/                  # 博客文章
│   │   └── posts/
│   └── community/             # 社区精选
│       └── featured.md
├── package.json
└── README.md
```

### 2. 首页设计

**Hero Section**：
- 产品标语："AI 驱动的智能写作平台"
- 核心卖点：快速生成、多引擎搜索、智能配图
- CTA 按钮：「开始创作」→ 跳转到 Streamlit 社区

**Feature Section**：
- 卡片展示 6 大核心功能
- 配图 + 简短说明

**社区入口**：
- 展示最新精选文章（从数据库读取）
- 「查看更多」→ Streamlit 社区

### 3. 数据接口设计

VitePress 需要通过 API 获取动态数据：

```typescript
// docs/.vitepress/data/articles.data.ts
export default {
  async load() {
    const response = await fetch('https://app.supawriter.com/api/featured-articles')
    return await response.json()
  }
}
```

Streamlit 后端提供 API：
```python
# page/api.py
@app.route('/api/featured-articles')
def get_featured_articles():
    """获取精选文章"""
    articles = db.query("""
        SELECT id, title, summary, author, created_at
        FROM articles
        WHERE is_featured = true
        ORDER BY created_at DESC
        LIMIT 6
    """)
    return jsonify(articles)
```

### 4. 技术栈

- **VitePress**: 静态站点生成
- **Vue 3**: 自定义组件
- **TailwindCSS**: 样式框架
- **GitHub Actions**: 自动部署到 Netlify/Vercel

### 5. SEO 优化

VitePress 自带优秀的 SEO 支持：
```ts
// config.ts
export default {
  head: [
    ['meta', { name: 'keywords', content: 'AI写作,智能创作,自动生成文章' }],
    ['meta', { property: 'og:title', content: 'SupaWriter - AI智能写作平台' }],
    ['meta', { property: 'og:description', content: '...' }]
  ]
}
```

## Streamlit 社区功能增强

### 1. 新增功能模块

**文章广场** (`page/article_plaza.py`)：
- 所有用户公开文章列表
- 支持搜索、筛选、排序
- 文章预览卡片

**文章详情页** (`page/article_detail.py`)：
- 完整文章展示
- 作者信息
- 评论区
- 点赞/收藏功能

**用户主页** (`page/user_profile.py`)：
- 个人文章列表
- 创作统计
- 关注/粉丝

### 2. 数据库表设计

```sql
-- 文章表（已有，需添加字段）
ALTER TABLE articles ADD COLUMN is_public BOOLEAN DEFAULT false;
ALTER TABLE articles ADD COLUMN is_featured BOOLEAN DEFAULT false;
ALTER TABLE articles ADD COLUMN view_count INTEGER DEFAULT 0;
ALTER TABLE articles ADD COLUMN like_count INTEGER DEFAULT 0;

-- 评论表（新增）
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id),
    user_id INTEGER REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 点赞表（新增）
CREATE TABLE likes (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id),
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(article_id, user_id)
);
```

### 3. API 路由规划

```python
# utils/api_routes.py
routes = {
    '/api/articles': 'get_articles',           # 文章列表
    '/api/articles/<id>': 'get_article',       # 文章详情
    '/api/featured-articles': 'get_featured',  # 精选文章
    '/api/comments': 'post_comment',           # 发表评论
    '/api/like': 'toggle_like',                # 点赞/取消
}
```

## 部署方案

### VitePress 官网
- **域名**: `supawriter.com` 或 `www.supawriter.com`
- **托管**: Vercel / Netlify（自动 CI/CD）
- **CDN**: 自动启用全球 CDN 加速

### Streamlit 社区
- **域名**: `app.supawriter.com`
- **服务器**: 现有服务器 (122.51.24.120) 或 Streamlit Cloud
- **Nginx**: 配置反向代理和 SSL

### 域名配置
```
supawriter.com          → VitePress 官网
app.supawriter.com      → Streamlit 社区
api.supawriter.com      → API 接口（可选）
```

## 开发时间线

### Phase 1: VitePress 官网（2周）
- [ ] 搭建 VitePress 项目
- [ ] 设计首页和导航
- [ ] 编写产品文档
- [ ] 集成数据 API
- [ ] 部署到 Vercel

### Phase 2: Streamlit 社区功能（3周）
- [ ] 开发文章广场页面
- [ ] 实现文章详情页
- [ ] 添加评论系统
- [ ] 实现点赞/收藏
- [ ] API 接口开发

### Phase 3: 数据打通（1周）
- [ ] VitePress 获取精选文章
- [ ] 统一用户认证
- [ ] 数据同步机制
- [ ] 性能优化

### Phase 4: 上线（1周）
- [ ] 域名配置
- [ ] SSL 证书
- [ ] CDN 加速
- [ ] 监控和日志

## 成本估算

| 项目 | 费用 | 备注 |
|------|------|------|
| 域名 | ¥60/年 | .com 域名 |
| Vercel 托管 | 免费 | VitePress 官网 |
| 服务器 | 现有 | Streamlit 社区 |
| CDN | 免费 | Vercel 自带 |
| SSL 证书 | 免费 | Let's Encrypt |
| **总计** | **¥60/年** | 仅域名费用 |

## 方案优势

✅ **SEO 友好**：VitePress 静态站点，搜索引擎收录好  
✅ **性能优秀**：官网极速加载，社区功能齐全  
✅ **技术隔离**：前后端分离，互不影响  
✅ **数据共享**：精选内容可在官网展示  
✅ **低成本**：利用免费服务，只需域名费用  
✅ **易维护**：VitePress 文档式开发，Streamlit 继续使用  

## 替代方案对比

### 方案 B：纯 Streamlit（不推荐）
❌ SEO 较差（单页应用）  
❌ 官网和社区混在一起，导航混乱  
❌ 性能一般（Python 后端）  
✅ 技术栈统一（但不是优势）

### 方案 C：Next.js 全栈（复杂）
✅ 功能最全面  
❌ 需要完全重写现有功能  
❌ 开发周期长（2-3个月）  
❌ 技术栈转换成本高（Python → Node.js）

### 方案 D：纯 VitePress（局限性大）
✅ 官网效果最好  
❌ 无法实现社区功能  
❌ 需要额外开发后端  

## 结论

**推荐方案 A（VitePress + Streamlit）**，原因：
1. 充分利用现有技术栈和功能
2. VitePress 专注官网展示（速度快、SEO 好）
3. Streamlit 继续做社区（已有用户系统）
4. 开发周期短，成本低
5. 可扩展性好，未来可独立演进

## 下一步行动

如果采纳此方案，建议按以下顺序推进：

1. **创建 VitePress 项目**：搭建官网基础框架
2. **设计首页**：参考优秀案例（Vue.js、Astro 官网）
3. **开发社区功能**：在 Streamlit 中添加文章广场
4. **数据接口**：实现 API 让 VitePress 获取数据
5. **部署上线**：配置域名和 CDN

需要我开始创建 VitePress 项目结构吗？
