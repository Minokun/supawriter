# 热点数据集成设计

## 概述

集成 newsnow API 作为统一热点数据源，替换现有的自建爬虫，实现热点数据的持久化存储和排名变化追踪，为后续趋势分析打下基础。

使用 Docker 容器化部署。

## 数据源

| 维度 | 说明 |
|------|------|
| **API** | newsnow API (`https://newsnow.busiyi.world/api/s`) |
| **平台** | 百度、微博、抖音、知乎、 B站、 澎湃、36氪、 财联社、 华尔街见闻等 11+ 平台 |
| **优势** | 统一数据格式、 11+ 平台覆盖, 公开 API 稳定 |

## 数据结构

### newsnow API 卬应格式
```json
{
  "status": "success",
  "id": "baidu",
  "updatedTime": 1772198859214,
  "items": [
    {
      "id": "https://www.baidu.com/s?wd=...",
      "title": "美团、淘宝、京东齐发声",
      "url": "https://www.baidu.com/s?wd=...",
      "extra": {
        "hover": "描述文本..."
      }
    }
  ]
}
```

### 统一后的热点数据格式
```python
{
    "id": str,              # 唯一标识 (来自 newsnow 的 id 字段)
    "title": str,           # 标题
    "url": str,             # 原始链接
    "mobile_url": str,      # 移动端链接 (可选)
    "source": str,          # 来源平台 (baidu/weibo/douyin...)
    "rank": int,             # 当前排名
    "hot_value": int,       # 热度值 (可能为空)
    "is_new": bool,          # 是否新增
    "description": str,     # 描述/摘要
    "icon_url": str,         # 热榜标记图标
    "published_at": datetime, # 发布时间
    "created_at": datetime, # 入库时间
    "updated_at": datetime  # 更新时间
}
```

## 数据库设计

### 表1: `hotspot_items`
热点主表，| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| title | VARCHAR(255) | 标题 (索引) |
| url | VARCHAR(500) | 鎟链接 |
| source | VARCHAR(50) | 来源平台 (索引) |
| source_id | VARCHAR(100) | 平台内部ID (索引) |
| hot_value | INTEGER | 热度值 |
| hot_value_prev | INTEGER | 上次热度值 |
| rank | INTEGER | 当前排名 (索引) |
| rank_prev | INTEGER | 上次排名 |
| rank_change | INTEGER | 排名变化 (正升负降) |
| is_new | BOOLEAN | 是否新增 |
| description | TEXT | 描述 |
| icon_url | VARCHAR(255) | 图标URL |
| mobile_url | VARCHAR(500) | 移动端链接 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

约束: `(title, source)` 噺一

### 表2: `hotspot_rank_history`
排名历史表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| hotspot_item_id | INTEGER | 关联热点ID |
| source | VARCHAR(50) | 来源平台 |
| rank | INTEGER | 记录时排名 |
| hot_value | INTEGER | 记录时热度 |
| is_new | BOOLEAN | 是否新增 |
| recorded_at | TIMESTAMP | 记录时间 |

索引: `(hotspot_item_id, recorded_at)`

### 表3: `hotspot_sources`
平台配置表 (可选)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(50) | 平台ID (baidu/weibo...) |
| name | VARCHAR(100) | 显示名称 |
| icon | VARCHAR(10) | 图标 (emoji) |
| enabled | BOOLEAN | 是否启用 |
| sort_order | INTEGER | 排序顺序 |
| category | VARCHAR(50) | 分类 |

## API 设计

### 新增端点
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/hotspots/v2/sources` | GET | 获取支持的平台列表 |
| `/api/hotspots/v2/latest` | GET | 获取最新热点 (各平台前N条) |
| `/api/hotspots/v2/latest/{source}` | GET | 获取指定平台热点 |
| `/api/hotspots/v2/history/{source}` | GET | 获取历史热点 |
| `/api/hotspots/v2/trend/{keyword}` | GET | 获取关键词趋势 |
| `/api/hotspots/v2/sync` | POST | 手动同步热点 |

## 服务层设计

### HotspotsCollectorService
```python
class HotspotsCollectorService:
    """热点采集服务"""

    def __init__(self, api_url: str, database: Database
    redis: Redis
    ):
        self.api_url = api_url
        self.fetcher = DataFetcher()

    async def fetch_all_sources(self) -> Dict[str, List[HotspotItem]]:
        """获取所有启用平台的热点"""

    async def fetch_source(self, source_id: str) -> List[HotspotItem]:
        """获取指定平台热点"""

    async def sync_and_save(self, sources: List[str]) -> SyncResult:
        """同步并保存热点数据"""

    def _parse_hot_value(self, item: dict) -> Optional[int]:
        """解析热度值"""

    def _detect_rank_change(self, current: int, previous: int) -> int:
        """计算排名变化"""

    def _is_new_hotspot(self, title: str, source: str) -> bool:
        """检测是否新增热点"""

    def _save_to_database(self, items: List[HotspotItem]) -> None:
        """保存到数据库"""

    def _update_rank_history(self, item: HotspotItem) -> None:
        """更新排名历史"""
```

## 定时任务设计

- 使用 APScheduler 或 Celery Beat
- 每 10 分钟抓取一次
- 比较排名变化
- 持久化到数据库

## Docker 部署

### Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 启动热点采集服务
CMD ["python", "-m", "backend.hotspots.worker"]
```

### docker-compose.yml
```yaml
services:
  hotspots-collector:
    build:
      context: .
      dockerfile: Dockerfile.hotspots
    environment:
      - NEWSNOW_API_URL=https://newsnow.busiyi.world/api/s
      - SYNC_INTERVAL_MINUTES=10
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
    depends:
      - postgres
      - redis
    networks:
      - supawriter-network
```

## 前端展示
- 热点列表显示排名变化趋势 (↑/↓/→/数字)
- 新增热点标记
- 排名历史图表
- 热度值趋势图

## 后续扩展
- 趋势分析 API
- 热点预测
- 关键词共现分析
- 情感分析
