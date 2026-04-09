# P0 技术设计文档 — 爆款基因植入

> **创建日期**: 2026-02-15
> **版本**: v1.0
> **关联PRD**: `docs/plans/2026-02-15-p0-prd.md`
> **关联总纲**: `docs/plans/2026-02-15-development-master-plan.md`

---

## 一、架构总览

### 1.1 P0 功能在系统中的位置

```
┌─────────────────── Frontend (Next.js) ───────────────────┐
│                                                          │
│  热点页        写作页        预览页        设置页          │
│  ┌─────┐     ┌─────┐     ┌──────┐     ┌──────┐         │
│  │F1:  │────▶│写作  │────▶│F3:   │     │F5:   │         │
│  │写这个│     │生成  │     │多平台 │     │风格   │         │
│  └─────┘     └──┬──┘     │预览   │     │学习   │         │
│                 │        └──────┘     └──────┘         │
│                 ▼                                       │
│           ┌──────────┐                                  │
│           │F4: 评分卡 │                                  │
│           └──────────┘                                  │
│                                                          │
│  F6: 新用户引导 (Onboarding Overlay)                      │
│  F2: 水印注入 (输出层，非独立页面)                          │
└──────────────────────────────────────────────────────────┘
                          │
                    API Layer
                          │
┌─────────────────── Backend (FastAPI) ────────────────────┐
│                                                          │
│  routes/                                                 │
│  ├── hotspots.py        (已有，无需修改)                   │
│  ├── articles.py        (扩展: 评分API、平台转换API)       │
│  ├── user_style.py      (新增: 风格学习API)               │
│  └── onboarding.py      (新增: 引导状态API)               │
│                                                          │
│  services/                                               │
│  ├── article_scoring.py (新增: 评分引擎)                   │
│  ├── platform_converter.py (新增: 多平台转换)              │
│  └── style_analyzer.py  (新增: 风格分析)                   │
│                                                          │
│  utils/                                                  │
│  ├── wechat_converter.py (已有，保持不变)                  │
│  └── watermark.py       (新增: 水印注入)                   │
│                                                          │
│  workers/                                                │
│  └── article_worker.py  (修改: 生成后触发评分+风格注入)     │
└──────────────────────────────────────────────────────────┘
```

### 1.2 新增/修改文件清单

| 类型 | 文件路径 | 操作 | 说明 |
|------|---------|------|------|
| **后端-路由** | `backend/api/routes/user_style.py` | 新增 | 风格学习CRUD API |
| **后端-服务** | `backend/api/services/article_scoring.py` | 新增 | 文章评分引擎 |
| **后端-服务** | `backend/api/services/platform_converter.py` | 新增 | 多平台格式转换 |
| **后端-服务** | `backend/api/services/style_analyzer.py` | 新增 | 写作风格分析 |
| **后端-工具** | `backend/api/utils/watermark.py` | 新增 | 水印注入工具 |
| **后端-Worker** | `backend/api/workers/article_worker.py` | 修改 | 生成后触发评分 |
| **后端-路由** | `backend/api/routes/articles_enhanced.py` | 修改 | 新增评分/转换端点 |
| **后端-主入口** | `backend/api/main.py` | 修改 | 注册新路由 |
| **前端-页面** | `frontend/src/app/hotspots/` | 修改 | 添加"写这个"按钮 |
| **前端-页面** | `frontend/src/app/writer/page.tsx` | 修改 | 接收热点参数预填 |
| **前端-组件** | `frontend/src/components/article/ScoreCard.tsx` | 新增 | 评分卡片组件 |
| **前端-组件** | `frontend/src/components/article/PlatformPreview.tsx` | 新增 | 多平台预览组件 |
| **前端-组件** | `frontend/src/components/onboarding/OnboardingFlow.tsx` | 新增 | 引导流程组件 |
| **前端-页面** | `frontend/src/app/settings/` | 修改 | 添加风格学习入口 |
| **数据库** | `deployment/migrate/008_p0_features.sql` | 新增 | 数据库迁移 |

---

## 二、数据库变更

### 2.1 新增表

#### user_writing_styles — 用户写作风格

```sql
CREATE TABLE IF NOT EXISTS user_writing_styles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    style_profile JSONB NOT NULL DEFAULT '{}',
    -- style_profile 结构:
    -- {
    --   "tone": "理性分析型，适度幽默",
    --   "sentence_style": "偏好短句，善用设问",
    --   "paragraph_structure": "总分总，数据驱动",
    --   "vocabulary": "善用比喻解释复杂概念",
    --   "opening_style": "常以故事或场景描写开头",
    --   "closing_style": "常以总结+行动号召结尾",
    --   "raw_analysis": "完整的LLM分析文本"
    -- }
    sample_filenames TEXT[] DEFAULT '{}',
    sample_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_user_writing_style UNIQUE (user_id)
);

CREATE INDEX idx_user_writing_styles_user_id ON user_writing_styles(user_id);

COMMENT ON TABLE user_writing_styles IS '用户写作风格配置，每个用户最多一条记录';
```

#### article_scores — 文章评分缓存

```sql
CREATE TABLE IF NOT EXISTS article_scores (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    total_score INTEGER NOT NULL CHECK (total_score >= 0 AND total_score <= 100),
    level VARCHAR(20) NOT NULL, -- 'excellent', 'good', 'average', 'poor'
    summary TEXT NOT NULL,
    dimensions JSONB NOT NULL DEFAULT '[]',
    -- dimensions 结构:
    -- [
    --   { "name": "readability", "label": "可读性", "score": 82, "weight": 0.3, "suggestions": ["..."] },
    --   { "name": "information_density", "label": "信息密度", "score": 70, "weight": 0.25, "suggestions": ["..."] },
    --   { "name": "seo_friendliness", "label": "SEO友好度", "score": 80, "weight": 0.25, "suggestions": ["..."] },
    --   { "name": "virality", "label": "传播潜力", "score": 75, "weight": 0.2, "suggestions": ["..."] }
    -- ]
    scored_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_article_score UNIQUE (article_id)
);

CREATE INDEX idx_article_scores_article_id ON article_scores(article_id);

COMMENT ON TABLE article_scores IS '文章质量评分，每篇文章一条评分记录';
```

#### user_onboarding — 用户引导状态

```sql
CREATE TABLE IF NOT EXISTS user_onboarding (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    completed BOOLEAN DEFAULT FALSE,
    user_role VARCHAR(50), -- 'media_operator', 'marketer', 'freelancer', 'personal_ip'
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_user_onboarding UNIQUE (user_id)
);

COMMENT ON TABLE user_onboarding IS '新用户引导状态';
```

### 2.2 完整迁移文件

文件路径: `deployment/migrate/008_p0_features.sql`

```sql
-- Migration 008: P0 爆款基因植入功能
-- Date: 2026-02-15
-- Features: 写作风格、文章评分、用户引导

BEGIN;

-- 1. 用户写作风格表
CREATE TABLE IF NOT EXISTS user_writing_styles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    style_profile JSONB NOT NULL DEFAULT '{}',
    sample_filenames TEXT[] DEFAULT '{}',
    sample_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_writing_style UNIQUE (user_id)
);
CREATE INDEX IF NOT EXISTS idx_user_writing_styles_user_id ON user_writing_styles(user_id);

-- 2. 文章评分表
CREATE TABLE IF NOT EXISTS article_scores (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    total_score INTEGER NOT NULL CHECK (total_score >= 0 AND total_score <= 100),
    level VARCHAR(20) NOT NULL,
    summary TEXT NOT NULL,
    dimensions JSONB NOT NULL DEFAULT '[]',
    scored_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_article_score UNIQUE (article_id)
);
CREATE INDEX IF NOT EXISTS idx_article_scores_article_id ON article_scores(article_id);

-- 3. 用户引导状态表
CREATE TABLE IF NOT EXISTS user_onboarding (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    completed BOOLEAN DEFAULT FALSE,
    user_role VARCHAR(50),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_onboarding UNIQUE (user_id)
);

COMMIT;
```

---

## 三、API 接口设计

### 3.1 文章评分 API

#### GET /api/v1/articles/{article_id}/score

获取文章评分。如果尚未评分，自动触发评分。

**请求**:
```
GET /api/v1/articles/123/score
Authorization: Bearer {token}
```

**响应 (Free用户)**:
```json
{
    "total_score": 78,
    "level": "good",
    "summary": "文章结构清晰，建议补充更多数据支撑",
    "dimensions": null,
    "upgrade_hint": "升级Pro查看详细评分和优化建议"
}
```

**响应 (Pro/Ultra用户)**:
```json
{
    "total_score": 78,
    "level": "good",
    "summary": "文章结构清晰，建议补充更多数据支撑",
    "dimensions": [
        {
            "name": "readability",
            "label": "可读性",
            "score": 82,
            "suggestions": [
                "第3段过长(320字)，建议拆分为2段",
                "建议在第2节和第3节之间添加过渡句"
            ]
        },
        {
            "name": "information_density",
            "label": "信息密度",
            "score": 70,
            "suggestions": [
                "缺少数据引用，建议添加统计数据",
                "第4段的论述缺乏具体案例支撑"
            ]
        },
        {
            "name": "seo_friendliness",
            "label": "SEO友好度",
            "score": 80,
            "suggestions": [
                "标题可更具吸引力，建议: \"...\"",
                "建议在前100字内出现核心关键词"
            ]
        },
        {
            "name": "virality",
            "label": "传播潜力",
            "score": 75,
            "suggestions": [
                "开头缺少hook，建议用提问或数据开场",
                "结尾可添加互动引导(提问/投票)"
            ]
        }
    ]
}
```

**错误响应**:
- `404`: 文章不存在或无权访问
- `503`: 评分服务暂时不可用

---

### 3.2 多平台格式转换 API

#### POST /api/v1/articles/{article_id}/convert

**请求**:
```json
{
    "platform": "zhihu",  // "wechat" | "zhihu" | "xiaohongshu" | "toutiao"
    "topic": "可选，用于生成话题标签"
}
```

**响应**:
```json
{
    "content": "转换后的内容...",
    "format": "markdown",  // "html" | "markdown" | "text"
    "tags": ["#人工智能", "#科技趋势", "#深度分析"],
    "word_count": 2850,
    "copy_format": "plain_text",  // "rich_text" | "plain_text"
    "platform": "zhihu"
}
```

**注意**: 小红书转换涉及LLM改写，响应时间较长（~10s），前端需显示loading。

---

### 3.3 写作风格 API

#### POST /api/v1/user/writing-style/analyze

上传范文并分析风格。

**请求**:
```json
{
    "samples": [
        { "filename": "我的爆款文章.md", "content": "文章内容..." },
        { "filename": "知乎高赞回答.md", "content": "文章内容..." },
        { "filename": "行业分析报告.md", "content": "文章内容..." }
    ]
}
```

**校验规则**:
- `samples` 数量: 3-5篇
- 每篇 `content` 字数: ≥ 500字
- 每篇 `content` 大小: ≤ 50KB

**响应**:
```json
{
    "style_profile": {
        "tone": "理性分析型，适度幽默",
        "sentence_style": "偏好短句，善用设问句引导思考",
        "paragraph_structure": "总分总结构，数据驱动论证",
        "vocabulary": "善用比喻解释复杂概念，少用成语",
        "opening_style": "常以故事或场景描写开头",
        "closing_style": "常以总结+行动号召结尾"
    },
    "summary": "您的写作风格偏理性分析，善于用数据和比喻让复杂概念易于理解，文章结构清晰，节奏感强。",
    "sample_count": 3
}
```

#### GET /api/v1/user/writing-style

获取当前风格配置。

**响应**:
```json
{
    "has_style": true,
    "style_profile": { ... },
    "summary": "...",
    "is_active": true,
    "sample_count": 3,
    "sample_filenames": ["我的爆款文章.md", "知乎高赞回答.md", "行业分析报告.md"],
    "updated_at": "2026-02-15T10:00:00Z"
}
```

#### PUT /api/v1/user/writing-style/toggle

开启/关闭风格应用。

**请求**: `{ "is_active": false }`
**响应**: `{ "success": true, "is_active": false }`

#### DELETE /api/v1/user/writing-style

删除风格配置。

**响应**: `{ "success": true }`

---

### 3.4 用户引导 API

#### GET /api/v1/user/onboarding

获取引导状态。

**响应**:
```json
{
    "completed": false,
    "user_role": null
}
```

#### POST /api/v1/user/onboarding/complete

完成引导。

**请求**:
```json
{
    "user_role": "media_operator"  // 可选
}
```

**响应**: `{ "success": true }`

---

## 四、核心服务设计

### 4.1 文章评分引擎 (`article_scoring.py`)

```python
"""
文章评分引擎

评分策略:
1. 可读性: 规则引擎（段落长度、句子数、标题层次等可计算指标）
2. 信息密度/SEO/传播力: LLM评分（通过Prompt让LLM评估并返回结构化JSON）

这样设计的原因:
- 可读性指标可精确计算，不需要浪费LLM调用
- 其他维度需要语义理解，适合LLM评估
- 混合方案兼顾速度和准确性
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class DimensionScore:
    name: str
    label: str
    score: int          # 0-100
    weight: float
    suggestions: list[str]

@dataclass
class ArticleScore:
    total_score: int
    level: str          # 'excellent' | 'good' | 'average' | 'poor'
    summary: str
    dimensions: list[DimensionScore]


class ArticleScoringService:
    """文章评分服务"""
    
    async def score_article(
        self, 
        content: str, 
        title: str, 
        topic: str = ""
    ) -> ArticleScore:
        """
        对文章进行多维度评分
        
        流程:
        1. 规则引擎计算可读性分数
        2. LLM评估其余三个维度
        3. 加权计算总分
        4. 生成评语和建议
        """
        # Step 1: 规则引擎 - 可读性
        readability = self._score_readability(content)
        
        # Step 2: LLM评分 - 信息密度、SEO、传播力
        llm_scores = await self._llm_score(content, title, topic)
        
        # Step 3: 合并计算
        dimensions = [readability] + llm_scores
        total = sum(d.score * d.weight for d in dimensions)
        total_score = round(total)
        
        # Step 4: 确定等级
        level = self._get_level(total_score)
        summary = self._generate_summary(total_score, dimensions)
        
        return ArticleScore(
            total_score=total_score,
            level=level,
            summary=summary,
            dimensions=dimensions
        )
    
    def _score_readability(self, content: str) -> DimensionScore:
        """
        规则引擎评估可读性
        
        评分因子:
        - 平均段落长度 (理想: 100-200字)
        - 平均句子长度 (理想: 20-40字)
        - 标题层次使用 (有h2/h3加分)
        - 列表/表格使用 (有加分)
        - 过渡词使用频率
        """
        suggestions = []
        score = 80  # 基础分
        
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        
        # 段落长度评估
        long_paras = [p for p in paragraphs if len(p) > 300]
        if long_paras:
            score -= len(long_paras) * 3
            suggestions.append(
                f"有{len(long_paras)}个段落超过300字，建议拆分"
            )
        
        # 标题层次
        has_h2 = '## ' in content
        has_h3 = '### ' in content
        if not has_h2:
            score -= 10
            suggestions.append("缺少二级标题，建议添加章节划分")
        
        # 列表使用
        has_list = '- ' in content or '1. ' in content
        if has_list:
            score += 5
        
        score = max(0, min(100, score))
        
        return DimensionScore(
            name="readability",
            label="可读性",
            score=score,
            weight=0.3,
            suggestions=suggestions
        )
    
    async def _llm_score(
        self, content: str, title: str, topic: str
    ) -> list[DimensionScore]:
        """
        LLM评估信息密度、SEO友好度、传播潜力
        
        使用单次LLM调用评估三个维度，返回结构化JSON
        """
        from utils.llm_chat import chat
        
        prompt = f"""请对以下文章进行质量评估，从三个维度打分(0-100)并给出具体建议。

文章标题: {title}
文章主题: {topic}
文章内容:
{content[:3000]}  

请严格按以下JSON格式返回:
{{
    "information_density": {{
        "score": 75,
        "suggestions": ["建议1", "建议2"]
    }},
    "seo_friendliness": {{
        "score": 80,
        "suggestions": ["建议1", "建议2"]
    }},
    "virality": {{
        "score": 70,
        "suggestions": ["建议1", "建议2"]
    }}
}}

评分标准:
- information_density(信息密度): 数据引用、事实支撑、论据充分性、信息量
- seo_friendliness(SEO友好度): 标题吸引力、关键词自然分布、结构清晰度
- virality(传播潜力): 开头吸引力、情感共鸣、分享动机、互动引导"""
        
        # 调用LLM并解析JSON响应
        # ... 实现省略，使用现有 chat() 函数
        pass
    
    def _get_level(self, score: int) -> str:
        if score >= 90: return "excellent"
        if score >= 75: return "good"
        if score >= 60: return "average"
        return "poor"
    
    def _generate_summary(
        self, total: int, dims: list[DimensionScore]
    ) -> str:
        """生成一句话评语"""
        # 找到最高分和最低分维度
        best = max(dims, key=lambda d: d.score)
        worst = min(dims, key=lambda d: d.score)
        return f"{best.label}表现突出，建议重点提升{worst.label}"
```

### 4.2 多平台转换器 (`platform_converter.py`)

```python
"""
多平台格式转换器

设计原则:
- 微信/知乎/头条: 纯规则转换，不调用LLM，响应快
- 小红书: 需要LLM改写（缩短+口语化+emoji），响应较慢
"""

class PlatformConverter:
    
    SUPPORTED_PLATFORMS = ["wechat", "zhihu", "xiaohongshu", "toutiao"]
    
    async def convert(
        self, 
        markdown_content: str, 
        platform: str, 
        topic: str = ""
    ) -> dict:
        if platform == "wechat":
            return self._convert_wechat(markdown_content)
        elif platform == "zhihu":
            return self._convert_zhihu(markdown_content, topic)
        elif platform == "xiaohongshu":
            return await self._convert_xiaohongshu(markdown_content, topic)
        elif platform == "toutiao":
            return self._convert_toutiao(markdown_content)
        else:
            raise ValueError(f"不支持的平台: {platform}")
    
    def _convert_wechat(self, content: str) -> dict:
        """复用现有 wechat_converter"""
        from utils.wechat_converter import markdown_to_wechat_html
        html = markdown_to_wechat_html(content)
        return {
            "content": html,
            "format": "html",
            "tags": [],
            "word_count": len(content),
            "copy_format": "rich_text"
        }
    
    def _convert_zhihu(self, content: str, topic: str) -> dict:
        """
        知乎格式: Markdown，但需调整
        - h1 → h2 (知乎不支持一级标题)
        - 关键结论加粗
        - 文末添加话题标签建议
        """
        # 标题降级
        lines = content.split('\n')
        converted = []
        for line in lines:
            if line.startswith('# ') and not line.startswith('## '):
                converted.append('#' + line)  # h1 → h2
            else:
                converted.append(line)
        
        result = '\n'.join(converted)
        
        # 生成话题标签（基于规则，不调用LLM）
        tags = self._generate_tags_rule_based(topic, content)
        
        return {
            "content": result,
            "format": "markdown",
            "tags": tags,
            "word_count": len(content),
            "copy_format": "plain_text"
        }
    
    async def _convert_xiaohongshu(self, content: str, topic: str) -> dict:
        """
        小红书格式: 需要LLM改写
        - 缩短到800-1200字
        - 口语化风格
        - 添加emoji
        - 生成话题标签
        """
        from utils.llm_chat import chat
        
        prompt = f"""请将以下文章改写为小红书风格的帖子。

要求:
1. 字数控制在800-1200字
2. 使用口语化、亲切的语气
3. 每段不超过3句话
4. 适当使用emoji作为段落标记(✅ ❌ 💡 📌 🔥 等)
5. 标题用emoji开头
6. 文末生成5-10个话题标签，格式为 #话题#

原文:
{content[:3000]}"""
        
        result = chat(
            prompt=prompt,
            system_prompt="你是一个专业的小红书内容运营，擅长将长文改写为小红书爆款帖子。",
            model_type="deepseek",
            model_name="deepseek-chat",
            max_tokens=4096
        )
        
        # 提取话题标签
        tags = self._extract_hashtags(result)
        
        return {
            "content": result,
            "format": "text",
            "tags": tags,
            "word_count": len(result),
            "copy_format": "plain_text"
        }
    
    def _convert_toutiao(self, content: str) -> dict:
        """
        头条格式: HTML，短段落，关键信息加粗
        """
        import markdown
        html = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        
        # 头条特殊处理: 段落间距加大、关键数字加粗等
        # ... 具体实现
        
        return {
            "content": html,
            "format": "html",
            "tags": [],
            "word_count": len(content),
            "copy_format": "rich_text"
        }
    
    def _generate_tags_rule_based(self, topic: str, content: str) -> list:
        """基于规则生成话题标签"""
        tags = []
        if topic:
            tags.append(f"#{topic}#")
        # 提取高频关键词作为标签
        # ... 简单的TF-IDF或关键词提取
        return tags[:5]
    
    def _extract_hashtags(self, text: str) -> list:
        """从文本中提取 #话题# 格式的标签"""
        import re
        return re.findall(r'#([^#]+)#', text)
```

### 4.3 水印注入 (`watermark.py`)

```python
"""
文章水印注入工具

设计原则:
- 水印在输出时注入，不存入数据库
- 通过用户等级判断是否添加
- 支持Markdown和HTML两种格式
"""

WATERMARK_MD = """
---
*本文由 [SupaWriter](https://supawriter.com?ref=watermark) AI 辅助创作*
"""

WATERMARK_HTML = """
<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center; color: #999; font-size: 12px;">
  本文由 <a href="https://supawriter.com?ref=watermark" style="color: #10b981; text-decoration: none;">SupaWriter</a> AI 辅助创作
</div>
"""


def inject_watermark(
    content: str, 
    user_tier: str, 
    format: str = "markdown"
) -> str:
    """
    条件性注入水印
    
    Args:
        content: 文章内容
        user_tier: 用户等级 ('free', 'pro', 'ultra')
        format: 输出格式 ('markdown', 'html')
    
    Returns:
        注入水印后的内容（或原内容，如果是付费用户）
    """
    if user_tier in ('pro', 'ultra'):
        return content
    
    if format == "html":
        return content + WATERMARK_HTML
    else:
        return content + WATERMARK_MD
```

### 4.4 article_worker.py 修改点

在文章生成完成后，自动触发评分：

```python
# 在 generate_article_task() 函数的 save_article_to_database() 之后添加:

# === P0新增: 自动触发文章评分 ===
try:
    from backend.api.services.article_scoring import ArticleScoringService
    scoring_service = ArticleScoringService()
    score = await scoring_service.score_article(
        content=content,
        title=outline.get('title', topic),
        topic=topic
    )
    # 保存评分到数据库
    await save_article_score(article_id, score)
    logger.info(f"Article scored: {article_id}, score={score.total_score}")
except Exception as e:
    # 评分失败不影响文章生成
    logger.warning(f"Article scoring failed (non-blocking): {e}")
```

风格注入点（在生成prompt构建时）：

```python
# 在构建文章生成的system_prompt时，检查用户是否有风格配置:

async def _get_style_prompt(user_id: int) -> str:
    """获取用户风格提示词（如果有）"""
    from utils.database import Database
    with Database.get_cursor() as cursor:
        cursor.execute("""
            SELECT style_profile, is_active 
            FROM user_writing_styles 
            WHERE user_id = %s AND is_active = TRUE
        """, (user_id,))
        row = cursor.fetchone()
        if row and row['style_profile']:
            profile = row['style_profile']
            return f"""
## 写作风格要求
请严格按照以下风格特征写作：
- 语气风格: {profile.get('tone', '')}
- 句式偏好: {profile.get('sentence_style', '')}
- 段落结构: {profile.get('paragraph_structure', '')}
- 用词特征: {profile.get('vocabulary', '')}
- 开头风格: {profile.get('opening_style', '')}
- 结尾风格: {profile.get('closing_style', '')}
"""
    return ""
```

---

## 五、前端组件设计

### 5.1 ScoreCard 组件

```typescript
// frontend/src/components/article/ScoreCard.tsx

interface ArticleScore {
  total_score: number;
  level: 'excellent' | 'good' | 'average' | 'poor';
  summary: string;
  dimensions?: {
    name: string;
    label: string;
    score: number;
    suggestions: string[];
  }[];
  upgrade_hint?: string;
}

interface ScoreCardProps {
  articleId: string;
  userTier: 'free' | 'pro' | 'ultra';
}

// 组件功能:
// 1. 加载时调用 GET /api/v1/articles/{id}/score
// 2. 显示总分环形图 + 等级标签
// 3. Free用户: 显示总分+评语+升级引导
// 4. Pro用户: 显示4维度进度条+具体建议
// 5. 支持折叠/展开
```

### 5.2 PlatformPreview 组件

```typescript
// frontend/src/components/article/PlatformPreview.tsx

interface PlatformPreviewProps {
  articleId: string;
  markdownContent: string;
  userTier: 'free' | 'pro' | 'ultra';
}

// 组件功能:
// 1. 顶部平台选择 tabs: [微信公众号] [知乎] [小红书] [头条号]
// 2. 切换时调用 POST /api/v1/articles/{id}/convert
// 3. 预览区域渲染转换后的内容
// 4. 底部"一键复制"按钮
// 5. 小红书转换时显示loading
// 6. 水印自动注入（Free用户）
```

### 5.3 OnboardingFlow 组件

```typescript
// frontend/src/components/onboarding/OnboardingFlow.tsx

// 组件功能:
// 1. 检查 GET /api/v1/user/onboarding 是否已完成
// 2. 未完成则显示全屏overlay引导
// 3. Step 1: 身份选择 (4个选项)
// 4. Step 2: 热点选择 (调用 hotspots API 获取实时热点)
// 5. Step 3: 跳转到 /writer?topic=xxx&source=onboarding 开始生成
// 6. 完成后调用 POST /api/v1/user/onboarding/complete
// 7. 支持"跳过"操作
```

---

## 六、Prompt 设计

### 6.1 文章评分 Prompt

```
你是一个专业的内容质量评估专家。请对以下文章进行评估。

文章标题: {title}
文章主题: {topic}
文章内容（前3000字）:
{content}

请从以下三个维度评分(0-100)，并给出2-3条具体、可操作的改进建议:

1. information_density (信息密度): 
   - 是否有数据/事实支撑
   - 论据是否充分
   - 信息量是否足够

2. seo_friendliness (SEO友好度):
   - 标题是否吸引点击
   - 关键词是否自然分布
   - 文章结构是否清晰

3. virality (传播潜力):
   - 开头是否有吸引力(hook)
   - 是否能引发情感共鸣
   - 是否有分享动机

请严格按以下JSON格式返回，不要添加任何其他文字:
{JSON模板}
```

### 6.2 风格分析 Prompt

```
你是一个专业的写作风格分析师。请分析以下{n}篇文章的写作风格特征。

{范文内容}

请从以下维度分析，并严格按JSON格式返回:
{
    "tone": "语气风格描述（如：理性分析型、口语亲切型等）",
    "sentence_style": "句式偏好（如：偏好短句、善用设问等）",
    "paragraph_structure": "段落结构特征（如：总分总、递进式等）",
    "vocabulary": "用词特征（如：善用比喻、专业术语多等）",
    "opening_style": "开头风格（如：常以故事开头、数据开头等）",
    "closing_style": "结尾风格（如：总结式、号召式等）",
    "raw_analysis": "200字以内的完整风格分析描述"
}
```

---

## 七、测试要点

| 功能 | 测试类型 | 关键测试用例 |
|------|---------|------------|
| F1 爆文生成器 | E2E | 热点页点击→写作页预填→生成成功 |
| F2 水印 | 单元测试 | Free用户有水印、Pro用户无水印、HTML/MD格式正确 |
| F3 多平台 | 集成测试 | 4个平台转换结果格式正确、复制粘贴到目标平台可用 |
| F4 评分 | 单元测试+人工 | 规则引擎计算正确、LLM评分JSON解析正确、10篇基准文章 |
| F5 风格 | 集成测试 | 上传→分析→存储→生成时应用→风格一致性 |
| F6 引导 | E2E | 新用户触发→完成流程→不再触发 |

---

*本文档配合 PRD 和 Sprint 计划使用*
