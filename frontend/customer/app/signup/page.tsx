'use client';

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { ChevronLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { register, checkEmail, checkPhone } from '@/lib/api/auth';
import { getPrefectures, getAreas, getSchoolsByArea } from '@/lib/api/schools';
import type { ApiError, Area, PublicSchool } from '@/lib/api/types';
import { GuestGuard } from '@/components/auth';

// ひらがなをカタカナに変換
const hiraganaToKatakana = (str: string): string => {
  return str.replace(/[\u3041-\u3096]/g, (char) => {
    return String.fromCharCode(char.charCodeAt(0) + 0x60);
  });
};

// 電話番号をハイフンなしの数字のみに変換
const formatPhoneNumber = (value: string): string => {
  return value.replace(/[^0-9]/g, '');
};

const brands = [
  { id: 'soroban', name: 'そろばん' },
  { id: 'elementary-juku', name: '小学生塾' },
  { id: 'junior-high-juku', name: '中学生塾' },
  { id: 'high-school-juku', name: '高校生塾' },
  { id: 'gakudo', name: '学童保育' },
  { id: 'eikaiwa', name: '英会話' },
  { id: 'eiken', name: '英検' },
  { id: 'shodo', name: '習字' },
  { id: 'shogi', name: '将棋' },
  { id: 'programming', name: 'プログラミング' },
];

const referralSources = [
  { id: 'flyer', name: 'チラシ' },
  { id: 'posting', name: 'ポスティング' },
  { id: 'website', name: 'ウェブサイト' },
  { id: 'sns', name: 'SNS' },
  { id: 'friend', name: '友人・知人の紹介' },
  { id: 'school', name: '学校' },
  { id: 'other', name: 'その他' },
];


function SignupContent() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    lastName: '',
    firstName: '',
    lastNameKana: '',
    firstNameKana: '',
    phone: '',
    email: '',
    emailConfirm: '',
    password: '',
    passwordConfirm: '',
    // 住所
    postalCode: '',
    prefecture: '',
    city: '',
    address1: '',
    address2: '',
    // 近隣校舎
    selectedPrefecture: '',
    selectedCity: '',
    nearestSchool: '',
    selectedBrands: [] as string[],
    referralSource: '',
    expectations: '',
  });
  const [errors, setErrors] = useState({ email: '', phone: '', password: '', api: '' });
  const [isLoading, setIsLoading] = useState(false);

  // IME入力追跡用
  const lastNameCompositionRef = useRef<string>('');
  const firstNameCompositionRef = useRef<string>('');

  // 姓のIME入力ハンドラー
  const handleLastNameComposition = (e: React.CompositionEvent<HTMLInputElement>) => {
    if (e.type === 'compositionupdate') {
      lastNameCompositionRef.current = e.data;
    } else if (e.type === 'compositionend') {
      // IME確定時にカタカナに変換してセット
      const katakana = hiraganaToKatakana(lastNameCompositionRef.current);
      if (katakana) {
        setFormData(prev => ({ ...prev, lastNameKana: katakana }));
      }
      lastNameCompositionRef.current = '';
    }
  };

  // 名のIME入力ハンドラー
  const handleFirstNameComposition = (e: React.CompositionEvent<HTMLInputElement>) => {
    if (e.type === 'compositionupdate') {
      firstNameCompositionRef.current = e.data;
    } else if (e.type === 'compositionend') {
      // IME確定時にカタカナに変換してセット
      const katakana = hiraganaToKatakana(firstNameCompositionRef.current);
      if (katakana) {
        setFormData(prev => ({ ...prev, firstNameKana: katakana }));
      }
      firstNameCompositionRef.current = '';
    }
  };

  // 電話番号入力ハンドラー（数字のみ）
  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value);
    setFormData({ ...formData, phone: formatted });
  };

  // 都道府県・市区町村・校舎データを取得
  const [prefectures, setPrefectures] = useState<string[]>([]);
  const [cities, setCities] = useState<Area[]>([]);
  const [schools, setSchools] = useState<PublicSchool[]>([]);
  const [isLoadingPrefectures, setIsLoadingPrefectures] = useState(false);
  const [isLoadingCities, setIsLoadingCities] = useState(false);
  const [isLoadingSchools, setIsLoadingSchools] = useState(false);

  // 都道府県一覧を取得
  useEffect(() => {
    const fetchPrefectures = async () => {
      setIsLoadingPrefectures(true);
      try {
        const data = await getPrefectures();
        setPrefectures(data);
      } catch (error) {
        console.error('Failed to fetch prefectures:', error);
      } finally {
        setIsLoadingPrefectures(false);
      }
    };
    fetchPrefectures();
  }, []);

  // 都道府県が選択されたら市区町村一覧を取得
  useEffect(() => {
    if (!formData.selectedPrefecture) {
      setCities([]);
      return;
    }

    const fetchCities = async () => {
      setIsLoadingCities(true);
      try {
        const data = await getAreas(formData.selectedPrefecture);
        setCities(data);
      } catch (error) {
        console.error('Failed to fetch cities:', error);
        setCities([]);
      } finally {
        setIsLoadingCities(false);
      }
    };
    fetchCities();
  }, [formData.selectedPrefecture]);

  // 市区町村が選択されたら校舎一覧を取得
  useEffect(() => {
    if (!formData.selectedCity) {
      setSchools([]);
      return;
    }

    const fetchSchools = async () => {
      setIsLoadingSchools(true);
      try {
        const data = await getSchoolsByArea(formData.selectedCity);
        setSchools(data);
      } catch (error) {
        console.error('Failed to fetch schools:', error);
        setSchools([]);
      } finally {
        setIsLoadingSchools(false);
      }
    };
    fetchSchools();
  }, [formData.selectedCity]);

  // 郵便番号から住所を自動取得
  const [isLoadingAddress, setIsLoadingAddress] = useState(false);

  const fetchAddressFromPostalCode = async (postalCode: string) => {
    // ハイフンを除去して7桁の数字のみにする
    const cleanedCode = postalCode.replace(/-/g, '');
    if (cleanedCode.length !== 7) return;

    setIsLoadingAddress(true);
    try {
      const response = await fetch(`https://zipcloud.ibsnet.co.jp/api/search?zipcode=${cleanedCode}`);
      const data = await response.json();

      if (data.results && data.results.length > 0) {
        const result = data.results[0];
        setFormData(prev => ({
          ...prev,
          prefecture: result.address1,
          city: result.address2,
          address1: result.address3,
        }));
      }
    } catch (error) {
      console.error('Failed to fetch address:', error);
    } finally {
      setIsLoadingAddress(false);
    }
  };

  // 郵便番号入力時のハンドラー
  const handlePostalCodeChange = (value: string) => {
    setFormData({ ...formData, postalCode: value });

    // 7桁（ハイフンあり8桁）入力されたら自動検索
    const cleanedCode = value.replace(/-/g, '');
    if (cleanedCode.length === 7) {
      fetchAddressFromPostalCode(value);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (step === 1) {
      const newErrors = { email: '', phone: '', password: '', api: '' };

      if (formData.email !== formData.emailConfirm) {
        newErrors.email = 'メールアドレスが一致しません';
      }

      if (formData.password !== formData.passwordConfirm) {
        newErrors.password = 'パスワードが一致しません';
      }

      if (newErrors.email || newErrors.password) {
        setErrors(newErrors);
        return;
      }

      // メールアドレスと電話番号の重複チェック
      setIsLoading(true);
      try {
        // メールアドレスチェック
        const emailResult = await checkEmail(formData.email);
        if (!emailResult.available) {
          setErrors({ email: emailResult.message, phone: '', password: '', api: '' });
          setIsLoading(false);
          return;
        }

        // 電話番号チェック
        const phoneResult = await checkPhone(formData.phone);
        if (!phoneResult.available) {
          setErrors({ email: '', phone: phoneResult.message, password: '', api: '' });
          setIsLoading(false);
          return;
        }
      } catch (err) {
        // APIエラーの場合は次のステップへ進める（登録時に再チェック）
        console.error('Validation check failed:', err);
      } finally {
        setIsLoading(false);
      }

      setErrors({ email: '', phone: '', password: '', api: '' });
    }

    if (step < 3) {
      setStep(step + 1);
    } else {
      // Step 3 完了時に API 呼び出し
      setIsLoading(true);
      setErrors({ email: '', phone: '', password: '', api: '' });

      try {
        await register({
          email: formData.email,
          password: formData.password,
          fullName: `${formData.lastName} ${formData.firstName}`,
          fullNameKana: `${formData.lastNameKana} ${formData.firstNameKana}`,
          phone: formData.phone,
          // 住所
          postalCode: formData.postalCode || undefined,
          prefecture: formData.prefecture || undefined,
          city: formData.city || undefined,
          address1: formData.address1 || undefined,
          address2: formData.address2 || undefined,
          // 近隣校舎・その他
          nearestSchoolId: formData.nearestSchool || undefined,
          interestedBrands: formData.selectedBrands.length > 0 ? formData.selectedBrands : undefined,
          referralSource: formData.referralSource || undefined,
          expectations: formData.expectations || undefined,
        });

        // 登録成功後、子供追加画面へ遷移
        router.push('/children');
      } catch (err) {
        let errorMessage = '登録に失敗しました。入力内容をご確認ください。';

        // エラーオブジェクトから適切にメッセージを抽出
        if (err && typeof err === 'object') {
          const apiError = err as ApiError;
          if (apiError.status === 400) {
            // 詳細エラーがある場合は、それを表示
            if (apiError.errors && typeof apiError.errors === 'object') {
              const errorDetails: string[] = [];
              for (const [field, messages] of Object.entries(apiError.errors)) {
                if (Array.isArray(messages)) {
                  errorDetails.push(...messages);
                }
              }
              if (errorDetails.length > 0) {
                errorMessage = errorDetails.join('\n');
              } else if (typeof apiError.message === 'string') {
                errorMessage = apiError.message;
              }
            } else if (typeof apiError.message === 'string') {
              errorMessage = apiError.message;
            } else {
              errorMessage = 'メールアドレスが既に使用されているか、入力内容に問題があります。';
            }
          } else if (apiError.status === 429) {
            errorMessage = 'リクエストが多すぎます。しばらく待ってからお試しください。';
          } else if (apiError.status >= 500) {
            errorMessage = 'サーバーエラーが発生しました。しばらく待ってからお試しください。';
          } else if (typeof apiError.message === 'string') {
            errorMessage = apiError.message;
          }
        }

        setErrors(prev => ({ ...prev, api: errorMessage }));
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleBrandToggle = (brandId: string) => {
    setFormData(prev => ({
      ...prev,
      selectedBrands: prev.selectedBrands.includes(brandId)
        ? prev.selectedBrands.filter(id => id !== brandId)
        : [...prev.selectedBrands, brandId]
    }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/login" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">新規登録</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6">
        <div className="mb-6">
          <div className="flex items-center justify-center space-x-2">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`h-2 flex-1 rounded-full transition-colors ${s <= step ? 'bg-blue-500' : 'bg-gray-200'
                  }`}
              />
            ))}
          </div>
          <p className="text-center text-sm text-gray-600 mt-2">
            Step {step} / 3
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {step === 1 && (
            <Card className="rounded-2xl shadow-lg mb-6">
              <CardContent className="p-6 space-y-5">
                <div>
                  <h2 className="text-lg font-bold text-gray-800">保護者情報</h2>
                  <p className="text-sm text-orange-600 mt-1">※ 保護者名で登録してください</p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="lastName" className="text-sm font-medium text-gray-700 mb-2 block">
                      姓 <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="lastName"
                      placeholder="山田"
                      value={formData.lastName}
                      onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                      onCompositionUpdate={handleLastNameComposition}
                      onCompositionEnd={handleLastNameComposition}
                      className="rounded-xl h-12"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="firstName" className="text-sm font-medium text-gray-700 mb-2 block">
                      名 <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="firstName"
                      placeholder="太郎"
                      value={formData.firstName}
                      onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                      onCompositionUpdate={handleFirstNameComposition}
                      onCompositionEnd={handleFirstNameComposition}
                      className="rounded-xl h-12"
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="lastNameKana" className="text-sm font-medium text-gray-700 mb-2 block">
                      セイ <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="lastNameKana"
                      placeholder="ヤマダ"
                      value={formData.lastNameKana}
                      onChange={(e) => setFormData({ ...formData, lastNameKana: e.target.value })}
                      className="rounded-xl h-12"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="firstNameKana" className="text-sm font-medium text-gray-700 mb-2 block">
                      メイ <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="firstNameKana"
                      placeholder="タロウ"
                      value={formData.firstNameKana}
                      onChange={(e) => setFormData({ ...formData, firstNameKana: e.target.value })}
                      className="rounded-xl h-12"
                      required
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="phone" className="text-sm font-medium text-gray-700 mb-2 block">
                    携帯電話番号 <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="phone"
                    type="tel"
                    inputMode="numeric"
                    placeholder="09012345678"
                    value={formData.phone}
                    onChange={handlePhoneChange}
                    className={`rounded-xl h-12 ${errors.phone ? 'border-red-500' : ''}`}
                    maxLength={11}
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">ハイフンなしで入力してください</p>
                  {errors.phone && (
                    <p className="text-xs text-red-600 mt-1">{errors.phone}</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="email" className="text-sm font-medium text-gray-700 mb-2 block">
                    メールアドレス <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="example@mail.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="rounded-xl h-12"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="emailConfirm" className="text-sm font-medium text-gray-700 mb-2 block">
                    メールアドレス（確認） <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="emailConfirm"
                    type="email"
                    placeholder="もう一度入力してください"
                    value={formData.emailConfirm}
                    onChange={(e) => setFormData({ ...formData, emailConfirm: e.target.value })}
                    className="rounded-xl h-12"
                    required
                  />
                  {errors.email && (
                    <p className="text-xs text-red-600 mt-1">{errors.email}</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="password" className="text-sm font-medium text-gray-700 mb-2 block">
                    パスワード <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="8文字以上"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="rounded-xl h-12"
                    required
                    minLength={8}
                  />
                  <p className="text-xs text-gray-600 mt-1">
                    半角英数字を含む8文字以上で設定してください
                  </p>
                </div>

                <div>
                  <Label htmlFor="passwordConfirm" className="text-sm font-medium text-gray-700 mb-2 block">
                    パスワード（確認） <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="passwordConfirm"
                    type="password"
                    placeholder="もう一度入力してください"
                    value={formData.passwordConfirm}
                    onChange={(e) => setFormData({ ...formData, passwordConfirm: e.target.value })}
                    className="rounded-xl h-12"
                    required
                    minLength={8}
                  />
                  {errors.password && (
                    <p className="text-xs text-red-600 mt-1">{errors.password}</p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {step === 2 && (
            <div className="space-y-6">
              {/* 住所入力 */}
              <Card className="rounded-2xl shadow-lg">
                <CardContent className="p-6 space-y-5">
                  <h2 className="text-lg font-bold text-gray-800 mb-4">ご住所</h2>

                  <div>
                    <Label htmlFor="postalCode" className="text-sm font-medium text-gray-700 mb-2 block">
                      郵便番号 <span className="text-red-500">*</span>
                    </Label>
                    <div className="relative">
                      <Input
                        id="postalCode"
                        placeholder="123-4567"
                        value={formData.postalCode}
                        onChange={(e) => handlePostalCodeChange(e.target.value)}
                        className="rounded-xl h-12"
                        required
                      />
                      {isLoadingAddress && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2">
                          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      7桁入力で住所が自動入力されます
                    </p>
                  </div>

                  <div>
                    <Label htmlFor="prefecture" className="text-sm font-medium text-gray-700 mb-2 block">
                      都道府県 <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="prefecture"
                      placeholder="愛知県"
                      value={formData.prefecture}
                      onChange={(e) => setFormData({ ...formData, prefecture: e.target.value })}
                      className="rounded-xl h-12"
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="city" className="text-sm font-medium text-gray-700 mb-2 block">
                      市区町村 <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="city"
                      placeholder="名古屋市中区"
                      value={formData.city}
                      onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                      className="rounded-xl h-12"
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="address1" className="text-sm font-medium text-gray-700 mb-2 block">
                      町名・番地 <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="address1"
                      placeholder="栄1-2-3"
                      value={formData.address1}
                      onChange={(e) => setFormData({ ...formData, address1: e.target.value })}
                      className="rounded-xl h-12"
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="address2" className="text-sm font-medium text-gray-700 mb-2 block">
                      建物名・部屋番号
                    </Label>
                    <Input
                      id="address2"
                      placeholder="○○マンション 101号室"
                      value={formData.address2}
                      onChange={(e) => setFormData({ ...formData, address2: e.target.value })}
                      className="rounded-xl h-12"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* 近隣校舎選択 */}
              <Card className="rounded-2xl shadow-lg">
                <CardContent className="p-6 space-y-5">
                  <h2 className="text-lg font-bold text-gray-800 mb-4">近隣校舎</h2>

                  <div>
                    <Label htmlFor="selectedPrefecture" className="text-sm font-medium text-gray-700 mb-2 block">
                      都道府県 <span className="text-red-500">*</span>
                    </Label>
                    <select
                      id="selectedPrefecture"
                      value={formData.selectedPrefecture}
                      onChange={(e) => setFormData({ ...formData, selectedPrefecture: e.target.value, selectedCity: '', nearestSchool: '' })}
                      className="w-full h-12 px-3 rounded-xl border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                      disabled={isLoadingPrefectures}
                    >
                      <option value="">
                        {isLoadingPrefectures ? '読み込み中...' : '都道府県を選択してください'}
                      </option>
                      {prefectures.map((pref) => (
                        <option key={pref} value={pref}>
                          {pref}
                        </option>
                      ))}
                    </select>
                  </div>

                  {formData.selectedPrefecture && (
                    <div>
                      <Label htmlFor="selectedCity" className="text-sm font-medium text-gray-700 mb-2 block">
                        市区町村 <span className="text-red-500">*</span>
                      </Label>
                      <select
                        id="selectedCity"
                        value={formData.selectedCity}
                        onChange={(e) => setFormData({ ...formData, selectedCity: e.target.value, nearestSchool: '' })}
                        className="w-full h-12 px-3 rounded-xl border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                        disabled={isLoadingCities}
                      >
                        <option value="">
                          {isLoadingCities ? '読み込み中...' : '市区町村を選択してください'}
                        </option>
                        {cities.map((city) => (
                          <option key={city.id} value={city.name}>
                            {city.name}（{city.schoolCount}校）
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {formData.selectedCity && (
                    <div>
                      <Label htmlFor="nearestSchool" className="text-sm font-medium text-gray-700 mb-2 block">
                        近隣校舎 <span className="text-red-500">*</span>
                      </Label>
                      <select
                        id="nearestSchool"
                        value={formData.nearestSchool}
                        onChange={(e) => setFormData({ ...formData, nearestSchool: e.target.value })}
                        className="w-full h-12 px-3 rounded-xl border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                        disabled={isLoadingSchools}
                      >
                        <option value="">
                          {isLoadingSchools ? '読み込み中...' : '校舎を選択してください'}
                        </option>
                        {schools.map((school) => (
                          <option key={school.id} value={school.id}>
                            {school.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6">
              <Card className="rounded-2xl shadow-lg">
                <CardContent className="p-6 space-y-4">
                  <div>
                    <h2 className="text-lg font-bold text-gray-800 mb-2">興味のあるブランド</h2>
                    <p className="text-sm text-gray-600 mb-4">複数選択可能です</p>
                  </div>

                  <div className="space-y-2">
                    {brands.map((brand) => (
                      <div
                        key={brand.id}
                        className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <Checkbox
                          id={`brand-${brand.id}`}
                          checked={formData.selectedBrands.includes(brand.id)}
                          onCheckedChange={() => handleBrandToggle(brand.id)}
                        />
                        <label
                          htmlFor={`brand-${brand.id}`}
                          className="flex-1 text-sm font-medium text-gray-800 cursor-pointer"
                        >
                          {brand.name}
                        </label>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-2xl shadow-lg">
                <CardContent className="p-6 space-y-4">
                  <div>
                    <Label htmlFor="referralSource" className="text-sm font-medium text-gray-700 mb-2 block">
                      何で知りましたか？ <span className="text-red-500">*</span>
                    </Label>
                    <select
                      id="referralSource"
                      value={formData.referralSource}
                      onChange={(e) => setFormData({ ...formData, referralSource: e.target.value })}
                      className="w-full h-12 px-3 rounded-xl border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    >
                      <option value="">選択してください</option>
                      {referralSources.map((source) => (
                        <option key={source.id} value={source.id}>
                          {source.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-2xl shadow-lg">
                <CardContent className="p-6 space-y-4">
                  <div>
                    <Label htmlFor="expectations" className="text-sm font-medium text-gray-700 mb-2 block">
                      このサービスに期待すること
                    </Label>
                    <Textarea
                      id="expectations"
                      placeholder="自由にご記入ください"
                      value={formData.expectations}
                      onChange={(e) => setFormData({ ...formData, expectations: e.target.value })}
                      className="rounded-xl min-h-[120px]"
                    />
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          <div className="mt-6 space-y-3">
            {errors.api && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                <p className="text-sm text-red-600">{errors.api}</p>
              </div>
            )}

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  登録中...
                </>
              ) : (
                step === 3 ? '登録する' : '次へ'
              )}
            </Button>

            {step > 1 && (
              <Button
                type="button"
                onClick={() => setStep(step - 1)}
                disabled={isLoading}
                variant="outline"
                className="w-full h-12 rounded-full border-2 border-gray-300 text-gray-700 font-semibold disabled:opacity-50"
              >
                戻る
              </Button>
            )}
          </div>
        </form>
      </main>
    </div>
  );
}

export default function SignupPage() {
  return (
    <GuestGuard>
      <SignupContent />
    </GuestGuard>
  );
}
