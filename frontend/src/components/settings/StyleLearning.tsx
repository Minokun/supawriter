'use client';

import { useState, useEffect } from 'react';
import { Upload, FileText, Trash2, Save, Sparkles, X, ChevronDown, ChevronUp, Lock } from 'lucide-react';
import { historyApi, StyleProfile, WritingStyleStatus } from '@/types/api';

const STYLE_DIMENSIONS = [
  { id: 'tone', name: '语气风格', icon: '💬' },
  { id: 'sentence_style', name: '句式偏好', icon: '📝' },
  { id: 'vocabulary', name: '用词特征', icon: '📚' },
  { id: 'paragraph_structure', name: '段落结构', icon: '📄' },
  { id: 'opening_style', name: '开头风格', icon: '🎯' },
  { id: 'closing_style', name: '结尾风格', icon: '🏁' }
];

const LEVEL_COLORS = {
  formal: { bg: 'bg-blue-50', text: 'text-blue-700', label: '正式风格' },
  colloquial: { bg: 'bg-orange-50', text: 'text-orange-700', label: '口语化' },
  emotional: { bg: 'bg-pink-50', text: 'text-pink-700', label: '情感化' },
  neutral: { bg: 'bg-gray-50', text: 'text-gray-700', label: '中性' }
};

interface StyleLearningProps {
  onSave?: (style: StyleProfile) => void;
}

export function StyleLearning({ onSave }: StyleLearningProps) {
  const [style, setStyle] = useState<WritingStyleStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [expandedDimension, setExpandedDimension] = useState<string | null>(null);
  const [expandedCard, setExpandedCard] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  // 加载当前风格
  useEffect(() => {
    loadCurrentStyle();
  }, []);

  const loadCurrentStyle = async () => {
    setLoading(true);
    try {
      const result = await historyApi.getCurrentStyle();
      setStyle(result);
      setExpandedCard(true);
    } catch (error) {
      console.error('Failed to load style:', error);
    } finally {
      setLoading(false);
    }
  };

  // 删除风格
  const handleDeleteStyle = async () => {
    if (confirm('确定要删除您的写作风格吗？')) {
      try {
        await historyApi.deleteStyle();
        setStyle(null);
        setExpandedCard(false);
      } catch (error) {
        console.error('Failed to delete style:', error);
        alert('删除失败，请重试');
      }
    }
  };

  // 上传范文
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadSuccess(false);

    try {
      // 读取文件内容
      const reader = new FileReader();
      reader.onload = async (event) => {
        const content = event.target?.result as string;
        if (!content) return;

        // 分析风格
        const analysis = await historyApi.analyzeStyle(content);
        setStyle({
          has_style: true,
          style_profile: analysis.style_profile,
          sample_filenames: ['uploaded_sample'],
          sample_count: 1,
          is_active: true
        });
        setExpandedCard(true);
        setUploading(false);
        setUploadSuccess(true);

        // 自动保存
        await historyApi.saveWritingStyle(content);

        // 3秒后隐藏成功提示
        setTimeout(() => setUploadSuccess(false), 3000);
      };

      reader.readAsText(file);
    } catch (error) {
      console.error('Failed to upload file:', error);
      alert('上传失败，请重试');
      setUploading(false);
    }
  };

  // 切换风格启用状态
  const handleToggle = async () => {
    if (!style) return;

    const newState = !style.is_active;
    await historyApi.toggleStyle(newState);
    setStyle({ ...style, is_active: newState });
  };

  const getLevelStyle = (styleStr: string) => {
    return LEVEL_COLORS[styleStr as keyof typeof LEVEL_COLORS] || LEVEL_COLORS.neutral;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-10 h-10 border-4 border-t border-gray-200 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-text-primary">
          写作风格学习
        </h2>
        <p className="text-text-secondary">
          上传您的范文，AI将分析您的写作风格并应用到后续文章生成中
        </p>

        {style && (
          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${getLevelStyle(style.style_profile?.tone?.style || 'neutral').bg}`}
            >
              {style.style_profile?.tone?.label || '未设置'}
            </span>
            <button
              onClick={handleToggle}
              className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
                style.is_active
                  ? 'bg-green-100 text-green-700 hover:bg-green-200'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {style.is_active ? '已启用' : '已禁用'}
            </button>
            <button
              onClick={handleDeleteStyle}
              className="text-xs text-red-600 hover:text-red-700 px-3 py-1"
            >
              <X size={16} />
            </button>
          </div>
        )}
      </div>

      {/* 上传范文区域 */}
      <div className="border border-border rounded-xl p-6 bg-white">
        <div className="flex items-center justify-center mb-4">
          <Upload className="w-10 h-10 text-primary mr-4" />
          <div>
            <h3 className="font-medium">上传范文</h3>
            <p className="text-sm text-text-tertiary">
              支持 .md, .txt 格式，建议上传 3-5 篇文章（至少500字）
            </p>
          </div>
        </div>

        {uploadSuccess && (
          <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg flex items-center">
            <Save size={20} className="mr-2" />
            范文分析完成！
          </div>
        )}

        <div className="relative">
          <input
            type="file"
            accept=".md,.txt"
            onChange={handleFileUpload}
            disabled={uploading}
            className="w-full border-2 border-dashed border-gray-300 rounded-lg p-8 text-center focus:outline-none focus:ring-2 focus:border-primary transition-all"
          />
          {uploading && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/80 rounded-lg">
              <div className="w-8 h-8 border-4 border-t border-primary animate-spin" />
            <span className="ml-3 text-primary">正在分析...</span>
            </div>
          )}
        </div>
      </div>

      {/* 风格详情卡片 */}
      {style && expandedCard && (
        <div className="border border-border rounded-xl p-6 bg-white">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-text-primary">
              {'写作风格分析'}
            </h3>
            <button
              onClick={() => setExpandedCard(false)}
              className="text-text-tertiary hover:text-text-primary"
            >
              <ChevronUp size={20} />
            </button>
          </div>

          <div className="space-y-4">
            {/* 6维度分析结果 */}
            {STYLE_DIMENSIONS.map((dimension) => {
              const dimValue = style.style_profile?.[dimension.id as keyof StyleProfile];
              if (!dimValue) return null;

              return (
                <div
                  key={dimension.id}
                  className="border border-border rounded-lg p-4"
                >
                  <button
                    onClick={() => setExpandedDimension(expandedDimension === dimension.id ? null : dimension.id)}
                    className="w-full flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center">
                      <span className="text-2xl mr-2">{dimension.icon}</span>
                      <div>
                        <div className="font-medium">{dimension.name}</div>
                        <div className="text-xs text-text-tertiary">
                          信心: {dimValue.confidence || 70}%
                        </div>
                      </div>
                    </div>
                    {expandedDimension === dimension.id ? (
                      <ChevronUp size={16} />
                    ) : (
                      <ChevronDown size={16} />
                    )}
                  </button>

                  {expandedDimension === dimension.id && (
                    <div className="mt-4 space-y-3">
                      <div className={`p-3 rounded-lg ${getLevelStyle(dimValue.style).bg} ${getLevelStyle(dimValue.style).text}`}>
                        <div className="font-medium text-text-primary">
                          {dimValue.label}
                        </div>
                        <p className="text-sm text-text-tertiary">
                          {dimValue.description || '无描述'}
                        </p>
                        {dimValue.avg_length !== undefined && (
                          <p className="text-xs text-text-tertiary">
                            平均句长: {dimValue.avg_length}字
                          </p>
                        )}
                        {dimValue.richness !== undefined && (
                          <p className="text-xs text-text-tertiary">
                            词汇丰富度: {dimValue.richness}%
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="flex justify-end mt-6">
            <button
              onClick={handleToggle}
              disabled={!style.is_active}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                style.is_active
                  ? 'bg-red-500 text-white hover:bg-red-600'
                  : 'bg-primary text-white hover:bg-primary/90'
              }`}
            >
              {style.is_active ? '禁用风格' : '启用风格'}
            </button>
          </div>
        </div>
      )}

      {/* 无风格时的引导卡片 */}
      {!style && !loading && (
        <div className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-primary to-purple-600 rounded-full flex items-center justify-center">
            <Sparkles size={32} className="text-white" />
          </div>
          <h3 className="font-semibold text-text-primary mb-2">
            还未设置写作风格
          </h3>
          <p className="text-text-secondary mb-6">
            上传范文后，AI将学习您的写作风格
          </p>
          <div className="text-sm text-text-tertiary">
            这将帮助生成更符合您风格的优质内容
          </div>
          <div className="flex items-center justify-center">
            <FileText size={48} className="text-text-tertiary mr-2" />
            <span className="text-primary">点击或拖拽上传范文</span>
          </div>
        </div>
      )}
    </div>
  );
}
