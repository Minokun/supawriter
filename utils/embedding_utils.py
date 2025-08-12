import os
import sys
import logging
import numpy as np
import faiss
from typing import List, Dict, Any, Tuple, Optional, Union
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import get_embedding_type, get_embedding_config, get_embedding_dimension, DEFAULT_IMAGE_EMBEDDING_METHOD
import requests

logger = logging.getLogger(__name__)
    
class Embedding:
    def get_embedding(self, data, is_image_url=False):
        # Get the latest embedding configuration
        embedding_type = get_embedding_type()
        embedding_config = get_embedding_config()
        
        if is_image_url:
            data = [{"image": url} for url in data]
        # Defensive: ensure selected embedding_type exists in config
        if embedding_type not in embedding_config:
            logger.error(f"未在EMBEDDING_CONFIG中找到embedding类型: {embedding_type}")
            return []
        url = embedding_config[embedding_type]['host']
        headers = {
            'Authorization': f'Bearer {embedding_config[embedding_type]["api_key"]}',
            'Content-Type': 'application/json'
        }

        # Handle direct image URL embedding with jina-embeddings-v4
        # 只要模型是jina-embeddings-v4且is_image_url为true就可以直接图片用嵌入向量的方式，与embedding_type无关
        if embedding_type in ("gitee", "xinference"):
            # OpenAI-compatible providers usually require only model + input
            request_data = {
                'model': embedding_config[embedding_type]['model'],
                'input': data
            }
        elif embedding_type == "jina":
            # Jina embeddings may accept an optional task for text retrieval
            request_data = {
                'model': embedding_config[embedding_type]['model'],
                # 保持与原实现一致，仅对jina提供task参数
                'task': "retrieval.passage",
                'input': data
            }
        else:
            # Fallback: do not send unsupported fields like 'task'
            request_data = {
                'model': embedding_config[embedding_type]['model'],
                'input': data
            }
            
        logger.info(f"发送请求到 {url}，提供商: {embedding_type}，模型: {embedding_config[embedding_type]['model']}")
        response = requests.post(url, headers=headers, json=request_data, timeout=embedding_config[embedding_type]['timeout'])
        
        response_json = response.json()
        logger.debug(f"API响应状态码: {response.status_code}")
        
        # Parse response for image embeddings with better handling of different formats
        if 'data' in response_json:
            # Standard format
            embeddings = [i.get('embedding', []) for i in response_json.get('data', [])]
            if embeddings and any(embeddings):
                logger.debug(f"成功从'data'字段提取嵌入向量，维度: {len(embeddings[0])}")
                return embeddings
        logger.warning("'data'字段中没有找到嵌入向量")
        return []
            
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
        使用内积(IP)索引计算余弦相似度，向量维度动态获取。
        """
        self.index = None
        self.data = []  # Store original data corresponding to embeddings
        logger.debug("FAISS index initialized")
    
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
        
        # Initialize the index if it's not already initialized
        if self.index is None:
            # Get the current embedding dimension from the first embedding
            embedding_dim = embeddings_np.shape[1]
            self.index = faiss.IndexFlatIP(embedding_dim)
            logger.debug(f"FAISS index initialized with dimension: {embedding_dim} using IndexFlatIP")
        
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
        搜索与查询向量最相似的k个项目
        
        Args:
            query_embedding: 查询向量
            k: 返回的最相似项目数量
            
        Returns:
            Tuple[List[int], List[float], List[Any]]: 索引、相似度分数（越大越相似）和对应数据的元组
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
        similarities, indices = self.index.search(query_np, k)
        
        # Flatten results
        indices = indices[0].tolist()
        similarities = similarities[0].tolist()
        
        # 注意：由于我们使用内积索引和L2归一化，这里返回的是余弦相似度分数
        # 相似度范围为-1到1，值越大表示越相似
        
        # Get corresponding data
        result_data = [self.data[i] for i in indices]
        
        return indices, similarities, result_data
        
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
        # 重新初始化索引，使用当前的嵌入维度
        embedding_dim = get_embedding_dimension()
        self.index = faiss.IndexFlatIP(embedding_dim)
        # 清空数据
        self.data = []
        logger.debug(f"FAISS索引已清空，使用维度: {embedding_dim}")
            
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
                logger.debug(f"空FAISS索引已保存到磁盘: {index_path}")
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
                
            logger.debug(f"Successfully saved FAISS index to {index_path} and data to {data_path} (items: {len(self.data)})")
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
            
            logger.debug(f"Successfully loaded FAISS index from {index_path} with {len(self.data)} items")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index from disk: {str(e)}")
            return False


# 全局FAISS索引缓存，避免循环导入
global_faiss_index_cache = {}

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
    
    # 使用全局缓存字典而不是导入grab_html_content模块
    global global_faiss_index_cache
    cache_key = f"{username or 'global'}/{article_id or 'default'}"
    
    # 尝试从全局缓存获取索引
    if cache_key in global_faiss_index_cache:
        cached_index = global_faiss_index_cache[cache_key]
        try:
            index_size = cached_index.get_size()
            logger.debug(f"Using cached FAISS index for {cache_key} with {index_size} items")
            return cached_index
        except Exception as e:
            logger.debug(f"Cached index invalid: {e}, removing from cache")
            del global_faiss_index_cache[cache_key]
    
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
                logger.debug(f"Loaded existing FAISS index from {index_path} with {faiss_index.get_size()} items")
                # 更新全局缓存
                global_faiss_index_cache[cache_key] = faiss_index
                logger.debug(f"Updated global FAISS index cache for {cache_key}")
                return faiss_index
            else:
                logger.warning("Failed to load FAISS index from disk, creating a new one")
        else:
            logger.debug(f"No existing FAISS index found at {index_path}, creating a new one")
    
    # 如果没有指定从磁盘加载或加载失败，创建新的索引实例
    logger.debug("Created new FAISS index instance")
    # 将新创建的索引添加到缓存
    global_faiss_index_cache[cache_key] = faiss_index
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
    
    # 保存索引和数据
    logger.debug(f"保存FAISS索引到: {index_path}")
    logger.debug(f"保存FAISS数据到: {data_path}")
    return faiss_index.save_to_disk(index_path, data_path)


def add_to_faiss_index(text: str, data: Any, faiss_index: FAISSIndex, auto_save: bool = False, username: str = None, article_id: str = None, is_image_url: bool = False) -> bool:
    """
    Add a single text or image URL and its corresponding data to the provided FAISS index.
    The text will be converted to an embedding vector automatically.
    
    Args:
        text: Text string to be embedded or image URL if is_image_url=True
        data: Corresponding data object
        faiss_index: The FAISS index instance to add the embedding to
        auto_save: Whether to automatically save the index after adding
        username: Optional username for saving the index to a user-specific location
        article_id: Optional article ID for saving the index to an article-specific location
        is_image_url: Whether the input is an image URL (for direct embedding)
        
    Returns:
        bool: Whether the operation was successful
    """
    try:
        # Log what we're adding to the index
        input_type = "image URL" if is_image_url else "text"
        logger.debug(f"Adding {input_type} to FAISS index: {text[:50]}...")
        logger.debug(f"Current FAISS index size: {faiss_index.get_size()}")
        
        # Get embedding for the text or image URL
        embedding_vectors = Embedding().get_embedding([text], is_image_url=is_image_url)
        
        # More detailed logging about the embedding vectors
        if not embedding_vectors:
            logger.error(f"Failed to get embedding for {input_type}: {text[:50]}... (embedding_vectors is None or empty)")
            return False
        
        if len(embedding_vectors) == 0:
            logger.error(f"Empty embedding vector list returned for {input_type}: {text[:50]}...")
            return False
            
        # Check if the first embedding is valid
        if not embedding_vectors[0] or len(embedding_vectors[0]) == 0:
            logger.error(f"Empty embedding vector returned for {input_type}: {text[:50]}...")
            return False
            
        logger.debug(f"Successfully generated embedding vector for {input_type}: {text[:50]}... with dimension {len(embedding_vectors[0])}")
        
        # Validate embedding dimension against current setting
        current_dim = get_embedding_dimension()
        if len(embedding_vectors[0]) != current_dim:
            logger.warning(f"Embedding dimension mismatch! Expected {current_dim}, got {len(embedding_vectors[0])}. Attempting to proceed anyway.")
            
        # Add the embedding to the FAISS index
        embedding = embedding_vectors[0]
        logger.debug(f"Generated embedding vector with dimension: {len(embedding)}")
        
        try:
            # Log the embedding vector details
            logger.debug(f"Adding embedding vector to FAISS index. Vector type: {type(embedding)}, dimension: {len(embedding)}")
            
            # Check if the embedding vector is valid
            if not all(isinstance(x, (int, float)) for x in embedding):
                logger.error(f"Invalid embedding vector contains non-numeric values: {embedding[:10]}...")
                return False
                
            # Add the embedding to the index
            faiss_index.add_embedding(embedding, data)
            
            # Verify the addition was successful
            new_size = faiss_index.get_size()
            logger.debug(f"Successfully added embedding to FAISS index. New size: {new_size}")
            
            # Double-check if the size actually increased
            if new_size <= 0:
                logger.warning("FAISS index size is still 0 or negative after adding embedding!")
        except Exception as e:
            logger.error(f"Failed to add embedding vector to FAISS index: {str(e)}")
            logger.exception("Detailed error information:")
            return False
        
        # Auto save to disk if requested
        if auto_save:
            try:
                save_path = f"{username}/{article_id}" if username and article_id else "global"
                logger.debug(f"Auto-saving FAISS index to: {save_path}")
                save_faiss_index(faiss_index, username=username, article_id=article_id)
                logger.debug(f"Successfully saved FAISS index, size: {faiss_index.get_size()}")
            except Exception as e:
                logger.error(f"Failed to save FAISS index: {str(e)}")
                return False
                
        return True
    except Exception as e:
        logger.error(f"Error during embedding generation process: {str(e)}")
        logger.exception("Detailed error information:")
        return False


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


def search_similar_text(query_text: str, faiss_index: FAISSIndex, k: int = 5, is_image_url: bool = False) -> Tuple[List[int], List[float], List[Any]]:
    """
    Search for similar items in the provided FAISS index using a text query or image URL.
    
    Args:
        query_text: The text to search for similar items or image URL if is_image_url=True.
        faiss_index: The FAISS index instance to search in.
        k: Number of similar items to retrieve.
        is_image_url: If True, treats query_text as an image URL for direct embedding.
        
    Returns:
        Tuple containing (indices, similarities, data) where similarities are cosine similarity scores (higher is more similar)
    """
    # 获取查询文本或图片URL的embedding
    embedding_vectors = Embedding().get_embedding([query_text], is_image_url=is_image_url)
    
    if not embedding_vectors or len(embedding_vectors) == 0:
        input_type = "image URL" if is_image_url else "query text"
        logger.warning(f"Failed to create embedding for {input_type}: {query_text[:50]}...")
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
    query_image_url = "https://pic.rmb.bdstatic.com/bjh/bb86a146718/241201/ab354f89a3d0cbe739ade4ef981eb060.jpeg?for=bg"
    embedding_vectors = Embedding().get_embedding([query_image_url], is_image_url=True)
    query_embedding = embedding_vectors[0]
    print(f"查询: '{query_image_url}'")
    indices, distances, data = search_similar(query_embedding, test_index, k=3)
    for i, (dist, item) in enumerate(zip(distances, data)):
        print(f"  结果 {i+1}: {item['text']} (ID: {item['id']}, 类别: {item.get('category', 'N/A')}, 距离: {dist})")

    
    print("\n===== FAISS测试完成 =====")