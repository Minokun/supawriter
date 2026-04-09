# -*- coding: utf-8 -*-
"""
文章生成服务
复用 utils/searxng_utils.py 和 utils/article_queue.py 的核心逻辑
"""

import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import json

# 使用 backend 兼容层导入 searxng 工具
from backend.api.utils.searxng_compat import Search, llm_task, chat
import utils.prompt_template as pt
# create_faiss_index, search_similar_text 已移至 article_worker._insert_images_to_chapter
from backend.api.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class ArticleGeneratorService:
    """文章生成服务类"""
    
    def __init__(self):
        """初始化文章生成服务"""
        self.search_engine = Search(result_num=30)
    
    async def generate_article_stream(
        self,
        topic: str,
        user_id: int,
        article_id: str,
        model_type: str = 'deepseek',
        model_name: str = 'deepseek-chat',
        knowledge_document_ids: Optional[list] = None,
        custom_style: str = "",
        user_idea: Optional[str] = None,
        user_references: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成文章，实时推送进度

        Args:
            topic: 文章主题
            user_id: 用户ID
            article_id: 文章ID
            model_type: 模型类型
            model_name: 模型名称
            knowledge_document_ids: 知识库文档ID列表
            custom_style: 自定义风格
            user_idea: 用户的想法/观点（用于指导文章方向）
            user_references: 用户贴入的参考文字
            
        Yields:
            进度事件字典
        """
        from utils.searxng_utils import parse_outline_json
        from backend.api.utils.searxng_compat import set_user_context

        try:
            # 重置图片收集列表
            self._current_images = []
            
            # 设置用户上下文，以便动态加载用户的 LLM 配置
            set_user_context(user_id)

            # 初始化进度
            await self._update_progress(article_id, {
                "status": "running",
                "progress_percent": 0,
                "current_step": "开始生成文章...",
                "article_id": article_id,
                "topic": topic,
            })
            yield self._create_progress_event(article_id, 0, "开始生成文章...")

            # Step 1: 联网搜索（使用 get_search_result，与 auto_writer 一致）
            await self._update_progress(article_id, {
                "status": "running",
                "progress_percent": 10,
                "current_step": "联网搜索相关资料...",
            })
            yield self._create_progress_event(article_id, 10, "联网搜索相关资料...")

            # 进度回调：在搜索过程中更新Redis子步骤进度
            # 回调签名: (completed_count, total_count)
            # 负数表示图片embedding阶段: (-batch_num, -total_batches)
            _main_loop = asyncio.get_event_loop()
            
            def _search_progress_callback(completed, total):
                if completed < 0:
                    # 图片embedding阶段
                    msg = f"图片处理中 ({-completed}/{-total})"
                else:
                    msg = f"抓取网页 ({completed}/{total})"
                logger.info(f"[搜索进度] {msg}")
                try:
                    asyncio.run_coroutine_threadsafe(
                        self._update_progress(article_id, {
                            "status": "running",
                            "progress_percent": 15,
                            "current_step": msg,
                        }),
                        _main_loop
                    )
                except Exception:
                    pass

            # 搜索加超时保护（5分钟），避免图片嵌入卡死
            try:
                search_results = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.search_engine.get_search_result,
                        topic,
                        topic,   # theme - 用于图片搜索
                        True,    # spider_mode
                        _search_progress_callback,  # progress_callback
                        str(user_id) if user_id else None,  # username
                        article_id,
                        model_type,
                        model_name,
                    ),
                    timeout=300  # 5分钟超时
                )
            except asyncio.TimeoutError:
                logger.warning(f"搜索超时(5分钟), 使用已有结果继续: topic={topic}")
                search_results = getattr(self.search_engine, '_partial_results', []) or []
                await self._update_progress(article_id, {
                    "status": "running",
                    "progress_percent": 20,
                    "current_step": "搜索超时，使用已有结果继续...",
                })
                yield self._create_progress_event(article_id, 20, "搜索超时，使用已有结果继续...")

            result_count = len(search_results) if search_results else 0
            if result_count == 0:
                logger.warning(f"搜索无结果: topic={topic}")

            # 注入用户参考资料作为合成 SearchResult
            if user_references and search_results is not None:
                synthetic_ref = {
                    'title': '用户参考资料',
                    'html_content': user_references,
                    'url': '',
                    'images': [],
                    'source': 'user',
                    'relevance_score': 999,
                }
                search_results.insert(0, synthetic_ref)
                result_count = len(search_results)
                logger.info(f"注入用户参考资料: {len(user_references)} 字符")

            # 构建用户想法标签（用于注入 prompt）
            user_idea_tag = f'<user_idea>{user_idea}</user_idea>' if user_idea else ''

            # 获取搜索统计信息
            search_stats = getattr(self.search_engine, 'last_search_stats', {})
            
            # 准备搜索结果列表（用于前端展示溯源，过滤用户资料）
            search_result_items = []
            for item in search_results[:50]:  # 限制最多50条
                if item.get('source') == 'user':
                    continue  # 跳过用户参考资料，不在溯源中显示
                search_result_items.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('html_content', '')[:200] if item.get('html_content') else '',
                    'source': item.get('source', 'ddgs')
                })

            # 将搜索结果和统计信息序列化后存储到Redis，供SSE轮询读取
            await self._update_progress(article_id, {
                "status": "running",
                "progress_percent": 25,
                "current_step": f"找到 {result_count} 条相关资料",
                "search_results": json.dumps(search_result_items, ensure_ascii=False),
                "search_stats": json.dumps(search_stats, ensure_ascii=False) if search_stats else "",
            })
            yield self._create_progress_event(
                article_id, 25, 
                f"找到 {result_count} 条相关资料",
                {
                    "type": "search",
                    "search_stats": search_stats,
                    "search_results": search_result_items
                }
            )

            # 日志：搜索图片统计
            total_images_in_results = sum(len(r.get('images', [])) for r in search_results if isinstance(r, dict))
            logger.info(f"[图片搜索] topic={topic}, 搜索结果数={result_count}, 包含图片的结果数={sum(1 for r in search_results if r.get('images'))}, 总图片数={total_images_in_results}")
            if search_stats:
                logger.info(f"[图片搜索] search_stats: web_images={search_stats.get('web_images_count', 0)}, total_images={search_stats.get('total_images_count', 0)}")

            # 提取图片URL并存入Redis，触发后台FAISS索引创建（与article_worker.execute_search对齐）
            image_urls_set = set()
            for r in search_results:
                if isinstance(r, dict):
                    imgs = r.get('images', [])
                    if isinstance(imgs, list):
                        image_urls_set.update(imgs)
            image_urls = list(image_urls_set)

            if user_id and article_id and image_urls:
                try:
                    from backend.api.workers.image_store import redis_image_store
                    from backend.api.workers.article_worker import _create_index_background
                    image_count = await redis_image_store.add_images(user_id, article_id, image_urls)
                    logger.info(f"[图片索引] 存储 {image_count} 张图片到Redis: user={user_id}, task={article_id}")
                    asyncio.create_task(_create_index_background(user_id, article_id))
                    logger.info(f"[图片索引] 已触发后台FAISS索引创建: user={user_id}, task={article_id}")
                except Exception as e:
                    logger.warning(f"[图片索引] 存储图片到Redis失败(搜索继续): {e}")

            # Step 2: 生成大纲（与 auto_writer 流程一致）
            await self._update_progress(article_id, {
                "status": "running",
                "progress_percent": 30,
                "current_step": "生成文章大纲...",
            })
            yield self._create_progress_event(article_id, 30, "生成文章大纲...")

            # 2a: 用 llm_task 对每条搜索结果生成大纲片段
            outlines = await asyncio.to_thread(
                llm_task,
                search_results,
                topic,
                pt.ARTICLE_OUTLINE_GEN,
                model_type,
                model_name,
                10,  # max_workers
            )

            # 2b: 用 chat 融合多份大纲为一份完整大纲
            def _fuse_outline():
                idea_part = f' {user_idea_tag}' if user_idea_tag else ''
                return chat(
                    f'<topic>{topic}</topic>{idea_part} <content>{outlines}</content>',
                    pt.ARTICLE_OUTLINE_SUMMARY,
                    model_type=model_type,
                    model_name=model_name,
                    max_tokens=16384,
                )
            outline_summary = await asyncio.to_thread(_fuse_outline)

            # 2c: 解析大纲 JSON
            outline = parse_outline_json(outline_summary, topic)

            await self._update_progress(article_id, {
                "status": "running",
                "progress_percent": 45,
                "current_step": "大纲生成完成",
                "outline": json.dumps(outline, ensure_ascii=False),
            })
            yield self._create_progress_event(article_id, 45, "大纲生成完成", {"outline": outline})

            # Step 3: 按章节生成内容（对齐 Streamlit / article_worker 流程）
            from backend.api.workers.article_worker import _insert_images_to_chapter

            content_outline = outline.get('content_outline', [])
            total_sections = len(content_outline)
            section_progress_step = 45 / max(total_sections, 1)

            article_chapters = []
            used_images = set()  # 跨章节共享已使用图片集合

            for idx, section in enumerate(content_outline, 1):
                h1 = section.get('h1', '')
                h2_list = section.get('h2', [])
                current_progress = 45 + int(idx * section_progress_step)
                is_first_chapter = idx == 1

                await self._update_progress(article_id, {
                    "status": "running",
                    "progress_percent": current_progress,
                    "current_step": f"生成章节 {idx}/{total_sections}: {h1}",
                })
                yield self._create_progress_event(
                    article_id, current_progress,
                    f"生成章节 {idx}/{total_sections}: {h1}"
                )

                # 与 Streamlit 一致：整个 outline_block 作为一个单元生成
                title_instruction = '，注意不要包含任何标题，直接开始正文内容，有吸引力开头（痛点/悬念），生动形象，风趣幽默！' if is_first_chapter else ''
                idea_part = f' {user_idea_tag}' if user_idea_tag else ''
                question = f'<完整大纲>{outline_summary}</完整大纲>{idea_part} 请根据上述信息，书写出以下内容 >>> {section} <<<{title_instruction}'

                # 先用 llm_task 基于搜索结果生成素材
                block_content = await asyncio.to_thread(
                    llm_task,
                    search_results,
                    question,
                    pt.ARTICLE_OUTLINE_BLOCK,
                    model_type,
                    model_name,
                    10,
                )

                # 再用 chat 精炼成最终内容
                final_instruction = '，注意不要包含任何标题（不要包含h1和h2标题），直接开始正文内容' if is_first_chapter else ''
                def _refine(t=section, bc=block_content, fi=final_instruction, ip=idea_part):
                    return chat(
                        f'<完整大纲>{outline_summary}</完整大纲>{ip} '
                        f'<相关资料>{bc}</相关资料> '
                        f'请根据上述信息，书写大纲中的以下这部分内容：{t}{fi}',
                        pt.ARTICLE_OUTLINE_BLOCK,
                        model_type=model_type,
                        model_name=model_name,
                    )
                chapter_content = await asyncio.to_thread(_refine)

                # 使用 FAISS 语义匹配插入图片（与 article_worker 共用逻辑）
                logger.info(f"[图片插入] 开始为章节 '{h1}' 插入图片 (FAISS)...")
                chapter_content = await _insert_images_to_chapter(
                    chapter_content=chapter_content,
                    outline_block=section,
                    search_results=search_results,
                    user_id=user_id,
                    task_id=article_id,
                    used_images=used_images,
                    max_images_per_chapter=3,
                    similarity_threshold=0
                )

                article_chapters.append(chapter_content)

                # 组装实时文章内容
                full_content = f"# {outline.get('title', topic)}\n\n" + '\n\n'.join(article_chapters)

                # 更新实时文章内容（每个章节完成后都推送）
                await self._update_progress(article_id, {
                    "status": "running",
                    "progress_percent": current_progress,
                    "current_step": f"章节 {idx}/{total_sections} 完成",
                    "content": full_content,
                })
                yield self._create_progress_event(
                    article_id, current_progress,
                    f"章节 {idx}/{total_sections} 完成",
                    {"live_article": full_content}
                )

            # 组装最终文章（不再将参考来源追加到正文中）
            full_content = f"# {outline.get('title', topic)}\n\n" + '\n\n'.join(article_chapters)

            # 构建参考来源（作为独立数据，不放入文章正文）
            references_list = []
            seen_urls = set()
            for item in search_results:
                if not isinstance(item, dict):
                    continue
                url = item.get('url', '').strip()
                title_text = item.get('title', '').strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                references_list.append({'title': title_text or url, 'url': url})

            # 构建文章元数据（用于DB保存和前端展示）
            article_metadata = {
                'model_type': model_type,
                'model_name': model_name,
                'spider_num': result_count,
                'custom_style': custom_style,
                'image_enabled': True,
                'total_images': total_images_in_results,
                'search_results_count': result_count,
                'references': references_list,
                'outline': outline,
            }

            # Step 4: 完成
            await self._update_progress(article_id, {
                "status": "completed",
                "progress_percent": 100,
                "current_step": "文章生成完成",
                "content": full_content,
                "references": json.dumps(references_list, ensure_ascii=False),
                "article_metadata": json.dumps(article_metadata, ensure_ascii=False),
            })
            yield self._create_progress_event(
                article_id, 100, "文章生成完成",
                {
                    "content": full_content,
                    "references": references_list,
                    "article_metadata": article_metadata,
                }
            )

        except Exception as e:
            logger.error(f"文章生成失败: {e}", exc_info=True)
            await self._update_progress(article_id, {
                "status": "failed",
                "progress_percent": 0,
                "current_step": "生成失败",
                "error_message": str(e),
            })
            yield self._create_progress_event(
                article_id, 0,
                f"生成失败: {str(e)}",
                error=True
            )
    
    async def _update_progress(self, article_id: str, data: Dict[str, Any]):
        """更新文章生成进度到 Redis"""
        try:
            await redis_client.set_article_progress(article_id, data)
        except Exception as e:
            logger.error(f"更新进度失败: {e}")
    
    def _create_progress_event(
        self, 
        article_id: str, 
        progress: int, 
        message: str,
        data: Optional[Dict] = None,
        error: bool = False
    ) -> Dict[str, Any]:
        """创建进度事件"""
        event = {
            "type": "error" if error else ("completed" if progress >= 100 else "progress"),
            "article_id": article_id,
            "progress_percent": progress,
            "current_step": message,
            "timestamp": datetime.now().isoformat()
        }
        if data:
            event["data"] = data
        if error:
            event["error_message"] = message
        return event
    
    # _find_relevant_images 已废弃，改用 article_worker._insert_images_to_chapter (FAISS 语义匹配)


# 全局实例
article_generator = ArticleGeneratorService()
