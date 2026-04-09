'use client';

import { useState } from 'react';
import { Check, X, Sparkles, ArrowRight, ArrowLeft, Users, Zap } from 'lucide-react';

const STEPS = [
  {
    id: 'welcome',
    title: '欢迎使用 SupaWriter',
    icon: Sparkles,
    description: '智能AI写作助手，让创作更轻松'
  },
  {
    id: 'role',
    title: '选择您的角色',
    icon: Users,
    description: '帮助我们为您推荐最合适的功能'
  },
  {
    id: 'explore',
    title: '体验核心功能',
    icon: Zap,
    description: '了解AI写作、热点追踪等能力'
  }
];

const USER_ROLES = [
  {
    id: 'media_operator',
    name: '媒体运营',
    icon: '📰',
    description: '管理多个自媒体账号，批量发布内容',
    features: ['多平台发布', '热点追踪', '数据看板']
  },
  {
    id: 'marketer',
    name: '市场营销',
    icon: '📈',
    description: '营销文案创作，SEO优化，转化提升',
    features: ['爆款生成', '评分系统', '关键词分析']
  },
  {
    id: 'freelancer',
    name: '自由职业者',
    icon: '👨‍💼',
    description: '接单创作，灵活接单，提升效率',
    features: ['风格学习', '批量生成', '任务管理']
  },
  {
    id: 'personal_ip',
    name: '个人博主',
    icon: '✍️',
    description: '个人品牌打造，内容创作，粉丝增长',
    features: ['写作助手', '热点挖掘', '个性化推荐']
  }
];

interface OnboardingFlowProps {
  onComplete?: () => void;
  onSkip?: () => void;
  hotspots?: Array<{
    title: string;
    url?: string;
  }>;
}

export function OnboardingFlow({ onComplete, onSkip, hotspots = [] }: OnboardingFlowProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [animateOut, setAnimateOut] = useState(false);
  const [animateIn, setAnimateIn] = useState(true);

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      completeOnboarding();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleRoleSelect = (roleId: string) => {
    setSelectedRole(roleId);
    };

  const handleSkip = () => {
    setAnimateOut(true);
    setTimeout(() => {
      onSkip?.();
    }, 300);
  };

  const completeOnboarding = async () => {
    // 保存用户角色到后端
    if (selectedRole) {
      try {
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
        const response = await fetch('/api/v1/articles/onboarding/complete', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify({ user_role: selectedRole })
        });

        if (response.ok) {
          console.log('Onboarding completed with role:', selectedRole);
        }
      } catch (error) {
        console.error('Failed to complete onboarding:', error);
      }
    }

    // 触发完成
    setAnimateOut(true);
    setTimeout(() => {
      onComplete?.();
    }, 300);
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm transition-all duration-300 ${animateOut ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>
      <div className={`bg-white rounded-2xl shadow-2xl w-full max-w-3xl mx-4 overflow-hidden transition-all duration-300 ${animateIn ? 'scale-100 opacity-100' : animateOut ? 'scale-95 opacity-0' : 'scale-100 opacity-100'}`}>
        {/* 跳过按钮 */}
        <button
          onClick={handleSkip}
          className="absolute top-4 right-4 text-text-tertiary hover:text-text-tertiary/80"
        >
          <X size={20} />
        </button>

        {/* 进度条 */}
        <div className="absolute top-0 left-0 right-0 h-2 bg-gray-200">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{ width: `${((currentStep + 1) / STEPS.length) * 100}%` }}
          />
        </div>

        {/* 内容区域 */}
        <div className="p-12">
          {currentStep === 0 && (
            <Step0Welcome onNext={handleNext} />
          )}

          {currentStep === 1 && (
            <Step1RoleSelect
              selectedRole={selectedRole}
              onRoleSelect={handleRoleSelect}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}

          {currentStep === 2 && (
            <Step2Explore
              hotspots={hotspots}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}

          {currentStep === 3 && (
            <Step3Complete onNext={completeOnboarding} />
          )}
        </div>
      </div>
    </div>
  );
}

// ================== 步骤组件 ==================

function Step0Welcome({ onNext }: { onNext: () => void }) {
  return (
    <div className="text-center py-12">
      <div className="w-24 h-24 mx-auto mb-8 bg-gradient-to-br from-primary to-purple-600 rounded-full flex items-center justify-center">
        <Sparkles size={48} className="text-white" />
      </div>

      <h1 className="text-3xl font-bold text-text-primary mb-4">
        欢迎使用 SupaWriter
      </h1>

      <p className="text-lg text-text-secondary mb-8 max-w-md mx-auto">
        您的智能AI写作助手
      </p>

      <p className="text-base text-text-secondary mb-12">
        让创作更轻松，让爆款文章源源不断
      </p>

      <button
        onClick={onNext}
        className="px-8 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-all shadow-lg"
      >
        开始体验
        <ArrowRight className="inline-block ml-2" size={20} />
      </button>
    </div>
  );
}

function Step1RoleSelect({
  selectedRole,
  onRoleSelect,
  onNext,
  onBack
}: {
  selectedRole: string | null;
  onRoleSelect: (roleId: string) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <div className="text-center py-12">
      <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-full flex items-center justify-center">
        <Users size={40} className="text-white" />
      </div>

      <h2 className="text-2xl font-bold text-text-primary mb-3">
        选择您的角色
      </h2>

      <p className="text-base text-text-secondary mb-8">
        这将帮助我们推荐最适合您的功能
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        {USER_ROLES.map((role) => (
          <button
            key={role.id}
            onClick={() => onRoleSelect(role.id)}
            className={`p-6 rounded-xl border-2 transition-all ${
              selectedRole === role.id
                ? 'border-primary bg-primary/5 ring-4 ring-primary/20'
                : 'border-gray-200 hover:border-primary/50 hover:bg-gray-50'
            }`}
          >
            <div className="text-4xl mb-3">{role.icon}</div>
            <div className="text-lg font-medium text-text-primary mb-2">
              {role.name}
            </div>
            <p className="text-sm text-text-secondary">
              {role.description}
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {role.features.slice(0, 3).map((feature) => (
                <span
                  key={feature}
                  className="px-2 py-1 bg-gray-100 rounded-full text-xs text-text-tertiary"
                >
                  {feature}
                </span>
              ))}
              {role.features.length > 3 && (
                <span className="px-2 py-1 bg-gray-100 rounded-full text-xs text-text-tertiary">
                  ...
                </span>
              )}
            </div>
          </button>
        ))}
      </div>

      <div className="flex justify-between mt-8">
        <button
          onClick={onBack}
          className="px-6 py-2 text-text-tertiary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="inline-block mr-2" size={20} />
          返回
        </button>

        <button
          onClick={onNext}
          disabled={!selectedRole}
          className={`px-8 py-3 rounded-lg font-medium transition-all ${
            selectedRole
              ? 'bg-primary text-white hover:bg-primary/90 shadow-lg'
              : 'bg-gray-300 text-text-tertiary cursor-not-allowed'
          }`}
        >
          下一步
          <ArrowRight className="inline-block ml-2" size={20} />
        </button>
      </div>
    </div>
  );
}

function Step2Explore({
  hotspots,
  onNext,
  onBack
}: {
  hotspots?: Array<{ title: string; url?: string }>;
  onNext: () => void;
  onBack: () => void;
}) {
  const displayHotspots = hotspots && hotspots.length > 0 ? hotspots.slice(0, 4) : [];

  return (
    <div className="text-center py-12">
      <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
        <Zap size={40} className="text-white" />
      </div>

      <h2 className="text-2xl font-bold text-text-primary mb-3">
        体验核心功能
      </h2>

      <p className="text-base text-text-secondary mb-8">
        看看这些功能，开始您的创作之旅
      </p>

      {/* 热点展示 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        {displayHotspots.map((hotspot, index) => (
          <div
            key={index}
            className="p-4 bg-gradient-to-br from-orange-50 to-red-500 rounded-lg hover:shadow-lg transition-all cursor-pointer group"
          >
            <div className="mb-2">
              <span className="text-xs text-white/80">🔥 热点</span>
            </div>
            <div className="text-base font-medium text-white mb-1">
              {hotspot.title.length > 20 ? hotspot.title.substring(0, 18) + '...' : hotspot.title}
            </div>
            <p className="text-sm text-white/90">
              点击查看详情并开始创作
            </p>
            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <ArrowRight size={16} className="text-white" />
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-between mt-8">
        <button
          onClick={onBack}
          className="px-6 py-2 text-text-tertiary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="inline-block mr-2" size={20} />
          返回
        </button>

        <button
          onClick={onNext}
          className="px-8 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 shadow-lg"
        >
          下一步
          <ArrowRight className="inline-block ml-2" size={20} />
        </button>
      </div>
    </div>
  );
}

function Step3Complete({ onNext }: { onNext: () => void }) {
  return (
    <div className="text-center py-12">
      <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-green-500 to-emerald-500 rounded-full flex items-center justify-center">
        <Check size={40} className="text-white" />
      </div>

      <h2 className="text-2xl font-bold text-text-primary mb-3">
        准备就绪！
      </h2>

      <p className="text-base text-text-secondary mb-8 max-w-md mx-auto">
        现在您可以开始使用所有功能了
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <FeatureCard
          icon="✍️"
          title="AI写作"
          description="智能文章生成"
        />
        <FeatureCard
          icon="📈"
          title="热点追踪"
          description="实时热点推荐"
        />
        <FeatureCard
          icon="📊"
          title="质量评分"
          description="优化文章质量"
        />
      </div>

      <button
        onClick={onNext}
        className="w-full md:col-span-3 px-8 py-4 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 shadow-lg"
      >
        开始创作
        <Sparkles className="inline-block ml-2" size={20} />
      </button>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div className="p-6 bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg hover:shadow-lg transition-all">
      <div className="text-3xl mb-2">{icon}</div>
      <div className="text-base font-medium text-text-primary">{title}</div>
      <p className="text-sm text-text-secondary">{description}</p>
    </div>
  );
}
