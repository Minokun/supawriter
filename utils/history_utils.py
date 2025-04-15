import os
import json
from datetime import datetime
import streamlit as st

# Path to the history database file
HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'history')

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

def add_history_record(username, topic, article_content, model_type=None, model_name=None, write_type=None, spider_num=None):
    """
    Add a new record to the user's history, with configurable parameters.
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
        "spider_num": spider_num
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

