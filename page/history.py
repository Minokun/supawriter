import streamlit as st
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import load_user_history
from settings import ARTICLE_TRANSFORMATIONS, HISTORY_FILTER_BASE_OPTIONS

@require_auth
def main():
    st.title("历史记录")
    
    # Get current user
    current_user = get_current_user()
    if not current_user:
        st.error("无法获取当前用户信息")
        return
    
    # Load user history
    history = load_user_history(current_user)
    
    if not history:
        st.info("暂无历史记录")
        return

    # Dynamically create history filter options
    transformation_type_names = list(ARTICLE_TRANSFORMATIONS.keys())
    # Ensure '转换后的文章' is not duplicated if it's a specific transformation type name
    # For now, we assume transformation names are distinct from '完成文章' or '所有文章'
    # A more robust approach might be to have '转换后的文章' as a category, then sub-filter by type
    # But for now, we list all transformation types as top-level filters after base options.
    dynamic_filter_options = HISTORY_FILTER_BASE_OPTIONS + transformation_type_names

    history_filter = st.radio(
        "选择查看的文章类型:", 
        dynamic_filter_options, 
        horizontal=True,
        key='history_filter_type'
    )
    
    # Filter history based on selection
    filtered_history = []
    if history_filter == "所有文章":
        filtered_history = history
    elif history_filter == "完成文章":
        filtered_history = [r for r in history if not r.get('is_transformed', False)]
    elif history_filter in transformation_type_names: # Check if it's one of the transformation types
        # Filter for transformed articles that match the selected transformation type by checking the topic suffix
        filtered_history = [r for r in history if r.get('is_transformed', False) and r.get('topic', '').endswith(f" ({history_filter})")]
    else: # Should not happen with current setup, but as a fallback
        filtered_history = history

    if not filtered_history:
        st.info(f"暂无 {history_filter} 类型的历史记录")
        return

    # Display history in reverse chronological order (newest first)
    for record in reversed(filtered_history):
        with st.expander(f"📝 {record['topic']} - {record['timestamp'][:16].replace('T', ' ')}"):
            # 展示配置信息
            st.markdown(f"**模型供应商**: {record.get('model_type', '-')}")
            st.markdown(f"**模型名称**: {record.get('model_name', '-')}")
            st.markdown(f"**写作模式**: {record.get('write_type', '-')}")
            st.markdown(f"**爬取数量**: {record.get('spider_num', '-')}")
            st.markdown(f"**文章摘要**: {record.get('summary', '-')}")
            if record.get('is_transformed') and record.get('original_article_id') is not None:
                st.markdown(f"**源文章ID**: {record.get('original_article_id')}")
            st.markdown("### 文章内容")
            st.markdown(record["article_content"])
            # 下载按钮
            st.download_button(
                label="下载文章",
                data=record["article_content"],
                file_name=f"{record['topic']}.md",
                mime="text/markdown",
                key=f"download_{record['id']}"
            )
            # 删除按钮
            if st.button("删除此条记录", key=f"delete_{record['id']}"):
                from utils.history_utils import delete_history_record
                delete_history_record(current_user, record['id'])
                st.rerun()

# Call the main function
main()
