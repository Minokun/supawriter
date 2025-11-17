# SupaWriter 认证系统说明

## 📌 概述

SupaWriter 支持三种登录方式，为不同地区和偏好的用户提供灵活的认证选择：

1. **Google OAuth2** - 基于 Streamlit 原生支持，适合国际用户
2. **微信开放平台** - 支持微信扫码登录，适合国内用户
3. **本地账号** - 传统用户名密码登录，无需第三方账号

## 🔐 认证优先级

系统按以下优先级检查用户认证状态：

```
1. 微信 OAuth2 认证
2. Google OAuth2 认证  
3. 传统 session/cookie 认证
```

## 🚀 快速开始

### 方式 1: Google OAuth2（推荐）

**优点**：
- 配置简单，Streamlit 原生支持
- 国际通用，用户基数大
- 安全性高，无需管理密码

**配置步骤**：

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建 OAuth 2.0 客户端 ID
3. 配置 `secrets.toml`：

```toml
[auth.google]
client_id = "your_client_id.apps.googleusercontent.com"
client_secret = "your_client_secret"
```

**详细配置**：参考 [Streamlit SSO 文档](https://docs.streamlit.io/develop/tutorials/sso)

### 方式 2: 微信开放平台

**优点**：
- 适合国内用户，使用习惯友好
- 支持显示微信头像和昵称
- 无需记忆账号密码

**配置步骤**：

1. 注册微信开放平台开发者账号
2. 创建网站应用并通过审核
3. 配置 `secrets.toml`：

```toml
[wechat]
app_id = "wx1234567890abcdef"
app_secret = "your_app_secret"
redirect_uri = "http://localhost:8501"  # 本地开发
# redirect_uri = "https://your-domain.com"  # 生产环境
```

**详细配置**：参考 [微信登录配置指南](./WECHAT_LOGIN_SETUP.md)

### 方式 3: 本地账号

**优点**：
- 无需额外配置
- 完全自主控制
- 适合内网或私有部署

**使用方法**：
- 首次使用时在登录页面注册账号
- 使用用户名和密码登录

## 🛠️ 技术实现

### 文件结构

```
supawriter/
├── utils/
│   ├── auth.py              # 统一认证接口
│   └── wechat_oauth.py      # 微信登录实现
├── auth_pages/
│   └── login.py             # 登录页面 UI
├── .streamlit/
│   ├── secrets.toml         # 认证配置（需创建）
│   └── secrets.toml.example # 配置模板
└── docs/
    ├── AUTHENTICATION.md    # 本文档
    └── WECHAT_LOGIN_SETUP.md # 微信配置详解
```

### 核心函数

**`utils/auth.py`**:
```python
is_authenticated()          # 检查用户是否已登录
get_user_id()              # 获取用户唯一标识
get_user_display_name()    # 获取用户显示名称
logout()                   # 退出登录
```

**`utils/wechat_oauth.py`**:
```python
WeChatOAuth               # 微信 OAuth 客户端类
init_wechat_oauth()       # 初始化微信 OAuth
wechat_login_flow()       # 处理微信登录流程
is_wechat_authenticated() # 检查微信登录状态
wechat_logout()           # 微信登出
```

## 🔄 用户数据管理

### 用户标识符

不同登录方式使用不同的用户标识符：

| 登录方式 | 用户标识符 | 示例 |
|---------|-----------|------|
| Google OAuth2 | `st.user.sub` 或 `st.user.email` | `108234567890123456789` |
| 微信 | `wechat_{unionid}` 或 `wechat_{openid}` | `wechat_oabcdefg123456` |
| 本地账号 | `username` | `john_doe` |

### 数据隔离

系统基于用户标识符实现数据隔离：

```
/data/
├── faiss/
│   ├── {user_id}/        # 用户特定的 FAISS 索引
│   │   └── {article_id}/ # 文章特定的索引
├── html/
│   └── {user_id}/        # 用户生成的 HTML 文件
└── config/
    └── {user_id}.json    # 用户配置
```

## 🌐 多环境配置

### 开发环境

```toml
# Google
[auth.google]
client_id = "dev_client_id"
client_secret = "dev_secret"

# 微信
[wechat]
app_id = "wx_dev_appid"
app_secret = "dev_app_secret"
redirect_uri = "http://localhost:8501"
```

### 生产环境

```toml
# Google
[auth.google]
client_id = "prod_client_id"
client_secret = "prod_secret"

# 微信（需要已备案域名和 HTTPS）
[wechat]
app_id = "wx_prod_appid"
app_secret = "prod_app_secret"
redirect_uri = "https://www.your-domain.com"
```

## 🔒 安全建议

### 密钥管理

1. **不要提交密钥到代码仓库**
   - 将 `secrets.toml` 添加到 `.gitignore`
   - 使用环境变量或密钥管理服务

2. **定期更换密钥**
   - Google：在 Cloud Console 重新生成
   - 微信：在开放平台重置 AppSecret

3. **使用不同的密钥**
   - 开发环境和生产环境使用不同的应用和密钥

### HTTPS 要求

- **生产环境必须使用 HTTPS**
  - Google OAuth2 要求
  - 微信开放平台强制要求
- **获取免费 SSL 证书**：
  - [Let's Encrypt](https://letsencrypt.org/)
  - [Cloudflare SSL](https://www.cloudflare.com/ssl/)

### CSRF 防护

微信登录实现了 CSRF 防护：
```python
# 生成随机 state
state = hashlib.md5(str(time.time()).encode()).hexdigest()
st.session_state.wechat_state = state

# 验证回调
if state != st.session_state.wechat_state:
    st.error("状态验证失败")
```

## 🐛 故障排除

### 问题 1: 微信登录按钮显示禁用

**原因**：未配置微信认证或配置错误

**解决**：
1. 检查 `secrets.toml` 中是否有 `[wechat]` 配置
2. 确认 `app_id`、`app_secret`、`redirect_uri` 都已填写

### 问题 2: Google 登录失败

**原因**：客户端 ID 或密钥错误

**解决**：
1. 检查 Google Cloud Console 的 OAuth 2.0 客户端配置
2. 确认重定向 URI 包含当前访问的 URL
3. 验证 `secrets.toml` 中的配置

### 问题 3: 多个用户看到相同的登录状态

**原因**：Session 隔离问题（已在 v2.0 修复）

**解决**：
- 确保使用最新版本的代码
- 清除浏览器 cookies 和缓存
- 使用无痕模式测试

## 📊 用户统计

查看不同登录方式的用户分布：

```python
from utils.auth import get_user_id, is_authenticated

if is_authenticated():
    user_id = get_user_id()
    
    if user_id.startswith('wechat_'):
        print("微信用户")
    elif '@' in user_id or 'google' in user_id:
        print("Google 用户")
    else:
        print("本地账号用户")
```

## 🔗 相关文档

- [微信登录详细配置](./WECHAT_LOGIN_SETUP.md)
- [Google OAuth2 配置](https://docs.streamlit.io/develop/tutorials/sso)
- [Streamlit Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)

## 💡 最佳实践

1. **推荐同时配置多种登录方式**
   - 为用户提供更多选择
   - 降低单一认证服务故障的影响

2. **用户体验优化**
   - 显示用户头像和昵称
   - 记住用户偏好设置
   - 提供便捷的账号切换

3. **数据备份**
   - 定期备份用户配置和数据
   - 支持跨账号的数据迁移

4. **隐私保护**
   - 仅获取必要的用户信息
   - 提供数据删除和注销功能
   - 遵守 GDPR 等隐私法规
