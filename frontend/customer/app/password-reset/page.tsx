'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ChevronLeft, Check, Mail } from 'lucide-react';
import Link from 'next/link';
import { requestPasswordReset } from '@/lib/api/auth';

export default function PasswordResetPage() {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSendEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      await requestPasswordReset(email);
      setStep(2);
    } catch (err) {
      // セキュリティのため、メールアドレスが存在しなくても成功として扱う
      // バックエンドも同様の動作をしているが、念のためフロントでも対応
      setStep(2);
    } finally {
      setIsLoading(false);
    }
  };

  // メール送信完了画面
  if (step === 2) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center px-4">
        <div className="text-center max-w-[390px] w-full">
          <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-6">
            <Check className="w-10 h-10 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-3">メール送信完了</h2>
          <p className="text-gray-600 mb-4">
            パスワード再設定用のリンクを<br />
            <span className="font-medium text-gray-800">{email}</span><br />
            に送信しました。
          </p>
          <p className="text-sm text-gray-500 mb-8">
            メールが届かない場合は、迷惑メールフォルダをご確認いただくか、
            入力したメールアドレスが正しいかご確認ください。
            リンクの有効期限は1時間です。
          </p>
          <Link href="/login">
            <Button className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg">
              ログインへ戻る
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/login" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">パスワード再設定</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6">
        <Card className="rounded-2xl shadow-lg">
          <CardContent className="p-6">
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 mb-4">
                <Mail className="h-8 w-8 text-blue-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-800 mb-2">メールアドレス確認</h2>
              <p className="text-sm text-gray-600">
                登録済みのメールアドレスを入力してください。<br />
                パスワード再設定用のリンクをお送りします。
              </p>
            </div>

            <form onSubmit={handleSendEmail} className="space-y-5">
              <div>
                <Label htmlFor="email" className="text-sm font-medium text-gray-700 mb-2 block">
                  メールアドレス <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="example@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="rounded-xl h-12"
                  required
                />
              </div>

              {error && (
                <p className="text-sm text-red-500 text-center">{error}</p>
              )}

              <Button
                type="submit"
                disabled={isLoading || !email}
                className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg"
              >
                {isLoading ? '送信中...' : 'リセットメールを送信'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
