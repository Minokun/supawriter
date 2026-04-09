'use client';

import { useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import { Brain, Newspaper, ScrollText } from 'lucide-react';
import { IntelligentMode } from './components/IntelligentMode';
import { ManualMode } from './components/ManualMode';
import { HistoryView } from './components/HistoryView';

type TabType = 'intelligent' | 'manual' | 'history';

const tabs = [
  { id: 'intelligent' as TabType, label: '智能模式', icon: Brain, description: 'AI筛选新闻生成选题' },
  { id: 'manual' as TabType, label: '手动模式', icon: Newspaper, description: '选择新闻源生成选题' },
  { id: 'history' as TabType, label: '历史记录', icon: ScrollText, description: '查看历史生成记录' },
];

export default function TweetTopicsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('intelligent');

  const activeTabData = tabs.find(t => t.id === activeTab);
  const ActiveIcon = activeTabData?.icon || Brain;

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in duration-500">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
          <div>
            <div className="flex items-center gap-4 mb-2">
              <div className="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center">
                <span className="text-2xl">💡</span>
              </div>
              <h1 className="font-heading text-4xl font-bold text-text-primary tracking-tight">
                推文选题
              </h1>
            </div>
            <p className="font-body text-lg text-text-secondary max-w-2xl">
              基于热点新闻，AI 生成优质推文选题灵感
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white rounded-2xl shadow-standard p-2 mb-8 flex gap-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium transition-all duration-200 ${
                  activeTab === tab.id
                    ? 'bg-primary text-white shadow-md'
                    : 'text-text-secondary hover:bg-bg hover:text-text-primary'
                }`}
              >
                <Icon size={20} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
          {activeTab === 'intelligent' && <IntelligentMode />}
          {activeTab === 'manual' && <ManualMode />}
          {activeTab === 'history' && <HistoryView />}
        </div>
      </div>
    </MainLayout>
  );
}
