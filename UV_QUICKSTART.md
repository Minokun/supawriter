# UV 快速开始指南

## 🚀 一键迁移

```bash
./migrate_to_uv.sh
```

脚本会自动：
- ✅ 备份当前环境
- ✅ 创建 UV 虚拟环境（.venv）
- ✅ 安装所有依赖
- ✅ 安装 Playwright 浏览器
- ✅ 提供清理旧环境选项

## 📋 手动步骤（如果需要）

### 1. 创建虚拟环境

```bash
uv venv
```

### 2. 安装依赖

```bash
# 推荐方式（最快）
uv sync

# 或使用 pyproject.toml
uv pip install -e .

# 或使用 requirements.txt（兼容）
uv pip install -r requirements.txt
```

### 3. 安装 Playwright 浏览器

```bash
uv run playwright install chromium
```

### 4. 运行应用

```bash
# 使用 uv run（无需激活环境）
uv run streamlit run web.py

# 或传统方式
source .venv/bin/activate
streamlit run web.py
```

## ⚡️ 常用命令速查

### 依赖管理

```bash
uv add requests              # 添加依赖
uv add --dev pytest          # 添加开发依赖
uv remove requests           # 删除依赖
uv pip list                  # 列出所有包
uv tree                      # 显示依赖树
```

### 运行命令

```bash
uv run python script.py      # 运行脚本
uv run streamlit run web.py  # 运行 Streamlit
uv run pytest                # 运行测试
```

### 环境管理

```bash
uv sync                      # 同步依赖（生产+开发）
uv sync --no-dev             # 仅生产依赖
uv lock                      # 生成锁文件
uv lock --upgrade            # 更新所有依赖
```

## 🔄 与 pip/venv 对比

| 任务 | pip/venv | uv |
|------|----------|-----|
| 创建环境 | `python -m venv venv`<br>`source venv/bin/activate` | `uv venv` |
| 安装依赖 | `pip install -r requirements.txt` | `uv sync` |
| 添加包 | `pip install pkg`<br>手动更新 requirements.txt | `uv add pkg` |
| 运行命令 | 必须先激活环境 | `uv run command` |
| 速度 | 慢 ⏱ | 快 🚀 (10-100倍) |

## 📦 项目文件说明

```
supawriter/
├── .venv/              # UV 虚拟环境（新）
├── venv/               # 旧虚拟环境（可删除）
├── pyproject.toml      # 项目配置（主文件）✨
├── uv.lock            # 依赖锁定（自动生成）🔒
├── requirements.txt    # 兼容模式保留
├── .python-version     # Python 版本
└── .gitignore         # 已更新
```

## ❓ 常见问题

### Q: 需要激活虚拟环境吗？
**A**: 不需要！使用 `uv run` 会自动使用正确的环境。

```bash
# 传统方式（需要激活）
source .venv/bin/activate
streamlit run web.py

# UV 方式（无需激活）
uv run streamlit run web.py
```

### Q: 如何回退到传统方式？
**A**: 保留了 requirements.txt 和备份文件：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_full_backup.txt
```

### Q: uv.lock 应该提交到 Git 吗？
**A**: 是的！这确保团队使用完全相同的依赖版本。

### Q: 如何在 Docker 中使用？
**A**: 参考 UV_MIGRATION.md 的 Docker 部分。

### Q: 旧的 venv 目录可以删除吗？
**A**: 确认新环境工作正常后可以删除：

```bash
rm -rf venv
```

## 🎯 最佳实践

1. ✅ **使用 `uv run`**: 避免手动激活环境
2. ✅ **提交 `uv.lock`**: 确保团队环境一致
3. ✅ **使用 `.venv`**: 标准虚拟环境目录名
4. ✅ **分离开发依赖**: 使用 `--dev` 标志
5. ❌ **不要混用**: 不要同时使用 pip 和 uv

## 📚 进一步学习

- **完整迁移指南**: `UV_MIGRATION.md`
- **UV 官方文档**: https://github.com/astral-sh/uv
- **项目配置**: 查看 `pyproject.toml`

## 🆘 需要帮助？

```bash
# 查看 UV 帮助
uv --help
uv add --help
uv run --help

# 清除缓存（如遇问题）
uv cache clean
```

---

**提示**: UV 速度快、简单、现代化。一旦习惯，你会发现比传统方式更高效！🚀
