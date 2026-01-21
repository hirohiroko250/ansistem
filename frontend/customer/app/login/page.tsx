'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AlertCircle, Loader2, Phone, Lock } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { GuestGuard } from '@/components/auth';
import { login } from '@/lib/api/auth';
import type { ApiError } from '@/lib/api/types';

function LoginContent() {
  const router = useRouter();
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!phone || !password) {
      setError('電話番号とパスワードを入力してください');
      return;
    }

    // 電話番号の簡易バリデーション（数字とハイフンのみ）
    const phoneRegex = /^[0-9-]+$/;
    if (!phoneRegex.test(phone)) {
      setError('有効な電話番号を入力してください');
      return;
    }

    setIsLoading(true);

    try {
      const response = await login({ phone, password });

      // パスワード変更が必要な場合はパスワード変更ページへリダイレクト
      if (response.user?.mustChangePassword) {
        router.push('/password-change');
      } else {
        router.push('/feed');
      }
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.status === 401) {
        setError('電話番号またはパスワードが正しくありません');
      } else if (apiError.status === 400) {
        setError(apiError.message || '入力内容に問題があります');
      } else if (apiError.status >= 500) {
        setError('サーバーエラーが発生しました。しばらくしてから再度お試しください');
      } else {
        setError(apiError.message || 'ログインに失敗しました');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center px-4">
      <div className="w-full max-w-[390px]">
        <div className="text-center mb-8">
          <Image
            src="/oza-logo.svg"
            alt="OZA"
            width={120}
            height={120}
            className="mx-auto mb-4"
            priority
          />
        </div>

        <Card className="rounded-2xl shadow-lg">
          <CardContent className="p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">ログイン</h2>

            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <Label htmlFor="phone" className="text-sm font-medium text-gray-700 mb-2 block">
                  電話番号
                </Label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    id="phone"
                    type="tel"
                    placeholder="09012345678"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="rounded-xl h-12 pl-10"
                    autoComplete="tel"
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="password" className="text-sm font-medium text-gray-700 mb-2 block">
                  パスワード
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="パスワードを入力"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="rounded-xl h-12 pl-10"
                    autoComplete="current-password"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
                  <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg disabled:opacity-70"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    ログイン中...
                  </span>
                ) : (
                  'ログイン'
                )}
              </Button>
            </form>

            <div className="mt-6 space-y-3 text-center">
              <Link href="/signup">
                <p className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                  新規登録はこちら
                </p>
              </Link>
              <Link href="/password-reset">
                <p className="text-sm text-gray-600 hover:text-gray-700">
                  パスワードをお忘れの方はこちら
                </p>
              </Link>
            </div>
          </CardContent>
        </Card>

        <p className="text-center text-xs text-gray-500 mt-6">
          © 2025 OZA. All rights reserved.
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <GuestGuard>
      <LoginContent />
    </GuestGuard>
  );
}
