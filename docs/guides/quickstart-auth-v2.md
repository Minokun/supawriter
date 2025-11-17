# 🚀 认证系统 V2 快速开始

## 一、系统特性

### ✨ 支持的登录方式

1. **📧 邮箱密码登录**
   - ⚠️ **应用不提供注册功能，请在官网注册**
   - 密码强度验证
   - 记住登录状态（30天）

2. **🔐 Google OAuth 登录**
   - 一键 Google 登录
   - 自动同步头像和邮箱
   - 首次登录自动创建账号

3. **🔐 微信扫码登录**
   - 微信扫码快速登录
   - 支持 unionid 和 openid
   - 自动同步昵称和头像

### 🔗 账号绑定功能

- **邮箱账号** → 可绑定 Google 和微信
- **Google 账号** → 可设置邮箱和密码
- **微信账号** → 可设置邮箱和密码
- **灵活切换** → 用任何已绑定的方式登录

## 二、快速部署

### 方法一：使用自动部署脚本（推荐）

```bash
# 进入项目目录
cd /path/to/supawriter

# 给脚本执行权限
chmod +x scripts/setup_auth_v2.sh

# 运行部署脚本
./scripts/setup_auth_v2.sh
```

脚本会自动：
1. ✅ 检查 Python 环境
2. ✅ 检查 PostgreSQL
3. ✅ 安装依赖包
4. ✅ 验证数据库连接
5. ✅ 执行数据库迁移
6. ✅ 运行系统测试

### 方法二：手动部署

#### 1. 安装依赖

```bash
pip install psycopg2-binary
# 或使用 uv
uv pip install psycopg2-binary
```

#### 2. 配置数据库

确保 `deployment/.env` 文件存在并包含数据库配置：

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=supawriter
POSTGRES_USER=supawriter
POSTGRES_PASSWORD=your_password
DATABASE_URL=postgresql://supawriter:your_password@localhost:5432/supawriter
```

#### 3. 启动 PostgreSQL

**使用 Docker：**
```bash
cd deployment
docker-compose up -d postgres
```

**或本地安装：**
```bash
# macOS
brew services start postgresql

# Linux
sudo systemctl start postgresql
```

#### 4. 执行数据库迁移

```bash
python scripts/migrate_database.py
```

这会：
- 创建 `users` 和 `oauth_accounts` 表
- 从 `data/users.pkl` 迁移现有用户（如果存在）
- 创建默认管理员账号

#### 5. 运行测试

```bash
python scripts/test_auth_system.py
```

## 三、在应用中使用

### 更新登录页面

**旧代码：**
```python
from auth_pages import login
if not login.app():
    st.stop()
```

**新代码：**
```python
from auth_pages import login_v2
if not login_v2.app():
    st.stop()
```

### 更新个人中心页面

**旧代码：**
```python
from auth_pages import profile
profile.app()
```

**新代码：**
```python
from auth_pages import profile_v2
profile_v2.app()
```

### 在代码中获取用户信息

```python
from utils.auth_v2 import AuthService

# 检查登录状态
if AuthService.is_authenticated():
    # 获取当前用户信息
    user = AuthService.get_current_user()
    
    # 用户信息包含：
    print(f"用户ID: {user['id']}")
    print(f"用户名: {user['username']}")
    print(f"邮箱: {user.get('email')}")
    print(f"显示名称: {user.get('display_name')}")
    print(f"头像URL: {user.get('avatar_url')}")
```

### 账号绑定管理

```python
from utils.account_binding import AccountBindingService

user_id = user['id']

# 获取已绑定的账号
bound_accounts = AccountBindingService.get_bound_accounts(user_id)

# 检查是否可以使用邮箱登录
can_email_login = AccountBindingService.can_login_with_email(user_id)

# 检查是否已绑定 Google
has_google = AccountBindingService.has_google_binding(user_id)

# 检查是否已绑定微信
has_wechat = AccountBindingService.has_wechat_binding(user_id)

# 为 OAuth 用户设置邮箱和密码
success, message = AccountBindingService.bind_email_and_password(
    user_id=user_id,
    email="user@example.com",
    password="SecurePass123!"
)

# 解绑 OAuth 账号
success, message = AccountBindingService.unbind_oauth_account(
    user_id=user_id,
    provider="google"  # 或 "wechat"
)
```

## 四、配置 OAuth

### Google OAuth（Streamlit 内置）

在 `.streamlit/secrets.toml` 中配置：

```toml
[auth_google]
client_id = "your-google-client-id.apps.googleusercontent.com"
client_secret = "your-google-client-secret"
redirect_uri = "http://localhost:8501"
```

**获取 Google OAuth 凭证：**
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目或选择现有项目
3. 启用 "Google+ API"
4. 创建 OAuth 2.0 客户端 ID
5. 添加授权重定向 URI

### 微信 OAuth

在 `.streamlit/secrets.toml` 中配置：

```toml
[wechat]
app_id = "your-wechat-app-id"
app_secret = "your-wechat-app-secret"
redirect_uri = "https://your-domain.com/callback"
```

**获取微信 OAuth 凭证：**
1. 访问 [微信开放平台](https://open.weixin.qq.com/)
2. 注册开发者账号
3. 创建网站应用
4. 获取 AppID 和 AppSecret
5. 配置授权回调域名

详细步骤参考：`docs/WECHAT_LOGIN_SETUP.md`

## 五、默认账号

如果执行了数据库迁移，系统会创建默认管理员账号：

```
用户名: admin
密码: admin123
```

**⚠️ 安全提示：** 首次登录后请立即修改密码！

## 六、测试功能

### 创建测试用户（管理员）

由于应用不提供注册功能，您需要手动创建测试用户：

**方法1：使用管理员工具**

**创建单个用户**
```bash
# 交互式创建
python scripts/create_user.py

# 命令行创建
python scripts/create_user.py \
    --username newuser \
    --email user@example.com \
    --password SecurePass123! \
    --display-name "新用户"
```

**批量创建用户**
```bash
# 使用JSON文件批量创建
python scripts/create_user.py --batch scripts/users_example.json
```

JSON文件格式示例：
```json
[
  {
    "username": "user1",
    "email": "user1@example.com",
    "password": "SecurePass123!",
    "display_name": "用户一"
  }
]
```

**方法2：直接在数据库中创建**
```sql
INSERT INTO users (username, email, password_hash, display_name, created_at, updated_at)
VALUES (
    'testuser',
    'test@example.com',
    -- 密码: Test123456!
    'b109f3bbbc244eb82441917ed06d618b9008dd09b3befd1b5e07394c706a8bb9',
    '测试用户',
    NOW(),
    NOW()
);
```

**测试登录**
1. 访问应用登录页面
2. 使用创建的邮箱和密码登录

### 测试 Google 登录

1. 点击"Google 登录"按钮
2. 选择 Google 账号
3. 首次登录会自动创建用户

### 测试账号绑定

1. 使用任意方式登录
2. 进入"个人中心"
3. 点击"管理登录方式"
4. 添加其他登录方式

## 七、故障排查

### 问题1: 数据库连接失败

```
psycopg2.OperationalError: could not connect to server
```

**解决方法：**
1. 检查 PostgreSQL 是否运行：`pg_isready`
2. 验证 `deployment/.env` 中的数据库配置
3. 确认防火墙未阻止连接

### 问题2: 表已存在

```
psycopg2.errors.DuplicateTable: relation "users" already exists
```

**解决方法：**
- 表已创建，可以跳过迁移
- 或手动删除表后重新迁移：
  ```sql
  DROP TABLE IF EXISTS oauth_accounts CASCADE;
  DROP TABLE IF EXISTS users CASCADE;
  ```

### 问题3: Google OAuth 失败

**检查清单：**
- [ ] `.streamlit/secrets.toml` 配置正确
- [ ] Google Console 中 OAuth 客户端已创建
- [ ] 重定向 URI 匹配（http://localhost:8501）
- [ ] Google+ API 已启用

### 问题4: 微信登录失败

**检查清单：**
- [ ] AppID 和 AppSecret 正确
- [ ] 回调域名已在微信开放平台配置
- [ ] 应用已通过审核
- [ ] 网络可以访问微信 API

## 八、数据迁移

### 从旧系统迁移

如果您之前使用 pickle 文件存储用户（`data/users.pkl`），迁移脚本会自动：

1. ✅ 读取 pickle 文件中的所有用户
2. ✅ 将用户导入到 PostgreSQL
3. ✅ 保留用户名、邮箱、密码哈希
4. ✅ 备份原 pickle 文件

### 验证迁移结果

```bash
# 连接数据库
psql $DATABASE_URL

# 查询用户数量
SELECT COUNT(*) FROM users;

# 查看用户列表
SELECT id, username, email, created_at FROM users;
```

## 九、API 参考

### 认证服务 (AuthService)

```python
from utils.auth_v2 import AuthService

# 注册用户
success, msg = AuthService.register_with_email(username, email, password)

# 邮箱登录
success, msg, user = AuthService.login_with_email(email, password, remember_me)

# 检查登录状态
is_logged_in = AuthService.is_authenticated()

# 获取当前用户
user = AuthService.get_current_user()

# 退出登录
AuthService.logout()

# 修改密码
success, msg = AuthService.change_password(user_id, old_pwd, new_pwd)

# 更新用户资料
success, msg = AuthService.update_profile(user_id, display_name="New Name")
```

### 账号绑定服务 (AccountBindingService)

```python
from utils.account_binding import AccountBindingService

# 绑定 Google 账号
success, msg = AccountBindingService.bind_google_account(user_id, google_info)

# 绑定微信账号
success, msg = AccountBindingService.bind_wechat_account(user_id, wechat_info)

# 设置邮箱和密码
success, msg = AccountBindingService.bind_email_and_password(user_id, email, pwd)

# 解绑 OAuth 账号
success, msg = AccountBindingService.unbind_oauth_account(user_id, provider)

# 获取已绑定账号
accounts = AccountBindingService.get_bound_accounts(user_id)
```

## 十、安全最佳实践

1. **密码策略**
   - 最少 8 个字符
   - 建议包含大小写字母、数字、特殊字符
   - 定期提醒用户更新密码

2. **数据库安全**
   - 使用强密码
   - 限制数据库访问权限
   - 启用 SSL 连接
   - 定期备份数据

3. **OAuth 密钥管理**
   - 不要将密钥提交到版本控制
   - 使用环境变量或 secrets
   - 定期轮换密钥
   - 监控异常登录

4. **会话管理**
   - 使用 HTTPS（生产环境）
   - 设置合理的会话过期时间
   - 实现登录尝试限制
   - 记录安全事件日志

## 十一、性能优化

1. **数据库连接池**
   - 已实现连接池（1-10个连接）
   - 根据负载调整 minconn 和 maxconn

2. **索引优化**
   - 已创建必要的索引
   - 定期 VACUUM 和 ANALYZE

3. **缓存策略**
   - 考虑使用 Redis 缓存用户会话
   - 缓存常用查询结果

## 十二、进阶功能

### 自定义登录流程

```python
# 在登录成功后执行自定义逻辑
def custom_login_callback(user):
    # 记录登录日志
    logger.info(f"User {user['username']} logged in")
    
    # 更新用户统计
    update_user_stats(user['id'])
    
    # 发送欢迎消息
    send_welcome_message(user['email'])
```

### 多因素认证（MFA）

可以在现有基础上添加：
- TOTP（Time-based One-Time Password）
- SMS 验证码
- 邮箱验证码

### 权限管理

扩展 `users` 表添加角色字段：
```sql
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user';
ALTER TABLE users ADD COLUMN permissions JSONB;
```

## 十三、更多资源

- **完整文档**: `AUTHENTICATION_V2_GUIDE.md`
- **数据库 Schema**: `deployment/migrate/001_create_auth_tables.sql`
- **测试脚本**: `scripts/test_auth_system.py`
- **微信配置**: `docs/WECHAT_LOGIN_SETUP.md`

## 十四、获取帮助

如有问题：
1. 查看日志输出
2. 运行测试脚本
3. 检查数据库连接
4. 验证配置文件
5. 查阅相关文档

---

**祝您使用愉快！🎉**
