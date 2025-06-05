import streamlit as st
from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import load_user_history, add_history_record
from utils.searxng_utils import chat
import utils.prompt_template as pt
from settings import LLM_MODEL, ARTICLE_TRANSFORMATIONS

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
            
            # Save the transformed article
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
                original_article_id=source_article_id
            )
            st.success("转换后的文章已保存到历史记录！")

            st.subheader("转换结果:")
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
