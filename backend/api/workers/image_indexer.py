# -*- coding: utf-8 -*-
"""
图片索引器 - 递归分治Embedding策略
"""

import asyncio
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# 配置
INITIAL_BATCH_SIZE = 10  # 初始批次大小
MIN_BATCH_SIZE = 1       # 最小批次（单张）


async def batch_embed_with_fallback(
    image_urls: List[str]
) -> List:
    """
    递归分治embedding策略

    策略：
    1. 初始按10张/批分组
    2. 批次失败 → 对半拆分（10→5+5）
    3. 5张批次还失败 → 逐张处理
    4. 递归直到单张

    Args:
        image_urls: 图片URL列表

    Returns:
        embedding结果列表（失败的位置为None）
    """
    total = len(image_urls)

    if total == 0:
        return []

    logger.info(f"【递归分治模式】{total}张图片，初始批次={INITIAL_BATCH_SIZE}")

    # 初始分批
    embeddings = await _process_batches_recursive(
        image_urls,
        INITIAL_BATCH_SIZE,
        level=1
    )

    success_count = sum(1 for e in embeddings if e and len(e) > 0)
    logger.info(f"✓ Embedding完成: {success_count}/{total} 张图片成功")

    return embeddings


async def _process_batches_recursive(
    urls: List[str],
    batch_size: int,
    level: int
) -> List:
    """
    递归处理批次

    Args:
        urls: 图片URL列表
        batch_size: 当前批次大小
        level: 递归层级（用于日志）

    Returns:
        embedding结果列表
    """
    from utils.embedding_utils import Embedding

    total = len(urls)
    indent = "  " * level
    embeddings = [None] * total

    # 分批
    batches = [
        (i, urls[i:i + batch_size])
        for i in range(0, total, batch_size)
    ]

    logger.info(f"{indent}层级{level}: {total}张图片 → {len(batches)}批(每批≤{batch_size}张)")

    # 处理每批
    for start_idx, batch in batches:
        batch_num = start_idx // batch_size + 1

        # === 尝试批量发送 ===
        try:
            logger.info(f"{indent}  批次[{batch_num}]: 批量发送{len(batch)}张...")

            batch_embeddings = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: Embedding().get_embedding(batch, is_image_url=True)
            )

            # 验证结果
            if batch_embeddings and len(batch_embeddings) == len(batch):
                batch_success = sum(1 for e in batch_embeddings if e and len(e) > 0)
                logger.info(f"{indent}    ✓ 批次[{batch_num}]成功: {batch_success}/{len(batch)}张")

                # 保存结果
                for i, emb in enumerate(batch_embeddings):
                    embeddings[start_idx + i] = emb

                continue  # 该批成功，处理下一批

            else:
                logger.warning(f"{indent}    ✗ 批次[{batch_num}]返回数量不匹配")

        except Exception as e:
            logger.warning(f"{indent}    ✗ 批次[{batch_num}]失败: {e}")

        # === 批次失败，递归分治 ===

        # 终止条件：已经是单张了
        if len(batch) == MIN_BATCH_SIZE:
            logger.info(f"{indent}    批次[{batch_num}]已达最小批次，逐张处理...")

            single_emb = await _process_single_image(batch[0])
            embeddings[start_idx] = single_emb

            status = "✓" if (single_emb and len(single_emb) > 0) else "✗"
            logger.info(f"{indent}      [{status}] 单张完成: {batch[0][:40]}...")
            continue

        # 对半拆分
        half_size = max(MIN_BATCH_SIZE, len(batch) // 2)
        logger.info(f"{indent}    批次[{batch_num}]对半拆分: {len(batch)} → {half_size} + {len(batch) - half_size}")

        # 递归处理左半部分
        left_embeddings = await _process_batches_recursive(
            batch[:half_size],
            MIN_BATCH_SIZE,
            level + 1
        )

        # 递归处理右半部分
        right_embeddings = await _process_batches_recursive(
            batch[half_size:],
            MIN_BATCH_SIZE,
            level + 1
        )

        # 合并结果
        for i, emb in enumerate(left_embeddings + right_embeddings):
            embeddings[start_idx + i] = emb

    return embeddings


async def _process_single_image(url: str) -> List:
    """处理单张图片"""
    from utils.embedding_utils import Embedding

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Embedding().get_embedding([url], is_image_url=True)
        )
        return result[0] if result else None
    except Exception as e:
        logger.debug(f"单张图片embedding失败: {e}")
        return None
