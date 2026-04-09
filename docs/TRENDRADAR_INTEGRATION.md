# TrendRadar Integration

This document describes the integration of [TrendRadar](https://github.com/sansan0/TrendRadar) into SupaWriter for hotspot data aggregation.

## Overview

TrendRadar is an open-source hotspot aggregation tool that fetches trending topics from multiple Chinese platforms. We've integrated it as a local API service that SupaWriter can call to get hotspot data.

## Architecture

```
┌─────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│   SupaWriter    │────▶│   TrendRadar API    │────▶│   newsnow API    │
│   (port 8000)   │     │   (port 8765)       │     │   (remote)       │
└─────────────────┘     └─────────────────────┘     └──────────────────┘
        │
        ▼
┌─────────────────┐
│   PostgreSQL    │
│   (hotspot_*)   │
└─────────────────┘
```

## Components

### 1. TrendRadar API Server (`/Users/wxk/Desktop/workspace/trendradar/api_server.py`)

A FastAPI server that exposes TrendRadar's data fetching capabilities:

- `GET /health` - Health check
- `GET /api/v1/sources` - List available sources
- `GET /api/v1/latest/{source}` - Get latest hotspots for a source
- `GET /api/v1/latest` - Get latest hotspots for all sources

### 2. SupaWriter Hotspots V2 Service

Updated to use TrendRadar as the primary data source with fallback to newsnow:

```python
# Priority order:
# 1. Local TrendRadar API (http://localhost:8765)
# 2. newsnow API (https://newsnow.busiyi.world/api/s) - fallback
```

### 3. Supported Platforms

| Platform | ID | Name |
|----------|-----|------|
| 百度热搜 | baidu | 百度热搜 |
| 微博 | weibo | 微博热搜 |
| 知乎 | zhihu | 知乎热榜 |
| 抖音 | douyin | 抖音热搜 |
| B站 | bilibili | B站热榜 |
| 今日头条 | toutiao | 今日头条 |
| 贴吧 | tieba | 贴吧 |
| 澎湃新闻 | thepaper | 澎湃新闻 |
| 凤凰网 | ifeng | 凤凰网 |
| 华尔街见闻 | wallstreetcn | 华尔街见闻 |
| 财联社 | cls | 财联社热门 |

## Usage

### Starting Services

```bash
# Start all services (including TrendRadar)
./manage.sh start

# Start only TrendRadar API
./manage.sh start trendradar

# Check status
./manage.sh status
```

### API Endpoints

```bash
# Get all sources
curl http://localhost:8000/api/v1/hotspots/v2/sources

# Get latest hotspots for a source
curl http://localhost:8000/api/v1/hotspots/v2/latest/baidu?limit=10

# Get latest hotspots for all sources
curl http://localhost:8000/api/v1/hotspots/v2/latest?limit=10

# Sync hotspots from TrendRadar
curl -X POST http://localhost:8000/api/v1/hotspots/v2/sync?source=baidu

# Clear cache
curl -X DELETE http://localhost:8000/api/v1/hotspots/v2/cache?source=baidu
```

### Direct TrendRadar API

```bash
# Health check
curl http://localhost:8765/health

# Get sources
curl http://localhost:8765/api/v1/sources

# Get baidu hotspots
curl http://localhost:8765/api/v1/latest/baidu?limit=10
```

## Configuration

### Environment Variables

```bash
# TrendRadar API URL (default: http://localhost:8765)
TRENDRADAR_API_URL=http://localhost:8765

# Fallback newsnow API URL
NEWSNOW_API_URL=https://newsnow.busiyi.world/api/s
```

### manage.sh Options

TrendRadar-specific options in manage.sh:

```bash
TRENDRADAR_PORT=${TRENDRADAR_PORT:-8765}
TRENDRADAR_DIR=${TRENDRADAR_DIR:-"$PROJECT_ROOT/../trendradar"}
```

## Database Schema

The hotspots data is stored in PostgreSQL with three tables:

1. `hotspot_sources` - Platform configurations
2. `hotspot_items` - Hotspot entries with current state
3. `hotspot_rank_history` - Historical rank tracking

## Troubleshooting

### TrendRadar API not starting

```bash
# Check if TrendRadar directory exists
ls -la /Users/wxk/Desktop/workspace/trendradar

# Check logs
./manage.sh logs trendradar

# Manual start
cd /Users/wxk/Desktop/workspace/trendradar
uv run python -m uvicorn api_server:app --host 0.0.0.0 --port 8765
```

### Hotspots not updating

```bash
# Sync manually
curl -X POST http://localhost:8000/api/v1/hotspots/v2/sync

# Clear cache and retry
curl -X DELETE http://localhost:8000/api/v1/hotspots/v2/cache
```

## Files Modified

1. `backend/api/services/hotspots_v2_service.py` - Updated to use TrendRadar API
2. `manage.sh` - Added TrendRadar service management
3. `/Users/wxk/Desktop/workspace/trendradar/api_server.py` - New API server

## Future Improvements

1. Add Docker Compose integration for TrendRadar
2. Implement rate limiting for API calls
3. Add webhook support for real-time updates
4. Implement keyword filtering and AI analysis from TrendRadar
