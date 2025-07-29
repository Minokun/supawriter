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
from utils.config_manager import get_config, set_config

@require_auth
def main():
    st.title("⚙️ 系统设置")
    st.info("在此处配置的选项将作为整个应用的默认设置。所有设置将自动保存，刷新页面后仍然有效。")

    # 从配置管理器加载配置
    config = get_config()
    
    # --- 全局模型设置 ---
    st.header("全局大语言模型设置")

    # 初始化模型设置
    if 'global_model_settings' not in config:
        # 使用settings.py中的第一个模型作为默认值
        default_provider = list(LLM_MODEL.keys())[0]
        default_model = LLM_MODEL[default_provider]['model'][0] if isinstance(LLM_MODEL[default_provider]['model'], list) else LLM_MODEL[default_provider]['model']
        model_settings = {
            'provider': default_provider,
            'model_name': default_model
        }
    else:
        model_settings = config['global_model_settings']
    
    # 将配置加载到session_state中方便UI交互
    if 'global_model_settings' not in st.session_state:
        st.session_state.global_model_settings = model_settings.copy()

    # 创建一个回调函数来更新模型名称
    def update_model_name():
        provider = st.session_state.selected_provider
        models = LLM_MODEL[provider]['model']
        # 当供应商改变时，自动选择新列表中的第一个模型
        st.session_state.global_model_settings['provider'] = provider
        st.session_state.global_model_settings['model_name'] = models[0] if isinstance(models, list) else models
        # 保存到配置
        config['global_model_settings'] = st.session_state.global_model_settings
        set_config('global_model_settings', st.session_state.global_model_settings)

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
    if st.button("保存LLM模型设置"):
        st.session_state.global_model_settings['provider'] = selected_provider
        st.session_state.global_model_settings['model_name'] = selected_model_name
        # 保存到配置
        set_config('global_model_settings', st.session_state.global_model_settings)
        st.success("LLM模型设置已成功保存！")

    # --- 嵌入模型设置 ---
    st.markdown("--- ")
    st.header("嵌入模型设置")
    st.info("嵌入模型用于处理图片和文本的向量表示，用于相似度匹配。修改这些设置需要重启应用才能生效。")
    
    # 嵌入模型默认配置
    embedding_defaults = {
        'xinference': {
            'model': 'jina-embeddings-v4',
            'dimension': 2048,
            'timeout': 10
        },
        'gitee': {
            'model': 'text-embedding-ada-002',
            'dimension': 1536,
            'timeout': 10
        },
        'jina': {
            'model': 'jina-embeddings-v2-base-en',
            'dimension': 768,
            'timeout': 10
        }
    }
    
    # 初始化嵌入设置
    if 'embedding_settings' not in config:
        embedding_settings = {
            'type': 'xinference',  # 默认嵌入类型
            'model': embedding_defaults['xinference']['model'],
            'dimension': embedding_defaults['xinference']['dimension'],
            'timeout': embedding_defaults['xinference']['timeout']
        }
    else:
        embedding_settings = config['embedding_settings']
    
    # 将配置加载到session_state中方便UI交互
    if 'embedding_settings' not in st.session_state:
        st.session_state.embedding_settings = embedding_settings.copy()
    
    # 嵌入类型选项
    embedding_types = ['xinference', 'gitee', 'jina']
    current_type = st.session_state.embedding_settings.get('type', 'xinference')
    
    # 获取当前类型在列表中的索引
    try:
        type_index = embedding_types.index(current_type)
    except ValueError:
        type_index = 0  # 默认为xinference
    
    # 显示当前选择的嵌入类型的其他参数
    col1, col2 = st.columns(2)
    with col1:
        # UI组件 - 只显示嵌入类型选择
        selected_type = st.selectbox(
            '请选择嵌入模型类型',
            options=embedding_types,
            index=type_index,
            key='selected_embedding_type',
            help='选择不同的嵌入类型将自动设置相应的模型参数'
        )
    
    # 显示当前选择类型的默认参数
    with col2:
        st.info(f"""
        **当前选择:** {selected_type}
        **模型:** {embedding_defaults[selected_type]['model']}
        **维度:** {embedding_defaults[selected_type]['dimension']}
        **超时:** {embedding_defaults[selected_type]['timeout']}s
        """)
    
    # 保存按钮
    if st.button("保存嵌入模型设置"):
        # 根据选择的类型自动设置其他参数
        st.session_state.embedding_settings = {
            'type': selected_type,
            'model': embedding_defaults[selected_type]['model'],
            'dimension': embedding_defaults[selected_type]['dimension'],
            'timeout': embedding_defaults[selected_type]['timeout']
        }
        # 保存到配置
        set_config('embedding_settings', st.session_state.embedding_settings)
        st.success("嵌入模型设置已成功保存！需要重启应用才能生效。")
    
    # 显示当前保存的设置
    st.markdown("--- ")
    st.write("**当前已保存的全局设置:**")
    st.json(config)

main()
