'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, Loader2, AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getMe, updateProfile } from '@/lib/api/auth';
import type { Profile, ApiError } from '@/lib/api/types';

export default function ProfileEditPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // フォーム入力状態
  const [lastName, setLastName] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastNameKana, setLastNameKana] = useState('');
  const [firstNameKana, setFirstNameKana] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [email, setEmail] = useState('');
  // 住所
  const [postalCode, setPostalCode] = useState('');
  const [prefecture, setPrefecture] = useState('');
  const [city, setCity] = useState('');
  const [address1, setAddress1] = useState('');
  const [address2, setAddress2] = useState('');

  // プロフィール情報を取得
  useEffect(() => {
    const fetchProfile = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getMe();
        setProfile(data);
        // フォームの初期値を設定
        setLastName(data.lastName || '');
        setFirstName(data.firstName || '');
        setLastNameKana(data.lastNameKana || '');
        setFirstNameKana(data.firstNameKana || '');
        setPhoneNumber(data.phoneNumber || '');
        setEmail(data.email || '');
        // 住所
        setPostalCode(data.postalCode || '');
        setPrefecture(data.prefecture || '');
        setCity(data.city || '');
        setAddress1(data.addressLine1 || '');
        setAddress2(data.addressLine2 || '');
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

  const handleSave = async () => {
    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      const updatedProfile = await updateProfile({
        lastName,
        firstName,
        lastNameKana,
        firstNameKana,
        phoneNumber,
        // emailの変更はセキュリティ上別の処理が必要な場合が多い
      });
      setProfile(updatedProfile);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.status === 401) {
        router.push('/login');
        return;
      }
      setSaveError(apiError.message || 'プロフィールの保存に失敗しました');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
            <Link href="/settings" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <h1 className="text-xl font-bold text-gray-800">プロフィール編集</h1>
          </div>
        </header>
        <main className="max-w-[390px] mx-auto px-4 py-6 pb-24 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </main>
        <BottomTabBar />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
            <Link href="/settings" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <h1 className="text-xl font-bold text-gray-800">プロフィール編集</h1>
          </div>
        </header>
        <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
          <Card className="rounded-xl shadow-md border-red-200">
            <CardContent className="p-6">
              <div className="flex items-center gap-2 text-red-600">
                <AlertCircle className="h-5 w-5" />
                <p className="text-sm">{error}</p>
              </div>
            </CardContent>
          </Card>
        </main>
        <BottomTabBar />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/settings" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">プロフィール編集</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        {saveSuccess && (
          <div className="mb-4 p-3 rounded-lg bg-green-50 border border-green-200">
            <p className="text-sm text-green-800">プロフィールを保存しました</p>
          </div>
        )}

        {saveError && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200">
            <div className="flex items-center gap-2 text-red-600">
              <AlertCircle className="h-4 w-4" />
              <p className="text-sm">{saveError}</p>
            </div>
          </div>
        )}

        <Card className="rounded-xl shadow-sm mb-4">
          <CardContent className="p-4">
            <h2 className="text-base font-semibold text-gray-800 mb-3">保護者情報</h2>

            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label htmlFor="lastName" className="text-xs font-medium text-gray-700 mb-1 block">
                    姓
                  </Label>
                  <Input
                    id="lastName"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    className="h-9 text-sm"
                    disabled={isSaving}
                  />
                </div>
                <div>
                  <Label htmlFor="firstName" className="text-xs font-medium text-gray-700 mb-1 block">
                    名
                  </Label>
                  <Input
                    id="firstName"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    className="h-9 text-sm"
                    disabled={isSaving}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label htmlFor="lastNameKana" className="text-xs font-medium text-gray-700 mb-1 block">
                    セイ
                  </Label>
                  <Input
                    id="lastNameKana"
                    value={lastNameKana}
                    onChange={(e) => setLastNameKana(e.target.value)}
                    className="h-9 text-sm"
                    placeholder="カタカナ"
                    disabled={isSaving}
                  />
                </div>
                <div>
                  <Label htmlFor="firstNameKana" className="text-xs font-medium text-gray-700 mb-1 block">
                    メイ
                  </Label>
                  <Input
                    id="firstNameKana"
                    value={firstNameKana}
                    onChange={(e) => setFirstNameKana(e.target.value)}
                    className="h-9 text-sm"
                    placeholder="カタカナ"
                    disabled={isSaving}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="phoneNumber" className="text-xs font-medium text-gray-700 mb-1 block">
                  携帯電話番号
                </Label>
                <Input
                  id="phoneNumber"
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="h-9 text-sm"
                  placeholder="090-1234-5678"
                  disabled={isSaving}
                />
              </div>

              <div>
                <Label htmlFor="email" className="text-xs font-medium text-gray-700 mb-1 block">
                  メールアドレス
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  className="h-9 text-sm bg-gray-100"
                  disabled
                />
                <p className="text-xs text-gray-500 mt-1">※メールアドレスの変更は別途お問い合わせください</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Button
          onClick={handleSave}
          disabled={isSaving}
          className="w-full h-12 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold disabled:opacity-50"
        >
          {isSaving ? (
            <span className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              保存中...
            </span>
          ) : (
            '保存する'
          )}
        </Button>
      </main>

      <BottomTabBar />
    </div>
  );
}
