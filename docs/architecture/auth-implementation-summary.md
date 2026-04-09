# 认证系统实现总结

## 已完成功能

### 后端 API

#### 1. 基础认证端点

**POST /api/v1/auth/register**
- 邮箱注册新用户
- 自动生成 JWT token
- 返回用户信息

**POST /api/v1/auth/login**
- 邮箱/密码登录
- 返回 JWT token
- 支持 bcrypt 和 SHA256 密码验证（向后兼容）

**POST /api/v1/auth/logout**
- 登出（客户端删除 token）
- 记录登出日志

**GET /api/v1/auth/me**
- 获取当前用户信息
- 需要 JWT token 认证

#### 2. OAuth 认证端点

**GET /api/v1/auth/oauth/{provider}**
- 支持的提供商：google, wechat（待实现）
- 生成 OAuth 授权 URL
- 使用 state 参数防止 CSRF

**GET /api/v1/auth/oauth/callback/{provider}**
- 处理 OAuth 回调
- 自动创建或绑定用户
- 返回 JWT token

#### 3. 账号管理端点（新增）

**GET /api/v1/auth/profile**
- 获取用户完整资料
- 包含已绑定的 OAuth 账号列表
- 显示是否设置了密码

**POST /api/v1/auth/bind-email**
- 为 OAuth 用户绑定邮箱和密码
- 允许添加备用登录方式
- 验证邮箱唯一性

**PUT /api/v1/auth/change-password**
- 修改密码
- 验证旧密码
- 使用 bcrypt 加密新密码

### 数据模型

#### 新增 Pydantic 模型

```python
class BindEmailRequest(BaseModel):
    """绑定邮箱请求"""
    email: EmailStr
    password: str  # 最小 8 位

class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str  # 最小 8 位

class OAuthAccountInfo(BaseModel):
    """OAuth 账号信息"""
    provider: str
    provider_user_id: str
    created_at: str

class UserProfileResponse(BaseModel):
    """用户完整资料响应"""
    id: int
    username: str
    email: Optional[str]
    display_name: Optional[str]
    avatar: Optional[str]
    bio: Optional[str]
    has_password: bool
    oauth_accounts: list[OAuthAccountInfo]
```

## 认证流程

### 1. Google OAuth 登录流程

```
用户点击 Google 登录
  ↓
前端调用 NextAuth signIn('google')
  ↓
NextAuth 处理 OAuth 流程
  ↓
回调到 /api/auth/callback/google
  ↓
前端调用 /api/auth/backend-token
  ↓
后端验证 Google token 并返回 JWT
  ↓
前端存储 JWT token 到 localStorage
  ↓
后续 API 调用使用 JWT token
```

### 2. 邮箱密码登录流程

```
用户输入邮箱和密码
  ↓
前端调用 POST /api/v1/auth/login
  ↓
后端验证邮箱和密码
  ↓
返回 JWT token 和用户信息
  ↓
前端存储 JWT token 到 localStorage
  ↓
后续 API 调用使用 JWT token
```

### 3. 账号绑定流程

```
OAuth 用户登录后
  ↓
访问个人设置页面
  ↓
调用 GET /api/v1/auth/profile 查看当前绑定状态
  ↓
如果 has_password = false，显示绑定邮箱表单
  ↓
用户输入邮箱和密码
  ↓
调用 POST /api/v1/auth/bind-email
  ↓
绑定成功，用户可以使用邮箱密码登录
```

## 安全特性

### 1. 密码安全
- ✅ 使用 bcrypt 哈希（新用户）
- ✅ 支持 SHA256 向后兼容（旧用户）
- ✅ 最小密码长度：8 位
- ⏳ 密码复杂度验证（待实现）

### 2. Token 安全
- ✅ JWT token 有效期：7 天
- ✅ Token 包含用户 ID 和类型
- ✅ 使用 HMAC-SHA256 签名
- ⏳ Refresh token 机制（待实现）
- ⏳ Token 黑名单（待实现）

### 3. OAuth 安全
- ✅ 使用 state 参数防止 CSRF
- ✅ 验证 state 时间戳（10 分钟有效）
- ✅ 安全存储 OAuth tokens
- ✅ 同一 OAuth 账号只能绑定一个用户

### 4. API 安全
- ✅ 所有敏感端点需要认证
- ✅ 邮箱唯一性验证
- ✅ 密码修改需要验证旧密码
- ✅ 详细的错误日志记录

## 数据库结构

### users 表
```sql
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### oauth_accounts 表
```sql
CREATE TABLE oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,  -- google, wechat
    provider_user_id VARCHAR(255) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    extra_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_user_id)
);
```

## 前端集成

### 1. 统一认证 Hook

```typescript
// lib/api.ts
export async function getBackendToken(): Promise<string | null> {
  // 从 NextAuth session 交换后端 JWT token
  // 自动缓存到 localStorage
}

export async function ensureAuth(): Promise<boolean> {
  const token = await getBackendToken();
  return token !== null;
}
```

### 2. API 调用示例

```typescript
// 使用后端 JWT token
const token = await getBackendToken();
const response = await fetch('/api/v1/settings/llm-providers', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

### 3. 登录页面（待实现）

```typescript
// app/login/page.tsx
- Google 登录按钮（已有）
- 邮箱密码登录表单（待实现）
- 注册链接（待实现）
- 忘记密码链接（待实现）
```

### 4. 个人设置页面（待实现）

```typescript
// app/settings/profile/page.tsx
- 显示已绑定的 OAuth 账号
- 绑定邮箱密码表单
- 修改密码表单
- 账号安全设置
```

## 下一步工作

### 高优先级
1. ✅ 后端 API 实现
2. 🔄 前端登录页面优化
3. 🔄 个人设置页面实现
4. ⏳ 邮箱密码登录测试

### 中优先级
1. ⏳ 微信 OAuth 集成
2. ⏳ 邮箱验证功能
3. ⏳ 密码重置功能
4. ⏳ Refresh token 机制

### 低优先级
1. ⏳ 双因素认证（2FA）
2. ⏳ 登录历史记录
3. ⏳ 设备管理
4. ⏳ 账号注销功能

## API 端点总览

| 方法 | 端点 | 认证 | 描述 |
|------|------|------|------|
| POST | /api/v1/auth/register | ❌ | 邮箱注册 |
| POST | /api/v1/auth/login | ❌ | 邮箱密码登录 |
| POST | /api/v1/auth/logout | ✅ | 登出 |
| GET | /api/v1/auth/me | ✅ | 获取当前用户信息 |
| GET | /api/v1/auth/profile | ✅ | 获取完整用户资料 |
| POST | /api/v1/auth/bind-email | ✅ | 绑定邮箱密码 |
| PUT | /api/v1/auth/change-password | ✅ | 修改密码 |
| GET | /api/v1/auth/oauth/{provider} | ❌ | OAuth 登录入口 |
| GET | /api/v1/auth/oauth/callback/{provider} | ❌ | OAuth 回调 |
| POST | /api/v1/auth/oauth/verify-token | ✅ | 验证 token |

## 测试建议

### 单元测试
- [ ] 密码哈希和验证
- [ ] JWT token 生成和验证
- [ ] OAuth state 生成和验证
- [ ] 邮箱唯一性验证

### 集成测试
- [ ] 邮箱注册流程
- [ ] 邮箱密码登录流程
- [ ] Google OAuth 登录流程
- [ ] 账号绑定流程
- [ ] 密码修改流程

### E2E 测试
- [ ] 完整的用户注册登录流程
- [ ] OAuth 登录后绑定邮箱
- [ ] 多种登录方式切换
- [ ] 密码修改和重新登录

## 注意事项

1. **Token 管理**：前端需要统一使用 `getBackendToken()` 获取 JWT token，不要直接使用 NextAuth 的 `session.accessToken`

2. **密码安全**：新用户使用 bcrypt，旧用户兼容 SHA256，建议提示旧用户修改密码以升级到 bcrypt

3. **OAuth 绑定**：同一个 OAuth 账号只能绑定到一个用户，防止账号冲突

4. **邮箱唯一性**：绑定邮箱时需要验证邮箱是否已被其他用户使用

5. **错误处理**：所有 API 调用都应该有适当的错误处理和用户提示

## 相关文档

- [认证系统优化方案](./auth-optimization-plan.md)
- [数据库 Schema](../../deployment/migrate/001_create_auth_tables.sql)
- [后端安全模块](../../backend/api/core/security.py)
- [前端 API 工具](../../frontend/src/lib/api.ts)
