# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SupaWriter is an AI-powered article writing assistant with two architectures:
1. **Streamlit** (port 8501) - Python single-app for rapid prototyping
2. **FastAPI + Next.js** (ports 8000/3000) - Production-ready frontend/backend separation

Both architectures share the same `utils/` modules and database, allowing them to run concurrently.

## Common Commands

### Service Management (Recommended)
```bash
./manage.sh start      # Start frontend + backend
./manage.sh stop       # Stop all services
./manage.sh status     # Check service status
./manage.sh logs all   # View all logs (or: backend, frontend)
./manage.sh restart    # Restart services
```

### Streamlit Only
```bash
streamlit run web.py   # Start Streamlit app
uv run streamlit run web.py  # With uv
```

### Backend (FastAPI)
```bash
cd backend && uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Next.js)
```bash
cd frontend && npm run dev    # Development (port 3000)
cd frontend && npm run build  # Production build
cd frontend && npm run lint   # Lint check
```

### Testing
```bash
# Backend Python tests
cd backend && pytest -v                           # All tests
cd backend && pytest tests/unit -v                # Unit tests only
cd backend && pytest tests/integration -v         # Integration tests
cd backend && pytest -k "test_name" -v            # Run specific test
cd backend && pytest -m "not slow" -v             # Skip slow tests

# Frontend E2E tests (Playwright)
npx playwright test                               # Run all Playwright tests
npx playwright test tests/p1-sprint56.spec.ts     # Run specific spec
```

## Architecture

### Backend (`backend/api/`)
- `main.py` - FastAPI app entry point, route registration
- `routes/` - API endpoints (auth, articles, chat, batch, settings, etc.)
- `services/` - Business logic layer (article generation, SEO, subscriptions)
- `models/` - SQLAlchemy ORM models
- `repositories/` - Database access layer
- `core/` - Cross-cutting concerns (encryption, redis, rate limiting)
- `workers/` - Background task workers (arq)

### Frontend (`frontend/src/`)
- `app/` - Next.js App Router pages (workspace, writer, batch, settings, etc.)
- `components/ui/` - Reusable UI components
- `components/writer/` - Article writing components
- `lib/api.ts` - TypeScript API client
- `lib/api/` - API module organization

### Shared Utils (`utils/`)
- `llm_chat.py` - LLM integration (OpenAI, DeepSeek)
- `searxng_utils.py` - Search engine utilities
- `database.py` / `db_adapter.py` - Database operations
- `prompt_template.py` - LLM prompt templates
- `wechat_converter.py` - WeChat article formatting
- `platform_converter.py` - Multi-platform content conversion
- `embedding_utils.py` - Vector embeddings and FAISS indexing

### Data (`data/`)
Runtime data storage: FAISS indexes, chat history, user sessions, SQLite DB.

## Key Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Backend environment (DB, Redis, API keys) |
| `.env.example` | Template with all config options |
| `frontend/.env.local` | Frontend environment |
| `.streamlit/secrets.toml` | Streamlit API keys and OAuth |

## Ports
- **3000**: Next.js frontend
- **8000**: FastAPI backend (docs at `/docs`)
- **8501**: Streamlit app
- **5432**: PostgreSQL
- **6379**: Redis

## Database

PostgreSQL is the primary database. SQLite (`data/supawriter.db`) available for development. Database migrations managed via Alembic in `deployment/migrate/`.

## Development Notes

- Use `uv` for Python package management: `uv sync`, `uv run <command>`
- Frontend uses yarn: `yarn install`, `yarn dev`
- Backend follows repository pattern: Routes → Services → Repositories → Models
- Article generation uses streaming responses for real-time output
- Authentication: Google OAuth, WeChat OAuth, and local accounts
