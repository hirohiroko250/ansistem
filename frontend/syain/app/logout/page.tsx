'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth';
import { LogOut, ArrowLeft } from 'lucide-react';

export default function LogoutPage() {
  const { signOut, user } = useAuth();
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);

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

  const handleCancel = () => {
    router.back();
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-xl border-0">
        <CardHeader className="text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <LogOut className="w-8 h-8 text-red-600" />
          </div>
          <CardTitle className="text-2xl">ログアウト</CardTitle>
          <CardDescription>
            {user?.email || 'ユーザー'} としてログイン中
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-center text-gray-600">
            ログアウトしますか？
          </p>

          <Button
            onClick={handleLogout}
            variant="destructive"
            className="w-full h-12"
            disabled={loggingOut}
          >
            <LogOut className="w-4 h-4 mr-2" />
            {loggingOut ? 'ログアウト中...' : 'ログアウトする'}
          </Button>

          <Button
            onClick={handleCancel}
            variant="outline"
            className="w-full h-12"
            disabled={loggingOut}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            キャンセル
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
