# 项目文件结构清理方案

## 当前问题诊断

### 1. 文档散乱 📄
根目录有 4 个文档文件，应该统一到 `docs/` 目录：
- `UV_QUICKSTART.md` → `docs/guides/uv-quickstart.md`
- `WECHAT_LOGIN_IMPLEMENTATION.md` → `docs/guides/wechat-login.md`
- `README.en.md` → 保留在根目录（国际化需要）
- `README.md` → 保留在根目录（项目主文档）

### 2. 空目录冗余 📁
- `/images/` - 完全空目录，应删除
- `/sources/images/` - 只有 .DS_Store，应检查是否有用

### 3. 系统垃圾文件 🗑️
- `/data/.DS_Store` - macOS 系统文件
- `/sources/.DS_Store` - macOS 系统文件
- 虽然在 .gitignore，但仍存在本地

### 4. scripts 目录结构 🔧
- `README_DAILY_NEWS.md` 命名不规范
- 测试脚本很多，应分类

### 5. data 目录混乱 💾
```
data/
├── .DS_Store          ❌ 系统文件
├── chat_history/      ✅ 业务数据
├── config/            ✅ 配置
├── daily_news/        ✅ 业务数据
├── faiss/             ✅ 索引数据
├── history/           ✅ 历史记录
├── html/              ✅ 输出文件
├── sessions/          ✅ 会话数据
├── supawriter.db      ✅ 数据库
└── users.pkl          ⚠️ 应迁移到数据库
```

## 清理方案

### 第一步：整理文档结构

#### 新的 docs/ 目录结构
```
docs/
├── README.md                          # 文档导航
├── guides/                            # 使用指南
│   ├── getting-started.md            # 快速开始（新建）
│   ├── uv-quickstart.md              # UV 包管理器指南（移动）
│   ├── wechat-login.md               # 微信登录实现（移动）
│   └── deployment.md                 # 部署指南（新建）
├── architecture/                      # 架构文档
│   ├── overview.md                   # 架构概览（新建）
│   ├── streamlit-analysis.md         # Streamlit 分析（已有）
│   └── frontend-proposal.md          # 前端方案（已有）
├── api/                               # API 文档
│   └── README.md                     # API 接口说明（新建）
└── development/                       # 开发文档
    ├── authentication.md             # 认证系统（已有）
    └── contributing.md               # 贡献指南（新建）
```

### 第二步：重组 scripts/ 目录

```
scripts/
├── README.md                          # 脚本说明
├── daily_news/                        # 每日新闻相关
│   ├── generate_daily_news.py
│   ├── daily_news_cron.py
│   └── run_daily_news.sh
├── tests/                             # 测试脚本
│   ├── test_ddgs_serper.py
│   ├── test_llm.py
│   ├── test_news_api.py
│   ├── test_qiniu_streamlit.py
│   ├── test_serper_search.py
│   ├── test_time_filter.py
│   └── test_wechat_oauth.py
└── tools/                             # 工具脚本
    └── verify_news_fix.py
```

### 第三步：清理系统文件

**删除的文件**：
```bash
# 删除 macOS 系统文件
find . -name ".DS_Store" -delete

# 删除空目录
rmdir images/
```

**保留但规范化**：
```bash
# sources/ 目录应改名为 assets/ 并整理
sources/images/ → assets/images/     # 如果有用的话
```

### 第四步：data/ 目录规范化

**添加 .gitkeep 文件**（确保空目录被 Git 追踪）：
```bash
# 在需要的空目录中添加 .gitkeep
touch data/chat_history/.gitkeep
touch data/config/.gitkeep
touch data/daily_news/.gitkeep
# ... 其他目录
```

**添加 data/README.md** 说明数据目录结构：
```markdown
# 数据目录说明

本目录存储应用运行时数据，已在 .gitignore 中排除。

## 目录结构
- chat_history/  聊天历史记录
- config/        用户配置文件
- daily_news/    每日新闻生成结果
- faiss/         FAISS 向量索引
- history/       文章历史记录
- html/          生成的 HTML 文件
- sessions/      用户会话数据
- supawriter.db  SQLite 数据库
- users.pkl      用户数据（待迁移到数据库）
```

### 第五步：优化根目录结构

**最终根目录**：
```
supawriter/
├── .git/
├── .github/                    # GitHub Actions（可选）
├── .streamlit/
├── .venv/
├── auth_pages/                 ✅ 认证页面
├── data/                       ✅ 数据目录
├── deployment/                 ✅ 部署脚本
├── docs/                       ✅ 文档（重组后）
├── page/                       ✅ 应用页面
├── scripts/                    ✅ 脚本（重组后）
├── templates/                  ✅ 模板文件
├── utils/                      ✅ 工具函数
├── .gitignore
├── .python-version
├── main.py
├── page_settings.py
├── pyproject.toml
├── README.md                   ✅ 主文档
├── README.en.md                ✅ 英文文档
├── requirements.txt
├── settings.py
├── uv.lock
└── web.py                      ✅ 入口文件
```

**删除/移动的文件**：
- ❌ `images/` 目录（空目录，删除）
- ❌ `sources/` 目录（改为 `assets/` 或删除）
- ➡️ `UV_QUICKSTART.md` → `docs/guides/uv-quickstart.md`
- ➡️ `WECHAT_LOGIN_IMPLEMENTATION.md` → `docs/guides/wechat-login.md`

## 执行清单

### 自动化清理脚本

```bash
#!/bin/bash
# cleanup.sh - 项目清理脚本

set -e

echo "🧹 开始清理项目..."

# 1. 删除系统垃圾文件
echo "删除 .DS_Store 文件..."
find . -name ".DS_Store" -delete

# 2. 创建新的文档目录结构
echo "创建文档目录结构..."
mkdir -p docs/guides
mkdir -p docs/architecture
mkdir -p docs/api
mkdir -p docs/development

# 3. 移动文档文件
echo "移动文档文件..."
[ -f UV_QUICKSTART.md ] && mv UV_QUICKSTART.md docs/guides/uv-quickstart.md
[ -f WECHAT_LOGIN_IMPLEMENTATION.md ] && mv WECHAT_LOGIN_IMPLEMENTATION.md docs/guides/wechat-login.md

# 4. 重组 scripts 目录
echo "重组 scripts 目录..."
mkdir -p scripts/daily_news
mkdir -p scripts/tests
mkdir -p scripts/tools

# 移动每日新闻脚本
mv scripts/generate_daily_news.py scripts/daily_news/ 2>/dev/null || true
mv scripts/daily_news_cron.py scripts/daily_news/ 2>/dev/null || true
mv scripts/run_daily_news.sh scripts/daily_news/ 2>/dev/null || true
mv scripts/README_DAILY_NEWS.md scripts/daily_news/README.md 2>/dev/null || true

# 移动测试脚本
mv scripts/test_*.py scripts/tests/ 2>/dev/null || true

# 移动工具脚本
mv scripts/verify_news_fix.py scripts/tools/ 2>/dev/null || true

# 5. 删除空目录
echo "删除空目录..."
[ -d images ] && rmdir images 2>/dev/null || true

# 6. 添加 data 说明文档
echo "创建 data/README.md..."
cat > data/README.md << 'EOF'
# 数据目录说明

本目录存储应用运行时数据，已在 .gitignore 中排除。

## 目录结构
- `chat_history/`  聊天历史记录
- `config/`        用户配置文件
- `daily_news/`    每日新闻生成结果
- `faiss/`         FAISS 向量索引
- `history/`       文章历史记录
- `html/`          生成的 HTML 文件
- `sessions/`      用户会话数据
- `supawriter.db`  SQLite 数据库
- `users.pkl`      用户数据（待迁移到数据库）

## 注意事项
- 所有数据文件都在 `.gitignore` 中排除
- 定期备份重要数据
- 建议将 `users.pkl` 迁移到 PostgreSQL
EOF

# 7. 创建 docs 导航文档
echo "创建 docs/README.md..."
cat > docs/README.md << 'EOF'
# SupaWriter 文档中心

## 📚 文档导航

### 快速开始
- [快速入门指南](guides/getting-started.md)
- [UV 包管理器使用](guides/uv-quickstart.md)
- [部署指南](guides/deployment.md)

### 功能指南
- [微信登录实现](guides/wechat-login.md)
- [认证系统说明](development/authentication.md)

### 架构文档
- [系统架构概览](architecture/overview.md)
- [Streamlit 架构分析](architecture/streamlit-architecture-analysis.md)
- [前端网站方案](architecture/frontend-proposal.md)

### API 文档
- [API 接口说明](api/README.md)

### 开发文档
- [贡献指南](development/contributing.md)
- [认证系统](development/authentication.md)
EOF

echo "✅ 清理完成！"
echo ""
echo "📊 清理统计："
echo "  - 已删除 .DS_Store 文件"
echo "  - 已重组 docs/ 目录"
echo "  - 已重组 scripts/ 目录"
echo "  - 已删除空目录"
echo ""
echo "⚠️  请手动检查："
echo "  - sources/ 目录是否需要保留"
echo "  - scripts/ 中的文件移动是否正确"
echo "  - 需要创建缺失的文档文件"
```

### 手动任务清单

- [ ] 运行 `cleanup.sh` 脚本
- [ ] 检查 `sources/` 目录内容，决定保留或删除
- [ ] 更新 `docs/README.md` 中的文档链接
- [ ] 创建缺失的文档文件：
  - [ ] `docs/guides/getting-started.md`
  - [ ] `docs/guides/deployment.md`
  - [ ] `docs/architecture/overview.md`
  - [ ] `docs/api/README.md`
  - [ ] `docs/development/contributing.md`
- [ ] 更新主 `README.md` 中的文档链接
- [ ] 提交 Git commit：`git commit -m "chore: reorganize project structure"`

## 预期效果

### 清理前 ❌
```
✗ 根目录有 4 个 MD 文件
✗ 空目录 images/
✗ .DS_Store 系统文件
✗ scripts/ 目录混乱
✗ 文档分散在多处
```

### 清理后 ✅
```
✓ 根目录只有主 README
✓ 文档统一在 docs/，分类清晰
✓ scripts/ 按功能分类
✓ 无系统垃圾文件
✓ 目录结构清晰易维护
```

## 维护建议

1. **文档优先**：每个新功能都应更新相应文档
2. **定期清理**：每月运行一次 `find . -name ".DS_Store" -delete`
3. **脚本分类**：新脚本按功能放入对应目录
4. **数据迁移**：逐步将文件存储迁移到数据库

---

**准备好执行清理了吗？我可以帮你：**
1. 创建 `cleanup.sh` 脚本
2. 逐步执行清理步骤
3. 补充缺失的文档
