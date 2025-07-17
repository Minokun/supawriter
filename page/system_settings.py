import streamlit as st
import sys
import os

# Add the parent directory to sys.path to ensure imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils.auth_decorator import require_auth
from settings import LLM_MODEL

@require_auth
def main():
    st.title("⚙️ 系统设置")
    st.info("在此处配置的选项将作为整个应用的默认设置。")

    # --- 全局模型设置 ---
    st.header("全局大语言模型设置")

    # 初始化session_state中的模型设置
    if 'global_model_settings' not in st.session_state:
        # 使用settings.py中的第一个模型作为默认值
        default_provider = list(LLM_MODEL.keys())[0]
        default_model = LLM_MODEL[default_provider]['model'][0] if isinstance(LLM_MODEL[default_provider]['model'], list) else LLM_MODEL[default_provider]['model']
        st.session_state.global_model_settings = {
            'provider': default_provider,
            'model_name': default_model
        }

    # 创建一个回调函数来更新模型名称
    def update_model_name():
        provider = st.session_state.selected_provider
        models = LLM_MODEL[provider]['model']
        # 当供应商改变时，自动选择新列表中的第一个模型
        st.session_state.global_model_settings['provider'] = provider
        st.session_state.global_model_settings['model_name'] = models[0] if isinstance(models, list) else models

    # 获取当前设置
    current_settings = st.session_state.global_model_settings
    current_provider = current_settings['provider']
    current_model_name = current_settings['model_name']

    # 获取当前供应商的模型列表
    available_models = LLM_MODEL[current_provider]['model']
    if not isinstance(available_models, list):
        available_models = [available_models]

    # 获取当前模型在列表中的索引
    try:
        model_index = available_models.index(current_model_name)
    except ValueError:
        model_index = 0 # 如果找不到，默认为第一个

    # UI组件
    selected_provider = st.selectbox(
        '请选择默认模型供应商',
        options=list(LLM_MODEL.keys()),
        index=list(LLM_MODEL.keys()).index(current_provider),
        key='selected_provider',
        on_change=update_model_name
    )

    selected_model_name = st.selectbox(
        '请选择默认模型名称',
        options=available_models,
        index=model_index,
        key='selected_model_name'
    )

    # 保存按钮
    if st.button("保存设置"):
        st.session_state.global_model_settings['provider'] = selected_provider
        st.session_state.global_model_settings['model_name'] = selected_model_name
        st.success("设置已成功保存！")

    # 显示当前保存的设置
    st.markdown("--- ")
    st.write("**当前已保存的设置:**")
    st.json(st.session_state.global_model_settings)

main()
