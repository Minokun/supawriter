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
                return list(ddgs.text(query, max_results=max_results))
            elif search_type == "images":
                return list(ddgs.images(query, max_results=max_results))
            elif search_type == "videos":
                return list(ddgs.videos(query, max_results=max_results))
            elif search_type == "news":
                return list(ddgs.news(query, max_results=max_results))
            else:
                raise ValueError(f"Unsupported search_type: {search_type}")
    except Exception as e:
        # Gracefully handle explicit timeout without retries
        if TimeoutException is not None and isinstance(e, TimeoutException):
            return []
        # Let caller decide how to display other errors
        raise RuntimeError(f"DDGS search failed: {e}\n{traceback.format_exc()}")
