'use client';

import { createContext, useContext, ReactNode } from 'react';
import { useAuth, AuthState } from '@/hooks/useAuth';

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthContextProvider({ children }: { children: ReactNode }) {
  const authState = useAuth();
  return (
    <AuthContext.Provider value={authState}>
      {children}
    </AuthContext.Provider>
  );
}

export function useSharedAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useSharedAuth must be used within AuthContextProvider');
  return ctx;
}
