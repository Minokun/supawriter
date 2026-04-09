'use client';

import { useState, useEffect } from 'react';
import Button from './Button';
import { Copy, Check, Loader2 } from 'lucide-react';
import { historyApi } from '@/types/api';

interface WeChatPreviewProps {
  markdown: string;
  onClose?: () => void;
}

export default function WeChatPreview({ markdown, onClose }: WeChatPreviewProps) {
  const [copied, setCopied] = useState(false);
  const [wechatHtml, setWechatHtml] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // 调用后端 API 转换 Markdown → 微信公众号 HTML
  useEffect(() => {
    if (!markdown) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    historyApi.convertWechat(markdown)
      .then(res => {
        setWechatHtml(res.html);
      })
      .catch(err => {
        console.error('转换失败:', err);
        setError('转换失败，请重试');
      })
      .finally(() => setLoading(false));
  }, [markdown]);

  // 构建完整的预览 HTML（带容器样式）
  const buildPreviewDoc = (htmlBody: string) => `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        body { margin: 0; padding: 20px; background: #fff; }
      </style>
    </head>
    <body>${htmlBody}</body>
    </html>
  `;

  // 一键复制富文本（HTML + 纯文本）
  const handleCopy = async () => {
    if (!wechatHtml) return;
    try {
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/html': new Blob([wechatHtml], { type: 'text/html' }),
          'text/plain': new Blob([markdown], { type: 'text/plain' })
        })
      ]);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // 降级方案：使用 execCommand
      try {
        const iframe = document.createElement('iframe');
        iframe.style.position = 'absolute';
        iframe.style.left = '-9999px';
        document.body.appendChild(iframe);
        const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
        if (iframeDoc) {
          iframeDoc.open();
          iframeDoc.write(wechatHtml);
          iframeDoc.close();
          const range = iframeDoc.createRange();
          range.selectNodeContents(iframeDoc.body);
          const selection = iframe.contentWindow?.getSelection();
          if (selection) {
            selection.removeAllRanges();
            selection.addRange(range);
            document.execCommand('copy');
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          }
        }
        document.body.removeChild(iframe);
      } catch (fallbackErr) {
        console.error('复制失败:', fallbackErr);
        alert('复制失败，请手动复制内容');
      }
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-surface rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b-2 border-border">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📱</span>
            <h2 className="font-heading text-xl font-semibold text-text-primary">
              公众号预览
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant={copied ? 'primary' : 'cta'}
              size="md"
              icon={copied ? <Check size={18} /> : <Copy size={18} />}
              onClick={handleCopy}
              disabled={loading || !!error}
            >
              {copied ? '已复制' : '一键复制'}
            </Button>
            {onClose && (
              <Button variant="secondary" size="md" onClick={onClose}>
                关闭
              </Button>
            )}
          </div>
        </div>

        {/* 预览区域 */}
        <div className="flex-1 overflow-y-auto p-6 bg-bg">
          <div className="max-w-[677px] mx-auto bg-white rounded-lg shadow-standard">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20">
                <Loader2 className="animate-spin text-primary mb-3" size={32} />
                <p className="text-text-secondary text-sm">正在转换公众号格式...</p>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-20">
                <p className="text-red-500 text-sm">{error}</p>
              </div>
            ) : (
              <iframe
                srcDoc={buildPreviewDoc(wechatHtml)}
                className="w-full h-[600px] border-0 rounded-lg"
                title="公众号预览"
                sandbox="allow-same-origin"
              />
            )}
          </div>
        </div>

        {/* 提示信息 */}
        <div className="p-4 bg-bg border-t-2 border-border">
          <p className="text-sm text-text-secondary text-center">
            💡 点击&ldquo;一键复制&rdquo;后，可直接粘贴到微信公众号编辑器，样式会自动保留
          </p>
        </div>
      </div>
    </div>
  );
}
