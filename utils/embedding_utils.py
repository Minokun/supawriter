import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
import sys
import logging
import numpy as np
import faiss
from typing import List, Dict, Any, Tuple, Optional
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import EMBEDDING_TYPE, EMBEDDING_MODEL_gitee, EMBEDDING_HOST_gitee, EMBEDDING_TIMEOUT_gitee, EMBEDDING_API_KEY_gitee, EMBEDDING_MODEL_xinference, EMBEDDING_HOST_xinference, EMBEDDING_TIMEOUT_xinference
from openai import OpenAI
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

gitee_client = OpenAI(
    base_url=EMBEDDING_HOST_gitee,
    api_key=EMBEDDING_API_KEY_gitee,
    timeout=EMBEDDING_TIMEOUT_gitee
)
xinference_client = OpenAI(
    base_url=f"{EMBEDDING_HOST_xinference}",
    api_key="not-needed",
    timeout=EMBEDDING_TIMEOUT_xinference
)

# 全局实例，避免重复创建
global_embedding_instance = None
global_faiss_index = None

def get_embedding_instance():
    """
    获取全局Embedding实例，如果不存在则创建一个
    
    Returns:
        Embedding: 全局Embedding实例
    """
    global global_embedding_instance
    if global_embedding_instance is None:
        global_embedding_instance = Embedding()
        logger.info("Created global Embedding instance")
    return global_embedding_instance
    
class Embedding:
    def __init__(self):
        global EMBEDDING_TYPE, gitee_client, xinference_client, EMBEDDING_MODEL_xinference, EMBEDDING_MODEL_gitee
        self.embedding_type = EMBEDDING_TYPE
        self.local_model_name = "BAAI/bge-large-zh-v1.5"
        self.embedding_model = EMBEDDING_MODEL_gitee if self.embedding_type == 'gitee' else EMBEDDING_MODEL_xinference
        self.embedding_host = EMBEDDING_HOST_gitee if self.embedding_type == 'gitee' else EMBEDDING_HOST_xinference
        self.embedding_timeout = EMBEDDING_TIMEOUT_gitee if self.embedding_type == 'gitee' else EMBEDDING_TIMEOUT_xinference
        self.embedding_api_key = EMBEDDING_API_KEY_gitee if self.embedding_type == 'gitee' else "not-needed"
        
        logger.info(f"Using embedding mode: {self.embedding_type}")
        
        if self.embedding_type == 'gitee':
            self.client = gitee_client
            logger.info(f"Gitee embedding model: {self.embedding_model} at {self.embedding_host}")
        elif self.embedding_type == 'xinference':
            self.client = xinference_client
            logger.info(f"Xinference embedding model: {self.embedding_model} at {self.embedding_host}")
        else:
            logger.info(f"Using local embedding model: {self.local_model_name}")
            try:
                # First try with trust_remote_code for models that might need it
                self.model = SentenceTransformer(self.local_model_name, trust_remote_code=True)
            except Exception as e:
                logger.warning(f"Failed to load with trust_remote_code=True: {e}, trying without it")
                # If that fails, try without trust_remote_code
                self.model = SentenceTransformer(self.local_model_name, trust_remote_code=False)
    
    def get_embedding(self, text):
        try:
            if self.embedding_type == 'gitee':
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=text,
                    encoding_format="float"
                )
                return response.data[0].embedding
            elif self.embedding_type == 'xinference':
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=text,
                    encoding_format="float"
                )
                return response.data[0].embedding
            else:
                return self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return None



class FAISSIndex:
    def __init__(self):
        """
        Initialize a FAISS index for storing and retrieving embeddings.
        维度将在添加第一个embedding时自动设置。
        """
        self.dimension = None
        self.index = None
        self.data = []  # Store original data corresponding to embeddings
        self.initialized = False
        logger.info("FAISS index initialized, dimension will be determined from first embedding")
    
    def _initialize_index(self, dimension: int) -> None:
        """
        Initialize the FAISS index with the specified dimension.
        
        Args:
            dimension: The dimension of the embeddings.
        """
        if self.initialized:
            return
            
        self.dimension = dimension
        # Using L2 distance for similarity search
        self.index = faiss.IndexFlatL2(dimension)
        self.initialized = True
        logger.info(f"FAISS index initialized with dimension: {dimension}")
    
    def add_embeddings(self, embeddings: List[List[float]], data: List[Any]) -> None:
        """
        Add embeddings and corresponding data to the index.
        
        Args:
            embeddings: List of embedding vectors.
            data: List of corresponding data objects.
        """
        if not embeddings or len(embeddings) == 0:
            logger.warning("No embeddings provided to add to FAISS index")
            return
            
        # Convert embeddings to numpy array
        embeddings_np = np.array(embeddings).astype('float32')
        
        # Initialize index if not already done
        if not self.initialized:
            self._initialize_index(embeddings_np.shape[1])
        
        # Add embeddings to index
        self.index.add(embeddings_np)
        
        # Store corresponding data
        self.data.extend(data)
        logger.info(f"Added {len(embeddings)} embeddings to FAISS index. Total: {len(self.data)}")
    
    def add_embedding(self, embedding: List[float], data_item: Any) -> None:
        """
        Add a single embedding and its corresponding data to the index.
        
        Args:
            embedding: The embedding vector.
            data_item: The corresponding data object.
        """
        self.add_embeddings([embedding], [data_item])
    
    def search(self, query_embedding: List[float], k: int = 5) -> Tuple[List[int], List[float], List[Any]]:
        """
        Search for similar embeddings in the index.
        
        Args:
            query_embedding: The query embedding vector.
            k: Number of similar items to retrieve.
            
        Returns:
            Tuple containing (indices, distances, data)
        """
        if not self.initialized:
            logger.warning("FAISS index not initialized yet, cannot perform search")
            return [], [], []
            
        # Ensure k doesn't exceed the number of items in the index
        k = min(k, len(self.data))
        if k == 0:
            return [], [], []
            
        # Convert query to numpy array
        query_np = np.array([query_embedding]).astype('float32')
        
        # Perform search
        distances, indices = self.index.search(query_np, k)
        
        # Get corresponding data
        result_data = [self.data[i] for i in indices[0]]
        
        return indices[0].tolist(), distances[0].tolist(), result_data
    
    def get_size(self) -> int:
        """
        Get the number of embeddings in the index.
        
        Returns:
            Number of embeddings in the index.
        """
        return len(self.data)


def get_faiss_index() -> FAISSIndex:
    """
    获取全局FAISS索引实例，如果不存在则创建一个。
    维度将在添加第一个embedding时自动设置。
        
    Returns:
        FAISSIndex: 全局FAISS索引实例
    """
    global global_faiss_index
    if global_faiss_index is None:
        global_faiss_index = FAISSIndex()
        logger.info("Created global FAISS index instance")
    return global_faiss_index


def add_to_faiss_index(text: str, data: Any) -> None:
    """
    Add a text string and its corresponding data to the global FAISS index.
    The text will be converted to an embedding vector automatically.
    
    Args:
        text: The text string to be embedded.
        data: The corresponding data object.
    """
    # 使用全局Embedding实例
    embedding_instance = get_embedding_instance()
    
    # 获取文本的embedding向量
    embedding_vector = embedding_instance.get_embedding(text)
    
    # 检查embedding是否成功
    if embedding_vector is None:
        logger.warning(f"Failed to create embedding for text: {text[:50]}...")
        return
    
    # 添加到索引
    index = get_faiss_index()
    index.add_embedding(embedding_vector, data)


def add_batch_to_faiss_index(texts: List[str], data: List[Any]) -> None:
    """
    Add a batch of text strings and their corresponding data to the global FAISS index.
    The texts will be converted to embedding vectors automatically.
    
    Args:
        texts: List of text strings to be embedded.
        data: List of corresponding data objects.
    """
    if not texts or len(texts) == 0:
        logger.warning("No texts provided to add to FAISS index")
        return
        
    # 使用全局Embedding实例
    embedding_instance = get_embedding_instance()
    
    # 批量获取embeddings
    embeddings = []
    valid_data = []
    
    for i, text in enumerate(texts):
        embedding_vector = embedding_instance.get_embedding(text)
        if embedding_vector is not None:
            embeddings.append(embedding_vector)
            valid_data.append(data[i])
        else:
            logger.warning(f"Failed to create embedding for text: {text[:50]}...")
    
    if not embeddings:
        logger.warning("No valid embeddings were created")
        return
        
    # 添加到索引
    index = get_faiss_index()
    index.add_embeddings(embeddings, valid_data)


def add_batch_embeddings_to_faiss_index(embeddings: List[List[float]], data: List[Any]) -> None:
    """
    Add a batch of pre-computed embeddings and their corresponding data to the global FAISS index.
    
    Args:
        embeddings: List of embedding vectors.
        data: List of corresponding data objects.
    """
    index = get_faiss_index()
    index.add_embeddings(embeddings, data)


def search_similar_text(query_text: str, k: int = 5) -> Tuple[List[int], List[float], List[Any]]:
    """
    Search for similar items in the global FAISS index using a text query.
    
    Args:
        query_text: The text to search for similar items.
        k: Number of similar items to retrieve.
        
    Returns:
        Tuple containing (indices, distances, data)
    """
    # 使用全局Embedding实例
    embedding_instance = get_embedding_instance()
    
    # 获取查询文本的embedding
    query_embedding = embedding_instance.get_embedding(query_text)
    
    if query_embedding is None:
        logger.warning(f"Failed to create embedding for query text: {query_text[:50]}...")
        return [], [], []
    
    # 使用embedding进行搜索
    return search_similar(query_embedding, k)


def search_similar(query_embedding: List[float], k: int = 5) -> Tuple[List[int], List[float], List[Any]]:
    """
    Search for similar items in the global FAISS index.
    
    Args:
        query_embedding: The query embedding vector.
        k: Number of similar items to retrieve.
        
    Returns:
        Tuple containing (indices, distances, data)
    """
    index = get_faiss_index()
    return index.search(query_embedding, k)

# 初始化全局Embedding实例
embedding_instance = get_embedding_instance()
faiss_index = get_faiss_index()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # 测试FAISS功能 - 使用中文示例
    print("\n===== 添加中文测试数据 =====")
    
    # 添加单条数据
    print("\n1. 添加单条数据:")
    add_to_faiss_index("人工智能", {"text": "人工智能", "id": 1, "category": "技术"})
    add_to_faiss_index("机器学习算法", {"text": "机器学习算法", "id": 2, "category": "技术"})
    add_to_faiss_index("深度学习模型", {"text": "深度学习模型", "id": 3, "category": "技术"})
    add_to_faiss_index("自然语言处理", {"text": "自然语言处理", "id": 4, "category": "技术"})
    add_to_faiss_index("计算机视觉", {"text": "计算机视觉", "id": 5, "category": "技术"})
    
    # 添加不同领域的数据
    add_to_faiss_index("中国历史文化", {"text": "中国历史文化", "id": 6, "category": "文化"})
    add_to_faiss_index("唐诗宋词", {"text": "唐诗宋词", "id": 7, "category": "文学"})
    add_to_faiss_index("现代文学作品", {"text": "现代文学作品", "id": 8, "category": "文学"})
    
    # 添加长文本
    add_to_faiss_index(
        "人工智能是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。",
        {"text": "人工智能定义", "id": 9, "category": "定义"}
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
        ]
    )
    
    # 获取索引大小
    index = get_faiss_index()
    print(f"FAISS索引中共有 {index.get_size()} 条数据")
    
    # 测试文本搜索 - 相似度查询
    print("\n===== 文本相似度搜索测试 =====")
    
    # 测试1: 技术相关查询
    print("\n1. 查询'机器学习技术'相似内容:")
    indices, distances, data = search_similar_text("机器学习技术", k=3)
    for i, (dist, item) in enumerate(zip(distances, data)):
        print(f"  结果 {i+1}: {item['text']} (ID: {item['id']}, 类别: {item.get('category', 'N/A')}, 距离: {dist})")
    
    # 测试2: 文学相关查询
    print("\n2. 查询'中国古典诗词'相似内容:")
    indices, distances, data = search_similar_text("中国古典诗词", k=3)
    for i, (dist, item) in enumerate(zip(distances, data)):
        print(f"  结果 {i+1}: {item['text']} (ID: {item['id']}, 类别: {item.get('category', 'N/A')}, 距离: {dist})")
    
    # 测试3: 长句查询
    print("\n3. 查询'神经网络如何在计算机视觉中应用'相似内容:")
    indices, distances, data = search_similar_text("神经网络如何在计算机视觉中应用", k=3)
    for i, (dist, item) in enumerate(zip(distances, data)):
        print(f"  结果 {i+1}: {item['text']} (ID: {item['id']}, 类别: {item.get('category', 'N/A')}, 距离: {dist})")
    
    # 测试4: 使用预先计算的embedding进行搜索
    print("\n4. 使用预先计算的embedding进行搜索:")
    query_text = "人工智能的发展趋势"
    query_embedding = get_embedding_instance().get_embedding(query_text)
    print(f"查询: '{query_text}'")
    indices, distances, data = search_similar(query_embedding, k=3)
    for i, (dist, item) in enumerate(zip(distances, data)):
        print(f"  结果 {i+1}: {item['text']} (ID: {item['id']}, 类别: {item.get('category', 'N/A')}, 距离: {dist})")
    
    print("\n===== FAISS测试完成 =====")
