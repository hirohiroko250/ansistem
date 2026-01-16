'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, MapPin, Users, Clock, AlertCircle, Check, Calendar as CalendarIcon, User, Circle, Triangle, X as XIcon, Minus, Loader2, BookOpen, Calculator, Pen, Gamepad2, Trophy, Globe, GraduationCap, type LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Calendar } from '@/components/ui/calendar';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { MapSchoolSelector } from '@/components/map-school-selector';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { format, getDay, addMonths, startOfMonth, endOfMonth, differenceInDays, addDays, startOfWeek, isSameDay, isToday } from 'date-fns';
import { ja } from 'date-fns/locale';
import { cn } from '@/lib/utils';
import { getChildren } from '@/lib/api/students';
import { getBrandCategories, getBrandSchools, getLessonCalendar, getClassSchedules, type BrandCategory, type CategoryBrand, type BrandSchool, type LessonCalendarDay, type ClassScheduleResponse, type TimeSlotSchedule, type ClassScheduleItem } from '@/lib/api/schools';
import { previewPricing, confirmPricing } from '@/lib/api/pricing';
import { getMyContracts, type MyContract } from '@/lib/api/contracts';
import type { Child, ApiError, PricingPreviewResponse } from '@/lib/api/types';
import { getMe } from '@/lib/api/auth';

// 曜日番号を曜日名に変換
const dayOfWeekNames: Record<number, string> = {
  0: '日曜日',
  1: '月曜日',
  2: '火曜日',
  3: '水曜日',
  4: '木曜日',
  5: '金曜日',
  6: '土曜日',
};

// チケット情報型（校舎で開講しているチケット一覧用）
type AvailableTicket = {
  ticketId: string;
  ticketName: string;
  durationMinutes?: number;
  gradeCode?: string;
  gradeName?: string;
  sortOrder?: number;
};

const dayMapping: Record<number, string> = {
  0: '日曜日',
  1: '月曜日',
  2: '火曜日',
  3: '水曜日',
  4: '木曜日',
  5: '金曜日',
  6: '土曜日',
};

// ブランドコードごとのアイコンとカラー設定
const brandStyleMap: Record<string, { icon: LucideIcon; color: string }> = {
  AEC: { icon: Globe, color: 'bg-blue-100 text-blue-600' },
  SOR: { icon: Calculator, color: 'bg-orange-100 text-orange-600' },
  BMC: { icon: Pen, color: 'bg-pink-100 text-pink-600' },
  PRO: { icon: Gamepad2, color: 'bg-purple-100 text-purple-600' },
  SHO: { icon: Trophy, color: 'bg-amber-100 text-amber-600' },
  KID: { icon: BookOpen, color: 'bg-green-100 text-green-600' },
  INT: { icon: Globe, color: 'bg-indigo-100 text-indigo-600' },
};

const getDefaultBrandStyle = () => ({ icon: GraduationCap, color: 'bg-gray-100 text-gray-600' });
const getBrandStyle = (brandCode: string) => brandStyleMap[brandCode] || getDefaultBrandStyle();

// 学年のソート順を定義
const gradeOrder: Record<string, number> = {
  '年少': 1,
  '年中': 2,
  '年長': 3,
  '小学1年': 10,
  '小学2年': 11,
  '小学3年': 12,
  '小学4年': 13,
  '小学5年': 14,
  '小学6年': 15,
  '中学1年': 20,
  '中学2年': 21,
  '中学3年': 22,
  '高校1年': 30,
  '高校2年': 31,
  '高校3年': 32,
};

const getGradeOrder = (grade?: string): number => {
  if (!grade) return 999;
  return gradeOrder[grade] ?? 999;
};

// チケット名からレベル/年齢順を推測（英会話クラスの色名など）
const ticketLevelOrder: Record<string, number> = {
  'White': 1,    // 低年齢
  'Yellow': 2,
  'Orange': 3,
  'Red': 4,
  'Purple': 5,
  'Blue': 6,
  'Green': 7,    // 高年齢
};

const getTicketLevelFromName = (ticketName: string): number => {
  // チケット名から色名を抽出してソート順を返す
  for (const [colorName, order] of Object.entries(ticketLevelOrder)) {
    if (ticketName.includes(colorName)) {
      return order;
    }
  }
  return 999; // 色名がない場合は最後
};

const sortChildrenByGrade = (children: Child[]): Child[] => {
  return [...children].sort((a, b) => getGradeOrder(a.grade) - getGradeOrder(b.grade));
};

// 選択したスケジュールを保持する型
type SelectedScheduleInfo = {
  id: string;
  dayOfWeek: string;
  startTime: string;
  endTime: string;
  className: string;
  capacity: number;
  reservedSeats: number;
};

export default function FromClassPurchasePage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [selectedChild, setSelectedChild] = useState<Child | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<BrandCategory | null>(null);
  const [selectedBrand, setSelectedBrand] = useState<CategoryBrand | null>(null);
  const [selectedSchoolId, setSelectedSchoolId] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [selectedDayOfWeek, setSelectedDayOfWeek] = useState<string | null>(null);
  const [startDate, setStartDate] = useState<Date>();
  const [selectedSchedules, setSelectedSchedules] = useState<string[]>([]);
  const [selectedScheduleInfo, setSelectedScheduleInfo] = useState<SelectedScheduleInfo[]>([]);
  const [additionalTicketCount, setAdditionalTicketCount] = useState(0);
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  // API関連のstate
  const [children, setChildren] = useState<Child[]>([]);
  const [isLoadingChildren, setIsLoadingChildren] = useState(true);
  const [childrenError, setChildrenError] = useState<string | null>(null);

  // 選択した生徒の既存契約（受講中クラス）
  const [existingContracts, setExistingContracts] = useState<MyContract[]>([]);

  const [categories, setCategories] = useState<BrandCategory[]>([]);
  const [isLoadingCategories, setIsLoadingCategories] = useState(true);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);

  const [schools, setSchools] = useState<BrandSchool[]>([]);
  const [isLoadingSchools, setIsLoadingSchools] = useState(false);
  const [schoolsError, setSchoolsError] = useState<string | null>(null);

  // ユーザーの近隣校舎ID
  const [nearestSchoolId, setNearestSchoolId] = useState<string | null>(null);

  // 開講時間割（APIから取得）
  const [classScheduleData, setClassScheduleData] = useState<ClassScheduleResponse | null>(null);
  const [isLoadingSchedules, setIsLoadingSchedules] = useState(false);
  const [schedulesError, setSchedulesError] = useState<string | null>(null);

  // 開講カレンダー
  const [lessonCalendar, setLessonCalendar] = useState<LessonCalendarDay[]>([]);
  const [isLoadingCalendar, setIsLoadingCalendar] = useState(false);

  const [pricingPreview, setPricingPreview] = useState<PricingPreviewResponse | null>(null);
  const [isLoadingPricing, setIsLoadingPricing] = useState(false);
  const [pricingError, setPricingError] = useState<string | null>(null);

  const [isConfirming, setIsConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  // チケット選択用
  const [availableTickets, setAvailableTickets] = useState<AvailableTicket[]>([]);
  const [isLoadingTickets, setIsLoadingTickets] = useState(false);
  const [ticketsError, setTicketsError] = useState<string | null>(null);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);

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

  // 選択した生徒の既存契約を取得
  useEffect(() => {
    if (!selectedChild) {
      setExistingContracts([]);
      return;
    }
    const fetchContracts = async () => {
      try {
        const response = await getMyContracts();
        // 選択した生徒のactive契約のみフィルタ
        const childContracts = response.contracts.filter(
          c => c.student.id === selectedChild.id && c.status === 'active'
        );
        setExistingContracts(childContracts);
      } catch (err) {
        console.error('Failed to fetch contracts:', err);
        setExistingContracts([]);
      }
    };
    fetchContracts();
  }, [selectedChild]);

  // ブランドカテゴリ一覧を取得
  useEffect(() => {
    const fetchCategories = async () => {
      setIsLoadingCategories(true);
      setCategoriesError(null);
      try {
        const data = await getBrandCategories();
        setCategories(data);
      } catch (err) {
        const apiError = err as ApiError;
        setCategoriesError(apiError.message || 'ブランド情報の取得に失敗しました');
      } finally {
        setIsLoadingCategories(false);
      }
    };
    fetchCategories();
  }, []);

  // カテゴリ選択時に校舎を取得（カテゴリ内の全ブランドの校舎を取得）
  useEffect(() => {
    if (!selectedCategory) return;

    const fetchSchools = async () => {
      setIsLoadingSchools(true);
      setSchoolsError(null);
      try {
        // カテゴリ内の全ブランドの校舎を取得して結合
        const categoryBrands = selectedCategory.brands || [];
        if (categoryBrands.length === 0) {
          setSchools([]);
          return;
        }

        const allSchoolsPromises = categoryBrands.map(brand => getBrandSchools(brand.id));
        const allSchoolsArrays = await Promise.all(allSchoolsPromises);

        // 校舎を結合し、IDで重複を除去
        const schoolMap = new Map<string, BrandSchool>();
        allSchoolsArrays.flat().forEach(school => {
          if (!schoolMap.has(school.id)) {
            schoolMap.set(school.id, school);
          }
        });
        const uniqueSchools = Array.from(schoolMap.values());

        // sortOrderでソート（sortOrderがなければ校舎名でソート）
        uniqueSchools.sort((a, b) => {
          const orderA = a.sortOrder ?? 9999;
          const orderB = b.sortOrder ?? 9999;
          if (orderA !== orderB) return orderA - orderB;
          return a.name.localeCompare(b.name, 'ja');
        });

        setSchools(uniqueSchools);
      } catch (err) {
        const apiError = err as ApiError;
        setSchoolsError(apiError.message || '校舎情報の取得に失敗しました');
      } finally {
        setIsLoadingSchools(false);
      }
    };
    fetchSchools();
  }, [selectedCategory]);

  // 校舎選択時にチケット一覧を取得（ClassScheduleから抽出）
  useEffect(() => {
    if (!selectedSchoolId) return;

    const fetchTickets = async () => {
      setIsLoadingTickets(true);
      setTicketsError(null);
      try {
        // ClassScheduleからチケット情報を取得
        const schedules = await getClassSchedules(
          selectedSchoolId,
          selectedBrand?.id,
          selectedCategory?.id
        );
        // schedules.timeSlotsからユニークなチケットIDを抽出
        const ticketMap = new Map<string, AvailableTicket>();
        schedules.timeSlots.forEach(ts => {
          Object.values(ts.days).forEach(day => {
            day.schedules.forEach(sched => {
              if (sched.ticketId && !ticketMap.has(sched.ticketId)) {
                ticketMap.set(sched.ticketId, {
                  ticketId: sched.ticketId,
                  ticketName: sched.ticketName || sched.ticketId,
                  durationMinutes: sched.durationMinutes,
                  gradeCode: sched.gradeCode,
                  gradeName: sched.gradeName,
                  sortOrder: sched.sortOrder,
                });
              }
            });
          });
        });
        // チケットを子どもの学年に合った順でソート
        const childGradeOrder = selectedChild ? getGradeOrder(selectedChild.grade) : 999;

        // 子どもの学年に基づいてチケットレベルの目安を決定
        // 幼児(年少〜年長)=1-3、小学低学年=4-6、小学高学年=7-9、中学生=10-12
        let childTicketLevel = 4; // デフォルトはRedあたり
        if (childGradeOrder <= 3) {
          childTicketLevel = 1; // 幼児 → White/Yellow
        } else if (childGradeOrder <= 12) {
          childTicketLevel = 3; // 小学1-3年 → Orange
        } else if (childGradeOrder <= 15) {
          childTicketLevel = 5; // 小学4-6年 → Purple
        } else {
          childTicketLevel = 6; // 中学生以上 → Blue/Green
        }

        const sortedTickets = Array.from(ticketMap.values()).sort((a, b) => {
          // チケット名から色レベルを取得
          const ticketLevelA = getTicketLevelFromName(a.ticketName);
          const ticketLevelB = getTicketLevelFromName(b.ticketName);

          // 子どもに合ったレベルに近いものを優先
          const distA = Math.abs(ticketLevelA - childTicketLevel);
          const distB = Math.abs(ticketLevelB - childTicketLevel);

          if (distA !== distB) return distA - distB;

          // sortOrderがある場合はそれを使用
          if (a.sortOrder !== undefined && b.sortOrder !== undefined) {
            return a.sortOrder - b.sortOrder;
          }

          // 最後はチケットレベル順（小さい方が低年齢）
          if (ticketLevelA !== ticketLevelB) {
            return ticketLevelA - ticketLevelB;
          }

          return a.ticketName.localeCompare(b.ticketName, 'ja');
        });
        setAvailableTickets(sortedTickets);
      } catch (err) {
        const apiError = err as ApiError;
        setTicketsError(apiError.message || 'チケット情報の取得に失敗しました');
        setAvailableTickets([]);
      } finally {
        setIsLoadingTickets(false);
      }
    };
    fetchTickets();
  }, [selectedSchoolId, selectedBrand?.id, selectedCategory?.id]);

  // チケット選択時に開講時間割を取得（APIから）
  useEffect(() => {
    if (!selectedSchoolId || !selectedTicketId) return;

    const fetchClassSchedules = async () => {
      setIsLoadingSchedules(true);
      setSchedulesError(null);
      try {
        const data = await getClassSchedules(
          selectedSchoolId,
          selectedBrand?.id,
          selectedCategory?.id,
          selectedTicketId  // チケットIDでフィルタリング
        );
        setClassScheduleData(data);
      } catch (err) {
        const apiError = err as ApiError;
        setSchedulesError(apiError.message || '開講時間割の取得に失敗しました');
        setClassScheduleData(null);
      } finally {
        setIsLoadingSchedules(false);
      }
    };
    fetchClassSchedules();
  }, [selectedSchoolId, selectedBrand?.id, selectedCategory?.id, selectedTicketId]);

  // 校舎選択時に開講カレンダーを取得
  useEffect(() => {
    if (!selectedBrand || !selectedSchoolId) return;

    const fetchCalendar = async () => {
      setIsLoadingCalendar(true);
      try {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth() + 1;
        const data = await getLessonCalendar({ brandId: selectedBrand.id, schoolId: selectedSchoolId, year, month });
        setLessonCalendar(data.calendar || []);
      } catch (err) {
        console.error('Failed to load calendar:', err);
        setLessonCalendar([]);
      } finally {
        setIsLoadingCalendar(false);
      }
    };
    fetchCalendar();
  }, [selectedBrand, selectedSchoolId]);

  const handleChildSelect = (child: Child) => {
    setSelectedChild(child);
    setStep(2);
  };

  const handleCategorySelect = (category: BrandCategory) => {
    setSelectedCategory(category);
    // カテゴリ選択後は直接校舎選択へ（ブランドは校舎選択後に絞り込む）
    // 最初のブランドを仮選択して校舎一覧を取得
    if (category.brands.length > 0) {
      setSelectedBrand(category.brands[0]);
    }
    setSelectedSchoolId(null);
    setStep(3);
  };

  const handleSchoolSelect = (schoolId: string) => {
    setSelectedSchoolId(schoolId);
    setSelectedTicketId(null);  // チケット選択をリセット
    // 校舎選択後は確認表示し、「次へ」ボタンで遷移
  };

  // 校舎確認後にチケット選択画面へ進む
  const handleConfirmSchool = () => {
    setStep(4); // チケット選択へ（新規追加）
  };

  // チケット選択時
  const handleTicketSelect = (ticketId: string) => {
    setSelectedTicketId(ticketId);
  };

  // チケット確認後に曜日・時間帯選択画面へ進む
  const handleConfirmTicket = () => {
    setStep(5); // 曜日・時間帯選択へ
  };

  const handleBackToStep = (targetStep: number) => {
    setStep(targetStep);
  };

  const handleTimeSlotSelect = (time: string, dayOfWeek: string) => {
    setSelectedTime(time);
    setSelectedDayOfWeek(dayOfWeek);
    setStep(6);  // 開始日・クラス選択へ
  };

  const handleScheduleToggle = (schedule: ClassScheduleItem) => {
    if (selectedSchedules.includes(schedule.id)) {
      setSelectedSchedules(selectedSchedules.filter(id => id !== schedule.id));
      setSelectedScheduleInfo(selectedScheduleInfo.filter(s => s.id !== schedule.id));
    } else {
      setSelectedSchedules([...selectedSchedules, schedule.id]);
      const dayNames: Record<string, string> = { '月': '月曜日', '火': '火曜日', '水': '水曜日', '木': '木曜日', '金': '金曜日', '土': '土曜日', '日': '日曜日' };
      setSelectedScheduleInfo([...selectedScheduleInfo, {
        id: schedule.id,
        dayOfWeek: selectedDayOfWeek || '',
        startTime: schedule.startTime,
        endTime: schedule.endTime,
        className: schedule.className,
        capacity: schedule.capacity,
        reservedSeats: schedule.reservedSeats,
      }]);
    }
  };

  const handleConfirm = async () => {
    if (!selectedChild || selectedSchedules.length === 0) return;

    setIsLoadingPricing(true);
    setPricingError(null);

    try {
      // 料金プレビューを取得
      const preview = await previewPricing({
        studentId: selectedChild.id,
        productIds: [],
        // courseIdはクラス予約の場合は使用しない
      });
      setPricingPreview(preview);
      setStep(7);  // 規約確認へ
    } catch (err) {
      const apiError = err as ApiError;
      setPricingError(apiError.message || '料金計算に失敗しました');
      // エラーでも次のステップへ進む
      setStep(7);  // 規約確認へ
    } finally {
      setIsLoadingPricing(false);
    }
  };

  const handleTermsAccepted = () => {
    const info = calculateAdditionalInfo();
    if (info.needed) {
      // 推奨枚数を自動設定
      setAdditionalTicketCount(info.tickets);
      setStep(8);  // 追加チケット購入へ
    } else {
      setStep(9);  // 予約確認へ
    }
  };

  // 購入確定
  const handleConfirmPurchase = async () => {
    if (!selectedChild) return;

    setIsConfirming(true);
    setConfirmError(null);

    try {
      const result = await confirmPricing({
        previewId: 'class-reservation',
        paymentMethod: 'credit_card',
        studentId: selectedChild.id,
        // 購入時に選択した情報を追加（生徒所属の自動作成用）
        brandId: selectedBrand?.id || undefined,
        schoolId: selectedSchoolId || undefined,
        startDate: startDate ? format(startDate, 'yyyy-MM-dd') : undefined,
        // スケジュール情報（曜日・時間帯）を送信
        schedules: selectedScheduleInfo.map(s => ({
          id: s.id,
          dayOfWeek: s.dayOfWeek,
          startTime: s.startTime,
          endTime: s.endTime,
          className: s.className,
        })),
        ticketId: selectedTicketId || undefined,
      });

      if (result.status === 'completed' || result.status === 'pending') {
        sessionStorage.setItem('purchaseResult', JSON.stringify({
          orderId: result.orderId,
          childName: selectedChild.fullName,
          courseName: `クラス予約（${selectedSchedules.length}クラス）`,
          amount: totalPrice,
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

  const selectedSchool = schools.find((s) => s.id === selectedSchoolId);

  // 選択した曜日・時間のスケジュールを取得（選択したチケットIDでフィルタリング）
  const getSchedulesForTimeAndDay = (): ClassScheduleItem[] => {
    if (!classScheduleData || !selectedTime || !selectedDayOfWeek) return [];
    const dayShort = selectedDayOfWeek.replace('曜日', '');
    const timeSlot = classScheduleData.timeSlots.find(ts => ts.time === selectedTime);
    if (!timeSlot) return [];
    const schedules = timeSlot.days[dayShort]?.schedules || [];
    // 選択したチケットIDでフィルタリング（バックエンドでもフィルタしているが、念のためフロントでも）
    if (selectedTicketId) {
      return schedules.filter(s => s.ticketId === selectedTicketId);
    }
    return schedules;
  };

  const filteredSchedulesByTimeAndDay = getSchedulesForTimeAndDay();

  const pricePerClass = 6000;
  const regularPrice = selectedScheduleInfo.length * pricePerClass;

  const calculateAdditionalInfo = () => {
    if (!startDate) return { needed: false, tickets: 0, price: 0, currentDay: 0, lessonDates: [] };

    const currentDay = startDate.getDate();
    const startDateStr = format(startDate, 'yyyy-MM-dd');
    const monthEnd = endOfMonth(startDate);
    const monthEndStr = format(monthEnd, 'yyyy-MM-dd');

    // 月初1日からの開始の場合は追加チケット不要
    if (currentDay === 1) {
      return { needed: false, tickets: 0, price: 0, currentDay, lessonDates: [] };
    }

    // 開講カレンダーから開始日以降の今月の開講日を数える
    const lessonDates: string[] = [];

    if (lessonCalendar.length > 0) {
      // カレンダーデータがある場合は正確に計算
      for (const day of lessonCalendar) {
        if (!day.isOpen) continue;
        // 開始日以降かつ今月末まで
        if (day.date >= startDateStr && day.date <= monthEndStr) {
          lessonDates.push(day.date);
        }
      }
    } else {
      // カレンダーデータがない場合は概算（週4回と仮定）
      const remainingDays = differenceInDays(monthEnd, startDate) + 1;
      const estimatedLessons = Math.ceil(remainingDays / 7) * 4;
      for (let i = 0; i < estimatedLessons; i++) {
        lessonDates.push(`estimated-${i}`);
      }
    }

    const tickets = lessonDates.length;
    const additionalPrice = tickets * pricePerClass;

    return {
      needed: tickets > 0,
      tickets,
      price: additionalPrice,
      currentDay,
      lessonDates,
    };
  };

  const additionalInfo = calculateAdditionalInfo();
  const additionalTicketPrice = additionalTicketCount * pricePerClass;
  const totalPrice = pricingPreview?.grandTotal ?? (regularPrice + additionalTicketPrice);

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="flex-shrink-0 bg-white shadow-sm z-40">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">クラスから選択</h1>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[390px] mx-auto px-4 py-6 pb-24">
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
            {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((s) => (
              <div
                key={s}
                className={`h-2 flex-1 rounded-full transition-colors ${s <= step ? 'bg-green-500' : 'bg-gray-200'
                  }`}
              />
            ))}
          </div>
          <p className="text-center text-sm text-gray-600 mt-2">
            Step {step} / 9
          </p>
        </div>

        {step === 1 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">お子様を選択</h2>

            {isLoadingChildren ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-green-500 mb-3" />
                <p className="text-sm text-gray-600">お子様情報を読み込み中...</p>
              </div>
            ) : childrenError ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="flex items-center gap-2 p-4 rounded-lg bg-red-50 border border-red-200 mb-4">
                  <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                  <p className="text-sm text-red-800">{childrenError}</p>
                </div>
                <Button onClick={() => window.location.reload()} variant="outline">
                  再読み込み
                </Button>
              </div>
            ) : children.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <p className="text-gray-600 mb-4">登録されているお子様がいません</p>
                <Link href="/children">
                  <Button>お子様を登録する</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {sortChildrenByGrade(children).map((child) => (
                  <Card
                    key={child.id}
                    className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                    onClick={() => handleChildSelect(child)}
                  >
                    <CardContent className="p-4 flex items-center">
                      <div className="w-14 h-14 rounded-full bg-green-100 text-green-600 flex items-center justify-center mr-4">
                        <User className="h-7 w-7" />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-800">{child.fullName}</h3>
                        <p className="text-sm text-gray-600">{child.grade}</p>
                      </div>
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
              <Card className="rounded-xl shadow-sm bg-green-50 border-green-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中のお子様</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName}（{selectedChild?.grade}）</p>
                </CardContent>
              </Card>
            </div>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">カテゴリを選択</h2>

            {isLoadingCategories ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-green-500 mb-3" />
                <p className="text-sm text-gray-600">カテゴリを読み込み中...</p>
              </div>
            ) : categoriesError ? (
              <div className="flex items-center gap-2 p-4 rounded-lg bg-red-50 border border-red-200 mb-4">
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                <p className="text-sm text-red-800">{categoriesError}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {categories.map((category) => {
                  // カテゴリ内の最初のブランドのコードでスタイルを決定
                  const firstBrandCode = category.brands[0]?.brandCode || '';
                  const style = getBrandStyle(firstBrandCode);
                  const Icon = style.icon;
                  return (
                    <Card
                      key={category.id}
                      className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                      onClick={() => handleCategorySelect(category)}
                    >
                      <CardContent className="p-4 flex items-center">
                        <div className={`w-14 h-14 rounded-full ${style.color} flex items-center justify-center mr-4`}>
                          <Icon className="h-7 w-7" />
                        </div>
                        <span className="text-lg font-semibold text-gray-800">{category.categoryName}</span>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="flex flex-col h-full">
            {/* コンパクトな選択状況表示 */}
            <div className="flex items-center gap-2 mb-3 text-sm">
              <span className="text-gray-500">選択中:</span>
              <span className="font-medium text-gray-800">{selectedChild?.fullName}</span>
              <span className="text-gray-400">›</span>
              <span className="text-green-600">{selectedCategory?.categoryName}</span>
            </div>

            <h2 className="text-lg font-semibold text-gray-800 mb-1">校舎を選択</h2>
            <p className="text-xs text-gray-500 mb-2">
              地図上のピンをタップして校舎を選択
            </p>

            {schoolsError ? (
              <div className="flex items-center gap-2 p-4 rounded-lg bg-red-50 border border-red-200 mb-4">
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                <p className="text-sm text-red-800">{schoolsError}</p>
              </div>
            ) : (
              <div className="flex-1 flex flex-col min-h-0">
                {/* マップコンテナ - 正方形 */}
                <div className="w-full aspect-square max-w-[350px] mx-auto">
                  <MapSchoolSelector
                    schools={schools}
                    selectedSchoolId={selectedSchoolId}
                    onSelectSchool={handleSchoolSelect}
                    isLoading={isLoadingSchools}
                    initialSchoolId={nearestSchoolId}
                  />
                </div>

                {/* 選択した校舎の確認と次へボタン - 常に表示 */}
                <div className="mt-3 space-y-2">
                  {selectedSchool ? (
                    <>
                      <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-gray-500">選択した校舎</p>
                          <p className="font-semibold text-gray-800 truncate">{selectedSchool.name}</p>
                          <p className="text-xs text-gray-500 truncate">{selectedSchool.address}</p>
                        </div>
                      </div>
                      <Button
                        onClick={handleConfirmSchool}
                        className="w-full h-12 rounded-full bg-green-600 hover:bg-green-700 text-white font-semibold"
                      >
                        次へ
                      </Button>
                    </>
                  ) : (
                    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 text-center">
                      <p className="text-sm text-gray-500">地図から校舎を選択してください</p>
                    </div>
                  )}
                </div>
              </div>
            )}

          </div>
        )}

        {/* Step 4: チケット（コース）選択 */}
        {step === 4 && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-green-50 border-green-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中の校舎</p>
                  <p className="font-semibold text-gray-800">{selectedSchool?.name}</p>
                  <p className="text-xs text-gray-600 mt-1">対象: {selectedChild?.fullName}（{selectedChild?.grade}）</p>
                </CardContent>
              </Card>
            </div>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">コース（チケット）を選択</h2>
            <p className="text-sm text-gray-600 mb-4">
              お子様の年齢・レベルに合ったコースを選択してください。
            </p>

            {isLoadingTickets ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-green-500 mb-3" />
                <p className="text-sm text-gray-600">コース情報を読み込み中...</p>
              </div>
            ) : ticketsError ? (
              <div className="flex items-center gap-2 p-4 rounded-lg bg-red-50 border border-red-200 mb-4">
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                <p className="text-sm text-red-800">{ticketsError}</p>
              </div>
            ) : availableTickets.length === 0 ? (
              <div className="text-center py-12">
                <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500">この校舎で開講中のコースがありません</p>
              </div>
            ) : (
              <div className="space-y-3">
                {availableTickets.map((ticket) => (
                  <Card
                    key={ticket.ticketId}
                    className={`rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer ${
                      selectedTicketId === ticket.ticketId
                        ? 'border-2 border-green-500 bg-green-50'
                        : ''
                    }`}
                    onClick={() => handleTicketSelect(ticket.ticketId)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-semibold text-gray-800">{ticket.ticketName}</h3>
                          {ticket.durationMinutes && (
                            <div className="flex items-center gap-1 mt-1 text-sm text-gray-600">
                              <Clock className="h-4 w-4" />
                              <span>{ticket.durationMinutes}分</span>
                            </div>
                          )}
                        </div>
                        {selectedTicketId === ticket.ticketId && (
                          <div className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center">
                            <Check className="h-4 w-4 text-white" />
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {selectedTicketId && (
              <Button
                onClick={handleConfirmTicket}
                className="w-full h-14 rounded-full bg-green-600 hover:bg-green-700 text-white font-semibold text-lg mt-6"
              >
                次へ
              </Button>
            )}
          </div>
        )}

        {/* Step 5: 曜日・時間帯選択 */}
        {step === 5 && (() => {
          const dayLabels = classScheduleData?.dayLabels || ['月', '火', '水', '木', '金', '土', '日'];

          const getStatusIcon = (status: string) => {
            switch (status) {
              case 'available':
                return <Circle className="h-5 w-5 text-green-600 fill-green-600" />;
              case 'few':
                return <Triangle className="h-5 w-5 text-orange-500 fill-orange-500" />;
              case 'full':
                return <XIcon className="h-5 w-5 text-red-600" />;
              case 'none':
                return <Minus className="h-5 w-5 text-gray-300" />;
              default:
                return null;
            }
          };

          const selectedTicket = availableTickets.find(t => t.ticketId === selectedTicketId);

          return (
            <div>
              <div className="mb-4">
                <Card className="rounded-xl shadow-sm bg-green-50 border-green-200">
                  <CardContent className="p-3">
                    <p className="text-xs text-gray-600 mb-1">選択中の校舎・コース</p>
                    <p className="font-semibold text-gray-800">{selectedSchool?.name}</p>
                    <p className="text-sm text-gray-700">{selectedTicket?.ticketName}</p>
                    <p className="text-xs text-gray-600 mt-1">対象: {selectedChild?.fullName}</p>
                  </CardContent>
                </Card>
              </div>

              <h2 className="text-lg font-semibold text-gray-800 mb-4">曜日・時間帯を選択</h2>
              <p className="text-sm text-gray-600 mb-4">
                希望する曜日と時間帯を選択してください。
              </p>

              <div className="mb-4 flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1">
                  <Circle className="h-4 w-4 text-green-600 fill-green-600" />
                  <span>空席あり</span>
                </div>
                <div className="flex items-center gap-1">
                  <Triangle className="h-4 w-4 text-orange-500 fill-orange-500" />
                  <span>残り僅か</span>
                </div>
                <div className="flex items-center gap-1">
                  <XIcon className="h-4 w-4 text-red-600" />
                  <span>満席</span>
                </div>
                <div className="flex items-center gap-1">
                  <Minus className="h-4 w-4 text-gray-300" />
                  <span>休講</span>
                </div>
              </div>

              {isLoadingSchedules ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-green-500 mb-3" />
                  <p className="text-sm text-gray-600">開講時間割を読み込み中...</p>
                </div>
              ) : schedulesError ? (
                <div className="flex items-center gap-2 p-4 rounded-lg bg-red-50 border border-red-200 mb-4">
                  <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                  <p className="text-sm text-red-800">{schedulesError}</p>
                </div>
              ) : !classScheduleData || classScheduleData.timeSlots.length === 0 ? (
                <div className="text-center py-12">
                  <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                  <p className="text-gray-500">このコースの開講クラスがありません</p>
                </div>
              ) : (
              <Card className="rounded-xl shadow-md overflow-hidden">
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-gradient-to-r from-green-600 to-green-700 text-white">
                          <th className="text-xs font-semibold py-3 px-2 text-left sticky left-0 bg-green-600 z-10">時間</th>
                          {dayLabels.map((label, idx) => (
                            <th key={idx} className="text-xs font-semibold py-3 px-2 text-center min-w-[50px]">
                              {label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {classScheduleData.timeSlots.map((timeSlot, timeIdx) => (
                          <tr key={timeIdx} className="border-b border-gray-200 hover:bg-gray-50">
                            <td className="text-xs font-semibold py-3 px-2 bg-gray-50 sticky left-0 z-10">
                              {timeSlot.time}
                            </td>
                            {dayLabels.map((label, dayIdx) => {
                              const dayData = timeSlot.days[label];
                              const status = dayData?.status || 'none';
                              const canSelect = status !== 'none' && status !== 'full';
                              const dayOfWeekName = label + '曜日';
                              const isSelected = selectedTime === timeSlot.time && selectedDayOfWeek === dayOfWeekName;

                              return (
                                <td
                                  key={dayIdx}
                                  className={`text-center py-3 px-2 ${canSelect ? 'cursor-pointer hover:bg-green-50' : ''
                                    } ${isSelected ? 'bg-green-100' : ''
                                    }`}
                                  onClick={() => {
                                    if (canSelect) {
                                      handleTimeSlotSelect(timeSlot.time, dayOfWeekName);
                                    }
                                  }}
                                >
                                  {getStatusIcon(status)}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
              )}
            </div>
          );
        })()}

        {/* Step 6: 開始日・クラス選択 */}
        {step === 6 && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-green-50 border-green-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中の情報</p>
                  <p className="font-semibold text-gray-800">{selectedSchool?.name}</p>
                  <p className="text-sm text-gray-700 mt-1">
                    {selectedDayOfWeek} {selectedTime}～
                  </p>
                  <p className="text-xs text-gray-600 mt-1">対象: {selectedChild?.fullName}</p>
                </CardContent>
              </Card>
            </div>

            {selectedScheduleInfo.length > 0 && (
              <Card className="rounded-xl shadow-sm bg-green-50 border-green-200 mb-4">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-2">選択中のクラス</p>
                  <div className="space-y-1">
                    {selectedScheduleInfo.map(schedule => (
                      <p key={schedule.id} className="text-sm font-semibold text-gray-800">
                        {schedule.dayOfWeek} {schedule.startTime}-{schedule.endTime} ({schedule.className})
                      </p>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <h2 className="text-lg font-semibold text-gray-800 mb-4">開始日を選択</h2>
            <p className="text-sm text-gray-600 mb-4">
              レッスンを開始する日付を選択してください。
            </p>

            {/* カレンダー凡例 */}
            {lessonCalendar.length > 0 && (
              <Card className="rounded-xl shadow-md mb-4">
                <CardContent className="p-3">
                  <div className="flex items-center justify-center gap-4 text-sm">
                    <div className="flex items-center gap-1">
                      <div className="w-4 h-4 rounded-full bg-orange-500"></div>
                      <span className="flex items-center gap-1">
                        <Globe className="h-3 w-3" /> 外国人講師
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-4 h-4 rounded-full bg-blue-500"></div>
                      <span className="flex items-center gap-1">
                        <Users className="h-3 w-3" /> 日本人講師
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <Card className="rounded-xl shadow-md mb-4">
              <CardContent className="p-4">
                <Calendar
                  mode="single"
                  selected={startDate}
                  onSelect={setStartDate}
                  disabled={(date) => {
                    if (date < new Date()) return true;
                    // 選択した曜日と一致するかチェック
                    const dayOfWeek = dayMapping[getDay(date)];
                    if (dayOfWeek !== selectedDayOfWeek) return true;
                    // 開講カレンダーがある場合は開講日のみ選択可能
                    if (lessonCalendar.length > 0) {
                      const dateStr = format(date, 'yyyy-MM-dd');
                      const calendarDay = lessonCalendar.find(d => d.date === dateStr);
                      return !calendarDay?.isOpen;
                    }
                    return false;
                  }}
                  modifiers={lessonCalendar.length > 0 ? {
                    nativeDay: (date) => {
                      const dateStr = format(date, 'yyyy-MM-dd');
                      const calendarDay = lessonCalendar.find(d => d.date === dateStr);
                      return calendarDay?.isNativeDay ?? false;
                    },
                    japaneseOnly: (date) => {
                      const dateStr = format(date, 'yyyy-MM-dd');
                      const calendarDay = lessonCalendar.find(d => d.date === dateStr);
                      return calendarDay?.isJapaneseOnly ?? false;
                    },
                  } : undefined}
                  modifiersStyles={{
                    nativeDay: {
                      backgroundColor: '#fed7aa',
                      borderRadius: '50%',
                    },
                    japaneseOnly: {
                      backgroundColor: '#bfdbfe',
                      borderRadius: '50%',
                    },
                  }}
                  locale={ja}
                  className="rounded-md"
                />
              </CardContent>
            </Card>

            <h2 className="text-lg font-semibold text-gray-800 mb-4 mt-6">
              クラスを選択（複数可）
            </h2>

            {filteredSchedulesByTimeAndDay.length > 0 ? (
              <div className="space-y-2">
                {filteredSchedulesByTimeAndDay.map(schedule => {
                  const isSelected = selectedSchedules.includes(schedule.id);
                  const isFull = schedule.availableSeats <= 0;
                  const availableSeats = schedule.availableSeats;

                  return (
                    <Card
                      key={schedule.id}
                      className={`rounded-xl shadow-sm transition-all cursor-pointer ${isSelected ? 'border-2 border-green-500 bg-green-50' :
                          isFull ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md'
                        }`}
                      onClick={() => !isFull && handleScheduleToggle(schedule)}
                    >
                      <CardContent className="p-3">
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3 flex-1">
                            <Checkbox
                              checked={isSelected}
                              disabled={isFull}
                              className="mt-1"
                            />
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-semibold text-gray-800">
                                  {schedule.className}
                                </span>
                              </div>
                              <div className="flex items-center gap-2 mb-1">
                                <Clock className="h-4 w-4 text-gray-600" />
                                <span className="text-sm text-gray-700">
                                  {schedule.startTime} - {schedule.endTime}
                                </span>
                              </div>
                              {schedule.displayCourseName && (
                                <p className="text-xs text-gray-500 mb-1">
                                  {schedule.displayCourseName}
                                </p>
                              )}
                              <div className="flex items-center gap-2">
                                <Users className="h-4 w-4 text-gray-500" />
                                <span className={`text-xs ${isFull ? 'text-red-600 font-semibold' :
                                    availableSeats <= 2 ? 'text-orange-600 font-semibold' :
                                      'text-gray-600'
                                  }`}>
                                  {isFull ? '満席' : `残り${availableSeats}席`}
                                </span>
                              </div>
                            </div>
                          </div>
                          {isSelected && (
                            <div className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center">
                              <Check className="h-4 w-4 text-white" />
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-12">
                <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500">この時間帯には開講中のクラスがありません</p>
                <Button
                  onClick={() => setStep(5)}
                  variant="outline"
                  className="mt-4"
                >
                  別の時間帯を選択
                </Button>
              </div>
            )}

            {selectedSchedules.length > 0 && startDate && (
              <Button
                onClick={handleConfirm}
                disabled={isLoadingPricing}
                className="w-full h-14 rounded-full bg-green-600 hover:bg-green-700 text-white font-semibold text-lg mt-6"
              >
                {isLoadingPricing ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    計算中...
                  </span>
                ) : (
                  `規約確認へ（${selectedSchedules.length}クラス選択中）`
                )}
              </Button>
            )}
          </div>
        )}

        {/* Step 7: 利用規約の確認 */}
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
              onClick={handleTermsAccepted}
              disabled={!agreedToTerms}
              className="w-full h-14 rounded-full bg-green-600 hover:bg-green-700 text-white font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              同意して次へ
            </Button>
          </div>
        )}

        {/* Step 8: 追加チケット購入 */}
        {step === 8 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">追加チケットの購入</h2>

            {/* 選択したクラス情報（受講曜日・時間）を表示 */}
            {selectedScheduleInfo.length > 0 && (
              <Card className="rounded-xl shadow-md mb-4 border-blue-200 bg-blue-50">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <CalendarIcon className="h-5 w-5 text-blue-600" />
                    <h3 className="font-semibold text-blue-900">受講するクラス</h3>
                  </div>
                  <div className="space-y-2">
                    {selectedScheduleInfo.map((schedule) => (
                      <div key={schedule.id} className="flex items-center justify-between bg-white rounded-lg p-3 border border-blue-100">
                        <div>
                          <p className="font-semibold text-gray-800">
                            {schedule.dayOfWeek} {schedule.startTime}～{schedule.endTime}
                          </p>
                          <p className="text-sm text-gray-600">{schedule.className}</p>
                        </div>
                        <Badge className="bg-blue-500 text-white">
                          {selectedTicketId ? availableTickets.find(t => t.ticketId === selectedTicketId)?.ticketName : 'クラス'}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 現在受講中のクラス（既存契約） */}
            {existingContracts.length > 0 && (
              <Card className="rounded-xl shadow-md mb-4 border-green-200 bg-green-50">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <BookOpen className="h-5 w-5 text-green-600" />
                    <h3 className="font-semibold text-green-900">現在受講中のクラス</h3>
                  </div>
                  <div className="space-y-2">
                    {existingContracts.map((contract) => (
                      <div key={contract.id} className="flex items-center justify-between bg-white rounded-lg p-3 border border-green-100">
                        <div>
                          <p className="font-semibold text-gray-800">
                            {contract.dayOfWeek !== undefined && contract.dayOfWeek !== null
                              ? `${dayOfWeekNames[contract.dayOfWeek]} ${contract.startTime || ''}～${contract.endTime || ''}`
                              : contract.course?.courseName || contract.ticket?.ticketName || '受講中'}
                          </p>
                          <p className="text-sm text-gray-600">
                            {contract.brand?.brandName || ''} / {contract.school?.schoolName || '未設定'}
                          </p>
                        </div>
                        <Badge className="bg-green-500 text-white">受講中</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <Card className="rounded-xl shadow-md mb-4 border-orange-200 bg-orange-50">
              <CardContent className="p-4">
                <div className="flex gap-3">
                  <AlertCircle className="h-5 w-5 text-orange-600 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-orange-900 mb-1">月半ばの入会について</h3>
                    <p className="text-sm text-orange-800 mb-3">
                      開始日が{additionalInfo.currentDay}日です。翌月から通常コース（月4回分チケット）が開始されます。
                    </p>
                    <p className="text-sm text-orange-800 mb-2">
                      今月の残りレッスン日数: <span className="font-bold">{additionalInfo.tickets}回</span>
                    </p>
                    {lessonCalendar.length > 0 ? (
                      <p className="text-xs text-orange-700">
                        ※ 開講カレンダーに基づいて計算しています
                      </p>
                    ) : (
                      <p className="text-xs text-orange-700">
                        ※ 概算値です（週4回と仮定）
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-xl shadow-md mb-4">
              <CardContent className="p-4">
                <h3 className="font-semibold text-gray-800 mb-3">単品チケット購入枚数</h3>
                <p className="text-sm text-gray-600 mb-4">
                  1回あたり ¥{pricePerClass.toLocaleString()}
                </p>

                <div className="flex items-center gap-4">
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setAdditionalTicketCount(Math.max(0, additionalTicketCount - 1))}
                    className="h-12 w-12 rounded-full"
                  >
                    <Minus className="h-5 w-5" />
                  </Button>

                  <div className="flex-1 text-center">
                    <div className="text-3xl font-bold text-gray-800">{additionalTicketCount}</div>
                    <div className="text-sm text-gray-600">枚</div>
                  </div>

                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setAdditionalTicketCount(additionalTicketCount + 1)}
                    className="h-12 w-12 rounded-full"
                  >
                    <Check className="h-5 w-5" />
                  </Button>
                </div>

                {additionalTicketCount > 0 && (
                  <div className="mt-4 p-3 bg-green-50 rounded-lg">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-700">小計</span>
                      <span className="text-lg font-bold text-green-600">
                        ¥{(additionalTicketCount * pricePerClass).toLocaleString()}
                      </span>
                    </div>
                  </div>
                )}

                <div className="mt-4 space-y-2">
                  <Button
                    variant="outline"
                    onClick={() => setAdditionalTicketCount(additionalInfo.tickets)}
                    className="w-full"
                  >
                    推奨枚数を選択（{additionalInfo.tickets}枚）
                  </Button>
                </div>
              </CardContent>
            </Card>

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setAdditionalTicketCount(0);
                  setStep(9);
                }}
                className="flex-1 h-14 rounded-full"
              >
                スキップ
              </Button>
              <Button
                onClick={() => setStep(9)}
                className="flex-1 h-14 rounded-full bg-green-600 hover:bg-green-700 text-white font-semibold"
              >
                確認画面へ
              </Button>
            </div>
          </div>
        )}

        {/* Step 9: 予約確認 */}
        {step === 9 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">予約内容の確認</h2>

            {confirmError && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 mb-4">
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                <p className="text-sm text-red-800">{confirmError}</p>
              </div>
            )}

            <Card className="rounded-xl shadow-md mb-6">
              <CardContent className="p-6 space-y-4">
                <div>
                  <p className="text-sm text-gray-600 mb-1">対象のお子様</p>
                  <p className="font-semibold text-gray-800">
                    {selectedChild?.fullName}（{selectedChild?.grade}）
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">ブランド</p>
                  <p className="font-semibold text-gray-800">{selectedBrand?.brandName}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">校舎</p>
                  <p className="font-semibold text-gray-800">{selectedSchool?.name}</p>
                  <p className="text-sm text-gray-600">{selectedSchool?.address}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">開始日</p>
                  <p className="font-semibold text-gray-800">
                    {startDate && format(startDate, 'yyyy年MM月dd日（E）', { locale: ja })}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-2">選択したクラス</p>
                  <div className="space-y-2">
                    {selectedScheduleInfo.map(schedule => (
                      <div key={schedule.id} className="bg-gray-50 rounded-lg p-3">
                        <p className="font-semibold text-gray-800">
                          {schedule.className}
                        </p>
                        <p className="text-sm text-gray-600">
                          {schedule.dayOfWeek} {schedule.startTime}-{schedule.endTime}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
                {/* 料金詳細 */}
                <div className="border-t pt-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-semibold text-gray-800">料金詳細</h4>
                  </div>

                  {pricingPreview && pricingPreview.items.length > 0 ? (
                    <div className="space-y-2">
                      {/* 料金項目 */}
                      {pricingPreview.items.map((item, idx) => (
                        <div key={idx} className="flex justify-between items-center text-sm">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-700">{item.productName}</span>
                            {item.quantity > 1 && (
                              <span className="text-xs text-gray-500">×{item.quantity}</span>
                            )}
                          </div>
                          <span className="font-medium">¥{item.total.toLocaleString()}</span>
                        </div>
                      ))}

                      {/* 割引 */}
                      {pricingPreview.discounts.length > 0 && (
                        <>
                          {pricingPreview.discounts.map((discount, idx) => (
                            <div key={`discount-${idx}`} className="flex justify-between items-center text-sm text-green-600">
                              <span>{discount.discountName}</span>
                              <span className="font-medium">-¥{(discount.discountAmount || discount.appliedAmount || 0).toLocaleString()}</span>
                            </div>
                          ))}
                        </>
                      )}

                      {/* 追加チケット（手動選択分） */}
                      {additionalTicketCount > 0 && (
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-gray-700">追加チケット ({additionalTicketCount}回分)</span>
                          <span className="font-medium">¥{additionalTicketPrice.toLocaleString()}</span>
                        </div>
                      )}

                      {/* 小計・税 */}
                      <div className="border-t pt-2 mt-2 space-y-1">
                        <div className="flex justify-between items-center text-xs text-gray-500">
                          <span>小計</span>
                          <span>¥{pricingPreview.subtotal.toLocaleString()}</span>
                        </div>
                        {pricingPreview.taxTotal > 0 && (
                          <div className="flex justify-between items-center text-xs text-gray-500">
                            <span>消費税</span>
                            <span>¥{pricingPreview.taxTotal.toLocaleString()}</span>
                          </div>
                        )}
                        {pricingPreview.discountTotal > 0 && (
                          <div className="flex justify-between items-center text-xs text-green-600">
                            <span>割引合計</span>
                            <span>-¥{pricingPreview.discountTotal.toLocaleString()}</span>
                          </div>
                        )}
                      </div>

                      {/* 合計 */}
                      <div className="flex justify-between items-center text-lg font-bold pt-2 border-t">
                        <span>合計金額</span>
                        <span className="text-green-600">¥{(pricingPreview.grandTotal + additionalTicketPrice).toLocaleString()}</span>
                      </div>
                    </div>
                  ) : (
                    /* pricingPreviewがない場合は従来の表示 */
                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-600">月額料金</span>
                        <span className="font-semibold">
                          ¥{regularPrice.toLocaleString()} ({selectedSchedules.length}クラス × 月4回)
                        </span>
                      </div>
                      {additionalTicketCount > 0 && (
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-gray-600">単品チケット</span>
                          <span className="font-semibold">
                            ¥{additionalTicketPrice.toLocaleString()} ({additionalTicketCount}回分)
                          </span>
                        </div>
                      )}
                      <div className="flex justify-between items-center text-lg font-bold pt-2 border-t">
                        <span>合計金額</span>
                        <span className="text-green-600">¥{totalPrice.toLocaleString()}</span>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Button
              onClick={handleConfirmPurchase}
              disabled={isConfirming}
              className="w-full h-14 rounded-full bg-green-600 hover:bg-green-700 text-white font-semibold text-lg disabled:opacity-70"
            >
              {isConfirming ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  処理中...
                </span>
              ) : (
                '予約を確定する'
              )}
            </Button>
          </div>
        )}
        </div>
      </main>

      <BottomTabBar />
    </div>
  );
}
