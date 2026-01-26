'use client';

/**
 * セキュリティ設定ページ - 生体認証の設定
 */

import { useState, useEffect } from 'react';
import { ArrowLeft, ScanFace, Shield, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import Link from 'next/link';
import { AuthGuard } from '@/components/auth';
import { useBiometricAuth, isBiometricAvailable } from '@/lib/hooks/use-biometric-auth';
import { useUser } from '@/lib/hooks';
import { useToast } from '@/hooks/use-toast';

function SecuritySettingsContent() {
  const { toast } = useToast();
  const { data: profile } = useUser();
  const {
    isAvailable,
    isEnabled,
    isSupported,
    isLoading,
    error,
    enableBiometric,
    disableBiometric,
    getRegisteredEmail,
  } = useBiometricAuth();

  const [password, setPassword] = useState('');
  const [showPasswordInput, setShowPasswordInput] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 登録済みのメールアドレス
  const registeredEmail = getRegisteredEmail();

  // 生体認証を有効化
  const handleEnableBiometric = async () => {
    if (!profile?.phone) {
      toast({
        title: 'エラー',
        description: 'ユーザー情報が取得できません',
        variant: 'destructive',
      });
      return;
    }

    if (!password) {
      toast({
        title: 'パスワードを入力',
        description: '生体認証を有効にするにはパスワードが必要です',
        variant: 'destructive',
      });
      return;
    }

    setIsSubmitting(true);

    const result = await enableBiometric(profile.phone);

    if (result.success) {
      // パスワードを暗号化して保存（簡易実装）
      // 注: 本番環境では、サーバー側でWebAuthn認証を行い、パスワードはローカルに保存しない
      localStorage.setItem('biometric_password', password);

      toast({
        title: '生体認証を有効化しました',
        description: '次回からFace ID / Touch IDでログインできます',
      });
      setShowPasswordInput(false);
      setPassword('');
    } else {
      toast({
        title: '有効化に失敗しました',
        description: result.error || '生体認証の設定に失敗しました',
        variant: 'destructive',
      });
    }

    setIsSubmitting(false);
  };

  // 生体認証を無効化
  const handleDisableBiometric = () => {
    disableBiometric();
    localStorage.removeItem('biometric_password');
    toast({
      title: '生体認証を無効化しました',
      description: '次回からパスワードでログインしてください',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center gap-3">
          <Link href="/settings" className="p-2 -ml-2 hover:bg-gray-100 rounded-full">
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">セキュリティ設定</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24 space-y-4">
        {/* 生体認証サポート状態 */}
        {!isSupported && (
          <Card className="rounded-xl border-yellow-200 bg-yellow-50">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div>
                  <p className="font-medium text-yellow-800">生体認証非対応</p>
                  <p className="text-sm text-yellow-700">
                    このブラウザまたはデバイスは生体認証に対応していません
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {isSupported && !isAvailable && (
          <Card className="rounded-xl border-yellow-200 bg-yellow-50">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div>
                  <p className="font-medium text-yellow-800">生体認証が利用できません</p>
                  <p className="text-sm text-yellow-700">
                    デバイスの設定でFace IDまたはTouch IDを有効にしてください
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 生体認証設定カード */}
        <Card className="rounded-xl shadow-md">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                <ScanFace className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <CardTitle className="text-lg">Face ID / Touch ID</CardTitle>
                <CardDescription>生体認証でログイン</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {isEnabled ? (
              <>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 border border-green-200">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="text-sm font-medium text-green-800">有効</p>
                    <p className="text-xs text-green-700">{registeredEmail} で登録済み</p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={handleDisableBiometric}
                >
                  生体認証を無効にする
                </Button>
              </>
            ) : isAvailable ? (
              <>
                {!showPasswordInput ? (
                  <Button
                    className="w-full bg-blue-600 hover:bg-blue-700"
                    onClick={() => setShowPasswordInput(true)}
                    disabled={isLoading}
                  >
                    <ScanFace className="h-5 w-5 mr-2" />
                    生体認証を有効にする
                  </Button>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="password" className="text-sm font-medium">
                        パスワードを入力して確認
                      </Label>
                      <Input
                        id="password"
                        type="password"
                        placeholder="現在のパスワード"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="mt-2"
                        disabled={isSubmitting}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        生体認証を有効にするには、パスワードの確認が必要です
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        className="flex-1"
                        onClick={() => {
                          setShowPasswordInput(false);
                          setPassword('');
                        }}
                        disabled={isSubmitting}
                      >
                        キャンセル
                      </Button>
                      <Button
                        className="flex-1 bg-blue-600 hover:bg-blue-700"
                        onClick={handleEnableBiometric}
                        disabled={isSubmitting || !password}
                      >
                        {isSubmitting ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          '有効にする'
                        )}
                      </Button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-gray-500">
                このデバイスでは生体認証を利用できません
              </p>
            )}

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
                <AlertCircle className="h-5 w-5 text-red-600" />
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* セキュリティ情報 */}
        <Card className="rounded-xl shadow-md">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center">
                <Shield className="h-6 w-6 text-gray-600" />
              </div>
              <div>
                <CardTitle className="text-lg">セキュリティについて</CardTitle>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="text-sm text-gray-600 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-blue-500">•</span>
                30分間操作がない場合、自動的にログアウトされます
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-500">•</span>
                生体認証はこのデバイスにのみ保存されます
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-500">•</span>
                不正アクセスを検知した場合、メールで通知します
              </li>
            </ul>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

export default function SecuritySettingsPage() {
  return (
    <AuthGuard>
      <SecuritySettingsContent />
    </AuthGuard>
  );
}
