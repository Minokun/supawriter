import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageUrlMapper:
    """
    Manages mappings between local image paths and their original URLs
    """
    
    def __init__(self, image_base_dir="images"):
        """
        Initialize the mapper with the base image directory
        
        Args:
            image_base_dir: Base directory for images
        """
        self.image_base_dir = image_base_dir
        
    def _get_mapping_file_path(self, task_id):
        """
        Get the path to the URL mapping file for a specific task
        
        Args:
            task_id: Task ID (e.g., 'task_191976')
            
        Returns:
            Path to the mapping file
        """
        task_dir = os.path.join(self.image_base_dir, task_id)
        return os.path.join(task_dir, "image_url_mapping.json")
        
    def save_url_mapping(self, task_id, filename, original_url):
        """
        Save a mapping between a local image filename and its original URL
        
        Args:
            task_id: Task ID (e.g., 'task_191976')
            filename: Local image filename (without path)
            original_url: Original URL of the image
            
        Returns:
            True if successful, False otherwise
        """
        mapping_file = self._get_mapping_file_path(task_id)
        
        # Create mapping dictionary
        mappings = {}
        
        # Load existing mappings if file exists
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mappings = json.load(f)
            except Exception as e:
                logger.error(f"Error loading mapping file: {e}")
                return False
        
        # Add or update mapping
        mappings[filename] = original_url
        
        # Save mappings
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(mapping_file), exist_ok=True)
            
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved URL mapping for {filename} in {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving mapping file: {e}")
            return False
            
    def get_url_for_image(self, image_path):
        """
        Get the original URL for a local image path
        
        Args:
            image_path: Full path to local image
            
        Returns:
            Original URL if found, None otherwise
        """
        # Extract task_id and filename from path
        try:
            # Path format: .../images/task_XXX/filename.jpg
            parts = image_path.split(os.sep)
            
            # Find the index of 'images' in the path
            if 'images' in parts:
                images_index = parts.index('images')
                if images_index + 2 < len(parts):  # Ensure we have task_id and filename
                    task_id = parts[images_index + 1]
                    filename = parts[images_index + 2]
                    
                    # Load mappings
                    mapping_file = self._get_mapping_file_path(task_id)
                    if os.path.exists(mapping_file):
                        with open(mapping_file, 'r', encoding='utf-8') as f:
                            mappings = json.load(f)
                            
                        # Return URL if found
                        if filename in mappings:
                            return mappings[filename]
        except Exception as e:
            logger.error(f"Error getting URL for image {image_path}: {e}")
            
        return None
        
    def batch_save_url_mappings(self, task_id, mappings):
        """
        Save multiple URL mappings at once
        
        Args:
            task_id: Task ID (e.g., 'task_191976')
            mappings: Dictionary of {filename: url} mappings
            
        Returns:
            True if successful, False otherwise
        """
        mapping_file = self._get_mapping_file_path(task_id)
        
        # Load existing mappings if file exists
        existing_mappings = {}
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    existing_mappings = json.load(f)
            except Exception as e:
                logger.error(f"Error loading mapping file: {e}")
                return False
        
        # Update mappings
        existing_mappings.update(mappings)
        
        # Save mappings
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(mapping_file), exist_ok=True)
            
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(existing_mappings, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(mappings)} URL mappings in {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving mapping file: {e}")
            return False
