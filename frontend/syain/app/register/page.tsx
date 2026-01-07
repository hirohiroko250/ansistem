'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { GraduationCap, ChevronLeft, ChevronRight } from 'lucide-react';
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
  school_name: string;
  school_code: string;
}

interface Brand {
  id: string;
  brand_name: string;
  brand_code: string;
}

interface Tenant {
  id: string;
  tenant_code: string;
  tenant_name: string;
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
  });

  // マスタデータの取得
  useEffect(() => {
    const fetchMasterData = async () => {
      try {
        // テナント（会社）一覧を取得
        const tenantsRes = await api.get<Tenant[]>('/tenants/tenants/', { skipAuth: true });
        setTenants(Array.isArray(tenantsRes) ? tenantsRes : []);

        // 校舎一覧を取得（認証不要）
        const schoolsRes = await api.get<School[]>('/schools/', { skipAuth: true });
        setSchools(Array.isArray(schoolsRes) ? schoolsRes : []);

        // ブランド一覧を取得（認証不要）
        const brandsRes = await api.get<Brand[]>('/schools/brands/', { skipAuth: true });
        setBrands(Array.isArray(brandsRes) ? brandsRes : []);
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
      await api.post('/auth/register/employee/', {
        last_name: formData.lastName,
        first_name: formData.firstName,
        email: formData.email,
        phone: formData.phone,
        password: formData.password,
        password_confirm: formData.passwordConfirm,
        tenant_id: formData.tenantId,
        department: formData.department,
        position_id: formData.positionId || null,
        position_text: formData.positionText,
        school_ids: formData.schoolIds,
        brand_ids: formData.brandIds,
        hire_date: formData.hireDate || null,
        postal_code: formData.postalCode,
        prefecture: formData.prefecture,
        city: formData.city,
        address: formData.address,
        nationality: formData.nationality,
      }, { skipAuth: true });

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
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="flex flex-col items-center mb-6">
          <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mb-4 shadow-lg">
            <GraduationCap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">新規社員登録</h1>
          <p className="text-sm text-gray-600 mt-1">Employee Registration</p>
        </div>

        {/* ステップインジケーター */}
        <div className="flex justify-center mb-6">
          <div className="flex items-center space-x-2">
            {[1, 2, 3, 4].map(s => (
              <div key={s} className="flex items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
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
                  <div className={`w-8 h-0.5 ${s < step ? 'bg-green-500' : 'bg-gray-200'}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        <Card className="shadow-xl border-0">
          <CardHeader>
            <CardTitle className="text-xl">
              {step === 1 && '基本情報'}
              {step === 2 && '所属情報'}
              {step === 3 && '対応校舎・ブランド'}
              {step === 4 && '住所・その他'}
            </CardTitle>
            <CardDescription>
              {step === 1 && 'お名前とログイン情報を入力してください'}
              {step === 2 && '所属会社と部署を選択してください'}
              {step === 3 && '対応する校舎とブランドを選択してください'}
              {step === 4 && '住所と採用日を入力してください'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Step 1: 基本情報 */}
              {step === 1 && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="lastName">姓 <span className="text-red-500">*</span></Label>
                      <Input
                        id="lastName"
                        placeholder="山田"
                        value={formData.lastName}
                        onChange={(e) => updateFormData('lastName', e.target.value)}
                        className="h-12"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="firstName">名 <span className="text-red-500">*</span></Label>
                      <Input
                        id="firstName"
                        placeholder="太郎"
                        value={formData.firstName}
                        onChange={(e) => updateFormData('firstName', e.target.value)}
                        className="h-12"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">メールアドレス <span className="text-red-500">*</span></Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="example@email.com"
                      value={formData.email}
                      onChange={(e) => updateFormData('email', e.target.value)}
                      className="h-12"
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
                      className="h-12"
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
                      className="h-12"
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
                      className="h-12"
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
                      <SelectTrigger className="h-12">
                        <SelectValue placeholder="会社を選択" />
                      </SelectTrigger>
                      <SelectContent>
                        {tenants.map(tenant => (
                          <SelectItem key={tenant.id} value={tenant.id}>
                            {tenant.tenant_code} - {tenant.tenant_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>部署</Label>
                    <Select
                      value={formData.department}
                      onValueChange={(value) => updateFormData('department', value)}
                    >
                      <SelectTrigger className="h-12">
                        <SelectValue placeholder="部署を選択（任意）" />
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
                    <Label>役職</Label>
                    <Select
                      value={formData.positionId}
                      onValueChange={(value) => updateFormData('positionId', value)}
                    >
                      <SelectTrigger className="h-12">
                        <SelectValue placeholder="役職を選択（任意）" />
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
                      className="h-12"
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
                              {school.school_name} ({school.school_code})
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
                              {brand.brand_name} ({brand.brand_code})
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
                      className="h-12"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="postalCode">郵便番号</Label>
                      <Input
                        id="postalCode"
                        placeholder="1234567"
                        value={formData.postalCode}
                        onChange={(e) => updateFormData('postalCode', e.target.value)}
                        className="h-12"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>都道府県</Label>
                      <Select
                        value={formData.prefecture}
                        onValueChange={(value) => updateFormData('prefecture', value)}
                      >
                        <SelectTrigger className="h-12">
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
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="city">市区町村</Label>
                    <Input
                      id="city"
                      placeholder="渋谷区"
                      value={formData.city}
                      onChange={(e) => updateFormData('city', e.target.value)}
                      className="h-12"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="address">住所</Label>
                    <Input
                      id="address"
                      placeholder="1-2-3 〇〇ビル101"
                      value={formData.address}
                      onChange={(e) => updateFormData('address', e.target.value)}
                      className="h-12"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="nationality">国籍</Label>
                    <Input
                      id="nationality"
                      placeholder="日本"
                      value={formData.nationality}
                      onChange={(e) => updateFormData('nationality', e.target.value)}
                      className="h-12"
                    />
                  </div>
                </>
              )}

              {/* エラー表示 */}
              {error && (
                <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">
                  {error}
                </div>
              )}

              {/* ナビゲーションボタン */}
              <div className="flex justify-between pt-4">
                {step > 1 ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={prevStep}
                    className="h-12"
                  >
                    <ChevronLeft className="w-4 h-4 mr-1" />
                    戻る
                  </Button>
                ) : (
                  <Link href="/login">
                    <Button type="button" variant="outline" className="h-12">
                      <ChevronLeft className="w-4 h-4 mr-1" />
                      ログイン画面へ
                    </Button>
                  </Link>
                )}

                {step < 4 ? (
                  <Button
                    type="button"
                    onClick={nextStep}
                    className="h-12 bg-blue-600 hover:bg-blue-700"
                  >
                    次へ
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                ) : (
                  <Button
                    type="button"
                    onClick={handleSubmit}
                    disabled={loading}
                    className="h-12 bg-green-600 hover:bg-green-700"
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
