# 认证系统优化方案

## 当前架构分析

### 现有功能
1. **Google OAuth 登录**：通过 NextAuth 实现
2. **后端 JWT Token**：用于 API 认证
3. **数据库结构**：
   - `users` 表：存储用户基本信息
   - `oauth_accounts` 表：存储 OAuth 账号绑定关系

### 存在的问题
1. 前端混用了 NextAuth token 和后端 JWT token
2. 只支持 Google 登录，缺少其他登录方式
3. 用户无法在个人设置中添加邮箱密码
4. 认证流程不够统一

## 优化目标

### 1. 统一认证流程
- 所有登录方式最终都获取后端 JWT token
- 前端统一使用后端 JWT token 进行 API 调用
- NextAuth 仅作为 OAuth 登录的中间层

### 2. 支持多种登录方式
- ✅ Google OAuth（已实现）
- 🔄 邮箱密码登录（待实现）
- 🔄 微信 OAuth 登录（待实现）
- 🔄 用户名密码登录（已有数据库支持）

### 3. 账号绑定功能
- 用户可以在个人设置中绑定邮箱密码
- 已有 OAuth 账号的用户可以添加邮箱密码作为备用登录方式
- 支持多个 OAuth 账号绑定到同一用户

## 实现方案

### Phase 1: 优化现有认证流程 ✅

**目标**：统一使用后端 JWT token

**已完成**：
- ✅ 更新 settings 页面使用 `getBackendToken()`
- ✅ 修复 401 认证错误

### Phase 2: 实现邮箱密码登录

#### 2.1 后端 API

**新增端点**：
```
POST /api/v1/auth/login
  - 支持邮箱/用户名 + 密码登录
  - 返回 JWT token

POST /api/v1/auth/register
  - 邮箱注册
  - 返回 JWT token

POST /api/v1/auth/bind-email
  - 为已登录用户绑定邮箱密码
  - 需要认证

PUT /api/v1/auth/change-password
  - 修改密码
  - 需要认证

POST /api/v1/auth/reset-password-request
  - 请求重置密码（发送邮件）

POST /api/v1/auth/reset-password
  - 重置密码（使用邮件中的 token）
```

#### 2.2 前端页面

**登录页面优化**：
```
/login
  - Google 登录按钮
  - 微信登录按钮（未来）
  - 邮箱/用户名 + 密码表单
  - "忘记密码" 链接
  - "注册账号" 链接
```

**个人设置页面**：
```
/settings/profile
  - 显示已绑定的 OAuth 账号
  - 添加/修改邮箱密码
  - 修改密码功能
```

### Phase 3: 实现微信 OAuth 登录

#### 3.1 后端实现

**新增端点**：
```
GET /api/v1/auth/wechat/authorize
  - 生成微信授权 URL

GET /api/v1/auth/wechat/callback
  - 处理微信回调
  - 创建或绑定用户
  - 返回 JWT token
```

#### 3.2 前端集成

- 在登录页面添加微信登录按钮
- 处理微信登录回调
- 获取后端 JWT token

### Phase 4: 完善用户个人资料管理

**新增功能**：
- 查看已绑定的登录方式
- 绑定/解绑 OAuth 账号
- 设置主登录方式
- 账号安全设置

## 数据库优化

### 现有表结构（已完善）

```sql
-- users 表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),  -- 可为空（OAuth 用户）
    display_name VARCHAR(100),
    avatar_url TEXT,
    motto VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- oauth_accounts 表
CREATE TABLE oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    provider VARCHAR(50) NOT NULL,  -- google, wechat
    provider_user_id VARCHAR(255) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    extra_data JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(provider, provider_user_id)
);
```

### 需要添加的索引

```sql
-- 优化邮箱登录查询
CREATE INDEX IF NOT EXISTS idx_users_email_active ON users(email) WHERE is_active = TRUE;

-- 优化 OAuth 查询
CREATE INDEX IF NOT EXISTS idx_oauth_provider_user ON oauth_accounts(provider, provider_user_id);
```

## 安全考虑

### 1. 密码安全
- 使用 bcrypt 哈希（已实现）
- 最小密码长度：8 位
- 密码复杂度要求：至少包含字母和数字

### 2. Token 安全
- JWT token 有效期：7 天
- Refresh token 有效期：60 天
- 支持 token 撤销（黑名单机制）

### 3. OAuth 安全
- 使用 state 参数防止 CSRF
- 验证 redirect_uri
- 安全存储 access_token 和 refresh_token

### 4. 邮箱验证
- 注册时发送验证邮件
- 重置密码需要邮箱验证
- 绑定邮箱需要验证

## 实现优先级

1. **高优先级**（本次实现）
   - ✅ 统一认证流程
   - 🔄 邮箱密码登录
   - 🔄 个人设置中绑定邮箱密码

2. **中优先级**（下一阶段）
   - 微信 OAuth 登录
   - 邮箱验证功能
   - 密码重置功能

3. **低优先级**（未来优化）
   - 双因素认证（2FA）
   - 登录历史记录
   - 设备管理

## 技术栈

### 后端
- FastAPI
- JWT (python-jose)
- Passlib (bcrypt)
- PostgreSQL

### 前端
- Next.js 14
- NextAuth.js (仅用于 OAuth)
- React Hook Form
- Zod (表单验证)

## 测试计划

### 单元测试
- 密码哈希和验证
- JWT token 生成和验证
- OAuth state 生成和验证

### 集成测试
- 邮箱密码登录流程
- OAuth 登录流程
- 账号绑定流程
- 密码修改流程

### E2E 测试
- 完整的用户注册登录流程
- 多种登录方式切换
- 账号绑定和解绑

## 迁移计划

### 现有用户迁移
1. 已有 Google OAuth 用户：无需迁移，可选择绑定邮箱密码
2. 已有用户名密码用户：无需迁移，可选择绑定 OAuth 账号

### 数据库迁移
- 无需修改现有表结构
- 添加新的索引以优化查询性能

## 时间估算

- Phase 1: ✅ 已完成
- Phase 2: 2-3 天
  - 后端 API: 1 天
  - 前端页面: 1-2 天
- Phase 3: 2-3 天
  - 微信 OAuth 集成: 2-3 天
- Phase 4: 1 天
  - 个人资料管理: 1 天

**总计**: 约 5-7 天
