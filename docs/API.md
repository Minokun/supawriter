# SupaWriter API 文档

> SupaWriter 后端 API 完整接口文档

**基础 URL**: `http://localhost:8000` (开发环境)

**API 版本**: v1

**认证方式**: JWT Bearer Token / OAuth2

---

## 目录

- [认证](#认证)
- [健康检查](#健康检查)
- [用户认证](#用户认证)
- [文章管理](#文章管理)
- [推文选题](#推文选题)
- [AI 助手](#ai-助手)
- [热点追踪](#热点追踪)
- [新闻聚合](#新闻聚合)
- [WebSocket](#websocket)
- [错误码](#错误码)

---

## 认证

### 获取 Token

大部分 API 需要认证。使用以下方式获取 Token：

#### 1. 邮箱密码登录

```http
POST /api/v1/auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**响应**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "user"
  }
}
```

#### 2. Google OAuth2

```http
POST /api/v1/auth/google HTTP/1.1
Content-Type: application/json

{
  "id_token": "google_id_token_from_frontend"
}
```

### 使用 Token

在请求头中添加 Authorization：

```http
GET /api/v1/articles HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 健康检查

### 基础健康检查

```http
GET /health HTTP/1.1
```

**响应**:

```json
{
  "status": "healthy",
  "service": "SupaWriter API",
  "version": "2.0.0",
  "timestamp": "2026-02-10T07:39:48.479194"
}
```

### 数据库健康检查

```http
GET /health/database HTTP/1.1
```

**响应**:

```json
{
  "status": "healthy",
  "database": {
    "status": "connected",
    "pool_size": 5,
    "max_overflow": 10,
    "checked_out": 0,
    "available": 5
  }
}
```

### 完整健康检查

```http
GET /health/full HTTP/1.1
```

**响应**:

```json
{
  "status": "healthy",
  "database": { "status": "connected" },
  "redis": { "status": "connected" },
  "cache": { "status": "enabled" }
}
```

---

## 用户认证

### 用户登录

```http
POST /api/v1/auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}
```

### 用户注册

```http
POST /api/v1/auth/register HTTP/1.1
Content-Type: application/json

{
  "email": "newuser@example.com",
  "username": "newuser",
  "password": "password",
  "display_name": "Display Name"
}
```

### Google 登录

```http
POST /api/v1/auth/google HTTP/1.1
Content-Type: application/json

{
  "id_token": "google_jwt_token"
}
```

### 微信登录

```http
POST /api/v1/auth/wechat HTTP/1.1
Content-Type: application/json

{
  "code": "wx_auth_code"
}
```

### 获取当前用户信息

```http
GET /api/v1/auth/me HTTP/1.1
Authorization: Bearer <token>
```

### 登出

```http
POST /api/v1/auth/logout HTTP/1.1
Authorization: Bearer <token>
```

---

## 文章管理

### 获取文章列表

```http
GET /api/v1/articles?page=1&limit=20 HTTP/1.1
Authorization: Bearer <token>
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码 |
| limit | integer | 20 | 每页数量 |
| status | string | - | 状态筛选 (draft/published/archived) |

**响应**:

```json
{
  "items": [
    {
      "id": 1,
      "title": "文章标题",
      "content": "文章内容",
      "status": "published",
      "created_at": "2026-02-10T00:00:00Z",
      "updated_at": "2026-02-10T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 20
}
```

### 创建文章

```http
POST /api/v1/articles HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "文章标题",
  "content": "文章内容",
  "status": "draft"
}
```

### 获取文章详情

```http
GET /api/v1/articles/{article_id} HTTP/1.1
Authorization: Bearer <token>
```

### 更新文章

```http
PUT /api/v1/articles/{article_id} HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "更新后的标题",
  "content": "更新后的内容"
}
```

### 删除文章

```http
DELETE /api/v1/articles/{article_id} HTTP/1.1
Authorization: Bearer <token>
```

---

## 推文选题

推文选题功能提供两种模式：
- **智能模式**: AI 从多个新闻源筛选新闻并生成选题
- **手动模式**: 选择单一新闻源生成选题

### 手动模式生成选题

```http
POST /api/v1/tweet-topics/generate HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "news_source": "澎湃科技",
  "news_count": 15,
  "topic_count": 8
}
```

**请求参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| news_source | string | 澎湃科技 | 新闻源 (澎湃科技/SOTA开源项目/实时新闻/新浪直播) |
| news_count | integer | 15 | 获取新闻数量 (5-30) |
| topic_count | integer | 8 | 生成选题数量 (3-15) |

**响应**:

```json
{
  "record": {
    "id": 1,
    "mode": "manual",
    "news_source": "澎湃科技",
    "news_count": 15,
    "topics_data": {
      "topics": [
        {
          "title": "选题标题",
          "subtitle": "副标题",
          "angle": "切入角度",
          "target_audience": "目标受众",
          "seo_keywords": ["关键词1", "关键词2"],
          "hook": "开篇钩子",
          "value_proposition": "价值主张",
          "content_outline": [...],
          "interaction_point": "互动引导",
          "share_trigger": "分享触发",
          "heat_score": 8,
          "difficulty": "中等"
        }
      ],
      "summary": "选题总结",
      "hot_keywords": ["热词1", "热词2"]
    },
    "timestamp": "2026-02-10T00:00:00Z"
  }
}
```

### 智能模式生成选题

```http
POST /api/v1/tweet-topics/generate-intelligent HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "topic_id": 1,
  "custom_topic": "AI与人工智能",
  "save_topic": true,
  "topic_description": "关注AI技术发展趋势",
  "topic_count": 10
}
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| topic_id | integer | ❌ | 已保存主题ID (与custom_topic二选一) |
| custom_topic | string | ❌ | 自定义主题名称 |
| save_topic | boolean | ❌ | 是否保存自定义主题 |
| topic_description | string | ❌ | 主题描述 |
| topic_count | integer | ❌ | 选题数量 (3-10) |

**响应**:

```json
{
  "record_id": 1,
  "mode": "intelligent",
  "topic_name": "AI与人工智能",
  "news_source": "all",
  "news_count": 60,
  "topics_data": {
    "filtered_news": [
      {
        "title": "相关新闻标题",
        "relevance_score": 9,
        "reason": "匹配原因"
      }
    ],
    "topics": [...],
    "summary": "选题总结",
    "hot_keywords": ["AI", "人工智能"]
  },
  "model_type": "deepseek",
  "model_name": "deepseek-chat"
}
```

### 获取选题历史

```http
GET /api/v1/tweet-topics/history HTTP/1.1
Authorization: Bearer <token>
```

**响应**:

```json
[
  {
    "id": 1,
    "mode": "intelligent",
    "topic_name": "AI与人工智能",
    "news_source": "all",
    "news_count": 60,
    "topics_data": {...},
    "timestamp": "2026-02-10T00:00:00Z"
  }
]
```

### 删除历史记录

```http
DELETE /api/v1/tweet-topics/{record_id} HTTP/1.1
Authorization: Bearer <token>
```

### 获取用户主题列表

```http
GET /api/v1/tweet-topics/user-topics HTTP/1.1
Authorization: Bearer <token>
```

**响应**:

```json
{
  "topics": [
    {
      "id": 1,
      "user_id": 1,
      "topic_name": "AI与人工智能",
      "description": "关注AI技术发展趋势",
      "created_at": "2026-02-10T00:00:00Z",
      "updated_at": "2026-02-10T00:00:00Z"
    }
  ]
}
```

### 创建用户主题

```http
POST /api/v1/tweet-topics/user-topics HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "topic_name": "新能源技术",
  "description": "关注新能源、储能、电动车等"
}
```

### 删除用户主题

```http
DELETE /api/v1/tweet-topics/user-topics/{topic_id} HTTP/1.1
Authorization: Bearer <token>
```

---

## AI 助手

### 获取聊天会话列表

```http
GET /api/v1/chat/sessions HTTP/1.1
Authorization: Bearer <token>
```

### 创建聊天会话

```http
POST /api/v1/chat/sessions HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "新对话"
}
```

### 发送消息

```http
POST /api/v1/chat/sessions/{session_id}/messages HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "用户消息内容",
  "model_type": "deepseek",
  "model_name": "deepseek-chat"
}
```

### 获取会话消息历史

```http
GET /api/v1/chat/sessions/{session_id}/messages HTTP/1.1
Authorization: Bearer <token>
```

---

## 热点追踪

### 获取热点话题

```http
GET /api/v1/hotspots?source=36kr&limit=20 HTTP/1.1
Authorization: Bearer <token>
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| source | string | 36kr | 热点来源 (36kr/baidu/weibo/douyin) |
| limit | integer | 20 | 返回数量 |

**响应**:

```json
{
  "source": "36kr",
  "hotspots": [
    {
      "title": "热点标题",
      "url": "链接地址",
      "hot_value": 1000000,
      "rank": 1
    }
  ],
  "updated_at": "2026-02-10T00:00:00Z"
}
```

---

## 新闻聚合

### 获取新闻列表

```http
GET /api/v1/news?source=thepaper&limit=20 HTTP/1.1
Authorization: Bearer <token>
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| source | string | thepaper | 新闻源 |
| limit | integer | 20 | 返回数量 |

**响应**:

```json
{
  "source": "澎湃科技",
  "news": [
    {
      "title": "新闻标题",
      "summary": "新闻摘要",
      "url": "链接地址",
      "published_at": "2026-02-10T00:00:00Z"
    }
  ]
}
```

---

## WebSocket

### 连接

```
ws://localhost:8000/api/v1/ws?token=<jwt_token>
```

### 消息格式

**客户端发送**:

```json
{
  "type": "message",
  "session_id": "session_id",
  "content": "消息内容"
}
```

**服务端推送**:

```json
{
  "type": "response",
  "content": "AI 回复内容",
  "is_complete": true
}
```

---

## 错误码

| HTTP 状态码 | 错误类型 | 说明 |
|------------|---------|------|
| 200 | - | 成功 |
| 201 | - | 创建成功 |
| 400 | ValidationError | 请求参数验证失败 |
| 401 | Unauthorized | 未认证或 Token 无效 |
| 403 | Forbidden | 无权限访问 |
| 404 | NotFound | 资源不存在 |
| 422 | ValidationError | 请求体格式错误 |
| 429 | RateLimitExceeded | 请求过于频繁 |
| 500 | InternalServerError | 服务器内部错误 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

或

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "详细错误信息",
    "details": {}
  }
}
```

---

## 限流规则

| 端点类型 | 限制 | 时间窗口 |
|---------|------|---------|
| 认证相关 | 10 次 | 1 分钟 |
| 内容生成 | 5 次 | 1 分钟 |
| 查询接口 | 60 次 | 1 分钟 |
| WebSocket | 10 连接 | 1 分钟 |

超过限制返回 `429 RateLimitExceeded`。

---

## 数据模型

### UserTopic

```typescript
{
  id: number;
  user_id: number;
  topic_name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}
```

### TopicDetail

```typescript
{
  title: string;
  subtitle?: string;
  angle?: string;
  target_audience?: string;
  seo_keywords?: string[];
  tags?: string[];
  content_outline?: Array<{ h1?: string; h2?: string[] } | string>;
  hook?: string;
  value_proposition?: string;
  interaction_point?: string;
  share_trigger?: string;
  estimated_words?: string;
  difficulty?: string;
  heat_score?: number;
  source_news?: string;
}
```

### TopicsData

```typescript
{
  topics: TopicDetail[];
  summary?: string;
  hot_keywords?: string[];
  filtered_news?: FilteredNews[];
}
```

---

## 版本历史

### v1.0 (2026-02-10)

- ✅ 推文选题功能上线
- ✅ 智能模式 + 手动模式
- ✅ 用户主题管理
- ✅ 多源新闻聚合

---

## 在线文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json
