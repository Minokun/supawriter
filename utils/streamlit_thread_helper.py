"""
Helper module for thread-safe Streamlit operations.
This module provides utilities for updating Streamlit UI elements from background threads.
"""
import logging
import threading
from typing import Dict, Any, Callable

# Dictionary to store thread-local data
_thread_data: Dict[int, Dict[str, Any]] = {}
_thread_lock = threading.Lock()

logger = logging.getLogger(__name__)

def thread_safe_callback(callback_fn: Callable = None):
    """
    Decorator to make callbacks thread-safe for Streamlit.
    Instead of directly updating Streamlit elements, this stores the updates
    in thread-local storage that can be safely accessed from the main thread.
    
    Args:
        callback_fn: The original callback function
    
    Returns:
        A wrapped function that stores data instead of updating Streamlit directly
    """
    def wrapper(*args, **kwargs):
        # Get the thread ID
        thread_id = threading.get_ident()
        
        # Store the callback data in thread-local storage
        with _thread_lock:
            if thread_id not in _thread_data:
                _thread_data[thread_id] = {}
            
            # Store the callback arguments
            _thread_data[thread_id]['args'] = args
            _thread_data[thread_id]['kwargs'] = kwargs
            _thread_data[thread_id]['called'] = True
        
        # Call the original function if provided
        if callback_fn:
            return callback_fn(*args, **kwargs)
    
    return wrapper

def create_thread_safe_callback(task_state: dict, progress_key: str, text_key: str, 
                               start_percent: int, end_percent: int, 
                               log_prefix: str = "Progress"):
    """
    Creates a thread-safe progress callback function for use with ThreadPoolExecutor.
    
    Args:
        task_state: Dictionary to store task state
        progress_key: Key for progress percentage in task_state
        text_key: Key for progress text in task_state
        start_percent: Starting percentage for this task
        end_percent: Ending percentage for this task
        log_prefix: Prefix for log messages
        
    Returns:
        A thread-safe callback function
    """
    @thread_safe_callback
    def safe_progress_callback(completed, total):
        # Calculate progress within the specified range
        progress_percentage = start_percent + int((completed / total) * (end_percent - start_percent))
        
        # Update task state (this won't directly update Streamlit)
        task_state[progress_key] = progress_percentage
        task_state[text_key] = f"{log_prefix} ({completed}/{total})"
        
        # Log the progress (this is safe from any thread)
        logger.info(f"{log_prefix}: {completed}/{total}")
    
    return safe_progress_callback

def process_thread_updates():
    """
    Process any pending thread updates from the main Streamlit thread.
    Call this function periodically from your main Streamlit code.
    """
    with _thread_lock:
        # Make a copy of the thread data to avoid modification during iteration
        thread_data_copy = _thread_data.copy()
        # Clear the original data
        _thread_data.clear()
    
    # Process each thread's data
    for thread_id, data in thread_data_copy.items():
        if data.get('called', False):
            # Log that we're processing an update from a background thread
            logger.debug(f"Processing update from thread {thread_id}")
            # The actual processing would happen here in the main thread
            # This is where you'd update Streamlit UI elements if needed
