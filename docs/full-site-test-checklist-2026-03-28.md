# SupaWriter 全站测试清单（2026-03-28）

> 2026-03-30 重建版：原文件缺失后按既有巡检结论、实施计划、当前代码状态与已落地修复重新生成。后续所有巡检、修复、回归继续以此文件为主清单。

目的：先完整列出全站要检查的功能、页面、跳转、权限、接口和合理性问题；后续所有巡检与修复都以此清单为准，不再零散处理。

状态说明：
- `TODO`：尚未系统检查
- `IN PROGRESS`：已检查部分路径，已有结论或局部修复，仍待补完
- `OPEN`：已确认存在问题，待修复/待验证
- `FIXED`：已修复并完成聚焦验证
- `N/A`：当前版本不应保留或应下线

## 实时进度看板（2026-03-30）

| 维度 | 数量 | 说明 |
|---|---:|---|
| 总项数 | 53 | 当前纳入主清单的检查/修复项 |
| `FIXED` | 40 | 已修复并完成聚焦验证 |
| `IN PROGRESS` | 11 | 已有结论或局部自动化覆盖，仍需继续收口 |
| `OPEN` | 2 | 已确认存在问题，待设计/实现/回归 |
| `TODO` | 0 | 尚未做系统检查 |

### 当前未关闭项总览

| 优先级 | 项目 | 当前状态 | 下一动作 |
|---|---|---|---|
| P0 | `G-009` 复杂页失败态 | IN PROGRESS | 已给 `/history` 补可见错误卡与重试入口，继续收口 `/writer` 与做实际浏览器验证 |
| P0 | `A-007` 账号管理深测 | IN PROGRESS | 已修 `/account` token 丢失时卡假登录态，并补改密 success/failure mock 回归；继续补更多 auth 边界分支 |
| P0 | `C-004` 历史记录深测 | IN PROGRESS | 已补失败态 UI、修预览页 SEO 改标题联动，并补下载格式 mock 回归；继续补更完整浏览器回归 |
| P0 | `C-006` 批量生成深测 | IN PROGRESS | 已修重试后详情抽屉状态不同步导致无“下载全部”按钮的问题，继续补更多失败态 |
| P0 | `C-007` Agent 深测 | IN PROGRESS | 已新增草稿 accept/discard mock 回归，继续补编辑链路与更多失败态 |
| P1 | `G-003` / `G-010` 导航与命名 | OPEN | 统一产品分层、入口文案、中英混搭 |
| P1 | `A-003` Google OAuth 真回站 | IN PROGRESS | 补真实第三方成功回调闭环验证 |
| P1 | `A-004` 注册异常分支 | IN PROGRESS | 补弱密码/字段级校验差异 |
| P1 | `H-003` 仪表盘定位 | IN PROGRESS | 继续验证保留层级与入口策略 |
| P1 | `H-005` 新闻源稳定性 | IN PROGRESS | 继续观察上游源波动与错误提示质量 |
| P1 | `H-006` 预警链路 | IN PROGRESS | 继续补 API/页面联动回归 |
| P2 | `G-001` 首页转化链路 | IN PROGRESS | 复核游客首页到注册/登录/定价的转化路径 |

### 当前工作树已落地但待进一步验证的修复

- `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/error.tsx` 与 `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/global-error.tsx`
  - 已新增全局错误边界，解决 Next App Router 在异常时出现 `missing required error components` 的结构性问题；
  - 该问题是本轮 Playwright 首次运行暴露出的真实缺口，也对应 `G-009` 的全站错误态收口项。
- `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/history/page.tsx`
  - 已补历史记录首屏加载失败时的可见错误卡与“重新加载”按钮；
  - 已修预览弹层中 `SEOPanel` 应用新标题后，列表会更新但预览头部不更新的问题；
  - 现已通过 `npx next lint --file src/app/history/page.tsx`，此前 `Image` 图标的误报 warning 也已顺手清掉。
- `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/account/page.tsx`
  - 已修 `getBackendToken()` 为空时不再停留在假登录态，而是走 `handleAuthExpired()`；
  - 2026-03-30 再新增改密 success/failure 的 root-level mock 回归，覆盖“成功关闭表单”与“失败保留表单并展示后端错误”；
  - 同日补 `frontend/src/app/account/account-response.js`，处理 `204/空响应体` 不再误判失败，并优先透传后端 `detail/message`；
  - 同日再统一 `bind email` / `unbind oauth` 在 token 丢失时改走 `handleAuthExpired()`，避免停留在假登录态或只提示“请先登录”；
  - 现存 warning 为历史上的 `useEffect` 依赖提示。
- `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/batch/page.tsx`
  - 已修重试失败任务后详情抽屉仍停留在旧 `selectedJob` 状态、导致“下载全部”按钮不出现的问题；
  - 已顺手删除重复的 free-tier guard，减少不可达分支；
  - 同日再统一 batch API/detail error message 透传，首屏失败卡会显示后端 `detail/message`，重试/取消/下载等操作也不再只显示通用错误。
- `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/settings/page.tsx`
  - 已修管理员降级为非管理员后仍停留在 `llm/services` 管理页的权限退化问题；
  - 现在非管理员会自动回退到 `models`，且 admin-only 分支不会继续加载；
  - 2026-03-30 再补首屏加载失败时的可见错误卡与“重新加载”按钮，避免默认空表单伪装成正常状态；
  - 同日补齐 add/delete provider，以及 LLM/Qiniu/Serper、模型配置、个人偏好保存分支的非 401 后端报错透传，避免静默失败或一律只显示“保存失败”。
- `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/writer/page.tsx`
  - 已补从历史记录带 `articleId` 进入编辑但加载失败时的可见错误态与“重新加载文章”入口；
  - 这部分目前已完成 lint，但由于 middleware 的 host/cookie 行为，浏览器级自动化仍需后续补稳定方案。
- `/Users/wxk/Desktop/workspace/supawriter/frontend/src/types/api.ts`、`/Users/wxk/Desktop/workspace/supawriter/frontend/src/lib/api/billing.ts`、`/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/pricing/page.tsx`、`/Users/wxk/Desktop/workspace/supawriter/backend/api/main.py`
  - 2026-03-30 已修 B-006 里确认存在的接口契约问题：`batch/agent` 重复前缀挂载、前端配额接口前缀漂移、批量任务 list/detail 结构兼容、定价页 quota pack fallback id 与活跃订阅判断漂移；
  - 已补 `tests/api-contract-audit.test.mjs` 聚焦回归覆盖这些契约项。
- `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/animations-test/page.tsx`
  - 2026-03-30 已进一步收口为“仅开发环境可见”；非 `development` 环境统一 `redirect('/writer')`；
  - `cd frontend && npm run lint -- --file src/app/animations-test/page.tsx` 已通过。
- `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/writer/TaskQueue.tsx`
  - 已修终态任务（`completed/failed/error`）仍可点击进入实时进度页的不合理跳转；
  - 现在只有 `queued/running` 任务会打开进度页，终态任务仅保留展示与移除能力。
- `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/agent/page.tsx`
  - 2026-03-30 已统一 agent 创建/更新/删除/审核与首屏加载错误的后端消息透传，不再一律只显示“操作失败”；
  - 首屏 `agents/drafts` 任一接口失败时，错误卡会显示当前收到的后端错误详情。
- `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-agent-mocked.spec.ts`
  - 2026-03-30 新增两条 root-level Playwright mock 回归：接受草稿与丢弃草稿；
  - 同日再补首屏加载失败 + 重试、创建失败后端错误透传等回归；
  - `PLAYWRIGHT_BASE_URL=http://localhost:3115 pnpm exec playwright test tests/frontend-agent-mocked.spec.ts --reporter=line --workers=1` 已通过。
- `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-account-password-mocked.spec.ts`
  - 2026-03-30 新增 `/account` 改密成功/失败双分支 mock 回归；
  - 已为冷启动编译场景放宽首次 `page.goto('/account')` 超时，避免把 Next 首编译误判为功能失败；
  - 同日再补 profile `401` 失效时跳回 `/auth/signin?callbackUrl=%2Faccount` 的回归；
  - `PLAYWRIGHT_BASE_URL=http://localhost:3115 pnpm exec playwright test tests/frontend-account-password-mocked.spec.ts --reporter=line --workers=1` 已通过。
- `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-history-download-mocked.spec.ts`
  - 2026-03-30 新增 `/history` Markdown / HTML 下载扩展名回归；
  - `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3113 pnpm exec playwright test tests/frontend-history-download-mocked.spec.ts --reporter=line --workers=1` 已通过。
- `/Users/wxk/Desktop/workspace/supawriter/tests/settings-admin-tab-access.test.mjs`
  - 2026-03-30 新增 settings 管理员 tab 权限退化测试；
  - `node --test tests/settings-admin-tab-access.test.mjs` 已通过。
- `/Users/wxk/Desktop/workspace/supawriter/tests/settings-response.test.mjs`
  - 2026-03-30 再补 helper 对 `message` 字段的回退断言；
  - 当前 `node --test tests/settings-response.test.mjs tests/settings-admin-tab-access.test.mjs` 为 `7 passed`。
- `/Users/wxk/Desktop/workspace/supawriter/tests/account-response.test.mjs`
  - 2026-03-30 新增 `/account` 响应解析 helper 回归，覆盖 `204 No Content`、JSON 错误体和 fallback message；
  - `node --test tests/account-response.test.mjs` 已通过。
- `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-agent-draft-review.spec.ts`
  - 2026-03-30 新增 `/agent` 草稿审核 happy-path mock 回归，覆盖 accept / discard 后状态刷新；
  - `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 pnpm exec playwright test tests/frontend-agent-draft-review.spec.ts --reporter=line` 已通过。
- `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-settings-mocked.spec.ts`
  - 2026-03-30 新增 `/settings` 浏览器级 mock 回归，覆盖成员/管理员 tab 可见性、首屏错误卡 + 重试、模型/偏好保存错误、provider 添加错误、服务保存错误；
  - `PLAYWRIGHT_BASE_URL=http://localhost:3114 pnpm exec playwright test tests/frontend-settings-mocked.spec.ts --reporter=line --workers=1` 已通过。
- `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-writer-mocked.spec.ts`
  - 2026-03-30 新增 `/writer` 浏览器级 mock 回归，覆盖未登录回跳 callback、任务队列失败 + 重试、后台刷新失败保留旧数据、编辑模式文章加载失败；
  - `PLAYWRIGHT_BASE_URL=http://localhost:3114 pnpm exec playwright test tests/frontend-writer-mocked.spec.ts --reporter=line --workers=1` 已通过。
- `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-batch-mocked.spec.ts`
  - 2026-03-30 再补 `/batch` 首屏失败卡 + 重试恢复回归，并验证后端错误详情在页面正文可见；
  - `PLAYWRIGHT_BASE_URL=http://localhost:3115 pnpm exec playwright test tests/frontend-batch-mocked.spec.ts --reporter=line --workers=1` 已通过。
- `/Users/wxk/Desktop/workspace/supawriter/tests/llm-provider-save.test.mjs`
  - 2026-03-30 新增 LLM provider 保存 payload helper 回归，覆盖模型编辑合并与 `••••••••` placeholder key 去除；
  - 可与 settings 相关 node tests 一起串行执行。
- `/Users/wxk/Desktop/workspace/supawriter/tests/api-contract-audit.test.mjs`
  - 2026-03-30 新增 API 契约审计回归，覆盖 `batch/agent` 路由挂载、`subscription/quota` 前缀、批量任务 payload 兼容、pricing fallback quota packs 与 active subscription 派生；
  - `node --test tests/api-contract-audit.test.mjs` 已通过。

### 状态同步提醒

- `R-001` ~ `R-004` 对应的 `C-001` / `C-005` / `C-008` / `C-009` / `C-010` 已在 2026-03-30 同步关闭；
- 后续更新时继续优先同步跨分段重复项，避免“结构已收口但页面项仍未关闭”的重复统计。

---

## A. 全局框架与通用体验

| ID | 模块 | 检查项 | 状态 | 备注 |
|---|---|---|---|---|
| G-001 | 路由 | 首页是否为清晰的游客入口 | IN PROGRESS | 已从强制进工作台调整为公开首页，但还需复核整体转化链路 |
| G-002 | 导航 | 游客导航是否只展示公开能力 | FIXED | 已隐藏会员章、头像、通知、受保护入口 |
| G-003 | 导航 | 登录后导航是否只展示可用功能 | OPEN | 主导航已收敛到 AI 助手 / 创作中心 / 热点中心 / 定价方案，但文案仍保留“社区基础功能”，且 `/batch` `/agent` 等高阶页只能靠直达访问，产品分层仍不够清晰 |
| G-004 | 鉴权 | 受保护页面是否统一重定向到登录页 | FIXED | 已补并验证主要受保护路由统一回跳到 `/auth/signin?callbackUrl=<相对路径>` |
| G-005 | 回跳 | 登录后 callbackUrl 回跳是否一致 | FIXED | 已修复并验证主要路径 |
| G-006 | 异常页 | `/auth/error` 恢复链路是否合理 | FIXED | 已验证返回公开首页与重新登录 |
| G-007 | 公共页 | 公共页是否误调用登录后接口 | FIXED | 已处理通知未读请求 |
| G-008 | 页头/页脚 | 服务条款、隐私政策等是否为有效链接 | FIXED | 登录/注册页法务链接已落到站内法务页 |
| G-009 | 加载态 | loading / empty / error 态是否完整 | IN PROGRESS | `/agent` `/batch` 已补可见失败态；2026-03-30 又补了根级 `error.tsx/global-error.tsx`、`/history` 可见错误卡 + 重试，`/writer` 等复杂页仍待继续收口 |
| G-010 | 文案 | 页面命名、按钮文案是否准确 | OPEN | 命名体系仍未收口：`创作中心` / `超能写手` / `工作台` 混用，且 `Agent` 中英混搭仍明显 |

---

## B. 认证与账户

| ID | 页面/功能 | 路由/接口 | 检查项 | 状态 | 备注 |
|---|---|---|---|---|---|
| A-001 | 登录页 | `/auth/signin` | 页面可打开、表单可提交 | FIXED | 登录无限转圈问题已修过 |
| A-002 | 登录流程 | `POST /api/v1/auth/login` | 错误凭据是否快速返回错误 | FIXED | 已确认错误凭据返回 401 |
| A-003 | 登录流程 | Google 登录 | 第三方登录按钮与回跳 | IN PROGRESS | 已验证回跳目标规整；真实 OAuth 成功回站仍需闭环验证 |
| A-004 | 注册页 | `/auth/register` | 表单字段、校验、错误提示 | IN PROGRESS | 已覆盖成功与重复账号分支，仍待补弱密码/字段级校验差异 |
| A-005 | 登录/注册切换 | `/auth/signin` `/auth/register` | callbackUrl 是否保留 | FIXED | 主要路径已验证 |
| A-006 | 忘记密码 | 登录页 | 是否存在无效入口 | FIXED | 已移除无效忘记密码链接 |
| A-007 | 账号管理 | `/account` | 是否必须登录、功能是否完整 | IN PROGRESS | 已验证受保护、改密 success/failure、profile 401 失效回跳，以及 bind/unbind 在 token 丢失时不再停留在假登录态；更多 OAuth 绑定/解绑异常分支仍待补 |
| A-008 | 设置页 | `/settings` | 是否必须登录、标签页是否合理 | FIXED | 已补管理员降级守卫、首屏错误卡 + 重试、模型/偏好保存错误透传、provider add/delete 与服务保存错误透传；`tests/settings-admin-tab-access.test.mjs`、`tests/settings-response.test.mjs`、`tests/llm-provider-save.test.mjs` 与 `tests/frontend-settings-mocked.spec.ts` 均已通过 |
| A-009 | 预警设置 | `/settings/alerts` | 与 alerts API 是否联通 | FIXED | 关键词加载、add/toggle/delete 基础链路已复验 |
| A-010 | 登出 | 导航菜单 | Token / Session 是否都清理 | FIXED | 登出会清除本地与 cookie 并重新拦截受保护页 |

---

## C. 核心创作流程

| ID | 页面/功能 | 路由 | 检查项 | 状态 | 备注 |
|---|---|---|---|---|---|
| C-001 | 创作主工作台 | `/writer` | 是否为真正核心入口 | FIXED | 已与 `/workspace -> /writer` 的收口结论同步；`/writer` 为唯一正式创作主入口，并已补历史文章加载失败可见错误态与终态任务禁止误进实时进度页 |
| C-002 | AI 助手 | `/ai-assistant` | 基础对话、报错、配额提示 | FIXED | 基础对话链路已回归过 |
| C-003 | 推文选题 | `/tweet-topics` | 生成功能、历史记录、按钮跳转 | FIXED | 生成、历史与跳转主链路已验证 |
| C-004 | 历史记录 | `/history` | 列表、详情、删除、回跳 | IN PROGRESS | 已完成搜索/删除/编辑/预览稳定性等多项验证；2026-03-30 又补首屏 error/retry，并修复预览弹层 `SEOPanel` 改标题后头部不同步的问题；同日新增 `tests/frontend-history-download-mocked.spec.ts` 覆盖 Markdown / HTML 下载扩展名。更完整浏览器回归仍待补 |
| C-005 | 工作台 | `/workspace` | 是否仍有存在必要 | FIXED | 已按既定口径收口为兼容跳转，服务端组件直接 `redirect('/writer')` |
| C-006 | 批量生成 | `/batch` | 功能完整度、权限是否合理 | IN PROGRESS | 已覆盖 retry + download、首屏失败卡 + 重试恢复，以及后端错误详情透传；创建/取消/详情异常链路仍待继续补 |
| C-007 | 写作 Agent | `/agent` | 功能完整度、权限是否合理 | IN PROGRESS | 已覆盖草稿 accept/discard、首屏失败卡 + 重试恢复，以及创建失败后端错误透传；编辑链路与更多失败态仍待继续补 |
| C-008 | 文章再创作 | `/rewrite` | 是否真有业务价值 | FIXED | 已收口为过渡跳转，服务端组件直接 `redirect('/history')`，能力回归历史记录主流程 |
| C-009 | 社区管理 | `/community` | 是否真有业务价值 | FIXED | 已退出生产功能面，服务端组件直接 `redirect('/writer')` |
| C-010 | AI 导航 | `/ai-navigator` | 是否应保留为产品功能 | FIXED | 已降级退出正式产品路由，服务端组件直接 `redirect('/hotspots')` |

---

## D. 热点、资讯与看板

| ID | 页面/功能 | 路由/接口 | 检查项 | 状态 | 备注 |
|---|---|---|---|---|---|
| H-001 | 热点中心 | `/hotspots` | 页面可打开、数据可返回、按钮可用 | FIXED | 游客只读展示与管理员同步入口已回归 |
| H-002 | 新闻页 | `/news` | 页面权限、数据与回跳是否合理 | FIXED | 当前口径为公开资讯聚合页 |
| H-003 | 数据看板 | `/dashboard` | 是否应一级展示、权限是否合理 | IN PROGRESS | 游客拦截和升级 CTA 已复验；是否保留一级入口仍是产品决策问题 |
| H-004 | 热点 API | `/api/v1/hotspots*` | 代理回源、错误态、缓存逻辑 | FIXED | 同步动作已走站内代理 |
| H-005 | 新闻 API | `/api/v1/news*` | 数据源稳定性与错误提示 | IN PROGRESS | 已改成上游失败显式报错，不再静默空数组；长期稳定性仍待观察 |
| H-006 | 预警中心 | `/api/v1/alerts*` | 前后端链路是否完整 | IN PROGRESS | 路由双前缀已修，功能深测待继续 |

---

## E. 定价、会员与权限表达

| ID | 页面/功能 | 路由/接口 | 检查项 | 状态 | 备注 |
|---|---|---|---|---|---|
| P-001 | 定价页 | `/pricing` | 游客体验、套餐展示、跳转 CTA | FIXED | 游客升级 CTA 已统一走登录页回跳 |
| P-002 | 套餐切换 | `/pricing` | 月付/季付/年付逻辑是否正确 | FIXED | 重复打折展示 bug 已修复 |
| P-003 | 升级按钮 | 定价与限制提示 | 是否跳到正确路径 | FIXED | 代码与页面 CTA 已统一指向 `/pricing` |
| P-004 | 会员章 | 导航/页面内 | 是否只在登录态出现 | FIXED | 游客页已隐藏 |
| P-005 | 权限提示 | 各高级功能页 | “升级会员”文案与行为是否准确 | FIXED | 页级升级/去定价 CTA 已统一 |

---

## F. 页面存在合理性 / 功能去留判断

| ID | 页面 | 当前判断 | 状态 | 备注 |
|---|---|---|---|---|
| R-001 | `/workspace` | 不保留独立产品页，收口为兼容跳转 | FIXED | 已确定收口到 `/writer` |
| R-002 | `/community` | 下线，占位页退出生产路由 | FIXED | 已确定下线或重定向到 `/writer` |
| R-003 | `/rewrite` | 下线独立页，改回主流程子能力 | FIXED | 已确定收口到 `/history` |
| R-004 | `/ai-navigator` | 下线正式产品路由，降级为内部资源清单 | FIXED | 已确定收口到 `/hotspots` |
| R-005 | `/animations-test` | 仅保留为开发调试页，退出生产入口 | FIXED | 已收口为开发环境专用；非开发环境统一重定向到 `/writer` |
| R-006 | `/login` | 保留为兼容别名，统一跳转到正式登录页 | FIXED | 当前实现已直接 `redirect('/auth/signin')`，并在存在 `callbackUrl` 时透传回跳参数 |

### R-001 ~ R-004 路由收口结论

| 路由 | 最终定位 | 路由动作 | 保留内容 | 下线内容 |
|---|---|---|---|---|
| `/workspace` | 历史过渡入口，不再作为正式产品页 | `302 -> /writer` | 保留 `/writer` 作为唯一创作主入口 | 下线入口卡片汇总页与静态热点壳页 |
| `/community` | 遗留占位页，直接退出生产 | `302 -> /writer` | 仅保留需求记录，不保留用户可见壳页 | 下线独立页面、占位说明、出口 CTA |
| `/rewrite` | 遗留占位页，能力回收进主流程 | `302 -> /history` | 保留“从历史记录继续编辑/再创作”的用户意图 | 下线独立页面与顶级导航心智 |
| `/ai-navigator` | 内部资源索引，不再算正式产品功能 | `302 -> /hotspots` | 若工具清单仍有价值，仅保留到内部资源页 | 下线生产路由与未审核外链集合 |

---

## G. 后端稳定性与关键接口

| ID | 接口/模块 | 检查项 | 状态 | 备注 |
|---|---|---|---|---|
| B-001 | `/health` | 容器健康检查是否稳定 | FIXED | 当前返回 200 |
| B-002 | 启动链 | 可选依赖缺失是否阻塞 API 启动 | FIXED | 已补回归测试 |
| B-003 | `SystemConfig` | 新旧 schema 兼容 | FIXED | 已补回归测试 |
| B-004 | `alerts` 路由 | 前缀是否正确 | FIXED | 已补回归测试 |
| B-005 | 登录接口 | 是否稳定快速响应 | FIXED | 已验证 |
| B-006 | 其余写作/热点/会员 API | 是否存在 404/500/前缀错误 | FIXED | 已修 `batch/agent` 重复挂载前缀、前端 quota 接口前缀漂移、批量任务 payload 兼容与 pricing fallback 契约漂移，并补 `tests/api-contract-audit.test.mjs` 回归 |

---

## 当前仍需继续重点处理的问题

1. `/writer`、`/history`、`/account`、`/settings` 等复杂页还需要把失败态与回跳链路统一做完。
2. 根测试目录已逐步补齐 `account/history/agent/settings` 相关回归，但 `/writer`、`/settings` 浏览器级覆盖与剩余 API 通盘扫描仍需继续扩充。
3. `Agent` 与 `Batch` 目前更适合继续补 mock/浏览器回归，而不是只做代码阅读。
4. 信息架构层面的重定向结论已经明确，但清单分段状态仍需同步，避免重复统计。

## 后续执行原则

后续不再“发现一个修一个”，而是保持：

1. 先把所有 `OPEN/TODO/IN PROGRESS` 明确成具体问题；
2. 按 `P0/P1/P2` 统一排序；
3. 每次只推进一小段：先补最小失败验证，再改实现，再做聚焦回归；
4. 每完成一项就回写本清单。
