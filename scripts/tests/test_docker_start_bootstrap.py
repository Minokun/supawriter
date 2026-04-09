from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCKER_COMPOSE = ROOT / "deployment" / "docker-compose.yml"
DOCKER_START = ROOT / "deployment" / "docker-start.sh"
BOOTSTRAP_SQL = ROOT / "deployment" / "postgres" / "bootstrap" / "001_extensions.sql"


def test_docker_compose_uses_bootstrap_init_directory():
    compose_text = DOCKER_COMPOSE.read_text(encoding="utf-8")

    assert "./postgres/bootstrap:/docker-entrypoint-initdb.d" in compose_text
    assert "./postgres/init:/docker-entrypoint-initdb.d" not in compose_text


def test_postgres_bootstrap_enables_required_extensions():
    bootstrap_sql = BOOTSTRAP_SQL.read_text(encoding="utf-8")

    assert 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";' in bootstrap_sql
    assert 'CREATE EXTENSION IF NOT EXISTS "pg_trgm";' in bootstrap_sql
    assert 'CREATE EXTENSION IF NOT EXISTS "pgcrypto";' in bootstrap_sql


def test_docker_start_runs_bootstrap_chain_before_app_services():
    script_text = DOCKER_START.read_text(encoding="utf-8")

    infra_up = 'docker-compose -f "$COMPOSE_FILE" up -d postgres redis trendradar'
    repair = 'docker-compose -f "$COMPOSE_FILE" run --rm backend python /app/deployment/scripts/repair_schema_drift.py'
    alembic = 'docker-compose -f "$COMPOSE_FILE" run --rm backend python -m alembic -c /app/backend/api/db/migrations/alembic.ini upgrade head'
    init_state = 'docker-compose -f "$COMPOSE_FILE" run --rm backend python /app/deployment/scripts/init_production_state.py'
    app_up = 'docker-compose -f "$COMPOSE_FILE" up -d backend worker frontend nginx'

    for fragment in (infra_up, repair, alembic, init_state, app_up):
        assert fragment in script_text

    assert "PG_READY_MAX_ATTEMPTS=" in script_text
    assert 'pg_ready_attempt=0' in script_text
    assert 'while ! docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "${POSTGRES_USER:-supawriter}" > /dev/null 2>&1; do' in script_text
    assert 'if [ "$pg_ready_attempt" -ge "$PG_READY_MAX_ATTEMPTS" ]; then' in script_text
    assert 'exit 1' in script_text

    assert script_text.index(infra_up) < script_text.index(repair)
    assert script_text.index(repair) < script_text.index(alembic)
    assert script_text.index(alembic) < script_text.index(init_state)
    assert script_text.index(init_state) < script_text.index(app_up)
