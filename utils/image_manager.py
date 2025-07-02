import os
import json
import re
import logging
from utils.gemma3_client import call_gemma3_api
from utils.embedding_utils import search_similar_text, add_to_faiss_index, get_embedding_instance
from utils.image_url_mapper import ImageUrlMapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageManager:
    def __init__(self, image_base_dir="images", task_id=None):
        """
        Initialize the ImageManager
        
        Args:
            image_base_dir: Base directory for images
            task_id: Specific task ID folder to scan (e.g., 'task_191976')
        """
        self.image_base_dir = image_base_dir
        self.task_id = task_id
        self.embedding_instance = get_embedding_instance()
        self.url_mapper = ImageUrlMapper(image_base_dir)
        
    def _get_image_dirs(self):
        """Get image directories to scan based on task_id"""
        if not os.path.exists(self.image_base_dir):
            os.makedirs(self.image_base_dir)
            
        if self.task_id:
            # If task_id is provided, only scan that specific directory
            task_dir = os.path.join(self.image_base_dir, self.task_id)
            return [task_dir] if os.path.isdir(task_dir) else []
        else:
            # Otherwise scan all task directories
            return [os.path.join(self.image_base_dir, d) for d in os.listdir(self.image_base_dir) 
                    if os.path.isdir(os.path.join(self.image_base_dir, d))]
    
    def analyze_images(self, article_theme, max_images=10):
        """
        Analyze images and get their descriptions
        
        Args:
            article_theme: Theme of the article for relevance checking
            max_images: Maximum number of images to analyze
            
        Returns:
            List of analyzed image info dictionaries
        """
        analyzed_images = []
        
        # Enhanced prompt for image analysis
        image_analysis_prompt = f"""
        查看图片并进行详细分析。如果是广告图片、图标或不包含实质内容的图片，请标记为已删除。
        对于其他图片，请用中文详细描述图片内容，并判断它与主题"{article_theme}"的相关性。
        
        输出格式为JSON:
        {{
            "is_deleted": true/false,
            "describe": "详细的图片描述",
            "is_related": true/false
        }}
        """
        
        # Get image directories to scan
        image_dirs = self._get_image_dirs()
        if not image_dirs:
            logger.warning(f"No image directories found in {self.image_base_dir}")
            return []
            
        # For each image directory
        for dir_path in image_dirs:
            if not os.path.exists(dir_path):
                continue
                
            logger.info(f"Scanning images in {dir_path}")
            
            # For each image in directory
            for img_file in os.listdir(dir_path):
                if not img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue
                    
                img_path = os.path.join(dir_path, img_file)
                logger.info(f"Analyzing image: {img_path}")
                
                # Use gemmar3 to analyze image
                try:
                    result = call_gemma3_api(image_analysis_prompt, img_path)
                    
                    if result and "choices" in result:
                        content = result["choices"][0]["message"]["content"]
                        # Extract JSON from the content
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            analysis = json.loads(json_match.group(0))
                            
                            if not analysis.get("is_deleted", True):
                                analyzed_images.append({
                                    "path": img_path,
                                    "description": analysis.get("describe", ""),
                                    "is_related": analysis.get("is_related", False)
                                })
                                logger.info(f"Image analyzed: {img_file} - Related: {analysis.get('is_related', False)}")
                                
                                # If we have enough images, stop analyzing
                                if len(analyzed_images) >= max_images:
                                    break
                except Exception as e:
                    logger.error(f"Error analyzing image {img_path}: {str(e)}")
        
        logger.info(f"Total analyzed images: {len(analyzed_images)}")
        return analyzed_images
    
    def split_article_into_paragraphs(self, markdown_content):
        """
        Split article into meaningful paragraphs
        
        Args:
            markdown_content: Article content in markdown format
            
        Returns:
            List of paragraph strings
        """
        # Remove code blocks first to avoid splitting within them
        code_blocks = []
        def replace_code_block(match):
            code_blocks.append(match.group(0))
            return f"CODE_BLOCK_{len(code_blocks)-1}"
        
        content_without_code = re.sub(r'```.*?```', replace_code_block, markdown_content, flags=re.DOTALL)
        
        # Split by double newlines, but keep headers with their paragraphs
        raw_paragraphs = re.split(r'\n\s*\n', content_without_code)
        
        # Process paragraphs to group headers with their content
        paragraphs = []
        current_paragraph = ""
        
        for p in raw_paragraphs:
            p = p.strip()
            if not p:
                continue
                
            # If it's a header, start a new paragraph
            if p.startswith('#'):
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                current_paragraph = p
            else:
                # If we have a current paragraph, append to it
                if current_paragraph:
                    current_paragraph += "\n\n" + p
                else:
                    current_paragraph = p
                    
        # Add the last paragraph if it exists
        if current_paragraph:
            paragraphs.append(current_paragraph)
            
        # Restore code blocks
        for i, paragraph in enumerate(paragraphs):
            for j, code_block in enumerate(code_blocks):
                paragraphs[i] = paragraphs[i].replace(f"CODE_BLOCK_{j}", code_block)
                
        return paragraphs
    
    def match_images_to_paragraphs(self, paragraphs, analyzed_images, similarity_threshold=0.5):
        """
        Match images to paragraphs based on semantic similarity
        
        Args:
            paragraphs: List of article paragraphs
            analyzed_images: List of analyzed image dictionaries
            similarity_threshold: Minimum similarity score (0-1) for an image to be considered relevant
            
        Returns:
            List of tuples (paragraph_index, image_info, similarity_score)
        """
        if not analyzed_images or not paragraphs:
            return []
            
        # Filter to only related images
        related_images = [img for img in analyzed_images if img.get("is_related", False)]
        if not related_images:
            logger.info("No related images found")
            return []
            
        # Get image descriptions and paragraph texts
        image_descriptions = [img["description"] for img in related_images]
        
        logger.info(f"Matching {len(image_descriptions)} images to {len(paragraphs)} paragraphs")
        
        # Find best matching paragraph for each image using embedding-based similarity
        results = []
        
        # 使用全局FAISS索引
        from utils.embedding_utils import get_faiss_index
        faiss_index = get_faiss_index()
        
        # 检查索引是否为空
        if faiss_index.get_size() == 0:
            logger.warning("FAISS索引为空，无法匹配图片")
            return []
        
        # 为段落创建嵌入向量
        embedding_instance = self.embedding_instance
        paragraph_data = []
        paragraph_embeddings = []
        
        for i, paragraph in enumerate(paragraphs):
            try:
                # 获取段落的嵌入向量
                paragraph_embedding = embedding_instance.get_embedding(paragraph)
                if paragraph_embedding is not None:
                    paragraph_embeddings.append(paragraph_embedding)
                    paragraph_data.append({'id': i, 'text': paragraph})
            except Exception as e:
                logger.error(f"Error embedding paragraph {i}: {str(e)}")
        
        if not paragraph_embeddings:
            logger.warning("No paragraph embeddings were created, cannot match images to paragraphs")
            return []
        
        # 对每个段落，在FAISS索引中搜索相似的图片
        for para_idx, (para_embedding, para_data) in enumerate(zip(paragraph_embeddings, paragraph_data)):
            try:
                # 在FAISS索引中搜索相似的图片描述
                indices, distances, matched_data = faiss_index.search(para_embedding, k=3)
                
                if matched_data and len(matched_data) > 0:
                    for i, (distance, data) in enumerate(zip(distances, matched_data)):
                        # 检查是否是图片数据
                        if 'image_url' in data and 'description' in data:
                            # 转换距离为相似度分数
                            similarity = 1.0 - min(distance / 2.0, 0.99)  # 归一化并反转
                            
                            # 只包含超过相似度阈值的匹配
                            if similarity >= similarity_threshold:
                                # 创建图片信息对象
                                image_info = {
                                    'path': data['image_url'],
                                    'description': data['description'],
                                    'is_related': data.get('is_related', True),
                                    'task_id': data.get('task_id', '')
                                }
                                
                                results.append((
                                    para_data['id'],
                                    image_info,
                                    similarity
                                ))
                                logger.info(f"Matched image to paragraph {para_data['id']} with score {similarity:.4f}")
                            else:
                                logger.info(f"Image match below threshold: {similarity:.4f} < {similarity_threshold}")
            except Exception as e:
                logger.error(f"Error searching for images for paragraph {para_idx}: {str(e)}")
                continue
        
        # 按相似度分数排序
        results.sort(key=lambda x: x[2], reverse=True)
        
        return results
    
    def insert_images_into_article(self, markdown_content, similarity_threshold=0.5, max_images=10, article_theme=""):
        """
        Main function to analyze and insert images into an article
        
        Args:
            markdown_content: Article content in markdown format
            similarity_threshold: Minimum similarity score (0-1) for an image to be considered relevant
            max_images: Maximum number of images to analyze (not necessarily insert)
            article_theme: Theme of the article for relevance checking
            
        Returns:
            Enhanced markdown content with images inserted
        """
        logger.info(f"Starting image insertion process for theme: {article_theme}")
        
        # 首先检查全局FAISS索引中是否有图片数据
        from utils.embedding_utils import get_faiss_index
        faiss_index = get_faiss_index()
        index_size = faiss_index.get_size()
        logger.info(f"当前FAISS索引大小: {index_size}")
        
        if index_size == 0:
            logger.warning("FAISS索引中没有图片数据，无法进行图片匹配")
            return markdown_content
        
        # Step 1: 如果有图片数据，继续分析图片
        analyzed_images = self.analyze_images(article_theme, max_images=max_images)
        
        if not analyzed_images:
            logger.info("No images found or analyzed")
            return markdown_content
            
        # Step 2: Split article into paragraphs
        paragraphs = self.split_article_into_paragraphs(markdown_content)
        
        # Step 3: Match images to paragraphs using similarity threshold
        image_paragraph_matches = self.match_images_to_paragraphs(
            paragraphs, 
            analyzed_images,
            similarity_threshold=similarity_threshold
        )
        
        # Step 4: Insert images before their matching paragraphs
        if not image_paragraph_matches:
            logger.info("No suitable image-paragraph matches found")
            return markdown_content
            
        # Sort by paragraph index to maintain document order
        image_paragraph_matches.sort(key=lambda x: x[0])
        
        # Insert images
        for offset, (paragraph_idx, image_info, similarity) in enumerate(image_paragraph_matches):
            # Adjust index for previously inserted images
            adjusted_idx = paragraph_idx + offset
            
            # Get image path and try to get the original URL
            img_path = image_info['path']
            original_url = self.url_mapper.get_url_for_image(img_path)
            
            if original_url:
                # Use the original URL if available
                logger.info(f"Using original URL for image: {original_url}")
                img_url = original_url
            else:
                # Fall back to local path with proper handling
                logger.warning(f"No URL mapping found for {img_path}, using local path")
                
                # Convert absolute path to relative path for better markdown compatibility
                try:
                    # Get project root directory
                    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                    
                    # Convert to relative path if the image is within the project
                    if img_path.startswith(project_root):
                        img_path = os.path.relpath(img_path, project_root)
                    
                    # Ensure forward slashes for web compatibility
                    img_path = img_path.replace('\\', '/')
                    
                    # Add leading slash if not present (for web server root-relative paths)
                    if not img_path.startswith('/'):
                        img_path = '/' + img_path
                except Exception as e:
                    logger.warning(f"Could not convert image path to relative: {e}")
                
                img_url = img_path
            
            # Create markdown with image description and URL
            img_markdown = f"\n\n![{image_info['description']}]({img_url})\n"
            
            # Insert before the paragraph
            if adjusted_idx < len(paragraphs):
                paragraphs.insert(adjusted_idx, img_markdown)
                logger.info(f"Inserted image before paragraph {paragraph_idx}")
        
        # Join paragraphs back together
        enhanced_content = "\n\n".join(paragraphs)
        logger.info("Image insertion complete")
        return enhanced_content
