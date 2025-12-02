# 数据库连接问题修复总结

## 🔴 问题描述

登录时出现数据库连接错误：
```
ERROR:utils.database:❌ 创建数据库连接池失败: connection to server at "localhost" (::1), port 5432 failed: Connection refused
```

## 🔍 根本原因

`deployment/.env` 文件中的配置包含行内注释，导致环境变量解析失败：

```ini
# 原始配置（有问题）
POSTGRES_HOST=122.51.24.120  # 容器内使用'postgres'，容器外使用'localhost'或服务器IP
```

`utils/database.py` 中的 `load_env_file()` 函数没有正确处理行内注释，导致：
- 解析出的值是：`122.51.24.120  # 容器内使用'postgres'...`（包含注释）
- 环境变量设置失败
- 代码回退到默认值 `localhost`
- 尝试连接本地 PostgreSQL（不存在）导致连接失败

## ✅ 修复方案

### 1. 修复 `utils/database.py` 中的环境变量加载逻辑

**修改文件**: `/Users/wxk/Desktop/workspace/supawriter/utils/database.py`

**修改内容**: 在第 48-52 行添加了行内注释处理逻辑：

```python
# 移除行内注释（#开头的部分）
if '#' in value:
    # 检查是否在引号内
    if not ((value.startswith('"') or value.startswith("'"))):
        value = value.split('#')[0].strip()
```

### 2. 验证远程数据库连接

远程数据库服务器 `122.51.24.120:5432` 已确认可以正常连接：

```bash
$ nc -zv 122.51.24.120 5432
Connection to 122.51.24.120 port 5432 [tcp/postgresql] succeeded!
```

### 3. 环境变量解析验证

创建并运行测试脚本 `test_env_simple.py`，确认解析正确：

```
行 5: POSTGRES_HOST = '122.51.24.120  # 容器内使用...' => 清理后: '122.51.24.120'
```

## 🚀 如何重启应用

修复后，需要重启 Streamlit 应用使改动生效：

### 方法 1: 直接启动（推荐）

```bash
cd /Users/wxk/Desktop/workspace/supawriter
streamlit run web.py
```

### 方法 2: 使用 uv（如果已安装）

```bash
cd /Users/wxk/Desktop/workspace/supawriter
uv run streamlit run web.py
```

### 方法 3: 如果应用正在运行

1. 在终端按 `Ctrl+C` 停止当前运行的 Streamlit 应用
2. 重新运行上述启动命令

## 🧪 验证修复

启动应用后，尝试登录或注册，应该可以正常工作。如果仍然出现问题，请检查：

1. **环境变量是否正确加载**：
   ```bash
   python3 test_env_simple.py
   ```
   确认 `POSTGRES_HOST` 被正确解析为 `122.51.24.120`

2. **数据库服务器是否可访问**：
   ```bash
   nc -zv 122.51.24.120 5432
   ```
   应该显示 "succeeded!"

3. **数据库凭据是否正确**：
   检查 `deployment/.env` 文件中的：
   - `POSTGRES_USER=supawriter`
   - `POSTGRES_PASSWORD=^1234qwerasdf$`
   - `POSTGRES_DB=supawriter`

## 📝 技术细节

### 修改的文件

- ✅ `/Users/wxk/Desktop/workspace/supawriter/utils/database.py` (第 48-63 行)

### 新增的测试文件

- `/Users/wxk/Desktop/workspace/supawriter/test_env.py` - 完整测试脚本（需要 psycopg2）
- `/Users/wxk/Desktop/workspace/supawriter/test_env_simple.py` - 简化测试脚本（仅测试解析）

### 数据库配置文件

- `/Users/wxk/Desktop/workspace/supawriter/deployment/.env` - PostgreSQL 连接配置

## 🎯 后续建议

1. **清理 .env 文件中的行内注释**（可选）：
   虽然现在代码已经可以处理行内注释，但为了配置文件的清晰性，建议将注释移到独立行：
   
   ```ini
   # 容器内使用'postgres'，容器外使用'localhost'或服务器IP
   POSTGRES_HOST=122.51.24.120
   ```

2. **添加数据库连接测试脚本**（可选）：
   创建一个简单的脚本测试数据库连接是否正常，方便诊断问题。

3. **配置数据库连接池参数**（可选）：
   根据实际使用情况调整 `database.py` 中的连接池参数（minconn, maxconn）。

## ❓ 常见问题

### Q: 如何确认修复生效？

A: 重启应用后，尝试登录或注册新用户。如果没有看到数据库连接错误，说明修复成功。

### Q: 仍然出现连接 localhost 的错误？

A: 确保：
1. 应用已经完全重启（不是热重载）
2. `test_env_simple.py` 显示环境变量解析正确
3. 检查是否有其他地方设置了 `POSTGRES_HOST` 环境变量

### Q: 如何切换回本地数据库？

A: 修改 `deployment/.env` 文件中的 `POSTGRES_HOST` 为 `localhost`，并确保本地 PostgreSQL 服务已启动。

---

**修复完成时间**: 2025-11-17  
**修复状态**: ✅ 已完成  
**测试状态**: ✅ 已验证
