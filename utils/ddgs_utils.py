import traceback
from typing import List

# Keep this module free of Streamlit/UI dependencies.
try:
    from ddgs import DDGS
    try:
        # Newer ddgs exposes a specific TimeoutException
        from ddgs.exceptions import TimeoutException  # type: ignore
    except Exception:
        TimeoutException = None  # type: ignore
except Exception as e:
    # Defer import errors to call time to allow apps to handle gracefully
    DDGS = None  # type: ignore
    TimeoutException = None  # type: ignore


def search_ddgs(query: str, search_type: str, max_results: int = 30) -> List[dict]:
    """
    Run DuckDuckGo Search (DDGS) for the given type.

    Args:
        query: Search query string.
        search_type: One of "text", "images", "videos", "news".
        max_results: Maximum number of results to fetch.

    Returns:
        A list of result dicts as returned by the ddgs library.

    Raises:
        RuntimeError: If ddgs is not installed or call fails.
    """
    if DDGS is None:
        raise RuntimeError("ddgs package is not available. Please install with: pip install ddgs")

    if not query:
        return []

    try:
        with DDGS() as ddgs:
            if search_type == "text":
                results = list(ddgs.text(query, max_results=max_results))
            elif search_type == "images":
                results = list(ddgs.images(query, max_results=max_results))
            elif search_type == "videos":
                results = list(ddgs.videos(query, max_results=max_results))
            elif search_type == "news":
                results = list(ddgs.news(query, max_results=max_results))
            else:
                raise ValueError(f"Unsupported search_type: {search_type}")
            
            # 返回结果，即使为空列表
            return results if results else []
            
    except Exception as e:
        # Gracefully handle explicit timeout without retries
        if TimeoutException is not None and isinstance(e, TimeoutException):
            return []
        
        # 处理常见的"无结果"情况，不抛出异常
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ['no results', 'ratelimit', 'blocked', '403', '429']):
            # 这些都是正常的"无结果"情况，返回空列表而不是抛异常
            return []
        
        # 其他真正的错误才抛出
        raise RuntimeError(f"DDGS search failed: {e}\n{traceback.format_exc()}")
