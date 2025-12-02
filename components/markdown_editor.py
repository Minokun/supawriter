"""
Markdown Editor Component with Synchronized Scrolling
A custom Streamlit v2 component that provides a split-pane editor with live preview
and synchronized scrolling between the editor and preview panes.
"""

import streamlit as st
from typing import Optional

# CSS for the editor component
EDITOR_CSS = """
* {
    box-sizing: border-box;
}

.editor-container {
    display: flex;
    gap: 12px;
    height: 500px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.editor-pane, .preview-pane {
    flex: 1;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--st-secondary-background-color, #e0e0e0);
    border-radius: 8px;
    overflow: hidden;
    background: var(--st-background-color, #ffffff);
}

.pane-header {
    padding: 8px 12px;
    background: var(--st-secondary-background-color, #f5f5f5);
    border-bottom: 1px solid var(--st-secondary-background-color, #e0e0e0);
    font-weight: 600;
    font-size: 14px;
    color: var(--st-text-color, #333);
    display: flex;
    align-items: center;
    gap: 6px;
}

.editor-textarea {
    flex: 1;
    width: 100%;
    padding: 12px;
    border: none;
    resize: none;
    font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
    font-size: 14px;
    line-height: 1.6;
    background: var(--st-background-color, #ffffff);
    color: var(--st-text-color, #333);
    outline: none;
}

.editor-textarea:focus {
    outline: none;
}

.preview-content {
    flex: 1;
    padding: 12px;
    overflow-y: auto;
    line-height: 1.6;
    color: var(--st-text-color, #333);
}

/* Markdown preview styles */
.preview-content h1 {
    font-size: 1.8em;
    border-bottom: 2px solid var(--st-primary-color, #ff4b4b);
    padding-bottom: 8px;
    margin: 16px 0 12px 0;
}

.preview-content h2 {
    font-size: 1.5em;
    border-bottom: 1px solid var(--st-secondary-background-color, #e0e0e0);
    padding-bottom: 6px;
    margin: 14px 0 10px 0;
}

.preview-content h3 {
    font-size: 1.25em;
    margin: 12px 0 8px 0;
}

.preview-content p {
    margin: 8px 0;
}

.preview-content code {
    background: var(--st-secondary-background-color, #f5f5f5);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
    font-size: 0.9em;
}

.preview-content pre {
    background: var(--st-secondary-background-color, #f5f5f5);
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
}

.preview-content pre code {
    background: none;
    padding: 0;
}

.preview-content blockquote {
    border-left: 4px solid var(--st-primary-color, #ff4b4b);
    margin: 8px 0;
    padding: 8px 16px;
    background: var(--st-secondary-background-color, #f5f5f5);
    border-radius: 0 6px 6px 0;
}

.preview-content ul, .preview-content ol {
    margin: 8px 0;
    padding-left: 24px;
}

.preview-content li {
    margin: 4px 0;
}

.preview-content a {
    color: var(--st-primary-color, #ff4b4b);
    text-decoration: none;
}

.preview-content a:hover {
    text-decoration: underline;
}

.preview-content img {
    max-width: 100%;
    border-radius: 6px;
}

.preview-content table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
}

.preview-content th, .preview-content td {
    border: 1px solid var(--st-secondary-background-color, #e0e0e0);
    padding: 8px 12px;
    text-align: left;
}

.preview-content th {
    background: var(--st-secondary-background-color, #f5f5f5);
    font-weight: 600;
}

.preview-content hr {
    border: none;
    border-top: 1px solid var(--st-secondary-background-color, #e0e0e0);
    margin: 16px 0;
}

/* Sync indicator */
.sync-indicator {
    font-size: 12px;
    color: var(--st-text-color, #666);
    opacity: 0.7;
}

/* Line numbers (optional) */
.line-info {
    font-size: 11px;
    color: var(--st-text-color, #999);
    padding: 4px 12px;
    background: var(--st-secondary-background-color, #f9f9f9);
    border-top: 1px solid var(--st-secondary-background-color, #e0e0e0);
}
"""

# JavaScript for the editor component with synchronized scrolling
# Using raw string to avoid escape sequence issues
EDITOR_JS = r"""
export default function(component) {
    const { data, setStateValue, parentElement } = component;
    
    // Check if container already exists to prevent duplicate creation
    let container = parentElement.querySelector('.editor-container');
    let textarea, preview, lineInfo;
    
    if (!container) {
        // Create container only if it doesn't exist
        container = document.createElement('div');
        container.className = 'editor-container';
        parentElement.appendChild(container);
        
        // Create editor pane
        const editorPane = document.createElement('div');
        editorPane.className = 'editor-pane';
        editorPane.innerHTML = `
            <div class="pane-header">
                <span>✏️ 编辑区</span>
                <span class="sync-indicator">🔗 同步滚动</span>
            </div>
            <textarea class="editor-textarea" placeholder="在此输入 Markdown 内容..."></textarea>
            <div class="line-info">行: 1, 列: 1</div>
        `;
        container.appendChild(editorPane);
        
        // Create preview pane
        const previewPane = document.createElement('div');
        previewPane.className = 'preview-pane';
        previewPane.innerHTML = `
            <div class="pane-header">
                <span>👁️ 实时预览</span>
            </div>
            <div class="preview-content"></div>
        `;
        container.appendChild(previewPane);
        
        textarea = editorPane.querySelector('.editor-textarea');
        preview = previewPane.querySelector('.preview-content');
        lineInfo = editorPane.querySelector('.line-info');
        
        // Set initial content only on first creation
        textarea.value = data.content || '';
    } else {
        // Reuse existing elements - don't overwrite user's edits
        textarea = container.querySelector('.editor-textarea');
        preview = container.querySelector('.preview-content');
        lineInfo = container.querySelector('.line-info');
    }
    
    // Simple Markdown parser
    function parseMarkdown(text) {
        if (!text) return '<p style="color: #999;">预览区域</p>';
        
        // First, handle images BEFORE escaping HTML (images contain URLs with special chars)
        // Store images temporarily
        const images = [];
        text = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
            const placeholder = `__IMG_${images.length}__`;
            images.push({ alt, src });
            return placeholder;
        });
        
        // Store links temporarily
        const links = [];
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label, href) => {
            const placeholder = `__LINK_${links.length}__`;
            links.push({ label, href });
            return placeholder;
        });
        
        // Store code blocks temporarily
        const codeBlocks = [];
        text = text.replace(/```([\s\S]*?)```/g, (match, code) => {
            const placeholder = `__CODEBLOCK_${codeBlocks.length}__`;
            codeBlocks.push(code);
            return placeholder;
        });
        
        // Store inline code temporarily
        const inlineCodes = [];
        text = text.replace(/`([^`]+)`/g, (match, code) => {
            const placeholder = `__INLINECODE_${inlineCodes.length}__`;
            inlineCodes.push(code);
            return placeholder;
        });
        
        let html = text
            // Escape HTML
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            // Headers
            .replace(/^### (.+)$/gm, '<h3>$1</h3>')
            .replace(/^## (.+)$/gm, '<h2>$1</h2>')
            .replace(/^# (.+)$/gm, '<h1>$1</h1>')
            // Bold and italic
            .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            // Blockquotes
            .replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')
            // Horizontal rules
            .replace(/^---$/gm, '<hr>')
            .replace(/^\*\*\*$/gm, '<hr>')
            // Unordered lists
            .replace(/^[\-\*] (.+)$/gm, '<li>$1</li>')
            // Ordered lists
            .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
            // Paragraphs
            .replace(/\n\n/g, '</p><p>')
            // Line breaks
            .replace(/\n/g, '<br>');
        
        // Restore code blocks
        codeBlocks.forEach((code, i) => {
            const escaped = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            html = html.replace(`__CODEBLOCK_${i}__`, `<pre><code>${escaped}</code></pre>`);
        });
        
        // Restore inline code
        inlineCodes.forEach((code, i) => {
            const escaped = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            html = html.replace(`__INLINECODE_${i}__`, `<code>${escaped}</code>`);
        });
        
        // Restore images
        images.forEach((img, i) => {
            html = html.replace(`__IMG_${i}__`, `<img src="${img.src}" alt="${img.alt}" onerror="this.style.display='none'">`);
        });
        
        // Restore links
        links.forEach((link, i) => {
            html = html.replace(`__LINK_${i}__`, `<a href="${link.href}" target="_blank">${link.label}</a>`);
        });
        
        // Wrap in paragraph if not starting with block element
        if (!html.startsWith('<h') && !html.startsWith('<pre') && !html.startsWith('<blockquote') && !html.startsWith('<ul') && !html.startsWith('<ol')) {
            html = '<p>' + html + '</p>';
        }
        
        // Clean up empty paragraphs
        html = html.replace(/<p><\/p>/g, '');
        html = html.replace(/<p><br><\/p>/g, '');
        
        // Wrap consecutive li elements in ul
        html = html.replace(/(<li>.*?<\/li>)+/gs, '<ul>$&</ul>');
        
        return html;
    }
    
    // Update preview
    function updatePreview() {
        preview.innerHTML = parseMarkdown(textarea.value);
    }
    
    // Update line info
    function updateLineInfo() {
        const pos = textarea.selectionStart;
        const text = textarea.value.substring(0, pos);
        const lines = text.split('\n');
        const line = lines.length;
        const col = lines[lines.length - 1].length + 1;
        lineInfo.textContent = `行: ${line}, 列: ${col} | 总行数: ${textarea.value.split('\n').length}`;
    }
    
    // Synchronized scrolling
    let isSyncingScroll = false;
    
    function syncScroll(source, target) {
        if (isSyncingScroll) return;
        isSyncingScroll = true;
        
        const sourceScrollRatio = source.scrollTop / (source.scrollHeight - source.clientHeight || 1);
        target.scrollTop = sourceScrollRatio * (target.scrollHeight - target.clientHeight);
        
        setTimeout(() => { isSyncingScroll = false; }, 50);
    }
    
    // Only add event listeners if not already added (check with a flag)
    if (!textarea._listenersAdded) {
        textarea._listenersAdded = true;
        
        textarea.addEventListener('scroll', () => syncScroll(textarea, preview));
        preview.addEventListener('scroll', () => syncScroll(preview, textarea));
        
        // Input handling - don't trigger state update on every keystroke to avoid re-render loop
        textarea.addEventListener('input', () => {
            updatePreview();
            updateLineInfo();
        });
        
        // Only update state on blur (when user finishes editing)
        textarea.addEventListener('blur', () => {
            setStateValue('content', textarea.value);
        });
        
        textarea.addEventListener('keyup', updateLineInfo);
        textarea.addEventListener('click', updateLineInfo);
    }
    
    // Initial render
    updatePreview();
    updateLineInfo();
    
    // Cleanup
    return () => {
        container.remove();
    };
}
"""

# HTML template (minimal, as we build DOM in JS)
EDITOR_HTML = """
<div id="markdown-editor-root"></div>
"""

# Register the component
_markdown_editor_component = st.components.v2.component(
    "markdown_editor_sync",
    html=EDITOR_HTML,
    css=EDITOR_CSS,
    js=EDITOR_JS,
)


def markdown_editor(
    content: str = "",
    key: Optional[str] = None,
    on_change: Optional[callable] = None,
) -> str:
    """
    Render a Markdown editor with synchronized scrolling preview.
    
    Args:
        content: Initial markdown content
        key: Unique key for the component
        on_change: Callback function when content changes
        
    Returns:
        The current content of the editor
    """
    # Mount the component
    result = _markdown_editor_component(
        data={"content": content},
        key=key,
        on_content_change=on_change if on_change else lambda: None,
    )
    
    # Return the current content
    return result.content if result and hasattr(result, 'content') else content
