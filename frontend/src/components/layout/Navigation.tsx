'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useRef, useEffect, useCallback } from 'react';
import { signOut } from 'next-auth/react';
import clsx from 'clsx';
import { User, Settings, LogOut, Edit, Loader2, Shield, LayoutDashboard } from 'lucide-react';
import NotificationCenter from '@/components/notifications/NotificationCenter';
import { userApi, checkUserQuota } from '@/lib/api';
import { resolveUserAvatar } from '@/lib/auth-avatar';
import { useSharedAuth } from '@/contexts/AuthContext';
import { useModelConfig } from '@/contexts/ModelConfigContext';
import { clearBackendAuth } from '@/lib/backend-auth-storage';
import type { MembershipTier } from '@/types/api';

// 导航菜单配置 - 支持子菜单
interface NavItem {
  name: string;
  path?: string;
  icon?: string;
  children?: { name: string; path: string; icon?: string }[];
}

const navItems: NavItem[] = [
  { name: 'AI 导航', path: '/ai-navigator', icon: '🧭' },
  { name: 'AI 助手', path: '/ai-assistant', icon: '🤖' },
  {
    name: '创作中心',
    icon: '✨',
    children: [
      { name: '文章创作', path: '/writer', icon: '✍️' },
      { name: '批量生成', path: '/batch', icon: '📦' },
      { name: '推文选题', path: '/tweet-topics', icon: '💡' },
      { name: '历史记录', path: '/history', icon: '📚' },
    ],
  },
  {
    name: '热点资讯',
    icon: '🔥',
    children: [
      { name: '热点中心', path: '/hotspots', icon: '🔥' },
      { name: '新闻资讯', path: '/news', icon: '📰' },
      { name: '全网热点', path: '/inspiration', icon: '💡' },
    ],
  },
  { name: '我的套餐', path: '/pricing', icon: '💎' },
];

const guestNavItems: NavItem[] = [
  {
    name: '热点资讯',
    icon: '🔥',
    children: [
      { name: '热点中心', path: '/hotspots', icon: '🔥' },
      { name: '新闻资讯', path: '/news', icon: '📰' },
      { name: '全网热点', path: '/inspiration', icon: '💡' },
    ],
  },
  { name: '我的套餐', path: '/pricing', icon: '💎' },
];

// 会员等级配置
const TIER_CONFIG: Record<MembershipTier, {
  label: string;
  bgColor: string;
  textColor: string;
  benefits: string[];
  quota: string;
  price: string;
}> = {
  free: {
    label: 'Free会员',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    quota: '5篇/月',
    price: '免费',
    benefits: [
      '每月5篇文章生成额度',
      '基础AI模型访问',
      '历史记录保存7天',
      '社区基础功能',
    ],
  },
  pro: {
    label: 'Pro会员',
    bgColor: 'bg-blue-500',
    textColor: 'text-white',
    quota: '20篇/月',
    price: '¥29.9/月',
    benefits: [
      '每月20篇文章生成额度',
      '中级AI模型访问',
      '历史记录永久保存',
      '优先客服支持',
      '高级写作模板',
    ],
  },
  ultra: {
    label: 'Ultra会员',
    bgColor: 'bg-gradient-to-r from-purple-500 to-pink-500',
    textColor: 'text-white',
    quota: '60篇/月',
    price: '¥59.9/月',
    benefits: [
      '每月60篇文章生成额度',
      '全部AI模型访问',
      '历史记录永久保存',
      '专属客服通道',
      '高级写作模板',
      'API接口访问',
      '优先体验新功能',
    ],
  },
  superuser: {
    label: '超级管理员',
    bgColor: 'bg-gradient-to-r from-red-500 to-orange-500',
    textColor: 'text-white',
    quota: '无限',
    price: '系统内置',
    benefits: [
      '无限文章生成额度',
      '全部AI模型访问',
      '历史记录永久保存',
      '系统管理权限',
      '用户管理权限',
      '全局配置权限',
      '所有功能无限制',
    ],
  },
};

export default function Navigation() {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isAdmin, membershipTier, userInfo, session } = useSharedAuth();
  const { config: modelConfig } = useModelConfig();
  const [mounted, setMounted] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showMembershipModal, setShowMembershipModal] = useState(false);
  const [quotaInfo, setQuotaInfo] = useState<{ used: number; limit: number; remaining: number; allowed: boolean } | null>(null);
  const [showProfileEdit, setShowProfileEdit] = useState(false);
  const [openSubmenu, setOpenSubmenu] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [navigating, setNavigating] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const menuRef = useRef<HTMLDivElement>(null);
  const itemsRef = useRef<Record<string, HTMLDivElement | null>>({});

  const authReady = mounted && isAuthenticated;
  const visibleNavItems = authReady ? navItems : guestNavItems;

  useEffect(() => {
    setMounted(true);
  }, []);

  const user = {
    name: userInfo?.display_name || userInfo?.username || '用户',
    email: userInfo?.email || '未绑定邮箱',
    avatar: resolveUserAvatar({
      backendAvatar: userInfo?.avatar,
      sessionAvatar: session?.user?.image,
    }),
  };

  const [editUser, setEditUser] = useState(user);

  // 监听路由变化，清除导航状态
  useEffect(() => {
    setNavigating(null);
  }, [pathname]);

  // 获取配额信息（当弹窗打开时）
  useEffect(() => {
    if (showMembershipModal && !isAdmin) {
      checkUserQuota()
        .then((data) => {
          setQuotaInfo({
            used: data.used,
            limit: data.limit,
            remaining: data.remaining,
            allowed: data.allowed,
          });
        })
        .catch((err) => {
          console.error('获取配额信息失败:', err);
        });
    }
  }, [showMembershipModal, isAdmin]);

  // 点击外部关闭菜单
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
      if (openSubmenu && itemsRef.current[openSubmenu] && !itemsRef.current[openSubmenu]?.contains(event.target as Node)) {
        setOpenSubmenu(null);
      }
    }
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [openSubmenu]);

  const handleLogout = async () => {
    clearBackendAuth();
    localStorage.removeItem('userInfoCache');
    await signOut({ callbackUrl: '/auth/signin' });
  };

  useEffect(() => {
    if (isAuthenticated) {
      const validAvatar = (user.avatar && typeof user.avatar === 'string' && user.avatar.trim() !== '')
        ? user.avatar
        : null;
      setEditUser({
        name: user.name,
        email: user.email,
        avatar: validAvatar,
      });
    }
  }, [isAuthenticated, user.avatar, user.email, user.name]);

  // 格式化模型名称显示
  const formatModelName = (model: string) => {
    // 如果格式是 "provider:model_name"，只显示模型名称部分
    if (model.includes(':')) {
      const parts = model.split(':');
      return parts[parts.length - 1];
    }
    return model;
  };

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-50 h-[72px] bg-surface border-b-2 border-border">
        <div className="h-full px-8 flex items-center justify-between">
          {/* Logo and Brand */}
          <Link href={authReady ? '/workspace' : '/'} className="flex items-center gap-3">
            <span className="text-[32px]">🚀</span>
            <h1 className="font-heading text-[20px] font-semibold text-text-primary">
              超能写
            </h1>
          </Link>

          {/* Navigation Menu */}
          <div className="flex items-center gap-6">
            {visibleNavItems.map((item) => {
              // 如果有子菜单
              if (item.children) {
                const isActive = item.children.some(child => pathname?.startsWith(child.path));
                const isOpen = openSubmenu === item.name;
                
                return (
                  <div key={item.name} className="relative" ref={(el) => { itemsRef.current[item.name] = el; }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenSubmenu(isOpen ? null : item.name);
                      }}
                      className={clsx(
                        'flex items-center gap-2 font-body text-[15px] font-medium transition-colors',
                        isActive
                          ? 'text-primary'
                          : 'text-text-secondary hover:text-text-primary'
                      )}
                    >
                      <span>{item.icon}</span>
                      {item.name}
                      <svg
                        className={clsx('w-4 h-4 transition-transform', isOpen && 'rotate-180')}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    
                    {/* 子菜单下拉 - 添加动画 */}
                    {isOpen && (
                      <div className="absolute top-full left-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-border py-2 z-[60] animate-in fade-in slide-in-from-top-2 duration-200">
                        {item.children.map((child, index) => {
                          const childActive = pathname?.startsWith(child.path);
                          const isLoading = navigating === child.path;
                          return (
                            <Link
                              key={child.path}
                              href={child.path}
                              prefetch={true}
                              onClick={(e) => {
                                e.stopPropagation();
                                setNavigating(child.path);
                                setOpenSubmenu(null);
                              }}
                              className={clsx(
                                'flex items-center gap-3 px-4 py-2.5 font-body text-[14px] transition-all duration-200',
                                // 依次淡入效果
                                'animate-in fade-in slide-in-from-left-2',
                                isLoading && 'opacity-60',
                                // 延迟计算
                                childActive
                                  ? 'text-primary bg-primary/5'
                                  : 'text-text-secondary hover:text-text-primary hover:bg-bg'
                              )}
                              style={{ animationDelay: `${index * 50}ms` }}
                            >
                              {isLoading ? (
                                <Loader2 className="animate-spin" size={14} />
                              ) : (
                                <span className="text-lg transition-transform duration-200 group-hover:scale-110">{child.icon}</span>
                              )}
                              {child.name}
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              }
              
              // 普通菜单项
              const isActive = pathname?.startsWith(item.path!);
              const isLoading = navigating === item.path;
              return (
                <Link
                  key={item.path}
                  href={item.path!}
                  prefetch={true}
                  onClick={() => setNavigating(item.path!)}
                  className={clsx(
                    'flex items-center gap-2 font-body text-[15px] font-medium transition-colors',
                    isLoading && 'opacity-60',
                    isActive
                      ? 'text-primary'
                      : 'text-text-secondary hover:text-text-primary'
                  )}
                >
                  {isLoading ? (
                    <Loader2 className="animate-spin" size={16} />
                  ) : (
                    <span>{item.icon}</span>
                  )}
                  {item.name}
                </Link>
              );
            })}
          </div>

          {/* Right Section */}
          <div className="flex items-center gap-4">
            {authReady ? (
              <>
                <NotificationCenter />

                {isAdmin ? (
                  <div className="h-8 px-4 bg-gradient-to-r from-amber-500 to-orange-500 rounded-lg flex items-center justify-center gap-2 shadow-md cursor-default">
                    <Shield size={14} className="text-white" />
                    <span className="font-body text-sm font-semibold text-white">超级管理员</span>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowMembershipModal(true)}
                    className={clsx(
                      'h-8 px-4 rounded-lg flex items-center justify-center cursor-pointer transition-all hover:opacity-90 hover:scale-105',
                      TIER_CONFIG[membershipTier].bgColor
                    )}
                  >
                    <span className={clsx('font-body text-sm font-semibold', TIER_CONFIG[membershipTier].textColor)}>
                      {TIER_CONFIG[membershipTier].label}
                    </span>
                  </button>
                )}

                <div className="relative" ref={menuRef}>
                  <button
                    onClick={() => {
                      setShowUserMenu(!showUserMenu);
                      const avatar = document.getElementById('user-avatar');
                      avatar?.classList.add('animate-bounce-in');
                      setTimeout(() => avatar?.classList.remove('animate-bounce-in'), 300);
                    }}
                    id="user-avatar"
                    className="w-8 h-8 bg-secondary rounded-full flex items-center justify-center cursor-pointer transition-all duration-200 hover:scale-110 hover:shadow-lg hover:shadow-secondary/50 active:scale-95"
                  >
                    {user.avatar ? (
                      <img
                        src={user.avatar}
                        alt={user.name}
                        className="w-full h-full rounded-full object-cover"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                          const parent = e.currentTarget.parentElement;
                          if (parent) {
                            const fallback = parent.querySelector('span');
                            if (fallback) fallback.style.display = 'block';
                          }
                        }}
                      />
                    ) : null}
                    <span className="text-white text-sm" style={{ display: user.avatar ? 'none' : 'block' }}>👤</span>
                  </button>

                  {showUserMenu && (
                    <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-border py-2 animate-in fade-in zoom-in-95 duration-200">
                      <div className="px-4 py-3 border-b border-border">
                        <p className="text-sm font-semibold text-text-primary">{user.name}</p>
                        <p className="text-xs text-text-secondary">{user.email}</p>
                      </div>

                      <button
                        onClick={() => {
                          setShowProfileEdit(true);
                          setShowUserMenu(false);
                        }}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-text-secondary hover:text-text-primary hover:bg-bg transition-all duration-200 text-left hover:translate-x-1"
                      >
                        <User size={18} className="transition-transform duration-200 group-hover:scale-110" />
                        个人信息
                      </button>

                      <button
                        onClick={() => {
                          setShowUserMenu(false);
                          router.push('/account');
                        }}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-text-secondary hover:text-text-primary hover:bg-bg transition-all duration-200 text-left hover:translate-x-1"
                      >
                        <Settings size={18} className="transition-transform duration-200 group-hover:scale-110" />
                        账号管理
                      </button>

                      <button
                        onClick={() => {
                          setShowUserMenu(false);
                          router.push('/settings');
                        }}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-text-secondary hover:text-text-primary hover:bg-bg transition-all duration-200 text-left hover:translate-x-1"
                      >
                        <Settings size={18} className="transition-transform duration-200 group-hover:scale-110" />
                        系统设置
                      </button>

                      <button
                        onClick={handleLogout}
                        className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 border-t border-border mt-2 transition-all duration-200 hover:translate-x-1"
                      >
                        <LogOut className="w-4 h-4 transition-transform duration-200 group-hover:scale-110" />
                        退出登录
                      </button>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                <Link
                  href="/auth/signin"
                  className="font-body text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
                >
                  登录
                </Link>
                <Link
                  href="/auth/register"
                  className="h-9 px-4 rounded-lg bg-primary text-white font-body text-sm font-semibold flex items-center justify-center hover:bg-primary-dark transition-colors"
                >
                  注册
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Profile Edit Modal - 添加动画 */}
      {showProfileEdit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity duration-300 animate-in fade-in"
            onClick={() => setShowProfileEdit(false)}
          />
          {/* Modal */}
          <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md p-6 animate-in fade-in zoom-in-95 duration-300">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-text-primary">编辑个人信息</h2>
              <button
                onClick={() => setShowProfileEdit(false)}
                className="text-text-secondary hover:text-text-primary transition-all duration-200 hover:rotate-90 hover:scale-110"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              {/* Avatar */}
              <div className="flex flex-col items-center gap-4">
                <div className="w-20 h-20 bg-secondary rounded-full flex items-center justify-center overflow-hidden relative">
                  {user.avatar ? (
                    <img
                      src={user.avatar}
                      alt={user.name}
                      className="w-full h-full rounded-full object-cover"
                      onError={(e) => {
                        // 图片加载失败时隐藏并显示默认头像
                        e.currentTarget.style.display = 'none';
                        const parent = e.currentTarget.parentElement;
                        if (parent) {
                          const fallback = parent.querySelector('svg');
                          if (fallback) fallback.style.display = 'block';
                        }
                      }}
                    />
                  ) : null}
                  <User className="w-10 h-10 text-white" style={{ display: user.avatar ? 'none' : 'block' }} />
                  {isUploading && (
                    <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                      <Loader2 className="w-6 h-6 text-white animate-spin" />
                    </div>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/gif,image/webp"
                  className="hidden"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;

                    // 验证文件大小 (5MB)
                    if (file.size > 5 * 1024 * 1024) {
                      setUploadError('文件大小不能超过 5MB');
                      return;
                    }

                    // 验证文件类型
                    if (!file.type.startsWith('image/')) {
                      setUploadError('请选择图片文件');
                      return;
                    }

                    setIsUploading(true);
                    setUploadError(null);

                    try {
                      const result = await userApi.uploadAvatar(file);
                      // 更新本地用户信息
                      setEditUser({ ...editUser, avatar: result.avatar_url });
                      // 更新 session (通过刷新页面或重新获取 token)
                      window.location.reload();
                    } catch (err: any) {
                      setUploadError(err.response?.data?.detail || '上传失败，请重试');
                    } finally {
                      setIsUploading(false);
                      // 清空文件输入
                      if (fileInputRef.current) {
                        fileInputRef.current.value = '';
                      }
                    }
                  }}
                />
                <button
                  className="text-sm text-primary hover:underline disabled:opacity-50"
                  disabled={isUploading}
                  onClick={() => fileInputRef.current?.click()}
                >
                  {isUploading ? '上传中...' : '更换头像'}
                </button>
                {uploadError && (
                  <p className="text-xs text-red-500">{uploadError}</p>
                )}
              </div>

              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  昵称
                </label>
                <input
                  type="text"
                  value={editUser.name}
                  onChange={(e) => setEditUser({ ...editUser, name: e.target.value })}
                  className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  邮箱
                </label>
                <input
                  type="email"
                  value={editUser.email}
                  onChange={(e) => setEditUser({ ...editUser, email: e.target.value })}
                  className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  disabled
                />
                <p className="text-xs text-text-tertiary mt-1">邮箱无法修改</p>
              </div>

              {/* Buttons */}
              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => {
                    setShowProfileEdit(false);
                    setUploadError(null);
                  }}
                  className="flex-1 px-4 py-2 border border-border rounded-lg text-text-primary hover:bg-bg"
                  disabled={isUploading}
                >
                  取消
                </button>
                <button
                  onClick={async () => {
                    setIsUploading(true);
                    try {
                      await userApi.updateProfile({
                        display_name: editUser.name,
                      });
                      setShowProfileEdit(false);
                      setUploadError(null);
                      // 刷新页面以更新显示
                      window.location.reload();
                    } catch (err: any) {
                      setUploadError(err.response?.data?.detail || '保存失败，请重试');
                    } finally {
                      setIsUploading(false);
                    }
                  }}
                  className="flex-1 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
                  disabled={isUploading}
                >
                  {isUploading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      保存中...
                    </>
                  ) : (
                    '保存'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Membership Benefits Modal */}
      {showMembershipModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowMembershipModal(false)}
          />
          {/* Modal */}
          <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 animate-in fade-in zoom-in-95 duration-300">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-text-primary">会员权益</h2>
              <button
                onClick={() => setShowMembershipModal(false)}
                className="text-text-secondary hover:text-text-primary transition-all duration-200 hover:rotate-90 hover:scale-110"
              >
                ✕
              </button>
            </div>

            {/* Current Tier */}
            <div className={clsx(
              'rounded-xl p-4 mb-6',
              TIER_CONFIG[membershipTier].bgColor
            )}>
              <div className="flex items-center justify-between">
                <div>
                  <span className={clsx('text-lg font-bold', TIER_CONFIG[membershipTier].textColor)}>
                    {TIER_CONFIG[membershipTier].label}
                  </span>
                  <p className={clsx('text-sm opacity-80', TIER_CONFIG[membershipTier].textColor)}>
                    配额: {quotaInfo ? `${quotaInfo.used}/${quotaInfo.limit}篇` : TIER_CONFIG[membershipTier].quota}
                  </p>
                  {quotaInfo && (
                    <div className="mt-2 w-full bg-white/30 rounded-full h-2">
                      <div
                        className="bg-white rounded-full h-2 transition-all duration-300"
                        style={{ width: `${Math.min((quotaInfo.used / quotaInfo.limit) * 100, 100)}%` }}
                      />
                    </div>
                  )}
                </div>
                <div className={clsx('text-right')}>
                  <span className={clsx('text-2xl font-bold', TIER_CONFIG[membershipTier].textColor)}>
                    {TIER_CONFIG[membershipTier].price}
                  </span>
                  {quotaInfo && (
                    <p className={clsx('text-sm opacity-80', TIER_CONFIG[membershipTier].textColor)}>
                      剩余 {quotaInfo.remaining} 篇
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Benefits List */}
            <div className="space-y-3 mb-6">
              {TIER_CONFIG[membershipTier].benefits.map((benefit, index) => (
                <div key={index} className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                    <svg className="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span className="text-text-primary text-sm">{benefit}</span>
                </div>
              ))}
            </div>

            {/* Upgrade Button */}
            {membershipTier !== 'ultra' && (
              <button
                onClick={() => {
                  setShowMembershipModal(false);
                  router.push('/pricing');
                }}
                className="w-full py-3 bg-gradient-to-r from-primary to-primary/80 text-white rounded-xl font-semibold hover:opacity-90 transition-all"
              >
                升级会员
              </button>
            )}

            {/* All Tiers Comparison */}
            <div className="mt-6 pt-6 border-t border-border">
              <p className="text-sm text-text-secondary mb-3">会员等级对比</p>
              <div className="grid grid-cols-3 gap-3">
                {(['free', 'pro', 'ultra'] as MembershipTier[]).map((tier) => (
                  <div
                    key={tier}
                    className={clsx(
                      'rounded-lg p-3 text-center',
                      tier === membershipTier ? 'ring-2 ring-primary' : '',
                      TIER_CONFIG[tier].bgColor
                    )}
                  >
                    <span className={clsx('text-xs font-semibold', TIER_CONFIG[tier].textColor)}>
                      {TIER_CONFIG[tier].label}
                    </span>
                    <p className={clsx('text-xs opacity-80 mt-1', TIER_CONFIG[tier].textColor)}>
                      {TIER_CONFIG[tier].quota}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
