# Review Blockers Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the current P0-P2 review blockers before the next containerized release: remove committed live secrets, sanitize HTML preview rendering, make container startup actually provision super-admin state, make the database accept the `superuser` tier everywhere, and remove the brittle Windows `shell=True` port cleanup path.

**Architecture:** Treat this as one release-blocking hardening pass, but keep each fix isolated behind its own tests and commit. The plan fixes the trust boundary in the frontend, the provisioning/migration path in backend and deployment scripts, and repository hygiene in config files. Existing test entry points stay in place: `node --test` for repo/config guards, `pytest` for Python scripts and backend behavior.

**Tech Stack:** Next.js 14, React 18, FastAPI, Alembic, psycopg2, pytest, Node test runner, shell scripts, Docker Compose.

---

## Scope Check

This touches several subsystems, but they are all release blockers for the same shipping path: local repo state, container startup, backend auth/admin behavior, and one frontend XSS boundary. Keep them in one plan, but land them as separate small commits so each fix can be reviewed and reverted independently.

## File Structure

### Repository and secret hygiene

- Modify: `.gitignore`
  - Ensure local secret files stay untracked, including `deployment/.env`.
- Modify: `.dockerignore`
  - Keep secret files out of build context without hiding files the runtime or tests actually need.
- Modify: `.env.example`
  - Keep only placeholders and safe defaults.
- Modify: `deployment/.env.example`
  - Keep deployment placeholders only, no live credentials.
- Modify: `README.md`
  - Document the new env bootstrap flow and rotation expectations.
- Modify: `QUICK_START.md`
  - Update local/container setup instructions to copy from example files instead of relying on tracked `.env`.
- Create: `tests/repo-hygiene.test.mjs`
  - Guard against tracking `.env` files and against example files drifting back to live-looking secrets.

### Frontend preview trust boundary

- Modify: `frontend/package.json`
  - Add one sanitizer dependency that works in both app runtime and local tests.
- Create: `frontend/src/lib/sanitize-preview-html.js`
  - Single responsibility: sanitize platform preview HTML before rendering.
- Modify: `frontend/src/components/writer/SplitEditor.tsx`
  - Sanitize preview HTML at the render boundary.
- Create: `tests/sanitize-preview-html.test.mjs`
  - Regression tests for script tags, inline event handlers, and allowed markup.

### Deployment bootstrap and admin provisioning

- Modify: `deployment/scripts/repair_schema_drift.py`
  - Add a dedicated users-tier constraint repair step so runtime drift repair can unblock old databases before provisioning.
- Modify: `scripts/tests/test_repair_schema_drift.py`
  - Assert the users table repair now covers the `superuser` tier constraint path.
- Modify: `deployment/scripts/init_production_state.py`
  - Provision whitelisted super-admins as `is_superuser = TRUE` and `membership_tier = 'superuser'`.
- Create: `scripts/tests/test_init_production_state.py`
  - Lock in the intended update SQL and tier result for whitelisted admin emails.
- Modify: `deployment/docker-start.sh`
  - Replace the current no-op migration block with an explicit sequence: schema repair, Alembic upgrade, production-state initialization.

### Database migration and auth contract

- Create: `backend/api/db/migrations/alembic/versions/20260401_allow_superuser_membership_tier.py`
  - Forward-only migration that updates the `check_membership_tier` constraint for already-deployed databases.
- Modify: `backend/tests/test_auth_exchange.py`
  - Assert admin responses preserve `membership_tier='superuser'` and `is_admin=True`.

### Windows launcher cleanup

- Modify: `start_unified.py`
  - Remove `shell=True` and parse `netstat -ano` output directly.
- Create: `scripts/tests/test_start_unified.py`
  - Verify the Windows branch invokes `subprocess.run` without `shell=True` and kills parsed PIDs correctly.

## Manual Release Notes

These are required after the code lands. They are not optional “maybe later” cleanups.

- Rotate `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, any DB passwords, and any other values that were ever committed.
- Purge the live secrets from git history with `git filter-repo` or BFG after the clean commit exists.
- Recreate local `.env` and `deployment/.env` from the example files after untracking them.
- Rebuild the backend/frontend containers after the env and migration changes land.

### Task 1: Stop tracking live secrets and add repo hygiene guards

**Files:**
- Create: `tests/repo-hygiene.test.mjs`
- Modify: `.gitignore`
- Modify: `.dockerignore`
- Modify: `.env.example`
- Modify: `deployment/.env.example`
- Modify: `README.md`
- Modify: `QUICK_START.md`
- Delete from git index: `.env`
- Delete from git index: `deployment/.env`

- [ ] **Step 1: Write the failing repo hygiene test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'

test('tracked env files are not committed', () => {
  const tracked = execFileSync('git', ['ls-files', '.env', 'deployment/.env'], {
    encoding: 'utf8',
  }).trim()

  assert.equal(tracked, '')
})

test('example env files keep placeholders instead of live secrets', () => {
  const rootExample = readFileSync('.env.example', 'utf8')
  const deployExample = readFileSync('deployment/.env.example', 'utf8')

  assert.match(rootExample, /GOOGLE_CLIENT_ID=your_google_client_id/i)
  assert.match(deployExample, /JWT_SECRET_KEY=CHANGE_ME_TO_A_LONG_RANDOM_VALUE/)
  assert.doesNotMatch(rootExample, /JWT_SECRET_KEY=ipYnDiOOM/i)
  assert.doesNotMatch(deployExample, /ENCRYPTION_KEY=Txnojiw-/i)
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test tests/repo-hygiene.test.mjs`
Expected: FAIL because `.env` and `deployment/.env` are still tracked.

- [ ] **Step 3: Apply the minimal repo hygiene fix**

```bash
git rm --cached .env deployment/.env
```

```gitignore
.env
.env.local
deployment/.env
backend/.env
frontend/.env.local
frontend/.env.production.local
```

```md
cp .env.example .env
cp deployment/.env.example deployment/.env
```

Implementation notes:
- Do not delete the developer’s working local env files from disk, only untrack them.
- Keep `.env.example` and `deployment/.env.example` as the only checked-in templates.
- Update `README.md` and `QUICK_START.md` to tell developers to copy from examples and generate fresh secrets locally.

- [ ] **Step 4: Re-run the repo hygiene test**

Run: `node --test tests/repo-hygiene.test.mjs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .gitignore .dockerignore .env.example deployment/.env.example README.md QUICK_START.md tests/repo-hygiene.test.mjs
git add -u .env deployment/.env
git commit -m "chore: stop tracking live env secrets"
```

### Task 2: Sanitize HTML platform previews before rendering

**Files:**
- Create: `frontend/src/lib/sanitize-preview-html.js`
- Create: `tests/sanitize-preview-html.test.mjs`
- Modify: `frontend/package.json`
- Modify: `frontend/src/components/writer/SplitEditor.tsx`

- [ ] **Step 1: Write the failing sanitizer regression test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { sanitizePreviewHtml } from '../frontend/src/lib/sanitize-preview-html.js'

test('removes scripts and inline event handlers', () => {
  const html = sanitizePreviewHtml(`
    <h1>Safe title</h1>
    <img src="x" onerror="window.__xss = true">
    <script>window.__xss = true</script>
  `)

  assert.match(html, /Safe title/)
  assert.doesNotMatch(html, /<script/i)
  assert.doesNotMatch(html, /onerror=/i)
})

test('keeps normal formatting tags used by the preview', () => {
  const html = sanitizePreviewHtml('<p><strong>Hello</strong> <em>world</em></p>')
  assert.match(html, /<strong>Hello<\/strong>/)
  assert.match(html, /<em>world<\/em>/)
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test tests/sanitize-preview-html.test.mjs`
Expected: FAIL because the sanitizer helper does not exist yet.

- [ ] **Step 3: Add the sanitizer and wire it into `SplitEditor`**

Run: `yarn --cwd frontend add isomorphic-dompurify`

```js
// frontend/src/lib/sanitize-preview-html.js
import DOMPurify from 'isomorphic-dompurify'

export function sanitizePreviewHtml(html) {
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['script', 'style'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick'],
  })
}
```

```tsx
import { sanitizePreviewHtml } from '@/lib/sanitize-preview-html'

<div
  className="p-4"
  dangerouslySetInnerHTML={{ __html: sanitizePreviewHtml(platformPreview.content) }}
/>
```

Implementation notes:
- Sanitize at the last render boundary, not upstream in random API consumers.
- Do not broaden this task into a full editor rewrite.
- Leave `NovelEditor` alone in this pass unless you find a second verified exploit path.

- [ ] **Step 4: Re-run the sanitizer regression test**

Run: `node --test tests/sanitize-preview-html.test.mjs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/src/lib/sanitize-preview-html.js frontend/src/components/writer/SplitEditor.tsx tests/sanitize-preview-html.test.mjs
git commit -m "fix: sanitize writer platform preview html"
```

### Task 3: Make container startup repair schema drift and provision super-admins

**Files:**
- Modify: `deployment/scripts/repair_schema_drift.py`
- Modify: `scripts/tests/test_repair_schema_drift.py`
- Modify: `deployment/scripts/init_production_state.py`
- Create: `scripts/tests/test_init_production_state.py`
- Modify: `deployment/docker-start.sh`

- [ ] **Step 1: Write the failing Python tests for schema repair and admin provisioning**

```py
# scripts/tests/test_init_production_state.py
from deployment.scripts.init_production_state import ensure_super_admins


class RecordingCursor:
    def __init__(self) -> None:
        self.calls = []
        self._fetchone_results = iter([
            {
                "id": 42,
                "email": "wxk952718180@gmail.com",
                "membership_tier": "free",
                "is_superuser": False,
            }
        ])

    def execute(self, statement, params=None):
        self.calls.append((statement, params))

    def fetchone(self):
        return next(self._fetchone_results)


def test_ensure_super_admins_promotes_whitelisted_user_to_superuser_tier(monkeypatch):
    cursor = RecordingCursor()
    monkeypatch.setattr(
        'deployment.scripts.init_production_state.SUPER_ADMIN_EMAILS',
        ['wxk952718180@gmail.com'],
    )

    ensure_super_admins(cursor)

    update_sql, update_params = cursor.calls[1]
    assert "SET is_superuser = TRUE" in update_sql
    assert update_params[0] == "superuser"
    assert update_params[1] == 42
```

```py
# scripts/tests/test_repair_schema_drift.py (new assertion)
from deployment.scripts.repair_schema_drift import ensure_users_columns

def test_ensure_users_columns_repairs_membership_tier_constraint():
    cursor = RecordingCursor()
    ensure_users_columns(cursor)
    executed_sql = "\n".join(cursor.statements)
    assert "DROP CONSTRAINT IF EXISTS check_membership_tier" in executed_sql
    assert "membership_tier IN ('free', 'pro', 'ultra', 'superuser')" in executed_sql
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest scripts/tests/test_repair_schema_drift.py scripts/tests/test_init_production_state.py -q`
Expected: FAIL because the repair script does not handle the tier constraint and the init script still writes `ultra`.

- [ ] **Step 3: Implement the minimal bootstrap fix**

```py
# deployment/scripts/repair_schema_drift.py
def ensure_users_columns(cursor) -> None:
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS membership_tier VARCHAR(20) DEFAULT 'free'")
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE")
    cursor.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_membership_tier")
    cursor.execute("""
        ALTER TABLE users
        ADD CONSTRAINT check_membership_tier
        CHECK (membership_tier IN ('free', 'pro', 'ultra', 'superuser'))
    """)
```

```py
# deployment/scripts/init_production_state.py
target_tier = "superuser"
cursor.execute(
    """
    UPDATE users
    SET is_superuser = TRUE,
        membership_tier = %s,
        updated_at = NOW()
    WHERE id = %s
    """,
    (target_tier, user["id"]),
)
```

```bash
# deployment/docker-start.sh
docker-compose -f docker-compose.full.yml exec -T backend python /app/deployment/scripts/repair_schema_drift.py
docker-compose -f docker-compose.full.yml exec -T backend python -m alembic -c /app/backend/api/db/migrations/alembic.ini upgrade head
docker-compose -f docker-compose.full.yml exec -T backend python /app/deployment/scripts/init_production_state.py
```

Implementation notes:
- Keep the startup flow idempotent. Running it twice should not keep mutating healthy rows.
- Do not keep the current `/app/deployment/postgres/migrations` glob block as the source of truth. It points at a path that does not exist in this repo.
- The repair script is the safety net. Alembic is the canonical schema migration path.

- [ ] **Step 4: Re-run the targeted Python tests**

Run: `pytest scripts/tests/test_repair_schema_drift.py scripts/tests/test_init_production_state.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add deployment/scripts/repair_schema_drift.py scripts/tests/test_repair_schema_drift.py deployment/scripts/init_production_state.py scripts/tests/test_init_production_state.py deployment/docker-start.sh
git commit -m "fix: bootstrap super-admin state in containers"
```

### Task 4: Add a forward migration for the `superuser` membership tier and lock the auth contract

**Files:**
- Create: `backend/api/db/migrations/alembic/versions/20260401_allow_superuser_membership_tier.py`
- Modify: `backend/tests/test_auth_exchange.py`

- [ ] **Step 1: Write the failing backend auth regression test**

```py
def test_exchange_token_returns_superuser_membership_for_whitelisted_admin(monkeypatch):
    monkeypatch.setattr(
        auth_exchange.OAuthAccount,
        "get_oauth_account",
        staticmethod(lambda provider, provider_user_id: {"user_id": 9}),
    )
    monkeypatch.setattr(
        auth_exchange.User,
        "get_user_by_id",
        staticmethod(lambda user_id: {
            "id": user_id,
            "username": "wxk952718180",
            "email": "wxk952718180@gmail.com",
            "display_name": "wxk",
            "avatar_url": None,
            "motto": "创作改变世界",
            "is_superuser": True,
            "membership_tier": "superuser",
        }),
    )
    monkeypatch.setattr(auth_exchange.User, "update_last_login", staticmethod(lambda user_id: True))
    monkeypatch.setattr(auth_exchange, "create_access_token", lambda user_id: f"token-{user_id}")

    response = asyncio.run(
        auth_exchange.exchange_token(
            auth_exchange.ExchangeTokenRequest(
                email="wxk952718180@gmail.com",
                name="wxk",
                google_id="google-user-1",
            )
        )
    )

    assert response.user.is_admin is True
    assert response.user.membership_tier == "superuser"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest backend/tests/test_auth_exchange.py -q`
Expected: FAIL until the new test is added and the migration/provisioning path consistently uses `superuser`.

- [ ] **Step 3: Add a forward-only Alembic migration**

```py
"""allow superuser membership tier"""

from alembic import op

revision = "20260401_allow_superuser_membership_tier"
down_revision = "1169ab91989f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_membership_tier")
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT check_membership_tier
        CHECK (membership_tier IN ('free', 'pro', 'ultra', 'superuser'))
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_membership_tier")
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT check_membership_tier
        CHECK (membership_tier IN ('free', 'pro', 'ultra'))
    """)
```

Implementation notes:
- Do not “fix” this by editing old historical Alembic files only. That does nothing for databases that already ran them.
- If the real `down_revision` differs when you implement, point it at the actual current head after inspecting `backend/api/db/migrations/alembic/versions`.

- [ ] **Step 4: Re-run the backend auth regression test**

Run: `pytest backend/tests/test_auth_exchange.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/db/migrations/alembic/versions/20260401_allow_superuser_membership_tier.py backend/tests/test_auth_exchange.py
git commit -m "fix: allow superuser membership tier in auth flow"
```

### Task 5: Remove `shell=True` from Windows port cleanup

**Files:**
- Create: `scripts/tests/test_start_unified.py`
- Modify: `start_unified.py`

- [ ] **Step 1: Write the failing Windows launcher regression test**

```py
import types
import start_unified


def test_kill_process_on_port_windows_avoids_shell_true(monkeypatch):
    calls = []
    killed = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if command == ['netstat', '-ano']:
            return types.SimpleNamespace(
                stdout='  TCP    0.0.0.0:3000    0.0.0.0:0    LISTENING    1234\\n',
                returncode=0,
            )
        return types.SimpleNamespace(stdout='', returncode=0)

    monkeypatch.setattr(start_unified.sys, 'platform', 'win32')
    monkeypatch.setattr(start_unified.subprocess, 'run', fake_run)
    monkeypatch.setattr(start_unified.time, 'sleep', lambda *_args, **_kwargs: None)

    start_unified.kill_process_on_port(3000)

    assert calls[0][0] == ['netstat', '-ano']
    assert calls[0][1].get('shell', False) is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest scripts/tests/test_start_unified.py -q`
Expected: FAIL because the current implementation passes a piped command with `shell=True`.

- [ ] **Step 3: Replace the Windows branch with direct parsing**

```py
elif sys.platform == 'win32':
    result = subprocess.run(
        ['netstat', '-ano'],
        capture_output=True,
        text=True,
        check=False,
    )
    for line in result.stdout.splitlines():
        if f':{port}' not in line or 'LISTENING' not in line:
            continue
        parts = line.split()
        pid = parts[-1]
        subprocess.run(['taskkill', '/F', '/PID', pid], check=False)
```

Implementation notes:
- Filter lines in Python. Do not smuggle shell pipelines back in through string commands.
- Keep behavior parity: still kill every PID listening on the requested port.

- [ ] **Step 4: Re-run the launcher regression test**

Run: `pytest scripts/tests/test_start_unified.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add start_unified.py scripts/tests/test_start_unified.py
git commit -m "fix: remove shell pipeline from windows port cleanup"
```

## Verification Sweep

- [ ] Run repo hygiene and sanitizer tests:

```bash
node --test tests/repo-hygiene.test.mjs tests/sanitize-preview-html.test.mjs
```

Expected: both PASS

- [ ] Run Python regression tests:

```bash
pytest backend/tests/test_auth_exchange.py scripts/tests/test_repair_schema_drift.py scripts/tests/test_init_production_state.py scripts/tests/test_start_unified.py -q
```

Expected: PASS

- [ ] Smoke-check container bootstrap on a clean local stack:

```bash
bash deployment/docker-start.sh
```

Expected:
- backend container is up
- Alembic upgrade runs without error
- `init_production_state.py` logs that the whitelisted admin row was repaired

- [ ] Smoke-check admin/auth behavior manually:

```bash
docker-compose -f deployment/docker-compose.full.yml exec -T backend python - <<'PY'
from utils.database import Database
with Database.get_cursor() as cursor:
    cursor.execute("SELECT email, is_superuser, membership_tier FROM users WHERE email = %s", ("wxk952718180@gmail.com",))
    print(cursor.fetchone())
PY
```

Expected: `is_superuser=True` and `membership_tier='superuser'`

## Handoff Notes

- Land Task 1 first. There is no point polishing anything else while live secrets are still in git.
- Land Task 3 and Task 4 in the same review window, because they are coupled by the `superuser` tier semantics.
- Do not call the work done until the manual secret rotation steps are finished. Code cleanup without key rotation is theater.
