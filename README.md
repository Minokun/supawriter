# 超级写手 (SupaWriter)

**超级写手** 是一个集成了大模型、搜索引擎和多模态技术的智能写作平台，旨在通过自动化手段提升内容创作效率和质量。它不仅是一个文本生成工具，更是一个涵盖资料收集、信息整理、内容创作和多平台发布的全流程创作系统。

## 📋 功能概述

### 核心功能

1. **智能内容创作**
   - 基于多个搜索引擎自动查询并整合互联网资料
   - **双引擎搜索**：集成 SearXNG + Serper API，提供更全面的搜索覆盖
   - 智能分析和提取关键信息，构建文章框架
   - 根据用户需求生成定制化高质量内容
   - 支持多种写作风格和内容类型
   - 自动生成文章概要，提供整体内容预览

2. **多模态内容处理**
   - 智能图像识别和处理，自动为文章匹配相关图片
   - 图像内容理解和描述，增强文章可视化效果
   - 用户和文章特定的FAISS索引，确保图片数据隔离和准确匹配
   - 支持直接使用图片URL，无需本地存储
   - **防盗链优化**：智能处理 CSDN、知乎、阿里云等主流网站的图片防盗链，确保图片下载成功率

3. **内容创作导航中心**
   - 集成多种搜索引擎：SearXNG、秘塔AI搜索、Google等
   - 连接主流内容发布平台：微信公众号、头条号、百家号等
   - 提供AI视频创作工具链接：即梦、剪映等视频创作平台
   - 本地Markdown编辑器和内容管理工具

4. **多渠道认证系统**
   - **Google OAuth2**：基于 Streamlit 原生支持的 Google 账号登录
   - **微信开放平台**：支持微信扫码登录，适合国内用户
   - **本地账号**：传统用户名密码登录方式
   - 用户数据完全隔离，支持多账号切换

5. **用户系统与历史记录**
   - 多用户支持，数据隔离
   - 创作历史记录和数据分析
   - 个性化设置和偏好保存
   - 统一的HTML预览和下载界面

6. **全网热点追踪**
   - **多平台热搜聚合**：实时获取36Kr创投、百度热搜、微博热搜、抖音热搜榜单
   - **一键创作**：直接基于热点话题一键跳转到写作页面，自动填充主题和上下文
   - **实时更新**：采用混合数据获取策略（API/HTML解析），保障数据实时性和稳定性

## 🔧 技术特点

1. **多引擎搜索系统**
   - **SearXNG**：隐私保护的元搜索引擎，聚合多个搜索源
   - **Serper API**：Google 搜索 API，提供高质量的搜索结果
   - 自动合并和去重搜索结果，提供更全面的信息覆盖
   - 智能关键词优化，提高搜索相关性

2. **高效并发网页抽取**
   - 基于Playwright的异步网页内容获取
   - 可配置的并发爬虫数量（默认20个）
   - 智能超时处理和错误重试机制
   - 批次内URL去重，避免重复内容

3. **智能图像处理系统**
   - 支持多种VL模型：GLM-4.1v和Qwen-VL系列
   - 图像URL规范化和去重处理
   - 基于FAISS的图像相似度检索
   - 支持直接图片URL嵌入或多模态处理
   - **多网站防盗链支持**：
     - CSDN、知乎、简书、掘金
     - 微信公众号、阿里云 OSS/CDN
     - 51CTO、InfoQ、SegmentFault
     - 智能 Referer 选择和多策略重试机制

4. **用户和文章特定的数据隔离**
   - 每篇文章独立的FAISS索引
   - 基于用户名和文章ID的索引路径结构：`/data/faiss/{username}/{article_id}/`
   - 自动索引加载和回退机制
   - 多用户环境下的数据安全隔离

5. **可靠的错误处理**
   - 搜索结果为空的错误处理和提示
   - 网络请求超时保护
   - 详细的日志记录和状态追踪
   - 任务状态实时更新

## 💯 应用场景

1. **自媒体内容创作**
   - 快速生成高质量的平台文章
   - 多平台内容发布和管理
   - 图文结合的富媒体内容

2. **专业文档撰写**
   - 研究报告和行业分析
   - 技术文档和教程
   - 项目计划和商业提案

3. **教育内容开发**
   - 课程材料和教案
   - 学习指南和参考资料
   - 知识点总结和扩展阅读

4. **个人知识管理**
   - 信息收集和整理
   - 知识总结和归纳
   - 个人笔记和学习记录

## 💯 工作流程

```mermaid
flowchart TD
    A[用户输入文章主题] --> B[配置生成参数]
    B --> C[执行文章生成任务]
    C --> D[搜索引擎查询相关资料]
    D --> E{搜索结果是否为空?}
    E -- 是 --> F[报错并终止任务]
    E -- 否 --> G[并发爬取网页内容]
    G --> H[分析内容生成大纲]
    H --> I[根据大纲生成文章章节]
    
    subgraph 图片处理流程
        J[图片搜索与识别] --> K[创建用户和文章特定FAISS索引]
        K --> L[图片内容理解与匹配]
        L --> M[将图片嵌入到文章中]
    end
    
    I --> N{是否启用图片?}
    N -- 是 --> J
    N -- 否 --> O[生成最终文章]
    M --> O
    
    O --> P[添加文章概要]
    P --> Q[保存到历史记录]
    Q --> R[提供预览和编辑功能]
    R --> S[导出Markdown或HTML]
```

## 📊 系统架构

```mermaid
graph TD
    A[用户界面] --> B[Streamlit Web应用]
    
    subgraph 核心组件
        B --> C[文章生成引擎]
        B --> D[搜索引擎接口]
        B --> E[图像处理系统]
        B --> F[历史记录管理]
        B --> G[用户认证系统]
    end
    
    subgraph 外部服务
        D --> H[SearXNG]
        D --> I[Serper API]
        E --> J[GLM-4.1v]
        E --> K[Qwen-VL]
        C --> L[大语言模型API]
    end
    
    subgraph 数据存储
        M[FAISS索引] --> E
        N[用户配置] --> B
        O[历史记录] --> F
        P[HTML输出] --> B
    end
```

## 🔨️ 系统要求

- Python 3.8+
- 支持异步操作的现代浏览器
- 互联网连接
- 大语言模型API密钥（支持多种提供商）
- 视觉语言模型API密钥（用于图像处理）

## ⚙️ 配置说明

### 主要配置文件

- **`.streamlit/secrets.toml`**: 配置必要的API密钥和访问凭证
  ```toml
  # ========== 认证配置 ==========
  # Google OAuth2 配置（Streamlit 原生支持）
  # 申请地址: https://console.cloud.google.com/apis/credentials
  # 文档: https://docs.streamlit.io/develop/tutorials/sso
  [auth.google]
  client_id = "your_google_client_id.apps.googleusercontent.com"
  client_secret = "your_google_client_secret"
  
  # 微信开放平台 OAuth2 配置（可选）
  # 申请地址: https://open.weixin.qq.com/
  # 文档: https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
  [wechat]
  app_id = "your_wechat_app_id"           # 微信开放平台应用的 AppID
  app_secret = "your_wechat_app_secret"   # 微信开放平台应用的 AppSecret
  redirect_uri = "http://localhost:8501"  # 授权回调地址，需要在微信开放平台配置
  
  # ========== AI 模型配置 ==========
  # 大语言模型配置
  [openai]
  model = "gpt-4-turbo"
  base_url = "https://api.openai.com/v1"
  api_key = "your_openai_api_key"
  
  # 视觉语言模型配置
  [glm]
  model = "glm-4-vision"
  base_url = "https://open.bigmodel.cn/api/paas/v4"
  api_key = "your_glm_api_key"
  
  # Serper 搜索引擎 API（可选，提供额外的搜索结果）
  SERPER_API_KEY = "your_serper_api_key"
  ```

- **`settings.py`**: 系统全局设置
  ```python
  # 文章生成配置
  DEFAULT_SPIDER_NUM = 20  # 爬取网页数量默认值
  DEFAULT_ENABLE_IMAGES = True  # 是否自动插入相关图片
  DEFAULT_IMAGE_EMBEDDING_METHOD = 'multimodal'  # 图片嵌入方式: 'multimodal' 或 'direct_embedding'
  
  # 视觉语言模型配置
  PROCESS_IMAGE_TYPE = "glm"  # 使用的图像处理模型类型: "glm" 或 "qwen"
  
  # 嵌入服务配置
  EMBEDDING_TYPE = 'gitee'  # 可选: "gitee", "xinference", "jina"
  EMBEDDING_D = 2048  # 嵌入向量维度
  EMBEDDING_MODEL = 'jina-embeddings-v4'  # 嵌入模型名称
  
  # Serper 搜索引擎 API
  SERPER_API_KEY = st.secrets.get('SERPER_API_KEY')  # 从 secrets 读取
  ```

### 支持的模型和服务

- **大语言模型**: OpenAI, 文心一言, 通义千问, Xinference, Jina
- **视觉语言模型**: GLM-4.1v, Qwen-VL系列
- **搜索引擎**: SearXNG (聚合多源), Serper API (Google搜索), 秘塔AI搜索
- **嵌入服务**: Gitee, Xinference, Jina
- **图片CDN支持**: CSDN, 知乎, 简书, 掘金, 微信公众号, 阿里云OSS, 51CTO, InfoQ, SegmentFault

## 🖼️ 图片防盗链技术

系统实现了智能的图片防盗链处理机制，确保从各大网站抓取图片时的成功率。

### 支持的网站及策略

| 网站类型 | 域名特征 | Referer 设置 |
|---------|---------|-------------|
| CSDN | csdnimg.cn, csdn.net | https://blog.csdn.net/ |
| 知乎 | zhihu.com, zhimg.com | https://www.zhihu.com/ |
| 简书 | jianshu.com, jianshu.io | https://www.jianshu.com/ |
| 掘金 | juejin.cn, juejin.im | https://juejin.cn/ |
| 微信公众号 | mmbiz.qpic.cn | https://mp.weixin.qq.com/ |
| 阿里云 OSS | alicdn.com, aliyuncs.com | https://developer.aliyun.com/ |
| 51CTO | 51cto.com | https://www.51cto.com/ |
| InfoQ | infoq.cn, infoq.com | https://www.infoq.cn/ |
| SegmentFault | segmentfault.com | https://segmentfault.com/ |

### 技术实现

1. **智能 Referer 选择**：根据图片 URL 域名自动选择合适的 Referer
2. **浏览器 Headers 模拟**：完整模拟 Chrome 浏览器的请求头
3. **多策略重试**（embedding_utils.py）：
   - 策略1: 标准 HTTPS 请求
   - 策略2: 禁用 SSL 验证
   - 策略3: 使用图片域名作为 Referer
4. **SSL 验证控制**：针对证书问题自动禁用验证

### 应用场景

- **图片嵌入向量生成**：`utils/embedding_utils.py`
- **本地图片下载**：`utils/image_utils.py`
- **七牛云上传**：`utils/qiniu_utils.py`

## 💻 使用指南

### 快速开始

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   # 或使用 uv（更快）
   uv pip install -r requirements.txt
   ```

2. **配置API密钥**
   - 复制 `.streamlit/secrets.toml.example` 为 `.streamlit/secrets.toml`
   - 根据配置说明添加必要的API密钥
   - **可选**：配置 Serper API Key 以获得更多搜索结果

3. **配置认证系统（可选）**
   
   项目支持三种登录方式，可根据需求配置：
   
   **a) Google OAuth2 登录（推荐）**
   ```
   1. 访问 Google Cloud Console: https://console.cloud.google.com/
   2. 创建新项目或选择现有项目
   3. 启用 "Google+ API"
   4. 创建 OAuth 2.0 客户端 ID（应用类型：Web 应用）
   5. 添加授权重定向 URI: http://localhost:8501
   6. 将 Client ID 和 Client Secret 填入 secrets.toml 的 [auth.google] 部分
   ```
   
   **b) 微信开放平台登录**
   ```
   1. 访问微信开放平台: https://open.weixin.qq.com/
   2. 注册开发者账号并创建网站应用
   3. 填写应用信息，通过审核后获得 AppID 和 AppSecret
   4. 在"网站信息"中配置授权回调域（如: localhost 或你的域名）
   5. 将 AppID、AppSecret 和回调 URL 填入 secrets.toml 的 [wechat] 部分
   
   注意：
   - redirect_uri 必须与微信开放平台配置的回调域一致
   - 本地开发可使用 http://localhost:8501
   - 生产环境需要使用 https 和已备案的域名
   ```
   
   **c) 本地账号登录**
   - 无需额外配置，首次使用时注册即可

4. **启动应用**
   ```bash
   streamlit run web.py
   ```

### 文章生成流程

1. 登录应用或使用匿名模式
2. 输入文章主题或关键词
3. 选择生成参数（模型、并发数量、是否启用图片等）
4. 点击生成按钮，等待文章生成
5. 在预览界面查看和编辑生成的文章
6. 导出为Markdown或HTML格式

## 📚 完整文档导航

项目提供了完整的文档体系，涵盖快速入门、功能指南、架构设计、开发文档和故障排除等各个方面。

### 🚀 快速开始

| 文档 | 说明 | 链接 |
|------|------|------|
| **默认账号信息** | 数据库默认管理员账号和密码，首次登录必读 | [查看文档](docs/guides/default-account.md) |
| **认证系统快速入门** | 新版认证系统的快速使用指南，5分钟上手 | [查看文档](docs/guides/quickstart-auth-v2.md) |
| **UV 包管理器** | 使用 UV 快速安装依赖，比 pip 快 10-100 倍 | [查看文档](docs/guides/uv-quickstart.md) |
| **数据库配置** | PostgreSQL 数据库配置和连接指南 | [查看文档](docs/guides/database-config.md) |

### 📖 功能指南

#### 认证相关

| 文档 | 说明 | 链接 |
|------|------|------|
| **认证系统完整指南** | 多渠道认证系统（Google/微信/本地账号）详细说明 | [查看文档](docs/guides/authentication-v2.md) |
| **微信登录实现** | 微信开放平台登录集成的技术实现细节 | [查看文档](docs/guides/wechat-login.md) |
| **微信登录配置** | 配置微信开放平台和授权回调的完整步骤 | [查看文档](docs/guides/wechat-login-setup.md) |
| **注册策略说明** | 用户注册和账号管理策略，了解系统设计思路 | [查看文档](docs/guides/registration-policy.md) |

#### 数据库相关

| 文档 | 说明 | 链接 |
|------|------|------|
| **数据库配置指南** | PostgreSQL 完整配置说明，包括本地和远程部署 | [查看文档](docs/guides/database-config.md) |
| **默认账号信息** | 数据库初始化的默认管理员账号和安全建议 | [查看文档](docs/guides/default-account.md) |

### 🏗️ 架构文档

| 文档 | 说明 | 链接 |
|------|------|------|
| **Streamlit 架构分析** | 深入分析 Streamlit 的并发性能和架构特点 | [查看文档](docs/architecture/streamlit-architecture-analysis.md) |
| **前端网站方案** | 混合架构方案设计，NextJS + Streamlit 方案探讨 | [查看文档](docs/architecture/frontend-proposal.md) |

### 🔧 开发文档

| 文档 | 说明 | 链接 |
|------|------|------|
| **认证系统架构** | 认证系统的技术架构和实现细节 | [查看文档](docs/development/authentication.md) |
| **实现总结** | 主要功能的实现总结和技术要点 | [查看文档](docs/development/implementation-summary.md) |

### 🆘 故障排除

| 文档 | 说明 | 链接 |
|------|------|------|
| **数据库连接问题修复** | 常见数据库连接错误的诊断和解决方案 | [查看文档](docs/troubleshooting/database-connection-fix.md) |

### 📝 变更日志

| 文档 | 说明 | 链接 |
|------|------|------|
| **注册功能移除日志** | V2 版本中注册功能的变更记录和原因说明 | [查看文档](docs/CHANGELOG_REGISTRATION_REMOVED.md) |

### 📁 文档索引

完整的文档目录和组织结构说明，请访问：[**文档中心**](docs/README.md)

## 👨‍💻 开发团队

超级写手由一个致力于AI辅助创作的团队开发，我们的目标是让内容创作变得更加高效、智能和有趣。

## 📦 最近更新

### v2.2 (2025-11)

- ✅ **全网热点追踪**：新增"全网热点"页面，聚合36Kr、百度、微博、抖音四大热搜源
- ✅ **创作工作流打通**：
  - 推文选题 -> 一键生成文章
  - 热门话题 -> 一键生成文章
  - 自动传递主题、风格和上下文信息
- ✅ **数据获取优化**：
  - 实现了针对微博、36Kr的增强型HTML解析策略，解决API权限问题
  - 增加了抖音热搜API接入

### v2.1 (2025-10)

- ✅ **多渠道认证系统**：新增微信开放平台登录支持
  - 支持 Google OAuth2 登录
  - 支持微信扫码登录（适合国内用户）
  - 支持传统本地账号登录
  - 用户数据完全隔离，多账号自由切换
- ✅ **用户体验优化**：登录页面支持显示微信头像和用户信息

### v2.0 (2025-10)

- ✅ **双引擎搜索**：集成 SearXNG + Serper API，提供更全面的搜索结果
- ✅ **图片防盗链优化**：支持 9 大主流网站的图片下载（CSDN、知乎、阿里云等）
- ✅ **智能 Referer 策略**：根据不同网站自动选择最佳 Referer
- ✅ **多策略重试机制**：确保图片下载成功率
- ✅ **包管理优化**：支持使用 uv 快速安装依赖

## 🗄️ 数据库部署与迁移

### PostgreSQL 服务器部署

项目提供了完整的 PostgreSQL 数据库部署方案，支持将数据存储到远程服务器。

**服务器信息**：
- 服务器地址：`122.51.24.120`
- 数据库端口：`5432`
- 数据库名：`supawriter`

**快速部署**：
```bash
# 1. 配置环境变量
cd deployment
cp .env.example .env
vim .env  # 修改数据库密码

# 2. 一键部署到服务器
cd scripts
./quick-deploy.sh
```

详细部署说明请参考：[deployment/README.md](deployment/README.md)

### 数据迁移到 PostgreSQL

将本地 JSON 数据迁移到服务器的 PostgreSQL 数据库：

**快速迁移**：
```bash
# 1. 配置迁移环境
cd deployment/migrate
cp .env.migration.example .env.migration
vim .env.migration  # 设置数据库密码

# 2. 运行迁移脚本（交互式）
./quick_migrate.sh

# 或直接运行 Python 脚本
python deployment/migrate/migrate_to_pgsql.py --host 122.51.24.120 --password YOUR_PASSWORD
```

**迁移的数据类型**：
- **文章数据**：用户创作的所有文章内容、配置和元数据
- **聊天历史**：AI 对话会话记录
- **用户配置**：个性化设置和偏好

**安全特性**：
- 支持数据增量迁移，避免重复
- 自动处理数据冲突
- 详细的迁移日志和状态反馈
- 支持单用户或全量迁移

详细迁移说明请参考：[deployment/migrate/README.md](deployment/migrate/README.md)

## 📦 未来规划

1. 支持更多搜索引擎和API源
2. 增强视频内容的抓取和处理能力
3. 支持更多内容平台的直接发布
4. 提供更多自定义写作风格和模板
5. 开发API接口，支持第三方集成
6. 增加协作功能，支持团队创作
7. 优化AI模型的响应速度和质量
8. 完善 PostgreSQL 数据层，支持云端数据同步

## 📓 贡献指南

欢迎对超级写手项目进行贡献！以下是参与开发的步骤：

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📃 许可证

本项目采用MIT许可证，详见LICENSE文件。

---