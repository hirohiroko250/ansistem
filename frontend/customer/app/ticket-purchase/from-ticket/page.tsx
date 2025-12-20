'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, Package, Sparkles, Calendar as CalendarIcon, Loader2, AlertCircle, BookOpen, Calculator, Pen, Gamepad2, Trophy, Globe, GraduationCap, Clock, Users, CheckCircle2, Circle, Triangle, X as XIcon, Minus, type LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar } from '@/components/ui/calendar';
import { Checkbox } from '@/components/ui/checkbox';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { format, addDays, lastDayOfMonth, eachDayOfInterval, getDay, startOfMonth } from 'date-fns';
import { ja } from 'date-fns/locale';

// 曜日名を数値に変換（日曜=0, 月曜=1, ...）- JavaScript getDay形式
const dayOfWeekToNumber: Record<string, number> = {
  '日': 0,
  '月': 1,
  '火': 2,
  '水': 3,
  '木': 4,
  '金': 5,
  '土': 6,
};

// 曜日名をバックエンド形式に変換（月=1, 火=2, ... 日=7）
const dayOfWeekToBackendNumber = (dayOfWeekName: string | null): number | undefined => {
  if (!dayOfWeekName) return undefined;
  // "水曜日" → "水"
  const dayChar = dayOfWeekName.replace('曜日', '').charAt(0);
  const mapping: Record<string, number> = {
    '月': 1,
    '火': 2,
    '水': 3,
    '木': 4,
    '金': 5,
    '土': 6,
    '日': 7,
  };
  return mapping[dayChar];
};

// 開始日から月末までの指定曜日の回数を計算
const countDayOfWeekOccurrences = (
  startDate: Date,
  dayOfWeek: string
): { count: number; dates: Date[] } => {
  const dayNum = dayOfWeekToNumber[dayOfWeek];
  if (dayNum === undefined) return { count: 0, dates: [] };

  const endOfMonth = lastDayOfMonth(startDate);
  const daysInRange = eachDayOfInterval({ start: startDate, end: endOfMonth });
  const matchingDates = daysInRange.filter(date => getDay(date) === dayNum);

  return {
    count: matchingDates.length,
    dates: matchingDates,
  };
};
import { getChildren } from '@/lib/api/students';
import { getPublicCourses, getPublicPacks, getPublicBrands } from '@/lib/api/courses';
import { getBrandSchools, getClassSchedules, getSchoolsByTicket, getTicketsBySchool, type BrandSchool, type ClassScheduleResponse, type ClassScheduleItem } from '@/lib/api/schools';
import { MapSchoolSelector } from '@/components/map-school-selector';
import { previewPricing, confirmPricing, getEnrollmentBillingInfo, type EnrollmentBillingInfo } from '@/lib/api/pricing';
import { getStaffLessonSchedules, type StaffLessonSchedule } from '@/lib/api/lessons';
import api from '@/lib/api/client';
import type { Child, PublicCourse, PublicPack, PublicBrand, PublicBrandCategory } from '@/lib/api/types';
import type { ApiError, PricingPreviewResponse } from '@/lib/api/types';
import { getMe } from '@/lib/api/auth';

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

// 学年のソート順を定義（小さい数字が上位）
// 生年月日から学年を計算（4月1日基準）
const calculateGradeFromBirthDate = (birthDate?: string): { grade: string; order: number } => {
  if (!birthDate) return { grade: '未設定', order: 999 };

  const birth = new Date(birthDate);
  const today = new Date();

  // 学年の基準日（4月1日）
  const currentYear = today.getFullYear();
  const fiscalYearStart = new Date(currentYear, 3, 1); // 4月1日

  // 今日が4月1日より前なら前年度
  const fiscalYear = today < fiscalYearStart ? currentYear - 1 : currentYear;

  // 年齢計算（学年基準日時点）
  const fiscalYearBasis = new Date(fiscalYear, 3, 1);
  let age = fiscalYear - birth.getFullYear();
  // 4月1日時点でまだ誕生日が来ていない場合は1歳引く
  const birthThisYear = new Date(fiscalYear, birth.getMonth(), birth.getDate());
  if (birthThisYear > fiscalYearBasis) {
    age--;
  }

  // 年齢から学年を決定
  if (age < 0) return { grade: '0歳', order: -1 };
  if (age === 0) return { grade: '0歳', order: 0 };
  if (age === 1) return { grade: '1歳', order: 1 };
  if (age === 2) return { grade: '2歳', order: 2 };
  if (age === 3) return { grade: '年少', order: 3 };
  if (age === 4) return { grade: '年中', order: 4 };
  if (age === 5) return { grade: '年長', order: 5 };
  if (age === 6) return { grade: '小1', order: 10 };
  if (age === 7) return { grade: '小2', order: 11 };
  if (age === 8) return { grade: '小3', order: 12 };
  if (age === 9) return { grade: '小4', order: 13 };
  if (age === 10) return { grade: '小5', order: 14 };
  if (age === 11) return { grade: '小6', order: 15 };
  if (age === 12) return { grade: '中1', order: 20 };
  if (age === 13) return { grade: '中2', order: 21 };
  if (age === 14) return { grade: '中3', order: 22 };
  if (age === 15) return { grade: '高1', order: 30 };
  if (age === 16) return { grade: '高2', order: 31 };
  if (age === 17) return { grade: '高3', order: 32 };
  if (age >= 18) return { grade: '大学生以上', order: 40 };

  return { grade: '不明', order: 999 };
};

// 子どもを学年（生年月日ベース）でソート（年少から順に）
const sortChildrenByGrade = (children: Child[]): Child[] => {
  return [...children].sort((a, b) => {
    const gradeA = calculateGradeFromBirthDate(a.birthDate);
    const gradeB = calculateGradeFromBirthDate(b.birthDate);
    return gradeA.order - gradeB.order;
  });
};

// 表示用の学年を取得
const getDisplayGrade = (child: Child): string => {
  if (child.grade) return child.grade;
  return calculateGradeFromBirthDate(child.birthDate).grade;
};

// コースの学年名からソート順を取得
const gradeNameOrder: Record<string, number> = {
  '年少': 3, '年中': 4, '年長': 5,
  '小1': 10, '小2': 11, '小3': 12, '小4': 13, '小5': 14, '小6': 15,
  '小学1年': 10, '小学2年': 11, '小学3年': 12, '小学4年': 13, '小学5年': 14, '小学6年': 15,
  '中1': 20, '中2': 21, '中3': 22,
  '中学1年': 20, '中学2年': 21, '中学3年': 22,
  '高1': 30, '高2': 31, '高3': 32,
  '高校1年': 30, '高校2年': 31, '高校3年': 32,
};

const getGradeOrder = (gradeName?: string): number => {
  if (!gradeName) return 999;
  // 「小3~高1」のような範囲表記の場合、最初の学年でソート
  const match = gradeName.match(/^(年少|年中|年長|小[1-6]|小学[1-6]年|中[1-3]|中学[1-3]年|高[1-3]|高校[1-3]年)/);
  if (match) {
    return gradeNameOrder[match[1]] ?? 999;
  }
  return gradeNameOrder[gradeName] ?? 999;
};

export default function FromTicketPurchasePage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [selectedChild, setSelectedChild] = useState<Child | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<PublicBrandCategory | null>(null);
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

  // ブランド（APIから取得）
  const [brands, setBrands] = useState<PublicBrand[]>([]);
  const [isLoadingBrands, setIsLoadingBrands] = useState(true);
  const [brandsError, setBrandsError] = useState<string | null>(null);

  // 校舎（ブランド開講校舎）
  const [schools, setSchools] = useState<BrandSchool[]>([]);
  const [isLoadingSchools, setIsLoadingSchools] = useState(false);
  const [schoolsError, setSchoolsError] = useState<string | null>(null);

  // ユーザーの近隣校舎ID
  const [nearestSchoolId, setNearestSchoolId] = useState<string | null>(null);

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

  // マイル使用
  const [milesToUse, setMilesToUse] = useState<number>(0);
  const [useMiles, setUseMiles] = useState<boolean>(false);

  // 締日情報（請求月判定）
  const [billingInfo, setBillingInfo] = useState<EnrollmentBillingInfo | null>(null);

  // クラス予約関連 state（購入前のクラス選択用）
  const [availableClasses, setAvailableClasses] = useState<StaffLessonSchedule[]>([]);
  const [isLoadingClasses, setIsLoadingClasses] = useState(false);
  const [classesError, setClassesError] = useState<string | null>(null);
  const [selectedClass, setSelectedClass] = useState<StaffLessonSchedule | null>(null);

  // コースの場合の購入前クラス選択フラグ
  const [preSelectClassMode, setPreSelectClassMode] = useState(false);

  // 開講時間割（曜日×時間帯表示用）
  const [classScheduleData, setClassScheduleData] = useState<ClassScheduleResponse | null>(null);
  const [isLoadingSchedules, setIsLoadingSchedules] = useState(false);
  const [schedulesError, setSchedulesError] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [selectedDayOfWeek, setSelectedDayOfWeek] = useState<string | null>(null);
  const [selectedScheduleItem, setSelectedScheduleItem] = useState<ClassScheduleItem | null>(null);

  // チケット開講校舎（フィルタ用）
  const [ticketSchools, setTicketSchools] = useState<BrandSchool[]>([]);
  const [isLoadingTicketSchools, setIsLoadingTicketSchools] = useState(false);

  // 校舎で開講しているチケットID一覧
  const [schoolTicketIds, setSchoolTicketIds] = useState<string[]>([]);

  // 校舎ID→ブランドIDのマップ（カテゴリ内の複数ブランドの校舎を追跡）
  const [schoolBrandMap, setSchoolBrandMap] = useState<Map<string, string>>(new Map());

  // パックのチケットごとのクラス選択用（曜日情報も含む）
  type TicketSelection = {
    schedule: ClassScheduleItem;
    dayOfWeek: string;
    time: string;
  };
  const [currentTicketIndex, setCurrentTicketIndex] = useState(0);
  const [selectedClassesPerTicket, setSelectedClassesPerTicket] = useState<Map<string, TicketSelection>>(new Map());

  // パック内アイテム（tickets と courses を統一）
  type PackItem = {
    id: string;         // アイテムの一意識別子
    name: string;       // 表示名
    ticketCode: string; // チケットコード（スケジュール取得用）
    perWeek: number;    // 週回数
  };

  // パックからアイテム一覧を取得するヘルパー
  const getPackItems = (pack: PublicPack): PackItem[] => {
    const items: PackItem[] = [];
    // ticketsを追加
    if (pack.tickets && pack.tickets.length > 0) {
      for (const t of pack.tickets) {
        items.push({
          id: t.ticketId,
          name: t.ticketName,
          ticketCode: t.ticketCode,
          perWeek: t.perWeek || 1,
        });
      }
    }
    // coursesを追加（ticketsが空の場合はcoursesを使用）
    if (pack.courses && pack.courses.length > 0) {
      for (const c of pack.courses) {
        // coursesにはticketCode/ticketIdが含まれる（API拡張済み）
        if (c.ticketCode) {
          items.push({
            id: c.courseId,
            name: c.courseName,
            ticketCode: c.ticketCode,
            perWeek: 1, // コースは基本週1回
          });
        }
      }
    }
    return items;
  };

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

  // カテゴリ選択時に校舎を取得（カテゴリ内の全ブランドの校舎を取得）
  useEffect(() => {
    if (!selectedCategory) return;

    const fetchSchools = async () => {
      setIsLoadingSchools(true);
      setSchoolsError(null);
      try {
        // カテゴリ内のブランドを取得
        const categoryBrands = brands.filter(b => b.category?.id === selectedCategory.id);

        if (categoryBrands.length === 0) {
          setSchools([]);
          return;
        }

        // カテゴリ内の全ブランドの校舎を取得して結合
        const allSchoolsPromises = categoryBrands.map(brand => getBrandSchools(brand.id));
        const allSchoolsArrays = await Promise.all(allSchoolsPromises);

        // 校舎を結合し、IDで重複を除去 + 校舎ID→ブランドIDマップを作成
        const schoolMap = new Map<string, BrandSchool>();
        const newSchoolBrandMap = new Map<string, string>();

        categoryBrands.forEach((brand, index) => {
          const schoolsForBrand = allSchoolsArrays[index] || [];
          schoolsForBrand.forEach(school => {
            if (!schoolMap.has(school.id)) {
              schoolMap.set(school.id, school);
              newSchoolBrandMap.set(school.id, brand.id);
            }
          });
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
        setSchoolBrandMap(newSchoolBrandMap);
      } catch (err) {
        const apiError = err as ApiError;
        setSchoolsError(apiError.message || '校舎情報の取得に失敗しました');
      } finally {
        setIsLoadingSchools(false);
      }
    };
    fetchSchools();
  }, [selectedCategory, brands]);

  // ブランド選択時にコース・パックを取得（校舎選択前にコース一覧を表示）
  useEffect(() => {
    if (!selectedBrand) return;

    const fetchCoursesAndPacks = async () => {
      setIsLoadingCourses(true);
      setCoursesError(null);
      try {
        // 校舎IDなしでブランドのコース・パックを取得
        const [coursesData, packsData] = await Promise.all([
          getPublicCourses({ brandId: selectedBrand.id }),
          getPublicPacks({ brandId: selectedBrand.id }),
        ]);

        // パックに含まれるコースIDを収集
        const courseIdsInPacks = new Set<string>();
        packsData.forEach((pack) => {
          if (pack.courses) {
            pack.courses.forEach((pc) => {
              courseIdsInPacks.add(pc.courseId);
            });
          }
        });

        // パックに含まれるコースを除外
        const filteredCourses = coursesData.filter(
          (course) => !courseIdsInPacks.has(course.id)
        );

        setCourses(filteredCourses);
        setPacks(packsData);
      } catch (err) {
        const apiError = err as ApiError;
        setCoursesError(apiError.message || 'コース情報の取得に失敗しました');
      } finally {
        setIsLoadingCourses(false);
      }
    };
    fetchCoursesAndPacks();
  }, [selectedBrand]);

  // コース選択時に料金プレビューを取得してStep 6へ（校舎は既に選択済み）
  const handleCourseSelect = async (course: PublicCourse | PublicPack) => {
    setSelectedCourse(course);
    setPricingError(null);
    setIsLoadingPricing(true);

    try {
      // 料金プレビュー取得
      const preview = await previewPricing({
        studentId: selectedChild?.id || '',
        productIds: [course.id],
        courseId: course.id,
      });
      setPricingPreview(preview);
    } catch (err) {
      const apiError = err as ApiError;
      setPricingError(apiError.message || '料金計算に失敗しました');
      setPricingPreview(null);
    } finally {
      setIsLoadingPricing(false);
    }

    setStep(6); // 開始日選択へ（校舎は既にStep 3で選択済み）
  };

  // 購入確定（クラス予約も含めて処理）
  const handleConfirmPurchase = async () => {
    if (!selectedChild || !selectedCourse) return;

    setIsConfirming(true);
    setConfirmError(null);

    try {
      // スケジュール情報を構築（曜日・時間帯をStudentItemに保存するため）
      const schedules: { id: string; dayOfWeek: string; startTime: string; endTime: string; className?: string }[] = [];

      // パックの場合: 各チケットの選択クラス情報を追加
      if (courseType === 'pack' && selectedClassesPerTicket.size > 0) {
        selectedClassesPerTicket.forEach((selection, ticketId) => {
          schedules.push({
            id: selection.schedule.id,
            dayOfWeek: selection.dayOfWeek + '曜日',  // "火" -> "火曜日" に変換
            startTime: selection.time,
            endTime: selection.schedule.endTime || '',
            className: selection.schedule.className,
          });
        });
      }
      // 単体コースの場合: 選択したスケジュール情報を追加
      else if (selectedScheduleItem && selectedDayOfWeek && selectedTime) {
        schedules.push({
          id: selectedScheduleItem.id,
          dayOfWeek: selectedDayOfWeek + '曜日',  // "火" -> "火曜日" に変換
          startTime: selectedTime,
          endTime: selectedScheduleItem.endTime || '',
          className: selectedScheduleItem.className,
        });
      }

      const result = await confirmPricing({
        previewId: pricingPreview?.items?.[0]?.productId || selectedCourse.id,
        paymentMethod: 'credit_card',
        studentId: selectedChild.id,
        courseId: selectedCourse.id,
        // 購入時に選択した情報を送信
        brandId: selectedBrand?.id,
        schoolId: selectedSchoolId || undefined,
        startDate: startDate ? format(startDate, 'yyyy-MM-dd') : undefined,
        // スケジュール情報（曜日・時間帯）を送信
        schedules: schedules.length > 0 ? schedules : undefined,
        // マイル使用
        milesToUse: useMiles && milesToUse > 0 ? milesToUse : undefined,
      });

      if (result.status === 'completed' || result.status === 'pending') {
        // 選択したクラスがある場合は予約も行う
        let bookedClassInfo = null;
        if (selectedClass) {
          try {
            await api.post('/lessons/attendances/', {
              schedule: selectedClass.id,
              student: selectedChild.id,
              status: 'scheduled',
            });
            bookedClassInfo = {
              id: selectedClass.id,
              date: selectedClass.scheduledDate,
              time: `${selectedClass.startTime}-${selectedClass.endTime}`,
              schoolName: selectedClass.school.name,
            };
          } catch (bookErr) {
            // クラス予約に失敗しても購入は成功しているので続行
            console.error('クラス予約に失敗しました:', bookErr);
          }
        }

        // 完了ページへ遷移
        const courseName = 'courseName' in selectedCourse ? selectedCourse.courseName : (selectedCourse as PublicPack).packName;
        sessionStorage.setItem('purchaseResult', JSON.stringify({
          orderId: result.orderId,
          childName: selectedChild.fullName,
          childId: selectedChild.id,
          courseName: courseName,
          courseId: selectedCourse.id,
          brandId: selectedBrand?.id,
          schoolId: selectedSchoolId,
          amount: pricingPreview?.grandTotal || selectedCourse.price,
          startDate: startDate ? format(startDate, 'yyyy-MM-dd') : null,
          bookedClass: bookedClassInfo,
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

  // 利用可能なクラス一覧を取得（レガシー: LessonSchedule）
  const fetchAvailableClasses = async (forDate?: Date) => {
    if (!selectedSchoolId || !selectedCourse) return;

    setIsLoadingClasses(true);
    setClassesError(null);

    try {
      // 指定日または契約開始日から2週間分のクラスを取得
      const baseDate = forDate || startDate || new Date();
      const fromDate = format(baseDate, 'yyyy-MM-dd');
      const toDate = format(addDays(baseDate, 14), 'yyyy-MM-dd');

      const response = await getStaffLessonSchedules({
        schoolId: selectedSchoolId,
        courseId: selectedCourse.id,
        startDate: fromDate,
        endDate: toDate,
        pageSize: 50,
      });

      // レスポンスが null/undefined の場合や results がない場合を安全にハンドリング
      const results = response?.results || [];

      // 空きがあるクラスのみフィルタリング
      const availableOnes = results.filter(
        cls => !cls.capacity || cls.currentEnrollment < cls.capacity
      );
      setAvailableClasses(availableOnes);
    } catch (err) {
      const apiError = err as ApiError;
      setClassesError(apiError.message || 'クラス情報の取得に失敗しました');
      setAvailableClasses([]);
    } finally {
      setIsLoadingClasses(false);
    }
  };

  // 開講時間割を取得（曜日×時間帯表示用）
  // overrideTicketCode: パック内のチケット選択時に特定のチケットコードを指定
  const fetchClassSchedules = async (overrideTicketCode?: string) => {
    if (!selectedSchoolId) return;

    setIsLoadingSchedules(true);
    setSchedulesError(null);

    try {
      // overrideTicketCodeが指定されていればそれを使用
      // そうでなければコースに紐付いたチケットコードを使用
      const ticketCode = overrideTicketCode || (
        selectedCourse && 'ticketCode' in selectedCourse
          ? (selectedCourse as PublicCourse).ticketCode
          : undefined
      );

      // "T10000063" → "Ti10000063" に変換
      const ticketIdForApi = ticketCode
        ? `Ti${ticketCode.replace(/^T/, '')}`
        : undefined;

      const data = await getClassSchedules(
        selectedSchoolId,
        selectedBrand?.id,
        undefined,
        ticketIdForApi
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

  const handleChildSelect = (child: Child) => {
    setSelectedChild(child);
    setStep(2);
  };

  const handleBrandSelect = (brand: PublicBrand) => {
    setSelectedBrand(brand);
    setSelectedSchoolId(null);
    setStep(4);
  };

  const handleSchoolSelect = async (schoolId: string) => {
    setSelectedSchoolId(schoolId);

    // 選択した校舎に対応するブランドをセット
    const brandIdForSchool = schoolBrandMap.get(schoolId);
    if (brandIdForSchool) {
      const brand = brands.find(b => b.id === brandIdForSchool);
      if (brand) {
        setSelectedBrand(brand);
      }
    }

    // 校舎で開講しているチケットを取得
    try {
      const ticketData = await getTicketsBySchool(schoolId);
      setSchoolTicketIds(ticketData.ticketIds);
    } catch (err) {
      console.error('チケット取得エラー:', err);
      setSchoolTicketIds([]);
    }
    // 校舎選択後は確認表示し、「次へ」ボタンで遷移
  };

  // 校舎確認後に次のステップへ進む
  const handleConfirmSchool = () => {
    setStep(4); // コースタイプ選択へ
  };

  const handleCourseTypeSelect = (type: 'single' | 'pack') => {
    setCourseType(type);
    setStep(5); // コース選択へ
  };

  const handleBackToStep = (targetStep: number) => {
    setStep(targetStep);
  };

  const selectedSchool = schools.find((s) => s.id === selectedSchoolId);

  // 選択された子どもの学年に合ったコースをフィルタリング
  const filterByGrade = (items: (PublicCourse | PublicPack)[]): (PublicCourse | PublicPack)[] => {
    if (!selectedChild) return items;

    // 子どもの学年を取得（DBの値または生年月日から計算）
    const childGradeInfo = calculateGradeFromBirthDate(selectedChild.birthDate);
    const childGradeOrder = childGradeInfo.order;

    return items.filter(item => {
      // gradeNameがない場合は全学年対象とみなす
      if (!item.gradeName) return true;

      // 「年少~年長」「小3~高1」「年長～小4」のような範囲表記をパース
      // 全角チルダ（～）と半角チルダ（~）両方に対応
      const rangeMatch = item.gradeName.match(/^(.+?)[~～](.+)$/);
      if (rangeMatch) {
        const fromGrade = rangeMatch[1].trim();
        const toGrade = rangeMatch[2].trim();
        const fromOrder = getGradeOrder(fromGrade);
        const toOrder = getGradeOrder(toGrade);
        // 子どもの学年が範囲内かチェック
        return childGradeOrder >= fromOrder && childGradeOrder <= toOrder;
      }

      // 単一学年の場合
      const courseGradeOrder = getGradeOrder(item.gradeName);
      return childGradeOrder === courseGradeOrder;
    });
  };

  // ブランドのソート順を定義
  const brandSortOrder: Record<string, number> = {
    'AEC': 1,  // 英語
    'SOR': 2,  // そろばん
    'BMC': 3,  // 書写
    'PRO': 4,  // プログラミング
    'SHO': 5,  // 習い事
    'KID': 6,  // キッズ
    'INT': 7,  // インターナショナル
  };

  const getBrandOrder = (brandCode?: string): number => {
    if (!brandCode) return 999;
    return brandSortOrder[brandCode] ?? 999;
  };

  // チケットコードからソート順を取得（数値部分でソート）
  const getTicketOrder = (ticketCode?: string): number => {
    if (!ticketCode) return 999999;
    // T10000063 → 10000063 として数値でソート
    const numPart = ticketCode.replace(/^T/, '');
    return parseInt(numPart, 10) || 999999;
  };

  // コースを校舎→ブランド→学年→チケット順にソート
  const sortByMultipleCriteria = (items: (PublicCourse | PublicPack)[]): (PublicCourse | PublicPack)[] => {
    return [...items].sort((a, b) => {
      // 1. 校舎名でソート（校舎名があれば）
      const schoolNameA = a.schoolName || '';
      const schoolNameB = b.schoolName || '';
      if (schoolNameA !== schoolNameB) {
        return schoolNameA.localeCompare(schoolNameB, 'ja');
      }

      // 2. ブランドコードでソート
      const brandCodeA = a.brandCode || '';
      const brandCodeB = b.brandCode || '';
      const brandOrderA = getBrandOrder(brandCodeA);
      const brandOrderB = getBrandOrder(brandCodeB);
      if (brandOrderA !== brandOrderB) {
        return brandOrderA - brandOrderB;
      }

      // 3. 学年でソート
      const gradeA = getGradeOrder(a.gradeName);
      const gradeB = getGradeOrder(b.gradeName);
      if (gradeA !== gradeB) {
        return gradeA - gradeB;
      }

      // 4. チケットコードでソート（コースの場合）
      const ticketCodeA = 'ticketCode' in a ? (a as PublicCourse).ticketCode : undefined;
      const ticketCodeB = 'ticketCode' in b ? (b as PublicCourse).ticketCode : undefined;
      const ticketOrderA = getTicketOrder(ticketCodeA);
      const ticketOrderB = getTicketOrder(ticketCodeB);
      if (ticketOrderA !== ticketOrderB) {
        return ticketOrderA - ticketOrderB;
      }

      // 5. コース名/パック名でソート
      const nameA = 'courseName' in a ? a.courseName : (a as PublicPack).packName;
      const nameB = 'courseName' in b ? b.courseName : (b as PublicPack).packName;
      return nameA.localeCompare(nameB, 'ja');
    });
  };

  // ticketCodeをClassScheduleのticket_id形式(Ti...)に変換するヘルパー
  const convertToTicketIdFormat = (ticketCode: string): string => {
    // Ch10000063 → Ti10000063
    // T10000063 → Ti10000063
    // Ti10000063 → Ti10000063
    if (ticketCode.startsWith('Ch')) {
      return `Ti${ticketCode.slice(2)}`;
    }
    if (ticketCode.startsWith('Ti')) {
      return ticketCode;
    }
    if (ticketCode.startsWith('T')) {
      return `Ti${ticketCode.slice(1)}`;
    }
    // その他のフォーマットの場合はそのまま返す
    return ticketCode;
  };

  // 校舎で開講しているチケットでコースをフィルタ
  const filterBySchoolTickets = (items: (PublicCourse | PublicPack)[]): (PublicCourse | PublicPack)[] => {
    // 校舎チケットIDがない場合はフィルタしない
    if (schoolTicketIds.length === 0) return items;

    // ticketCodeを正規化する関数（T10000063形式に統一）
    const normalizeTicketCode = (code: string): string => {
      // Ti10000063 → T10000063
      if (code.startsWith('Ti')) {
        return `T${code.slice(2)}`;
      }
      // Ch10000063 → T10000063
      if (code.startsWith('Ch')) {
        return `T${code.slice(2)}`;
      }
      return code;
    };

    // schoolTicketIdsを正規化
    const normalizedSchoolTicketIds = schoolTicketIds.map(normalizeTicketCode);

    return items.filter(item => {
      // PublicCourseの場合、ticketCodeをチェック
      if ('ticketCode' in item && item.ticketCode) {
        const normalizedCode = normalizeTicketCode(item.ticketCode);
        return normalizedSchoolTicketIds.includes(normalizedCode);
      }
      // パックの場合：全てのコース/チケットが校舎で開講している必要がある
      if ('tickets' in item || 'courses' in item) {
        const packItems = getPackItems(item as PublicPack);
        // パックにアイテムがない場合は表示しない
        if (packItems.length === 0) return false;
        // 全てのアイテムのチケットが校舎で開講しているか確認
        return packItems.every(packItem => {
          if (packItem.ticketCode) {
            const normalizedCode = normalizeTicketCode(packItem.ticketCode);
            return normalizedSchoolTicketIds.includes(normalizedCode);
          }
          // ticketCodeがない場合は開講していないとみなす
          return false;
        });
      }
      // ticketCodeがないコースは表示しない
      return false;
    });
  };

  // コースタイプに応じてコースをフィルタリング + 学年でフィルタ + 校舎チケットでフィルタ
  const availableItems: (PublicCourse | PublicPack)[] = (() => {
    let items: (PublicCourse | PublicPack)[] = [];
    if (courseType === 'single') {
      items = courses;
    } else if (courseType === 'pack') {
      items = [...courses, ...packs];
    }
    const afterGradeFilter = filterByGrade(items);
    const afterTicketFilter = filterBySchoolTickets(afterGradeFilter);
    // 学年でフィルタリング → 校舎チケットでフィルタリング → 複数条件でソート
    // ソート順: 校舎 → ブランド → 学年 → チケット
    return sortByMultipleCriteria(afterTicketFilter);
  })();

  // 料金計算（API レスポンスがあればそれを使用）
  // grandTotalには入会金、設備費、教材費、割引が全て含まれている
  const isPack = selectedCourse && 'tickets' in selectedCourse;
  // マイル割引を計算
  const mileDiscountAmount = useMiles && milesToUse >= 4 && pricingPreview?.mileInfo?.canUse
    ? Math.floor((milesToUse - 2) / 2) * 500  // 4pt以上で500円引、以後2ptごとに500円引
    : 0;
  // 合計金額: APIのgrandTotalを使用（入会金、設備費、教材費、割引を全て含む）
  // マイル割引はフロントエンドで計算して引く
  const totalAmount = pricingPreview?.grandTotal
    ? pricingPreview.grandTotal - mileDiscountAmount  // APIで全て計算済み（マイル割引を引く）
    : (selectedCourse?.price || 0) - mileDiscountAmount;  // フォールバック: コース価格のみ

  // コース名を取得するヘルパー関数
  const getCourseName = (course: PublicCourse | PublicPack): string => {
    if ('courseName' in course) return course.courseName;
    return (course as PublicPack).packName;
  };

  const getCourseDescription = (course: PublicCourse | PublicPack): string => {
    return course.description || '';
  };

  const isMonthlyItem = (item: PublicCourse | PublicPack): boolean => {
    if ('isMonthly' in item) return item.isMonthly;
    return true; // パックは常に月額的な扱い
  };

  // 月額授業料のみを取得（tuitionタイプの商品価格）
  const getTuitionPrice = (item: PublicCourse | PublicPack): number => {
    if ('items' in item && item.items) {
      const tuitionItem = item.items.find(
        (i: { productType?: string }) => i.productType === 'tuition'
      );
      if (tuitionItem && 'price' in tuitionItem) {
        return (tuitionItem as { price: number }).price || 0;
      }
    }
    return 0;
  };

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="flex-shrink-0 bg-white shadow-sm z-40">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/ticket-purchase" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">チケット購入</h1>
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
                className={`h-2 flex-1 rounded-full transition-colors ${
                  s <= step ? 'bg-blue-500' : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
          <p className="text-center text-sm text-gray-600 mt-2">
            {step === 7 && preSelectClassMode ? 'クラス選択' :
             step === 8 ? '利用規約' :
             step === 9 ? '購入確認' :
             `Step ${step} / 9`}
          </p>
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
                    <CardContent className="p-4 flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800">{child.fullName}</h3>
                        <p className="text-sm text-gray-600">{getDisplayGrade(child)}</p>
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
            <h2 className="text-lg font-semibold text-gray-800 mb-4">カテゴリを選択</h2>

            {isLoadingBrands ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-3" />
                <p className="text-sm text-gray-600">カテゴリを読み込み中...</p>
              </div>
            ) : brandsError ? (
              <div className="flex items-center gap-2 p-4 rounded-lg bg-red-50 border border-red-200 mb-4">
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                <p className="text-sm text-red-800">{brandsError}</p>
              </div>
            ) : (
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
                  }, [] as PublicBrandCategory[]);

                  // sortOrderでソート
                  const sortedCategories = categories.sort((a, b) => a.sortOrder - b.sortOrder);

                  return sortedCategories.map((category) => (
                    <Card
                      key={category.id}
                      className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                      onClick={() => {
                        setSelectedCategory(category);
                        // カテゴリ内の最初のブランドを選択
                        const categoryBrands = brands.filter(b => b.category?.id === category.id);
                        if (categoryBrands.length > 0) {
                          setSelectedBrand(categoryBrands[0]);
                        }
                        // 校舎選択へ
                        setStep(3);
                      }}
                    >
                      <CardContent className="p-4 flex items-center justify-between">
                        <div className="flex items-center">
                          <div
                            className="w-12 h-12 rounded-full flex items-center justify-center mr-4"
                            style={{ backgroundColor: category.colorPrimary ? `${category.colorPrimary}20` : '#E5E7EB' }}
                          >
                            <GraduationCap
                              className="h-6 w-6"
                              style={{ color: category.colorPrimary || '#6B7280' }}
                            />
                          </div>
                          <span className="text-base font-semibold text-gray-800">{category.categoryName}</span>
                        </div>
                        <ChevronLeft className="h-5 w-5 text-gray-400 rotate-180" />
                      </CardContent>
                    </Card>
                  ));
                })()}
              </div>
            )}
          </div>
        )}

        {/* Step 3: 校舎選択 */}
        {step === 3 && (
          <div className="flex flex-col h-full">
            {/* コンパクトな選択状況表示 */}
            <div className="flex items-center gap-2 mb-3 text-sm">
              <span className="text-gray-500">選択中:</span>
              <span className="font-medium text-gray-800">{selectedChild?.fullName}</span>
              <span className="text-gray-400">›</span>
              <span className="text-blue-600">{selectedCategory?.categoryName}</span>
            </div>

            <h2 className="text-lg font-semibold text-gray-800 mb-1">校舎を選択</h2>
            <p className="text-xs text-gray-500 mb-2">
              通いたい校舎を選択してください
            </p>

            {isLoadingSchools ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-3" />
                <p className="text-sm text-gray-600">校舎を読み込み中...</p>
              </div>
            ) : schoolsError ? (
              <div className="flex items-center gap-2 p-4 rounded-lg bg-red-50 border border-red-200 mb-4">
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                <p className="text-sm text-red-800">{schoolsError}</p>
              </div>
            ) : schools.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <AlertCircle className="h-8 w-8 text-gray-400 mb-3" />
                <p className="text-gray-600 text-center">
                  校舎が見つかりません
                </p>
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
                      <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-gray-500">選択した校舎</p>
                          <p className="font-semibold text-gray-800 truncate">{selectedSchool.name}</p>
                          <p className="text-xs text-gray-500 truncate">{selectedSchool.address}</p>
                        </div>
                      </div>
                      <Button
                        onClick={handleConfirmSchool}
                        className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold"
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

        {/* Step 4: コースタイプ選択 */}
        {step === 4 && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName}</p>
                  <p className="text-sm text-gray-700 mt-1">{selectedCategory?.categoryName} → {selectedSchool?.name}</p>
                </CardContent>
              </Card>
            </div>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">コースタイプを選択</h2>
            <div className="space-y-4">
              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-blue-500"
                onClick={() => {
                  setCourseType('single');
                  setStep(5);
                }}
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
                onClick={() => {
                  setCourseType('pack');
                  setStep(5);
                }}
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

        {/* Step 5: コース選択（校舎で開講しているチケットのみ） */}
        {step === 5 && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName}</p>
                  <p className="text-sm text-gray-700 mt-1">{selectedCategory?.categoryName} → {selectedSchool?.name}</p>
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

            {coursesError && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 mb-4">
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                <p className="text-sm text-red-800">{coursesError}</p>
              </div>
            )}

            {isLoadingCourses || isLoadingPricing ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-3" />
                <p className="text-sm text-gray-600">
                  {isLoadingCourses ? 'コースを読み込み中...' : '料金を計算中...'}
                </p>
              </div>
            ) : availableItems.length === 0 ? (
              <p className="text-center text-gray-600 py-8">
                {courseType === 'single'
                  ? '単品コースがありません'
                  : 'パック/月額コースがありません'}
              </p>
            ) : (
              <div className="space-y-3">
                {availableItems.map((item) => {
                  // セット内容から当月分授業料を除外（入会時授業料は別計算のため）
                  const filteredItems = 'items' in item && item.items
                    ? item.items.filter((i: { productName: string }) =>
                        !i.productName.includes('当月分授業料') &&
                        !i.productName.includes('入会時授業料')
                      )
                    : [];
                  // パックの場合はコース一覧を表示
                  const packCourses = 'courses' in item ? item.courses : [];
                  const packTickets = 'tickets' in item ? item.tickets : [];

                  return (
                    <Card
                      key={item.id}
                      className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                      onClick={() => handleCourseSelect(item)}
                    >
                      <CardContent className="p-4">
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-semibold text-gray-800">{getCourseName(item)}</h3>
                            {isMonthlyItem(item) && (
                              <Badge className="bg-green-500 text-white">月額</Badge>
                            )}
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-gray-500">月謝</p>
                            <span className="text-xl font-bold text-blue-600">
                              ¥{('tuitionPrice' in item && item.tuitionPrice ? item.tuitionPrice : getTuitionPrice(item)).toLocaleString()}
                            </span>
                          </div>
                        </div>

                        {/* 対象学年 */}
                        {item.gradeName && (
                          <p className="text-xs text-gray-600 mb-2">
                            <span className="font-medium">対象学年:</span> {item.gradeName}
                          </p>
                        )}


                        {/* パックの場合：含まれるコース */}
                        {packCourses && packCourses.length > 0 && (
                          <div className="mb-2">
                            <p className="text-xs font-medium text-gray-600 mb-1">セット内容:</p>
                            <div className="flex flex-wrap gap-1">
                              {packCourses.map((pc: { courseId: string; courseName: string }) => (
                                <Badge key={pc.courseId} variant="outline" className="text-xs bg-blue-50 text-blue-700">
                                  {pc.courseName}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* パックの場合：チケット情報 */}
                        {packTickets && packTickets.length > 0 && (
                          <div className="mb-2">
                            <p className="text-xs font-medium text-gray-600 mb-1">チケット:</p>
                            <div className="flex flex-wrap gap-1">
                              {packTickets.map((pt: { ticketId: string; ticketName: string; perWeek?: number }) => (
                                <Badge key={pt.ticketId} variant="outline" className="text-xs bg-orange-50 text-orange-700">
                                  {pt.ticketName}{pt.perWeek ? ` ×週${pt.perWeek}回` : ''}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 説明 */}
                        <p className="text-sm text-gray-600">{getCourseDescription(item)}</p>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {step === 6 && (
          <div>
            {/* コンパクトな選択状況表示 */}
            <div className="flex items-center gap-1 mb-3 text-xs text-gray-500 flex-wrap">
              <span className="font-medium text-gray-700">{selectedChild?.fullName}</span>
              <span>›</span>
              <span className="text-blue-600">{selectedSchool?.name}</span>
              <span>›</span>
              <span className="text-blue-600">{selectedCourse && getCourseName(selectedCourse)}</span>
            </div>

            <h2 className="text-lg font-semibold text-gray-800 mb-2">開始日を選択</h2>

            <Card className="rounded-xl shadow-md mb-3">
              <CardContent className="p-2">
                <Calendar
                  mode="single"
                  selected={startDate}
                  onSelect={async (date) => {
                    setStartDate(date);
                    // 開始日が選択されたら料金プレビューを再取得（入会時授業料を含む）
                    if (date && selectedCourse && selectedChild) {
                      setIsLoadingPricing(true);
                      try {
                        const dateStr = format(date, 'yyyy-MM-dd');
                        // 料金プレビューと締日情報を並行取得
                        const [preview, billing] = await Promise.all([
                          previewPricing({
                            studentId: selectedChild.id,
                            productIds: [selectedCourse.id],
                            courseId: selectedCourse.id,
                            startDate: dateStr,
                            dayOfWeek: dayOfWeekToBackendNumber(selectedDayOfWeek),
                          }),
                          getEnrollmentBillingInfo(dateStr).catch(() => null),
                        ]);
                        setPricingPreview(preview);
                        setBillingInfo(billing);
                      } catch (err) {
                        console.error('料金プレビュー取得エラー:', err);
                      } finally {
                        setIsLoadingPricing(false);
                      }
                    }
                  }}
                  disabled={(date) => date < startOfMonth(new Date())}
                  locale={ja}
                  className="rounded-md"
                />
              </CardContent>
            </Card>

            {startDate && (
              <div className="mb-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm text-green-800">
                  <CalendarIcon className="inline h-4 w-4 mr-1" />
                  開始日: {format(startDate, 'yyyy年MM月dd日（E）', { locale: ja })}
                </p>
                {selectedCourse && isMonthlyItem(selectedCourse) && (
                  <p className="text-xs text-green-700 mt-1">
                    ※月額コースは{format(addDays(startDate, 30), 'yyyy年MM月1日', { locale: ja })}から本格的に開始されます
                  </p>
                )}
              </div>
            )}

            {/* 締日情報（請求月判定）表示 */}
            {billingInfo && (
              <div className={`mb-3 p-3 rounded-lg border ${
                billingInfo.is_after_closing
                  ? 'bg-amber-50 border-amber-200'
                  : 'bg-blue-50 border-blue-200'
              }`}>
                <div className="flex items-start gap-2">
                  <AlertCircle className={`h-4 w-4 mt-0.5 flex-shrink-0 ${
                    billingInfo.is_after_closing ? 'text-amber-600' : 'text-blue-600'
                  }`} />
                  <div className="flex-1">
                    <p className={`text-sm font-medium ${
                      billingInfo.is_after_closing ? 'text-amber-800' : 'text-blue-800'
                    }`}>
                      請求月のお知らせ
                    </p>
                    <p className={`text-xs mt-1 ${
                      billingInfo.is_after_closing ? 'text-amber-700' : 'text-blue-700'
                    }`}>
                      {billingInfo.message}
                    </p>
                    {billingInfo.is_after_closing && billingInfo.first_billable_month && (
                      <p className="text-xs mt-1 text-amber-600">
                        ※ 締日（{billingInfo.closing_day}日）を過ぎているため、{billingInfo.first_billable_month.month}月分から請求されます
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 入会時授業料の表示（月途中入会の場合） */}
            {startDate && pricingPreview?.enrollmentTuition && (
              <div className="mb-3 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-orange-800">入会時授業料（{pricingPreview.enrollmentTuition.tickets}回分）</p>
                    <p className="text-xs text-gray-600">月途中入会のため追加</p>
                  </div>
                  <p className="text-lg font-bold text-orange-600">
                    ¥{pricingPreview.enrollmentTuition.total.toLocaleString()}
                  </p>
                </div>
              </div>
            )}

            {/* 料金読み込み中 */}
            {isLoadingPricing && (
              <div className="flex items-center justify-center py-2">
                <Loader2 className="h-4 w-4 animate-spin text-blue-500 mr-2" />
                <span className="text-xs text-gray-600">料金計算中...</span>
              </div>
            )}

            {startDate && !isLoadingPricing && (
              <Button
                onClick={() => {
                  // パックアイテム（tickets または courses）を取得
                  const isPack = selectedCourse && ('tickets' in selectedCourse || 'courses' in selectedCourse);
                  const packItems = isPack ? getPackItems(selectedCourse as PublicPack) : [];
                  const hasPackItems = packItems.length > 0;

                  if (selectedCourse && (isMonthlyItem(selectedCourse) || hasPackItems)) {
                    setPreSelectClassMode(true);
                    setCurrentTicketIndex(0);
                    setSelectedClassesPerTicket(new Map());

                    // パックの場合は最初のアイテムで開講時間割を取得
                    if (hasPackItems) {
                      fetchClassSchedules(packItems[0].ticketCode);
                    } else {
                      fetchClassSchedules();
                    }
                    setStep(7); // クラス選択ステップへ
                  } else {
                    // 単品コースは直接規約確認へ
                    setStep(8);
                  }
                }}
                className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg"
              >
                次へ
              </Button>
            )}
          </div>
        )}

        {/* Step 7: 月額コースの場合のクラス選択（購入前） */}
        {step === 7 && preSelectClassMode && (() => {
          const dayLabels = classScheduleData?.dayLabels || ['月', '火', '水', '木', '金', '土', '日'];

          // パックアイテム（tickets または courses）を取得
          const isPack = selectedCourse && ('tickets' in selectedCourse || 'courses' in selectedCourse);
          const packItems = isPack ? getPackItems(selectedCourse as PublicPack) : [];
          const hasPackItems = packItems.length > 0;
          const currentItem = hasPackItems ? packItems[currentTicketIndex] : null;
          const totalItems = packItems.length;
          const isLastItem = currentTicketIndex >= totalItems - 1;

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

          const handleTimeSlotSelect = (time: string, dayOfWeek: string) => {
            setSelectedTime(time);
            setSelectedDayOfWeek(dayOfWeek);
            // 選択したセルのスケジュールを取得
            const dayLabel = dayOfWeek.replace('曜日', '');
            const timeSlot = classScheduleData?.timeSlots.find(ts => ts.time === time);
            const dayData = timeSlot?.days[dayLabel];
            if (dayData?.schedules && dayData.schedules.length > 0) {
              // パックの場合は現在のアイテムのチケットコードでフィルタ
              // コースの場合はコースのチケットIDでフィルタ
              let expectedTicketId: string | undefined;
              if (currentItem) {
                // パックアイテム: ticketCodeを Ti形式に変換
                expectedTicketId = currentItem.ticketCode
                  ? `Ti${currentItem.ticketCode.replace(/^T/, '')}`
                  : undefined;
              } else if (selectedCourse && 'ticketCode' in selectedCourse && (selectedCourse as PublicCourse).ticketCode) {
                // コースのチケット
                expectedTicketId = `Ti${((selectedCourse as PublicCourse).ticketCode || '').replace(/^T/, '')}`;
              }

              // チケットIDでフィルタリング
              const filteredSchedules = expectedTicketId
                ? dayData.schedules.filter(s => s.ticketId === expectedTicketId)
                : dayData.schedules;

              if (filteredSchedules.length > 0) {
                setSelectedScheduleItem(filteredSchedules[0]);
              } else {
                // フィルタ結果が空の場合は最初のスケジュールを使用（フォールバック）
                setSelectedScheduleItem(dayData.schedules[0]);
              }
            }
          };

          // パックの次のアイテムに進む
          const handleNextItem = () => {
            // 現在のアイテムの選択を保存（曜日と時間も含む）
            if (currentItem && selectedScheduleItem && selectedDayOfWeek && selectedTime) {
              const newMap = new Map(selectedClassesPerTicket);
              newMap.set(currentItem.id, {
                schedule: selectedScheduleItem,
                dayOfWeek: selectedDayOfWeek,
                time: selectedTime,
              });
              setSelectedClassesPerTicket(newMap);
            }

            if (!isLastItem) {
              // 次のアイテムへ
              const nextIndex = currentTicketIndex + 1;
              setCurrentTicketIndex(nextIndex);
              setSelectedTime(null);
              setSelectedDayOfWeek(null);
              setSelectedScheduleItem(null);
              fetchClassSchedules(packItems[nextIndex].ticketCode);
            } else {
              // すべてのアイテムの選択が完了したら規約確認へ
              setStep(8);
            }
          };

          return (
            <div>
              <div className="mb-4">
                <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                  <CardContent className="p-3">
                    <p className="text-xs text-gray-600 mb-1">選択中</p>
                    <p className="font-semibold text-gray-800">{selectedChild?.fullName}</p>
                    <p className="text-sm text-gray-700 mt-1">{selectedCategory?.categoryName} → {selectedSchool?.name}</p>
                    <p className="text-sm text-gray-700">{selectedCourse && getCourseName(selectedCourse)}</p>
                    <p className="text-sm text-gray-700">開始日: {startDate && format(startDate, 'yyyy年MM月dd日', { locale: ja })}</p>
                  </CardContent>
                </Card>
              </div>

              {/* パックの場合はアイテム進捗を表示 */}
              {hasPackItems && (
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-gray-700">
                      コース {currentTicketIndex + 1} / {totalItems}
                    </p>
                    <Badge variant="outline" className="text-xs">
                      {currentItem?.name}
                    </Badge>
                  </div>
                  <div className="flex gap-1">
                    {packItems.map((_, idx) => (
                      <div
                        key={idx}
                        className={`h-2 flex-1 rounded-full ${
                          idx < currentTicketIndex
                            ? 'bg-green-500'
                            : idx === currentTicketIndex
                            ? 'bg-blue-500'
                            : 'bg-gray-200'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              )}

              <h2 className="text-lg font-semibold text-gray-800 mb-2">
                {hasPackItems ? `${currentItem?.name} の曜日・時間帯を選択` : '曜日・時間帯を選択'}
              </h2>
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

              {schedulesError && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 mb-4">
                  <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                  <p className="text-sm text-red-800">{schedulesError}</p>
                </div>
              )}

              {isLoadingSchedules ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-3" />
                  <p className="text-sm text-gray-600">開講時間割を読み込み中...</p>
                </div>
              ) : !classScheduleData || classScheduleData.timeSlots.length === 0 ? (
                <Card className="rounded-xl shadow-md mb-4">
                  <CardContent className="p-6 text-center">
                    <CalendarIcon className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-600 mb-2">この校舎では現在開講枠がありません</p>
                    <p className="text-sm text-gray-500">
                      購入後にカレンダー画面で予約できます
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <Card className="rounded-xl shadow-md overflow-hidden mb-4">
                  <CardContent className="p-0">
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="bg-gradient-to-r from-blue-600 to-blue-700 text-white">
                            <th className="text-xs font-semibold py-3 px-2 text-left sticky left-0 bg-blue-600 z-10">時間</th>
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
                                    className={`text-center py-3 px-2 ${canSelect ? 'cursor-pointer hover:bg-blue-50' : ''
                                      } ${isSelected ? 'bg-blue-100' : ''
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

              {selectedTime && selectedDayOfWeek && (
                <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200 mb-4">
                  <CardContent className="p-3">
                    <p className="text-xs text-gray-600 mb-1">選択したクラス</p>
                    <p className="font-semibold text-gray-800">
                      {selectedDayOfWeek} {selectedTime}～
                    </p>
                    {selectedScheduleItem && (
                      <p className="text-sm text-gray-700 mt-1">
                        {selectedScheduleItem.className}
                      </p>
                    )}
                  </CardContent>
                </Card>
              )}

              <div className="space-y-3">
                <Button
                  onClick={() => {
                    if (hasPackItems) {
                      handleNextItem();
                    } else {
                      setStep(8);
                    }
                  }}
                  disabled={!selectedTime && classScheduleData?.timeSlots.length !== undefined && classScheduleData.timeSlots.length > 0}
                  className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg disabled:opacity-50"
                >
                  {selectedTime
                    ? (hasPackItems && !isLastItem ? '次のコースへ' : '次へ')
                    : (!classScheduleData || classScheduleData.timeSlots.length === 0)
                      ? (hasPackItems && !isLastItem ? '次のコースへ（後で予約）' : '次へ（後で予約）')
                      : '曜日・時間帯を選択してください'}
                </Button>

              </div>
            </div>
          );
        })()}

        {/* Step 8: 利用規約 */}
        {step === 8 && (
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
              onClick={() => setStep(9)}
              disabled={!agreedToTerms}
              className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              同意して次へ
            </Button>
          </div>
        )}

        {/* Step 9: 購入内容の確認 */}
        {step === 9 && (
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
                  <p className="text-sm text-gray-600 mb-1">カテゴリ</p>
                  <p className="font-semibold text-gray-800">
                    {selectedCategory?.categoryName}
                  </p>
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
                  <p className="font-semibold text-gray-800">{selectedCourse && getCourseName(selectedCourse)}</p>
                  <p className="text-sm text-gray-600">{selectedCourse && getCourseDescription(selectedCourse)}</p>
                </div>

                {/* 選択したクラス（曜日・時間帯） */}
                {selectedDayOfWeek && selectedTime && (
                  <div className="border-t pt-4">
                    <p className="text-sm text-gray-600 mb-1">選択クラス</p>
                    <div className="bg-blue-50 rounded-lg p-3">
                      <p className="font-semibold text-gray-800">
                        {selectedDayOfWeek} {selectedTime}～
                      </p>
                      {selectedScheduleItem && (
                        <p className="text-sm text-gray-600 mt-1">
                          {selectedScheduleItem.className}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* 選択したクラス（月額コースの場合） */}
                {selectedClass && (
                  <div className="border-t pt-4">
                    <p className="text-sm text-gray-600 mb-1">初回レッスン</p>
                    <div className="bg-blue-50 rounded-lg p-3">
                      <p className="font-semibold text-gray-800">
                        {format(new Date(selectedClass.scheduledDate), 'M月d日（E）', { locale: ja })}
                      </p>
                      <p className="text-sm text-gray-600">
                        {selectedClass.startTime} - {selectedClass.endTime}
                      </p>
                      <p className="text-xs text-gray-500">{selectedClass.school.name}</p>
                    </div>
                  </div>
                )}


                {/* マイル割引セクション */}
                {pricingPreview?.mileInfo && pricingPreview.mileInfo.balance > 0 && (
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-amber-500" />
                        <span className="text-sm font-medium text-gray-800">マイルポイント</span>
                      </div>
                      <span className="text-sm text-gray-600">
                        残高: <span className="font-semibold text-amber-600">{pricingPreview.mileInfo.balance}pt</span>
                      </span>
                    </div>

                    {pricingPreview.mileInfo.canUse ? (
                      <div className="space-y-3">
                        <div className="flex items-center gap-3">
                          <Checkbox
                            id="use-miles"
                            checked={useMiles}
                            onCheckedChange={(checked) => {
                              setUseMiles(checked === true);
                              if (!checked) setMilesToUse(0);
                              else setMilesToUse(pricingPreview.mileInfo?.balance || 0);
                            }}
                          />
                          <label htmlFor="use-miles" className="text-sm text-gray-700 cursor-pointer">
                            マイルを使用して割引する
                          </label>
                        </div>

                        {useMiles && (
                          <div className="pl-6 space-y-2">
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-gray-600">使用pt:</span>
                              <input
                                type="number"
                                min={4}
                                max={pricingPreview.mileInfo.balance}
                                step={2}
                                value={milesToUse}
                                onChange={(e) => {
                                  const val = parseInt(e.target.value) || 0;
                                  setMilesToUse(Math.min(val, pricingPreview.mileInfo?.balance || 0));
                                }}
                                className="w-20 px-2 py-1 text-sm border rounded text-center"
                              />
                              <span className="text-sm text-gray-500">/ {pricingPreview.mileInfo.balance}pt</span>
                            </div>
                            {milesToUse >= 4 && (
                              <div className="flex justify-between text-sm">
                                <span className="text-green-700">マイル割引（{milesToUse}pt使用）</span>
                                <span className="text-green-700 font-semibold">-¥{mileDiscountAmount.toLocaleString()}</span>
                              </div>
                            )}
                            <p className="text-xs text-gray-500">
                              ※4pt以上から使用可能。4ptで500円引、以後2ptごとに500円引
                            </p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500">
                          {pricingPreview.mileInfo.reason || 'マイルを使用するにはコース契約が2つ以上必要です'}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                <div className="border-t pt-4 space-y-3">
                  {/* 月別料金グループ表示 */}
                  {pricingPreview?.billingByMonth ? (
                    <>
                      {/* 入会時費用 */}
                      {pricingPreview.billingByMonth.enrollment.items.length > 0 && (
                        <div className="bg-blue-50 rounded-lg p-3 space-y-2">
                          <div className="flex justify-between items-center border-b border-blue-200 pb-2 mb-2">
                            <span className="font-semibold text-blue-800">{pricingPreview.billingByMonth.enrollment.label}</span>
                            <span className="font-semibold text-blue-800">¥{pricingPreview.billingByMonth.enrollment.total.toLocaleString()}</span>
                          </div>
                          {pricingPreview.billingByMonth.enrollment.items.map((item, index) => (
                            <div key={index} className="flex justify-between text-sm">
                              <span className="text-gray-700">{item.productName}</span>
                              <span className="text-gray-800">¥{item.priceWithTax.toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* 当月分（回数割） */}
                      {pricingPreview.billingByMonth.currentMonth.items.length > 0 && (
                        <div className="bg-amber-50 rounded-lg p-3 space-y-2">
                          <div className="flex justify-between items-center border-b border-amber-200 pb-2 mb-2">
                            <span className="font-semibold text-amber-800">{pricingPreview.billingByMonth.currentMonth.label}</span>
                            <span className="font-semibold text-amber-800">¥{pricingPreview.billingByMonth.currentMonth.total.toLocaleString()}</span>
                          </div>
                          {pricingPreview.billingByMonth.currentMonth.items.map((item, index) => (
                            <div key={index} className="flex justify-between text-sm">
                              <span className="text-gray-700">{item.productName}</span>
                              <span className="text-gray-800">¥{item.priceWithTax.toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* 翌月分 */}
                      {pricingPreview.billingByMonth.month1.items.length > 0 && (
                        <div className="bg-green-50 rounded-lg p-3 space-y-2">
                          <div className="flex justify-between items-center border-b border-green-200 pb-2 mb-2">
                            <span className="font-semibold text-green-800">{pricingPreview.billingByMonth.month1.label}</span>
                            <span className="font-semibold text-green-800">¥{pricingPreview.billingByMonth.month1.total.toLocaleString()}</span>
                          </div>
                          {pricingPreview.billingByMonth.month1.items.map((item, index) => (
                            <div key={index} className="flex justify-between text-sm">
                              <span className="text-gray-700">{item.productName}</span>
                              <span className="text-gray-800">¥{item.priceWithTax.toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* 翌々月分〜 */}
                      {pricingPreview.billingByMonth.month2.items.length > 0 && (
                        <div className="bg-purple-50 rounded-lg p-3 space-y-2">
                          <div className="flex justify-between items-center border-b border-purple-200 pb-2 mb-2">
                            <span className="font-semibold text-purple-800">{pricingPreview.billingByMonth.month2.label}</span>
                            <span className="font-semibold text-purple-800">¥{pricingPreview.billingByMonth.month2.total.toLocaleString()}</span>
                          </div>
                          {pricingPreview.billingByMonth.month2.items.map((item, index) => (
                            <div key={index} className="flex justify-between text-sm">
                              <span className="text-gray-700">{item.productName}</span>
                              <span className="text-gray-800">¥{item.priceWithTax.toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    /* フォールバック: courseItemsを表示 */
                    <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                      {pricingPreview?.courseItems && pricingPreview.courseItems.map((item, index) => (
                        <div key={index} className="flex justify-between text-sm">
                          <span className="text-gray-700">{item.productName}</span>
                          <span className="text-gray-800">¥{item.priceWithTax.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* 割引 */}
                  {pricingPreview?.discounts && pricingPreview.discounts.length > 0 && (
                    <div className="bg-green-50 rounded-lg p-3 space-y-2">
                      {pricingPreview.discounts.map((discount: { discountName: string; discountAmount: number }, index: number) => (
                        <div key={`discount-${index}`} className="flex justify-between text-sm">
                          <span className="text-green-600">{discount.discountName}</span>
                          <span className="text-green-600">-¥{discount.discountAmount.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* マイル割引表示 */}
                  {milesToUse > 0 && mileDiscountAmount > 0 && (
                    <div className="flex justify-between text-sm bg-amber-50 rounded-lg p-3">
                      <span className="text-amber-600 font-medium">マイル割引（{milesToUse}pt使用）</span>
                      <span className="text-amber-600 font-medium">-¥{mileDiscountAmount.toLocaleString()}</span>
                    </div>
                  )}

                  {/* 合計 */}
                  <div className="flex justify-between items-center pt-2 border-t">
                    <span className="text-lg font-semibold text-gray-800">合計金額</span>
                    <span className="text-2xl font-bold text-blue-600">
                      ¥{totalAmount.toLocaleString()}
                    </span>
                  </div>
                  {pricingPreview && (
                    <p className="text-xs text-gray-500 text-right">
                      （税込）
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
        </div>
      </main>

      <BottomTabBar />
    </div>
  );
}
