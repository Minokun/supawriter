'use client';

import * as Novel from 'novel';
import { useEffect, useState, useRef, forwardRef, useImperativeHandle } from 'react';
import { Markdown } from 'tiptap-markdown';
import { NodeViewWrapper, ReactNodeViewRenderer } from '@tiptap/react';
import { Node, textblockTypeInputRule } from '@tiptap/core';
import mermaid from 'mermaid';

// Initialize Mermaid
if (typeof window !== 'undefined') {
  mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    fontFamily: 'Nunito, sans-serif',
    flowchart: { htmlLabels: true, useMaxWidth: true },
  });
}

// Mermaid Component for Tiptap
const MermaidComponent = ({ node }: any) => {
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string>('');
  const isMounted = useRef(true);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    isMounted.current = true;
    const renderMermaid = async () => {
      const content = node.attrs.content;
      if (!content || !content.trim()) return;
      
      try {
        const cleanContent = content.trim();
        // Mermaid requires a unique ID for each render
        const id = `mermaid-svg-${Math.random().toString(36).substr(2, 9)}`;
        
        // Clean up previous SVG before rendering new one
        if (isMounted.current) {
            const { svg: renderedSvg } = await mermaid.render(id, cleanContent);
            if (isMounted.current) {
              setSvg(renderedSvg);
              setError('');
            }
        }
      } catch (err: any) {
        console.error('Mermaid render error:', err);
        if (isMounted.current) {
          // If error is just a string, use it, otherwise generic message
          const msg = typeof err === 'string' ? err : 'Mermaid 语法错误';
          setError(msg);
        }
      }
    };

    // Use a small timeout to ensure DOM is ready and prevent race conditions with Tiptap rendering
    const timer = setTimeout(renderMermaid, 100);
    return () => { 
        isMounted.current = false;
        clearTimeout(timer);
    };
  }, [node.attrs.content]);

  return (
    <NodeViewWrapper className="mermaid-wrapper my-8 flex flex-col items-center">
      {error ? (
        <div className="w-full p-4 bg-error/5 border border-error/20 rounded-xl text-error text-xs font-mono">
          <p className="font-bold mb-2">⚠️ {error}</p>
          <pre className="opacity-70 overflow-x-auto p-2 bg-white/50 rounded">{node.attrs.content}</pre>
        </div>
      ) : svg ? (
        <div 
          className="mermaid-container w-full bg-white p-6 rounded-xl border border-border shadow-sm flex justify-center overflow-x-auto"
          dangerouslySetInnerHTML={{ __html: svg }} 
        />
      ) : (
        <div className="mermaid-loading w-full h-32 flex items-center justify-center bg-bg rounded-xl border border-dashed border-border animate-pulse text-text-tertiary text-sm">
          正在生成图表...
        </div>
      )}
    </NodeViewWrapper>
  );
};

// Custom Mermaid Extension
const MermaidExtension = Node.create({
  name: 'mermaid',
  group: 'block',
  atom: true,
  draggable: true,

  addAttributes() {
    return {
      content: {
        default: '',
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div.mermaid',
        getAttrs: (node: any) => ({ content: node.textContent }),
      },
      {
        tag: 'pre.mermaid',
        getAttrs: (node: any) => ({ content: node.textContent }),
      },
      {
        tag: 'pre',
        getAttrs: (node: any) => {
          const code = node.querySelector('code');
          if (code && code.classList.contains('language-mermaid')) {
            return { content: code.textContent };
          }
          if (node.classList.contains('mermaid')) {
            return { content: node.textContent };
          }
          // Special case for some markdown parsers
          if (node.innerText?.trim().startsWith('flowchart') || node.innerText?.trim().startsWith('graph ')) {
             // Caution: this might be too aggressive if not careful, but useful for debugging
          }
          return false;
        },
        priority: 1100,
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { class: 'mermaid' }, HTMLAttributes.content];
  },

  addNodeView() {
    return ReactNodeViewRenderer(MermaidComponent);
  },

  addInputRules() {
    return [
      textblockTypeInputRule({
        find: /^\s*```mermaid\s*$/,
        type: this.type,
      }),
    ];
  },
});

// Extract components with fallbacks
const EditorRoot = Novel.EditorRoot;
const EditorContent = Novel.EditorContent;
const StarterKit = Novel.StarterKit;
const Mathematics = (Novel as any).Mathematics;
const TiptapImage = (Novel as any).UpdatedImage || (Novel as any).TiptapImage;

interface NovelEditorProps {
  content: string;
  readOnly?: boolean;
  className?: string;
  onUpdate?: (content: string) => void;
}

const NovelEditor = forwardRef<any, NovelEditorProps>(({ content, readOnly = false, className, onUpdate }, ref) => {
  const [editorInstance, setEditorInstance] = useState<any | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useImperativeHandle(ref, () => ({
    getEditor: () => editorInstance,
    getContainer: () => containerRef.current,
  }));

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Update content when prop changes
  useEffect(() => {
    if (editorInstance && content !== undefined) {
      try {
        const currentMarkdown = editorInstance.storage?.markdown?.getMarkdown?.();
        if (currentMarkdown !== content) {
          editorInstance.commands.setContent(content, false);
        }
      } catch (e) {
        editorInstance.commands.setContent(content, false);
      }
      editorInstance.setEditable(!readOnly);
    }
  }, [content, editorInstance, readOnly]);

  if (!isMounted) {
    return null;
  }

  if (!EditorRoot || !EditorContent) {
    return (
      <div className="p-4 border border-error rounded-lg bg-error/5 text-error">
        编辑器加载失败，请检查组件库导出。
      </div>
    );
  }

  // Extensions list
  const extensions = [
    StarterKit.configure({
        codeBlock: {
            HTMLAttributes: {
                class: 'rounded-xl bg-slate-900 text-slate-100 p-6 font-mono text-sm leading-relaxed shadow-lg my-6',
            }
        }
    }), 
    Markdown.configure({
        html: true,
        tightLists: true,
        tightListClass: 'tight',
    }),
    MermaidExtension,
  ];

  if (TiptapImage) {
    extensions.push(
      TiptapImage.configure({
        allowBase64: true,
        HTMLAttributes: {
          class: 'rounded-lg max-w-full h-auto my-4 mx-auto block',
        },
      })
    );
  }

  if (Mathematics) {
    extensions.push(Mathematics);
  }

  return (
    <div 
      className={`novel-editor-container ${className || ''} ${readOnly ? 'read-only' : ''}`}
      ref={containerRef}
    >
      <EditorRoot>
        <EditorContent
          initialContent={content as any}
          extensions={extensions as any}
          editorProps={{
            attributes: {
              class: `prose prose-lg focus:outline-none max-w-full text-text-primary`,
            },
          }}
          onUpdate={({ editor }) => {
            if (onUpdate) {
              const markdown = editor.storage.markdown.getMarkdown();
              onUpdate(markdown);
            }
          }}
          // @ts-ignore
          onReady={({ editor }) => {
            setEditorInstance(editor);
          }}
        />
      </EditorRoot>
    </div>
  );
});

NovelEditor.displayName = 'NovelEditor';
export default NovelEditor;