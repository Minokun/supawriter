'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { Bell, Check, Trash2, ExternalLink, Loader2, X } from 'lucide-react';
import { notificationsApi, AlertRecord } from '@/types/api';
import { useToast } from '@/components/ui/ToastContainer';

interface NotificationCenterProps {
  onNavigate?: () => void;
}

export default function NotificationCenter({ onNavigate }: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<AlertRecord[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { showSuccess, showError } = useToast();

  // 加载通知列表
  const loadNotifications = useCallback(async (pageNum: number = 1, append: boolean = false) => {
    setLoading(true);
    try {
      const response = await notificationsApi.getNotifications(pageNum, 10);
      if (append) {
        setNotifications(prev => [...prev, ...response.notifications]);
      } else {
        setNotifications(response.notifications);
      }
      setUnreadCount(response.unread_count);
      setHasMore(response.notifications.length === 10);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // 加载未读数量
  const loadUnreadCount = useCallback(async () => {
    try {
      const response = await notificationsApi.getUnreadCount();
      setUnreadCount(response.count);
    } catch (error) {
      console.error('Failed to load unread count:', error);
    }
  }, []);

  // 初始加载
  useEffect(() => {
    loadUnreadCount();
    // 每30秒刷新一次未读数量
    const interval = setInterval(loadUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [loadUnreadCount]);

  // 打开下拉菜单时加载通知
  useEffect(() => {
    if (isOpen) {
      loadNotifications(1, false);
      setPage(1);
    }
  }, [isOpen, loadNotifications]);

  // 点击外部关闭
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 标记已读
  const handleMarkAsRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await notificationsApi.markAsRead(id);
      setNotifications(prev =>
        prev.map(n => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      showError('标记已读失败');
    }
  };

  // 标记全部已读
  const handleMarkAllRead = async () => {
    try {
      const result = await notificationsApi.markAllRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
      showSuccess(`已标记 ${result.count} 条通知为已读`);
    } catch (error) {
      showError('标记全部已读失败');
    }
  };

  // 删除通知
  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    // 先获取通知信息（在数组更新前）
    const deleted = notifications.find(n => n.id === id);
    try {
      await notificationsApi.deleteNotification(id);
      setNotifications(prev => prev.filter(n => n.id !== id));
      // 如果删除的是未读通知，更新未读数量
      if (deleted && !deleted.is_read) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
      showSuccess('通知已删除');
    } catch (error) {
      showError('删除失败');
    }
  };

  // 加载更多
  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    loadNotifications(nextPage, true);
  };

  // 格式化时间
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString('zh-CN');
  };

  // 获取来源图标/名称
  const getSourceLabel = (source: string) => {
    const sourceMap: Record<string, { name: string; color: string }> = {
      baidu: { name: '百度', color: '#2932e1' },
      weibo: { name: '微博', color: '#e6162d' },
      zhihu: { name: '知乎', color: '#0084ff' },
      toutiao: { name: '头条', color: '#ed4040' },
      douyin: { name: '抖音', color: '#000000' },
    };
    return sourceMap[source] || { name: source, color: '#666' };
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* 铃铛按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-text-secondary hover:text-text-primary hover:bg-bg rounded-lg transition-all"
        aria-label="通知中心"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-xs font-medium rounded-full flex items-center justify-center">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* 下拉菜单 */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-[400px] max-w-[calc(100vw-32px)] bg-white rounded-xl shadow-lg border border-border overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-200">
          {/* 头部 */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-bg">
            <h3 className="font-semibold text-text-primary">通知中心</h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 px-2 py-1 rounded hover:bg-primary/10 transition-colors"
                >
                  <Check size={12} />
                  全部已读
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 text-text-tertiary hover:text-text-primary rounded transition-colors"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* 通知列表 */}
          <div className="max-h-[400px] overflow-y-auto">
            {loading && notifications.length === 0 ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="animate-spin text-primary" size={24} />
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-text-secondary">
                <Bell size={48} className="text-text-tertiary mb-3" />
                <p>暂无新通知</p>
                <p className="text-sm text-text-tertiary mt-1">
                  设置关键词后，当热点匹配时会通知您
                </p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {notifications.map((notification) => {
                  const source = getSourceLabel(notification.hotspot_source);
                  return (
                    <div
                      key={notification.id}
                      className={`p-4 hover:bg-bg transition-colors ${
                        !notification.is_read ? 'bg-primary/5' : ''
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {/* 未读指示器 */}
                        <div className="mt-1.5">
                          {!notification.is_read ? (
                            <div className="w-2 h-2 bg-primary rounded-full" />
                          ) : (
                            <div className="w-2 h-2 bg-transparent" />
                          )}
                        </div>

                        {/* 内容 */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className="text-xs px-2 py-0.5 rounded-full font-medium"
                              style={{
                                backgroundColor: `${source.color}20`,
                                color: source.color,
                              }}
                            >
                              {source.name}
                            </span>
                            <span className="text-xs text-text-tertiary">
                              {formatTime(notification.matched_at)}
                            </span>
                          </div>

                          <p className="text-sm text-text-primary font-medium mb-1 line-clamp-2">
                            {notification.hotspot_title}
                          </p>

                          <div className="flex items-center gap-2">
                            <span className="text-xs text-text-secondary">
                              匹配关键词:
                            </span>
                            <span className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded-full">
                              {notification.keyword}
                            </span>
                          </div>
                        </div>

                        {/* 操作按钮 */}
                        <div className="flex items-center gap-1">
                          {!notification.is_read && (
                            <button
                              onClick={(e) => handleMarkAsRead(notification.id, e)}
                              className="p-1.5 text-text-tertiary hover:text-primary hover:bg-primary/10 rounded transition-colors"
                              title="标记已读"
                            >
                              <Check size={14} />
                            </button>
                          )}
                          <button
                            onClick={(e) => handleDelete(notification.id, e)}
                            className="p-1.5 text-text-tertiary hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                            title="删除"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* 加载更多 */}
                {hasMore && (
                  <div className="p-3 text-center">
                    <button
                      onClick={handleLoadMore}
                      disabled={loading}
                      className="text-sm text-primary hover:text-primary/80 disabled:opacity-50"
                    >
                      {loading ? (
                        <Loader2 className="animate-spin inline mr-1" size={14} />
                      ) : (
                        '加载更多'
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 底部 */}
          <div className="px-4 py-3 border-t border-border bg-bg flex items-center justify-between">
            <Link
              href="/settings/alerts"
              onClick={() => {
                setIsOpen(false);
                onNavigate?.();
              }}
              className="text-sm text-primary hover:text-primary/80 flex items-center gap-1"
            >
              <ExternalLink size={14} />
              设置预警关键词
            </Link>
            {notifications.length > 0 && (
              <span className="text-xs text-text-tertiary">
                共 {notifications.length} 条通知
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
