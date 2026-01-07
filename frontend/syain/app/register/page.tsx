'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { GraduationCap, ChevronLeft, ChevronRight, Camera, Search, Train, Car } from 'lucide-react';
import api from '@/lib/api/client';

// 型定義
interface Department {
  name: string;
}

interface Position {
  id: string;
  position_name: string;
}

interface School {
  id: string;
  schoolName: string;
  schoolCode: string;
}

interface Brand {
  id: string;
  brandName: string;
  brandCode: string;
}

interface Tenant {
  id: string;
  tenantCode: string;
  tenantName: string;
}

// 都道府県リスト
const PREFECTURES = [
  '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
  '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
  '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
  '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
  '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
  '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
  '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県',
];

export default function RegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // マスタデータ
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);

  // フォームデータ
  const [formData, setFormData] = useState({
    // 基本情報
    lastName: '',
    firstName: '',
    email: '',
    phone: '',
    password: '',
    passwordConfirm: '',
    birthDate: '',

    // 所属情報
    tenantId: '',
    department: '',
    positionId: '',
    positionText: '',

    // 対応校舎・ブランド
    schoolIds: [] as string[],
    brandIds: [] as string[],

    // 雇用情報
    hireDate: '',

    // 住所情報
    postalCode: '',
    prefecture: '',
    city: '',
    address: '',
    nationality: '日本',

    // 通勤情報
    nearestStation: '',
    commutingMethod: '' as '' | 'train' | 'car' | 'both',
  });

  // 顔写真
  const [profileImage, setProfileImage] = useState<string | null>(null);
  const [profileImageFile, setProfileImageFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [addressLoading, setAddressLoading] = useState(false);

  // マスタデータの取得
  useEffect(() => {
    const fetchMasterData = async () => {
      try {
        // テナント（会社）一覧を取得（公開API）
        const tenantsRes = await api.get<any>('/tenants/tenants/', { skipAuth: true });
        const tenantsList = tenantsRes?.data || tenantsRes?.results || (Array.isArray(tenantsRes) ? tenantsRes : []);
        setTenants(tenantsList);

        // 校舎一覧を取得（公開API）- 配列で返ってくる
        const schoolsRes = await api.get<School[]>('/schools/public/schools/', { skipAuth: true });
        setSchools(Array.isArray(schoolsRes) ? schoolsRes : []);

        // ブランド一覧を取得（公開API）- カテゴリー配列で返ってくる
        const brandsRes = await api.get<any>('/schools/public/brand-categories/', { skipAuth: true });
        const categories = brandsRes?.data || brandsRes || [];
        // カテゴリーからブランドをフラットに取得
        const allBrands: Brand[] = [];
        categories.forEach((cat: any) => {
          if (cat.brands && Array.isArray(cat.brands)) {
            allBrands.push(...cat.brands);
          }
        });
        setBrands(allBrands);
      } catch (err) {
        console.error('マスタデータ取得エラー:', err);
      }
    };
    fetchMasterData();
  }, []);

  // テナント変更時に部署・役職を取得
  useEffect(() => {
    const fetchTenantData = async () => {
      if (!formData.tenantId) {
        setDepartments([]);
        setPositions([]);
        return;
      }

      try {
        // 部署一覧を取得（公開API）
        const deptRes = await api.get<Department[]>('/tenants/departments/', {
          skipAuth: true,
          tenantId: formData.tenantId,
        });
        setDepartments(Array.isArray(deptRes) ? deptRes : []);

        // 役職一覧を取得（公開API）
        const posRes = await api.get<Position[]>('/tenants/positions/public/', {
          skipAuth: true,
          tenantId: formData.tenantId,
        });
        setPositions(Array.isArray(posRes) ? posRes : []);
      } catch (err) {
        console.error('テナントデータ取得エラー:', err);
      }
    };
    fetchTenantData();
  }, [formData.tenantId]);

  const updateFormData = (field: string, value: string | string[]) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const toggleSchool = (schoolId: string) => {
    setFormData(prev => ({
      ...prev,
      schoolIds: prev.schoolIds.includes(schoolId)
        ? prev.schoolIds.filter(id => id !== schoolId)
        : [...prev.schoolIds, schoolId],
    }));
  };

  const toggleBrand = (brandId: string) => {
    setFormData(prev => ({
      ...prev,
      brandIds: prev.brandIds.includes(brandId)
        ? prev.brandIds.filter(id => id !== brandId)
        : [...prev.brandIds, brandId],
    }));
  };

  // 郵便番号から住所を検索
  const searchAddress = async () => {
    const postalCode = formData.postalCode.replace(/-/g, '');
    if (postalCode.length !== 7) {
      setError('郵便番号は7桁で入力してください');
      return;
    }

    setAddressLoading(true);
    setError('');

    try {
      const response = await fetch(`https://zipcloud.ibsnet.co.jp/api/search?zipcode=${postalCode}`);
      const data = await response.json();

      if (data.status === 200 && data.results && data.results.length > 0) {
        const result = data.results[0];
        setFormData(prev => ({
          ...prev,
          prefecture: result.address1,
          city: result.address2 + result.address3,
        }));
      } else {
        setError('住所が見つかりませんでした');
      }
    } catch (err) {
      console.error('住所検索エラー:', err);
      setError('住所の検索に失敗しました');
    } finally {
      setAddressLoading(false);
    }
  };

  // 顔写真の選択
  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        setError('画像サイズは5MB以下にしてください');
        return;
      }

      setProfileImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setProfileImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const validateStep = (currentStep: number): boolean => {
    switch (currentStep) {
      case 1:
        if (!formData.lastName || !formData.firstName) {
          setError('姓名は必須です');
          return false;
        }
        if (!formData.email) {
          setError('メールアドレスは必須です');
          return false;
        }
        if (!formData.password || formData.password.length < 8) {
          setError('パスワードは8文字以上で入力してください');
          return false;
        }
        if (formData.password !== formData.passwordConfirm) {
          setError('パスワードが一致しません');
          return false;
        }
        break;
      case 2:
        if (!formData.tenantId) {
          setError('会社を選択してください');
          return false;
        }
        if (!formData.department) {
          setError('部署を入力してください');
          return false;
        }
        if (!formData.positionId && !formData.positionText) {
          setError('役職を選択または入力してください');
          return false;
        }
        break;
    }
    setError('');
    return true;
  };

  const nextStep = () => {
    if (validateStep(step)) {
      setStep(prev => Math.min(prev + 1, 4));
    }
  };

  const prevStep = () => {
    setError('');
    setStep(prev => Math.max(prev - 1, 1));
  };

  const handleSubmit = async () => {
    if (!validateStep(step)) return;

    setLoading(true);
    setError('');

    try {
      // FormDataを使って画像も送信
      const submitData = new FormData();
      submitData.append('last_name', formData.lastName);
      submitData.append('first_name', formData.firstName);
      submitData.append('email', formData.email);
      submitData.append('phone', formData.phone);
      submitData.append('password', formData.password);
      submitData.append('password_confirm', formData.passwordConfirm);
      submitData.append('tenant_id', formData.tenantId);
      submitData.append('department', formData.department);
      if (formData.positionId) submitData.append('position_id', formData.positionId);
      submitData.append('position_text', formData.positionText);
      formData.schoolIds.forEach(id => submitData.append('school_ids', id));
      formData.brandIds.forEach(id => submitData.append('brand_ids', id));
      if (formData.hireDate) submitData.append('hire_date', formData.hireDate);
      if (formData.birthDate) submitData.append('birth_date', formData.birthDate);
      submitData.append('postal_code', formData.postalCode);
      submitData.append('prefecture', formData.prefecture);
      submitData.append('city', formData.city);
      submitData.append('address', formData.address);
      submitData.append('nationality', formData.nationality);
      submitData.append('nearest_station', formData.nearestStation);
      submitData.append('commuting_method', formData.commutingMethod);

      if (profileImageFile) {
        submitData.append('profile_image', profileImageFile);
      }

      // multipart/form-dataで送信
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

      // デバッグ: 送信データをログ出力
      console.log('Submitting to:', `${apiUrl}/auth/register/employee/`);
      const formDataEntries: Record<string, string | File> = {};
      submitData.forEach((value, key) => {
        formDataEntries[key] = value;
      });
      console.log('Form data:', formDataEntries);

      const response = await fetch(`${apiUrl}/auth/register/employee/`, {
        method: 'POST',
        body: submitData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Registration error:', errorData);
        // エラーメッセージを詳細に表示
        let errorMessage = '登録に失敗しました';
        if (errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (typeof errorData === 'object') {
          // フィールドごとのエラーを表示
          const fieldErrors = Object.entries(errorData)
            .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
            .join('\n');
          errorMessage = fieldErrors || '登録に失敗しました';
        }
        throw new Error(errorMessage);
      }

      setSuccess(true);
    } catch (err: unknown) {
      const apiError = err as { message?: string };
      setError(apiError.message || '登録に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-xl border-0">
          <CardHeader className="space-y-1 text-center">
            <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <CardTitle className="text-2xl">登録完了</CardTitle>
            <CardDescription>
              社員登録が完了しました。<br />
              管理者の承認後、ログインが可能になります。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => router.push('/login')}
              className="w-full h-12 bg-blue-600 hover:bg-blue-700"
            >
              ログイン画面へ
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 py-6 px-4">
      <div className="max-w-md mx-auto">
        <div className="text-center mb-4">
          <div className="w-14 h-14 bg-blue-600 rounded-full flex items-center justify-center mb-3 shadow-lg mx-auto">
            <GraduationCap className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-xl font-bold text-gray-900">新規社員登録</h1>
          <p className="text-xs text-gray-600 mt-1">Employee Registration</p>
        </div>

        {/* ステップインジケーター */}
        <div className="flex justify-center mb-4">
          <div className="flex items-center space-x-1">
            {[1, 2, 3, 4].map(s => (
              <div key={s} className="flex items-center">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium ${
                    s === step
                      ? 'bg-blue-600 text-white'
                      : s < step
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {s < step ? '✓' : s}
                </div>
                {s < 4 && (
                  <div className={`w-6 h-0.5 ${s < step ? 'bg-green-500' : 'bg-gray-200'}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        <Card className="shadow-xl border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">
              {step === 1 && '基本情報'}
              {step === 2 && '所属情報'}
              {step === 3 && '対応校舎・ブランド'}
              {step === 4 && '住所・その他'}
            </CardTitle>
            <CardDescription className="text-xs">
              {step === 1 && 'お名前とログイン情報を入力'}
              {step === 2 && '所属会社と部署を選択'}
              {step === 3 && '校舎とブランドを選択'}
              {step === 4 && '住所と採用日を入力'}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="space-y-3">
              {/* Step 1: 基本情報 */}
              {step === 1 && (
                <>
                  {/* 顔写真アップロード */}
                  <div className="flex justify-center mb-2">
                    <div
                      className="relative w-24 h-24 rounded-full bg-gray-100 border-2 border-dashed border-gray-300 flex items-center justify-center cursor-pointer hover:border-blue-500 transition-colors overflow-hidden"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {profileImage ? (
                        <Image
                          src={profileImage}
                          alt="プロフィール写真"
                          fill
                          className="object-cover"
                        />
                      ) : (
                        <div className="text-center">
                          <Camera className="w-8 h-8 text-gray-400 mx-auto" />
                          <span className="text-xs text-gray-500">写真を追加</span>
                        </div>
                      )}
                    </div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleImageSelect}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="lastName">姓 <span className="text-red-500">*</span></Label>
                      <Input
                        id="lastName"
                        placeholder="山田"
                        value={formData.lastName}
                        onChange={(e) => updateFormData('lastName', e.target.value)}
                        className="h-10"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="firstName">名 <span className="text-red-500">*</span></Label>
                      <Input
                        id="firstName"
                        placeholder="太郎"
                        value={formData.firstName}
                        onChange={(e) => updateFormData('firstName', e.target.value)}
                        className="h-10"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="birthDate">生年月日</Label>
                    <Input
                      id="birthDate"
                      type="date"
                      value={formData.birthDate}
                      onChange={(e) => updateFormData('birthDate', e.target.value)}
                      className="h-10"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email">メールアドレス <span className="text-red-500">*</span></Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="example@email.com"
                      value={formData.email}
                      onChange={(e) => updateFormData('email', e.target.value)}
                      className="h-10"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">電話番号</Label>
                    <Input
                      id="phone"
                      type="tel"
                      placeholder="080-1234-5678"
                      value={formData.phone}
                      onChange={(e) => updateFormData('phone', e.target.value)}
                      className="h-10"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password">パスワード <span className="text-red-500">*</span></Label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="8文字以上"
                      value={formData.password}
                      onChange={(e) => updateFormData('password', e.target.value)}
                      className="h-10"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="passwordConfirm">パスワード（確認） <span className="text-red-500">*</span></Label>
                    <Input
                      id="passwordConfirm"
                      type="password"
                      placeholder="もう一度入力してください"
                      value={formData.passwordConfirm}
                      onChange={(e) => updateFormData('passwordConfirm', e.target.value)}
                      className="h-10"
                    />
                  </div>
                </>
              )}

              {/* Step 2: 所属情報 */}
              {step === 2 && (
                <>
                  <div className="space-y-2">
                    <Label>会社 <span className="text-red-500">*</span></Label>
                    <Select
                      value={formData.tenantId}
                      onValueChange={(value) => updateFormData('tenantId', value)}
                    >
                      <SelectTrigger className="h-10">
                        <SelectValue placeholder="会社を選択" />
                      </SelectTrigger>
                      <SelectContent>
                        {tenants.map(tenant => (
                          <SelectItem key={tenant.id} value={tenant.id}>
                            {tenant.tenantCode} - {tenant.tenantName}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>部署 <span className="text-red-500">*</span></Label>
                    <Select
                      value={formData.department}
                      onValueChange={(value) => updateFormData('department', value)}
                    >
                      <SelectTrigger className="h-10">
                        <SelectValue placeholder="部署を選択" />
                      </SelectTrigger>
                      <SelectContent>
                        {departments.map(dept => (
                          <SelectItem key={dept.name} value={dept.name}>
                            {dept.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input
                      placeholder="または部署名を入力"
                      value={formData.department}
                      onChange={(e) => updateFormData('department', e.target.value)}
                      className="h-12 mt-2"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>役職 <span className="text-red-500">*</span></Label>
                    <Select
                      value={formData.positionId}
                      onValueChange={(value) => updateFormData('positionId', value)}
                    >
                      <SelectTrigger className="h-10">
                        <SelectValue placeholder="役職を選択" />
                      </SelectTrigger>
                      <SelectContent>
                        {positions.map(pos => (
                          <SelectItem key={pos.id} value={pos.id}>
                            {pos.position_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="positionText">役職（テキスト）</Label>
                    <Input
                      id="positionText"
                      placeholder="マスタ未登録時の役職名"
                      value={formData.positionText}
                      onChange={(e) => updateFormData('positionText', e.target.value)}
                      className="h-10"
                    />
                  </div>
                </>
              )}

              {/* Step 3: 対応校舎・ブランド */}
              {step === 3 && (
                <>
                  <div className="space-y-2">
                    <Label>対応校舎</Label>
                    <div className="border rounded-lg p-4 max-h-48 overflow-y-auto space-y-2">
                      {schools.length === 0 ? (
                        <p className="text-sm text-gray-500">校舎データを取得中...</p>
                      ) : (
                        schools.map(school => (
                          <div key={school.id} className="flex items-center space-x-2">
                            <Checkbox
                              id={`school-${school.id}`}
                              checked={formData.schoolIds.includes(school.id)}
                              onCheckedChange={() => toggleSchool(school.id)}
                            />
                            <label
                              htmlFor={`school-${school.id}`}
                              className="text-sm cursor-pointer"
                            >
                              {school.schoolName} ({school.schoolCode})
                            </label>
                          </div>
                        ))
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      選択済み: {formData.schoolIds.length}校
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label>対応ブランド</Label>
                    <div className="border rounded-lg p-4 max-h-48 overflow-y-auto space-y-2">
                      {brands.length === 0 ? (
                        <p className="text-sm text-gray-500">ブランドデータを取得中...</p>
                      ) : (
                        brands.map(brand => (
                          <div key={brand.id} className="flex items-center space-x-2">
                            <Checkbox
                              id={`brand-${brand.id}`}
                              checked={formData.brandIds.includes(brand.id)}
                              onCheckedChange={() => toggleBrand(brand.id)}
                            />
                            <label
                              htmlFor={`brand-${brand.id}`}
                              className="text-sm cursor-pointer"
                            >
                              {brand.brandName} ({brand.brandCode})
                            </label>
                          </div>
                        ))
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      選択済み: {formData.brandIds.length}ブランド
                    </p>
                  </div>
                </>
              )}

              {/* Step 4: 住所・その他 */}
              {step === 4 && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="hireDate">採用日</Label>
                    <Input
                      id="hireDate"
                      type="date"
                      value={formData.hireDate}
                      onChange={(e) => updateFormData('hireDate', e.target.value)}
                      className="h-10"
                    />
                  </div>

                  {/* 郵便番号と検索ボタン */}
                  <div className="space-y-2">
                    <Label htmlFor="postalCode">郵便番号</Label>
                    <div className="flex gap-2">
                      <Input
                        id="postalCode"
                        placeholder="4640096"
                        value={formData.postalCode}
                        onChange={(e) => updateFormData('postalCode', e.target.value)}
                        className="h-10 flex-1"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-10 px-3"
                        onClick={searchAddress}
                        disabled={addressLoading}
                      >
                        <Search className="w-4 h-4 mr-1" />
                        {addressLoading ? '検索中' : '検索'}
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>都道府県</Label>
                    <Select
                      value={formData.prefecture}
                      onValueChange={(value) => updateFormData('prefecture', value)}
                    >
                      <SelectTrigger className="h-10">
                        <SelectValue placeholder="選択" />
                      </SelectTrigger>
                      <SelectContent>
                        {PREFECTURES.map(pref => (
                          <SelectItem key={pref} value={pref}>
                            {pref}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="city">市区町村</Label>
                    <Input
                      id="city"
                      placeholder="名古屋市千種区"
                      value={formData.city}
                      onChange={(e) => updateFormData('city', e.target.value)}
                      className="h-10"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="address">住所</Label>
                    <Input
                      id="address"
                      placeholder="1-2-3 〇〇ビル101"
                      value={formData.address}
                      onChange={(e) => updateFormData('address', e.target.value)}
                      className="h-10"
                    />
                  </div>

                  {/* 最寄駅 */}
                  <div className="space-y-2">
                    <Label htmlFor="nearestStation">最寄駅</Label>
                    <Input
                      id="nearestStation"
                      placeholder="名古屋駅"
                      value={formData.nearestStation}
                      onChange={(e) => updateFormData('nearestStation', e.target.value)}
                      className="h-10"
                    />
                  </div>

                  {/* 通勤方法 */}
                  <div className="space-y-2">
                    <Label>通勤方法</Label>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant={formData.commutingMethod === 'train' ? 'default' : 'outline'}
                        size="sm"
                        className={`flex-1 h-10 ${formData.commutingMethod === 'train' ? 'bg-blue-600' : ''}`}
                        onClick={() => updateFormData('commutingMethod', formData.commutingMethod === 'train' ? '' : 'train')}
                      >
                        <Train className="w-4 h-4 mr-1" />
                        電車
                      </Button>
                      <Button
                        type="button"
                        variant={formData.commutingMethod === 'car' ? 'default' : 'outline'}
                        size="sm"
                        className={`flex-1 h-10 ${formData.commutingMethod === 'car' ? 'bg-blue-600' : ''}`}
                        onClick={() => updateFormData('commutingMethod', formData.commutingMethod === 'car' ? '' : 'car')}
                      >
                        <Car className="w-4 h-4 mr-1" />
                        車
                      </Button>
                      <Button
                        type="button"
                        variant={formData.commutingMethod === 'both' ? 'default' : 'outline'}
                        size="sm"
                        className={`flex-1 h-10 ${formData.commutingMethod === 'both' ? 'bg-blue-600' : ''}`}
                        onClick={() => updateFormData('commutingMethod', formData.commutingMethod === 'both' ? '' : 'both')}
                      >
                        両方
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="nationality">国籍</Label>
                    <Input
                      id="nationality"
                      placeholder="日本"
                      value={formData.nationality}
                      onChange={(e) => updateFormData('nationality', e.target.value)}
                      className="h-10"
                    />
                  </div>
                </>
              )}

              {/* エラー表示 */}
              {error && (
                <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg whitespace-pre-wrap">
                  {error}
                </div>
              )}

              {/* ナビゲーションボタン */}
              <div className="flex justify-between pt-3 gap-2">
                {step > 1 ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={prevStep}
                    size="sm"
                    className="h-9"
                  >
                    <ChevronLeft className="w-4 h-4 mr-1" />
                    戻る
                  </Button>
                ) : (
                  <Link href="/login">
                    <Button type="button" variant="outline" size="sm" className="h-9">
                      <ChevronLeft className="w-4 h-4 mr-1" />
                      ログインへ
                    </Button>
                  </Link>
                )}

                {step < 4 ? (
                  <Button
                    type="button"
                    onClick={nextStep}
                    size="sm"
                    className="h-9 bg-blue-600 hover:bg-blue-700"
                  >
                    次へ
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                ) : (
                  <Button
                    type="button"
                    onClick={handleSubmit}
                    disabled={loading}
                    size="sm"
                    className="h-9 bg-green-600 hover:bg-green-700"
                  >
                    {loading ? '登録中...' : '登録する'}
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
