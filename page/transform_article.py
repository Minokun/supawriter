import streamlit as st
import os
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import load_user_history, add_history_record
from utils.searxng_utils import chat
import utils.prompt_template as pt
from settings import LLM_MODEL, ARTICLE_TRANSFORMATIONS
from utils.image_manager import ImageManager

@require_auth
def main():
    st.title("文章再创作")

    current_user = get_current_user()
    if not current_user:
        st.error("无法获取当前用户信息")
        return

    history = load_user_history(current_user)
    if not history:
        st.info("暂无历史文章可供转换。")
        return

    # Filter for original articles only, or allow transforming transformed ones too?
    # For now, let's allow transforming any article.
    article_options = {f"{record['topic']} ({record['timestamp'][:10]}) - ID: {record['id']}": record for record in reversed(history)}
    
    st.subheader("图片设置")
    enable_images = st.checkbox("自动插入相关图片", value=False)
    auto_select_image_dir = st.checkbox("自动选择插入图片的选项", value=False, help="如果勾选，将自动使用原文章抓取图片的task_id目录")
    
    # 初始化变量
    image_task_id = None
    similarity_threshold = 0.5
    max_images = 10
    image_base_dir = "images"
    
    if enable_images:
        # 获取可用的任务目录
        if not os.path.exists(image_base_dir):
            os.makedirs(image_base_dir)
            
        task_dirs = [d for d in os.listdir(image_base_dir) 
                   if os.path.isdir(os.path.join(image_base_dir, d)) and d.startswith("task_")]
        
        # 如果选择了自动选择图片目录，先不显示选择框
        if not auto_select_image_dir:
            similarity_threshold = st.slider(
                "相似度阈值", 
                min_value=0.3, 
                max_value=0.9, 
                value=0.5, 
                step=0.05
            )
                
            max_images = st.slider(
                "最大扫描图片数量", 
                min_value=5, 
                max_value=30, 
                value=10
            )
                
            if task_dirs:
                image_task_id = st.selectbox(
                    "选择图片目录", 
                    options=task_dirs,
                    format_func=lambda x: x.replace("task_", "任务 ")
                )
                st.info(f"将从 {os.path.join(image_base_dir, image_task_id)} 目录中分析图片")
            else:
                st.warning("未找到任何图片任务目录")
        else:
            # 显示提示信息，表明将自动使用原文章的图片目录
            st.info("将自动使用原文章抓取图片的task_id目录")
            
        if not task_dirs:
            st.warning(f"图片目录 '{image_base_dir}' 中没有任何任务目录")
            enable_images = False
    
    selected_article_display_name = st.selectbox(
        "选择一篇文章进行再创作:", 
        list(article_options.keys()),
        help="选择一篇您之前生成的文章。"
    )

    if not selected_article_display_name:
        st.warning("请选择一篇文章。")
        return

    selected_record = article_options[selected_article_display_name]

    transformation_options = ARTICLE_TRANSFORMATIONS
    selected_transformation_name = st.selectbox(
        "选择转换类型:", 
        list(transformation_options.keys())
    )

    # Get model config from original article or use defaults/sidebar options
    # For simplicity, let's try to use original model settings if available, else default
    original_model_type = selected_record.get('model_type', list(LLM_MODEL.keys())[0])
    original_model_name = selected_record.get('model_name', LLM_MODEL[original_model_type]['model'][0])

    if st.button(f"开始 {selected_transformation_name}"):
        source_article_content = selected_record['article_content']
        source_article_id = selected_record['id']
        source_article_topic = selected_record['topic']
        source_article_summary = selected_record.get('summary', '')
        prompt_to_use = transformation_options[selected_transformation_name]

        transformed_content = ""
        with st.spinner(f"正在 {selected_transformation_name}..."):
            try:
                transformed_content = chat(
                    source_article_content, 
                    prompt_to_use, 
                    model_type=original_model_type, 
                    model_name=original_model_name
                )
                st.success(f"{selected_transformation_name} 完成！")
            except ConnectionError as e:
                st.error(f"{selected_transformation_name} 转换错误: {str(e)}")
                return
            except Exception as e:
                st.error(f"{selected_transformation_name} 转换发生未知错误: {str(e)}")
                return

        if transformed_content.strip():
            # Ensure the new topic clearly indicates it's a transformed version based on the selected transformation name
            # If the original topic already indicates a transformation, avoid nesting, e.g. "Topic (白话文) (白话文)"
            base_topic = source_article_topic
            # Attempt to remove previous transformation tags if any
            for trans_name in ARTICLE_TRANSFORMATIONS.keys():
                if base_topic.endswith(f" ({trans_name})"):
                    base_topic = base_topic[:-len(f" ({trans_name})")].strip()
                    break
            new_topic = f"{base_topic} ({selected_transformation_name})"
            base_summary = source_article_summary
            for trans_name in ARTICLE_TRANSFORMATIONS.keys():
                if base_summary.endswith(f" ({trans_name} 版本)"):
                    base_summary = base_summary[:-len(f" ({trans_name} 版本)")].strip()
                    break
            new_summary = f"{base_summary} ({selected_transformation_name} 版本)"  
            
            # 如果启用图片分析与插入，处理文章
            if enable_images and transformed_content.strip():
                # 如果启用自动选择，使用原文章的task_id
                if auto_select_image_dir:
                    # 获取原文章的图片参数
                    original_image_task_id = selected_record.get('image_task_id')
                    original_similarity_threshold = selected_record.get('image_similarity_threshold', 0.5)
                    original_max_images = selected_record.get('image_max_count', 10)
                    
                    if original_image_task_id:
                        image_task_id = original_image_task_id
                        similarity_threshold = original_similarity_threshold
                        max_images = original_max_images
                        st.info(f"使用原文章的图片目录: {image_task_id}")
                    else:
                        st.warning("原文章没有相关的图片task_id信息，将使用默认选择。")
                
                if image_task_id:
                    with st.status("正在分析并插入相关图片..."):
                        try:
                            # 初始化图片管理器
                            image_manager = ImageManager(
                                image_base_dir=image_base_dir,
                                task_id=image_task_id
                            )
                            
                            # 插入图片到文章
                            transformed_content = image_manager.insert_images_into_article(
                                transformed_content,
                                similarity_threshold=similarity_threshold,
                                max_images=max_images,
                                article_theme=new_topic
                            )
                            
                            st.success(f"图片插入完成！使用目录: {image_task_id}, 相似度阈值: {similarity_threshold}, 最大图片数: {max_images}")
                        except Exception as e:
                            st.error(f"图片处理失败: {str(e)}")
                            st.warning("继续使用原始转换文章。")
                else:
                    st.warning("未指定图片目录，无法插入图片。")
            
            # Save the transformed article
            # 保存转换后的文章（可能包含图片）
            
            # 从原始文章记录中获取图片相关参数
            # 首先加载原始文章的记录
            history = load_user_history(current_user)
            original_record = None
            for record in history:
                if record.get('id') == source_article_id:
                    original_record = record
                    break
            
            # 获取原始文章的图片参数
            image_enabled = original_record.get('image_enabled', False) if original_record else False
            image_task_id = original_record.get('image_task_id', None) if original_record else None
            image_similarity_threshold = original_record.get('image_similarity_threshold', None) if original_record else None
            image_max_count = original_record.get('image_max_count', None) if original_record else None
            
            add_history_record(
                current_user,
                new_topic,
                transformed_content,
                summary=new_summary,
                model_type=original_model_type, # or the model used for transformation
                model_name=original_model_name, # or the model used for transformation
                write_type=selected_record.get('write_type'), # Inherit or set new?
                spider_num=selected_record.get('spider_num'), # Inherit or set new?
                custom_style=selected_record.get('custom_style'), # Inherit or set new?
                is_transformed=True,
                original_article_id=source_article_id,
                image_task_id=image_task_id,
                image_enabled=image_enabled,
                image_similarity_threshold=image_similarity_threshold,
                image_max_count=image_max_count
            )
            st.success("转换后的文章已保存到历史记录！")

            st.subheader("转换结果:")
            
            # 判断是否为HTML内容
            is_html = transformed_content.strip().startswith('<') and transformed_content.strip().endswith('>')
            
            if is_html and selected_transformation_name == "转换为Bento风格网页":
                # 对于HTML内容，不直接显示，而是提供运行按钮
                st.info("这是一个Bento风格网页内容，点击下方按钮查看效果")
                
                # 添加运行按钮
                # 首先需要保存到历史记录中并获取最新记录的ID
                history = load_user_history(current_user)
                latest_record_id = None
                for record in reversed(history):
                    if record['topic'] == new_topic:
                        latest_record_id = record['id']
                        break
                
                if latest_record_id:
                    # 获取最新记录的HTML内容
                    def on_run_button_click(rec_id):
                        st.session_state.record_id_for_viewer = rec_id
                        st.switch_page("page/html_viewer.py")

                    st.button("🖥️ 运行网页", 
                              key=f"run_transformed_{latest_record_id}", 
                              on_click=on_run_button_click, 
                              args=(latest_record_id,))

                
                # 下载按钮
                st.download_button(
                    label=f"下载 {selected_transformation_name}",
                    data=transformed_content,
                    file_name=f"{new_topic}.html",
                    mime="text/html",
                    key=f"download_transformed_{source_article_id}_{selected_transformation_name.replace(' ', '_')}"
                )
            else:
                # 对于普通文本内容，直接显示
                st.markdown(transformed_content)
                st.download_button(
                    label=f"下载 {selected_transformation_name} 版本",
                    data=transformed_content,
                    file_name=f"{new_topic}.md",
                    mime="text/markdown",
                    key=f"download_transformed_{source_article_id}_{selected_transformation_name.replace(' ', '_')}"
                )
        else:
            st.error("转换后内容为空，未保存。")

if __name__ == "__main__":
    main()
