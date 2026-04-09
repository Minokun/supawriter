# Streamlit 页面功能映射 - 前端实现计划

## 📊 页面功能梳理

### 1. 超能AI助手 (home.py) → `/ai-assistant`

**核心功能**：
- ✅ 多轮对话聊天界面
- ✅ 聊天历史管理（新建、加载、删除）
- ✅ 自动生成对话标题（取首条消息前10字）
- ✅ 对话导出为Markdown
- ✅ 支持thinking过程显示
- ✅ 模型选择（从配置读取）
- ✅ 聊天记录持久化

**实现要点**：
- 使用WebSocket或轮询实现流式响应
- 左侧边栏显示历史会话列表
- 支持会话切换和管理
- 消息气泡UI（用户/AI区分）

**API需求**：
```
POST /api/chat/send - 发送消息
GET /api/chat/sessions - 获取会话列表
POST /api/chat/sessions - 创建新会话
GET /api/chat/sessions/:id - 加载会话
DELETE /api/chat/sessions/:id - 删除会话
PUT /api/chat/sessions/:id/title - 更新标题
```

---

### 2. 超能写手 (auto_write.py) → `/writer`

**核心功能**：
- ✅ 文章主题输入
- ✅ 文章类型选择
- ✅ 特殊要求配置
- ⚡ 任务队列管理（3个标签页）
  - 队列管理：待处理/执行中/已完成
  - 文章撰写：主要创作界面
  - 知识库：文档上传和管理
- ⚡ 实时进度显示（爬虫、大纲、章节）
- ⚡ Markdown编辑器（编辑/预览/公众号预览）
- ⚡ 图片搜索和嵌入
- ⚡ 相似内容检索
- ⚡ 文章保存和下载

**实现要点**：
- 三标签页布局：队列、撰写、知识库
- 实时进度条和状态更新
- 支持后台任务执行
- Markdown编辑器集成（Monaco Editor或类似）
- 公众号预览功能

**API需求**：
```
POST /api/articles/generate - 生成文章
GET /api/articles/queue - 获取队列任务
POST /api/articles/queue - 添加到队列
PUT /api/articles/queue/:id - 更新任务状态
DELETE /api/articles/queue/:id - 删除任务
GET /api/articles/progress/:id - 获取生成进度
POST /api/knowledge/upload - 上传文档
GET /api/knowledge/list - 文档列表
DELETE /api/knowledge/:id - 删除文档
```

---

### 3. 全网热点 (hotspots.py) → `/inspiration`

**核心功能**：
- ✅ 多源热点聚合（澎湃、36Kr、百度、微博、抖音）
- ✅ 标签筛选切换
- ✅ 热度排名显示
- ✅ 一键创作按钮（加入队列）
- ⚡ 自动刷新（5分钟）
- ⚡ 数据缓存（5分钟TTL）

**实现要点**：
- Pills标签切换UI
- 排名徽章（第1名特殊样式）
- 热度分数显示
- 点击"一键创作"跳转到超能写手并预填主题

**API需求**：
```
GET /api/hotspots?source=all|36kr|baidu|weibo|douyin - 获取热点
POST /api/articles/queue - 添加热点到队列
```

---

### 4. 新闻资讯 (news.py) → `/news`

**核心功能**：
- ✅ 新闻源选择（Pills UI）
- ✅ 新闻列表展示
- ✅ 时间显示
- ✅ 外链跳转

**实现要点**：
- 科技感渐变背景
- 新闻卡片布局
- 来源标签显示

**API需求**：
```
GET /api/news?source=source_name - 获取新闻列表
```

---

### 5. 推文选题 (tweet_topics.py) → `/tweet-topics`

**核心功能**：
- ✅ 新闻源选择（Pills UI）
- ✅ 生成推文选题（角度、受众、钩子、风格）
- ✅ 选题卡片展示
- ✅ 生成文章按钮（跳转到超能写手）
- ⚡ 历史记录查看
- ⚡ 删除历史记录

**实现要点**：
- 渐变卡片UI
- 元数据徽章（角度、受众等）
- 点击"生成文章"跳转并预填主题

**API需求**：
```
POST /api/tweet-topics/generate - 生成选题
GET /api/tweet-topics/history - 获取历史
DELETE /api/tweet-topics/:id - 删除记录
```

---

### 6. 文章再创作 (article_recreation.py) → `/rewrite`

**核心功能**：
- ✅ URL输入
- ✅ 操作类型选择（改写、扩写、缩写、HTML生成）
- ⚡ 网页内容抓取
- ⚡ AI处理和转换
- ⚡ 结果预览和下载

**实现要点**：
- URL验证
- 操作类型单选按钮
- 加载状态显示
- 结果展示（Markdown/HTML）

**API需求**：
```
POST /api/articles/rewrite - 文章再创作
  body: { url, operation: 'rewrite'|'expand'|'summarize'|'html' }
```

---

### 7. 历史记录 (history.py) → `/history`

**核心功能**：
- ✅ 历史记录列表
- ✅ 筛选功能（类型、日期）
- ✅ Markdown预览
- ✅ 公众号预览
- ✅ HTML预览
- ✅ 下载功能（Markdown/HTML）
- ✅ 删除记录
- ⚡ 编辑功能
- ⚡ 截图功能

**实现要点**：
- 4列按钮布局：Markdown预览、公众号预览、下载、删除
- 弹窗预览
- 一键复制功能
- 筛选器UI

**API需求**：
```
GET /api/articles/history - 获取历史记录
GET /api/articles/:id - 获取单篇文章
PUT /api/articles/:id - 更新文章
DELETE /api/articles/:id - 删除文章
POST /api/articles/:id/screenshot - 生成截图
```

---

### 8. 系统设置 (system_settings.py) → `/settings`

**核心功能**：
- ✅ 全局模型设置（Provider、Model）
- ✅ 嵌入模型配置
- ✅ API密钥管理
- ⚡ 爬虫数量设置
- ⚡ 图片嵌入方法
- ⚡ 其他全局配置

**实现要点**：
- 分组表单布局
- 下拉选择器
- 密钥输入（密码类型）
- 实时保存

**API需求**：
```
GET /api/settings - 获取设置
PUT /api/settings - 更新设置
POST /api/settings/secrets - 保存密钥
```

---

### 9. 社区管理 (community_management.py) → `/community`

**核心功能**：
- ✅ 文章同步到数据库
- ✅ 同步状态检查
- ✅ 已发布文章管理
- ✅ 文章查询和删除
- ⚡ 批量操作

**实现要点**：
- 两标签页：一键发布、文章管理
- 同步状态显示
- 数据表格展示
- 批量选择和操作

**API需求**：
```
POST /api/community/sync - 同步文章
GET /api/community/check - 检查同步状态
GET /api/community/articles - 获取已发布文章
DELETE /api/community/articles/:id - 删除文章
```

---

### 10. 知识库 (已在超能写手中) → `/writer` (知识库标签)

**核心功能**：
- ✅ 文档上传
- ✅ 文档列表
- ✅ 文档删除
- ✅ 搜索功能

**实现要点**：
- 拖拽上传
- 文件类型图标
- 文件大小和日期显示

---

## 🗺️ 页面路由映射

| Streamlit页面 | 前端路由 | 状态 |
|--------------|---------|------|
| home.py | `/ai-assistant` | ⏳ 待实现 |
| auto_write.py | `/writer` | ✅ 部分完成 |
| hotspots.py | `/inspiration` | ✅ 已完成 |
| news.py | `/news` | ⏳ 待实现 |
| tweet_topics.py | `/tweet-topics` | ⏳ 待实现 |
| article_recreation.py | `/rewrite` | ⏳ 待实现 |
| history.py | `/history` | ⏳ 待实现 |
| system_settings.py | `/settings` | ⏳ 待实现 |
| community_management.py | `/community` | ⏳ 待实现 |
| gpts.py | 暂不实现 | - |
| ddgs_search.py | 暂不实现 | - |
| asr.py/tts.py | 暂不实现 | - |

---

## 🔄 页面跳转流程

### 1. 热点 → 超能写手
```
用户在 /inspiration 点击"一键创作"
→ 跳转到 /writer
→ 预填主题到输入框
→ 自动添加到队列
```

### 2. 推文选题 → 超能写手
```
用户在 /tweet-topics 点击"生成文章"
→ 跳转到 /writer
→ 预填主题和风格
→ 自动添加到队列
```

### 3. 新闻 → 超能写手
```
用户在 /news 点击新闻
→ 可选择"基于此新闻创作"
→ 跳转到 /writer
→ 预填新闻标题
```

---

## 🎯 实现优先级

### P0 - 核心功能（本周完成）
1. ✅ AI助手聊天页面
2. ✅ 超能写手完整功能（队列+撰写+知识库）
3. ✅ 历史记录页面

### P1 - 重要功能（下周完成）
4. ⏳ 文章再创作
5. ⏳ 推文选题
6. ⏳ 新闻资讯

### P2 - 辅助功能（后续完成）
7. ⏳ 系统设置
8. ⏳ 社区管理

---

## 📝 技术实现要点

### 状态管理
- 使用 Zustand 或 Context API 管理全局状态
- 队列状态、用户信息、配置等

### 实时更新
- WebSocket 连接用于流式响应
- 轮询用于任务进度更新

### 文件上传
- 使用 react-dropzone
- 支持拖拽上传

### Markdown编辑
- Monaco Editor 或 react-markdown-editor-lite
- 实时预览

### 公众号预览
- iframe 嵌入HTML
- 一键复制功能

---

## 🧪 测试计划

### 功能测试
- [ ] 所有页面路由正常访问
- [ ] 页面间跳转和参数传递
- [ ] 表单提交和验证
- [ ] API调用和错误处理

### 集成测试
- [ ] 热点→超能写手流程
- [ ] 推文选题→超能写手流程
- [ ] 文章生成→历史记录流程
- [ ] 队列任务执行流程

### UI测试
- [ ] 响应式布局
- [ ] 加载状态显示
- [ ] 错误提示
- [ ] 成功反馈

---

*文档创建时间: 2026-01-28*
*最后更新: 2026-01-28*
