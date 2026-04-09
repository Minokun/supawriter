# SupaWriter 容器化生产级修复设计

**日期**: 2026-03-28  
**主题**: 容器化部署生产化、鉴权收敛、数据库迁移治理、订阅/权限一致性修复

## 1. 背景与现状

当前项目在完成“全部服务容器化”后，已经暴露出一组系统性问题，而不是单点 bug：

- 当前实际运行的是开发栈容器，而非生产栈容器。
- 前端容器内服务端逻辑错误地通过 `localhost` 访问后端，导致 OAuth token exchange 在容器内失败。
- 浏览器与 NextAuth / backend JWT 链路存在 token 混用，后端日志中已出现 `Signature verification failed`。
- 数据库 schema 与代码版本不一致，且 Alembic 版本记录漂移，导致接口和 worker 在运行时访问不存在的列/表。
- 订阅体系和会员等级体系语义混杂，导致“没有 subscription 记录”会在 UI 层表现为“账号变成 free”。
- 容器启动顺序未强约束迁移完成，worker/backed 会在旧 schema 上启动并报错。
- 容器化部署缺少生产可用的验收标准、可观测性和失败阻断机制。

## 2. 核心目标

本次修复的目标不是“修几个报错”，而是将容器化部署重构为一套可重复、可迁移、可验证、可观测的生产级运行方式。

目标包括：

1. 以生产容器编排作为唯一部署真相。
2. 保证数据库迁移是应用启动前置条件。
3. 统一认证和权限链路，消除旧 token / 错 token 混用。
4. 统一会员等级与订阅语义，避免 UI 误降级。
5. 修复前端、后端、worker 在容器内的服务发现与健康检查。
6. 提供可落地的部署、初始化、回归验证方案。

## 3. 方案选择

采用方案 A：**以生产容器栈为唯一真相，重建启动链路**。

不采用“先补 dev 再补 prod”的原因：

- 容器化问题已经跨越鉴权、schema、初始化、运行拓扑；先补 dev 只会复制错误。
- 生产不可用的根因来自设计不收敛，而不是单个配置缺失。
- 只有将 prod 栈定义为唯一部署基线，才能让 dev 栈收敛为它的轻量开发变体。

## 4. 目标架构

生产部署按如下链路运行：

`postgres / redis -> migrate/init -> backend -> worker -> frontend -> nginx`

其中：

- `postgres` 和 `redis` 负责基础依赖。
- `migrate/init` 负责执行 Alembic 迁移、幂等初始化数据、超级管理员修复与必要默认数据补齐。
- `backend` 仅在迁移完成后启动。
- `worker` 仅在迁移完成且 backend schema 正确后启动。
- `frontend` 区分浏览器访问地址和容器内服务访问地址。
- `nginx` 作为外部统一入口。

## 5. 设计细节

### 5.1 容器编排与启动顺序

生产 `docker-compose.yml` 将被重构为：

- 保留 `postgres`、`redis`、`backend`、`worker`、`frontend`、`nginx`。
- 新增一次性 `migrate` 服务，负责：
  - 等待数据库健康。
  - 执行 `alembic upgrade head`。
  - 执行幂等初始化脚本。
- `backend` 和 `worker` 对 `migrate` 产生依赖，不允许跳过。
- 所有健康检查必须反映真实可用状态，而不是仅仅端口存活。

### 5.2 数据库迁移治理

当前数据库处于“表结构部分已新、Alembic 版本仍旧”的漂移状态，必须治理。

修复原则：

- 统一只使用 Alembic 管理 schema 版本。
- 启动流程中强制执行 `upgrade head`。
- PostgreSQL 首次初始化脚本只负责创建数据库、基础扩展和最小保底对象，不再承载长期演进 schema。
- 对已经漂移的库，提供一次性修复脚本或诊断脚本，用于：
  - 校验 `alembic_version` 与实际结构是否一致。
  - 在必要时安全 stamp 到正确版本，前提是结构已核验。
- 新部署场景下，禁止依赖手工 SQL 或隐式建表。

额外约束：

- `deployment/postgres/init/*.sql` 中与业务 schema 演进重复的内容需要下线、冻结或收敛到最小引导模式，避免与 Alembic 双写 schema。
- 生产库升级路径与全新库初始化路径必须最终落到同一份 Alembic `head` 状态。
- 对当前存量库，先执行“schema 体检 -> 差异修补 / 版本校准 -> Alembic 升级”，禁止直接假定可安全 `upgrade head`。

### 5.3 环境变量与容器内外地址治理

需要区分两类地址：

- **浏览器侧公开地址**：用户浏览器可访问。
- **容器内服务间地址**：容器之间通过服务名访问。

修复原则：

- 前端浏览器侧调用后端，可继续使用公开 API 地址。
- 前端服务端代码（如 NextAuth route handlers、server components）访问后端时，必须使用容器内地址，如 `http://backend:8000`。
- 禁止在容器内服务端逻辑中使用 `localhost` 指向另一个服务。
- 为前端拆分：
  - `NEXT_PUBLIC_API_URL`：浏览器用。
  - `API_PROXY_URL` 或 `INTERNAL_API_URL`：前端容器内服务端逻辑用。

### 5.4 认证链路收敛

当前链路问题在于：

- Google OAuth 登录后，NextAuth 可能在失败时 fallback 到 Google access token。
- 前端本地 `localStorage` 中可能残留旧 backend token。
- 后端只接受自己签发的 JWT，导致签名不一致时出现 401 和间歇性权限异常。

目标链路：

- NextAuth 仅负责 OAuth 会话管理。
- 业务 API 统一只接受 backend JWT。
- OAuth 成功后必须通过 backend exchange endpoint 获取 backend JWT。
- 若 exchange 失败，不再 fallback 到 Google access token 充当业务 token。
- 前端 token 刷新逻辑必须识别 token 来源，避免把旧 token、邮箱 token、Google token 混在一起。
- `/api/v1/auth/me` 成为前端身份与权限展示的唯一可信来源。

### 5.5 权限与订阅语义统一

当前 `membership_tier`、`is_superuser`、`subscriptions` 三者语义混杂。

统一规则：

- `membership_tier` 表示用户功能等级。
- `is_superuser + SUPER_ADMIN_EMAILS` 表示系统超级管理员身份。
- `subscriptions` 表示付费订阅状态与账单周期，不等同于账号是否可显示为 `free`。

明确边界：

- `is_superuser` 决定是否可访问管理员能力。
- `membership_tier` 决定普通业务功能额度与能力边界。
- 若代码中仍存在 `superuser` 作为“伪会员等级”的历史逻辑，需要在实现阶段统一收敛，避免“角色”和“套餐”等级继续混用。

行为定义：

- 超级管理员始终具有最高管理权限，不因缺少 subscription 记录而丢失。
- 已人工设置为 `ultra` / `superuser` 的用户，不应因为订阅表为空而在 UI 上显示为 `free`。
- 订阅接口仅负责显示“当前付费计划 / 账单状态 / 额度来源”，不能覆盖 `/auth/me` 的身份等级。
- 前端展示逻辑必须优先使用 `/auth/me` 返回的 `membership_tier` 与 `is_admin`。

### 5.6 用户初始化与数据修复

需要新增幂等初始化脚本，负责：

- 确保超级管理员邮箱列表中的账号被打上 `is_superuser=true`。
- 对 `wxk952718180@gmail.com` 执行幂等修复：
  - 若存在用户，则确保管理员标记正确。
  - 保持或提升到目标等级（至少不低于 `ultra`）。
- 补齐缺失的默认配置、默认 providers、默认 tier defaults。
- 避免重复创建重复数据。

修复策略要求：

- 不能直接覆盖用户已有的更高权限或更高等级。
- 初始化脚本必须支持重复执行，且每次执行结果稳定。
- 初始化脚本必须区分“全新库默认数据”与“存量生产数据修复”，避免误改真实业务数据。

### 5.7 Backend 与 Worker 稳定性

Backend / worker 必须从“能启动”提升到“正确启动”。

修复要求：

- worker 启动前必须确认所依赖表和初始数据存在。
- backend 的 `/health` 需要更准确反映数据库连接、关键依赖状态。
- 关键接口报 schema 错误时，不能再被隐藏成泛化的 500；日志中需保留可定位信息。
- 对启动时依赖系统配置、审计服务、模型配置等模块做兜底和前置初始化。

### 5.8 Frontend 生产可用性

Frontend 将进行以下治理：

- 容器内 NextAuth 与 token exchange 只使用容器内可达 backend 地址。
- 对 `/api/auth/backend-token` 失败场景提供明确错误处理，不再静默失败。
- 清理旧 token 使用策略：当 token 来源非法或签名失效时，统一清理并重新获取 backend JWT。
- 修正用户信息缓存逻辑，避免缓存中的旧 `membership_tier` 覆盖最新后端状态。
- 保持开发模式提示（如 Next.js outdated）不影响生产部署；生产使用 `next build` / `next start` 镜像，不暴露 dev overlay。

补充要求：

- 所有 Next.js server route / server-side fetch 路径统一使用内部后端地址，避免继续散落使用 `NEXT_PUBLIC_API_URL`。
- 浏览器侧 API 地址、服务端内部 API 地址、OAuth 回调地址必须在环境变量命名上显式区分。

### 5.9 MetaMask 报错处理策略

仓库中不存在 MetaMask / ethereum / web3 集成代码，因此该错误极大概率来自浏览器扩展注入。

处理策略：

- 不在项目中新增针对 MetaMask 的业务修复。
- 确认项目自身不主动调用相关 API。
- 若用户端仍见报错，可通过无扩展窗口复测，将其与项目运行错误区分开。
- 如页面因为未捕获浏览器注入异常而被打断，可在前端补充更稳健的全局错误边界与事件隔离。

## 6. 非目标

本次修复不包括：

- 重构整个业务功能域。
- 升级所有第三方依赖到最新版本。
- 改造支付系统为真实支付网关。
- 处理与容器化稳定性无关的所有历史代码风格问题。

## 7. 验收标准

### 7.1 基础验收

- 新数据库上执行生产 compose 可完整拉起服务。
- 迁移服务自动完成且成功后 backend / worker 才启动。
- backend、worker、frontend、nginx 均为 healthy 或可用状态。

### 7.2 用户与权限验收

- 邮箱登录可用。
- Google 登录可用。
- `wxk952718180@gmail.com` 登录后保持管理员身份，且 UI 不显示为错误的 `free`。
- `/api/v1/auth/me`、后台用户管理、订阅页显示一致。

### 7.3 业务验收

- 工作台打开正常。
- 热点同步 worker 不报缺表错。
- 设置页模型配置可读取。
- 订阅页可读且逻辑一致。
- 管理后台用户检索和权限操作正常。

### 7.4 稳定性验收

- 旧 token 或错误签名 token 会被明确拒绝并触发重新认证。
- 容器重启后数据与权限状态保持一致。
- 未执行迁移时，系统不会“带病启动”。

## 8. 实施顺序

建议实施顺序：

1. 固化生产 compose 与启动依赖。
2. 诊断存量数据库 schema 漂移并确定版本校准方案。
3. 修复数据库迁移与 schema 一致性。
4. 修复前端容器内 API 地址与 token exchange。
5. 修复 backend JWT / 前端 token 管理一致性。
6. 修复权限与订阅展示语义。
7. 增加初始化脚本与管理员修复逻辑。
8. 执行端到端回归验证。
9. 回填 dev compose，使其成为 prod 的开发镜像变体。

## 9. 风险与缓解

- **风险：现有数据库已经漂移，直接 upgrade 可能失败**  
  缓解：先做 schema 诊断与版本校准，再执行标准迁移。

- **风险：前端 token 逻辑调整后影响现有登录状态**  
  缓解：增加受控清理与重新 exchange 流程，避免无限跳转。

- **风险：订阅与等级逻辑修复后暴露更多历史脏数据**  
  缓解：加入幂等数据修复脚本和验收清单。

- **风险：worker 在新启动顺序下暴露更多初始化缺失**  
  缓解：将默认数据初始化纳入 migrate/init 阶段。

## 10. 交付物

本次实现应产出：

- 修复后的生产 `docker-compose.yml` 及相关 Dockerfile / 启动脚本。
- 标准化数据库迁移与初始化机制。
- 管理员与默认数据幂等修复脚本。
- 修复后的前后端鉴权链路。
- 修复后的会员等级 / 订阅展示逻辑。
- 部署与回归验证说明。
