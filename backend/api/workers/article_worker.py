# -*- coding: utf-8 -*-
"""
Article Generation Worker Function
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Any, Optional

# 使用 backend 兼容层导入 searxng 工具
from backend.api.utils.searxng_compat import (
    Search, llm_task, chat, parse_outline_json,
    set_user_context  # 导入用户上下文设置函数
)

# Image indexing imports
from backend.api.workers.image_store import redis_image_store
from backend.api.workers.image_indexer import batch_embed_with_fallback
from backend.api.core.faiss_cache import faiss_cache

import re

logger = logging.getLogger(__name__)


def remove_thinking_tags(content):
    """
    移除大模型输出中的 thinking 标签及其内容
    支持的标签格式：<thinking>、<think>、<thought>
    """
    if not content or not isinstance(content, str):
        return content
    
    think_patterns = [
        r'(?:^|\n)\s*<thinking>.*?</thinking>\s*(?:\n|$)',
        r'(?:^|\n)\s*<think>.*?</think>\s*(?:\n|$)',
        r'(?:^|\n)\s*<thought>.*?</thought>\s*(?:\n|$)'
    ]
    
    cleaned_content = content
    for pattern in think_patterns:
        cleaned_content = re.sub(pattern, '\n', cleaned_content, flags=re.DOTALL | re.IGNORECASE)
    
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    return cleaned_content.strip('\n')


def _scrape_single_url(url: str) -> Optional[Dict[str, Any]]:
    """
    抓取单个 URL 的内容

    Args:
        url: 要抓取的 URL

    Returns:
        包含 title, url, content, source 的字典，失败返回 None
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse

        # 设置超时和请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        # 获取 Referer
        parsed = urlparse(url)
        referer = f"{parsed.scheme}://{parsed.netloc}/"
        headers['Referer'] = referer

        # 请求页面
        response = requests.get(url, timeout=10, headers=headers, verify=False)
        response.raise_for_status()

        # 解析内容
        soup = BeautifulSoup(response.content, 'html.parser')

        # 提取标题
        title = ''
        if soup.title:
            title = soup.title.string.strip() if soup.title.string else ''

        # 提取正文（取段落文本）
        paragraphs = soup.find_all('p')
        content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])

        return {
            'title': title,
            'url': url,
            'content': content,
            'source': 'extra_url',
            'images': []
        }

    except Exception as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        return None


async def execute_search(
    topic: str,
    spider_num: int = None,
    enable_images: bool = True,
    extra_urls: list = None,
    progress_tracker = None,
    model_type: str = "deepseek",
    model_name: str = "deepseek-chat",
    user_id: int = None,
    task_id: str = None
) -> List[Dict[str, Any]]:
    """
    Execute web search for article content

    Note: Query optimization and LLM filtering are handled internally by Search.get_search_result()

    Args:
        topic: Search topic (will be optimized internally)
        spider_num: Number of results to fetch
        enable_images: Whether to fetch images
        extra_urls: Additional URLs to scrape
        progress_tracker: Optional ProgressTracker instance
        model_type: LLM provider
        model_name: LLM model name
        user_id: User ID for FAISS index isolation
        task_id: Task ID for FAISS index isolation

    Returns:
        List of search results with title, url, content
    """

    if progress_tracker:
        await progress_tracker.update(10, "正在搜索相关内容...")

    # Run search in thread pool (blocking function)
    # Note: Search.get_search_result() internally:
    # 1. Optimizes the query with LLM
    # 2. Performs search with optimized query
    # 3. Filters results with LLM relevance check
    # Use SystemConfig default if spider_num not explicitly provided
    if spider_num is None:
        try:
            from backend.api.core.system_config import SystemConfig
            spider_num = SystemConfig.get_int('search.default_spider_num', 20)
        except Exception:
            spider_num = 20

    loop = asyncio.get_event_loop()
    search = Search(result_num=spider_num)

    search_result = await loop.run_in_executor(
        None,
        lambda: search.get_search_result(
            topic,  # Original topic (will be optimized and filtered internally)
            theme=topic,
            spider_mode=False,
            progress_callback=None,
            username=str(user_id) if user_id else None,  # Convert user_id to username string
            article_id=task_id,  # Use task_id as article_id
            model_type=model_type,
            model_name=model_name
        )
    )

    if not search_result:
        raise ValueError("搜索结果为空，请尝试修改搜索关键词")

    if progress_tracker:
        await progress_tracker.update(
            30,
            f"搜索完成，获取 {len(search_result)} 个结果",
            {
                "type": "search",
                "results": search_result
            }
        )

    # 处理额外 URL（新增逻辑）
    if extra_urls and len(extra_urls) > 0:
        if progress_tracker:
            await progress_tracker.update(
                35,
                f"正在抓取 {len(extra_urls)} 个额外链接..."
            )

        logger.info(f"Scraping {len(extra_urls)} extra URLs...")

        # 并发抓取额外 URL
        extra_results = await asyncio.gather(*[
            loop.run_in_executor(None, _scrape_single_url, url)
            for url in extra_urls
        ])

        # 去重合并（基于 URL）
        seen_urls = {r.get('url', '') for r in search_result if r.get('url')}
        added_count = 0

        for result in extra_results:
            if result and result.get('url'):
                if result['url'] not in seen_urls:
                    search_result.append(result)
                    seen_urls.add(result['url'])
                    added_count += 1

        logger.info(f"Extra URL scraping completed: {added_count}/{len(extra_urls)} added")

        if progress_tracker:
            await progress_tracker.update(
                50,
                f"额外链接抓取完成，共 {len(search_result)} 个结果",
                {
                    "type": "search",
                    "results": search_result
                }
            )

    # Extract and store image URLs in Redis for background FAISS indexing
    # Use a set for automatic deduplication
    image_urls_set = set()
    for result in search_result:
        if isinstance(result, dict):
            images = result.get('images', [])
            if isinstance(images, list):
                image_urls_set.update(images)
    image_urls = list(image_urls_set)  # Convert back to list for add_images

    if user_id and task_id and image_urls:
        try:
            image_count = await redis_image_store.add_images(user_id, task_id, image_urls)
            logger.info(f"[Search] Stored {image_count} images in Redis for FAISS indexing: user={user_id}, task={task_id}")

            # Trigger background FAISS index creation (fire-and-forget)
            asyncio.create_task(_create_index_background(user_id, task_id))
            logger.info(f"[Search] Triggered background FAISS index creation: user={user_id}, task={task_id}")
        except Exception as e:
            logger.warning(f"[Search] Failed to store images in Redis (search continuing): {e}")

    logger.info(f"Search completed: {len(search_result)} results for topic: {topic}")
    return search_result


async def generate_outline(
    search_results: List[Dict[str, Any]],
    topic: str,
    model_type: str = "deepseek",
    model_name: str = "deepseek-chat",
    custom_style: str = "",
    progress_tracker = None
) -> Dict[str, Any]:
    """
    Generate article outline from search results

    Args:
        search_results: Search results from execute_search
        topic: Article topic
        model_type: LLM provider
        model_name: LLM model name
        custom_style: Custom style requirements
        progress_tracker: Optional ProgressTracker

    Returns:
        Outline dict with title, summary, content_outline
    """
    import utils.prompt_template as pt

    loop = asyncio.get_event_loop()

    if progress_tracker:
        await progress_tracker.update(30, "正在生成大纲...")

    # Generate outline
    outlines = await loop.run_in_executor(
        None,
        lambda: llm_task(
            search_results,
            topic,
            pt.ARTICLE_OUTLINE_GEN,
            model_type=model_type,
            model_name=model_name
        )
    )
    outlines = remove_thinking_tags(outlines)

    if progress_tracker:
        await progress_tracker.update(50, "正在融合大纲...")

    # Merge outline
    if isinstance(outlines, str) and outlines.count("title") <= 1:
        outline_summary = outlines
    else:
        outline_summary = await loop.run_in_executor(
            None,
            lambda: chat(
                f'<topic>{topic}</topic> <content>{outlines}</content>',
                pt.ARTICLE_OUTLINE_SUMMARY,
                model_type=model_type,
                model_name=model_name,
                max_tokens=16384
            )
        )
        outline_summary = remove_thinking_tags(outline_summary)

    # Parse to JSON
    outline_json = parse_outline_json(outline_summary, topic)
    outline_json.setdefault('title', topic)
    outline_json.setdefault('summary', "")
    outline_json.setdefault('content_outline', [])
    # Store raw outline summary string for use in article writing prompts
    outline_json['_raw_outline_summary'] = outline_summary

    if progress_tracker:
        await progress_tracker.update(
            60,
            "大纲生成完成",
            {
                "type": "outline",
                "outline": outline_json
            }
        )

    logger.info(f"Outline generated: {len(outline_json.get('content_outline', []))} sections")
    return outline_json


async def _insert_images_fallback(
    chapter_content: str,
    outline_block: Dict[str, Any],
    search_results: List[Dict[str, Any]],
    used_images: set,
    max_images_per_chapter: int = 3,
) -> str:
    """
    当 FAISS 索引不可用时，基于轮询策略从搜索结果中选择图片插入章节。

    策略：从所有搜索结果中收集未使用的图片，轮询分配到各章节。
    这保证了即使 embedding API 完全失败，文章中仍然会有图片。
    """
    from utils.qiniu_utils import ensure_public_image_url

    try:
        # 收集所有搜索结果中未使用的图片
        available_images = []
        for item in search_results:
            if not isinstance(item, dict):
                continue
            images = item.get('images', [])
            if not images:
                continue
            for img_url in images:
                if isinstance(img_url, str) and img_url not in used_images:
                    available_images.append(img_url)

        if not available_images:
            logger.info("[Fallback] No images available in search results")
            return chapter_content

        logger.info(f"[Fallback] Found {len(available_images)} unused images across all search results")

        # 选择图片（最多 max_images_per_chapter 张）
        images_inserted = 0
        for image_url in available_images:
            if images_inserted >= max_images_per_chapter:
                break

            used_images.add(image_url)

            # 确保图片 URL 可公开访问
            try:
                public_url = await asyncio.get_event_loop().run_in_executor(
                    None, lambda url=image_url: ensure_public_image_url(url)
                )
            except Exception as e:
                logger.error(f"[Fallback] Error ensuring public URL: {e}")
                continue

            if not public_url or len(public_url) < 10:
                logger.warning(f"[Fallback] Invalid image URL, skipping: {image_url[:80]}")
                continue

            # 插入策略与 FAISS 路径一致
            if images_inserted == 0:
                image_markdown = f"![图片]({public_url})\n\n"
                chapter_content = image_markdown + chapter_content
            else:
                paragraphs = chapter_content.split('\n\n')
                if len(paragraphs) >= 3:
                    insert_position = len(paragraphs) // max_images_per_chapter * images_inserted
                    insert_position = min(insert_position, len(paragraphs) - 1)
                    insert_position = max(insert_position, 1)
                    image_markdown = f"\n\n![图片]({public_url})"
                    paragraphs[insert_position] = paragraphs[insert_position] + image_markdown
                    chapter_content = '\n\n'.join(paragraphs)
                else:
                    image_markdown = f"\n\n![图片]({public_url})"
                    chapter_content += image_markdown

            images_inserted += 1
            logger.info(f"[Fallback] Inserted image {images_inserted}/{max_images_per_chapter}: {image_url[:60]}")

        if images_inserted > 0:
            logger.info(f"[Fallback] ✓ Inserted {images_inserted} images via fallback")
        else:
            logger.warning("[Fallback] No images inserted (all URLs invalid)")

        return chapter_content

    except Exception as e:
        logger.error(f"[Fallback] Error in image fallback: {e}")
        return chapter_content


async def _insert_images_to_chapter(
    chapter_content: str,
    outline_block: Dict[str, Any],
    search_results: List[Dict[str, Any]],
    user_id: int,
    task_id: str,
    used_images: set = None,
    max_images_per_chapter: int = 3,
    similarity_threshold: float = 0
) -> str:
    """
    为章节内容插入相关图片（对齐 Streamlit 版本逻辑）

    关键改进（vs 旧版）：
    1. 查询文本 = 章节标题 + h2列表 + 实际生成的章节内容（而非大纲元数据）
    2. 相似度阈值默认为 0（与 Streamlit 一致），接受所有匹配
    3. used_images 跨章节共享，避免同一张图片在不同章节重复出现
    4. 插入策略：第1张放章节开头，后续均匀分布在段落之间

    Args:
        chapter_content: 实际生成的章节内容
        outline_block: 大纲块（包含 h1, h2, content）
        search_results: 搜索结果（包含图片）
        user_id: 用户 ID
        task_id: 任务 ID
        used_images: 跨章节共享的已使用图片集合（避免重复）
        max_images_per_chapter: 每章节最多插入图片数
        similarity_threshold: 相似度阈值（默认0，与Streamlit一致）

    Returns:
        插入图片后的章节内容
    """
    if used_images is None:
        used_images = set()

    try:
        from utils.embedding_utils import search_similar_text
        from utils.qiniu_utils import ensure_public_image_url
        from backend.api.core.faiss_cache import faiss_cache

        # 等待后台 FAISS 索引创建完成
        logger.info(f"[Insert] Waiting for FAISS index: user={user_id}, task={task_id}")
        faiss_index = await _wait_for_faiss_index(user_id, task_id)

        if faiss_index is None:
            logger.warning(f"[Insert] FAISS index not available, using keyword-based fallback: user={user_id}, task={task_id}")
            return await _insert_images_fallback(
                chapter_content, outline_block, search_results,
                used_images, max_images_per_chapter
            )

        logger.info(f"[Insert] FAISS index ready: user={user_id}, task={task_id}, size={faiss_index.get_size()}")

        # 构建查询文本（与 Streamlit 一致：章节标题 + h2列表 + 实际生成的章节内容）
        h1 = outline_block.get('h1', '')
        h2_list = outline_block.get('h2', [])
        h2_str = "".join(h2_list) if isinstance(h2_list, list) else str(h2_list)

        # 关键：使用实际生成的 chapter_content 而非大纲中的 content 元数据
        query_text = f"{h1}{h2_str}{chapter_content}".strip()
        logger.info(f"[Insert] Chapter query built: h1='{h1[:50]}', h2_count={len(h2_list) if isinstance(h2_list, list) else 1}, content_length={len(chapter_content)}")

        if not query_text:
            logger.warning("[Insert] Empty query text, skipping image insertion")
            return chapter_content

        # FAISS 相似度搜索
        logger.info(f"[Insert] Starting FAISS search with k=10...")
        indices, similarities, matched_data = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: search_similar_text(query_text, faiss_index, k=10, is_image_url=False)
        )

        logger.info(f"[Insert] FAISS search returned {len(matched_data)} matches, similarities: {similarities[:5] if len(similarities) > 0 else []}")

        # 过滤和选择图片（与 Streamlit 一致的逻辑）
        selected_images = []
        images_inserted = 0
        logger.info(f"[Insert] Filtering images: threshold={similarity_threshold}, max={max_images_per_chapter}, already_used={len(used_images)}")

        if matched_data:
            for similarity, data in zip(similarities, matched_data):
                if images_inserted >= max_images_per_chapter:
                    break

                if not isinstance(data, dict) or 'image_url' not in data:
                    continue

                image_url = data['image_url']

                # 跨章节去重
                if image_url in used_images:
                    logger.debug(f"[Insert] Skipping already used image: {image_url[:80]}...")
                    continue

                # 相似度阈值检查
                if similarity < similarity_threshold:
                    continue

                # 确保图片 URL 可公开访问（上传到七牛云）
                try:
                    public_url = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda url=image_url: ensure_public_image_url(url)
                    )
                except Exception as e:
                    logger.error(f"[Insert] Error ensuring public URL: {e}")
                    used_images.add(image_url)
                    continue

                # 验证图片URL是否有效
                if not public_url or len(public_url) < 10:
                    logger.warning(f"[Insert] Invalid image URL, skipping: {image_url[:80]}...")
                    used_images.add(image_url)
                    continue

                logger.info(f"[Insert] ✓ Selected image (similarity={similarity:.4f}): {image_url[:80]}...")

                # 标记原始URL为已使用（跨章节生效）
                used_images.add(image_url)

                # 按 Streamlit 策略插入图片
                if images_inserted == 0:
                    # 第一张图片放在章节开头
                    image_markdown = f"![图片]({public_url})\n\n"
                    chapter_content = image_markdown + chapter_content
                else:
                    # 后续图片尝试插入到段落之间（均匀分布）
                    paragraphs = chapter_content.split('\n\n')
                    if len(paragraphs) >= 3:
                        # 计算插入位置 - 均匀分布
                        insert_position = len(paragraphs) // max_images_per_chapter * images_inserted
                        insert_position = min(insert_position, len(paragraphs) - 1)
                        insert_position = max(insert_position, 1)

                        image_markdown = f"\n\n![图片]({public_url})"
                        paragraphs[insert_position] = paragraphs[insert_position] + image_markdown
                        chapter_content = '\n\n'.join(paragraphs)
                    else:
                        # 段落不够，添加到末尾
                        image_markdown = f"\n\n![图片]({public_url})"
                        chapter_content += image_markdown

                logger.info(f"[Insert] Inserted image {images_inserted+1}/{max_images_per_chapter} for chapter '{h1[:30]}'")
                images_inserted += 1
                selected_images.append(public_url)

        if not selected_images:
            logger.warning(f"[Insert] No suitable images found after filtering (had {len(matched_data)} candidates, {len(used_images)} already used)")
        else:
            logger.info(f"[Insert] ✓✓✓ Successfully inserted {len(selected_images)} images into chapter '{h1[:30]}'!")

        return chapter_content

    except Exception as e:
        logger.error(f"[Insert] Error inserting images: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        # 失败时返回原始内容，不影响文章生成
        return chapter_content


def _build_references_section(search_results: List[Dict[str, Any]]) -> str:
    """
    从搜索结果中构建参考来源章节（Markdown 格式）

    Args:
        search_results: 搜索结果列表，每项包含 title, url, source 等字段

    Returns:
        Markdown 格式的参考来源章节字符串，无有效来源时返回空字符串
    """
    seen_urls = set()
    references = []

    for item in search_results:
        if not isinstance(item, dict):
            continue
        url = item.get('url', '').strip()
        title = item.get('title', '').strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        # 跳过额外抓取的无标题结果
        display_title = title if title else url
        references.append(f"- [{display_title}]({url})")

    if not references:
        return ""

    return "---\n\n## 参考来源\n\n" + "\n".join(references)


async def write_article_content(
    outline: Dict[str, Any],
    search_results: List[Dict[str, Any]],
    topic: str,
    model_type: str = "deepseek",
    model_name: str = "deepseek-chat",
    custom_style: str = "",
    progress_tracker = None,
    user_id: int = None,
    task_id: str = None
) -> str:
    """
    Write article content from outline

    Args:
        outline: Outline dict from generate_outline
        search_results: Search results
        topic: Article topic
        model_type: LLM provider
        model_name: LLM model
        custom_style: Custom style requirements
        progress_tracker: Optional ProgressTracker
        user_id: User ID (for FAISS isolation)
        task_id: Task ID (for FAISS isolation)

    Returns:
        Complete article content as string
    """
    import utils.prompt_template as pt

    loop = asyncio.get_event_loop()
    article_chapters = []

    content_outline = outline.get('content_outline', [])
    if not content_outline:
        return ""

    # Use raw outline summary string (same as Streamlit) instead of dict
    outline_summary = outline.get('_raw_outline_summary', str(outline))

    total = len(content_outline)
    base_progress = 60

    # 跨章节共享已使用图片集合，避免同一张图片在不同章节重复出现（与 Streamlit 一致）
    used_images = set()

    for i, outline_block in enumerate(content_outline):
        n = i + 1
        progress = base_progress + int((n / total) * 35)

        if progress_tracker:
            await progress_tracker.update(
                progress,
                f"正在撰写: {outline_block.get('h1', '')} ({n}/{total})"
            )

        # Generate chapter content (match Streamlit: first chapter has extra instructions)
        is_first_chapter = n == 1
        title_instruction = '，注意不要包含任何标题，直接开始正文内容，有吸引力开头（痛点/悬念），生动形象，风趣幽默！' if is_first_chapter else ''
        question = f'<完整大纲>{outline_summary}</完整大纲> 请根据上述信息，书写出以下内容 >>> {outline_block} <<<{title_instruction}'

        outline_block_content = await loop.run_in_executor(
            None,
            lambda: llm_task(
                search_results,
                question=question,
                output_type=pt.ARTICLE_OUTLINE_BLOCK,
                model_type=model_type,
                model_name=model_name
            )
        )
        outline_block_content = remove_thinking_tags(outline_block_content)

        # Apply custom style if provided
        custom_prompt = pt.ARTICLE_OUTLINE_BLOCK
        if custom_style and custom_style.strip():
            custom_prompt = custom_prompt.replace(
                '---要求---',
                f'---要求---\n        - 请围绕这个这个中心主题来编写当前章节内容：{custom_style}\n'
            )

        # Finalize content
        final_instruction = '，注意不要包含任何标题（不要包含h1和h2标题），直接开始正文内容' if is_first_chapter else ''
        outline_block_content_final = await loop.run_in_executor(
            None,
            lambda: chat(
                f'<完整大纲>{outline_summary}</完整大纲> <相关资料>{outline_block_content}</相关资料> 请根据上述信息，书写大纲中的以下这部分内容：{outline_block}{final_instruction}',
                custom_prompt,
                model_type=model_type,
                model_name=model_name
            )
        )
        outline_block_content_final = remove_thinking_tags(outline_block_content_final)

        # Insert images into chapter (always enabled, cross-chapter dedup via shared used_images)
        logger.info(f"Inserting images into chapter {n}/{total}, used_images_count={len(used_images)}")
        outline_block_content_final = await _insert_images_to_chapter(
            chapter_content=outline_block_content_final,
            outline_block=outline_block,
            search_results=search_results,
            user_id=user_id,
            task_id=task_id,
            used_images=used_images,
            max_images_per_chapter=3,
            similarity_threshold=0
        )

        article_chapters.append(outline_block_content_final)

        # Update live preview
        if progress_tracker:
            live_article = '\n\n'.join(article_chapters)
            if outline.get('summary'):
                live_article = f"> {outline['summary']}\n\n" + live_article

            await progress_tracker.update(
                progress,
                f"正在撰写: {outline_block.get('h1', '')} ({n}/{total})",
                {
                    "type": "writing",
                    "live_article": live_article,
                    "chapter_index": n,
                    "chapter_total": total
                }
            )

    # Combine all chapters
    final_content = '\n\n'.join(article_chapters)

    # Add summary at the beginning
    if outline.get('summary') and outline['summary'].strip():
        final_content = f"> {outline['summary'].strip()}\n\n" + final_content

    # 参考来源不再追加到文章正文中，改为独立存储在 metadata 中
    # references_section = _build_references_section(search_results)

    logger.info(f"Article content written: {len(final_content)} characters")
    return final_content


async def save_article_to_database(
    task_id: str,
    user_id: int,
    title: str,
    content: str,
    summary: str = "",
    outline: dict = None,
    topic: str = "",
    model_type: str = "deepseek",
    model_name: str = "deepseek-chat"
) -> str:
    """
    Save generated article to database

    Args:
        task_id: Task identifier
        user_id: User ID
        title: Article title
        content: Article content (Markdown)
        summary: Article summary
        outline: Outline dict
        topic: Original topic
        model_type: LLM provider
        model_name: LLM model name

    Returns:
        Article ID (UUID as string)
    """
    import psycopg2
    import psycopg2.extras
    import json

    logger.info(f"[DB] Saving article: user_id={user_id}, title={title[:50]}")

    # Create direct database connection (not using Streamlit's Database class)
    conn = None
    try:
        # Prefer DATABASE_URL (works in both Docker and local dev)
        # Fall back to individual POSTGRES_* env vars for backward compat
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            # psycopg2 accepts postgresql:// URIs directly
            logger.debug("[DB] Connecting via DATABASE_URL")
            conn = psycopg2.connect(database_url)
        else:
            pg_host = os.getenv('POSTGRES_HOST', 'localhost')
            pg_port = os.getenv('POSTGRES_PORT', '5432')
            pg_db = os.getenv('POSTGRES_DB', 'supawriter')
            pg_user = os.getenv('POSTGRES_USER', 'postgres')
            pg_password = os.getenv('POSTGRES_PASSWORD', '')
            conn_string = (
                f"host={pg_host} "
                f"port={pg_port} "
                f"dbname={pg_db} "
                f"user={pg_user} "
                f"password={pg_password}"
            )
            logger.debug(f"[DB] Connecting via individual params: {pg_host}:{pg_port}")
            conn = psycopg2.connect(conn_string)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get username from user_id
        cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            raise ValueError(f"User not found: user_id={user_id}")
        username = user_row['username']
        logger.info(f"[DB] Found user: {username}")

        # Insert article with correct column names
        metadata_json = json.dumps({'outline': outline}) if outline else '{}'

        insert_sql = """
            INSERT INTO articles
            (user_id, username, topic, title, article_content, summary, metadata, model_type, model_name, image_enabled, word_count, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """

        values = (
            user_id,
            username,
            topic,
            title,
            content,
            summary,
            metadata_json,
            model_type,
            model_name,
            True,  # image_enabled always true
            0  # word_count placeholder, updated later
        )

        logger.debug(f"[DB] Executing INSERT: user_id={user_id}, username={username}")
        cursor.execute(insert_sql, values)
        result = cursor.fetchone()
        article_id = str(result['id'])

        conn.commit()
        logger.info(f"[DB] Article saved successfully: id={article_id}")

        return article_id

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"[DB] Error saving article: {e}")
        raise
    finally:
        if conn:
            conn.close()


async def _create_index_background(user_id: int, task_id: str) -> None:
    """
    后台异步创建 FAISS 索引

    此方法在 execute_search 完成后异步调用，避免阻塞章节写作流程

    Args:
        user_id: 用户 ID
        task_id: 任务 ID（使用 article_id）
    """
    # Create progress tracker for FAISS updates
    from backend.api.workers.progress import ProgressTracker
    progress = ProgressTracker(task_id)

    # Validate parameters
    if not user_id or not task_id:
        logger.warning("[FAISS] Invalid parameters for background index creation")
        return

    from utils.image_filter import filter_image_urls
    from utils.embedding_utils import create_faiss_index

    try:
        # Update progress: starting FAISS indexing
        await progress.update(
            progress=15,
            step="正在创建图片索引...",
            data={"faiss_status": "initializing"}
        )

        # 1. 从 Redis 获取图像 URL 列表
        image_urls = await redis_image_store.get_images(user_id, task_id)
        if not image_urls:
            logger.warning(f"[FAISS] No images found in Redis for indexing: user={user_id}, task={task_id}")
            await faiss_cache.mark_task_status(user_id, task_id, "failed")
            await progress.update(
                progress=30,
                step="没有找到可用的图片",
                data={"faiss_status": "no_images"}
            )
            return

        logger.info(f"[FAISS] Starting background index creation: user={user_id}, task={task_id}, images={len(image_urls)}")

        # 2. 使用维度过滤（非多模态 LLM）
        # filter_image_urls 会过滤尺寸不合规的图像
        filtered_urls, _ = filter_image_urls(image_urls, check_url_only=False)
        if not filtered_urls:
            logger.warning(f"[FAISS] No images passed dimension filter: user={user_id}, task={task_id}")
            await faiss_cache.mark_task_status(user_id, task_id, "failed")
            await progress.update(
                progress=30,
                step="图片尺寸过滤后无可用图片",
                data={"faiss_status": "no_valid_images"}
            )
            return

        logger.info(f"[FAISS] Filtered images: {len(filtered_urls)}/{len(image_urls)} passed")

        # Update progress: filtering complete
        await progress.update(
            progress=20,
            step=f"正在处理 {len(filtered_urls)} 张图片的 embedding...",
            data={"faiss_status": "embedding", "total_images": len(filtered_urls)}
        )

        # 3. 使用递归分治策略批量嵌入 (10→5→1)
        # batch_embed_with_fallback 会处理批量嵌入失败的重试逻辑
        embeddings = await batch_embed_with_fallback(filtered_urls)
        if not embeddings:
            logger.error(f"[FAISS] Failed to generate embeddings: user={user_id}, task={task_id}")
            await faiss_cache.mark_task_status(user_id, task_id, "failed")
            await progress.update(
                progress=30,
                step="图片 embedding 失败",
                data={"faiss_status": "embedding_failed"}
            )
            return

        logger.info(f"[FAISS] Generated embeddings: {len(embeddings)} vectors")

        # Update progress: embeddings complete, saving index
        await progress.update(
            progress=28,
            step="正在保存图片索引...",
            data={"faiss_status": "saving", "image_count": len(embeddings)}
        )

        # 4. 创建并保存 FAISS 索引
        faiss_index = create_faiss_index()

        # Build data list for FAISS index (format: [embedding_vector, metadata_dict])
        data_list = [
            {"image_url": url, "task_id": task_id, "type": "image"}
            for url in filtered_urls
        ]

        # Add embeddings to index (correct method: add_embeddings(embeddings, data))
        faiss_index.add_embeddings(embeddings, data_list)

        # 5. 保存到 faiss_cache (文件系统 + Redis 元数据)
        success = await faiss_cache.save_index(
            user_id=user_id,
            task_id=task_id,
            faiss_index=faiss_index,
            status="normal"
        )

        if success:
            # 6. 标记索引为就绪状态
            await redis_image_store.mark_ready(user_id, task_id, len(filtered_urls))
            logger.info(f"[FAISS] Index created successfully: user={user_id}, task={task_id}, count={len(filtered_urls)}")

            # Update progress: FAISS indexing complete
            await progress.update(
                progress=30,
                step=f"图片索引创建完成 ({len(filtered_urls)} 张图片)",
                data={"faiss_status": "ready", "image_count": len(filtered_urls)}
            )
        else:
            logger.error(f"[FAISS] Failed to save index: user={user_id}, task={task_id}")
            await faiss_cache.mark_task_status(user_id, task_id, "failed")
            await progress.update(
                progress=30,
                step="图片索引保存失败",
                data={"faiss_status": "save_failed"}
            )

    except Exception as e:
        logger.exception(f"[FAISS] Background index creation failed: user={user_id}, task={task_id}, error={e}")
        await faiss_cache.mark_task_status(user_id, task_id, "failed")
        try:
            await progress.update(
                progress=30,
                step="图片索引创建出错",
                data={"faiss_status": "error", "error": str(e)}
            )
        except:
            pass  # Don't let progress update errors propagate


async def _wait_for_faiss_index(
    user_id: int,
    task_id: str,
    timeout: float = 30.0,
    poll_interval: float = 2.0
) -> Optional[Any]:
    """
    等待后台 FAISS 索引创建完成

    查找策略（按优先级）：
    1. faiss_cache（Redis 元数据 + 文件系统）— 后台 _create_index_background 创建的索引
    2. 文件系统直接加载 — 搜索阶段 get_streamlit_faiss_index() 已保存的索引
       （搜索阶段通过 searxng_utils → grab_html_content 在处理图片时已创建 FAISS 索引，
        但不会注册到 Redis 元数据中，所以 faiss_cache 找不到）

    Args:
        user_id: 用户 ID
        task_id: 任务 ID（使用 article_id）
        timeout: 最大等待时间（秒），默认 30 秒
        poll_interval: 轮询间隔（秒），默认 2 秒

    Returns:
        FAISSIndex 实例如果索引就绪，None 如果超时或失败
    """
    # Validate poll_interval
    if poll_interval <= 0:
        raise ValueError(f"poll_interval must be positive, got {poll_interval}")

    start_time = time.time()
    filesystem_checked = False

    logger.info(f"[FAISS] Waiting for index to be ready: user={user_id}, task={task_id}, timeout={timeout}s")

    while True:
        elapsed = time.time() - start_time

        # 检查超时
        if elapsed >= timeout:
            logger.warning(f"[FAISS] Timeout waiting for index: user={user_id}, task={task_id}, elapsed={elapsed:.1f}s")
            return None

        # 尝试从 faiss_cache 获取索引（需要 Redis 元数据）
        faiss_index = await faiss_cache.get_or_load_index(user_id, task_id)

        if faiss_index is not None:
            # 检查索引是否为空
            if faiss_index.get_size() > 0:
                logger.info(f"[FAISS] Index ready (cache): user={user_id}, task={task_id}, size={faiss_index.get_size()}, elapsed={elapsed:.1f}s")
                return faiss_index
            else:
                logger.debug(f"[FAISS] Index exists but empty: user={user_id}, task={task_id}")

        # 文件系统回退：搜索阶段通过 get_streamlit_faiss_index() 已保存索引到磁盘，
        # 但不会注册到 Redis 元数据中。直接尝试从磁盘加载。
        if not filesystem_checked:
            try:
                from utils.embedding_utils import create_faiss_index
                disk_index = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: create_faiss_index(
                        load_from_disk=True,
                        index_dir='data/faiss',
                        username=str(user_id),
                        article_id=task_id
                    )
                )
                if disk_index and disk_index.get_size() > 0:
                    logger.info(f"[FAISS] Index loaded from filesystem fallback: user={user_id}, task={task_id}, size={disk_index.get_size()}")
                    # 注册到 faiss_cache 以便后续使用
                    await faiss_cache.save_index(user_id, task_id, disk_index, status="normal")
                    return disk_index
                else:
                    logger.debug(f"[FAISS] Filesystem index empty or not found: user={user_id}, task={task_id}")
            except Exception as e:
                logger.debug(f"[FAISS] Filesystem fallback failed: user={user_id}, task={task_id}, error={e}")
            filesystem_checked = True

        # 检查 Redis 状态（缓存 status_value 以避免重复调用 .get()）
        status = await redis_image_store.get_status(user_id, task_id)
        status_value = status.get('status')

        if status_value == 'failed':
            logger.warning(f"[FAISS] Index creation failed: user={user_id}, task={task_id}")
            return None

        # 检查是否已标记为 ready 但索引尚未加载到缓存
        if status_value == 'ready':
            logger.debug(f"[FAISS] Index marked ready in Redis, waiting for cache: user={user_id}, task={task_id}")

        # 等待一段时间后重试
        logger.debug(f"[FAISS] Index not ready, polling in {poll_interval}s: user={user_id}, task={task_id}")
        await asyncio.sleep(poll_interval)


async def generate_article_task(
    ctx,
    task_id: str,
    topic: str,
    user_id: int,
    custom_style: str = "",
    spider_num: int = None,
    extra_urls: list = None,
    model_type: str = "deepseek",
    model_name: str = "deepseek-chat"
) -> dict:
    """
    Generate article task for arq worker
    """
    logger.info(f"Starting article generation: task_id={task_id}, topic={topic}, user_id={user_id}")

    # 设置用户上下文，加载用户的 LLM 配置
    set_user_context(user_id)

    from backend.api.workers.progress import ProgressTracker

    progress = ProgressTracker(task_id)
    # Set status to running immediately
    await progress.update(0, "正在启动任务...", status="running")

    try:
        # Execute search
        search_result = await execute_search(
            topic=topic,
            spider_num=spider_num,
            enable_images=True,
            extra_urls=extra_urls,
            progress_tracker=progress,
            model_type=model_type,
            model_name=model_name,
            user_id=user_id,
            task_id=task_id
        )

        # Generate outline
        outline = await generate_outline(
            search_results=search_result,
            topic=topic,
            model_type=model_type,
            model_name=model_name,
            custom_style=custom_style,
            progress_tracker=progress
        )

        # Write content
        content = await write_article_content(
            outline=outline,
            search_results=search_result,
            topic=topic,
            model_type=model_type,
            model_name=model_name,
            custom_style=custom_style,
            progress_tracker=progress,
            user_id=user_id,
            task_id=task_id
        )

        # Save to database
        article_id = await save_article_to_database(
            task_id=task_id,
            user_id=user_id,
            title=outline.get('title', topic),
            content=content,
            summary=outline.get('summary', ''),
            outline=outline,
            topic=topic,
            model_type=model_type,
            model_name=model_name
        )

        # Auto-score the article after successful generation
        try:
            from backend.api.services.article_scoring import ArticleScoringService
            from backend.api.db.models.article import ArticleScore
            from datetime import datetime
            import json

            # Calculate scores
            readability = ArticleScoringService.calculate_readability_score(content)
            info_density = await ArticleScoringService.calculate_information_density_score(content, article['title'])
            seo = await ArticleScoringService.calculate_seo_score(content, article['title'])
            virality = await ArticleScoringService.calculate_virality_score(content, article['title'])

            dimensions = [readability, info_density, seo, virality]
            total_score = ArticleScoringService.calculate_total_score(dimensions)
            level = ArticleScoringService.get_level(total_score)
            summary = ArticleScoringService.generate_summary(total_score, level, dimensions)

            # Save score to database
            await ArticleScore.create(
                article_id=article_id,
                total_score=total_score,
                level=level,
                summary=summary,
                dimensions=json.dumps(dimensions),
                scored_at=datetime.now()
            )
            logger.info(f"Auto-scored article {article_id}: {total_score} points ({level})")

            # 更新用户评分统计（集成点：评分完成后更新 UserStats）
            try:
                from backend.api.workers.stats_refresh_worker import update_user_score_stats
                await update_user_score_stats(user_id, total_score)
                logger.debug(f"Updated user {user_id} score stats after scoring")
            except Exception as stats_e:
                logger.warning(f"Failed to update user score stats: {stats_e}")

        except Exception as e:
            logger.error(f"Auto-scoring failed for article {article_id}: {e}")

        # 更新用户文章统计（集成点：文章生成完成后更新 UserStats）
        try:
            from backend.api.workers.stats_refresh_worker import increment_user_article_count
            word_count = len(content) if content else 0
            await increment_user_article_count(user_id, word_count)
            logger.debug(f"Updated user {user_id} article count stats")
        except Exception as stats_e:
            logger.warning(f"Failed to update user article stats: {stats_e}")

        # Mark FAISS index as completed
        from backend.api.core.faiss_cache import faiss_cache
        await faiss_cache.mark_task_status(user_id, task_id, "completed")

        # Complete
        article = {
            'id': str(article_id),
            'task_id': task_id,
            'title': outline.get('title', topic),
            'content': content,
            'summary': outline.get('summary', ''),
            'outline': outline
        }

        await progress.complete(article)

        return {
            'success': True,
            'task_id': task_id,
            'article_id': str(article_id),
            'title': article['title']
        }

    except Exception as e:
        logger.error(f"Article generation failed: {e}")
        await progress.error(str(e))
        return {
            'success': False,
            'error': str(e),
            'task_id': task_id
        }
