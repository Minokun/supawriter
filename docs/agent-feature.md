# Writing Agent Feature Documentation

## Overview

The Writing Agent automates content creation by monitoring hotspots/news and generating article drafts. Two operational modes are supported:

1. **Intelligent Topic Selection** (has `topic_id`): Uses LLM to filter and rank news/hotspots by relevance to a user-defined topic, then generates top-N articles.
2. **Legacy Hotspot Matching** (no `topic_id`): Simple keyword matching against hotspot feeds, generates drafts for matches.

## Architecture

```
Frontend (Next.js)
  ├── Agent Page (CRUD, trigger, logs, batch review)
  ├── useAgentWebSocket hook (real-time notifications)
  └── agentApi (REST client)

Backend (FastAPI)
  ├── Routes: /api/v1/agents/*
  ├── AgentService (DB operations, draft management)
  ├── TopicSelector (LLM-based topic ranking)
  ├── agent_worker (ARQ scheduled tasks)
  └── WebSocket notifications (ConnectionManager)
```

## Database Models

### WritingAgent
| Field | Type | Description |
|-------|------|-------------|
| `topic_id` | UUID (nullable) | Bound user topic for intelligent mode |
| `news_sources` | JSON array | News API sources (e.g., `["澎湃科技", "实时新闻"]`) |
| `schedule_cron` | String | Execution interval: `30min`, `1h`, `6h`, `12h`, `24h` |
| `article_count` | Integer | Articles per trigger (1-3) |

### AgentExecutionLog
Tracks each scan execution with mode, trigger type, status, timing, and results.

**Migration**: `deployment/migrate/011_agent_intelligent_topics.sql`, `012_agent_execution_logs.sql`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/agents` | List user agents |
| POST | `/api/v1/agents` | Create agent |
| PUT | `/api/v1/agents/{id}` | Update agent |
| DELETE | `/api/v1/agents/{id}` | Delete agent |
| POST | `/api/v1/agents/{id}/trigger` | Manual trigger |
| GET | `/api/v1/agents/{id}/logs` | Get execution logs |
| GET | `/api/v1/agents/drafts` | List drafts |
| POST | `/api/v1/agents/drafts/batch-review` | Batch accept/discard |

## WebSocket Events

| Event Type | Direction | Description |
|-----------|-----------|-------------|
| `agent_trigger_started` | Server → Client | Scan has begun |
| `agent_trigger_completed` | Server → Client | Scan finished (with results) |
| `agent_draft_ready` | Server → Client | Individual draft generated |

## Error Handling & Retry

- `backend/api/core/retry.py` provides `@async_retry` decorator and `retry_async` helper
- Applied to: `get_active_agents`, `get_all_hotspots`, `create_execution_log`, `update_execution_log`
- Retries transient DB errors (OperationalError, DisconnectionError) and network errors (ConnectError, ReadTimeout)
- Exponential backoff: `base * 2^attempt`, capped at 30s

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_core/test_retry.py` | 11 | Retry decorator + functional helper |
| `test_services/test_agent_worker.py` | 28 | Schedule logic, hotspot evaluation |
| `test_services/test_topic_selector.py` | 22 | Prompt formatting, matching, LLM parsing |
| `integration/test_agent_api.py` | 14 | CRUD, trigger, logs, batch review endpoints |

**Total: 75 tests**

## Deployment Checklist

1. **Run migrations** (in order):
   ```bash
   psql -f deployment/migrate/011_agent_intelligent_topics.sql
   psql -f deployment/migrate/012_agent_execution_logs.sql
   ```

2. **Verify ARQ worker** has `trigger_single_agent` registered in `worker_settings.py`

3. **Rebuild frontend**:
   ```bash
   cd frontend && npm run build
   ```

4. **Restart services**: Backend API, ARQ worker

5. **Verify**: Hit `GET /api/v1/agents` to confirm new fields are returned
