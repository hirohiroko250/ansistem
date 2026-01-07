'use client';

import { useState, useEffect } from 'react';
import { ChevronRight, User, CreditCard, HelpCircle, LogOut, Loader2, AlertCircle, KeyRound } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getMe, logout } from '@/lib/api/auth';
import type { Profile, ApiError } from '@/lib/api/types';

const menuItems = [
  { id: 1, icon: User, label: 'プロフィール編集', href: '/settings/profile-edit' },
  { id: 2, icon: KeyRound, label: 'パスワード変更', href: '/settings/password' },
  { id: 3, icon: CreditCard, label: '支払い方法', href: '/settings/payment' },
  { id: 4, icon: HelpCircle, label: 'よくある質問', href: '#' },
];

export default function SettingsPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    const fetchProfile = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getMe();
        setProfile(data);
      } catch (err) {
        const apiError = err as ApiError;
        if (apiError.status === 401) {
          router.push('/login');
          return;
        }
        setError(apiError.message || 'プロフィール情報の取得に失敗しました');
      } finally {
        setIsLoading(false);
      }
    };
    fetchProfile();
  }, [router]);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } catch {
      // ログアウトエラーは無視してリダイレクト
    }
    router.push('/login');
  };

  // 名前の頭文字を取得（アバター用）
  const getInitials = (profile: Profile | null): string => {
    if (!profile) return '';
    if (profile.lastName) return profile.lastName.slice(0, 2);
    if (profile.fullName) return profile.fullName.slice(0, 2);
    return profile.email.slice(0, 2).toUpperCase();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <h1 className="text-2xl font-bold text-blue-600">Settings</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        {isLoading ? (
          <Card className="rounded-xl shadow-md mb-6">
            <CardContent className="p-6 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </CardContent>
          </Card>
        ) : error ? (
          <Card className="rounded-xl shadow-md mb-6 border-red-200">
            <CardContent className="p-6">
              <div className="flex items-center gap-2 text-red-600">
                <AlertCircle className="h-5 w-5" />
                <p className="text-sm">{error}</p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="rounded-xl shadow-md mb-6">
            <CardContent className="p-6 flex items-center gap-4">
              <Avatar className="h-16 w-16">
                <AvatarFallback className="bg-blue-100 text-blue-600 text-xl font-semibold">
                  {getInitials(profile)}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1">
                <h2 className="text-lg font-bold text-gray-800">
                  {profile?.fullName || `${profile?.lastName || ''} ${profile?.firstName || ''}`.trim() || 'ユーザー'}
                </h2>
                <p className="text-sm text-gray-600">{profile?.email}</p>
              </div>
              <ChevronRight className="h-5 w-5 text-gray-400" />
            </CardContent>
          </Card>
        )}

        <div className="space-y-2 mb-6">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link key={item.id} href={item.href}>
                <Card className="rounded-xl shadow-sm hover:shadow-md transition-shadow cursor-pointer">
                  <CardContent className="p-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
                      <Icon className="h-5 w-5 text-gray-600" />
                    </div>
                    <span className="flex-1 font-medium text-gray-800">{item.label}</span>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>

        <div className="mt-12 text-center text-sm text-gray-500 mb-6">
          <p>MyLesson v1.0.0</p>
        </div>

        <Card
          className={`rounded-xl shadow-sm hover:shadow-md transition-shadow cursor-pointer border-red-200 ${isLoggingOut ? 'opacity-50 cursor-not-allowed' : ''}`}
          onClick={!isLoggingOut ? handleLogout : undefined}
        >
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center">
              {isLoggingOut ? (
                <Loader2 className="h-5 w-5 text-red-600 animate-spin" />
              ) : (
                <LogOut className="h-5 w-5 text-red-600" />
              )}
            </div>
            <span className="flex-1 font-medium text-red-600">
              {isLoggingOut ? 'ログアウト中...' : 'ログアウト'}
            </span>
          </CardContent>
        </Card>
      </main>

      <BottomTabBar />
    </div>
  );
}
