# 微信开放平台登录配置指南

本文档将指导你如何在 SupaWriter 中配置微信开放平台的扫码登录功能。

## 📋 前提条件

1. **微信开放平台账号**：需要注册为开发者（个人或企业）
2. **网站应用审核**：需要创建并通过审核的网站应用
3. **已备案域名**（生产环境）：微信要求使用已备案的域名

## 🔧 配置步骤

### 1. 注册微信开放平台账号

1. 访问 [微信开放平台](https://open.weixin.qq.com/)
2. 点击右上角"注册"按钮
3. 选择账号类型：
   - **个人开发者**：适合个人开发和测试
   - **企业开发者**：适合商业应用，需要营业执照

### 2. 创建网站应用

1. 登录微信开放平台，进入"管理中心"
2. 点击"网站应用" → "创建网站应用"
3. 填写应用信息：
   - **应用名称**：你的应用名称（如：SupaWriter）
   - **应用简介**：简要描述应用功能
   - **应用官网**：你的网站地址
   - **应用图标**：上传应用 Logo（120x120 像素）

4. 填写**网站信息**：
   - **网站域名**：
     - 本地开发：`localhost` 或 `127.0.0.1`
     - 生产环境：你的已备案域名（如：`www.example.com`）
   - **授权回调域**：
     - 本地开发：`localhost`
     - 生产环境：你的域名（不带 http:// 和路径）

5. 提交申请，等待审核（通常 1-7 个工作日）

### 3. 获取应用凭证

审核通过后：

1. 进入"网站应用"页面
2. 找到你创建的应用
3. 记录以下信息：
   - **AppID**：应用的唯一标识
   - **AppSecret**：应用密钥（需要点击"查看"按钮）

⚠️ **重要提示**：AppSecret 非常重要，请妥善保管，不要泄露或提交到代码仓库！

### 4. 配置 SupaWriter

1. 打开 `.streamlit/secrets.toml` 文件（如果不存在，复制 `secrets.toml.example`）

2. 添加微信配置：

```toml
[wechat]
app_id = "wx1234567890abcdef"        # 替换为你的 AppID
app_secret = "your_app_secret_here"  # 替换为你的 AppSecret
redirect_uri = "http://localhost:8501"  # 本地开发使用
# redirect_uri = "https://www.example.com"  # 生产环境使用你的域名
```

3. 保存文件并重启应用：

```bash
streamlit run web.py
```

### 5. 测试登录

1. 访问应用登录页面
2. 点击"使用微信登录"按钮
3. 使用微信扫描二维码
4. 在手机微信中确认授权
5. 成功登录后，会显示你的微信昵称和头像

## 🌐 生产环境部署注意事项

### 域名要求

1. **已备案域名**：微信要求生产环境必须使用已在中国工信部备案的域名
2. **HTTPS 协议**：生产环境必须使用 HTTPS（微信强制要求）
3. **回调域配置**：
   - 在微信开放平台的"网站信息"中配置授权回调域
   - 回调域不需要包含协议（http/https）和路径
   - 例如：`www.example.com` 或 `example.com`

### 配置示例

**本地开发环境**：
```toml
[wechat]
app_id = "wx1234567890abcdef"
app_secret = "your_app_secret_here"
redirect_uri = "http://localhost:8501"
```

**生产环境**：
```toml
[wechat]
app_id = "wx1234567890abcdef"
app_secret = "your_app_secret_here"
redirect_uri = "https://www.example.com"
```

### Streamlit Cloud 部署

如果使用 Streamlit Cloud 部署：

1. 在 Streamlit Cloud 的 App Settings 中添加 secrets
2. redirect_uri 使用你的 Streamlit Cloud URL：
   ```toml
   redirect_uri = "https://your-app.streamlit.app"
   ```
3. 在微信开放平台配置回调域：`your-app.streamlit.app`

## 🔍 常见问题

### Q1: 提示"微信登录未配置"

**原因**：secrets.toml 文件中未配置微信信息或配置格式错误

**解决方案**：
1. 确认 secrets.toml 文件存在于 `.streamlit/` 目录下
2. 检查配置格式是否正确（使用 `[wechat]` 作为配置节）
3. 确保 `app_id`、`app_secret`、`redirect_uri` 都已配置

### Q2: 扫码后提示授权失败

**可能原因**：
1. AppSecret 配置错误
2. redirect_uri 与微信平台配置的回调域不匹配
3. 应用未通过审核或已被封禁

**解决方案**：
1. 检查 AppSecret 是否正确
2. 确认 redirect_uri 与微信开放平台的授权回调域完全一致
3. 检查应用审核状态

### Q3: 本地开发可以，部署到服务器后无法使用

**原因**：生产环境的 redirect_uri 配置不正确

**解决方案**：
1. 确保使用 HTTPS 协议
2. 确认域名已备案
3. 在微信开放平台更新授权回调域为生产环境域名
4. 更新 secrets.toml 中的 redirect_uri 为生产环境 URL

### Q4: 如何支持多个域名？

微信开放平台的一个应用只能配置一个授权回调域。如果需要支持多个域名：

**方案 1**：创建多个网站应用（推荐）
- 为每个域名创建独立的网站应用
- 在不同环境使用不同的 AppID 和 AppSecret

**方案 2**：使用通配符子域名
- 配置主域名：`example.com`
- 可以使用所有子域名：`www.example.com`、`app.example.com` 等

## 📚 相关资源

- [微信开放平台官网](https://open.weixin.qq.com/)
- [微信登录开发文档](https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html)
- [网站应用接入指南](https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html)
- [常见问题 FAQ](https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_FAQ.html)

## 🔐 安全建议

1. **保护密钥**：
   - 不要将 AppSecret 提交到公开的代码仓库
   - 使用环境变量或密钥管理服务存储敏感信息
   - 定期更换 AppSecret（微信开放平台支持重置）

2. **验证回调**：
   - 使用 state 参数防止 CSRF 攻击
   - 验证回调来源，确保是微信官方服务器

3. **用户数据**：
   - 仅获取必要的用户信息
   - 妥善存储用户数据，遵守隐私保护法规
   - 为用户提供注销账号和删除数据的功能

## 💡 提示

- 微信开放平台的审核周期较长，建议提前申请
- 测试阶段可以使用 localhost，无需等待审核
- 如遇问题，可查看微信开放平台的社区论坛获取帮助
- 建议同时配置 Google OAuth2，为用户提供更多登录选择
