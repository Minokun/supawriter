# 前端体验与信息架构审计（2026-03-28）

审计范围：`frontend` 本地站点的页面可达性、按钮跳转、权限一致性、功能合理性、开发/生产运行表现。

## 已确认的运行问题

### P0：开发模式不稳定
- 开发模式下 `/`、`/auth/signin`、`/hotspots` 间歇性触发 React Client Manifest 报错并出现空白页/500。
- 生产构建可通过，问题更像 `next dev` 下的 RSC/bundler 缓存链路异常。
- 相关入口：
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/layout.tsx`
  - `frontend/src/app/auth/signin/page.tsx`
  - `frontend/src/app/hotspots/page.tsx`

### P1：死链与无效链接
- 登录页“忘记密码？”指向不存在的 `/auth/forgot-password`。
- 登录页与注册页底部“服务条款 / 隐私政策”仍为 `#` 占位。
- AI 导航页内链 `/ddgs-search` 不存在于当前 Next 路由中。
- 相关文件：
  - `frontend/src/app/auth/signin/page.tsx`
  - `frontend/src/app/auth/register/page.tsx`
  - `frontend/src/app/ai-navigator/page.tsx`

### P1：后端地址假设过强
- 热点代理接口默认回源 `http://backend:8000`，在本地非 Docker 环境会 `ENOTFOUND backend`。
- 导致 `/hotspots` 在生产模式下页面能打开，但数据实际不可用。
- 相关文件：
  - `frontend/src/lib/server-backend-url.ts`
  - `frontend/src/app/api/hotspots/v2/latest/[source]/route.ts`
  - `frontend/src/app/api/hotspots/v2/sources/route.ts`

### P2：错误态表达不足
- `/pricing` 后端不可达时主体内容接近空白，仅 toast 提示“加载定价信息失败”。
- 登录/注册页在后端不可达时能提示“网络错误，请稍后重试”，表现尚可。

## 权限与跳转一致性问题

### 根路由策略不合理
- `/` 直接重定向到受保护的 `/workspace`。
- 未登录用户首次访问会马上被送到登录页，缺少产品介绍、功能说明或转化入口。
- `/auth/error` 页上的“返回首页”实际也会走到 `/`，随后再次进入受保护路径，异常恢复链路不顺畅。
- 相关文件：`frontend/src/app/page.tsx`

### 鉴权策略混乱
- 通过 middleware 强制登录的页面：
  - `/workspace`
  - `/writer`
  - `/ai-assistant`
  - `/ai-navigator`
  - `/tweet-topics`
  - `/rewrite`
  - `/history`
  - `/news`
  - `/community`
  - `/settings`
- 允许直接打开、但页面内再提示“请先登录”的页面：
  - `/account`
  - `/agent`
  - `/dashboard`
  - `/batch`
- 公开但强依赖后端的页面：
  - `/pricing`
  - `/hotspots`
- 结果是同类功能访问体验不一致，用户难以预测“点进去会看到什么”。
- 相关文件：`frontend/src/middleware.ts`

### 导航与实际能力不匹配
- 顶部导航直接暴露“社区管理”，但页面仍是“开发中”占位。
- “创作中心”里同时有“超能写手 / 批量生成 / 写作Agent / 文章再创作 / 历史记录”，但其中部分页面尚未可用或强依赖会员与后端。
- 导航信息密度偏高，容易让用户误以为所有入口都已成熟可用。
- 相关文件：
  - `frontend/src/components/layout/Navigation.tsx`
  - `frontend/src/app/community/page.tsx`
  - `frontend/src/app/rewrite/page.tsx`

## 功能合理性 / 信息架构问题

### 1. `workspace` 与 `writer` 角色重叠
- `/workspace` 本质是功能入口页，只展示 3 张卡片与热点摘要。
- `/writer` 才是真正的核心创作工作台。
- 当前根路由先跳 `/workspace`，再让用户二次点击进入 `/writer`，增加一步无必要跳转。
- 若“写作”是核心任务，可考虑：
  - 未登录：首页展示产品介绍 + CTA；
  - 已登录：直接进入 `/writer`；
  - `/workspace` 下沉为仪表盘或精选推荐页。

### 2. `ai-navigator` 功能边界过宽
- 页面更像“收藏夹/资源导航站”，混合了搜索工具、内容平台、视频工具、模型平台、算力平台。
- 与站内核心任务（写作、热点、选题、生成）弱耦合。
- 还包含外链到大量第三方站点，维护成本高、失效率高、价值难统一。
- 若保留，建议转为“工具资源库”；若不保留，可从主导航降级。
- 相关文件：`frontend/src/app/ai-navigator/page.tsx`

### 3. `community` / `rewrite` 当前没有产品价值闭环
- `/community` 仅“开发中”，但已经挂在主导航。
- `/rewrite` 仅“开发中”，却仍作为创作主入口之一。
- 这类未完成功能出现在一级导航，会直接稀释主产品可信度。

### 4. `agent` / `batch` / `dashboard` 面向进阶用户，却放在强曝光导航
- 三者更像进阶功能或会员功能。
- 当前顶部导航一级直出“数据看板”，子菜单直出“批量生成 / 写作Agent”，但免费或未登录用户进入后往往只看到限制提示。
- 更适合放到：
  - “工作台 / 高级功能”
  - 会员升级页内做功能对比
  - 权限足够时再显示

### 5. “社区管理”命名不准确
- 页面文案写的是“管理和发布文章到社区”，但实际功能不存在。
- “社区管理”会让用户以为有审核、发布、成员、评论等后台能力。
- 若未来只是内容分发，建议命名为“内容发布”或“渠道发布”。

## 按钮 / 路由审计

### 已确认异常
- `/auth/signin` → “忘记密码？” → 404
- `/ai-navigator` → `/ddgs-search` → 路由不存在

### 已确认可用但体验待优化
- `/workspace` → `/ai-assistant`、`/writer`、`/rewrite`
  - 其中 `/rewrite` 虽可跳转，但目标页仍是“开发中”。
- `/workspace` → `/hotspots`
  - 页面可开，但数据受后端配置影响。
- `/dashboard`、`/agent`、`/settings/alerts`
  - 存在“升级会员”按钮，逻辑上合理，但需要先保证功能说明足够清晰。

## 页面状态分级建议

### 建议保留为一级核心
- `/writer`
- `/ai-assistant`
- `/tweet-topics`
- `/hotspots`（前提是数据源稳定）

### 建议改为二级入口 / 会员入口
- `/agent`
- `/batch`
- `/dashboard`
- `/settings/alerts`

### 建议暂时下线或隐藏
- `/community`
- `/rewrite`
- `/ai-navigator`（若暂未打磨成产品化资源库）

### 建议重构
- `/workspace`
- `/pricing`
- `/`

## 下一步建议

1. 先修死链、后端地址默认值、开发模式不稳定问题。
2. 统一鉴权策略：决定哪些页面必须先登录，哪些页面允许游客预览。
3. 清理一级导航，只保留“当前真正能用且有价值”的功能。
4. 将“开发中”页面从主导航移除，改为内部灰度入口或直接隐藏。
5. 重新定义首页与工作台：
   - 首页负责转化；
   - 工作台负责已登录用户效率；
   - 写作页负责核心创作。

## 2026-03-28 补充检查记录

### 已修复
- 登录页“点击登录一直转圈”根因已确认并修复：
  - 后端启动链被 `streamlit` / `playwright` / `pyglet` 等可选依赖阻塞；
  - 当前 `POST /api/v1/auth/login` 已恢复正常返回，错误凭据会立即返回 `401 Invalid email or password`；
  - `GET /health` 已恢复 `200 OK`。
- `system_settings` 的 schema 漂移已兼容：
  - 当前开发库实际使用旧列名 `key` / `value`；
  - `SystemConfig` 已兼容新旧两套字段名，启动日志里的 `setting_key does not exist` 已消失。
- `alerts` / `dashboard` 路由重复前缀已修复：
  - 原先后端实际挂载成 `/api/v1/alerts/alerts/*`、`/api/v1/dashboard/dashboard`；
  - 现在前端请求的 `/api/v1/alerts/*`、`/api/v1/dashboard` 可正确命中。
- 公开页不再渲染通知中心：
  - 避免匿名访问 `/pricing`、`/hotspots` 等页面时无意义请求通知未读接口。
- 公开页导航已切换为游客模式：
  - 不再显示 `Free会员` 徽章、用户头像下拉；
  - 改为明确的 `登录` / `注册` CTA；
  - 游客导航仅保留公开目的地：`/hotspots`、`/pricing`。

### 新发现
- 公开页与应用内页目前仍共用同一个主导航组件，只是根据登录态裁剪内容。
- 这已经足够解决误导性问题，但长期看更适合拆成两套导航：
  - 游客导航：品牌、产品介绍、热点、定价、登录/注册；
  - 应用导航：AI 助手、创作中心、账户、会员、通知等。
