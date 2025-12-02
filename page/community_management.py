import streamlit as st
import sys
import logging
import asyncio
import pandas as pd
from datetime import datetime
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import load_user_history
from utils.db_adapter import check_synced_articles, sync_articles_to_db, get_user_articles, get_user_articles_count, delete_article

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('community_management')

@require_auth
def main():
    st.title("🌐 社区管理")
    st.markdown("管理本地文章与PostgreSQL数据库的同步，查询和管理已发布的文章。")
    
    # Get current user
    current_user = get_current_user()
    if not current_user:
        st.error("无法获取当前用户信息")
        return
    
    # 创建标签页
    tab1, tab2 = st.tabs(["📤 一键发布", "📊 文章管理"])
    
    # ==================== 标签页1: 一键发布 ====================
    with tab1:
        st.markdown("### 将本地文章同步到PostgreSQL数据库")
        
        # Load user history
        history = load_user_history(current_user)
        
        if not history:
            st.info("暂无本地历史记录")
        else:
            # 检查按钮
            col1, col2 = st.columns([1, 3])
            with col1:
                check_button = st.button("🔍 检查同步状态", type="primary", use_container_width=True)
            
            if check_button:
                with st.spinner("正在检查同步状态..."):
                    try:
                        # 使用asyncio运行异步函数
                        sync_status = asyncio.run(check_synced_articles(current_user))
                        
                        if 'error' in sync_status:
                            st.error(f"❌ {sync_status['error']}")
                        elif 'message' in sync_status:
                            st.info(sync_status['message'])
                        else:
                            # 显示同步统计
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("总文章数", sync_status['total_count'])
                            with col2:
                                st.metric("已同步", sync_status['synced_count'], 
                                        delta=None, delta_color="normal")
                            with col3:
                                st.metric("未同步", sync_status['unsynced_count'], 
                                        delta=None, delta_color="inverse")
                            
                            # 保存同步状态到session_state
                            st.session_state['sync_status'] = sync_status
                            
                            if sync_status['unsynced_count'] > 0:
                                st.success(f"✅ 发现 {sync_status['unsynced_count']} 篇未同步的文章")
                            else:
                                st.success("✅ 所有文章已同步到数据库")
                                
                    except Exception as e:
                        st.error(f"检查失败: {str(e)}")
                        logger.error(f"检查同步状态失败: {e}")
            
            # 如果有未同步的文章，显示选择和发布界面
            if 'sync_status' in st.session_state and st.session_state['sync_status'].get('unsynced_count', 0) > 0:
                st.divider()
                st.markdown("#### 选择要发布的文章")
                
                unsynced_articles = st.session_state['sync_status']['unsynced']
                
                # 全选checkbox
                select_all = st.checkbox("🎯 全选", key="select_all_articles")
                
                # 当全选状态改变时，更新所有单个checkbox的状态
                if select_all:
                    # 全选时，设置所有checkbox为选中
                    for article in unsynced_articles:
                        article_id = article.get('id')
                        checkbox_key = f"article_checkbox_{article_id}"
                        if checkbox_key not in st.session_state or not st.session_state[checkbox_key]:
                            st.session_state[checkbox_key] = True
                
                # 文章选择列表
                selected_article_ids = []
                
                for article in unsynced_articles:
                    article_id = article.get('id')
                    article_topic = article.get('topic', '无标题')
                    article_time = article.get('timestamp', '')[:16].replace('T', ' ')
                    
                    # 显示文章checkbox，使用key让Streamlit自动管理状态
                    checkbox_key = f"article_checkbox_{article_id}"
                    is_checked = st.checkbox(
                        f"📝 {article_topic} - {article_time}", 
                        key=checkbox_key
                    )
                    
                    if is_checked:
                        selected_article_ids.append(article_id)
                
                # 发布按钮
                st.divider()
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.info(f"已选择 {len(selected_article_ids)} 篇文章")
                with col2:
                    publish_button = st.button(
                        "🚀 发布选中文章", 
                        type="primary",
                        disabled=len(selected_article_ids) == 0,
                        use_container_width=True
                    )
                
                # 执行发布
                if publish_button and len(selected_article_ids) > 0:
                    with st.spinner(f"正在发布 {len(selected_article_ids)} 篇文章..."):
                        try:
                            result = asyncio.run(sync_articles_to_db(current_user, selected_article_ids))
                            
                            if result.get('success'):
                                # 显示同步结果
                                success_msg = f"✅ 发布完成！已处理 {result.get('success_count', 0)} 条记录"
                                
                                # 如果有失败的，显示失败数量
                                if result.get('failed_count', 0) > 0:
                                    success_msg += f"（失败: {result['failed_count']}）"
                                
                                st.success(success_msg)
                                st.info("💡 提示：重新点击 '检查同步状态' 可查看准确的同步统计")
                                
                                # 显示错误信息（如果有）
                                if result.get('errors'):
                                    with st.expander("查看错误详情"):
                                        for error in result['errors']:
                                            st.error(error)
                                
                                # 清除session_state中的同步状态，让用户可以重新检查
                                if 'sync_status' in st.session_state:
                                    del st.session_state['sync_status']
                            else:
                                st.error(f"❌ 发布失败: {result.get('error', '未知错误')}")
                                
                        except Exception as e:
                            st.error(f"发布失败: {str(e)}")
                            logger.error(f"批量发布失败: {e}")
    
    # ==================== 标签页2: 文章管理 ====================
    with tab2:
        st.markdown("### 查询和管理数据库中的文章")
        
        # 搜索区域
        col1, col2 = st.columns([3, 1])
        with col1:
            search_keyword = st.text_input("🔍 搜索关键词", placeholder="输入标题关键词搜索...")
        with col2:
            st.write("")  # 占位符，用于对齐
            search_button = st.button("搜索", type="primary", use_container_width=True)
        
        # 显示统计信息
        try:
            # 获取文章总数
            total_count = asyncio.run(get_user_articles_count(current_user))
            
            # 获取前100篇用于显示
            articles = asyncio.run(get_user_articles(current_user, limit=100))
            
            if total_count > 0:
                # 显示准确的总数
                if total_count > 100:
                    st.info(f"📊 数据库中共有 **{total_count}** 篇文章（显示前 100 篇）")
                else:
                    st.info(f"📊 数据库中共有 **{total_count}** 篇文章")
            else:
                st.info("📭 数据库中暂无文章")
            
            if articles:
                # 如果有搜索关键词，过滤文章
                if search_keyword and search_button:
                    keyword_lower = search_keyword.lower()
                    filtered_articles = [
                        article for article in articles 
                        if keyword_lower in article.get('topic', '').lower()
                    ]
                    st.success(f"🔍 找到 {len(filtered_articles)} 篇匹配的文章")
                else:
                    filtered_articles = articles if articles else []
                
                # 显示文章列表
                st.divider()
                
                if not filtered_articles:
                    st.warning("未找到匹配的文章")
                else:
                    # 使用dataframe显示文章列表
                    df_data = []
                    for article in filtered_articles:
                        created_at = article.get('created_at')
                        if created_at:
                            if isinstance(created_at, str):
                                time_str = created_at[:16].replace('T', ' ')
                            else:
                                time_str = created_at.strftime('%Y-%m-%d %H:%M')
                        else:
                            time_str = '-'
                        
                        df_data.append({
                            'ID': str(article.get('id', '-')),
                            '标题': article.get('topic', '无标题'),
                            '创建时间': time_str,
                            '模型': article.get('model_name', '-'),
                            '标签数': len(article.get('tags', []))
                        })
                    
                    df = pd.DataFrame(df_data)
                    
                    # 使用st.data_editor显示可选择的表格
                    st.markdown("#### 文章列表")
                    
                    # 显示文章详情和删除按钮
                    for idx, article in enumerate(filtered_articles):
                        with st.expander(f"📄 {article.get('topic', '无标题')} - {df_data[idx]['创建时间']}"):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                # 显示文章信息
                                st.markdown(f"**ID**: `{article.get('id', '-')}`")
                                st.markdown(f"**模型**: {article.get('model_name', '-')}")
                                st.markdown(f"**写作模式**: {article.get('write_type', '-')}")
                                
                                tags = article.get('tags', [])
                                if tags:
                                    tags_str = ', '.join(tags) if isinstance(tags, list) else tags
                                    st.markdown(f"**标签**: {tags_str}")
                                
                                # 显示内容预览
                                preview = article.get('preview', '')
                                if preview:
                                    st.markdown("**内容预览**:")
                                    st.text(preview[:200] + "..." if len(preview) > 200 else preview)
                            
                            with col2:
                                # 删除按钮
                                delete_key = f"delete_btn_{article.get('id')}"
                                if st.button("🗑️ 删除", key=delete_key, type="secondary", use_container_width=True):
                                    st.session_state[f'confirm_delete_{article.get("id")}'] = True
                                
                                # 确认删除
                                if st.session_state.get(f'confirm_delete_{article.get("id")}'):
                                    st.warning("确认删除？")
                                    col_yes, col_no = st.columns(2)
                                    with col_yes:
                                        if st.button("✓", key=f"yes_{article.get('id')}", use_container_width=True):
                                            try:
                                                success = asyncio.run(delete_article(current_user, str(article.get('id'))))
                                                if success:
                                                    st.success("✅ 删除成功")
                                                    st.session_state[f'confirm_delete_{article.get("id")}'] = False
                                                    st.rerun()
                                                else:
                                                    st.error("❌ 删除失败")
                                            except Exception as e:
                                                st.error(f"删除失败: {str(e)}")
                                    with col_no:
                                        if st.button("✗", key=f"no_{article.get('id')}", use_container_width=True):
                                            st.session_state[f'confirm_delete_{article.get("id")}'] = False
                                            st.rerun()
                
        except Exception as e:
            error_msg = str(e)
            if 'PostgreSQL' in error_msg or '未启用' in error_msg:
                st.warning("⚠️ PostgreSQL数据库未启用，无法使用文章管理功能")
                st.info("💡 请在 `deployment/.env` 中配置数据库连接信息")
            else:
                st.error(f"❌ 加载文章列表失败: {error_msg}")
                logger.error(f"加载文章列表失败: {e}")

if __name__ == "__main__":
    main()
