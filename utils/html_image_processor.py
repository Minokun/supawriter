import os
import logging
import re
from bs4 import BeautifulSoup
from utils.image_url_mapper import ImageUrlMapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def replace_local_image_paths_with_urls(html_content, task_id=None):
    """
    Replace local image paths in HTML content with their original URLs
    
    Args:
        html_content (str): HTML content with local image paths
        task_id (str, optional): Task ID for image mapping lookup
        
    Returns:
        str: HTML content with original image URLs
    """
    if not html_content:
        return html_content
        
    # Create BeautifulSoup object
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Initialize image URL mapper
    url_mapper = ImageUrlMapper()
    
    # Find all img tags
    img_tags = soup.find_all('img')
    
    # Count of replacements made
    replacements_made = 0
    
    for img in img_tags:
        src = img.get('src', '')
        
        # Check if this is a local path
        if src and (src.startswith('/') or 
                    src.startswith('./') or 
                    'images/' in src or 
                    '\\images\\' in src):
            
            # Try to normalize the path
            try:
                # Convert to absolute path if it's relative
                if not os.path.isabs(src):
                    # Get the base directory of the project
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    abs_path = os.path.normpath(os.path.join(base_dir, src))
                else:
                    abs_path = src
                
                # Get original URL from the mapper
                original_url = url_mapper.get_url_for_image(abs_path)
                
                if original_url:
                    # Replace the src attribute with the original URL
                    img['src'] = original_url
                    replacements_made += 1
                    logger.info(f"Replaced local path '{src}' with original URL '{original_url}'")
                else:
                    logger.warning(f"Could not find original URL for image: {src}")
            except Exception as e:
                logger.error(f"Error processing image path {src}: {e}")
    
    logger.info(f"Replaced {replacements_made} local image paths with original URLs")
    
    # Return the modified HTML
    return str(soup)
