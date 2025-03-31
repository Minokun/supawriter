import functools
import streamlit as st
from utils.auth import is_authenticated

def require_auth(func):
    """
    装饰器：要求用户登录才能访问页面
    如果用户未登录，将显示错误消息并返回False
    注意：此装饰器不会阻止st.set_page_config()的执行
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Allow the function to run first to handle st.set_page_config()
        result = func(*args, **kwargs)
        
        # Then check authentication
        if not is_authenticated():
            st.error("请先登录后再访问此页面")
            st.stop()
            
        return result
    return wrapper
