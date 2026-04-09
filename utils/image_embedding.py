#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图片 Embedding 处理模块

使用 Jina Embeddings API 直接对图片进行向量化，替代多模态 Chat 模型。
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from utils.embedding_utils import Embedding, add_to_faiss_index, create_faiss_index

logger = logging.getLogger(__name__)


class ImageEmbeddingProcessor:
    """
    图片 Embedding 处理器

    使用 Jina embeddings-v4 模型直接对图片进行向量化，
    不再依赖多模态 Chat 模型生成描述文本。
    """

    def __init__(self):
        """初始化图片 Embedding 处理器"""
        self.embedding = Embedding()

    def process_image_urls(
        self,
        image_urls: List[str],
        username: str = None,
        article_id: str = None,
        task_id: str = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        批量处理图片 URL，生成 embedding 并存储到 FAISS 索引

        Args:
            image_urls: 图片 URL 列表
            username: 用户名（用于构建用户特定的 FAISS 索引路径）
            article_id: 文章 ID（用于构建文章特定的 FAISS 索引路径）
            task_id: 任务 ID（用于日志追踪）

        Returns:
            Tuple[List[Dict], int]: (成功处理的图片列表, 成功数量)
            图片列表格式: [{
                "image_url": str,
                "embedding": List[float],
                "dimension": int
            }]
        """
        if not image_urls:
            logger.debug("没有图片需要处理")
            return [], 0

        logger.info(f"开始处理 {len(image_urls)} 张图片的 embedding (task_id={task_id})")

        # 批量获取图片 embedding
        try:
            embedding_vectors = self.embedding.get_embedding(image_urls, is_image_url=True)

            if not embedding_vectors:
                logger.warning(f"未获取到任何图片 embedding (task_id={task_id})")
                return [], 0

            # 获取 embedding 维度
            dimension = len(embedding_vectors[0]) if embedding_vectors and embedding_vectors[0] else 0

            # 构建结果列表
            results = []
            success_count = 0

            for i, (url, vector) in enumerate(zip(image_urls, embedding_vectors)):
                if vector and len(vector) > 0:
                    results.append({
                        "image_url": url,
                        "embedding": vector,
                        "dimension": len(vector)
                    })
                    success_count += 1
                else:
                    logger.debug(f"图片 {i+1} embedding 为空: {url}")

            logger.info(f"图片 embedding 处理完成: {success_count}/{len(image_urls)} 成功 (task_id={task_id})")
            return results, success_count

        except Exception as e:
            logger.error(f"批量处理图片 embedding 失败: {e} (task_id={task_id})")
            return [], 0

    def process_and_index_images(
        self,
        image_urls: List[str],
        faiss_index,
        username: str = None,
        article_id: str = None,
        task_id: str = None
    ) -> int:
        """
        处理图片 URL 并直接添加到 FAISS 索引

        Args:
            image_urls: 图片 URL 列表
            faiss_index: FAISS 索引实例
            username: 用户名
            article_id: 文章 ID
            task_id: 任务 ID

        Returns:
            int: 成功添加到索引的图片数量
        """
        if not image_urls:
            return 0

        logger.info(f"开始处理 {len(image_urls)} 张图片并添加到 FAISS 索引 (task_id={task_id})")

        success_count = 0
        failed_urls = []

        for url in image_urls:
            try:
                # 准备数据
                data = {
                    "image_url": url,
                    "task_id": task_id,
                    "type": "image"
                }

                # 使用 add_to_faiss_index 直接添加图片 URL（is_image_url=True）
                if add_to_faiss_index(
                    text=url,
                    data=data,
                    faiss_index=faiss_index,
                    auto_save=False,  # 批量添加后统一保存
                    username=username,
                    article_id=article_id,
                    is_image_url=True
                ):
                    success_count += 1
                else:
                    failed_urls.append(url)

            except Exception as e:
                logger.debug(f"处理图片失败: {url} - {e}")
                failed_urls.append(url)

        if failed_urls:
            logger.debug(f"失败的图片 URL ({len(failed_urls)}): {failed_urls[:3]}...")

        logger.info(f"成功添加 {success_count}/{len(image_urls)} 张图片到 FAISS 索引 (task_id={task_id})")
        return success_count


# 全局实例
_image_embedding_processor = None


def get_image_embedding_processor() -> ImageEmbeddingProcessor:
    """获取图片 Embedding 处理器单例"""
    global _image_embedding_processor
    if _image_embedding_processor is None:
        _image_embedding_processor = ImageEmbeddingProcessor()
    return _image_embedding_processor


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    processor = get_image_embedding_processor()

    # 测试图片 URL
    test_urls = [
        "https://pic.rmb.bdstatic.com/bjh/bb86a146718/241201/ab354f89a3d0cbe739ade4ef981eb060.jpeg",
        "https://www.w3schools.com/images/img_2026_bootcamp_160.webp"
    ]

    print("\n=== 测试 1: 批量处理图片 URL ===")
    results, count = processor.process_image_urls(test_urls, task_id="test_001")
    print(f"处理结果: {count}/{len(test_urls)} 成功")
    for r in results:
        print(f"  - {r['image_url'][:50]}... (维度: {r['dimension']})")

    print("\n=== 测试 2: 处理并添加到 FAISS 索引 ===")
    faiss_index = create_faiss_index()
    added = processor.process_and_index_images(test_urls, faiss_index, task_id="test_002")
    print(f"添加到索引: {added}/{len(test_urls)}")
    print(f"索引大小: {faiss_index.get_size()}")
