# 用户注册策略说明

## 📋 当前策略

SupaWriter 应用**不提供用户注册功能**，所有用户注册将在官网统一处理。

### 应用端（Streamlit）

**仅提供登录功能：**
- ✅ 邮箱密码登录
- ✅ Google OAuth 登录
- ✅ 微信扫码登录
- ❌ 不提供注册入口

**用户必须先在官网注册，然后才能登录应用。**

### 官网（待开发）

**提供完整的用户注册流程：**
- 用户信息收集
- 邮箱验证
- 账号审核（如需要）
- 自动创建数据库用户记录

## 🔧 技术实现

### 应用端修改

#### 1. 登录页面 (`auth_pages/login_v2.py`)

**移除的功能：**
- ❌ 注册表单 (`show_email_register_form`)
- ❌ "注册新账号"按钮
- ❌ 注册相关的UI组件

**保留的功能：**
- ✅ 邮箱登录表单
- ✅ OAuth登录按钮
- ✅ 注册提示信息（引导用户访问官网）

#### 2. 后端API (`utils/auth_v2.py`)

**保留所有注册功能：**
```python
# 这些函数保留，供官网API调用
AuthService.register_with_email(username, email, password, display_name)
```

**原因：**
- 官网后端需要调用这些API来创建用户
- 保持代码的完整性和可维护性
- 便于后续功能扩展

### 数据库操作

#### 官网创建用户的流程

```python
# 官网后端调用示例
from utils.auth_v2 import AuthService

# 1. 验证邮箱（官网实现）
verify_email(email)

# 2. 创建用户（调用应用API）
success, message = AuthService.register_with_email(
    username=username,
    email=email,
    password=password,
    display_name=display_name
)

# 3. 发送欢迎邮件（官网实现）
send_welcome_email(email)
```

#### 手动创建用户（管理员）

```sql
-- 直接在数据库中创建用户
INSERT INTO users (
    username, 
    email, 
    password_hash, 
    display_name, 
    created_at, 
    updated_at
) VALUES (
    'newuser',
    'user@example.com',
    -- 密码: Test123456!
    -- 使用 Python: hashlib.sha256('Test123456!'.encode()).hexdigest()
    'b109f3bbbc244eb82441917ed06d618b9008dd09b3befd1b5e07394c706a8bb9',
    '新用户',
    NOW(),
    NOW()
);
```

## 📝 用户体验

### 登录页面提示

用户访问应用时会看到：

```
👋 欢迎使用 SupaWriter
AI驱动的智能写作平台

📧 邮箱登录
[邮箱输入框]
[密码输入框]
[记住我]
[🔐 登录]

💡 如需注册账号，请访问官网进行注册

---

🔐 第三方登录
[🔐 Google 登录]  [🔐 微信登录]
```

### 用户引导流程

1. **新用户访问应用** → 看到登录页面
2. **点击"访问官网"** → 跳转到官网注册页面
3. **在官网完成注册** → 收到确认邮件
4. **返回应用登录** → 使用注册的账号登录

## 🔒 安全考虑

### 优势

1. **集中管理**
   - 所有用户注册在官网统一处理
   - 便于实施统一的验证流程
   - 减少应用端的安全风险

2. **审核机制**
   - 官网可以实施人工或自动审核
   - 防止恶意注册和滥用
   - 控制用户增长速度

3. **数据一致性**
   - 单一入口确保数据一致
   - 避免重复注册
   - 便于用户信息管理

### 注意事项

1. **OAuth登录的特殊处理**
   - Google/微信首次登录仍会自动创建用户
   - 可选：要求OAuth用户也必须先在官网注册
   - 建议：保持OAuth自动创建，提升用户体验

2. **API安全**
   - 后端注册API应该有访问控制
   - 只允许官网后端调用
   - 实施API密钥或JWT认证

## 🚀 未来扩展

### 官网开发计划

**第一阶段：基础注册**
- [ ] 注册表单页面
- [ ] 邮箱验证功能
- [ ] 调用应用API创建用户
- [ ] 发送欢迎邮件

**第二阶段：增强功能**
- [ ] 手机号验证
- [ ] 实名认证（如需要）
- [ ] 邀请码机制
- [ ] 用户审核后台

**第三阶段：集成优化**
- [ ] 单点登录（SSO）
- [ ] 统一用户中心
- [ ] 订阅和付费管理

## 📞 技术支持

### 开发者接口

如需在官网中集成用户注册，请参考：

```python
# 推荐：创建专门的官网API端点
from utils.auth_v2 import AuthService
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/register', methods=['POST'])
def register_user():
    """官网注册API端点"""
    data = request.json
    
    # 1. 验证官网API密钥
    if not verify_api_key(request.headers.get('X-API-Key')):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # 2. 调用注册服务
    success, message = AuthService.register_with_email(
        username=data['username'],
        email=data['email'],
        password=data['password'],
        display_name=data.get('display_name')
    )
    
    # 3. 返回结果
    if success:
        return jsonify({'message': message}), 201
    else:
        return jsonify({'error': message}), 400
```

### 管理员工具

```bash
# 批量导入用户脚本（待开发）
python scripts/import_users.py --csv users.csv

# 手动创建单个用户
python scripts/create_user.py \
    --username newuser \
    --email user@example.com \
    --password SecurePass123!
```

## 📄 变更日志

### 2025-01-17
- ✅ 移除应用端注册功能
- ✅ 保留后端注册API
- ✅ 添加官网注册引导
- ✅ 更新相关文档

---

**注意：** 此策略适用于当前版本，后续可能根据业务需求调整。
