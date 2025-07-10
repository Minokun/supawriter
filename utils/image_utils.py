"""
Image utilities for downloading and managing images.
"""

import os
import requests
import logging
import uuid
from pathlib import Path
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_image(image_url, save_dir, filename=None):
    """
    Download an image from a URL and save it to the specified directory.
    
    Args:
        image_url (str): URL of the image to download
        save_dir (str): Directory to save the image to
        filename (str, optional): Filename to save the image as. If None, a UUID will be generated.
        
    Returns:
        str or None: Path to the saved image if successful, None otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            # Extract file extension from URL
            parsed_url = urlparse(image_url)
            path = parsed_url.path
            ext = os.path.splitext(path)[1]
            if not ext or ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                ext = '.jpg'  # Default to .jpg if no valid extension found
            
            # Generate a UUID for the filename
            filename = f"{uuid.uuid4()}{ext}"
        
        # Full path to save the image
        save_path = os.path.join(save_dir, filename)
        
        # Download the image
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Save the image
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Successfully downloaded image from {image_url} to {save_path}")
        return save_path
    
    except Exception as e:
        logger.error(f"Error downloading image from {image_url}: {str(e)}")
        return None

def get_image_save_directory(article_title):
    """
    Get the directory path for saving images for a specific article.
    
    Args:
        article_title (str): Title of the article
        
    Returns:
        str: Path to the directory for saving images
    """
    # Clean the article title to make it suitable for a directory name
    clean_title = "".join(c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in article_title)
    clean_title = clean_title.strip().replace(' ', '_')
    
    # Base directory for images
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images')
    
    # Article-specific directory
    article_dir = os.path.join(base_dir, clean_title)
    
    return article_dir
