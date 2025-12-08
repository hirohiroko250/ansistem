'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { InputOTP, InputOTPGroup, InputOTPSlot } from '@/components/ui/input-otp';
import { ChevronLeft, Check, Smartphone } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function PasswordResetPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSendSMS = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      setStep(2);
    }, 1000);
  };

  const handleVerifyOTP = (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length !== 6) return;
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      setStep(3);
    }, 1000);
  };

  const handleResetPassword = (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      alert('パスワードが一致しません');
      return;
    }
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      setStep(4);
    }, 1000);
  };

  const handleResendCode = () => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      alert('認証コードを再送信しました');
    }, 1000);
  };

  if (step === 4) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center px-4">
        <div className="text-center max-w-[390px] w-full">
          <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-6">
            <Check className="w-10 h-10 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-3">パスワード変更完了</h2>
          <p className="text-gray-600 mb-8">
            パスワードの変更が完了しました。<br />
            新しいパスワードでログインしてください。
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
        <div className="mb-6">
          <div className="flex items-center justify-center space-x-2">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`h-2 flex-1 rounded-full transition-colors ${
                  s <= step ? 'bg-blue-500' : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
          <p className="text-center text-sm text-gray-600 mt-2">
            Step {step} / 3
          </p>
        </div>

        {step === 1 && (
          <Card className="rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 mb-4">
                  <Smartphone className="h-8 w-8 text-blue-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-800 mb-2">電話番号確認</h2>
                <p className="text-sm text-gray-600">
                  登録済みの電話番号に認証コードを送信します
                </p>
              </div>

              <form onSubmit={handleSendSMS} className="space-y-5">
                <div>
                  <Label htmlFor="phone" className="text-sm font-medium text-gray-700 mb-2 block">
                    電話番号 <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="phone"
                    type="tel"
                    placeholder="090-1234-5678"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="rounded-xl h-12"
                    required
                  />
                </div>

                <Button
                  type="submit"
                  disabled={isLoading}
                  className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg"
                >
                  {isLoading ? '送信中...' : 'SMSを送信する'}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {step === 2 && (
          <Card className="rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-gray-800 mb-2">認証コード入力</h2>
                <p className="text-sm text-gray-600">
                  {phone} に送信された6桁のコードを入力してください
                </p>
              </div>

              <form onSubmit={handleVerifyOTP} className="space-y-5">
                <div className="flex justify-center">
                  <InputOTP
                    maxLength={6}
                    value={otp}
                    onChange={(value) => setOtp(value)}
                  >
                    <InputOTPGroup>
                      <InputOTPSlot index={0} className="w-12 h-14 text-lg rounded-lg" />
                      <InputOTPSlot index={1} className="w-12 h-14 text-lg rounded-lg" />
                      <InputOTPSlot index={2} className="w-12 h-14 text-lg rounded-lg" />
                      <InputOTPSlot index={3} className="w-12 h-14 text-lg rounded-lg" />
                      <InputOTPSlot index={4} className="w-12 h-14 text-lg rounded-lg" />
                      <InputOTPSlot index={5} className="w-12 h-14 text-lg rounded-lg" />
                    </InputOTPGroup>
                  </InputOTP>
                </div>

                <Button
                  type="submit"
                  disabled={isLoading || otp.length !== 6}
                  className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg"
                >
                  {isLoading ? '認証中...' : '認証する'}
                </Button>

                <div className="text-center">
                  <button
                    type="button"
                    onClick={handleResendCode}
                    disabled={isLoading}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    コードを再送する
                  </button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {step === 3 && (
          <Card className="rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-gray-800 mb-2">新しいパスワード設定</h2>
                <p className="text-sm text-gray-600">
                  新しいパスワードを入力してください
                </p>
              </div>

              <form onSubmit={handleResetPassword} className="space-y-5">
                <div>
                  <Label htmlFor="newPassword" className="text-sm font-medium text-gray-700 mb-2 block">
                    新しいパスワード <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="newPassword"
                    type="password"
                    placeholder="8文字以上"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="rounded-xl h-12"
                    required
                    minLength={8}
                  />
                  <p className="text-xs text-gray-600 mt-1">
                    半角英数字を含む8文字以上で設定してください
                  </p>
                </div>

                <div>
                  <Label htmlFor="confirmPassword" className="text-sm font-medium text-gray-700 mb-2 block">
                    パスワード再入力 <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="もう一度入力してください"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="rounded-xl h-12"
                    required
                    minLength={8}
                  />
                </div>

                <Button
                  type="submit"
                  disabled={isLoading}
                  className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg"
                >
                  {isLoading ? '変更中...' : 'パスワードを変更する'}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
