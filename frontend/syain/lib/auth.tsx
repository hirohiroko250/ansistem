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
  getProfile,
  getAccessToken,
} from '@/lib/api';
import type { Profile, LoginRequest, ApiError } from '@/lib/api';

interface AuthContextType {
  user: Profile | null;
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
  const [user, setUser] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // 初期化時にユーザー情報を取得
  useEffect(() => {
    const initAuth = async () => {
      const token = getAccessToken();
      if (token) {
        try {
          const profile = await getProfile();
          // 社員・講師のみアクセス可能 (バックエンドはcamelCase + 大文字で返す)
          const userType = ((profile as any).userType || profile.user_type || '').toUpperCase();
          if (userType === 'STAFF' || userType === 'INSTRUCTOR' || userType === 'TEACHER') {
            setUser(profile);
          } else {
            // 権限がない場合はログアウト
            await apiLogout();
            setUser(null);
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
      // 社員・講師のみアクセス可能 (バックエンドはcamelCase + 大文字で返す)
      const userType = ((response.user as any).userType || response.user.user_type || '').toUpperCase();
      if (userType !== 'STAFF' && userType !== 'INSTRUCTOR' && userType !== 'TEACHER') {
        await apiLogout();
        return { error: 'このアカウントでは講師業務システムにアクセスできません' };
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
      const profile = await getProfile();
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
