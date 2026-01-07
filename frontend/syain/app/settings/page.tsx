'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { useAuth } from '@/lib/auth';
import { BottomNav } from '@/components/bottom-nav';
import { User, Bell, LogOut, Save, Settings, ChevronRight } from 'lucide-react';
import api from '@/lib/api/client';

interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  lastName?: string;
  firstName?: string;
  phoneNumber?: string;
}

export default function SettingsPage() {
  const { user, loading, isAuthenticated, signOut } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [lastName, setLastName] = useState('');
  const [firstName, setFirstName] = useState('');
  const [phone, setPhone] = useState('');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    loadProfile();
  }, [isAuthenticated, loading, router]);

  const loadProfile = async () => {
    try {
      const data = await api.get<UserProfile>('/auth/me/');
      setProfile(data);
      setLastName(data.lastName || '');
      setFirstName(data.firstName || '');
      setPhone(data.phoneNumber || '');
    } catch (err) {
      console.error('プロフィール取得エラー:', err);
    } finally {
      setLoadingProfile(false);
    }
  };

  const handleSave = async () => {
    setSubmitting(true);
    try {
      await api.patch('/auth/me/', {
        lastName,
        firstName,
        phoneNumber: phone,
      });
      alert('設定を保存しました');
    } catch (err) {
      console.error('保存エラー:', err);
      alert('保存に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await signOut();
    } catch (err) {
      console.error('ログアウトエラー:', err);
      // エラーが発生してもログイン画面に遷移
      router.push('/login');
    }
  };

  if (loading || loadingProfile) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-[390px] mx-auto">
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Settings className="w-6 h-6" />
              設定
            </h1>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {/* アカウント情報 */}
          <Card className="shadow-md border-0">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <User className="w-5 h-5" />
                アカウント情報
              </CardTitle>
              <CardDescription>{user?.email}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="lastName">姓</Label>
                  <Input
                    id="lastName"
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    className="h-12"
                    placeholder="山田"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="firstName">名</Label>
                  <Input
                    id="firstName"
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    className="h-12"
                    placeholder="太郎"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">電話番号</Label>
                <Input
                  id="phone"
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="h-12"
                  placeholder="090-1234-5678"
                />
              </div>

              <div className="space-y-2">
                <Label>メールアドレス</Label>
                <Input
                  type="email"
                  value={user?.email || ''}
                  disabled
                  className="h-12 bg-gray-100"
                />
                <p className="text-xs text-gray-500">メールアドレスは変更できません</p>
              </div>
            </CardContent>
          </Card>

          {/* 通知設定 */}
          <Card className="shadow-md border-0">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Bell className="w-5 h-5" />
                通知設定
              </CardTitle>
              <CardDescription>プッシュ通知の管理</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-sm">通知を受け取る</p>
                  <p className="text-xs text-gray-600">チャットやタスクの通知</p>
                </div>
                <Switch
                  checked={notificationsEnabled}
                  onCheckedChange={setNotificationsEnabled}
                />
              </div>
            </CardContent>
          </Card>

          {/* パスワード変更 */}
          <Card
            className="shadow-md border-0 cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => router.push('/settings/password')}
          >
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">パスワード変更</p>
                  <p className="text-sm text-gray-500">ログインパスワードの変更</p>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </div>
            </CardContent>
          </Card>

          {/* 保存ボタン */}
          <Button
            onClick={handleSave}
            disabled={submitting}
            className="w-full h-12 bg-blue-600 hover:bg-blue-700"
          >
            <Save className="w-4 h-4 mr-2" />
            {submitting ? '保存中...' : '設定を保存'}
          </Button>

          {/* ログアウト */}
          <Card className="shadow-md border-0 border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <Button
                onClick={handleLogout}
                variant="destructive"
                className="w-full h-12"
                disabled={loggingOut}
              >
                <LogOut className="w-4 h-4 mr-2" />
                {loggingOut ? 'ログアウト中...' : 'ログアウト'}
              </Button>
            </CardContent>
          </Card>

          {/* アプリ情報 */}
          <div className="text-center text-xs text-gray-400 pt-4">
            <p>講師業務システム v1.0.0</p>
            <p className="mt-1">© 2024 アンイングリッシュグループ</p>
          </div>
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
