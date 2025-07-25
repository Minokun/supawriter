import os
import sys
import logging
import numpy as np
import faiss
from typing import List, Dict, Any, Tuple, Optional
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import EMBEDDING_TYPE, EMBEDDING_CONFIG, EMBEDDING_D
from openai import OpenAI
import requests

logger = logging.getLogger(__name__)
    
class Embedding:
    def get_embedding(self, data):
        if EMBEDDING_TYPE == "gitee":
            response = OpenAI(
                base_url=EMBEDDING_CONFIG[EMBEDDING_TYPE]['host'],
                api_key=EMBEDDING_CONFIG[EMBEDDING_TYPE]['api_key'],
                timeout=EMBEDDING_CONFIG[EMBEDDING_TYPE]['timeout']
            ).embeddings.create(
                model=EMBEDDING_CONFIG[EMBEDDING_TYPE]['model'],
                input=data
            )
            return [i.embedding for i in response.data]
        else:
            url = EMBEDDING_CONFIG[EMBEDDING_TYPE]['host']
            headers = {
                'Authorization': f'Bearer {EMBEDDING_CONFIG[EMBEDDING_TYPE]["api_key"]}',
                'Content-Type': 'application/json'
            }
            task = "retrieval" if EMBEDDING_TYPE == "xinference" else "retrieval.passage"
            data = {
                'model': EMBEDDING_CONFIG[EMBEDDING_TYPE]['model'],
                'task': task,
                'input': data
            }
            response = requests.post(url, headers=headers, json=data, timeout=EMBEDDING_CONFIG[EMBEDDING_TYPE]['timeout'])
            return [i['embedding'] for i in response.json()['data']]
            
    def cosine_similarity(self, text1, text2):
        """
        计算两段文本的余弦相似度
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            
        Returns:
            float: 余弦相似度，范围为[-1, 1]，值越大表示越相似
        """
        try:
            # 获取两段文本的向量表示
            embedding1, embedding2 = self.get_embedding([text1, text2])
            
            if embedding1 is None or embedding2 is None:
                logger.warning("Failed to get embeddings for similarity calculation")
                return 0.0
                
            # 转换为numpy数组以便于计算
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # 计算余弦相似度: cos(θ) = (A · B) / (||A|| × ||B||)
            dot_product = np.dot(vec1, vec2)
            norm_a = np.linalg.norm(vec1)
            norm_b = np.linalg.norm(vec2)
            
            # 避免除零错误
            if norm_a == 0 or norm_b == 0:
                return 0.0
                
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)  # 确保返回浮点数
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0  # 出错时返回0相似度



class FAISSIndex:
    def __init__(self):
        """
        Initialize a FAISS index for storing and retrieving embeddings.
        使用内积(IP)索引计算余弦相似度，向量维度固定为EMBEDDING_D。
        """
        self.index = faiss.IndexFlatIP(EMBEDDING_D)  # 使用内积索引计算余弦相似度
        self.data = []  # Store original data corresponding to embeddings
        logger.info(f"FAISS index initialized with dimension: {EMBEDDING_D} using IndexFlatIP")
    
    def add_embeddings(self, embeddings: List[List[float]], data: List[Any]) -> None:
        """
        Add embeddings and corresponding data to the index.
        
        Args:
            embeddings: List of embedding vectors.
            data: List of data corresponding to the embeddings.
        """
        if len(embeddings) != len(data):
            logger.warning(f"Mismatch between embeddings ({len(embeddings)}) and data ({len(data)})")
            return
            
        # Convert embeddings to numpy array
        embeddings_np = np.array(embeddings).astype('float32')
        
        # 对向量进行L2归一化，使内积等价于余弦相似度
        faiss.normalize_L2(embeddings_np)
        
        # Add embeddings to index
        self.index.add(embeddings_np)
        
        # Store corresponding data
        self.data.extend(data)
        logger.debug(f"Added {len(embeddings)} embeddings to FAISS index. Total: {len(self.data)}")
    
    def add_embedding(self, embedding: List[float], data_item: Any) -> None:
        """
        Add a single embedding and its corresponding data to the index.
        
        Args:
            embedding: The embedding vector.
            data_item: The data corresponding to the embedding.
        """
        self.add_embeddings([embedding], [data_item])
    
    def search(self, query_embedding: List[float], k: int = 5) -> Tuple[List[int], List[float], List[Any]]:
        """
        Search for similar embeddings in the index.
        
        Args:
            query_embedding: The query embedding vector.
            k: Number of results to return.
            
        Returns:
            Tuple containing (indices, distances, data)
        """
        # Ensure k doesn't exceed the number of items in the index
        k = min(k, len(self.data))
        if k == 0:
            logger.warning("FAISS index is empty, cannot perform search")
            return [], [], []
            
        # Convert query to numpy array
        query_np = np.array([query_embedding]).astype('float32')
        
        # 对查询向量进行L2归一化，使内积等价于余弦相似度
        faiss.normalize_L2(query_np)
        
        # Perform search
        distances, indices = self.index.search(query_np, k)
        
        # Flatten results
        indices = indices[0].tolist()
        distances = distances[0].tolist()
        
        # 由于我们使用内积索引，距离实际上是相似度分数（越大越相似）
        # 转换为标准距离格式（越小越相似）
        distances = [1 - d for d in distances]
        
        # Get corresponding data
        result_data = [self.data[i] for i in indices]
        
        return indices, distances, result_data
        
    def get_size(self) -> int:
        """
        Get the number of items in the FAISS index.
        
        Returns:
            int: Number of items in the index
        """
        return len(self.data)
    
    def clear(self) -> None:
        """
        Clear the FAISS index and associated data.
        
        Returns:
            None
        """
        # 重新初始化索引
        self.index = faiss.IndexFlatIP(EMBEDDING_D)
        # 清空数据
        self.data = []
        logger.info("FAISS索引已清空")
            
        # 将空索引保存到磁盘
        try:
            # 默认索引路径
            index_dir = 'data/faiss'
            index_path = f"{index_dir}/index.faiss"
            data_path = f"{index_dir}/index_data.pkl"
                
            # 确保目录存在
            import os
            os.makedirs(index_dir, exist_ok=True)
                
            # 保存空索引到磁盘
            success = self.save_to_disk(index_path, data_path)
            if success:
                logger.info(f"空FAISS索引已保存到磁盘: {index_path}")
            else:
                logger.warning(f"保存空FAISS索引到磁盘失败")
        except Exception as e:
            logger.error(f"保存空FAISS索引到磁盘时出错: {str(e)}")
        
    def save_to_disk(self, index_path: str, data_path: str) -> bool:
        """
        Save the index and data to disk.
        
        Args:
            index_path: Path to save the index.
            data_path: Path to save the data.
            
        Returns:
            True if successful, False otherwise.
        """
        import pickle
        import os
            
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            
            # 保存索引
            faiss.write_index(self.index, index_path)
            
            # 保存数据
            data_dict = {
                'data': self.data
            }
            with open(data_path, 'wb') as f:
                pickle.dump(data_dict, f)
                
            logger.info(f"Successfully saved FAISS index to {index_path} and data to {data_path} (items: {len(self.data)})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index to disk: {str(e)}")
            return False
            
    def load_from_disk(self, index_path: str, data_path: str) -> bool:
        """
        Load a FAISS index and associated data from disk.
        
        Args:
            index_path: Path from where to load the FAISS index
            data_path: Path from where to load the associated data
            
        Returns:
            bool: True if successful, False otherwise
        """
        import pickle
        import os
        
        try:
            # Check if files exist
            if not os.path.exists(index_path) or not os.path.exists(data_path):
                logger.warning(f"FAISS index or data file not found at {index_path} or {data_path}")
                return False
                
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            
            # Load associated data
            with open(data_path, 'rb') as f:
                data_dict = pickle.load(f)
                self.data = data_dict['data']
                # 兼容旧版本数据，忽略dimension字段
            
            logger.info(f"Successfully loaded FAISS index from {index_path} with {len(self.data)} items")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index from disk: {str(e)}")
            return False


def create_faiss_index(load_from_disk: bool = False, index_dir: str = 'data/faiss', username: str = None, article_id: str = None) -> FAISSIndex:
    """
    创建一个新的FAISS索引实例，可选从磁盘加载。
    维度将在添加第一个embedding时自动设置。
    
    Args:
        load_from_disk: 是否尝试从磁盘加载现有索引
        index_dir: FAISS索引文件的存储目录
        username: 用户名，用于创建用户特定的索引路径
        article_id: 文章ID，用于创建文章特定的索引路径
        
    Returns:
        FAISSIndex: 新创建的或从磁盘加载的FAISS索引实例
    """
    import os
    from pathlib import Path
    
    faiss_index = FAISSIndex()
    
    # 根据用户名和文章ID构建索引路径
    if username and article_id:
        # 使用文章特定的索引路径：/data/faiss/{username}/{article_id}/
        actual_index_dir = os.path.join(index_dir, username, article_id)
    elif username:
        # 使用用户特定的索引路径：/data/faiss/{username}/
        actual_index_dir = os.path.join(index_dir, username)
    else:
        # 使用全局索引路径
        actual_index_dir = index_dir
    
    # 设置索引文件路径
    index_path = os.path.join(actual_index_dir, 'index.faiss')
    data_path = os.path.join(actual_index_dir, 'index_data.pkl')
    
    # 如果指定从磁盘加载且文件存在，尝试加载
    if load_from_disk:
        # 创建目录（如果不存在）
        Path(actual_index_dir).mkdir(parents=True, exist_ok=True)
        
        # 检查文件是否存在
        index_exists = os.path.exists(index_path)
        data_exists = os.path.exists(data_path)
        
        if index_exists and data_exists:
            success = faiss_index.load_from_disk(index_path, data_path)
            if success:
                logger.info(f"Loaded existing FAISS index from {index_path} with {faiss_index.get_size()} items")
                return faiss_index
            else:
                logger.warning("Failed to load FAISS index from disk, creating a new one")
        else:
            logger.info(f"No existing FAISS index found at {index_path}, creating a new one")
    
    # 如果没有指定从磁盘加载或加载失败，创建新的索引实例
    logger.info("Created new FAISS index instance")
    return faiss_index


def save_faiss_index(faiss_index: FAISSIndex, index_dir: str = 'data/faiss', username: str = None, article_id: str = None) -> bool:
    """
    将FAISS索引保存到磁盘。
    
    Args:
        faiss_index: 要保存的FAISS索引实例
        index_dir: FAISS索引文件的存储目录
        username: 用户名，用于创建用户特定的索引路径
        article_id: 文章ID，用于创建文章特定的索引路径
        
    Returns:
        bool: 是否成功保存
    """
    import os
    from pathlib import Path
    
    # 根据用户名和文章ID构建索引路径
    if username and article_id:
        # 使用文章特定的索引路径：/data/faiss/{username}/{article_id}/
        actual_index_dir = os.path.join(index_dir, username, article_id)
    elif username:
        # 使用用户特定的索引路径：/data/faiss/{username}/
        actual_index_dir = os.path.join(index_dir, username)
    else:
        # 使用全局索引路径
        actual_index_dir = index_dir
    
    # 创建目录（如果不存在）
    Path(actual_index_dir).mkdir(parents=True, exist_ok=True)
    
    # 设置索引文件路径 - 统一使用index.faiss和index_data.pkl命名
    index_path = os.path.join(actual_index_dir, 'index.faiss')
    data_path = os.path.join(actual_index_dir, 'index_data.pkl')
        
    # 保存到磁盘
    return faiss_index.save_to_disk(index_path, data_path)


def add_to_faiss_index(text: str, data: Any, faiss_index: FAISSIndex, auto_save: bool = True, username: str = None, article_id: str = None) -> None:
    """
    Add a text string and its corresponding data to the provided FAISS index.
    The text will be converted to an embedding vector automatically.
        
    Args:
        text: The text string to be embedded.
        data: The data object corresponding to the text.
        faiss_index: The FAISS index instance to add the embedding to.
        auto_save: Whether to automatically save the index after adding the embedding.
        username: Optional username for saving the index to a user-specific location.
        article_id: Optional article ID for saving the index to an article-specific location.
    """
    # 获取文本的embedding向量
    embedding_vectors = Embedding().get_embedding([text])
        
    # 检查embedding是否成功
    if not embedding_vectors or len(embedding_vectors) == 0:
        logger.warning(f"Failed to create embedding for text: {text[:50]}...")
        return
        
    # 添加到索引
    faiss_index.add_embedding(embedding_vectors[0], data)
    
    # 自动保存到磁盘
    if auto_save:
        try:
            save_faiss_index(faiss_index, username=username, article_id=article_id)
            logger.debug(f"Auto-saved FAISS index after adding embedding")
        except Exception as e:
            logger.warning(f"Failed to auto-save FAISS index: {str(e)}")


def add_batch_to_faiss_index(texts: List[str], data: List[Any], faiss_index: FAISSIndex) -> None:
    """
    Add a batch of text strings and their corresponding data to the provided FAISS index.
    The texts will be converted to embedding vectors automatically.
    
    Args:
        texts: List of text strings to be embedded.
        data: List of corresponding data objects.
        faiss_index: The FAISS index instance to add the embeddings to.
    """
    if not texts or len(texts) == 0:
        logger.warning("No texts provided to add to FAISS index")
        return
        
    # 批量获取embeddings
    embedding_vectors = Embedding().get_embedding(texts)
    
    if not embedding_vectors or len(embedding_vectors) == 0:
        logger.warning("No valid embeddings were created")
        return
    
    # 过滤有效的embeddings和对应的数据
    valid_embeddings = []
    valid_data = []
    
    for i, embedding in enumerate(embedding_vectors):
        if embedding is not None:
            valid_embeddings.append(embedding)
            valid_data.append(data[i])
    
    if not valid_embeddings:
        logger.warning("No valid embeddings were created after filtering")
        return
        
    # 添加到索引
    faiss_index.add_embeddings(valid_embeddings, valid_data)


def add_batch_embeddings_to_faiss_index(embeddings: List[List[float]], data: List[Any], faiss_index: FAISSIndex) -> None:
    """
    Add a batch of pre-computed embeddings and their corresponding data to the provided FAISS index.
    
    Args:
        embeddings: List of embedding vectors.
        data: List of corresponding data objects.
        faiss_index: The FAISS index instance to add the embeddings to.
    """
    faiss_index.add_embeddings(embeddings, data)


def search_similar_text(query_text: str, faiss_index: FAISSIndex, k: int = 5) -> Tuple[List[int], List[float], List[Any]]:
    """
    Search for similar items in the provided FAISS index using a text query.
    
    Args:
        query_text: The text to search for similar items.
        faiss_index: The FAISS index instance to search in.
        k: Number of similar items to retrieve.
        
    Returns:
        Tuple containing (indices, distances, data)
    """
    # 获取查询文本的embedding
    embedding_vectors = Embedding().get_embedding([query_text])
    
    if not embedding_vectors or len(embedding_vectors) == 0:
        logger.warning(f"Failed to create embedding for query text: {query_text[:50]}...")
        return [], [], []
    
    # 使用embedding进行搜索
    return search_similar(embedding_vectors[0], faiss_index, k)


def search_similar(query_embedding: List[float], faiss_index: FAISSIndex, k: int = 5) -> Tuple[List[int], List[float], List[Any]]:
    """
    Search for similar items in the provided FAISS index.
    
    Args:
        query_embedding: The query embedding vector.
        faiss_index: The FAISS index instance to search in.
        k: Number of similar items to retrieve.
        
    Returns:
        Tuple containing (indices, distances, data)
    """
    return faiss_index.search(query_embedding, k)

# 提供get_embedding_instance函数以保持与现有代码的向后兼容性
def get_embedding_instance():
    """
    返回Embedding类的实例，用于向后兼容
    
    Returns:
        Embedding: Embedding类的实例
    """
    return Embedding()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # 测试FAISS功能 - 使用中文示例
    print("\n===== 添加中文测试数据 =====")
    
    # 创建一个测试用的FAISS索引
    test_index = create_faiss_index()
    
    # 添加单条数据
    print("\n1. 添加单条数据:")
    add_to_faiss_index("人工智能", {"text": "人工智能", "id": 1, "category": "技术"}, test_index)
    add_to_faiss_index("机器学习算法", {"text": "机器学习算法", "id": 2, "category": "技术"}, test_index)
    add_to_faiss_index("深度学习模型", {"text": "深度学习模型", "id": 3, "category": "技术"}, test_index)
    add_to_faiss_index("自然语言处理", {"text": "自然语言处理", "id": 4, "category": "技术"}, test_index)
    add_to_faiss_index("计算机视觉", {"text": "计算机视觉", "id": 5, "category": "技术"}, test_index)
    
    # 添加不同领域的数据
    add_to_faiss_index("中国历史文化", {"text": "中国历史文化", "id": 6, "category": "文化"}, test_index)
    add_to_faiss_index("唐诗宋词", {"text": "唐诗宋词", "id": 7, "category": "文学"}, test_index)
    add_to_faiss_index("现代文学作品", {"text": "现代文学作品", "id": 8, "category": "文学"}, test_index)
    
    # 添加长文本
    add_to_faiss_index(
        "人工智能是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。",
        {"text": "人工智能定义", "id": 9, "category": "定义"},
        test_index
    )
    
    # 批量添加数据
    print("\n2. 批量添加数据:")
    add_batch_to_faiss_index(
        [
            "深度学习是机器学习的一个分支，它使用多层神经网络来提取数据特征。",
            "卷积神经网络在图像识别领域取得了巨大的成功。",
            "循环神经网络适合处理序列数据，如自然语言和时间序列。",
            "强化学习是通过与环境交互来学习最优策略的方法。",
            "迁移学习可以将一个领域学到的知识应用到另一个相关领域。"
        ],
        [
            {"text": "深度学习简介", "id": 10, "category": "机器学习"},
            {"text": "卷积神经网络", "id": 11, "category": "深度学习"},
            {"text": "循环神经网络", "id": 12, "category": "深度学习"},
            {"text": "强化学习", "id": 13, "category": "机器学习"},
            {"text": "迁移学习", "id": 14, "category": "机器学习"}
        ],
        test_index
    )
    
    # 获取索引大小
    print(f"FAISS索引中共有 {test_index.get_size()} 条数据")
    
    # 测试文本搜索 - 相似度查询
    print("\n===== 文本相似度搜索测试 =====")
    
    # 测试1: 技术相关查询
    print("\n1. 查询'机器学习技术'相似内容:")
    indices, distances, data = search_similar_text("机器学习技术", test_index, k=3)
    for i, (dist, item) in enumerate(zip(distances, data)):
        print(f"  结果 {i+1}: {item['text']} (ID: {item['id']}, 类别: {item.get('category', 'N/A')}, 距离: {dist})")
    
    # 测试2: 文学相关查询
    print("\n2. 查询'中国古典诗词'相似内容:")
    indices, distances, data = search_similar_text("中国古典诗词", test_index, k=3)
    for i, (dist, item) in enumerate(zip(distances, data)):
        print(f"  结果 {i+1}: {item['text']} (ID: {item['id']}, 类别: {item.get('category', 'N/A')}, 距离: {dist})")
    
    # 测试3: 长句查询
    print("\n3. 查询'神经网络如何在计算机视觉中应用'相似内容:")
    indices, distances, data = search_similar_text("神经网络如何在计算机视觉中应用", test_index, k=3)
    for i, (dist, item) in enumerate(zip(distances, data)):
        print(f"  结果 {i+1}: {item['text']} (ID: {item['id']}, 类别: {item.get('category', 'N/A')}, 距离: {dist})")

    
    # 测试4: 使用预先计算的embedding进行搜索
    print("\n4. 使用预先计算的embedding进行搜索:")
    query_text = "人工智能的发展趋势"
    embedding_vectors = Embedding().get_embedding([query_text])
    query_embedding = embedding_vectors[0]
    print(f"查询: '{query_text}'")
    indices, distances, data = search_similar(query_embedding, test_index, k=3)
    for i, (dist, item) in enumerate(zip(distances, data)):
        print(f"  结果 {i+1}: {item['text']} (ID: {item['id']}, 类别: {item.get('category', 'N/A')}, 距离: {dist})")

    
    print("\n===== FAISS测试完成 =====")