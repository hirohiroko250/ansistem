'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AlertCircle, Loader2, Lock, CheckCircle2, ArrowLeft, Mail } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { changePassword, requestPasswordReset } from '@/lib/api/auth';
import type { ApiError } from '@/lib/api/types';
import { AuthGuard } from '@/components/auth';

function SettingsPasswordContent() {
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // パスワードを忘れた場合のモード
  const [forgotMode, setForgotMode] = useState(false);
  const [email, setEmail] = useState('');
  const [emailSent, setEmailSent] = useState(false);

  // パスワード強度チェック
  const passwordChecks = {
    length: newPassword.length >= 8,
    different: newPassword !== currentPassword && newPassword.length > 0,
  };

  const allChecksPass = passwordChecks.length && passwordChecks.different;
  const passwordsMatch = newPassword === confirmPassword && confirmPassword.length > 0;

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

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

      setSuccess('パスワードを変更しました');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');

      // 3秒後に設定画面に戻る
      setTimeout(() => {
        router.push('/settings');
      }, 3000);
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

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email) {
      setError('メールアドレスを入力してください');
      return;
    }

    // 簡易的なメール形式チェック
    if (!email.includes('@')) {
      setError('有効なメールアドレスを入力してください');
      return;
    }

    setIsLoading(true);

    try {
      await requestPasswordReset(email);
      setEmailSent(true);
    } catch (err) {
      const apiError = err as ApiError;
      // セキュリティのため、メールが存在しない場合でも成功扱いにする
      if (apiError.status === 404 || apiError.status === 400) {
        setEmailSent(true);
      } else {
        setError(apiError.message || 'メールの送信に失敗しました。しばらくしてからお試しください。');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // パスワードを忘れた場合のフォーム
  if (forgotMode) {
    if (emailSent) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
          <header className="sticky top-0 z-40 bg-white shadow-sm">
            <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center gap-3">
              <button onClick={() => { setForgotMode(false); setEmailSent(false); }}>
                <ArrowLeft className="h-6 w-6 text-gray-600" />
              </button>
              <h1 className="text-lg font-bold text-gray-800">パスワード再設定</h1>
            </div>
          </header>

          <main className="max-w-[390px] mx-auto px-4 py-6">
            <Card className="rounded-xl shadow-md">
              <CardContent className="p-6 text-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Mail className="h-8 w-8 text-green-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-800 mb-2">メールを送信しました</h2>
                <p className="text-sm text-gray-600 mb-4">
                  {email} 宛てにパスワード再設定用のメールを送信しました。
                  メール内のリンクをクリックして、新しいパスワードを設定してください。
                </p>
                <p className="text-xs text-gray-500 mb-6">
                  メールが届かない場合は、迷惑メールフォルダをご確認ください。
                </p>
                <Button
                  onClick={() => { setForgotMode(false); setEmailSent(false); setEmail(''); }}
                  className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700"
                >
                  戻る
                </Button>
              </CardContent>
            </Card>
          </main>
        </div>
      );
    }

    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center gap-3">
            <button onClick={() => setForgotMode(false)}>
              <ArrowLeft className="h-6 w-6 text-gray-600" />
            </button>
            <h1 className="text-lg font-bold text-gray-800">パスワード再設定</h1>
          </div>
        </header>

        <main className="max-w-[390px] mx-auto px-4 py-6">
          <Card className="rounded-xl shadow-md">
            <CardContent className="p-6">
              <p className="text-sm text-gray-600 mb-6">
                登録されているメールアドレスを入力してください。
                パスワード再設定用のリンクをお送りします。
              </p>

              <form onSubmit={handleForgotPassword} className="space-y-4">
                <div>
                  <Label htmlFor="email" className="text-sm font-medium text-gray-700 mb-2 block">
                    メールアドレス
                  </Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="example@email.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="rounded-xl h-12 pl-10"
                      autoComplete="email"
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
                  disabled={isLoading || !email}
                  className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold disabled:opacity-50"
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="h-5 w-5 animate-spin" />
                      送信中...
                    </span>
                  ) : (
                    '再設定メールを送信'
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </main>
      </div>
    );
  }

  // 通常のパスワード変更フォーム
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center gap-3">
          <Link href="/settings">
            <ArrowLeft className="h-6 w-6 text-gray-600" />
          </Link>
          <h1 className="text-lg font-bold text-gray-800">パスワード変更</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6">
        <Card className="rounded-xl shadow-md">
          <CardContent className="p-6">
            <form onSubmit={handleChangePassword} className="space-y-5">
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

              {success && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 border border-green-200">
                  <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0" />
                  <p className="text-sm text-green-800">{success}</p>
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading || !allChecksPass || !passwordsMatch}
                className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold disabled:opacity-50"
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

            {/* パスワードを忘れた場合 */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <button
                onClick={() => setForgotMode(true)}
                className="w-full text-center text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                パスワードを忘れた場合
              </button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

export default function SettingsPasswordPage() {
  return (
    <AuthGuard>
      <SettingsPasswordContent />
    </AuthGuard>
  );
}
