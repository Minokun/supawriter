# 一键发布功能设计

## 背景

历史记录页面每篇文章缺少快捷发布到多平台的入口。用户需要手动转换格式、复制内容、打开各平台发布页，流程繁琐。

## 需求

1. 历史页面每篇文章卡片新增「发布」按钮
2. 点击后弹出 PublishModal，支持多选发布平台
3. 每个平台独立操作：复制标题、复制格式化内容（HTML/MD/纯文本）、打开发布页
4. 底部提供「复制标题」和「全部打开」快捷操作
5. 支持平台：微信公众号、知乎、小红书、CSDN、百家号、知识星球、今日头条

## 约束

- 不做平台 API 对接，仅跳转发布页 + 剪贴板复制
- 复用现有 `platform_converter.py` 格式转换逻辑
- 复用现有 `clipboard.ts` 富文本复制工具
- 新增 CSDN、百家号、知识星球三个平台的格式转换

## 成功标准

- 用户在历史页面点击发布按钮 → 弹窗选择平台 → 一键复制+打开 → 粘贴发布
- 整个流程 < 3 次点击完成单平台发布
- 支持 7 个平台的内容格式转换

## 详细设计

### 后端改动

#### 1. 扩展 `utils/platform_converter.py`

新增 3 个平台转换函数：

- `_convert_csdn(content, topic)` → Markdown（h1→h2，添加分类标签建议）
- `_convert_baijiahao(content)` → HTML（短段落阅读样式）
- `_convert_zsxq(content)` → Markdown（知识星球原始 Markdown）

更新 `SUPPORTED_PLATFORMS` 集合和 `convert_to_platform()` 分发逻辑。

#### 2. 无需新 API endpoint

现有 `POST /api/v1/articles/convert/platform` 已支持动态 platform 参数，前端传入新平台名即可。

### 前端改动

#### 3. 新建 `PublishModal` 组件

路径：`frontend/src/components/writer/PublishModal.tsx`

Props：
```typescript
interface PublishModalProps {
  article: Article;
  open: boolean;
  onClose: () => void;
}
```

内部结构：
- 平台配置常量 `PLATFORMS`：名称、图标、格式类型、发布页 URL
- 复选框多选平台
- 每个平台行：平台名 + 复制按钮 + 打开发布页按钮
- 底部操作栏：复制标题 | 全部打开选中平台

#### 4. 修改历史页面

在 `frontend/src/app/history/page.tsx` 中：
- 新增 `publishArticle` state
- 在文章卡片操作按钮组中加入「发布」按钮（Send/SendHorizontal 图标）
- 引入 PublishModal 组件

### 平台发布页 URL 映射

| 平台 | 发布页 URL | 内容格式 |
|------|-----------|---------|
| 微信公众号 | `https://mp.weixin.qq.com/` | HTML (rich_text) |
| 知乎 | `https://zhuanlan.zhihu.com/write` | Markdown (plain_text) |
| 小红书 | `https://creator.xiaohongshu.com/publish/publish` | 纯文本 (plain_text) |
| CSDN | `https://mp.csdn.net/mp_blog/creation/editor` | Markdown (plain_text) |
| 百家号 | `https://baijiahao.baidu.com/builder/rc/edit` | HTML (rich_text) |
| 知识星球 | `https://wx.zsxq.com/` | Markdown (plain_text) |
| 今日头条 | `https://mp.toutiao.com/profile_v4/graphic/articles` | HTML (rich_text) |

## Design Documents

- [BDD Specifications](./bdd-specs.md) - Behavior scenarios and testing strategy
- [Architecture](./architecture.md) - System architecture and component details
- [Best Practices](./best-practices.md) - Security, performance, and code quality guidelines
