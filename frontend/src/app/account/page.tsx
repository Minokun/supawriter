'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Mail, Lock, Link as LinkIcon, CheckCircle, Loader2, User } from 'lucide-react';
import { useToast } from '@/components/ui/ToastContainer';
import { getBackendToken } from '@/lib/api';
import { getApiBaseUrl } from '@/lib/api-base-url';
import { clearBackendAuth } from '@/lib/backend-auth-storage';
import { getAccountErrorMessage, readAccountResponseData } from '@/app/account/account-response';
import { useAuth } from '@/hooks/useAuth';

interface OAuthAccount {
  provider: string;
  provider_user_id: string;
  created_at: string;
}

interface UserProfile {
  id: number;
  username: string;
  email: string | null;
  display_name: string;
  has_password: boolean;
  oauth_accounts: OAuthAccount[];
}

export default function AccountPage() {
  const { isAuthenticated, status } = useAuth();
  const router = useRouter();
  const { showSuccess, showError } = useToast();
  const signInHref = '/auth/signin?callbackUrl=%2Faccount';
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [showBindEmail, setShowBindEmail] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [mounted, setMounted] = useState(false);

  // 等待组件挂载，避免服务端和客户端渲染不一致
  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || loading || status !== 'unauthenticated') {
      return;
    }
    router.replace(signInHref);
  }, [loading, mounted, router, signInHref, status]);
  
  // 绑定邮箱表单
  const [bindEmailForm, setBindEmailForm] = useState({
    email: '',
    password: '',
    confirmPassword: '',
  });
  
  // 修改密码表单
  const [changePasswordForm, setChangePasswordForm] = useState({
    oldPassword: '',
    newPassword: '',
    confirmNewPassword: '',
  });

  const apiUrl = getApiBaseUrl();

  const handleAuthExpired = () => {
    clearBackendAuth();
    setProfile(null);
    setLoading(false);
    showError('登录已失效，请重新登录');
    if (typeof window !== 'undefined') {
      window.setTimeout(() => {
        window.location.replace(signInHref);
      }, 0);
      return;
    }
    router.replace(signInHref);
  };

  useEffect(() => {
    if (!mounted) {
      return;
    }

    if (isAuthenticated) {
      loadProfile();
      return;
    }

    if (status === 'unauthenticated') {
      setLoading(false);
    }
  }, [isAuthenticated, mounted, status]);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const token = await getBackendToken();
      if (!token) {
        handleAuthExpired();
        return;
      }

      const response = await fetch(`${apiUrl}/api/v1/auth/profile`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setProfile(data);
      } else if (response.status === 401) {
        handleAuthExpired();
      } else {
        const errorData = await response.json();
        showError(errorData.detail || '加载账号信息失败');
      }
    } catch (error) {
      console.error('加载账号信息失败:', error);
      showError('网络错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleBindEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (bindEmailForm.password !== bindEmailForm.confirmPassword) {
      showError('两次输入的密码不一致');
      return;
    }

    if (bindEmailForm.password.length < 8) {
      showError('密码至少需要 8 个字符');
      return;
    }

    try {
      const token = await getBackendToken();
      if (!token) {
        handleAuthExpired();
        return;
      }

      const response = await fetch(`${apiUrl}/api/v1/auth/bind-email`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: bindEmailForm.email,
          password: bindEmailForm.password,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        showSuccess('邮箱绑定成功');
        setShowBindEmail(false);
        setBindEmailForm({ email: '', password: '', confirmPassword: '' });
        loadProfile();
      } else if (response.status === 401) {
        handleAuthExpired();
      } else {
        showError(data.detail || '绑定失败，请稍后重试');
      }
    } catch (error) {
      console.error('绑定邮箱失败:', error);
      showError('网络错误，请稍后重试');
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (changePasswordForm.newPassword !== changePasswordForm.confirmNewPassword) {
      showError('两次输入的新密码不一致');
      return;
    }

    if (changePasswordForm.newPassword.length < 8) {
      showError('新密码至少需要 8 个字符');
      return;
    }

    try {
      const token = await getBackendToken();
      if (!token) {
        handleAuthExpired();
        return;
      }

      const response = await fetch(`${apiUrl}/api/v1/auth/change-password`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          old_password: changePasswordForm.oldPassword,
          new_password: changePasswordForm.newPassword,
        }),
      });

      const data = await readAccountResponseData(response);

      if (response.ok) {
        showSuccess('密码修改成功');
        setShowChangePassword(false);
        setChangePasswordForm({ oldPassword: '', newPassword: '', confirmNewPassword: '' });
      } else if (response.status === 401) {
        handleAuthExpired();
      } else {
        showError(getAccountErrorMessage(data, '修改失败，请检查旧密码是否正确'));
      }
    } catch (error) {
      console.error('修改密码失败:', error);
      showError('网络错误，请稍后重试');
    }
  };

  const handleUnbindOAuth = async (provider: string) => {
    if (!confirm(`确定要解绑 ${getProviderName(provider)} 登录吗？`)) return;

    try {
      const token = await getBackendToken();
      if (!token) {
        handleAuthExpired();
        return;
      }

      const response = await fetch(`${apiUrl}/api/v1/auth/unbind-oauth/${provider}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (response.ok) {
        showSuccess(`${getProviderName(provider)} 已解绑`);
        loadProfile();
      } else if (response.status === 401) {
        handleAuthExpired();
      } else {
        showError(data.detail || '解绑失败');
      }
    } catch (error) {
      console.error('解绑失败:', error);
      showError('网络错误，请稍后重试');
    }
  };

  const getProviderName = (provider: string) => {
    const names: Record<string, string> = {
      google: 'Google',
      wechat: '微信',
      github: 'GitHub',
    };
    return names[provider] || provider;
  };

  // 组件未挂载时始终显示加载状态，避免 hydration 不匹配
  if (!mounted || loading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </MainLayout>
    );
  }

  // 只在组件已挂载后显示未认证提示
  if (!isAuthenticated) {
    return (
      <MainLayout>
        <div className="text-center py-12">
          <div className="flex flex-col items-center justify-center">
            <Loader2 className="animate-spin text-primary mb-4" size={40} />
            <p className="text-text-secondary">正在跳转到登录...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-text-primary mb-2">账号管理</h1>
          <p className="text-text-secondary">管理您的账号信息和登录方式</p>
        </div>

        <div className="space-y-6">
          {/* 账号信息 */}
          <Card>
            <div className="p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <User className="w-5 h-5" />
                账号信息
              </h3>
              {profile ? (
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-text-secondary">用户名</label>
                    <p className="text-base font-medium">{profile.username}</p>
                  </div>
                  <div>
                    <label className="text-sm text-text-secondary">显示名称</label>
                    <p className="text-base font-medium">{profile.display_name}</p>
                  </div>
                  <div>
                    <label className="text-sm text-text-secondary">邮箱地址</label>
                    <div className="flex items-center gap-2">
                      <p className="text-base font-medium">
                        {profile.email || '未绑定'}
                      </p>
                      {profile.email && (
                        <Badge variant="success">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          已绑定
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-text-secondary">加载中...</p>
              )}
            </div>
          </Card>

          {/* 登录方式 */}
          {profile && (
            <Card>
              <div className="p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Lock className="w-5 h-5" />
                  登录方式
                </h3>
                <div className="space-y-3">
                  {/* 邮箱密码登录 */}
                  <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                    <div className="flex items-center gap-3">
                      <Mail className="w-5 h-5 text-text-secondary" />
                      <div>
                        <p className="font-medium">邮箱密码登录</p>
                        <p className="text-sm text-text-secondary">
                          {profile.has_password ? '已设置密码' : '未设置密码'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {profile.has_password ? (
                        <>
                          <Badge variant="success">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            已启用
                          </Badge>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setShowChangePassword(true)}
                          >
                            <Lock className="w-4 h-4 mr-1" />
                            修改密码
                          </Button>
                        </>
                      ) : (
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => setShowBindEmail(true)}
                        >
                          <LinkIcon className="w-4 h-4 mr-1" />
                          绑定邮箱
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* OAuth 登录方式 */}
                  {profile.oauth_accounts.map((account) => (
                    <div
                      key={`${account.provider}-${account.provider_user_id}`}
                      className="flex items-center justify-between p-4 border border-border rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <LinkIcon className="w-5 h-5 text-text-secondary" />
                        <div>
                          <p className="font-medium">{getProviderName(account.provider)} 登录</p>
                          <p className="text-sm text-text-secondary">
                            绑定于 {new Date(account.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="success">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          已绑定
                        </Badge>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleUnbindOAuth(account.provider)}
                        >
                          解绑
                        </Button>
                      </div>
                    </div>
                  ))}

                  {profile.oauth_accounts.length === 0 && !profile.has_password && (
                    <div className="text-center py-4 text-text-secondary">
                      <p>暂无绑定的登录方式</p>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          )}

          {/* 绑定邮箱表单 */}
          {showBindEmail && (
            <Card>
              <div className="p-6">
                <h3 className="text-lg font-semibold mb-4">绑定邮箱密码</h3>
                <form onSubmit={handleBindEmail} className="space-y-4">
                  <Input
                    label="邮箱地址"
                    type="email"
                    value={bindEmailForm.email}
                    onChange={(e) => setBindEmailForm({ ...bindEmailForm, email: e.target.value })}
                    placeholder="your@email.com"
                    required
                  />
                  <Input
                    label="设置密码"
                    type="password"
                    value={bindEmailForm.password}
                    onChange={(e) => setBindEmailForm({ ...bindEmailForm, password: e.target.value })}
                    placeholder="至少 8 个字符"
                    required
                    minLength={8}
                  />
                  <Input
                    label="确认密码"
                    type="password"
                    value={bindEmailForm.confirmPassword}
                    onChange={(e) => setBindEmailForm({ ...bindEmailForm, confirmPassword: e.target.value })}
                    placeholder="再次输入密码"
                    required
                    minLength={8}
                  />
                  <div className="flex gap-3">
                    <Button type="submit" variant="primary">
                      确认绑定
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => {
                        setShowBindEmail(false);
                        setBindEmailForm({ email: '', password: '', confirmPassword: '' });
                      }}
                    >
                      取消
                    </Button>
                  </div>
                </form>
              </div>
            </Card>
          )}

          {/* 修改密码表单 */}
          {showChangePassword && (
            <Card>
              <div className="p-6">
                <h3 className="text-lg font-semibold mb-4">修改密码</h3>
                <form onSubmit={handleChangePassword} className="space-y-4">
                  <Input
                    label="当前密码"
                    type="password"
                    value={changePasswordForm.oldPassword}
                    onChange={(e) => setChangePasswordForm({ ...changePasswordForm, oldPassword: e.target.value })}
                    placeholder="输入当前密码"
                    required
                  />
                  <Input
                    label="新密码"
                    type="password"
                    value={changePasswordForm.newPassword}
                    onChange={(e) => setChangePasswordForm({ ...changePasswordForm, newPassword: e.target.value })}
                    placeholder="至少 8 个字符"
                    required
                    minLength={8}
                  />
                  <Input
                    label="确认新密码"
                    type="password"
                    value={changePasswordForm.confirmNewPassword}
                    onChange={(e) => setChangePasswordForm({ ...changePasswordForm, confirmNewPassword: e.target.value })}
                    placeholder="再次输入新密码"
                    required
                    minLength={8}
                  />
                  <div className="flex gap-3">
                    <Button type="submit" variant="primary">
                      确认修改
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => {
                        setShowChangePassword(false);
                        setChangePasswordForm({ oldPassword: '', newPassword: '', confirmNewPassword: '' });
                      }}
                    >
                      取消
                    </Button>
                  </div>
                </form>
              </div>
            </Card>
          )}

          {/* 安全提示 */}
          <Card>
            <div className="p-6 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">安全提示</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• 建议绑定邮箱密码作为备用登录方式</li>
                <li>• 密码至少需要 8 个字符</li>
                <li>• 定期修改密码可以提高账号安全性</li>
                <li>• 不要在多个网站使用相同的密码</li>
              </ul>
            </div>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
