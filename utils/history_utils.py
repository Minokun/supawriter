import os
import json
import uuid
import logging
from datetime import datetime
import streamlit as st

# Helper to sanitize filenames to avoid path traversal and illegal characters
def sanitize_filename(name: str, replacement: str = '_', max_length: int = 200) -> str:
    """
    Sanitize a filename by removing path separators and illegal characters.
    Keeps unicode characters, but replaces characters invalid on common filesystems.
    Ensures the final length is within max_length.
    """
    if not name:
        return uuid.uuid4().hex

    # Replace OS-specific path separators
    name = name.replace(os.sep, replacement)
    if os.altsep:
        name = name.replace(os.altsep, replacement)

    # Replace characters generally invalid in filenames and problematic in URLs
    # Include URL-reserved characters to avoid web server issues (e.g., '%', '#', '&', '+')
    invalid_chars = '<>:"/\\|?*#%&+\n\r\t'
    name = ''.join((c if (c not in invalid_chars and ord(c) >= 32) else replacement) for c in name)

    # Normalize repeated replacements
    while replacement*2 in name:
        name = name.replace(replacement*2, replacement)

    # Trim leading/trailing spaces and dots
    name = name.strip().strip('.')

    # Enforce max length while keeping extension if present
    if len(name) > max_length:
        base, ext = os.path.splitext(name)
        # Limit extremely long extensions defensively
        ext = ext[:10]
        keep = max(1, max_length - len(ext))
        name = base[:keep] + ext

    # Fallback if becomes empty
    if not name:
        name = uuid.uuid4().hex

    return name

# Path to the history database file
HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'history')

# Path to the user HTML files
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

# Path to the chat history directory
CHAT_HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'chat_history')

# Ensure the directories exist
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

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

def add_history_record(username, topic, article_content, summary=None, model_type=None, model_name=None, write_type=None, spider_num=None, custom_style=None, is_transformed=False, original_article_id=None, image_task_id=None, image_enabled=False, image_similarity_threshold=None, image_max_count=None, tags=None, article_topic=None):
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
        tags: Tags from the article outline
        article_topic: Original topic entered by user for article generation
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
        "image_max_count": image_max_count,
        "tags": tags,
        "article_topic": article_topic
    }
    history.append(record)
    save_user_history(username, history)
    return record

def delete_history_record(username, record_id):
    """
    Delete a history record by id for the user.
    """
    history = load_user_history(username)
    # Find the record to delete (to derive related file paths)
    record_to_delete = None
    for r in history:
        if r.get("id") == record_id:
            record_to_delete = r
            break

    # Build user html dir path
    user_html_dir = os.path.join(DATA_DIR, 'html', username)

    # Attempt to delete related local files if present
    if record_to_delete is not None:
        try:
            topic = record_to_delete.get('topic', 'article')
            # Keep filename generation consistent with page/history.py
            base_name = f"{topic.replace(' ', '_')}_{record_to_delete.get('id')}"

            # HTML file
            html_filename = sanitize_filename(f"{base_name}.html")
            html_path = os.path.join(user_html_dir, html_filename)
            if os.path.exists(html_path):
                try:
                    os.remove(html_path)
                    logging.info(f"Removed history HTML file: {html_path}")
                except Exception as e:
                    logging.error(f"Error removing history HTML file {html_path}: {e}")

            # Screenshot file (if any)
            screenshot_filename = sanitize_filename(f"{base_name}_screenshot.png")
            screenshot_path = os.path.join(user_html_dir, screenshot_filename)
            if os.path.exists(screenshot_path):
                try:
                    os.remove(screenshot_path)
                    logging.info(f"Removed history screenshot file: {screenshot_path}")
                except Exception as e:
                    logging.error(f"Error removing history screenshot file {screenshot_path}: {e}")
        except Exception as e:
            logging.error(f"Error during cleanup of files for record {record_id}: {e}")

    # Persist filtered history list
    new_history = [r for r in history if r.get("id") != record_id]
    save_user_history(username, new_history)
    return True

def save_html_to_user_dir(username, html_content, filename=None):
    """
    Save HTML content to the user's HTML directory.
    If a file with the same name already exists, it will be overwritten.
    
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

    # Sanitize filename to avoid illegal characters and separators
    filename = sanitize_filename(filename)
    
    # Full path to save the file
    file_path = os.path.join(user_html_dir, filename)
    
    # Check if file already exists and remove it
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logging.info(f"Removed existing file: {file_path}")
        except Exception as e:
            logging.error(f"Error removing existing file {file_path}: {str(e)}")
    
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

    # Sanitize filename
    filename = sanitize_filename(filename)
    
    # Full path to save the file
    file_path = os.path.join(user_html_dir, filename)
    
    # Save the image data
    with open(file_path, 'wb') as f:
        f.write(image_data)
    
    # URL path for nginx to serve
    url_path = f"{username}/{filename}"
    
    return file_path, url_path

# ================ Chat History Functions ================

def get_user_chat_history_dir(username):
    """
    Get the directory path for a user's chat history.
    
    Args:
        username (str): The username of the user
        
    Returns:
        str: Path to the user's chat history directory
    """
    user_chat_dir = os.path.join(CHAT_HISTORY_DIR, username)
    os.makedirs(user_chat_dir, exist_ok=True)
    return user_chat_dir

def list_chat_sessions(username):
    """
    List all chat sessions for a user.
    
    Args:
        username (str): The username of the user
        
    Returns:
        list: List of chat session metadata dictionaries
    """
    user_chat_dir = get_user_chat_history_dir(username)
    sessions = []
    
    # Get all JSON files in the user's chat directory
    for filename in os.listdir(user_chat_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(user_chat_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                    # Extract metadata from the chat data
                    session_id = os.path.splitext(filename)[0]
                    title = chat_data.get('title', 'Untitled Chat')
                    created_at = chat_data.get('created_at', '')
                    updated_at = chat_data.get('updated_at', '')
                    message_count = len(chat_data.get('messages', []))
                    
                    sessions.append({
                        'id': session_id,
                        'title': title,
                        'created_at': created_at,
                        'updated_at': updated_at,
                        'message_count': message_count
                    })
            except Exception as e:
                print(f"Error loading chat session {filename}: {str(e)}")
    
    # Sort sessions by updated_at (most recent first)
    sessions.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    return sessions

def create_chat_session(username, title=None):
    """
    Create a new chat session for a user.
    
    Args:
        username (str): The username of the user
        title (str, optional): Title for the chat session
        
    Returns:
        dict: The newly created chat session data
    """
    user_chat_dir = get_user_chat_history_dir(username)
    
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    # Create initial chat data
    timestamp = datetime.now().isoformat()
    chat_data = {
        'title': title or 'New Chat',
        'created_at': timestamp,
        'updated_at': timestamp,
        'messages': []
    }
    
    # Save the chat data
    file_path = os.path.join(user_chat_dir, f"{session_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)
    
    return {'id': session_id, **chat_data}

def load_chat_session(username, session_id):
    """
    Load a chat session for a user.
    
    Args:
        username (str): The username of the user
        session_id (str): ID of the chat session to load
        
    Returns:
        dict: The chat session data or None if not found
    """
    user_chat_dir = get_user_chat_history_dir(username)
    file_path = os.path.join(user_chat_dir, f"{session_id}.json")
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                chat_data = json.load(f)
                return {'id': session_id, **chat_data}
        except Exception as e:
            print(f"Error loading chat session {session_id}: {str(e)}")
    
    return None

def save_chat_session(username, session_id, messages, title=None):
    """
    Save or update a chat session for a user.
    
    Args:
        username (str): The username of the user
        session_id (str): ID of the chat session to save
        messages (list): List of message dictionaries
        title (str, optional): Title for the chat session
        
    Returns:
        dict: The updated chat session data
    """
    user_chat_dir = get_user_chat_history_dir(username)
    file_path = os.path.join(user_chat_dir, f"{session_id}.json")
    
    # Check if the session exists
    existing_data = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except Exception:
            pass
    
    # Update the chat data
    timestamp = datetime.now().isoformat()
    chat_data = {
        'title': title or existing_data.get('title', 'New Chat'),
        'created_at': existing_data.get('created_at', timestamp),
        'updated_at': timestamp,
        'messages': messages
    }
    
    # Save the updated chat data
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)
    
    return {'id': session_id, **chat_data}

def update_chat_title(username, session_id, title):
    """
    Update the title of a chat session.
    
    Args:
        username (str): The username of the user
        session_id (str): ID of the chat session
        title (str): New title for the chat session
        
    Returns:
        bool: True if successful, False otherwise
    """
    user_chat_dir = get_user_chat_history_dir(username)
    file_path = os.path.join(user_chat_dir, f"{session_id}.json")
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                chat_data = json.load(f)
            
            chat_data['title'] = title
            chat_data['updated_at'] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Error updating chat title for {session_id}: {str(e)}")
    
    return False

def delete_chat_session(username, session_id):
    """
    Delete a chat session for a user.
    
    Args:
        username (str): The username of the user
        session_id (str): ID of the chat session to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    user_chat_dir = get_user_chat_history_dir(username)
    file_path = os.path.join(user_chat_dir, f"{session_id}.json")
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting chat session {session_id}: {str(e)}")
    
    return False

