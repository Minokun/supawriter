import streamlit as st
import sys
import os
import json
import ast

# Add the parent directory to sys.path to ensure imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils.auth_decorator import require_auth
from settings import LLM_MODEL
from utils.config_manager import get_config, set_config, load_secrets_toml, save_secrets_toml

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

    # --- 备用模型设置（可折叠） ---
    with st.expander("🔄 备用模型设置（可选）", expanded=False):
        st.caption("当默认模型因内容审核、速率限制或连接错误失败时，系统将自动切换到备用模型继续处理。")
        
        # 初始化备用模型设置
        fallback_settings = current_settings.get('fallback', {})
        fallback_enabled = fallback_settings.get('enabled', False)
        fallback_provider = fallback_settings.get('provider', '')
        fallback_model_name = fallback_settings.get('model_name', '')
        
        # 启用备用模型开关
        enable_fallback = st.checkbox(
            "启用备用模型",
            value=fallback_enabled,
            key='enable_fallback_model',
            help="启用后，当默认模型失败时将自动切换到备用模型"
        )
        
        if enable_fallback:
            # 备用模型供应商选择（排除当前选择的默认供应商，或允许相同供应商不同模型）
            fallback_provider_options = list(LLM_MODEL.keys())
            
            # 获取备用供应商的索引
            try:
                fallback_provider_index = fallback_provider_options.index(fallback_provider) if fallback_provider else 0
            except ValueError:
                fallback_provider_index = 0
            
            selected_fallback_provider = st.selectbox(
                '备用模型供应商',
                options=fallback_provider_options,
                index=fallback_provider_index,
                key='selected_fallback_provider'
            )
            
            # 获取备用供应商的模型列表
            fallback_available_models = LLM_MODEL[selected_fallback_provider]['model']
            if not isinstance(fallback_available_models, list):
                fallback_available_models = [fallback_available_models]
            
            # 获取备用模型在列表中的索引
            try:
                fallback_model_index = fallback_available_models.index(fallback_model_name) if fallback_model_name else 0
            except ValueError:
                fallback_model_index = 0
            
            selected_fallback_model = st.selectbox(
                '备用模型名称',
                options=fallback_available_models,
                index=fallback_model_index,
                key='selected_fallback_model'
            )
            
            # 显示提示
            if selected_fallback_provider == selected_provider and selected_fallback_model == selected_model_name:
                st.warning("⚠️ 备用模型与默认模型相同，建议选择不同的模型以确保故障转移有效。")
    
    # 保存按钮
    if st.button("保存LLM模型设置"):
        st.session_state.global_model_settings['provider'] = selected_provider
        st.session_state.global_model_settings['model_name'] = selected_model_name
        
        # 保存备用模型设置
        if 'enable_fallback_model' in st.session_state and st.session_state.enable_fallback_model:
            st.session_state.global_model_settings['fallback'] = {
                'enabled': True,
                'provider': st.session_state.get('selected_fallback_provider', ''),
                'model_name': st.session_state.get('selected_fallback_model', '')
            }
        else:
            st.session_state.global_model_settings['fallback'] = {'enabled': False}
        
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
            'model': 'jina-embeddings-v4',
            'dimension': 2048,
            'timeout': 10
        },
        'jina': {
            'model': 'jina-embeddings-v4',
            'dimension': 2048,
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

    # --- API密钥配置 ---
    st.markdown("--- ")
    st.header("API 密钥配置")
    st.info("在这里配置的密钥将保存在项目的 `.streamlit/secrets.toml` 文件中。请妥善保管您的密钥。")

    secrets_data = load_secrets_toml()
    if not secrets_data:
        st.warning("无法加载 `secrets.toml` 文件，或文件为空。")
    else:
        # 使用一个字典来收集更新后的值
        updated_secrets = secrets_data.copy()

        # 分离顶级配置和分节配置
        top_level_keys = {k: v for k, v in secrets_data.items() if not isinstance(v, dict)}
        section_keys = {k: v for k, v in secrets_data.items() if isinstance(v, dict)}

        # 用于记录本次渲染中出现的列表字段，保存时写回
        list_fields = []  # list of tuples: (section_name or None, key, session_key)

        # 小工具：将可能的字符串列表安全解析为 list
        def parse_list_value(val):
            if isinstance(val, list):
                return [str(x) for x in val]
            if isinstance(val, str):
                s = val.strip()
                if s.startswith("[") and s.endswith("]"):
                    try:
                        parsed = json.loads(s)
                        if isinstance(parsed, list):
                            return [str(x) for x in parsed]
                    except Exception:
                        try:
                            parsed = ast.literal_eval(s)
                            if isinstance(parsed, list):
                                return [str(x) for x in parsed]
                        except Exception:
                            pass
            return None

        # 1. 渲染顶级配置（一般为字符串，如有列表可扩展为列表编辑器）
        if top_level_keys:
            with st.expander("全局配置", expanded=True):
                for key, value in top_level_keys.items():
                    parsed_list = parse_list_value(value)
                    if parsed_list is not None:
                        # 顶级列表字段的编辑器
                        skey = f"list__{key}_items"
                        if skey not in st.session_state:
                            st.session_state[skey] = parsed_list
                        st.markdown(f"**{key}**")
                        items = st.session_state[skey]
                        remove_indices = []
                        for i in range(len(items)):
                            c1, c2 = st.columns([0.8, 0.2])
                            with c1:
                                items[i] = st.text_input(f"{key}[{i}]", value=items[i], key=f"{skey}_item_{i}")
                            with c2:
                                if st.button("删除", key=f"{skey}_del_{i}"):
                                    remove_indices.append(i)
                        # 执行删除
                        for idx in sorted(remove_indices, reverse=True):
                            items.pop(idx)
                        if st.button(f"➕ 添加 {key}", key=f"{skey}_add"):
                            items.append("")
                        st.session_state[skey] = items
                        list_fields.append((None, key, skey))
                    else:
                        new_value = st.text_input(
                            f"{key}",
                            value=value,
                            key=f"top_level_{key}",
                            type="password" if "key" in key.lower() or "token" in key.lower() else "default"
                        )
                        updated_secrets[key] = new_value

        # 2. 渲染分节配置
        for section, keys in section_keys.items():
            with st.expander(f"配置节: {section}", expanded=False):
                if isinstance(keys, dict):
                    updated_secrets[section] = updated_secrets.get(section, {})
                    for key, value in keys.items():
                        # 检查是否是子字典（例如 auth.google），如果是，则跳过，因为它会在自己的节中处理
                        if isinstance(value, dict):
                            continue
                        # 列表字段：提供增删改 UI；否则使用文本输入
                        parsed_list = parse_list_value(value)
                        if parsed_list is not None:
                            skey = f"list_{section}_{key}_items"
                            if skey not in st.session_state:
                                st.session_state[skey] = parsed_list
                            st.markdown(f"**{key}**")
                            items = st.session_state[skey]
                            remove_indices = []
                            for i in range(len(items)):
                                c1, c2 = st.columns([0.8, 0.2])
                                with c1:
                                    items[i] = st.text_input(f"{key}[{i}]", value=items[i], key=f"{skey}_item_{i}")
                                with c2:
                                    if st.button("删除", key=f"{skey}_del_{i}"):
                                        remove_indices.append(i)
                            for idx in sorted(remove_indices, reverse=True):
                                items.pop(idx)
                            if st.button(f"➕ 添加 {key}", key=f"{skey}_add"):
                                items.append("")
                            st.session_state[skey] = items
                            list_fields.append((section, key, skey))
                        else:
                            new_value = st.text_input(
                                f"{key}", 
                                value=value, 
                                key=f"{section}_{key}",
                                type="password" if "key" in key.lower() or "token" in key.lower() else "default"
                            )
                            updated_secrets[section][key] = new_value

        if st.button("保存 API 密钥"):
            # 将列表编辑器中的内容写回 updated_secrets，保证为数组而非字符串
            for section, key, skey in list_fields:
                items = [x for x in st.session_state.get(skey, []) if isinstance(x, str) and x.strip() != ""]
                if section is None:
                    updated_secrets[key] = items
                else:
                    updated_secrets[section][key] = items
            if save_secrets_toml(updated_secrets):
                st.success("API 密钥已成功保存！")
                st.rerun()
            else:
                st.error("保存 API 密钥失败，请检查日志。")

    # 显示当前保存的设置
    st.markdown("--- ")
    st.write("**当前已保存的全局设置:**")
    st.json(config)

main()
