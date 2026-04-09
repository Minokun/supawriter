'use client';

import { Cpu, Settings as SettingsIcon, Sparkles, Crown } from 'lucide-react';

export type SettingsTab = 'llm' | 'services' | 'models' | 'preferences' | 'style' | 'subscription';

interface SettingsTabsProps {
  activeTab: SettingsTab;
  isAdmin: boolean;
  onChange: (tab: SettingsTab) => void;
}

export function SettingsTabs({ activeTab, isAdmin, onChange }: SettingsTabsProps) {
  const getTabClassName = (tab: SettingsTab) => `flex items-center gap-2 h-10 px-5 rounded-lg font-body text-[15px] font-semibold transition-all ${
    activeTab === tab
      ? 'bg-primary text-white'
      : 'bg-transparent border-[1.5px] border-border text-text-secondary hover:border-primary'
  }`;

  return (
    <div className="flex gap-2 mb-6">
      {isAdmin && (
        <>
          <button onClick={() => onChange('llm')} className={getTabClassName('llm')}>
            <Cpu size={18} />
            LLM 提供商
          </button>
          <button onClick={() => onChange('services')} className={getTabClassName('services')}>
            <SettingsIcon size={18} />
            其他服务
          </button>
        </>
      )}

      <button onClick={() => onChange('models')} className={getTabClassName('models')}>
        <Cpu size={18} />
        模型配置
      </button>
      <button onClick={() => onChange('preferences')} className={getTabClassName('preferences')}>
        <SettingsIcon size={18} />
        个人偏好
      </button>
      <button onClick={() => onChange('style')} className={getTabClassName('style')}>
        <Sparkles size={18} />
        风格学习
      </button>
      <button onClick={() => onChange('subscription')} className={getTabClassName('subscription')}>
        <Crown size={18} />
        订阅管理
      </button>
    </div>
  );
}
