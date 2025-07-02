import os
import json
import uuid
from datetime import datetime
import streamlit as st

# Path to the history database file
HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'history')

# Path to the user HTML files
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

# Ensure the history directory exists
os.makedirs(HISTORY_DIR, exist_ok=True)

def get_user_history_file(username):
    """Get the path to the user's history file."""
    return os.path.join(HISTORY_DIR, f"{username}_history.json")

def load_user_history(username):
    """Load user history from the history file."""
    history_file = get_user_history_file(username)
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # If file is corrupted, return empty history
            return []
    return []

def save_user_history(username, history):
    """Save user history to the history file."""
    history_file = get_user_history_file(username)
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def add_history_record(username, topic, article_content, summary=None, model_type=None, model_name=None, write_type=None, spider_num=None, custom_style=None, is_transformed=False, original_article_id=None, image_task_id=None, image_enabled=False, image_similarity_threshold=None, image_max_count=None):
    """
    Add a new record to the user's history, with configurable parameters.
    
    Args:
        username: The username of the user
        topic: The topic of the article
        article_content: The content of the article
        summary: Optional summary of the article
        model_type: The type of model used
        model_name: The name of the model used
        write_type: The type of writing (simple, detailed)
        spider_num: The number of websites crawled
        custom_style: Custom writing style
        is_transformed: Whether this is a transformed article
        original_article_id: ID of the original article if this is transformed
        image_task_id: The task ID for images used in the article
        image_enabled: Whether images were enabled for this article
        image_similarity_threshold: The similarity threshold used for image matching
        image_max_count: The maximum number of images to analyze
    """
    history = load_user_history(username)
    # 生成唯一ID（避免删除后ID重复）
    record_id = max([r.get("id", 0) for r in history], default=0) + 1
    record = {
        "id": record_id,
        "topic": topic,
        "timestamp": datetime.now().isoformat(),
        "article_content": article_content,
        "model_type": model_type,
        "model_name": model_name,
        "write_type": write_type,
        "spider_num": spider_num,
        "custom_style": custom_style,
        "summary": summary,
        "is_transformed": is_transformed,
        "original_article_id": original_article_id,
        "image_task_id": image_task_id,
        "image_enabled": image_enabled,
        "image_similarity_threshold": image_similarity_threshold,
        "image_max_count": image_max_count
    }
    history.append(record)
    save_user_history(username, history)
    return record

def delete_history_record(username, record_id):
    """
    Delete a history record by id for the user.
    """
    history = load_user_history(username)
    new_history = [r for r in history if r.get("id") != record_id]
    save_user_history(username, new_history)
    return True

def save_html_to_user_dir(username, html_content, filename=None):
    """
    Save HTML content to the user's HTML directory.
    
    Args:
        username (str): The username of the user
        html_content (str): The HTML content to save
        filename (str, optional): Filename to use. If None, a UUID will be generated
        
    Returns:
        tuple: (file_path, url_path) - The file path and URL path to access the HTML
    """
    # Create user HTML directory if it doesn't exist
    user_html_dir = os.path.join(DATA_DIR, 'html', username)
    os.makedirs(user_html_dir, exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        filename = f"{uuid.uuid4().hex}.html"
    elif not filename.endswith('.html'):
        filename = f"{filename}.html"
    
    # Full path to save the file
    file_path = os.path.join(user_html_dir, filename)
    
    # Save the HTML content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # URL path for nginx to serve
    url_path = f"{username}/{filename}"
    
    return file_path, url_path

def save_image_to_user_dir(username, image_data, filename=None):
    """
    Save image data to the user's HTML directory.
    
    Args:
        username (str): The username of the user
        image_data (bytes): The image data to save
        filename (str, optional): Filename to use. If None, a UUID will be generated
        
    Returns:
        tuple: (file_path, url_path) - The file path and URL path to access the image
    """
    # Create user HTML directory if it doesn't exist
    user_html_dir = os.path.join(DATA_DIR, 'html', username)
    os.makedirs(user_html_dir, exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        filename = f"{uuid.uuid4().hex}.png"
    elif not filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
        filename = f"{filename}.png"
    
    # Full path to save the file
    file_path = os.path.join(user_html_dir, filename)
    
    # Save the image data
    with open(file_path, 'wb') as f:
        f.write(image_data)
    
    # URL path for nginx to serve
    url_path = f"/html/{username}/{filename}"
    
    return file_path, url_path

