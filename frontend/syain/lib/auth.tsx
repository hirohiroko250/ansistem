'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from 'react';
import { useRouter } from 'next/navigation';
import {
  login as apiLogin,
  logout as apiLogout,
  getMe,
  isAuthenticated as checkAuth,
  getUserFromToken,
} from '@/lib/api/auth';
import type { Profile, LoginResponse } from '@/lib/api/auth';
import type { ApiError } from '@/lib/api/client';

interface AuthContextType {
  user: Profile | LoginResponse['user'] | null;
  loading: boolean;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<{ error: string | null }>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  isAuthenticated: false,
  signIn: async () => ({ error: null }),
  signOut: async () => {},
  refreshUser: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Profile | LoginResponse['user'] | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // 初期化時にユーザー情報を取得
  useEffect(() => {
    const initAuth = async () => {
      if (checkAuth()) {
        try {
          // まずトークンからユーザー情報を取得（高速）
          const tokenUser = getUserFromToken();
          if (tokenUser) {
            // 社員・管理者のみアクセス可能
            const userType = tokenUser.userType?.toUpperCase();
            if (userType === 'STAFF' || userType === 'ADMIN' || userType === 'INSTRUCTOR' || userType === 'TEACHER') {
              setUser(tokenUser);
              // バックグラウンドで詳細情報を取得
              try {
                const profile = await getMe();
                setUser(profile);
              } catch {
                // 詳細取得に失敗してもトークン情報は使う
              }
            } else {
              // 権限がない場合はログアウト
              await apiLogout();
              setUser(null);
            }
          }
        } catch {
          setUser(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    try {
      const response = await apiLogin({ email, password });
      // 社員・管理者のみアクセス可能
      const userType = response.user.userType?.toUpperCase();
      if (userType !== 'STAFF' && userType !== 'ADMIN' && userType !== 'INSTRUCTOR' && userType !== 'TEACHER') {
        await apiLogout();
        return { error: 'このアカウントでは社員システムにアクセスできません' };
      }
      setUser(response.user);
      return { error: null };
    } catch (err) {
      const apiError = err as ApiError;
      return { error: apiError.message || 'ログインに失敗しました' };
    }
  }, []);

  const signOut = useCallback(async () => {
    await apiLogout();
    setUser(null);
    router.push('/login');
  }, [router]);

  const refreshUser = useCallback(async () => {
    try {
      const profile = await getMe();
      setUser(profile);
    } catch {
      setUser(null);
    }
  }, []);

  const value: AuthContextType = {
    user,
    loading,
    isAuthenticated: !!user,
    signIn,
    signOut,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

// 認証が必要なページ用のHook
export function useRequireAuth(redirectTo = '/login') {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push(redirectTo);
    }
  }, [isAuthenticated, loading, redirectTo, router]);

  return { loading, isAuthenticated };
}
