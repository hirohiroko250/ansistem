'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, User, Star, Clock, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar } from '@/components/ui/calendar';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { MapSchoolSelector } from '@/components/map-school-selector';
import { getBrandSchools, type BrandSchool } from '@/lib/api/schools';
import Link from 'next/link';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import { getChildren } from '@/lib/api/students';
import type { Child as ApiChild } from '@/lib/api/types';
import { getAccessToken } from '@/lib/api/client';
import { getMe } from '@/lib/api/auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

type Child = {
  id: string;
  studentId: string;
  name: string;
  age: number;
  birthDate?: string;  // 学年フィルター用
};

// 生年月日から年齢を計算
function calculateAge(birthDate: string | undefined): number {
  if (!birthDate) return 0;
  const today = new Date();
  const birth = new Date(birthDate);
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age;
}

// APIのChild型をページで使うChild型に変換
function convertApiChild(apiChild: ApiChild): Child {
  return {
    id: apiChild.id,
    studentId: apiChild.studentNumber || '',
    name: apiChild.fullName || `${apiChild.lastName}${apiChild.firstName}`,
    age: calculateAge(apiChild.birthDate),
    birthDate: apiChild.birthDate,  // 学年フィルター用に生年月日を保持
  };
}

type BrandCategory = {
  id: string;
  categoryCode: string;
  categoryName: string;
  sortOrder: number;
};

type Brand = {
  id: string;
  name: string;
  code: string;
  color: string;
  category?: BrandCategory;
};

type ScheduleTime = {
  id: string;
  time: string;
  timeSlotId: string;
  timeSlotName: string;
  capacity: number;
  trialCapacity: number;
  brandId: string;
  brandName: string;
};

type AvailabilitySlot = {
  scheduleId: string;
  timeSlotId: string;
  time: string;
  trialCapacity: number;
  bookedCount: number;
  availableCount: number;
  isAvailable: boolean;
};

type DaySchedule = {
  day: string;
  times: ScheduleTime[];
};

type DailyAvailability = {
  date: string;
  dayOfWeek: number;
  isOpen: boolean;
  totalCapacity: number;
  bookedCount: number;
  availableCount: number;
  isAvailable: boolean;
  reason?: string;
};



// ブランドカラー設定
const brandColors: Record<string, string> = {
  'AEC': 'bg-blue-500',
  'SDR': 'bg-green-500',
  'PRO': 'bg-purple-500',
  'SHO': 'bg-orange-500',
  'KID': 'bg-pink-500',
};

const getDayOfWeek = (date: Date): string => {
  const days = ['日曜日', '月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日'];
  return days[date.getDay()];
};

export default function TrialPage() {
  const [step, setStep] = useState<'child' | 'category' | 'school' | 'date' | 'time' | 'confirm'>('child');
  const [selectedChild, setSelectedChild] = useState<Child | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<BrandCategory | null>(null);
  const [selectedBrand, setSelectedBrand] = useState<Brand | null>(null);  // 内部で自動選択
  const [selectedDate, setSelectedDate] = useState<Date>();
  const [selectedTime, setSelectedTime] = useState<ScheduleTime | null>(null);
  const [selectedAvailability, setSelectedAvailability] = useState<AvailabilitySlot | null>(null);


  // API データ
  const [children, setChildren] = useState<Child[]>([]);
  const [childrenLoading, setChildrenLoading] = useState(true);
  const [childrenError, setChildrenError] = useState<string | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [schools, setSchools] = useState<BrandSchool[]>([]);
  const [selectedSchoolId, setSelectedSchoolId] = useState<string | null>(null);
  const [isLoadingSchools, setIsLoadingSchools] = useState(false);
  const [schedules, setSchedules] = useState<DaySchedule[]>([]);
  const [loading, setLoading] = useState(false);

  // ユーザーの近隣校舎ID
  const [nearestSchoolId, setNearestSchoolId] = useState<string | null>(null);

  // 空き状況
  const [availability, setAvailability] = useState<AvailabilitySlot[]>([]);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [isClosed, setIsClosed] = useState(false);

  // 月間空き状況
  const [monthlyAvailability, setMonthlyAvailability] = useState<Record<string, DailyAvailability>>({});
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date());

  // 予約状態
  const [bookingLoading, setBookingLoading] = useState(false);
  const [bookingError, setBookingError] = useState<string | null>(null);
  const [bookingSuccess, setBookingSuccess] = useState(false);


  // ユーザープロファイル取得（近隣校舎ID）
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const profile = await getMe();
        if (profile.nearestSchoolId) {
          setNearestSchoolId(profile.nearestSchoolId);
        }
      } catch (error) {
        console.error('Failed to fetch profile:', error);
      }
    };
    fetchProfile();
  }, []);

  // 子供一覧取得
  useEffect(() => {
    const fetchChildren = async () => {
      try {
        setChildrenLoading(true);
        setChildrenError(null);
        const apiChildren = await getChildren();
        setChildren(apiChildren.map(convertApiChild));
      } catch (error) {
        console.error('Failed to fetch children:', error);
        setChildrenError('お子様情報の取得に失敗しました');
      } finally {
        setChildrenLoading(false);
      }
    };
    fetchChildren();
  }, []);

  // ブランド一覧取得
  useEffect(() => {
    const fetchBrands = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/contracts/public/brands/`);
        const data = await res.json();
        // APIレスポンスは配列、またはdata.dataに配列がある
        const brandsArray = Array.isArray(data) ? data : (data.data || []);
        setBrands(brandsArray.map((b: any) => ({
          id: b.id,
          name: b.brandName || b.name,
          code: b.brandCode || b.code,
          color: brandColors[b.brandCode || b.code] || 'bg-gray-500',
          category: b.category ? {
            id: b.category.id,
            categoryCode: b.category.categoryCode,
            categoryName: b.category.categoryName,
            sortOrder: b.category.sortOrder,
          } : undefined,
        })));
      } catch (error) {
        console.error('Failed to fetch brands:', error);
      }
    };
    fetchBrands();
  }, []);

  // 校舎一覧取得（カテゴリ選択後、自動選択されたブランドを使用）
  useEffect(() => {
    if (!selectedBrand) return;

    const fetchSchools = async () => {
      setIsLoadingSchools(true);
      setSelectedSchoolId(null);
      try {
        const data = await getBrandSchools(selectedBrand.id);
        setSchools(data);
      } catch (error) {
        console.error('Failed to fetch schools:', error);
        setSchools([]);
      } finally {
        setIsLoadingSchools(false);
      }
    };
    fetchSchools();
  }, [selectedBrand]);

  // スケジュール取得（校舎選択時）- 学年フィルター対応
  useEffect(() => {
    if (!selectedSchoolId || !selectedBrand) return;

    const fetchSchedules = async () => {
      setLoading(true);
      try {
        // birth_dateパラメータを追加して学年フィルターを適用
        const birthDateParam = selectedChild?.birthDate ? `&birth_date=${selectedChild.birthDate}` : '';
        const res = await fetch(
          `${API_BASE_URL}/schools/public/trial-schedule/?school_id=${selectedSchoolId}&brand_id=${selectedBrand.id}${birthDateParam}`
        );
        const data = await res.json();
        if (data.schedule) {
          setSchedules(data.schedule);
        }
      } catch (error) {
        console.error('Failed to fetch schedules:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchSchedules();
  }, [selectedSchoolId, selectedBrand, selectedChild?.birthDate]);

  // 月間空き状況取得
  useEffect(() => {
    if (!selectedSchoolId || !selectedBrand || step !== 'date') return;

    const fetchMonthlyAvailability = async () => {
      try {
        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth() + 1;
        const res = await fetch(
          `${API_BASE_URL}/schools/public/trial-monthly-availability/?school_id=${selectedSchoolId}&brand_id=${selectedBrand.id}&year=${year}&month=${month}`
        );
        const data = await res.json();
        if (data.days) {
          const availabilityMap: Record<string, DailyAvailability> = {};
          data.days.forEach((day: DailyAvailability) => {
            availabilityMap[day.date] = day;
          });
          setMonthlyAvailability(availabilityMap);
        }
      } catch (error) {
        console.error('Failed to fetch monthly availability:', error);
      }
    };
    fetchMonthlyAvailability();
  }, [selectedSchoolId, selectedBrand, currentMonth, step]);

  // 選択中の校舎を取得
  const selectedSchool = schools.find(s => s.id === selectedSchoolId);

  const isDateAvailable = (date: Date): boolean => {
    if (schedules.length === 0) return false;
    const dayOfWeek = getDayOfWeek(date);
    return schedules.some((s) => s.day === dayOfWeek);
  };

  const getAvailableTimesForDate = (date: Date | undefined): ScheduleTime[] => {
    if (!date || schedules.length === 0) return [];
    const dayOfWeek = getDayOfWeek(date);
    const scheduleForDay = schedules.find((s) => s.day === dayOfWeek);
    if (!scheduleForDay) return [];
    // 時間順にソート（例: "10:00-11:00" → 10:00でソート）
    return [...scheduleForDay.times].sort((a, b) => {
      const timeA = a.time.split('-')[0].trim();
      const timeB = b.time.split('-')[0].trim();
      return timeA.localeCompare(timeB);
    });
  };

  const handleChildSelect = (child: Child) => {
    setSelectedChild(child);
    setStep('category');
  };

  const handleCategorySelect = (category: BrandCategory) => {
    setSelectedCategory(category);
    // カテゴリ内の最初のブランドを自動選択して、直接校舎選択へ
    const categoryBrands = brands.filter(b => b.category?.id === category.id);
    if (categoryBrands.length > 0) {
      setSelectedBrand(categoryBrands[0]);
    }
    setStep('school');
  };

  const handleSchoolSelect = (schoolId: string) => {
    setSelectedSchoolId(schoolId);
  };

  const handleDateSelect = async (date: Date | undefined) => {
    setSelectedDate(date);
    setSelectedAvailability(null);
    setIsClosed(false);

    if (date && selectedSchoolId && selectedBrand) {
      // 空き状況を取得
      setAvailabilityLoading(true);
      try {
        const dateStr = format(date, 'yyyy-MM-dd');
        const res = await fetch(
          `${API_BASE_URL}/schools/public/trial-availability/?school_id=${selectedSchoolId}&brand_id=${selectedBrand.id}&date=${dateStr}`
        );
        const data = await res.json();

        if (data.isClosed) {
          setIsClosed(true);
          setAvailability([]);
        } else if (data.slots) {
          setAvailability(data.slots);
          setIsClosed(false);
        }
      } catch (error) {
        console.error('Failed to fetch availability:', error);
      } finally {
        setAvailabilityLoading(false);
      }
      setStep('time');
    }
  };

  const handleTimeSelect = (time: ScheduleTime, avail: AvailabilitySlot | null) => {
    setSelectedTime(time);
    setSelectedAvailability(avail);
  };

  const handleConfirm = async () => {
    if (!selectedChild || !selectedSchoolId || !selectedBrand || !selectedDate || !selectedAvailability) {
      return;
    }

    setBookingLoading(true);
    setBookingError(null);

    try {
      const token = getAccessToken();
      const res = await fetch(`${API_BASE_URL}/schools/public/trial-booking/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          student_id: selectedChild.id,
          school_id: selectedSchoolId,
          brand_id: selectedBrand.id,
          schedule_id: selectedAvailability.scheduleId,
          trial_date: format(selectedDate, 'yyyy-MM-dd'),
          notes: '',
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setBookingError(data.error || '予約に失敗しました');
        return;
      }

      setBookingSuccess(true);
      setStep('confirm');
    } catch (error) {
      console.error('Booking failed:', error);
      setBookingError('予約に失敗しました。再度お試しください。');
    } finally {
      setBookingLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">体験授業</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        {step === 'child' && (
          <section>
            <Link href="/">
              <Button variant="ghost" className="mb-4">
                <ChevronLeft className="h-4 w-4 mr-2" />
                戻る
              </Button>
            </Link>

            <Card className="rounded-xl shadow-md bg-yellow-50 border-yellow-200 mb-6">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Star className="h-6 w-6 text-yellow-600" />
                  <div>
                    <h3 className="font-semibold text-gray-800 mb-1">無料体験授業</h3>
                    <p className="text-sm text-gray-600">初めての方向けの体験授業です</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">お子様を選択してください</h2>
            <div className="space-y-3">
              {childrenLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                </div>
              ) : childrenError ? (
                <div className="text-center py-8">
                  <p className="text-red-600 mb-4">{childrenError}</p>
                  <Button onClick={() => window.location.reload()} variant="outline">
                    再読み込み
                  </Button>
                </div>
              ) : children.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-600 mb-4">お子様が登録されていません</p>
                  <Link href="/settings/children/new">
                    <Button>お子様を登録する</Button>
                  </Link>
                </div>
              ) : (
                [...children].sort((a, b) => b.age - a.age).map((child) => (
                  <Card
                    key={child.id}
                    className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                    onClick={() => handleChildSelect(child)}
                  >
                    <CardContent className="p-4 flex items-center gap-4">
                      <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
                        <User className="h-6 w-6 text-yellow-600" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-800">{child.studentId ? `${child.studentId} ` : ''}{child.name}</h3>
                        <p className="text-sm text-gray-600">{child.age > 0 ? `${child.age}歳` : ''}</p>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </section>
        )}

        {step === 'category' && (
          <section>
            <Button variant="ghost" className="mb-4" onClick={() => setStep('child')}>
              <ChevronLeft className="h-4 w-4 mr-2" />
              戻る
            </Button>

            <Card className="rounded-xl shadow-md bg-yellow-50 border-yellow-200 mb-6">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <User className="h-5 w-5 text-yellow-600" />
                  <div>
                    <p className="text-sm text-gray-600">選択中のお子様</p>
                    <p className="font-semibold text-gray-800">{selectedChild?.studentId} {selectedChild?.name}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">カテゴリを選択</h2>
            <div className="space-y-3">
              {/* カテゴリのみ表示 */}
              {(() => {
                // カテゴリを抽出（重複を除去）
                const categories = brands.reduce((acc, brand) => {
                  const category = brand.category;
                  if (category && !acc.find(c => c.id === category.id)) {
                    acc.push(category);
                  }
                  return acc;
                }, [] as BrandCategory[]);

                // sortOrderでソート
                const sortedCategories = categories.sort((a, b) => a.sortOrder - b.sortOrder);

                return sortedCategories.map((category) => (
                  <Card
                    key={category.id}
                    className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                    onClick={() => handleCategorySelect(category)}
                  >
                    <CardContent className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-full bg-yellow-100 flex items-center justify-center">
                          <Star className="h-6 w-6 text-yellow-600" />
                        </div>
                        <h3 className="font-semibold text-gray-800">{category.categoryName}</h3>
                      </div>
                      <ChevronLeft className="h-5 w-5 text-gray-400 rotate-180" />
                    </CardContent>
                  </Card>
                ));
              })()}
            </div>
          </section>
        )}

        {step === 'school' && (
          <section>
            <Button variant="ghost" className="mb-4" onClick={() => setStep('category')}>
              <ChevronLeft className="h-4 w-4 mr-2" />
              戻る
            </Button>

            <Card className="rounded-xl shadow-md bg-yellow-50 border-yellow-200 mb-6">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <User className="h-5 w-5 text-yellow-600" />
                  <div>
                    <p className="text-sm text-gray-600">選択中のお子様</p>
                    <p className="font-semibold text-gray-800">{selectedChild?.name}</p>
                  </div>
                </div>
                <div className="mt-2 pt-2 border-t border-yellow-300">
                  <p className="text-sm text-gray-600">カテゴリ</p>
                  <p className="font-semibold text-gray-800">{selectedCategory?.categoryName}</p>
                </div>
              </CardContent>
            </Card>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">校舎を選択</h2>

            <MapSchoolSelector
              schools={schools}
              selectedSchoolId={selectedSchoolId}
              onSelectSchool={handleSchoolSelect}
              isLoading={isLoadingSchools}
              initialSchoolId={nearestSchoolId}
            />

            {selectedSchoolId && (
              <Button
                onClick={() => setStep('date')}
                className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg mt-6"
              >
                次へ
              </Button>
            )}
          </section>
        )}

        {step === 'date' && (
          <section>
            <Button variant="ghost" className="mb-4" onClick={() => setStep('school')}>
              <ChevronLeft className="h-4 w-4 mr-2" />
              戻る
            </Button>

            <Card className="rounded-xl shadow-md bg-yellow-50 border-yellow-200 mb-6">
              <CardContent className="p-4">
                <div className="space-y-2">
                  <div>
                    <p className="text-sm text-gray-600">お子様</p>
                    <p className="font-semibold text-gray-800">{selectedChild?.name}</p>
                  </div>
                  <div className="pt-2 border-t border-yellow-300">
                    <p className="text-sm text-gray-600">校舎</p>
                    <p className="font-semibold text-gray-800">{selectedSchool?.name}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">体験日を選択</h2>

            {schedules.length > 0 && (
              <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800 font-medium mb-2">開講曜日</p>
                <div className="flex flex-wrap gap-2">
                  {schedules.map((s) => (
                    <Badge key={s.day} className="bg-blue-500">{s.day}</Badge>
                  ))}
                </div>
              </div>
            )}

            <Card className="rounded-xl shadow-md">
              <CardContent className="p-4">
                <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={handleDateSelect}
                  onMonthChange={(month) => setCurrentMonth(month)}
                  disabled={(date) => {
                    const today = new Date();
                    today.setHours(0, 0, 0, 0);
                    return date < today || !isDateAvailable(date);
                  }}
                  locale={ja}
                  className="rounded-md"
                  modifiers={{
                    hasAvailability: (date) => {
                      const dateStr = format(date, 'yyyy-MM-dd');
                      const dayInfo = monthlyAvailability[dateStr];
                      return dayInfo?.isAvailable === true;
                    },
                    full: (date) => {
                      const dateStr = format(date, 'yyyy-MM-dd');
                      const dayInfo = monthlyAvailability[dateStr];
                      return dayInfo?.isOpen === true && dayInfo?.availableCount === 0;
                    },
                    hasBookings: (date) => {
                      const dateStr = format(date, 'yyyy-MM-dd');
                      const dayInfo = monthlyAvailability[dateStr];
                      return (dayInfo?.bookedCount ?? 0) > 0;
                    },
                  }}
                  modifiersClassNames={{
                    hasAvailability: 'bg-green-100 hover:bg-green-200',
                    full: 'bg-red-100 hover:bg-red-200',
                    hasBookings: 'font-bold',
                  }}
                  components={{
                    DayContent: ({ date }) => {
                      const dateStr = format(date, 'yyyy-MM-dd');
                      const dayInfo = monthlyAvailability[dateStr];
                      const bookedCount = dayInfo?.bookedCount ?? 0;
                      const availableCount = dayInfo?.availableCount ?? 0;
                      const isOpen = dayInfo?.isOpen ?? false;

                      return (
                        <div className="flex flex-col items-center">
                          <span>{date.getDate()}</span>
                          {isOpen && (bookedCount > 0 || availableCount > 0) && (
                            <span className={`text-[10px] leading-none ${availableCount === 0 ? 'text-red-600' : 'text-green-600'}`}>
                              {bookedCount > 0 ? `${bookedCount}人` : `残${availableCount}`}
                            </span>
                          )}
                        </div>
                      );
                    },
                  }}
                />
              </CardContent>
            </Card>

            <div className="mt-4 flex items-center gap-4 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-green-100 rounded"></div>
                <span>空きあり</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-red-100 rounded"></div>
                <span>満席</span>
              </div>
            </div>
          </section>
        )}

        {step === 'time' && (
          <section>
            <Button variant="ghost" className="mb-4" onClick={() => setStep('date')}>
              <ChevronLeft className="h-4 w-4 mr-2" />
              戻る
            </Button>

            <Card className="rounded-xl shadow-md bg-yellow-50 border-yellow-200 mb-6">
              <CardContent className="p-4">
                <div className="space-y-2">
                  <div>
                    <p className="text-sm text-gray-600">お子様</p>
                    <p className="font-semibold text-gray-800">{selectedChild?.name}</p>
                  </div>
                  <div className="pt-2 border-t border-yellow-300">
                    <p className="text-sm text-gray-600">校舎</p>
                    <p className="font-semibold text-gray-800">{selectedSchool?.name}</p>
                  </div>
                  <div className="pt-2 border-t border-yellow-300">
                    <p className="text-sm text-gray-600">体験日</p>
                    <p className="font-semibold text-gray-800">
                      {selectedDate && format(selectedDate, 'yyyy年MM月dd日 (E)', { locale: ja })}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">時間帯を選択</h2>

            {isClosed && (
              <Card className="rounded-xl shadow-md bg-red-50 border-red-200 mb-4">
                <CardContent className="p-4 flex items-center gap-3">
                  <AlertCircle className="h-5 w-5 text-red-600" />
                  <p className="text-red-700">この日は休講日です。別の日を選択してください。</p>
                </CardContent>
              </Card>
            )}

            {availabilityLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              </div>
            ) : (
              <div className="space-y-3">
                {getAvailableTimesForDate(selectedDate).map((timeSlot) => {
                  const avail = availability.find(a => a.scheduleId === timeSlot.id);
                  const isAvailable = avail ? avail.isAvailable : true;
                  const bookedCount = avail ? avail.bookedCount : 0;
                  const availableCount = avail ? avail.availableCount : timeSlot.trialCapacity;

                  return (
                    <Card
                      key={timeSlot.id}
                      className={`rounded-xl shadow-md transition-all ${
                        !isAvailable
                          ? 'opacity-50 cursor-not-allowed bg-gray-100'
                          : 'hover:shadow-lg cursor-pointer'
                      } ${selectedTime?.id === timeSlot.id ? 'border-2 border-blue-500 bg-blue-50' : ''}`}
                      onClick={() => isAvailable && handleTimeSelect(timeSlot, avail || null)}
                    >
                      <CardContent className="p-4 flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                          isAvailable ? 'bg-blue-100' : 'bg-gray-200'
                        }`}>
                          <Clock className={`h-6 w-6 ${isAvailable ? 'text-blue-600' : 'text-gray-400'}`} />
                        </div>
                        <div className="flex-1">
                          <p className={`font-semibold ${isAvailable ? 'text-gray-800' : 'text-gray-500'}`}>
                            {timeSlot.time}
                          </p>
                          <div className="flex items-center gap-2">
                            <p className={`text-sm ${isAvailable ? 'text-gray-600' : 'text-gray-400'}`}>
                              残り {availableCount} / {timeSlot.trialCapacity} 名
                            </p>
                            {!isAvailable && (
                              <Badge variant="secondary" className="bg-red-100 text-red-700">満席</Badge>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}

            {bookingError && (
              <Card className="rounded-xl shadow-md bg-red-50 border-red-200 mt-4">
                <CardContent className="p-4 flex items-center gap-3">
                  <AlertCircle className="h-5 w-5 text-red-600" />
                  <p className="text-red-700">{bookingError}</p>
                </CardContent>
              </Card>
            )}

            {selectedTime && selectedAvailability && (
              <Button
                onClick={handleConfirm}
                disabled={bookingLoading}
                className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg mt-6 disabled:opacity-50"
              >
                {bookingLoading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin mr-2" />
                    予約中...
                  </>
                ) : (
                  '体験を予約する'
                )}
              </Button>
            )}
          </section>
        )}

        {step === 'confirm' && bookingSuccess && (
          <section className="text-center py-8">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-10 w-10 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-4">予約完了</h2>
            <p className="text-gray-600 mb-6">体験授業のご予約ありがとうございます。</p>

            <Card className="rounded-xl shadow-md bg-gray-50 mb-6">
              <CardContent className="p-4 text-left">
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-gray-500">お子様</p>
                    <p className="font-semibold text-gray-800">{selectedChild?.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">校舎</p>
                    <p className="font-semibold text-gray-800">{selectedSchool?.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">日時</p>
                    <p className="font-semibold text-gray-800">
                      {selectedDate && format(selectedDate, 'yyyy年MM月dd日 (E)', { locale: ja })}
                      {' '}
                      {selectedTime?.time}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Link href="/">
              <Button className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg">
                ホームに戻る
              </Button>
            </Link>
          </section>
        )}
      </main>

      <BottomTabBar />
    </div>
  );
}
