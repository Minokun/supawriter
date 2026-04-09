# Streamlit vs FastAPI 文章生成对比分析报告

> **日期**: 2026-03-04
> **分析对象**: Streamlit 版本 (web.py) vs FastAPI + Next.js 版本

---

## 执行摘要

经过详细代码审查，发现两个版本使用的 **Prompt 模板完全相同**，但 **图片插入策略和文章组装流程存在显著差异**，这很可能是导致文章质量差异的主要原因。

| 维度 | Streamlit 版本 | FastAPI 版本 | 影响 |
|------|---------------|--------------|------|
| **Prompt 模板** | `utils/prompt_template.py` | 相同 | 无差异 |
| **LLM 调用** | `utils/llm_chat.chat()` | 相同 | 无差异 |
| **图片插入时机** | 逐章节即时插入 | 全部完成后统一插入 | **显著差异** |
| **图片选择策略** | 每章最多3张，低阈值 | 全文最多6张，全局排序 | **显著差异** |
| **Summary 处理** | 文章开头添加引用 | 未添加到正文 | **有差异** |

---

## 1. Prompt 模板对比

### 结论: ✅ 完全相同

两个版本使用相同的 Prompt 模板文件：

```python
# Streamlit 版本
import utils.prompt_template as pt

# FastAPI 版本
import utils.prompt_template as pt
```

使用的模板常量：
- `pt.ARTICLE_OUTLINE_GEN` - 生成大纲
- `pt.ARTICLE_OUTLINE_SUMMARY` - 融合大纲
- `pt.ARTICLE_OUTLINE_BLOCK` - 生成章节内容

**Prompt 内容完全一致**，没有差异。

---

## 2. LLM 调用链对比

### 结论: ✅ 调用链相同

| 步骤 | Streamlit | FastAPI |
|------|-----------|---------|
| 搜索 | `Search.get_search_result()` | 相同 |
| 大纲生成 | `llm_task()` -> `chat()` | 相同 |
| 大纲融合 | `chat()` | 相同 |
| 章节生成 | `llm_task()` -> `chat()` | 相同 |

**FastAPI 版本通过兼容层导入**：
```python
# backend/api/utils/searxng_compat.py
from utils.searxng_utils import Search, llm_task, chat, parse_outline_json
```

实际调用的是同一个函数，**没有差异**。

---

## 3. 关键差异点

### 3.1 图片插入策略差异 🔴

#### Streamlit 版本 (逐章节插入)

```python
# page/auto_write.py 第509-611行
for i, outline_block in enumerate(outline_summary_json['content_outline']):
    # 1. 生成章节内容
    outline_block_content = llm_task(...)
    outline_block_content_final = chat(...)

    # 2. 【立即】为该章节插入图片（在循环内部）
    if enable_images and faiss_index:
        # 每个章节最多3张图片
        max_images_per_chapter = 3

        # 相似度阈值 = 0（较低，容易匹配）
        similarity_threshold = 0

        # 搜索相似图片
        _, similarities, matched_data = search_similar_text(...)

        # 第一张图片放在章节开头
        if images_inserted == 0:
            image_markdown = f"![图片]({public_url})\n\n"
            outline_block_content_final = image_markdown + outline_block_content_final
        else:
            # 后续图片均匀分布在段落之间
            paragraphs = outline_block_content_final.split('\n\n')
            insert_position = len(paragraphs) // (max_images_per_chapter) * images_inserted
```

**特点**：
- ✅ 图片与章节内容同步生成，上下文匹配度高
- ✅ 每个章节独立选择图片，确保章节内有图
- ✅ 图片位置灵活（开头 + 段落间均匀分布）
- ⚠️ 阈值较低（0），可能插入不太相关的图片

#### FastAPI 版本 (统一插入)

```python
# backend/api/services/article_generator.py 第305-327行
# 1. 先生成所有章节（无图片）
for idx, section in enumerate(content_outline, 1):
    chapter_content = await asyncio.to_thread(_refine)
    article_chapters.append(chapter_content)

# 2. 【全部完成后】统一插入图片
full_content_with_images = await _insert_images_to_full_article(
    full_article=full_content,
    outline=outline,
    search_results=search_results,
    max_total_images=6,  # 整篇文章最多6张
    similarity_threshold=0
)

# backend/api/workers/article_worker.py 第329-477行
async def _insert_images_to_full_article(...):
    # 两轮分配策略：
    # 第一轮：每个章节至少1张
    # 第二轮：全局分配剩余配额

    # 按相似度全局排序
    all_candidates.sort(key=lambda x: x['similarity'], reverse=True)
```

**特点**：
- ✅ 全局优化，选择最相关的6张图片
- ✅ 避免图片重复
- ⚠️ 图片与章节生成脱节，上下文匹配可能不如逐章插入
- ⚠️ 每个章节只保证1张，可能某些章节无图

### 3.2 Summary 处理差异 🟡

#### Streamlit 版本

```python
# page/auto_write.py 第632-635行
# 在文章最前面添加summary（使用markdown引用格式）
if outline_summary_json.get('summary') and outline_summary_json['summary'].strip():
    summary_text = outline_summary_json['summary'].strip()
    summary_markdown = f"> {summary_text}\n\n"
    final_article_content = summary_markdown + final_article_content
```

**效果**：文章开头有摘要引用块，提升阅读体验

#### FastAPI 版本

```python
# backend/api/services/article_generator.py
# 没有找到在 final_content 中添加 summary 的代码
# outline 中包含 summary，但未插入到文章正文
```

**效果**：文章缺少摘要引导

### 3.3 实时预览差异 🟡

#### Streamlit 版本

```python
# 每个章节生成后都更新实时预览
live_article_content = '\n\n'.join(article_chapters)
task_state['live_article'] = live_article_content
```

#### FastAPI 版本

```python
# 每个章节完成后推送进度
yield self._create_progress_event(
    article_id, current_progress,
    f"章节 {idx}/{total_sections} 完成",
    {"live_article": full_content}
)
```

两者都有实时预览，但 FastAPI 版本在前端展示可能有差异。

---

## 4. 问题诊断

### 为什么 FastAPI 版本文章感觉"不够好"？

| 可能原因 | 分析 | 建议 |
|---------|------|------|
| **图片匹配度** | 统一插入时文章已完成，无法针对每个章节优化图片位置 | 改为逐章节插入 |
| **图片分布不均** | 某些章节可能无图，影响阅读体验 | 确保每章至少1-2张图 |
| **缺少摘要** | FastAPI 版本未将 summary 添加到正文 | 添加摘要引用块 |
| **阈值过低** | similarity_threshold=0 可能插入不相关图片 | 提高阈值到 0.3-0.5 |

---

## 5. 修复建议

### 方案 A: 对齐 Streamlit 版本（推荐）

修改 `backend/api/services/article_generator.py`：

1. **逐章节插入图片**（而非全部完成后）
2. **添加 Summary 到文章开头**
3. **调整图片选择阈值**

### 方案 B: 优化统一插入策略

修改 `backend/api/workers/article_worker.py`：

1. **增加每章最少图片数**（从1张改为2张）
2. **提高相似度阈值**（从0改为0.3）
3. **在文章开头添加 Summary**

---

## 6. 代码差异详情

### 图片插入调用对比

```python
# Streamlit 版本 - 逐章插入（在生成循环内）
for outline_block in content_outline:
    chapter_content = generate_chapter(...)

    # 立即插入图片
    if enable_images:
        images = search_images_for_chapter(chapter_content)
        chapter_with_images = insert_images(chapter_content, images)
        article_chapters.append(chapter_with_images)

# FastAPI 版本 - 统一插入（在生成循环外）
for section in content_outline:
    chapter_content = generate_chapter(...)
    article_chapters.append(chapter_content)  # 无图片

# 全部完成后统一插入
full_content = assemble(article_chapters)
content_with_images = await insert_images_to_full_article(full_content)
```

---

## 7. 结论

**核心发现**：
1. ✅ Prompt 模板完全相同
2. ✅ LLM 调用链相同
3. 🔴 **图片插入策略不同**（逐章 vs 统一）
4. 🟡 **Summary 处理不同**（Streamlit 添加引用，FastAPI 未添加）

**建议行动**：
1. **短期**：修改 FastAPI 版本，添加 Summary 到文章开头
2. **中期**：评估是否需要改为逐章节插入图片策略
3. **长期**：统一两个版本的生成逻辑，避免维护两套代码

---

*报告生成时间: 2026-03-04*
