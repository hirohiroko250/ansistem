'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AlertCircle, Loader2, Lock, CheckCircle2 } from 'lucide-react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { changePassword } from '@/lib/api/auth';
import type { ApiError } from '@/lib/api/types';

export default function PasswordChangePage() {
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // パスワード強度チェック
  const passwordChecks = {
    length: newPassword.length >= 8,
    different: newPassword !== currentPassword && newPassword.length > 0,
  };

  const allChecksPass = passwordChecks.length && passwordChecks.different;
  const passwordsMatch = newPassword === confirmPassword && confirmPassword.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // バリデーション
    if (!currentPassword || !newPassword || !confirmPassword) {
      setError('すべての項目を入力してください');
      return;
    }

    if (!allChecksPass) {
      setError('パスワードの要件を満たしてください');
      return;
    }

    if (!passwordsMatch) {
      setError('新しいパスワードが一致しません');
      return;
    }

    setIsLoading(true);

    try {
      await changePassword({
        currentPassword,
        newPassword,
        newPasswordConfirm: confirmPassword,
      });

      // 成功したらフィードページへ
      router.push('/feed');
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.status === 400) {
        setError(apiError.message || '入力内容に問題があります');
      } else if (apiError.status === 401) {
        setError('現在のパスワードが正しくありません');
      } else {
        setError(apiError.message || 'パスワードの変更に失敗しました');
      }
    } finally {
      setIsLoading(false);
    }
  };

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
              パスワードの変更
            </h2>
            <p className="text-sm text-gray-600 mb-6 text-center">
              初回ログインのため、新しいパスワードを設定してください
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* 現在のパスワード */}
              <div>
                <Label htmlFor="currentPassword" className="text-sm font-medium text-gray-700 mb-2 block">
                  現在のパスワード
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    id="currentPassword"
                    type="password"
                    placeholder="現在のパスワード"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="rounded-xl h-12 pl-10"
                    autoComplete="current-password"
                    disabled={isLoading}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  初期パスワード：1 + 電話番号下4桁
                </p>
              </div>

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
                    disabled={isLoading}
                  />
                </div>

                {/* パスワード要件チェック */}
                <div className="mt-2 space-y-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2
                      className={`h-4 w-4 ${passwordChecks.length ? 'text-green-500' : 'text-gray-300'}`}
                    />
                    <span className={`text-xs ${passwordChecks.length ? 'text-green-600' : 'text-gray-500'}`}>
                      8文字以上
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2
                      className={`h-4 w-4 ${passwordChecks.different ? 'text-green-500' : 'text-gray-300'}`}
                    />
                    <span className={`text-xs ${passwordChecks.different ? 'text-green-600' : 'text-gray-500'}`}>
                      現在のパスワードと異なる
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
                    disabled={isLoading}
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
                disabled={isLoading || !allChecksPass || !passwordsMatch}
                className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg disabled:opacity-50"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    変更中...
                  </span>
                ) : (
                  'パスワードを変更'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-xs text-gray-500 mt-6">
          &copy; 2025 OZA. All rights reserved.
        </p>
      </div>
    </div>
  );
}
