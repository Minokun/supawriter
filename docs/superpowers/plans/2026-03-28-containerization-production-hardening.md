# Containerization Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SupaWriter’s containerized deployment production-ready by unifying startup flow, schema migration, auth/token handling, role/subscription semantics, and deployment verification.

**Architecture:** Production deployment is driven from a single compose topology where Postgres/Redis come up first, a dedicated migration/init stage normalizes schema and seed state, then backend/worker/frontend/nginx start against a consistent environment model. Auth is normalized so browser and server-side flows always converge on backend-issued JWTs, while membership tier and subscription state are displayed from clearly separated backend sources.

**Tech Stack:** Docker Compose, Dockerfiles, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Next.js 14, NextAuth, TypeScript, shell verification scripts

---

### Task 1: Normalize production compose topology

**Files:**
- Modify: `deployment/docker-compose.yml`
- Modify: `deployment/docker-start.sh`
- Modify: `deployment/README.md`
- Reference: `deployment/docker-compose.dev.yml`

- [ ] **Step 1: Write the failing verification expectation**

Document the expected production startup contract in the plan workspace notes:

```text
Expected production order:
postgres/redis healthy -> migrate completed successfully -> backend/worker/frontend start -> nginx starts
```

- [ ] **Step 2: Verify current production topology violates the contract**

Run: `docker compose -f deployment/docker-compose.yml config`
Expected: Compose renders without a dedicated `migrate` service and backend/worker do not depend on migration completion.

- [ ] **Step 3: Add a dedicated migration/init service**

Update `deployment/docker-compose.yml` so that:

```yaml
migrate:
  build:
    context: ..
    dockerfile: deployment/Dockerfile.backend
  command: ["sh", "-lc", "python -m alembic -c backend/api/db/migrations/alembic.ini upgrade head && python deployment/scripts/init_production_state.py"]
  depends_on:
    postgres:
      condition: service_healthy
  restart: "no"
```

Also update `backend` and `worker` to depend on successful migration completion, not just database health.

- [ ] **Step 4: Update the production startup wrapper**

Make `deployment/docker-start.sh` use the real compose file, stop referencing `docker-compose.full.yml`, and run only the supported startup path.

- [ ] **Step 5: Re-run compose rendering verification**

Run: `docker compose -f deployment/docker-compose.yml config`
Expected: `migrate` appears in output and backend/worker dependencies reference migration completion.

- [ ] **Step 6: Commit**

```bash
git add deployment/docker-compose.yml deployment/docker-start.sh deployment/README.md
git commit -m "ops: normalize production compose startup flow"
```

### Task 2: Establish migration authority and schema diagnosis

**Files:**
- Create: `deployment/scripts/check_schema_drift.py`
- Create: `deployment/scripts/init_production_state.py`
- Modify: `deployment/postgres/init/init.sql`
- Modify: `deployment/postgres/init/complete-init.sql`
- Modify: `backend/api/db/migrations/alembic/env.py`
- Modify: `deployment/README.md`

- [ ] **Step 1: Write the failing schema-drift check design**

Define the minimum drift checks:

```python
required_checks = [
    "alembic_version present",
    "users has phone/email_verified/avatar_source/membership_tier",
    "hotspot_sources exists",
    "user_model_configs has chat_model/writer_model/embedding_model",
]
```

- [ ] **Step 2: Verify current database is drifted**

Run: `PGPASSWORD=... psql ... -c "select * from alembic_version"`
Expected: Version does not match current model/schema reality or fails the new drift script.

- [ ] **Step 3: Implement a schema drift checker**

Create `deployment/scripts/check_schema_drift.py` that:
- connects using `DATABASE_URL`
- inspects `information_schema`
- prints pass/fail per required object
- exits non-zero on drift

- [ ] **Step 4: Minimize init SQL responsibility**

Reduce `deployment/postgres/init/init.sql` and `deployment/postgres/init/complete-init.sql` to only first-boot essentials (database bootstrap / extensions / truly minimal seed safety), removing long-lived business schema duplication that Alembic should own.

- [ ] **Step 5: Implement idempotent production init script**

Create `deployment/scripts/init_production_state.py` that:
- runs after Alembic
- repairs super-admin flags
- seeds required tier defaults/global providers if missing
- never overwrites stronger existing user privilege data

- [ ] **Step 6: Verify drift checker behavior**

Run: `python deployment/scripts/check_schema_drift.py`
Expected: Non-zero before full repair on drifted DB, zero on aligned schema.

- [ ] **Step 7: Commit**

```bash
git add deployment/scripts/check_schema_drift.py deployment/scripts/init_production_state.py deployment/postgres/init/init.sql deployment/postgres/init/complete-init.sql backend/api/db/migrations/alembic/env.py deployment/README.md
git commit -m "ops: enforce alembic as schema authority"
```

### Task 3: Fix frontend internal/backend address separation

**Files:**
- Modify: `frontend/src/lib/auth.ts`
- Modify: `frontend/src/app/api/auth/backend-token/route.ts`
- Modify: `frontend/src/app/api/news/[source]/route.ts`
- Modify: `frontend/src/app/api/hotspots/v2/cache/route.ts`
- Modify: `frontend/src/app/api/hotspots/v2/latest/route.ts`
- Modify: `frontend/src/app/api/hotspots/v2/latest/[source]/route.ts`
- Modify: `frontend/src/app/api/hotspots/v2/sources/route.ts`
- Modify: `frontend/src/app/api/hotspots/v2/sync/route.ts`
- Modify: `deployment/docker-compose.yml`
- Modify: `deployment/docker-compose.dev.yml`
- Modify: `frontend/.env.local.example`

- [ ] **Step 1: Write the failing routing expectation**

State the invariant:

```text
Server-side Next.js code must never use NEXT_PUBLIC_API_URL to reach a sibling container.
```

- [ ] **Step 2: Verify current code violates the invariant**

Run: `rg -n "NEXT_PUBLIC_API_URL .*localhost|const BACKEND_API = process.env.NEXT_PUBLIC_API_URL|const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL" frontend/src/app/api frontend/src/lib/auth.ts`
Expected: Multiple server-side call sites rely on `NEXT_PUBLIC_API_URL`.

- [ ] **Step 3: Introduce one internal backend env convention**

Refactor the affected files to use a single helper pattern:

```ts
const INTERNAL_API_URL = process.env.INTERNAL_API_URL || process.env.API_PROXY_URL || 'http://backend:8000'
```

Use it only in server-side routes / NextAuth callbacks.

- [ ] **Step 4: Update compose env wiring**

Set `INTERNAL_API_URL=http://backend:8000` for frontend in both prod and dev compose files while keeping browser-facing URL separate.

- [ ] **Step 5: Re-run source scan**

Run: `rg -n "NEXT_PUBLIC_API_URL" frontend/src/app/api frontend/src/lib/auth.ts`
Expected: Browser-only usage remains; server-side fetch paths use the internal env variable.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/auth.ts frontend/src/app/api/auth/backend-token/route.ts frontend/src/app/api/news/[source]/route.ts frontend/src/app/api/hotspots/v2/cache/route.ts frontend/src/app/api/hotspots/v2/latest/route.ts frontend/src/app/api/hotspots/v2/latest/[source]/route.ts frontend/src/app/api/hotspots/v2/sources/route.ts frontend/src/app/api/hotspots/v2/sync/route.ts deployment/docker-compose.yml deployment/docker-compose.dev.yml frontend/.env.local.example
git commit -m "fix: separate internal and public frontend api addresses"
```

### Task 4: Harden backend JWT exchange and client token lifecycle

**Files:**
- Modify: `frontend/src/lib/auth.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/hooks/useAuth.ts`
- Modify: `frontend/src/lib/api-client.ts`
- Modify: `frontend/src/app/auth/signin/page.tsx`
- Modify: `frontend/src/app/auth/register/page.tsx`
- Modify: `backend/api/routes/auth_exchange.py`
- Modify: `backend/api/routes/auth.py`

- [ ] **Step 1: Write the failing auth regression expectations**

Define the expected cases:

```text
1. OAuth success -> backend JWT issued
2. exchange failure -> no Google access token used as API token
3. invalid stored token -> cleared and re-auth initiated
```

- [ ] **Step 2: Verify current fallback exists**

Run: `rg -n "token.accessToken = account.access_token|keeping existing email-login token|Using cached token" frontend/src/lib/auth.ts frontend/src/lib/api.ts frontend/src/hooks/useAuth.ts`
Expected: Existing fallback/cached-token logic can preserve invalid tokens.

- [ ] **Step 3: Remove non-backend-token fallback**

Update `frontend/src/lib/auth.ts` so failed exchange does not reuse Google access tokens for backend API auth.

- [ ] **Step 4: Normalize token cache invalidation**

Refactor `frontend/src/lib/api.ts`, `frontend/src/hooks/useAuth.ts`, and `frontend/src/lib/api-client.ts` so that:
- backend JWT is the only API token source
- invalid signature or 401 clears stale token state
- OAuth flow can re-exchange cleanly
- email/password login tokens remain valid only if backend-issued

- [ ] **Step 5: Ensure `/auth/me` is authoritative**

Adjust auth/user-loading flow so UI role/tier state always refreshes from `/api/v1/auth/me` after successful token acquisition.

- [ ] **Step 6: Verify with targeted scan/build expectation**

Run: `rg -n "account.access_token|keeping existing email-login token" frontend/src`
Expected: No code path remains that uses third-party access tokens as backend business JWTs.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/auth.ts frontend/src/lib/api.ts frontend/src/hooks/useAuth.ts frontend/src/lib/api-client.ts frontend/src/app/auth/signin/page.tsx frontend/src/app/auth/register/page.tsx backend/api/routes/auth_exchange.py backend/api/routes/auth.py
git commit -m "fix: normalize backend jwt exchange lifecycle"
```

### Task 5: Separate membership tier from subscription display semantics

**Files:**
- Modify: `backend/api/services/subscription_service.py`
- Modify: `backend/api/routes/subscription.py`
- Modify: `backend/api/core/dependencies.py`
- Modify: `backend/api/services/tier_service.py`
- Modify: `frontend/src/components/settings/SubscriptionManagement.tsx`
- Modify: `frontend/src/hooks/useAuth.ts`
- Modify: `frontend/src/lib/api/billing.ts`

- [ ] **Step 1: Write the failing behavior cases**

Define the expected semantics:

```text
membership_tier controls feature level
subscription controls billing state
missing subscription must not make an ultra/admin user display as free
```

- [ ] **Step 2: Verify current UI mixes the concerns**

Run: `rg -n "membershipTier !== 'free'|current_plan|free" frontend/src/components/settings/SubscriptionManagement.tsx backend/api/services/subscription_service.py`
Expected: Subscription responses and tier state are coupled in current rendering logic.

- [ ] **Step 3: Make backend subscription response explicit**

Adjust subscription backend so free-plan fallback is clearly “no active paid subscription” rather than “authoritative account tier”. If needed, include a separate field indicating subscription status vs feature tier source.

- [ ] **Step 4: Refactor frontend subscription UI**

Update `SubscriptionManagement.tsx` so it:
- shows membership tier from auth state
- shows billing/subscription state separately
- does not downgrade displayed tier based on missing subscription rows

- [ ] **Step 5: Verify the super-admin account repair contract**

Ensure backend tier logic still treats configured super-admin emails with `is_superuser=true` as admin-capable users regardless of subscription rows.

- [ ] **Step 6: Run targeted scan**

Run: `rg -n "membershipTier !== 'free'|current_plan" frontend/src/components/settings/SubscriptionManagement.tsx`
Expected: Rendering logic distinguishes feature tier from billing state.

- [ ] **Step 7: Commit**

```bash
git add backend/api/services/subscription_service.py backend/api/routes/subscription.py backend/api/core/dependencies.py backend/api/services/tier_service.py frontend/src/components/settings/SubscriptionManagement.tsx frontend/src/hooks/useAuth.ts frontend/src/lib/api/billing.ts
git commit -m "fix: separate feature tier from billing subscription state"
```

### Task 6: Repair health checks, worker readiness, and admin bootstrap

**Files:**
- Modify: `backend/api/routes/health.py`
- Modify: `backend/api/main.py`
- Modify: `backend/api/workers/hotspots_worker.py`
- Modify: `backend/api/services/hotspots_v2_service.py`
- Modify: `deployment/scripts/init_production_state.py`
- Modify: `deployment/docker-compose.yml`

- [ ] **Step 1: Write the failing readiness criteria**

Define readiness expectations:

```text
backend health = app up + db reachable + required schema available
worker readiness = required tables and seed sources exist before sync task runs
```

- [ ] **Step 2: Verify current health endpoint is too weak**

Run: `curl -s http://localhost:8001/health`
Expected: Database/schema readiness is not fully reflected or returns incomplete status.

- [ ] **Step 3: Strengthen backend health reporting**

Update `backend/api/routes/health.py` and any needed startup helpers to report database/schema readiness meaningfully.

- [ ] **Step 4: Guard worker execution on required schema/data**

Refactor hotspot worker startup path so missing required tables or missing source seed state fail fast and clearly, while init script is responsible for seeding required source records.

- [ ] **Step 5: Ensure admin bootstrap is idempotent**

Extend `deployment/scripts/init_production_state.py` so that `wxk952718180@gmail.com` and any configured super-admin emails are repaired safely without overwriting stronger existing state.

- [ ] **Step 6: Verify logs/health behavior**

Run: `docker compose -f deployment/docker-compose.yml config` plus targeted local health checks.
Expected: readiness model is explicit and compatible with compose health/dependency flow.

- [ ] **Step 7: Commit**

```bash
git add backend/api/routes/health.py backend/api/main.py backend/api/workers/hotspots_worker.py backend/api/services/hotspots_v2_service.py deployment/scripts/init_production_state.py deployment/docker-compose.yml
git commit -m "ops: add real readiness and bootstrap repair flow"
```

### Task 7: Verify the productionized container path end-to-end

**Files:**
- Modify: `deployment/README.md`
- Modify: `deployment/verify_all.py`
- Create: `deployment/verify_production_stack.sh`
- Reference: `docs/superpowers/specs/2026-03-28-containerization-production-hardening-design.md`

- [ ] **Step 1: Write the verification checklist**

Create a checklist covering:

```text
compose config
migration service success
backend health
frontend reachability
worker no missing-table crash
auth/me works after login
admin tier preserved
subscription view consistent
```

- [ ] **Step 2: Add a verification script**

Create `deployment/verify_production_stack.sh` that runs the concrete smoke checks for the production stack and exits non-zero on failure.

- [ ] **Step 3: Update verification docs/tooling**

Document the exact startup, migration, and smoke-test commands in `deployment/README.md` and align `deployment/verify_all.py` if it still points to obsolete files such as `docker-compose.full.yml`.

- [ ] **Step 4: Run verification commands**

Run, in order:
- `docker compose -f deployment/docker-compose.yml config`
- `python deployment/scripts/check_schema_drift.py` (against target DB)
- `bash deployment/verify_production_stack.sh`

Expected: all commands exit 0 and report the production stack checks as passing.

- [ ] **Step 5: Commit**

```bash
git add deployment/README.md deployment/verify_all.py deployment/verify_production_stack.sh
git commit -m "docs: add production stack verification workflow"
```
