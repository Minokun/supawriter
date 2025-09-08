import logging
import time
from typing import Callable, List, Dict

from utils.ddgs_utils import search_ddgs

from utils.embedding_utils import (
    Embedding,
    add_batch_embeddings_to_faiss_index,
    save_faiss_index,
)

logger = logging.getLogger(__name__)


def index_ddgs_images(
    query: str,
    faiss_index,
    username: str,
    article_id: str,
    max_results: int = 30,
    chunk_size: int = 30,
    log_fn: Callable[[str, str], None] | None = None,
) -> int:
    """
    Search images via DDGS, batch-embed up to chunk_size per request, and add to FAISS.

    Args:
        query: Search query.
        faiss_index: FAISSIndex instance to update.
        username: User name for saving.
        article_id: Article id for saving.
        max_results: Max images to fetch from DDGS.
        chunk_size: Max items per embedding API call (API supports up to 30).
        log_fn: Optional log function like log(level, msg).

    Returns:
        int: Count of images successfully embedded and added to FAISS.
    """
    def _log(level: str, msg: str):
        if log_fn:
            log_fn(level, msg)
        else:
            getattr(logger, level if level in ("info", "warning", "error", "debug") else "info")(msg)

    _log('info', f"开始使用DDGS进行图片搜索以丰富索引: query='{query}' ...")

    # 1) Search images via shared util
    ddgs_results = search_ddgs(query, 'images', max_results=max_results)
    _log('info', f"DDGS图片搜索完成，获取到 {len(ddgs_results)} 条图片结果")

    # 2) Prepare URLs and payloads
    image_urls: List[str] = []
    payloads: List[Dict] = []
    for item in ddgs_results:
        image_url = item.get('image') or item.get('thumbnail')
        if not image_url:
            continue
        title = item.get('title') or ''
        source_url = item.get('url') or item.get('source') or ''
        payloads.append({
            'image_url': image_url,
            'title': title,
            'source_url': source_url,
            'provider': 'ddgs',
        })
        image_urls.append(image_url)

    if not image_urls:
        _log('warning', 'DDGS未返回有效图片URL，跳过索引更新。')
        return 0

    # 3) Batch embed and add to FAISS
    total_added = 0
    batch_success = 0
    fallback_success = 0
    skipped = 0
    embedder = Embedding()

    for i in range(0, len(image_urls), chunk_size):
        batch_urls = image_urls[i:i + chunk_size]
        batch_payloads = payloads[i:i + chunk_size]
        try:
            vectors = embedder.get_embedding(batch_urls, is_image_url=True)
        except Exception as e:
            _log('error', f"批量获取图片embedding失败: {str(e)} | 批次范围: {i}-{i+len(batch_urls)-1}")
            vectors = None

        valid_vectors = []
        valid_payloads = []
        if vectors and isinstance(vectors, list) and len(vectors) == len(batch_urls):
            # 正常批量返回
            for vec, payload in zip(vectors, batch_payloads):
                if vec and isinstance(vec, list) and len(vec) > 0:
                    valid_vectors.append(vec)
                    valid_payloads.append(payload)
            if valid_vectors:
                batch_success += len(valid_vectors)
        else:
            # 批量失败或返回不完整，逐张回退
            _log('warning', f"批量嵌入返回空/不完整结果，回退为逐张处理。本批次大小: {len(batch_urls)}")
            for u, p in zip(batch_urls, batch_payloads):
                # 简单重试：最多2次，100ms退避
                attempts = 0
                single_vecs = None
                while attempts < 2 and not (single_vecs and isinstance(single_vecs, list) and len(single_vecs) > 0 and isinstance(single_vecs[0], list) and len(single_vecs[0]) > 0):
                    attempts += 1
                    try:
                        single_vecs = embedder.get_embedding([u], is_image_url=True)
                    except Exception as e:
                        _log('error', f"单张获取图片embedding失败(第{attempts}次): {str(e)} | url: {u}")
                        time.sleep(0.1)
                        continue
                    if not (single_vecs and isinstance(single_vecs, list) and len(single_vecs) > 0 and isinstance(single_vecs[0], list) and len(single_vecs[0]) > 0):
                        _log('warning', f"单张embedding返回空向量(第{attempts}次)，url: {u}")
                        time.sleep(0.1)
                if single_vecs and isinstance(single_vecs, list) and len(single_vecs) > 0 and isinstance(single_vecs[0], list) and len(single_vecs[0]) > 0:
                    valid_vectors.append(single_vecs[0])
                    valid_payloads.append(p)
                    fallback_success += 1
                else:
                    skipped += 1

        if not valid_vectors:
            continue

        add_batch_embeddings_to_faiss_index(valid_vectors, valid_payloads, faiss_index)
        total_added += len(valid_vectors)

    # 4) Save once
    if total_added > 0:
        save_faiss_index(faiss_index, username=username, article_id=article_id)
        _log('info', f"已将 {total_added} 张DDGS图片向量写入FAISS索引 | 批量成功: {batch_success} | 回退成功: {fallback_success} | 跳过: {skipped} | 当前索引大小: {faiss_index.get_size()}")
    else:
        _log('warning', '本次DDGS批量嵌入未成功添加任何图片向量。')

    return total_added
