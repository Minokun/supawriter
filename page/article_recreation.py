import streamlit as st
import os
import sys
import re

# Add the parent directory to sys.path to ensure imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils.auth_decorator import require_auth
from utils.auth import get_current_user
from utils.history_utils import load_user_history, add_history_record, save_html_to_user_dir, sanitize_filename
from utils.llm_chat import chat
from settings import LLM_MODEL, ARTICLE_TRANSFORMATIONS, default_provider, openai_model
from utils.config_manager import get_config


def _extract_html_document(content: str) -> str:
    """Try to extract a valid HTML document from LLM output."""
    if not content or not isinstance(content, str):
        return content

    cleaned = content.strip()

    # Prefer content inside fenced code blocks if present
    fence_match = re.search(r"```(?:html)?\s*(.*?)```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1).strip()
        if candidate:
            cleaned = candidate

    # Locate <!DOCTYPE html> if available
    lower_cleaned = cleaned.lower()
    doctype_idx = lower_cleaned.find('<!doctype html')
    if doctype_idx != -1:
        end_idx = lower_cleaned.rfind('</html>')
        if end_idx != -1:
            return cleaned[doctype_idx:end_idx + len('</html>')].strip()
        return cleaned[doctype_idx:].strip()

    # Fall back to extracting from the first <html ...> tag
    html_idx = lower_cleaned.find('<html')
    if html_idx != -1:
        end_idx = lower_cleaned.rfind('</html>')
        body = cleaned[html_idx:end_idx + len('</html>')] if end_idx != -1 else cleaned[html_idx:]
        body = body.strip()
        if not body.lower().startswith('<!doctype html'):
            body = f"<!DOCTYPE html>\n{body}"
        return body

    # Remove stray fences/backticks if no html found
    cleaned = re.sub(r"```", "", cleaned)
    return cleaned


def _enforce_bento_layout_constraints(html: str) -> str:
    """Normalize Bento HTML to avoid sections stretching to full viewport height."""
    if not html or not isinstance(html, str):
        return html

    # Remove problematic Tailwind classes that force full-screen height
    full_height_classes = [
        "min-h-screen",
        "h-screen",
        "min-h-full",
        "h-full"
    ]
    for cls in full_height_classes:
        html = html.replace(f" {cls} ", " ")
        html = html.replace(f" {cls}\n", " \n")
        html = html.replace(f"\n{cls} ", "\n")
        html = html.replace(f" {cls}", "")
        html = html.replace(f"{cls} ", "")

    # Downgrade inline styles that force viewport-scale heights
    height_patterns = [
        (r"min-height\s*:\s*1?\d{2,3}vh", "min-height: auto"),
        (r"height\s*:\s*1?\d{2,3}vh", "height: auto")
    ]
    for pattern, replacement in height_patterns:
        html = re.sub(pattern, replacement, html, flags=re.IGNORECASE)

    # Collapse redundant whitespace introduced by removals
    html = re.sub(r"\s{2,}", " ", html)
    
    # Ensure Tailwind CSS is present if Tailwind classes are used
    # Check for common Tailwind classes like "text-", "bg-", "p-", "m-", "grid", "flex"
    if 'class=' in html.lower() and ('grid' in html.lower() or 'flex' in html.lower() or 'text-' in html.lower()):
        if 'tailwindcss' not in html.lower() and 'cdn.tailwindcss.com' not in html.lower():
            tailwind_cdn = '<script src="https://cdn.tailwindcss.com"></script>'
            if '</head>' in html:
                html = html.replace('</head>', f"{tailwind_cdn}</head>")
            elif '<head>' in html:
                html = html.replace('<head>', f"<head>{tailwind_cdn}")
            else:
                # No head tag, prepend to body or html
                html = f"{tailwind_cdn}\n{html}"

    # Critical fix for AOS (Animate On Scroll) - ensures content visibility
    # AOS hides elements with data-aos by default, they only show after init
    if 'aos.js' in html.lower() or 'data-aos' in html.lower():
        # Remove any existing inline AOS.init() calls that might execute too early
        html = re.sub(r'AOS\.init\s*\([^)]*\)\s*;?', '', html, flags=re.IGNORECASE)
        
        # Inject robust initialization script that:
        # 1. Waits for window load (ensures AOS library is loaded)
        # 2. Falls back to removing data-aos if AOS fails to load
        init_script = """
    <script>
        // Critical AOS initialization - must run after library loads
        window.addEventListener('load', function() {
            if (typeof AOS !== 'undefined') {
                try {
                    AOS.init({
                        duration: 800,
                        easing: 'ease-out-cubic',
                        once: true,
                        offset: 50,
                        disable: false
                    });
                    console.log('AOS initialized successfully');
                } catch (e) {
                    console.error('AOS init failed:', e);
                    // Fallback: remove data-aos to make content visible
                    document.querySelectorAll('[data-aos]').forEach(el => {
                        el.removeAttribute('data-aos');
                        el.style.opacity = '1';
                        el.style.transform = 'none';
                    });
                }
            } else {
                console.warn('AOS library not loaded, removing animations');
                // Fallback: remove data-aos to make content visible
                document.querySelectorAll('[data-aos]').forEach(el => {
                    el.removeAttribute('data-aos');
                    el.style.opacity = '1';
                    el.style.transform = 'none';
                });
            }
        });
        // Emergency fallback if load event already fired
        if (document.readyState === 'complete') {
            setTimeout(function() {
                if (!window.AOS || !AOS.init) {
                    document.querySelectorAll('[data-aos]').forEach(el => {
                        el.removeAttribute('data-aos');
                        el.style.opacity = '1';
                        el.style.transform = 'none';
                    });
                }
            }, 1000);
        }
    </script>
    """
        if '</body>' in html:
            html = html.replace('</body>', f"{init_script}</body>")
        else:
            html += init_script
                
    return html

# 辅助函数：清理大模型输出中的 thinking 标签
def remove_thinking_tags(content):
    """
    移除大模型输出中的 thinking 标签及其内容
    支持的标签格式：<thinking>、<think>、<thought>
    只移除独立成段的thinking标签，避免误删代码示例中的内容
    """
    if not content or not isinstance(content, str):
        return content
    
    # 只在内容开头或换行后匹配thinking标签，避免误删代码示例
    # 使用更严格的匹配模式：标签前后必须有换行或在字符串开头/结尾
    think_patterns = [
        r'(?:^|\n)\s*<thinking>.*?</thinking>\s*(?:\n|$)',
        r'(?:^|\n)\s*<think>.*?</think>\s*(?:\n|$)',
        r'(?:^|\n)\s*<thought>.*?</thought>\s*(?:\n|$)'
    ]
    
    cleaned_content = content
    for pattern in think_patterns:
        # 使用 DOTALL 标志使 . 匹配包括换行符在内的所有字符
        # 保留匹配前后的换行符，只删除标签本身
        cleaned_content = re.sub(pattern, '\n', cleaned_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 清理可能产生的多余空行（3个或以上换行符减少为2个）
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    
    # 清理首尾多余空行，但保留基本格式
    return cleaned_content.strip('\n')

@require_auth
def main():
    # 自定义CSS样式
    st.markdown("""
    <style>
    /* 主标题样式 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    /* 卡片样式 */
    .card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    
    /* 统计卡片 */
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        margin: 0;
    }
    
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-top: 0.3rem;
    }
    
    /* 步骤指示器 */
    .step-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    
    .step-number {
        background: #667eea;
        color: white;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        flex-shrink: 0;
    }
    
    .step-text {
        font-size: 1.1rem;
        font-weight: 600;
        color: #333;
    }
    
    /* 提示框 */
    .tip-box {
        background: #f0f7ff;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 页面标题
    st.markdown('<h1 class="main-title">✨ 文章再创作工作台</h1>', unsafe_allow_html=True)
    st.markdown("**将您的文章转换为多种格式，释放内容的无限可能**")
    st.divider()

    current_user = get_current_user()
    if not current_user:
        st.error("🔒 无法获取当前用户信息")
        return

    history = load_user_history(current_user)
    if not history:
        st.info("📝 暂无历史文章可供转换，请先前往内容创作页面生成文章。")
        return

    # 显示统计信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{len(history)}</div>
            <div class="stat-label">📚 可用文章</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        transformation_count = len([r for r in history if r.get('is_transformed')])
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{transformation_count}</div>
            <div class="stat-label">🔄 已转换</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{len(ARTICLE_TRANSFORMATIONS)}</div>
            <div class="stat-label">🎨 转换模式</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 使用容器和选项卡优化布局
    with st.container():
        # 步骤1: 选择文章
        st.markdown("""
        <div class="step-indicator">
            <div class="step-number">1</div>
            <div class="step-text">选择源文章</div>
        </div>
        """, unsafe_allow_html=True)
        
        article_options = {f"📄 {record['topic']} ({record['timestamp'][:10]})": record for record in reversed(history)}
        
        selected_article_display_name = st.selectbox(
            "从历史记录中选择一篇文章",
            list(article_options.keys()),
            help="💡 选择您之前生成的文章作为转换源",
            label_visibility="collapsed"
        )

        if not selected_article_display_name:
            st.warning("⚠️ 请选择一篇文章")
            return

        selected_record = article_options[selected_article_display_name]
        
        # 显示选中文章的详情
        with st.expander("📋 查看文章详情", expanded=False):
            detail_col1, detail_col2 = st.columns(2)
            with detail_col1:
                st.markdown(f"**📝 主题:** {selected_record.get('topic', '-')}")
                st.markdown(f"**📅 创建时间:** {selected_record.get('timestamp', '-')[:16]}")
                st.markdown(f"**🆔 文章ID:** {selected_record.get('id', '-')}")
            with detail_col2:
                st.markdown(f"**🤖 模型:** {selected_record.get('model_type', '-')} / {selected_record.get('model_name', '-')}")
                st.markdown(f"**✍️ 写作模式:** {selected_record.get('write_type', '-')}")
                st.markdown(f"**📊 字数:** {len(selected_record.get('article_content', ''))} 字")

    st.divider()
    
    with st.container():
        # 步骤2: 选择转换类型
        st.markdown("""
        <div class="step-indicator">
            <div class="step-number">2</div>
            <div class="step-text">选择转换模式</div>
        </div>
        """, unsafe_allow_html=True)
        
        transformation_options = ARTICLE_TRANSFORMATIONS
        
        # 使用网格布局显示转换选项
        cols = st.columns(3)
        transformation_icons = {
            "白话文": "📖",
            "小红书风格": "💄",
            "转换为Bento风格网页": "🎨",
            "深度分析报告": "📊",
            "问答格式": "❓",
            "技术文档": "💻"
        }
        
        # 使用单选按钮组
        selected_transformation_name = st.radio(
            "选择转换类型",
            list(transformation_options.keys()),
            format_func=lambda x: f"{transformation_icons.get(x, '✨')} {x}",
            horizontal=True,
            label_visibility="collapsed"
        )

    st.divider()
    
    with st.container():
        # 步骤3: 模型配置
        st.markdown("""
        <div class="step-indicator">
            <div class="step-number">3</div>
            <div class="step-text">确认模型配置</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 使用全局模型设置 - 从配置管理器获取
        config = get_config()
        global_settings = config.get('global_model_settings', {})
        
        # 获取模型配置，确保不为空
        model_type = global_settings.get('provider') if global_settings else None
        model_name = global_settings.get('model_name') if global_settings else None
        
        # 如果全局设置为空或模型配置不完整，则使用第一个可用的模型作为后备
        if not model_type or not model_name or model_type not in LLM_MODEL:
            st.warning("⚙️ 尚未配置全局模型或配置无效，请前往'系统设置'页面进行配置。将使用默认模型。")
            # 提供一个后备的默认模型
            fallback_provider = list(LLM_MODEL.keys())[0]
            fallback_model = LLM_MODEL[fallback_provider]['model'][0] if isinstance(LLM_MODEL[fallback_provider]['model'], list) else LLM_MODEL[fallback_provider]['model']
            model_type = fallback_provider
            model_name = fallback_model

        # 显示模型信息卡片
        model_col1, model_col2 = st.columns([2, 1])
        with model_col1:
            st.info(f"🤖 **当前模型:** {model_type} / {model_name}")
        with model_col2:
            if st.button("⚙️ 修改设置", use_container_width=True):
                st.switch_page("page/system_settings.py")

    st.divider()
    
    # 执行转换
    if st.button(f"🚀 开始 {selected_transformation_name}", type="primary", use_container_width=True):
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
                transformed_content = remove_thinking_tags(transformed_content)  # 清理 thinking 标签
            except ConnectionError as e:
                st.error(f"{selected_transformation_name} 转换错误: {str(e)}")
                return
            except Exception as e:
                st.error(f"{selected_transformation_name} 转换发生未知错误: {str(e)}")
                return

        # 如果首次调用未返回内容且是 Bento 转换，尝试使用默认模型兜底
        if selected_transformation_name == "转换为Bento风格网页" and not transformed_content.strip():
            try:
                st.info("当前模型未返回内容，正在尝试使用默认模型重新生成 Bento 网页...")
                fallback_provider = default_provider
                fallback_model = openai_model
                transformed_content = chat(
                    source_article_content,
                    prompt_to_use,
                    model_type=fallback_provider,
                    model_name=fallback_model
                )
                transformed_content = remove_thinking_tags(transformed_content)
                # 更新记录使用的模型信息
                model_type = fallback_provider
                model_name = fallback_model
            except Exception as e:
                st.error(f"使用默认模型生成 Bento 网页时出错: {str(e)}")
                return

        if transformed_content.strip():
            st.success(f"{selected_transformation_name} 完成！")
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
            
            # Normalize HTML output for Bento web pages
            if selected_transformation_name == "转换为Bento风格网页":
                normalized_html = _extract_html_document(transformed_content)
                if not normalized_html.strip():
                    st.error("转换结果未生成有效的HTML，请稍后重试或检查原文内容。")
                    return
                transformed_content = _enforce_bento_layout_constraints(normalized_html)
                
                # 验证HTML内容有效性（至少应该包含基本的HTML结构）
                if len(transformed_content.strip()) < 200:
                    st.error(f"生成的HTML内容过短（仅{len(transformed_content.strip())}字符），可能不完整。请重试或检查模型输出。")
                    st.code(transformed_content[:500], language="html")
                    return
                
                # 立即保存HTML文件到文件系统，避免历史记录页面显示空白
                # 生成与历史记录页面一致的文件名
                raw_filename = f"{new_topic.replace(' ', '_')}_{max([r.get('id', 0) for r in history], default=0) + 1}.html"
                html_filename = sanitize_filename(raw_filename)
                try:
                    save_html_to_user_dir(current_user, transformed_content, html_filename)
                    st.info(f"✅ HTML文件已保存: {html_filename} ({len(transformed_content)}字符)")
                except Exception as e:
                    st.warning(f"保存HTML文件时出现警告: {str(e)}，但内容已保存到数据库")

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
            st.balloons()
            
            success_col1, success_col2 = st.columns([2, 1])
            with success_col1:
                if selected_transformation_name == "转换为Bento风格网页":
                    st.success(f"🎉 Bento风格网页转换成功！请在历史记录中查看精彩结果。")
                else:
                    st.success(f"🎉 文章转换成功！新内容已保存到历史记录。")
            
            with success_col2:
                # 添加导航到历史记录的按钮
                if st.button("📂 查看历史记录", type="primary", use_container_width=True):
                    st.switch_page("page/history.py")
        else:
            st.error("转换后内容为空，未保存。模型可能未返回有效内容，请检查模型配置或稍后重试。")
            try:
                raw_preview = transformed_content if isinstance(transformed_content, str) else str(transformed_content)
                st.info(f"模型原始输出长度: {len(raw_preview)} 字符")
                if raw_preview:
                    st.code(raw_preview[:500], language="html")
            except Exception as e:
                st.info(f"无法显示模型原始输出，用于调试的错误信息: {str(e)}")

main()
