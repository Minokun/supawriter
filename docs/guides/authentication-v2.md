# SupaWriter 认证系统 V2 升级指南

## 概述

新的认证系统支持以下功能：

### ✨ 主要特性

1. **多种登录方式**
   - 📧 邮箱 + 密码登录
   - 🔐 Google OAuth 登录
   - 🔐 微信扫码登录

2. **账号绑定功能**
   - 邮箱账号可以绑定 Google 和微信
   - Google/微信账号可以设置邮箱和密码
   - 支持多种登录方式绑定到同一用户

3. **数据存储**
   - 使用 PostgreSQL 数据库
   - 安全的密码哈希存储
   - OAuth 令牌安全管理

## 快速开始

### 1. 安装依赖

```bash
pip install psycopg2-binary
# 或使用 uv
uv pip install psycopg2-binary
```

### 2. 配置数据库

确保 PostgreSQL 数据库已启动，配置在以下位置之一：

**选项 A: 环境变量**
```bash
export DATABASE_URL="postgresql://supawriter:password@localhost:5432/supawriter"
```

**选项 B: deployment/.env 文件**
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=supawriter
POSTGRES_USER=supawriter
POSTGRES_PASSWORD=your_password
DATABASE_URL=postgresql://supawriter:your_password@localhost:5432/supawriter
```

**选项 C: Streamlit secrets**
在 `.streamlit/secrets.toml` 中添加：
```toml
DATABASE_URL = "postgresql://supawriter:password@localhost:5432/supawriter"

[postgres]
host = "localhost"
port = 5432
database = "supawriter"
user = "supawriter"
password = "your_password"
```

### 3. 执行数据库迁移

```bash
# 确保deployment/.env中的数据库配置正确
cd /path/to/supawriter

# 执行迁移脚本
python scripts/migrate_database.py
```

迁移脚本会：
- ✅ 创建 `users` 和 `oauth_accounts` 表
- ✅ 从 `data/users.pkl` 迁移现有用户
- ✅ 备份原 pickle 文件

### 4. 配置 OAuth（可选）

#### Google OAuth

在 `.streamlit/secrets.toml` 中配置（Streamlit 自带）：
```toml
[auth_google]
client_id = "your-google-client-id"
client_secret = "your-google-client-secret"
redirect_uri = "http://localhost:8501"
```

#### 微信 OAuth

在 `.streamlit/secrets.toml` 中配置：
```toml
[wechat]
app_id = "your-wechat-app-id"
app_secret = "your-wechat-app-secret"
redirect_uri = "http://your-domain.com/callback"
```

参考 `docs/WECHAT_LOGIN_SETUP.md` 了解详细配置。

### 5. 更新代码引用

**原有代码（使用旧认证）：**
```python
from utils.auth import is_authenticated, get_current_user, logout
```

**新代码（使用新认证）：**
```python
from utils.auth_v2 import AuthService

# 检查登录
if AuthService.is_authenticated():
    user = AuthService.get_current_user()
    user_id = user['id']
    username = user['username']

# 退出登录
AuthService.logout()
```

### 6. 使用新的登录页面

**更新 web.py 或主入口文件：**
```python
# 旧代码
from auth_pages import login
login.app()

# 新代码
from auth_pages import login_v2
login_v2.app()
```

## 数据库 Schema

### users 表
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    display_name VARCHAR(100),
    avatar_url TEXT,
    motto VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### oauth_accounts 表
```sql
CREATE TABLE oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    extra_data JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(provider, provider_user_id)
);
```

## API 使用示例

### 注册新用户

```python
from utils.auth_v2 import AuthService

success, message = AuthService.register_with_email(
    username="john_doe",
    email="john@example.com",
    password="SecurePass123!",
    display_name="John Doe"
)

if success:
    print("注册成功！")
else:
    print(f"注册失败: {message}")
```

### 邮箱登录

```python
success, message, user = AuthService.login_with_email(
    email="john@example.com",
    password="SecurePass123!",
    remember_me=True
)

if success:
    print(f"登录成功: {user['username']}")
```

### Google 登录

```python
# Streamlit OAuth 会自动处理
# 在回调中：
google_info = {
    'sub': st.user.sub,
    'email': st.user.email,
    'name': st.user.name,
    'picture': st.user.picture
}

success, message, user = AuthService.login_with_google(google_info)
```

### 账号绑定

```python
from utils.account_binding import AccountBindingService

# 绑定 Google 账号
success, message = AccountBindingService.bind_google_account(
    user_id=user_id,
    google_info=google_info
)

# 为 OAuth 用户设置邮箱密码
success, message = AccountBindingService.bind_email_and_password(
    user_id=user_id,
    email="john@example.com",
    password="SecurePass123!"
)

# 解绑 OAuth 账号
success, message = AccountBindingService.unbind_oauth_account(
    user_id=user_id,
    provider="google"
)
```

### 查询已绑定账号

```python
from utils.account_binding import AccountBindingService

bound_accounts = AccountBindingService.get_bound_accounts(user_id)
for account in bound_accounts:
    print(f"{account['display_name']}: {account['identifier']}")
```

## 测试

### 1. 测试数据库连接

```bash
python -c "from utils.database import Database; conn = Database.get_connection_pool(); print('✅ 数据库连接成功')"
```

### 2. 测试用户注册

```python
from utils.auth_v2 import AuthService

# 注册测试用户
success, msg = AuthService.register_with_email(
    username="test_user",
    email="test@example.com",
    password="Test123456!",
    display_name="测试用户"
)
print(f"{msg}")
```

### 3. 测试登录

```python
# 登录测试
success, msg, user = AuthService.login_with_email(
    email="test@example.com",
    password="Test123456!"
)
if success:
    print(f"✅ 登录成功: {user['username']}")
```

## 故障排除

### 问题 1: 数据库连接失败

**错误信息：** `psycopg2.OperationalError: could not connect to server`

**解决方法：**
1. 检查 PostgreSQL 是否运行：`pg_isready`
2. 检查数据库配置是否正确
3. 确保网络连接正常

### 问题 2: 迁移失败

**错误信息：** `psycopg2.errors.DuplicateTable`

**解决方法：**
表已存在，跳过迁移或手动删除表后重新迁移。

### 问题 3: OAuth 登录失败

**Google OAuth：**
- 检查 `.streamlit/secrets.toml` 配置
- 确保 `redirect_uri` 正确
- 检查 Google Console 配置

**微信 OAuth：**
- 检查 AppID 和 AppSecret
- 确保回调域名已在微信开放平台配置
- 参考 `docs/WECHAT_LOGIN_SETUP.md`

## 向后兼容

为了保持向后兼容，`utils/auth_v2.py` 提供了兼容函数：

```python
# 这些函数会自动适配新系统
from utils.auth_v2 import is_authenticated, get_current_user, logout

if is_authenticated():
    username = get_current_user()
    print(f"当前用户: {username}")
```

## 安全建议

1. **密码策略**
   - 最少 8 个字符
   - 建议包含大小写字母、数字和特殊字符

2. **数据库安全**
   - 使用强密码
   - 限制数据库访问权限
   - 定期备份数据

3. **OAuth 密钥**
   - 不要将密钥提交到版本控制
   - 使用环境变量或 secrets 管理
   - 定期轮换密钥

## 更多资源

- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [Streamlit Authentication](https://docs.streamlit.io/library/advanced-features/authentication)
- [Google OAuth 文档](https://developers.google.com/identity/protocols/oauth2)
- [微信开放平台文档](https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html)

## 支持

如有问题，请查看：
- 项目文档：`docs/`
- 迁移日志：检查迁移脚本输出
- 应用日志：查看 Streamlit 日志输出
