import streamlit as st
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import load_user_history

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
    
    # Display history in reverse chronological order (newest first)
    for record in reversed(history):
        with st.expander(f"📝 {record['topic']} - {record['timestamp'][:16].replace('T', ' ')}"):
            # 展示配置信息
            st.markdown(f"**模型供应商**: {record.get('model_type', '-')}")
            st.markdown(f"**模型名称**: {record.get('model_name', '-')}")
            st.markdown(f"**写作模式**: {record.get('write_type', '-')}")
            st.markdown(f"**爬取数量**: {record.get('spider_num', '-')}")
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
