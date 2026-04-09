'use client';

import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import { Check } from 'lucide-react';

interface UserPreferences {
  editor_theme?: string;
  language?: string;
  auto_save?: boolean;
  notifications_enabled?: boolean;
}

interface PreferencesSettingsProps {
  preferences: UserPreferences;
  saveSuccess: boolean;
  onChange: (preferences: UserPreferences) => void;
  onSave: () => void;
}

export function PreferencesSettings({ preferences, saveSuccess, onChange, onSave }: PreferencesSettingsProps) {
  return (
    <Card padding="xl">
      <div className="space-y-6">
        <div>
          <label className="block font-body text-sm font-medium text-text-primary mb-2">
            编辑器主题
          </label>
          <select
            value={preferences.editor_theme}
            onChange={(e) => onChange({ ...preferences, editor_theme: e.target.value })}
            className="w-full h-12 px-4 bg-surface border-[1.5px] border-border rounded-lg font-body text-[15px] text-text-primary focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10 transition-all"
          >
            <option value="light">浅色</option>
            <option value="dark">深色</option>
            <option value="auto">跟随系统</option>
          </select>
        </div>

        <div>
          <label className="block font-body text-sm font-medium text-text-primary mb-2">
            语言
          </label>
          <select
            value={preferences.language}
            onChange={(e) => onChange({ ...preferences, language: e.target.value })}
            className="w-full h-12 px-4 bg-surface border-[1.5px] border-border rounded-lg font-body text-[15px] text-text-primary focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10 transition-all"
          >
            <option value="zh-CN">简体中文</option>
            <option value="en-US">English</option>
          </select>
        </div>

        <div className="flex items-center justify-between p-4 bg-bg rounded-lg">
          <div>
            <p className="font-body text-base font-semibold text-text-primary">自动保存</p>
            <p className="text-sm text-text-secondary">编辑时自动保存草稿</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.auto_save}
              onChange={(e) => onChange({ ...preferences, auto_save: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
          </label>
        </div>

        <div className="flex items-center justify-between p-4 bg-bg rounded-lg">
          <div>
            <p className="font-body text-base font-semibold text-text-primary">通知</p>
            <p className="text-sm text-text-secondary">接收系统通知</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.notifications_enabled}
              onChange={(e) => onChange({ ...preferences, notifications_enabled: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
          </label>
        </div>

        <Button
          variant={saveSuccess ? 'secondary' : 'primary'}
          size="lg"
          onClick={onSave}
          className={`w-full ${saveSuccess ? 'bg-green-500 text-white border-green-500 hover:bg-green-600' : ''}`}
          disabled={saveSuccess}
        >
          {saveSuccess ? (
            <>
              <Check size={18} />
              已保存
            </>
          ) : '保存偏好设置'}
        </Button>
      </div>
    </Card>
  );
}
