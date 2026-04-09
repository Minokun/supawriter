'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import { Users, Search, Loader2 } from 'lucide-react';
import { useToast } from '@/components/ui/ToastContainer';
import {
  searchUsers,
  updateUserTier
} from '@/lib/api';
import type { MembershipTier, UserSearchResult } from '@/types/api';

const TIERS: MembershipTier[] = ['free', 'pro', 'ultra', 'superuser'];

const TIER_COLORS: Record<MembershipTier, string> = {
  free: 'bg-gray-100 text-gray-700',
  pro: 'bg-blue-100 text-blue-700',
  ultra: 'bg-purple-100 text-purple-700',
  superuser: 'bg-red-100 text-red-700'
};

const TIER_NAMES: Record<MembershipTier, string> = {
  free: 'Free',
  pro: 'Pro',
  ultra: 'Ultra',
  superuser: 'Superuser'
};

export default function UserManagementPage() {
  const { isAuthenticated, isAdmin } = useAuth();
  const { showSuccess, showError } = useToast();
  const [mounted, setMounted] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [users, setUsers] = useState<UserSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingTiers, setEditingTiers] = useState<Record<number, MembershipTier>>({});

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (searchQuery.length >= 1) {
      const timer = setTimeout(() => loadUsers(), 300);
      return () => clearTimeout(timer);
    }
  }, [searchQuery]);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const response = await searchUsers(searchQuery, 20, 0);
      setUsers(response.users);
    } catch (error) {
      console.error('Failed to load users:', error);
      showError('Failed to search users');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateTier = async (userId: number, tier: MembershipTier) => {
    try {
      await updateUserTier(userId, tier);
      showSuccess('User tier updated');

      // Remove editing state and refresh
      setEditingTiers(prev => {
        const newState = { ...prev };
        delete newState[userId];
        return newState;
      });
      loadUsers();
    } catch (error) {
      console.error('Failed to update tier:', error);
      showError('Failed to update');
    }
  };

  if (!mounted) {
    return (
      <MainLayout>
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="animate-spin text-primary mr-4" size={48} />
          </div>
        </div>
      </MainLayout>
    );
  }

  if (!isAuthenticated || !isAdmin) {
    return (
      <MainLayout>
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col items-center justify-center py-12">
            <p className="text-text-secondary text-lg mb-4">Admin access required</p>
            <Button variant="primary" onClick={() => window.location.href = '/settings'}>
              Back to Settings
            </Button>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <Users size={32} />
          <div>
            <h1 className="font-heading text-[32px] font-semibold text-text-primary">
              User Management
            </h1>
            <p className="font-body text-base text-text-secondary mt-1">
              Search users and manage membership tiers
            </p>
          </div>
        </div>

        {/* Search Box */}
        <Card padding="lg" className="mb-6">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-secondary" size={20} />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by username, email, or display name..."
              className="pl-12"
            />
          </div>
        </Card>

        {/* User List */}
        {loading ? (
          <Card padding="xl">
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="animate-spin text-primary mb-4" size={48} />
              <p className="text-text-secondary">Searching...</p>
            </div>
          </Card>
        ) : users.length > 0 ? (
          <Card padding="xl">
            <div className="space-y-4">
              {users.map(user => {
                const editingTier = editingTiers[user.id];
                const currentTier = user.membership_tier;

                return (
                  <div
                    key={user.id}
                    className="flex items-center justify-between p-4 bg-bg rounded-lg"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="font-heading text-base font-semibold text-text-primary">
                          {user.display_name || user.username}
                        </span>
                        {user.is_superuser && (
                          <Badge variant="primary">Super Admin</Badge>
                        )}
                      </div>
                      <div className="text-sm text-text-secondary">
                        {user.username} - {user.email}
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      {!editingTier ? (
                        <>
                          <Badge className={TIER_COLORS[currentTier]}>
                            {TIER_NAMES[currentTier]}
                          </Badge>
                          {!user.is_superuser && (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => setEditingTiers(prev => ({
                                ...prev,
                                [user.id]: currentTier
                              }))}
                            >
                              Change Tier
                            </Button>
                          )}
                        </>
                      ) : (
                        <div className="flex items-center gap-2">
                          {TIERS.map(tier => (
                            <button
                              key={tier}
                              onClick={() => handleUpdateTier(user.id, tier)}
                              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                                editingTier === tier
                                  ? 'bg-primary text-white'
                                  : 'bg-transparent border border-border text-text-secondary hover:border-primary'
                              }`}
                            >
                              {TIER_NAMES[tier]}
                            </button>
                          ))}
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setEditingTiers(prev => {
                              const newState = { ...prev };
                              delete newState[user.id];
                              return newState;
                            })}
                          >
                            Cancel
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        ) : searchQuery.length > 0 ? (
          <Card padding="xl">
            <div className="text-center py-12 text-text-secondary">
              No users found matching your search
            </div>
          </Card>
        ) : (
          <Card padding="xl">
            <div className="text-center py-12 text-text-secondary">
              Enter a search term to find users
            </div>
          </Card>
        )}
      </div>
    </MainLayout>
  );
}
