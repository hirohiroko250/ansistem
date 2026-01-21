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
import { useUser, useUpdateProfile } from '@/lib/hooks/use-user';
import type { ApiError } from '@/lib/api/types';
import { AuthGuard } from '@/components/auth';

function ProfileEditContent() {
  const router = useRouter();
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // React Queryフック
  const { data: profile, isLoading, error: queryError } = useUser();
  const updateProfileMutation = useUpdateProfile();

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

  // プロフィールデータが読み込まれたらフォームを初期化
  useEffect(() => {
    if (profile) {
      setLastName(profile.lastName || '');
      setFirstName(profile.firstName || '');
      setLastNameKana(profile.lastNameKana || '');
      setFirstNameKana(profile.firstNameKana || '');
      setPhoneNumber(profile.phoneNumber || '');
      setEmail(profile.email || '');
      setPostalCode(profile.postalCode || '');
      setPrefecture(profile.prefecture || '');
      setCity(profile.city || '');
      setAddress1(profile.address1 || '');
      setAddress2(profile.address2 || '');
    }
  }, [profile]);

  const error = queryError ? 'プロフィール情報の取得に失敗しました' : null;
  const isSaving = updateProfileMutation.isPending;

  const handleSave = () => {
    setSaveError(null);
    setSaveSuccess(false);

    updateProfileMutation.mutate(
      {
        lastName,
        firstName,
        lastNameKana,
        firstNameKana,
        phoneNumber,
        postalCode,
        prefecture,
        city,
        address1,
        address2,
      },
      {
        onSuccess: () => {
          setSaveSuccess(true);
          setTimeout(() => setSaveSuccess(false), 3000);
        },
        onError: (err: unknown) => {
          const apiError = err as ApiError | undefined;
          if (apiError?.status === 401) {
            router.push('/login');
            return;
          }
          setSaveError(apiError?.message || 'プロフィールの保存に失敗しました');
        },
      }
    );
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

        <Card className="rounded-xl shadow-sm mb-4">
          <CardContent className="p-4">
            <h2 className="text-base font-semibold text-gray-800 mb-3">住所</h2>

            <div className="space-y-3">
              <div>
                <Label htmlFor="postalCode" className="text-xs font-medium text-gray-700 mb-1 block">
                  郵便番号
                </Label>
                <Input
                  id="postalCode"
                  value={postalCode}
                  onChange={(e) => setPostalCode(e.target.value)}
                  className="h-9 text-sm w-32"
                  placeholder="123-4567"
                  disabled={isSaving}
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label htmlFor="prefecture" className="text-xs font-medium text-gray-700 mb-1 block">
                    都道府県
                  </Label>
                  <Input
                    id="prefecture"
                    value={prefecture}
                    onChange={(e) => setPrefecture(e.target.value)}
                    className="h-9 text-sm"
                    placeholder="東京都"
                    disabled={isSaving}
                  />
                </div>
                <div>
                  <Label htmlFor="city" className="text-xs font-medium text-gray-700 mb-1 block">
                    市区町村
                  </Label>
                  <Input
                    id="city"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    className="h-9 text-sm"
                    placeholder="渋谷区"
                    disabled={isSaving}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="address1" className="text-xs font-medium text-gray-700 mb-1 block">
                  番地・建物名
                </Label>
                <Input
                  id="address1"
                  value={address1}
                  onChange={(e) => setAddress1(e.target.value)}
                  className="h-9 text-sm"
                  placeholder="1-2-3 サンプルビル101"
                  disabled={isSaving}
                />
              </div>

              <div>
                <Label htmlFor="address2" className="text-xs font-medium text-gray-700 mb-1 block">
                  建物名・部屋番号（任意）
                </Label>
                <Input
                  id="address2"
                  value={address2}
                  onChange={(e) => setAddress2(e.target.value)}
                  className="h-9 text-sm"
                  placeholder=""
                  disabled={isSaving}
                />
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

export default function ProfileEditPage() {
  return (
    <AuthGuard>
      <ProfileEditContent />
    </AuthGuard>
  );
}
