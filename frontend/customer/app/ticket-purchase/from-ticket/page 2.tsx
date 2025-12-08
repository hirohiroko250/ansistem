'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, Package, Sparkles, Calendar as CalendarIcon, Loader2, AlertCircle, Calculator, GraduationCap, Users, MessageCircle, PenTool, Ticket } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar } from '@/components/ui/calendar';
import { Checkbox } from '@/components/ui/checkbox';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { SchoolMap } from '@/components/school-map';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { format, addDays } from 'date-fns';
import { ja } from 'date-fns/locale';
import { getChildren } from '@/lib/api/students';
import { getPublicBrands, getPublicCourses, getPublicPacks } from '@/lib/api/courses';
import { getPublicSchools } from '@/lib/api/schools';
import { previewPricing, confirmPricing } from '@/lib/api/pricing';
import type { Child, PublicBrand, PublicCourse, PublicPack, PublicSchool } from '@/lib/api/types';
import type { ApiError, PricingPreviewResponse } from '@/lib/api/types';

// ブランドのアイコンマッピング
const brandIcons: { [key: string]: React.ElementType } = {
  soroban: Calculator,
  juku: GraduationCap,
  gakudo: Users,
  eikaiwa: MessageCircle,
  shodo: PenTool,
  event: Ticket,
};

// ブランドの色マッピング
const brandColors: { [key: string]: string } = {
  soroban: 'bg-blue-100 text-blue-600',
  juku: 'bg-green-100 text-green-600',
  gakudo: 'bg-purple-100 text-purple-600',
  eikaiwa: 'bg-orange-100 text-orange-600',
  shodo: 'bg-pink-100 text-pink-600',
  event: 'bg-red-100 text-red-600',
};

export default function FromTicketPurchasePage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [selectedChild, setSelectedChild] = useState<Child | null>(null);
  const [selectedBrand, setSelectedBrand] = useState<PublicBrand | null>(null);
  const [selectedSchoolId, setSelectedSchoolId] = useState<string | null>(null);
  const [courseType, setCourseType] = useState<'single' | 'pack' | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<PublicCourse | PublicPack | null>(null);
  const [startDate, setStartDate] = useState<Date>();
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  // API 関連の state
  const [children, setChildren] = useState<Child[]>([]);
  const [isLoadingChildren, setIsLoadingChildren] = useState(true);
  const [childrenError, setChildrenError] = useState<string | null>(null);

  // ブランド
  const [brands, setBrands] = useState<PublicBrand[]>([]);
  const [isLoadingBrands, setIsLoadingBrands] = useState(false);
  const [brandsError, setBrandsError] = useState<string | null>(null);

  // 校舎
  const [schools, setSchools] = useState<PublicSchool[]>([]);
  const [isLoadingSchools, setIsLoadingSchools] = useState(false);
  const [schoolsError, setSchoolsError] = useState<string | null>(null);

  // コース・パック
  const [courses, setCourses] = useState<PublicCourse[]>([]);
  const [packs, setPacks] = useState<PublicPack[]>([]);
  const [isLoadingCourses, setIsLoadingCourses] = useState(false);
  const [coursesError, setCoursesError] = useState<string | null>(null);

  const [pricingPreview, setPricingPreview] = useState<PricingPreviewResponse | null>(null);
  const [isLoadingPricing, setIsLoadingPricing] = useState(false);
  const [pricingError, setPricingError] = useState<string | null>(null);

  const [isConfirming, setIsConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  // 子ども一覧を取得
  useEffect(() => {
    const fetchChildren = async () => {
      setIsLoadingChildren(true);
      setChildrenError(null);
      try {
        const data = await getChildren();
        setChildren(data);
      } catch (err) {
        const apiError = err as ApiError;
        if (apiError.status === 401) {
          router.push('/login');
          return;
        }
        setChildrenError(apiError.message || 'お子様情報の取得に失敗しました');
      } finally {
        setIsLoadingChildren(false);
      }
    };
    fetchChildren();
  }, [router]);

  // ブランド一覧を取得
  useEffect(() => {
    const fetchBrands = async () => {
      setIsLoadingBrands(true);
      setBrandsError(null);
      try {
        const data = await getPublicBrands();
        setBrands(data);
      } catch (err) {
        const apiError = err as ApiError;
        setBrandsError(apiError.message || 'ブランド情報の取得に失敗しました');
      } finally {
        setIsLoadingBrands(false);
      }
    };
    fetchBrands();
  }, []);

  // ブランド選択時に校舎を取得
  useEffect(() => {
    if (!selectedBrand) return;

    const fetchSchools = async () => {
      setIsLoadingSchools(true);
      setSchoolsError(null);
      try {
        const data = await getPublicSchools();
        // ブランドでフィルタリング (校舎にブランド情報があれば)
        setSchools(data);
      } catch (err) {
        const apiError = err as ApiError;
        setSchoolsError(apiError.message || '校舎情報の取得に失敗しました');
      } finally {
        setIsLoadingSchools(false);
      }
    };
    fetchSchools();
  }, [selectedBrand]);

  // 校舎選択時にコース・パックを取得
  useEffect(() => {
    if (!selectedBrand || !selectedSchoolId) return;

    const fetchCoursesAndPacks = async () => {
      setIsLoadingCourses(true);
      setCoursesError(null);
      try {
        const [coursesData, packsData] = await Promise.all([
          getPublicCourses({ brandId: selectedBrand.id, schoolId: selectedSchoolId }),
          getPublicPacks({ brandId: selectedBrand.id, schoolId: selectedSchoolId }),
        ]);
        setCourses(coursesData);
        setPacks(packsData);
      } catch (err) {
        const apiError = err as ApiError;
        setCoursesError(apiError.message || 'コース情報の取得に失敗しました');
      } finally {
        setIsLoadingCourses(false);
      }
    };
    fetchCoursesAndPacks();
  }, [selectedBrand, selectedSchoolId]);

  // コース選択時に料金プレビューを取得
  const handleCourseSelect = async (course: any) => {
    setSelectedCourse(course);
    setPricingError(null);
    setIsLoadingPricing(true);

    try {
      const preview = await previewPricing({
        studentId: selectedChild?.id || '',
        productIds: [course.id],
        courseId: course.courseId,
      });
      setPricingPreview(preview);
      setStep(6);
    } catch (err) {
      const apiError = err as ApiError;
      setPricingError(apiError.message || '料金計算に失敗しました');
      // エラーでも次のステップへ進む（ローカル価格を使用）
      setPricingPreview(null);
      setStep(6);
    } finally {
      setIsLoadingPricing(false);
    }
  };

  // 購入確定
  const handleConfirmPurchase = async () => {
    if (!selectedChild || !selectedCourse) return;

    setIsConfirming(true);
    setConfirmError(null);

    try {
      const result = await confirmPricing({
        previewId: pricingPreview?.items?.[0]?.productId || selectedCourse.id,
        paymentMethod: 'credit_card',
      });

      if (result.status === 'completed' || result.status === 'pending') {
        // 購入情報を sessionStorage に保存
        sessionStorage.setItem('purchaseResult', JSON.stringify({
          orderId: result.orderId,
          childName: selectedChild.fullName,
          courseName: selectedCourse.name,
          amount: pricingPreview?.grandTotal || selectedCourse.price,
          startDate: startDate ? format(startDate, 'yyyy-MM-dd') : null,
        }));
        router.push('/ticket-purchase/complete');
      } else {
        setConfirmError(result.message || '購入処理に失敗しました');
      }
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.status === 401) {
        router.push('/login');
        return;
      }
      setConfirmError(apiError.message || '購入処理に失敗しました');
    } finally {
      setIsConfirming(false);
    }
  };

  const handleChildSelect = (child: Child) => {
    setSelectedChild(child);
    setStep(2);
  };

  const handleBrandSelect = (brandId: string) => {
    setSelectedBrand(brandId);
    setStep(3);
  };

  const handleSchoolSelect = (schoolId: number) => {
    setSelectedSchoolId(schoolId);
  };

  const handleCourseTypeSelect = (type: 'single' | 'pack') => {
    setCourseType(type);
    setStep(5);
  };

  const handleBackToStep = (targetStep: number) => {
    setStep(targetStep);
  };

  const filteredCompanies = companies.filter(
    (company) => company.brand === selectedBrand
  );

  const mapSchools = filteredCompanies.flatMap((company) =>
    company.schools
      .filter((school) => school.position)
      .map((school) => ({
        id: school.id,
        name: school.name,
        address: school.address,
        company: company.name,
        companyColor: company.color,
        position: school.position!,
      }))
  );

  const selectedSchool = mapSchools.find((s) => s.id === selectedSchoolId);
  const selectedCompany = filteredCompanies.find((c) =>
    c.schools.some((s) => s.id === selectedSchoolId)
  );

  const availableCourses = selectedCompany?.courses.filter((course) => {
    if (courseType === 'single') {
      return !course.isMonthly && course.type !== 'fee';
    } else if (courseType === 'pack') {
      return course.isMonthly || course.type === 'fee';
    }
    return true;
  }) || [];

  // 料金計算（API レスポンスがあればそれを使用、なければローカル価格）
  const totalAmount = pricingPreview?.grandTotal ?? (selectedCourse?.price || 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/ticket-purchase" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">チケット購入</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        {step > 1 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleBackToStep(step - 1)}
            className="mb-4 -ml-2"
            disabled={isLoadingPricing || isConfirming}
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            戻る
          </Button>
        )}

        <div className="mb-6">
          <div className="flex items-center justify-center space-x-2">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
              <div
                key={s}
                className={`h-2 flex-1 rounded-full transition-colors ${
                  s <= step ? 'bg-blue-500' : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
          <p className="text-center text-sm text-gray-600 mt-2">Step {step} / 8</p>
        </div>

        {step === 1 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">お子様を選択</h2>

            {isLoadingChildren ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-3" />
                <p className="text-sm text-gray-600">お子様情報を読み込み中...</p>
              </div>
            ) : childrenError ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="flex items-center gap-2 p-4 rounded-lg bg-red-50 border border-red-200 mb-4">
                  <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                  <p className="text-sm text-red-800">{childrenError}</p>
                </div>
                <Button
                  onClick={() => window.location.reload()}
                  variant="outline"
                >
                  再読み込み
                </Button>
              </div>
            ) : children.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <p className="text-gray-600 mb-4">登録されているお子様がいません</p>
                <Link href="/children/add">
                  <Button>お子様を登録する</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {children.map((child) => (
                  <Card
                    key={child.id}
                    className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                    onClick={() => handleChildSelect(child)}
                  >
                    <CardContent className="p-4 flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800">{child.fullName}</h3>
                        <p className="text-sm text-gray-600">{child.grade}</p>
                      </div>
                      <ChevronLeft className="h-5 w-5 text-gray-400 rotate-180" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName}</p>
                </CardContent>
              </Card>
            </div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">ブランドを選択</h2>
            <div className="space-y-3">
              {brands.map((brand) => {
                const Icon = brand.icon;
                return (
                  <Card
                    key={brand.id}
                    className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                    onClick={() => handleBrandSelect(brand.id)}
                  >
                    <CardContent className="p-4 flex items-center">
                      <div className={`w-14 h-14 rounded-full ${brand.color} flex items-center justify-center mr-4`}>
                        <Icon className="h-7 w-7" />
                      </div>
                      <span className="text-lg font-semibold text-gray-800">{brand.name}</span>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName} → {brands.find(b => b.id === selectedBrand)?.name}</p>
                </CardContent>
              </Card>
            </div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">校舎を選択</h2>
            <p className="text-sm text-gray-600 mb-4">
              マップ上の校舎マーカーをタップして選択してください。運営会社ごとに色分けされています。
            </p>

            <div className="mb-4">
              <SchoolMap
                schools={mapSchools}
                selectedSchool={selectedSchoolId}
                onSchoolSelect={handleSchoolSelect}
              />
            </div>

            {selectedSchool && (
              <Card className="rounded-xl shadow-md mb-4 border-2 border-blue-500">
                <CardContent className="p-4">
                  <p className="text-xs text-gray-600 mb-1">選択中の校舎</p>
                  <h3 className="font-bold text-gray-800 mb-1">{selectedSchool.name}</h3>
                  <p className="text-sm text-gray-600 mb-2">{selectedSchool.address}</p>
                  <Badge className="text-xs" style={{ backgroundColor: selectedSchool.companyColor }}>
                    {selectedSchool.company}
                  </Badge>
                </CardContent>
              </Card>
            )}

            {selectedSchoolId && (
              <Button
                onClick={() => setStep(4)}
                className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg"
              >
                次へ
              </Button>
            )}
          </div>
        )}

        {step === 4 && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName}</p>
                  <p className="text-sm text-gray-700 mt-1">{selectedSchool?.name}</p>
                </CardContent>
              </Card>
            </div>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">コースタイプを選択</h2>
            <div className="space-y-4">
              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-blue-500"
                onClick={() => handleCourseTypeSelect('single')}
              >
                <CardContent className="p-6">
                  <div className="flex items-center gap-4 mb-3">
                    <div className="w-16 h-16 rounded-full bg-orange-100 flex items-center justify-center">
                      <Package className="h-8 w-8 text-orange-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-bold text-lg text-gray-800">単品コース</h3>
                      <p className="text-sm text-gray-600">回数券・都度利用</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    必要な時に必要な分だけ購入できる、柔軟な利用プランです。
                  </p>
                </CardContent>
              </Card>

              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-blue-500"
                onClick={() => handleCourseTypeSelect('pack')}
              >
                <CardContent className="p-6">
                  <div className="flex items-center gap-4 mb-3">
                    <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
                      <Sparkles className="h-8 w-8 text-green-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-bold text-lg text-gray-800">お得パックコース</h3>
                      <p className="text-sm text-gray-600">月額制・定期コース</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    定期的に通う方にお得な月額制プランです。入会金もこちらから。
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {step === 5 && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName}</p>
                  <p className="text-sm text-gray-700 mt-1">{selectedSchool?.name}</p>
                  <Badge className="mt-1 text-xs">
                    {courseType === 'single' ? '単品コース' : 'お得パックコース'}
                  </Badge>
                </CardContent>
              </Card>
            </div>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">コースを選択</h2>

            {pricingError && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-yellow-50 border border-yellow-200 mb-4">
                <AlertCircle className="h-5 w-5 text-yellow-600 shrink-0" />
                <p className="text-sm text-yellow-800">{pricingError}</p>
              </div>
            )}

            {isLoadingPricing ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-3" />
                <p className="text-sm text-gray-600">料金を計算中...</p>
              </div>
            ) : (
              <div className="space-y-3">
                {availableCourses.map((course: any) => (
                  <Card
                    key={course.id}
                    className={`rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer ${
                      course.popular ? 'border-2 border-blue-500' : ''
                    }`}
                    onClick={() => handleCourseSelect(course)}
                  >
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-gray-800">{course.name}</h3>
                          {course.popular && <Badge className="bg-blue-500 text-white">人気</Badge>}
                          {course.type === 'fee' && <Badge className="bg-gray-500 text-white">初回</Badge>}
                        </div>
                        <span className="text-xl font-bold text-blue-600">
                          ¥{course.price.toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{course.description}</p>
                      {course.tickets > 0 && (
                        <p className="text-sm text-gray-500">{course.tickets}チケット</p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 6 && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName}</p>
                  <p className="text-sm text-gray-700 mt-1">{selectedSchool?.name}</p>
                  <p className="text-sm text-gray-700 mt-1">{selectedCourse?.name}</p>
                </CardContent>
              </Card>
            </div>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">契約開始日を選択</h2>
            <p className="text-sm text-gray-600 mb-4">
              {selectedCourse?.isMonthly
                ? 'レッスンを開始する日付を選択してください。月額コースは翌月1日から開始されます。'
                : 'チケットを利用開始する日付を選択してください。'}
            </p>

            <Card className="rounded-xl shadow-md mb-4">
              <CardContent className="p-4">
                <Calendar
                  mode="single"
                  selected={startDate}
                  onSelect={setStartDate}
                  disabled={(date) => date < new Date()}
                  locale={ja}
                  className="rounded-md"
                />
              </CardContent>
            </Card>

            {startDate && (
              <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm text-green-800">
                  <CalendarIcon className="inline h-4 w-4 mr-1" />
                  選択した開始日: {format(startDate, 'yyyy年MM月dd日（E）', { locale: ja })}
                </p>
                {selectedCourse?.isMonthly && (
                  <p className="text-xs text-green-700 mt-2">
                    ※月額コースは{format(addDays(startDate, 30), 'yyyy年MM月1日', { locale: ja })}から本格的に開始されます
                  </p>
                )}
              </div>
            )}

            {startDate && (
              <Button
                onClick={() => setStep(7)}
                className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg"
              >
                次へ
              </Button>
            )}
          </div>
        )}

        {step === 7 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">利用規約の確認</h2>

            <Card className="rounded-xl shadow-md mb-4">
              <CardContent className="p-4">
                <div className="h-96 overflow-y-auto bg-gray-50 rounded-lg p-4 text-sm text-gray-700 space-y-3">
                  <h3 className="font-semibold text-base text-gray-800">MyLesson 利用規約</h3>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">第1条（適用）</h4>
                    <p>本規約は、当社が提供するMyLessonサービス（以下「本サービス」といいます）の利用条件を定めるものです。利用者は本規約に同意の上、本サービスを利用するものとします。</p>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">第2条（利用登録）</h4>
                    <p>本サービスの利用を希望する方は、本規約に同意の上、当社の定める方法によって利用登録を申請し、当社がこれを承認することによって、利用登録が完了するものとします。</p>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">第3条（料金および支払方法）</h4>
                    <p>利用者は、本サービスの利用料金を、当社が指定する方法により支払うものとします。</p>
                    <ul className="list-disc ml-5 mt-2">
                      <li>月額コースは毎月1日に翌月分の料金が発生します</li>
                      <li>単品チケットは購入時に料金が発生します</li>
                      <li>返金は原則として行いません</li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">第4条（キャンセルポリシー）</h4>
                    <p>予約のキャンセルは、以下の通りとします：</p>
                    <ul className="list-disc ml-5 mt-2">
                      <li>レッスン開始24時間前まで：無料キャンセル</li>
                      <li>レッスン開始24時間以内：チケット消化</li>
                      <li>無断欠席：チケット消化</li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">第5条（禁止事項）</h4>
                    <p>利用者は、本サービスの利用にあたり、以下の行為をしてはなりません：</p>
                    <ul className="list-disc ml-5 mt-2">
                      <li>法令または公序良俗に違反する行為</li>
                      <li>犯罪行為に関連する行為</li>
                      <li>他の利用者、第三者、または当社の権利を侵害する行為</li>
                      <li>本サービスの運営を妨害する行為</li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">第6条（個人情報の取扱い）</h4>
                    <p>当社は、本サービスの提供に必要な範囲で、利用者の個人情報を取得します。取得した個人情報は、プライバシーポリシーに従って適切に管理します。</p>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">第7条（免責事項）</h4>
                    <p>当社は、本サービスに関して、利用者と他の利用者または第三者との間で生じた取引、連絡または紛争等について一切責任を負いません。</p>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">第8条（サービス内容の変更等）</h4>
                    <p>当社は、利用者への事前の通知なく、本サービスの内容を変更、追加または廃止することがあり、利用者はこれを承諾するものとします。</p>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">第9条（規約の変更）</h4>
                    <p>当社は、利用者の承諾を得ることなく本規約を変更することができるものとします。変更後の本規約は、当社が別途定める場合を除いて、本サービス上に表示した時点より効力を生じるものとします。</p>
                  </div>

                  <div className="pt-3 border-t">
                    <p className="text-xs text-gray-600">最終更新日：2024年12月4日</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="flex items-start gap-3 mb-4 p-4 bg-gray-50 rounded-lg">
              <Checkbox
                checked={agreedToTerms}
                onCheckedChange={(checked) => setAgreedToTerms(!!checked)}
                id="terms"
              />
              <label htmlFor="terms" className="text-sm text-gray-700 cursor-pointer">
                利用規約を確認し、同意します
              </label>
            </div>

            <Button
              onClick={() => setStep(8)}
              disabled={!agreedToTerms}
              className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              同意して次へ
            </Button>
          </div>
        )}

        {step === 8 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">購入内容の確認</h2>

            {confirmError && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 mb-4">
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                <p className="text-sm text-red-800">{confirmError}</p>
              </div>
            )}

            <Card className="rounded-xl shadow-md mb-6">
              <CardContent className="p-6 space-y-4">
                <div>
                  <p className="text-sm text-gray-600 mb-1">お子様</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName}</p>
                  <p className="text-sm text-gray-600">{selectedChild?.grade}</p>
                </div>
                <div className="border-t pt-4">
                  <p className="text-sm text-gray-600 mb-1">ブランド</p>
                  <p className="font-semibold text-gray-800">
                    {brands.find((b) => b.id === selectedBrand)?.name}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">運営会社</p>
                  <p className="font-semibold text-gray-800">{selectedCompany?.name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">校舎</p>
                  <p className="font-semibold text-gray-800">{selectedSchool?.name}</p>
                  <p className="text-sm text-gray-600">{selectedSchool?.address}</p>
                </div>
                <div className="border-t pt-4">
                  <p className="text-sm text-gray-600 mb-1">契約開始日</p>
                  <p className="font-semibold text-gray-800">
                    {startDate && format(startDate, 'yyyy年MM月dd日（E）', { locale: ja })}
                  </p>
                </div>
                <div className="border-t pt-4">
                  <p className="text-sm text-gray-600 mb-1">コース</p>
                  <p className="font-semibold text-gray-800">{selectedCourse?.name}</p>
                  <p className="text-sm text-gray-600">{selectedCourse?.description}</p>
                </div>

                {pricingPreview && pricingPreview.discounts && pricingPreview.discounts.length > 0 && (
                  <div className="border-t pt-4">
                    <p className="text-sm text-gray-600 mb-2">適用される割引</p>
                    {pricingPreview.discounts.map((discount, index) => (
                      <div key={index} className="flex justify-between text-sm">
                        <span className="text-green-700">{discount.discountName}</span>
                        <span className="text-green-700">-¥{discount.appliedAmount.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="border-t pt-4">
                  <div className="flex justify-between items-center">
                    <span className="text-lg font-semibold text-gray-800">合計金額</span>
                    <span className="text-2xl font-bold text-blue-600">
                      ¥{totalAmount.toLocaleString()}
                    </span>
                  </div>
                  {pricingPreview && (
                    <p className="text-xs text-gray-500 mt-1 text-right">
                      （税込 ¥{(pricingPreview.taxTotal || 0).toLocaleString()}）
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            <Button
              onClick={handleConfirmPurchase}
              disabled={isConfirming}
              className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg disabled:opacity-70"
            >
              {isConfirming ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  処理中...
                </span>
              ) : (
                '購入を確定する'
              )}
            </Button>
          </div>
        )}
      </main>

      <BottomTabBar />
    </div>
  );
}
