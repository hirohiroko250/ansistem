'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AlertCircle, Loader2, Lock, CheckCircle2 } from 'lucide-react';
import Image from 'next/image';
import { confirmPasswordReset } from '@/lib/api/auth';
import type { ApiError } from '@/lib/api/types';

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  // パスワード強度チェック
  const passwordChecks = {
    length: newPassword.length >= 8,
  };

  const allChecksPass = passwordChecks.length;
  const passwordsMatch = newPassword === confirmPassword && confirmPassword.length > 0;

  useEffect(() => {
    if (!token) {
      setError('無効なリンクです。パスワード再設定を再度リクエストしてください。');
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!token) {
      setError('無効なリンクです');
      return;
    }

    if (!newPassword || !confirmPassword) {
      setError('すべての項目を入力してください');
      return;
    }

    if (!allChecksPass) {
      setError('パスワードは8文字以上で入力してください');
      return;
    }

    if (!passwordsMatch) {
      setError('パスワードが一致しません');
      return;
    }

    setIsLoading(true);

    try {
      await confirmPasswordReset({
        token,
        newPassword,
        newPasswordConfirm: confirmPassword,
      });

      setIsSuccess(true);
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.status === 400) {
        setError('リンクの有効期限が切れているか、既に使用されています。再度リクエストしてください。');
      } else {
        setError(apiError.message || 'パスワードの再設定に失敗しました');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // 成功画面
  if (isSuccess) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center px-4">
        <div className="w-full max-w-[420px]">
          <div className="text-center mb-8">
            <Image
              src="/oza-logo.svg"
              alt="OZA"
              width={100}
              height={100}
              className="mx-auto mb-4"
              priority
            />
          </div>

          <Card className="rounded-2xl shadow-lg">
            <CardContent className="p-6 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="h-8 w-8 text-green-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-800 mb-2">パスワードを再設定しました</h2>
              <p className="text-sm text-gray-600 mb-6">
                新しいパスワードでログインしてください。
              </p>
              <Button
                onClick={() => router.push('/login')}
                className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700"
              >
                ログインへ
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center px-4">
      <div className="w-full max-w-[420px]">
        <div className="text-center mb-8">
          <Image
            src="/oza-logo.svg"
            alt="OZA"
            width={100}
            height={100}
            className="mx-auto mb-4"
            priority
          />
        </div>

        <Card className="rounded-2xl shadow-lg">
          <CardContent className="p-6">
            <h2 className="text-xl font-bold text-gray-800 mb-2 text-center">
              パスワードの再設定
            </h2>
            <p className="text-sm text-gray-600 mb-6 text-center">
              新しいパスワードを入力してください
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* 新しいパスワード */}
              <div>
                <Label htmlFor="newPassword" className="text-sm font-medium text-gray-700 mb-2 block">
                  新しいパスワード
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    id="newPassword"
                    type="password"
                    placeholder="8文字以上で入力"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="rounded-xl h-12 pl-10"
                    autoComplete="new-password"
                    disabled={isLoading || !token}
                  />
                </div>

                {/* パスワード要件チェック */}
                <div className="mt-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2
                      className={`h-4 w-4 ${passwordChecks.length ? 'text-green-500' : 'text-gray-300'}`}
                    />
                    <span className={`text-xs ${passwordChecks.length ? 'text-green-600' : 'text-gray-500'}`}>
                      8文字以上
                    </span>
                  </div>
                </div>
              </div>

              {/* 新しいパスワード（確認） */}
              <div>
                <Label htmlFor="confirmPassword" className="text-sm font-medium text-gray-700 mb-2 block">
                  新しいパスワード（確認）
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="もう一度入力"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="rounded-xl h-12 pl-10"
                    autoComplete="new-password"
                    disabled={isLoading || !token}
                  />
                </div>
                {confirmPassword && !passwordsMatch && (
                  <p className="text-xs text-red-500 mt-1">パスワードが一致しません</p>
                )}
                {passwordsMatch && (
                  <div className="flex items-center gap-2 mt-1">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span className="text-xs text-green-600">パスワードが一致しています</span>
                  </div>
                )}
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
                  <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading || !allChecksPass || !passwordsMatch || !token}
                className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold disabled:opacity-50"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    設定中...
                  </span>
                ) : (
                  'パスワードを再設定'
                )}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <button
                onClick={() => router.push('/login')}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                ログインに戻る
              </button>
            </div>
          </CardContent>
        </Card>

        <p className="text-center text-xs text-gray-500 mt-6">
          &copy; 2025 OZA. All rights reserved.
        </p>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    }>
      <ResetPasswordContent />
    </Suspense>
  );
}
