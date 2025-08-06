import streamlit as st
import os
import sys

# Add the parent directory to sys.path to ensure imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import load_user_history, add_history_record, save_html_to_user_dir
from llm_chat import chat
from settings import LLM_MODEL, ARTICLE_TRANSFORMATIONS
from utils.config_manager import get_config

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

    # 使用全局模型设置 - 从配置管理器获取
    config = get_config()
    global_settings = config.get('global_model_settings', {})
    # 如果全局设置为空，则使用第一个可用的模型作为后备
    if not global_settings:
        st.warning("尚未配置全局模型，请前往'系统设置'页面进行配置。将使用默认模型。")
        # 提供一个后备的默认模型
        default_provider = list(LLM_MODEL.keys())[0]
        default_model = LLM_MODEL[default_provider]['model'][0] if isinstance(LLM_MODEL[default_provider]['model'], list) else LLM_MODEL[default_provider]['model']
        model_type = default_provider
        model_name = default_model
    else:
        model_type = global_settings.get('provider')
        model_name = global_settings.get('model_name')

    st.info(f"将使用模型: **{model_type}/{model_name}**")

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
                    model_type=model_type, 
                    model_name=model_name
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
            
            # Save the transformed article
            # 保存转换后的文章（可能包含图片）
            
            # Load original article record to get its properties
            history = load_user_history(current_user)
            original_record = None
            for record in history:
                if record.get('id') == source_article_id:
                    original_record = record
                    break
            
            add_history_record(
                current_user,
                new_topic,
                transformed_content,
                summary=new_summary,
                model_type=model_type, # 使用全局模型设置
                model_name=model_name, # 使用全局模型设置
                write_type=selected_record.get('write_type'), # Inherit or set new?
                spider_num=selected_record.get('spider_num'), # Inherit or set new?
                custom_style=selected_record.get('custom_style'), # Inherit or set new?
                is_transformed=True,
                original_article_id=source_article_id
            )
            
            # 转换成功，提示用户在历史记录中查看
            if selected_transformation_name == "转换为Bento风格网页":
                st.success(f"Bento风格网页转换成功！请在历史记录中查看结果。")
            else:
                st.success(f"文章转换成功！请在历史记录中查看结果。")
                
            # 添加导航到历史记录的按钮
            if st.button("前往历史记录查看"):
                st.experimental_set_url("/history")
        else:
            st.error("转换后内容为空，未保存。")

main()
