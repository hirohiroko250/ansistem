'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { ChevronLeft, Package, Sparkles, Calendar as CalendarIcon, CalendarPlus, Loader2, AlertCircle, BookOpen, Calculator, Pen, Gamepad2, Trophy, Globe, GraduationCap, Clock, Users, CheckCircle2, Circle, Triangle, X as XIcon, Minus, MessageSquare, type LucideIcon } from 'lucide-react';
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
// SeminarSelection と CertificationSelection は同じページ内で処理するため不要
// import { SeminarSelection } from '@/components/ticket-purchase/SeminarSelection';
// import { CertificationSelection } from '@/components/ticket-purchase/CertificationSelection';

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
  const [selectedBrandIds, setSelectedBrandIds] = useState<string[]>([]); // 校舎に紐付く全ブランドID
  const [categoryBrandIds, setCategoryBrandIds] = useState<string[]>([]); // カテゴリ内の全ブランドID
  const [selectedSchoolId, setSelectedSchoolId] = useState<string | null>(null);
  const [itemType, setItemType] = useState<'regular' | 'seminar' | 'certification' | 'event' | null>(null);
  const [courseType, setCourseType] = useState<'single' | 'pack' | null>(null);
  const [frequency, setFrequency] = useState<'weekly' | 'other' | null>(null); // 週１回 or それ以外
  const [selectedCourse, setSelectedCourse] = useState<PublicCourse | PublicPack | null>(null);
  const [startDate, setStartDate] = useState<Date>(new Date());
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false);
  const termsRef = useRef<HTMLDivElement>(null);

  // 利用規約のスクロールハンドラー
  const handleTermsScroll = useCallback(() => {
    if (!termsRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = termsRef.current;
    // 下から10px以内にスクロールしたら「最後まで読んだ」とみなす
    if (scrollTop + clientHeight >= scrollHeight - 10) {
      setHasScrolledToBottom(true);
    }
  }, []);

  // ステップ10（利用規約）に戻った時にスクロール状態をリセット
  useEffect(() => {
    if (step === 10) {
      setHasScrolledToBottom(false);
      setAgreedToTerms(false);
    }
  }, [step]);

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

  // コースデータのキャッシュ（同じリクエストを繰り返さない）
  const courseCacheRef = useRef<Map<string, { courses: PublicCourse[], packs: PublicPack[] }>>(new Map());

  // 講習会
  const [seminars, setSeminars] = useState<Array<{
    id: string;
    seminar_code: string;
    seminar_name: string;
    seminar_type: string;
    brand_name?: string;
    year: number;
    start_date?: string;
    end_date?: string;
    base_price: number;
    description?: string;
    is_active: boolean;
    is_required?: boolean;
    enrollment_price_jan?: number;
    enrollment_price_feb?: number;
    enrollment_price_mar?: number;
    enrollment_price_apr?: number;
    enrollment_price_may?: number;
    enrollment_price_jun?: number;
    enrollment_price_jul?: number;
    enrollment_price_aug?: number;
    enrollment_price_sep?: number;
    enrollment_price_oct?: number;
    enrollment_price_nov?: number;
    enrollment_price_dec?: number;
  }>>([]);
  const [selectedSeminars, setSelectedSeminars] = useState<string[]>([]);
  const [isLoadingSeminars, setIsLoadingSeminars] = useState(false);
  const [seminarsError, setSeminarsError] = useState<string | null>(null);

  // 検定
  const [certifications, setCertifications] = useState<Array<{
    id: string;
    certification_code: string;
    certification_name: string;
    certification_type: string;
    brand_name?: string;
    exam_date?: string;
    application_deadline?: string;
    exam_fee: number;
    description?: string;
    is_active: boolean;
  }>>([]);
  const [selectedCertifications, setSelectedCertifications] = useState<string[]>([]);
  const [isLoadingCertifications, setIsLoadingCertifications] = useState(false);
  const [certificationsError, setCertificationsError] = useState<string | null>(null);

  const [pricingPreview, setPricingPreview] = useState<PricingPreviewResponse | null>(null);
  const [isLoadingPricing, setIsLoadingPricing] = useState(false);
  const [pricingError, setPricingError] = useState<string | null>(null);

  const [isConfirming, setIsConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  // マイル使用
  const [milesToUse, setMilesToUse] = useState<number>(0);
  const [useMiles, setUseMiles] = useState<boolean>(false);

  // 教材費選択（半年払い/月払い）
  const [selectedTextbookIds, setSelectedTextbookIds] = useState<string[]>([]);

  // 教材費オプションが読み込まれたらデフォルトで最初のオプションを選択
  useEffect(() => {
    if (pricingPreview?.textbookOptions && pricingPreview.textbookOptions.length > 0 && selectedTextbookIds.length === 0) {
      // 最初のオプション（通常は年払い）をデフォルト選択
      setSelectedTextbookIds([pricingPreview.textbookOptions[0].productId]);
    }
  }, [pricingPreview?.textbookOptions]);

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
  // 校舎ID → ブランドID配列のマップ（カテゴリ内の複数ブランドが同じ校舎を持つ場合に対応）
  const [schoolBrandMap, setSchoolBrandMap] = useState<Map<string, string[]>>(new Map());

  // パックのチケットごとのクラス選択用（曜日情報も含む）
  type TicketSelection = {
    schedule: ClassScheduleItem;
    dayOfWeek: string;
    time: string;
    schoolId: string;      // 校舎ID
    schoolName: string;    // 校舎名（表示用）
  };
  const [currentTicketIndex, setCurrentTicketIndex] = useState(0);
  const [selectedClassesPerTicket, setSelectedClassesPerTicket] = useState<Map<string, TicketSelection>>(new Map());

  // 単体コースの複数クラス選択用（週あたり回数 > 1 の場合）
  const [currentWeeklyIndex, setCurrentWeeklyIndex] = useState(0);
  const [selectedWeeklySchedules, setSelectedWeeklySchedules] = useState<TicketSelection[]>([]);

  // 複数校舎対応：選択可能な校舎一覧と現在表示中の校舎
  const [selectedSchoolIds, setSelectedSchoolIds] = useState<string[]>([]);  // 選択した校舎ID一覧
  const [currentScheduleSchoolId, setCurrentScheduleSchoolId] = useState<string | null>(null);  // 現在のスケジュール表示校舎
  const [classScheduleDataPerSchool, setClassScheduleDataPerSchool] = useState<Map<string, ClassScheduleResponse>>(new Map());  // 校舎ごとのスケジュール

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
    // coursesを追加（ticketCodeがなくても追加）
    if (pack.courses && pack.courses.length > 0) {
      for (const c of pack.courses) {
        items.push({
          id: c.courseId,
          name: c.courseName,
          ticketCode: c.ticketCode || '', // ticketCodeがない場合は空文字
          perWeek: 1, // コースは基本週1回
        });
      }
    }
    return items;
  };

  // チケット購入状態の保存キー
  const PURCHASE_STATE_KEY = 'ticket-purchase-state';

  // チャットに移動する際に状態を保存
  const saveStateAndGoToChat = () => {
    const stateToSave = {
      step,
      selectedChild,
      selectedCategory,
      selectedBrand,
      selectedBrandIds,
      selectedSchoolId,
      selectedCourse,
      courseType,
      frequency,
      itemType,
      startDate: startDate?.toISOString(),
      selectedDayOfWeek,
      selectedTime,
      selectedScheduleItem,
      selectedTextbookIds,
      selectedSeminars,
      selectedCertifications,
      selectedWeeklySchedules,
      selectedSchoolIds,
      milesToUse,
      pricingPreview,
      timestamp: Date.now(),
    };
    localStorage.setItem(PURCHASE_STATE_KEY, JSON.stringify(stateToSave));

    // チャット画面に遷移（新規チャットで料金についての質問を開始）
    // 選択中のコース名と金額を含めたメッセージを作成
    const courseName = selectedCourse ? getCourseName(selectedCourse) : '';
    const amount = totalAmount.toLocaleString();
    const initialMessage = encodeURIComponent(`【チケット購入画面からの質問】\n${courseName}の料金について質問があります。\n表示金額: ¥${amount}\n\n`);
    router.push(`/chat/new?message=${initialMessage}`);
  };

  // ページロード時に保存された状態を復元
  useEffect(() => {
    const savedState = localStorage.getItem(PURCHASE_STATE_KEY);
    if (savedState) {
      try {
        const parsed = JSON.parse(savedState);
        // 24時間以内の保存データのみ復元
        if (parsed.timestamp && Date.now() - parsed.timestamp < 24 * 60 * 60 * 1000) {
          if (parsed.step) setStep(parsed.step);
          if (parsed.selectedChild) setSelectedChild(parsed.selectedChild);
          if (parsed.selectedCategory) setSelectedCategory(parsed.selectedCategory);
          if (parsed.selectedBrand) setSelectedBrand(parsed.selectedBrand);
          if (parsed.selectedBrandIds) setSelectedBrandIds(parsed.selectedBrandIds);
          if (parsed.selectedSchoolId) setSelectedSchoolId(parsed.selectedSchoolId);
          if (parsed.selectedCourse) setSelectedCourse(parsed.selectedCourse);
          if (parsed.courseType) setCourseType(parsed.courseType);
          if (parsed.frequency) setFrequency(parsed.frequency);
          if (parsed.itemType) setItemType(parsed.itemType);
          if (parsed.startDate) setStartDate(new Date(parsed.startDate));
          if (parsed.selectedDayOfWeek) setSelectedDayOfWeek(parsed.selectedDayOfWeek);
          if (parsed.selectedTime) setSelectedTime(parsed.selectedTime);
          if (parsed.selectedScheduleItem) setSelectedScheduleItem(parsed.selectedScheduleItem);
          if (parsed.selectedTextbookIds) setSelectedTextbookIds(parsed.selectedTextbookIds);
          if (parsed.selectedSeminars) setSelectedSeminars(parsed.selectedSeminars);
          if (parsed.selectedCertifications) setSelectedCertifications(parsed.selectedCertifications);
          if (parsed.selectedWeeklySchedules) setSelectedWeeklySchedules(parsed.selectedWeeklySchedules);
          if (parsed.selectedSchoolIds) setSelectedSchoolIds(parsed.selectedSchoolIds);
          if (parsed.milesToUse !== undefined) setMilesToUse(parsed.milesToUse);
          if (parsed.pricingPreview) setPricingPreview(parsed.pricingPreview);
        }
        // 復元後はクリア（再度復元しないため）
        localStorage.removeItem(PURCHASE_STATE_KEY);
      } catch (e) {
        console.error('Failed to restore purchase state:', e);
        localStorage.removeItem(PURCHASE_STATE_KEY);
      }
    }
  }, []);

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
        const brandIds = categoryBrands.map(b => b.id);
        setCategoryBrandIds(brandIds);

        if (categoryBrands.length === 0) {
          setSchools([]);
          return;
        }

        // カテゴリ内の全ブランドの校舎を取得して結合
        const allSchoolsPromises = categoryBrands.map(brand => getBrandSchools(brand.id));
        const allSchoolsArrays = await Promise.all(allSchoolsPromises);

        // 校舎を結合し、IDで重複を除去 + 校舎ID→ブランドID配列マップを作成
        const schoolMap = new Map<string, BrandSchool>();
        const newSchoolBrandMap = new Map<string, string[]>();

        categoryBrands.forEach((brand, index) => {
          const schoolsForBrand = allSchoolsArrays[index] || [];
          schoolsForBrand.forEach(school => {
            if (!schoolMap.has(school.id)) {
              schoolMap.set(school.id, school);
            }
            // 校舎に対応するブランドID配列に追加
            const existingBrands = newSchoolBrandMap.get(school.id) || [];
            if (!existingBrands.includes(brand.id)) {
              newSchoolBrandMap.set(school.id, [...existingBrands, brand.id]);
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

  // 校舎選択時にコース・パックを取得（校舎フィルタ + カテゴリでクライアント側フィルタ）
  useEffect(() => {
    // カテゴリ内のブランドIDを直接計算
    const brandIdsInCategory = selectedCategory
      ? new Set(brands.filter(b => b.category?.id === selectedCategory.id).map(b => b.id))
      : new Set<string>();

    const brandIdList = Array.from(brandIdsInCategory).sort();
    if (brandIdList.length === 0 || !selectedSchoolId) return;

    // キャッシュキーを生成
    const cacheKey = `${brandIdList.join(',')}_${selectedSchoolId}`;

    // キャッシュがあれば即座に反映
    const cached = courseCacheRef.current.get(cacheKey);
    if (cached) {
      setCourses(cached.courses);
      setPacks(cached.packs);
      setIsLoadingCourses(false);
      return;
    }

    const fetchCoursesAndPacks = async () => {
      setIsLoadingCourses(true);
      setCoursesError(null);
      try {
        // ブランドIDと校舎IDでサーバーサイドフィルタリング
        const [categoryCourses, categoryPacks] = await Promise.all([
          getPublicCourses({ brandIds: brandIdList, schoolId: selectedSchoolId }),
          getPublicPacks({ brandIds: brandIdList, schoolId: selectedSchoolId }),
        ]);

        // キャッシュに保存
        courseCacheRef.current.set(cacheKey, { courses: categoryCourses, packs: categoryPacks });

        // パックに含まれるコースも単品として表示する（¥0除外は後で行う）
        setCourses(categoryCourses);
        setPacks(categoryPacks);
      } catch (err) {
        const apiError = err as ApiError;
        setCoursesError(apiError.message || 'コース情報の取得に失敗しました');
      } finally {
        setIsLoadingCourses(false);
      }
    };
    fetchCoursesAndPacks();
  }, [selectedCategory, brands, selectedSchoolId]);

  // 講習会を取得（itemType === 'seminar' の場合）
  useEffect(() => {
    if (!selectedBrand || itemType !== 'seminar') return;

    const fetchSeminars = async () => {
      setIsLoadingSeminars(true);
      setSeminarsError(null);
      try {
        const params = new URLSearchParams({ is_active: 'true' });
        params.append('brand_id', selectedBrand.id);
        const response = await api.get<{ results?: typeof seminars } | typeof seminars>(`/contracts/seminars/?${params.toString()}`);
        const data = Array.isArray(response) ? response : (response.results || []);

        // 現在の月を取得（1-12）
        const currentMonth = new Date().getMonth() + 1;

        // 月ごとのenrollment_price取得関数
        const getEnrollmentPriceForMonth = (seminar: typeof data[0], month: number): number => {
          const priceFields: Record<number, keyof typeof seminar> = {
            1: 'enrollment_price_jan',
            2: 'enrollment_price_feb',
            3: 'enrollment_price_mar',
            4: 'enrollment_price_apr',
            5: 'enrollment_price_may',
            6: 'enrollment_price_jun',
            7: 'enrollment_price_jul',
            8: 'enrollment_price_aug',
            9: 'enrollment_price_sep',
            10: 'enrollment_price_oct',
            11: 'enrollment_price_nov',
            12: 'enrollment_price_dec',
          };
          const fieldName = priceFields[month];
          const value = seminar[fieldName];
          return typeof value === 'number' ? value : 0;
        };

        // フィルタリング：
        // 1. is_required が true の場合は除外（必須講習は表示しない）
        // 2. 現在月の enrollment_price が 0 より大きい場合のみ表示
        const filteredData = data.filter(seminar => {
          // 必須講習は除外
          if (seminar.is_required === true) return false;

          // 現在月の enrollment_price が 0 より大きいかチェック
          const enrollmentPrice = getEnrollmentPriceForMonth(seminar, currentMonth);
          return enrollmentPrice > 0;
        });

        setSeminars(filteredData);
      } catch (err) {
        setSeminarsError('講習会情報の取得に失敗しました');
      } finally {
        setIsLoadingSeminars(false);
      }
    };
    fetchSeminars();
  }, [selectedBrand, itemType]);

  // 検定を取得（itemType === 'certification' の場合）
  useEffect(() => {
    if (!selectedBrand || itemType !== 'certification') return;

    const fetchCertifications = async () => {
      setIsLoadingCertifications(true);
      setCertificationsError(null);
      try {
        const params = new URLSearchParams({ is_active: 'true' });
        params.append('brand_id', selectedBrand.id);
        const response = await api.get<{ results?: typeof certifications } | typeof certifications>(`/contracts/certifications/?${params.toString()}`);
        const data = Array.isArray(response) ? response : (response.results || []);

        // 購入制限フィルター: 検定週と1週間前は購入不可
        // exam_dateから14日以内（検定週 + 1週間前）は除外
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const filteredData = data.filter(cert => {
          if (!cert.exam_date) return true; // exam_dateが未設定の場合は表示

          const examDate = new Date(cert.exam_date);
          examDate.setHours(0, 0, 0, 0);

          // 検定週の開始日（日曜日）を計算
          const examWeekStart = new Date(examDate);
          const dayOfWeek = examDate.getDay(); // 0=日曜, 6=土曜
          examWeekStart.setDate(examDate.getDate() - dayOfWeek);

          // 1週間前の開始日
          const restrictionStart = new Date(examWeekStart);
          restrictionStart.setDate(examWeekStart.getDate() - 7);

          // 検定週の終了日（土曜日）
          const examWeekEnd = new Date(examWeekStart);
          examWeekEnd.setDate(examWeekStart.getDate() + 6);

          // 今日が制限期間内（1週間前〜検定週末）かチェック
          const isRestricted = today >= restrictionStart && today <= examWeekEnd;

          if (isRestricted) {
          }

          return !isRestricted;
        });

        setCertifications(filteredData);
      } catch (err) {
        setCertificationsError('検定情報の取得に失敗しました');
      } finally {
        setIsLoadingCertifications(false);
      }
    };
    fetchCertifications();
  }, [selectedBrand, itemType]);

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

    setStep(8); // 開始日選択へ
  };

  // 購入確定（クラス予約も含めて処理）
  const handleConfirmPurchase = async () => {
    // 通常コースの場合はコース必須、講習会・検定の場合は選択必須
    if (!selectedChild) return;
    if (itemType === 'regular' && !selectedCourse) return;
    if (itemType === 'seminar' && selectedSeminars.length === 0) return;
    if (itemType === 'certification' && selectedCertifications.length === 0) return;

    setIsConfirming(true);
    setConfirmError(null);

    try {
      // 講習会の購入処理
      if (itemType === 'seminar') {
        for (const seminarId of selectedSeminars) {
          const seminar = seminars.find(s => s.id === seminarId);
          if (!seminar) continue;
          await api.post('/contracts/seminar-enrollments/', {
            student: selectedChild.id,
            seminar: seminarId,
            status: 'applied',
            unit_price: seminar.base_price,
            discount_amount: 0,
            final_price: seminar.base_price,
            billing_month: new Date().toISOString().slice(0, 7),
          });
        }

        const totalPrice = seminars
          .filter(s => selectedSeminars.includes(s.id))
          .reduce((sum, s) => sum + s.base_price, 0);

        sessionStorage.setItem('purchaseResult', JSON.stringify({
          orderId: `SEM-${Date.now()}`,
          childName: selectedChild.fullName,
          childId: selectedChild.id,
          courseName: seminars.filter(s => selectedSeminars.includes(s.id)).map(s => s.seminar_name).join('、'),
          courseId: selectedSeminars[0],
          amount: totalPrice,
          startDate: null,
          type: 'seminar',
        }));
        router.push('/ticket-purchase/complete');
        return;
      }

      // 検定の購入処理
      if (itemType === 'certification') {
        for (const certId of selectedCertifications) {
          const cert = certifications.find(c => c.id === certId);
          if (!cert) continue;
          await api.post('/contracts/certification-enrollments/', {
            student: selectedChild.id,
            certification: certId,
            status: 'applied',
            unit_price: cert.exam_fee,
            discount_amount: 0,
            final_price: cert.exam_fee,
            billing_month: new Date().toISOString().slice(0, 7),
          });
        }

        const totalPrice = certifications
          .filter(c => selectedCertifications.includes(c.id))
          .reduce((sum, c) => sum + c.exam_fee, 0);

        sessionStorage.setItem('purchaseResult', JSON.stringify({
          orderId: `CERT-${Date.now()}`,
          childName: selectedChild.fullName,
          childId: selectedChild.id,
          courseName: certifications.filter(c => selectedCertifications.includes(c.id)).map(c => c.certification_name).join('、'),
          courseId: selectedCertifications[0],
          amount: totalPrice,
          startDate: null,
          type: 'certification',
        }));
        router.push('/ticket-purchase/complete');
        return;
      }

      // 通常コースの購入処理（既存の実装）
      if (!selectedCourse) return;
      // デバッグ: 送信前のデータを確認

      // スケジュール情報を構築（曜日・時間帯をStudentItemに保存するため）- 複数校舎対応
      const schedules: { id: string; dayOfWeek: string; startTime: string; endTime: string; className?: string; schoolId?: string }[] = [];

      // パックの場合: 各チケットの選択クラス情報を追加
      if (courseType === 'pack' && selectedClassesPerTicket.size > 0) {
        selectedClassesPerTicket.forEach((selection) => {
          schedules.push({
            id: selection.schedule.id,
            dayOfWeek: selection.dayOfWeek,  // 既に "火曜日" 形式で保存されている
            startTime: selection.time,
            endTime: selection.schedule.endTime || '',
            className: selection.schedule.className,
            schoolId: selection.schoolId,  // 複数校舎対応
          });
        });
      }
      // 単体コースで複数週次選択がある場合: selectedWeeklySchedulesから追加
      else if (selectedWeeklySchedules.length > 0) {
        for (const selection of selectedWeeklySchedules) {
          schedules.push({
            id: selection.schedule.id,
            dayOfWeek: selection.dayOfWeek,  // 既に "火曜日" 形式で保存されている
            startTime: selection.time,
            endTime: selection.schedule.endTime || '',
            className: selection.schedule.className,
            schoolId: selection.schoolId,  // 複数校舎対応
          });
        }
      }
      // 単体コースで週1回の場合: 選択したスケジュール情報を追加
      else if (selectedScheduleItem && selectedDayOfWeek && selectedTime) {
        schedules.push({
          id: selectedScheduleItem.id,
          dayOfWeek: selectedDayOfWeek + '曜日',  // "火" -> "火曜日" に変換
          startTime: selectedTime,
          endTime: selectedScheduleItem.endTime || '',
          className: selectedScheduleItem.className,
          schoolId: currentScheduleSchoolId || selectedSchoolId || undefined,  // 複数校舎対応
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
        // 教材費選択
        selectedTextbookIds: selectedTextbookIds.length > 0 ? selectedTextbookIds : undefined,
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
  // 校舎ごとの開講時間割を取得（複数校舎対応）
  const fetchClassSchedules = async (overrideTicketCode?: string, overrideSchoolId?: string) => {
    const targetSchoolId = overrideSchoolId || currentScheduleSchoolId || selectedSchoolId;
    if (!targetSchoolId) return;

    // キャッシュをチェック（同じ校舎のスケジュールが既にある場合）
    const cacheKey = `${targetSchoolId}_${overrideTicketCode || ''}`;
    const existingData = classScheduleDataPerSchool.get(cacheKey);
    if (existingData && !overrideSchoolId) {
      // キャッシュがあればそれを使用（表示用stateを更新）
      setClassScheduleData(existingData);
      return;
    }

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
        targetSchoolId,
        selectedBrand?.id,
        undefined,
        ticketIdForApi
      );
      setClassScheduleData(data);

      // キャッシュに保存
      setClassScheduleDataPerSchool(prev => {
        const newMap = new Map(prev);
        newMap.set(cacheKey, data);
        return newMap;
      });
    } catch (err) {
      const apiError = err as ApiError;
      setSchedulesError(apiError.message || '開講時間割の取得に失敗しました');
      setClassScheduleData(null);
    } finally {
      setIsLoadingSchedules(false);
    }
  };

  // 校舎切り替え処理（複数校舎対応）
  const handleSwitchScheduleSchool = async (schoolId: string, ticketCode?: string) => {
    setCurrentScheduleSchoolId(schoolId);
    setSelectedTime(null);
    setSelectedDayOfWeek(null);
    setSelectedScheduleItem(null);
    await fetchClassSchedules(ticketCode, schoolId);
  };

  // 別の校舎を追加（複数校舎対応）
  const handleAddSchool = (schoolId: string) => {
    if (!selectedSchoolIds.includes(schoolId)) {
      setSelectedSchoolIds(prev => [...prev, schoolId]);
    }
    handleSwitchScheduleSchool(schoolId);
  };

  const handleChildSelect = (child: Child) => {
    setSelectedChild(child);
    setStep(3); // カテゴリ選択へ
  };

  const handleBrandSelect = (brand: PublicBrand) => {
    setSelectedBrand(brand);
    setSelectedSchoolId(null);
    setStep(5); // 校舎選択へ
  };

  const handleSchoolSelect = async (schoolId: string) => {
    setSelectedSchoolId(schoolId);
    // 複数校舎対応：選択校舎一覧を初期化
    setSelectedSchoolIds([schoolId]);
    setCurrentScheduleSchoolId(schoolId);

    // カテゴリ内の最初のブランドをselectedBrandにセット（互換性のため）
    if (categoryBrandIds.length > 0) {
      const brand = brands.find(b => b.id === categoryBrandIds[0]);
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
    if (itemType === 'seminar' || itemType === 'certification') {
      setStep(7); // 講習会・検定選択へ（コースタイプ選択をスキップ）
    } else {
      setStep(6); // コースタイプ選択へ
    }
  };

  const handleCourseTypeSelect = (type: 'single' | 'pack') => {
    setCourseType(type);
    setStep(7); // コース選択へ
  };

  const handleBackToStep = (targetStep: number) => {
    // 講習会・検定の場合は、スキップしたステップを考慮
    if (itemType === 'seminar' || itemType === 'certification') {
      // 講習会・検定のステップ: 1, 2, 3, 4-5, 7, 10, 11
      // step 10 から戻る → step 7 へ
      // step 7 から戻る → step 5 へ
      if (targetStep === 9 || targetStep === 8 || targetStep === 6) {
        setStep(5);
        return;
      }
    }
    // Step 7から戻る場合は頻度選択をリセット
    if (step === 7 && targetStep === 6) {
      setFrequency(null);
      setStep(6);
      return;
    }
    // Step 6で頻度選択中に戻る場合はコースタイプをリセット
    if (step === 6 && courseType && !frequency) {
      setCourseType(null);
      // step 6のままにする（コースタイプ選択画面に戻る）
      return;
    }
    // Step 6でコースタイプ選択中に戻る場合は通常通り
    if (step === 6 && !courseType) {
      setCourseType(null);
      setFrequency(null);
      setStep(5);
      return;
    }
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

      // 「小1~」「年長～」のような「〇〇~」パターンをパース（「以上」と同じ意味）
      // 全角チルダ（～）と半角チルダ（~）両方に対応
      const tildeEndMatch = item.gradeName.match(/^(.+?)[~～]$/);
      if (tildeEndMatch) {
        const minGrade = tildeEndMatch[1].trim();
        const minOrder = getGradeOrder(minGrade);
        // 子どもの学年が最小学年以上かチェック
        return childGradeOrder >= minOrder;
      }

      // 「小1以上」「年長以上」のような「〇〇以上」パターンをパース
      const aboveMatch = item.gradeName.match(/^(.+?)以上$/);
      if (aboveMatch) {
        const minGrade = aboveMatch[1].trim();
        const minOrder = getGradeOrder(minGrade);
        // 子どもの学年が最小学年以上かチェック
        return childGradeOrder >= minOrder;
      }

      // 「小6以下」「中3以下」のような「〇〇以下」パターンをパース
      const belowMatch = item.gradeName.match(/^(.+?)以下$/);
      if (belowMatch) {
        const maxGrade = belowMatch[1].trim();
        const maxOrder = getGradeOrder(maxGrade);
        // 子どもの学年が最大学年以下かチェック
        return childGradeOrder <= maxOrder;
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
        const included = normalizedSchoolTicketIds.includes(normalizedCode);
        return included;
      }
      // パックの場合
      if ('tickets' in item || 'courses' in item) {
        const packItems = getPackItems(item as PublicPack);
        // パックにアイテムがない場合は表示しない
        if (packItems.length === 0) return false;
        // ticketCodeを持つアイテムがあるか確認
        const itemsWithTicket = packItems.filter(pi => pi.ticketCode);
        // ticketCodeを持つアイテムがない場合は、チケットフィルタをスキップして表示
        if (itemsWithTicket.length === 0) return true;
        // ticketCodeを持つアイテムがある場合は、それらが全て校舎で開講しているかチェック
        return itemsWithTicket.every(packItem => {
          const normalizedCode = normalizeTicketCode(packItem.ticketCode);
          return normalizedSchoolTicketIds.includes(normalizedCode);
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
      // 単品コース: パックに含まれているコースは既にバックエンドで除外済み
      // また、コース名に「+」が含まれるもの（複合コース）も除外
      items = courses.filter(c => !c.courseName.includes('+'));
    } else if (courseType === 'pack') {
      // パック + 「+」を含むコース（複合コース）を表示
      const plusCourses = courses.filter(c => c.courseName.includes('+'));
      items = [...packs, ...plusCourses];
    }
    const afterGradeFilter = filterByGrade(items);
    const afterTicketFilter = filterBySchoolTickets(afterGradeFilter);

    // ¥0のコース/パックを除外（表示ロジックと同じ方法で価格を判定）
    const afterPriceFilter = afterTicketFilter.filter((item) => {
      // 表示と同じロジック: tuitionPriceがあればそれを使用、なければitemsからtuitionを探す
      let displayPrice = 0;
      if ('tuitionPrice' in item && item.tuitionPrice) {
        displayPrice = item.tuitionPrice;
      } else if ('items' in item && item.items) {
        const tuitionItem = item.items.find(
          (i: { productType?: string }) => i.productType === 'tuition'
        );
        if (tuitionItem && 'price' in tuitionItem) {
          displayPrice = (tuitionItem as { price: number }).price || 0;
        }
      }
      // 表示価格が0より大きい場合のみ表示
      const included = displayPrice > 0;
      if (!included) {
      }
      return included;
    });

    // 週回数でフィルタリング（frequency選択に基づく）
    const afterFrequencyFilter = afterPriceFilter.filter((item) => {
      // パックの場合はフィルタしない（パックは複数チケットを含む）
      if ('tickets' in item) return true;

      // 単品コースの場合、コース名またはチケット名から週回数を判定
      const courseName = 'courseName' in item ? item.courseName : '';
      const ticketName = 'ticketName' in item ? (item as PublicCourse).ticketName || '' : '';
      const checkString = courseName + ticketName;

      // 「Free」を含むかチェック（フリーパス/無制限）
      const isFree = checkString.includes('Free') || checkString.includes('フリー');
      // 「週1」を含むかチェック
      const isWeekly1 = checkString.includes('週1') || checkString.includes('×1');

      if (frequency === 'weekly') {
        // 週1回選択時: 週1回のコースのみ表示（Freeは除外）
        return isWeekly1 && !isFree;
      } else if (frequency === 'other') {
        // 複数回選択時: 週1回以外（Free、週2以上）を表示
        return !isWeekly1 || isFree;
      }

      // frequencyが未選択の場合は全て表示
      return true;
    });

    // 学年でフィルタリング → 校舎チケットでフィルタリング → 価格フィルタ → 週回数フィルタ → 複数条件でソート
    // ソート順: 校舎 → ブランド → 学年 → チケット
    return sortByMultipleCriteria(afterFrequencyFilter);
  })();

  // 料金計算（API レスポンスがあればそれを使用）
  // grandTotalには入会金、設備費、教材費、割引が全て含まれている
  const isPack = selectedCourse && 'tickets' in selectedCourse;
  // マイル割引を計算
  const mileDiscountAmount = useMiles && milesToUse >= 4 && pricingPreview?.mileInfo?.canUse
    ? Math.floor((milesToUse - 2) / 2) * 500  // 4pt以上で500円引、以後2ptごとに500円引
    : 0;

  // 講習会の合計金額
  const seminarTotalAmount = seminars
    .filter(s => selectedSeminars.includes(s.id))
    .reduce((sum, s) => sum + s.base_price, 0);

  // 検定の合計金額
  const certificationTotalAmount = certifications
    .filter(c => selectedCertifications.includes(c.id))
    .reduce((sum, c) => sum + c.exam_fee, 0);

  // 合計金額: APIのgrandTotalをそのまま使用
  // grandTotalには入会金、設備費、教材費、当月分回数割、2〜3ヶ月目の月謝、割引が全て含まれている
  // 注意: APIの割引（discounts）にはマイル割引が含まれているため、フロントエンドで再度引かない
  const totalAmount = itemType === 'seminar'
    ? seminarTotalAmount
    : itemType === 'certification'
    ? certificationTotalAmount
    : pricingPreview?.grandTotal ?? (selectedCourse?.price || 0);

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
          <Link href="/" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">Class申込</h1>
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

        <div className="mb-3">
          <div className="flex items-center justify-center space-x-1">
            {(itemType === 'regular' ? [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] :
              (itemType === 'seminar' || itemType === 'certification') ? [1, 2, 3, 4, 5, 7, 10, 11] :
              [1, 2, 3]).map((s) => (
              <div
                key={s}
                className={`h-1.5 flex-1 rounded-full transition-colors ${
                  s <= step ? 'bg-blue-500' : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
          <p className="text-center text-xs text-gray-500 mt-1">
            {step === 9 && preSelectClassMode ? 'クラス選択' :
             step === 10 ? '入会規約' :
             step === 11 ? '購入確認' :
             itemType === 'regular' ? `${step}/11` :
             (itemType === 'seminar' || itemType === 'certification') ? `${[1,2,3,4,5,7,10,11].indexOf(step) + 1}/8` :
             `${step}/3`}
          </p>
        </div>

        {/* Step 1: 項目選択 */}
        {step === 1 && !itemType && (
          <div>
            <h2 className="text-base font-semibold text-gray-800 mb-3">購入する項目を選択</h2>
            <div className="space-y-2">
              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-blue-500"
                onClick={() => {
                  setItemType('regular');
                  setStep(2);
                }}
              >
                <CardContent className="p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <BookOpen className="h-5 w-5 text-blue-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-sm text-gray-800">通常授業</h3>
                      <p className="text-xs text-gray-600">単品コース・月額パック</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600">
                    通常の授業コースやお得な月額パックプランです。
                  </p>
                </CardContent>
              </Card>

              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-purple-500"
                onClick={() => {
                  setItemType('seminar');
                  setStep(2);
                }}
              >
                <CardContent className="p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                      <CalendarIcon className="h-5 w-5 text-purple-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-sm text-gray-800">講習会</h3>
                      <p className="text-xs text-gray-600">夏期・冬期・春期講習</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600">
                    季節講習や特別講習に申し込めます。
                  </p>
                </CardContent>
              </Card>

              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-amber-500"
                onClick={() => {
                  setItemType('certification');
                  setStep(2);
                }}
              >
                <CardContent className="p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                      <Trophy className="h-5 w-5 text-amber-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-sm text-gray-800">検定</h3>
                      <p className="text-xs text-gray-600">英検・漢検・数検など</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600">
                    各種検定試験に申し込めます。
                  </p>
                </CardContent>
              </Card>

              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-green-500 opacity-50"
              >
                <CardContent className="p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                      <Users className="h-5 w-5 text-green-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-sm text-gray-800">イベント</h3>
                      <p className="text-xs text-gray-600">特別イベント・体験会</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600">
                    近日公開予定
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {/* Step 2: お子様選択（全ての項目タイプ共通） */}
        {step === 2 && (
          <div>
            <h2 className="text-base font-semibold text-gray-800 mb-3">お子様を選択</h2>

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
                    <CardContent className="p-2 flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-sm text-gray-800">{child.fullName}</h3>
                        <p className="text-xs text-gray-600">{getDisplayGrade(child)}</p>
                      </div>
                      <ChevronLeft className="h-4 w-4 text-gray-400 rotate-180" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Step 3: カテゴリ選択（通常授業・講習会・検定共通） */}
        {step === 3 && (itemType === 'regular' || itemType === 'seminar' || itemType === 'certification') && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName} {selectedChild && <span className="text-gray-600">({getDisplayGrade(selectedChild)})</span>}</p>
                </CardContent>
              </Card>
            </div>
            <h2 className="text-base font-semibold text-gray-800 mb-3">カテゴリを選択</h2>

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
                        // ブランド選択へ
                        setStep(4);
                      }}
                    >
                      <CardContent className="p-2 flex items-center justify-between">
                        <div className="flex items-center">
                          <div
                            className="w-8 h-8 rounded-full flex items-center justify-center mr-2"
                            style={{ backgroundColor: category.colorPrimary ? `${category.colorPrimary}20` : '#E5E7EB' }}
                          >
                            <GraduationCap
                              className="h-4 w-4"
                              style={{ color: category.colorPrimary || '#6B7280' }}
                            />
                          </div>
                          <span className="text-sm font-semibold text-gray-800">{category.categoryName}</span>
                        </div>
                        <ChevronLeft className="h-4 w-4 text-gray-400 rotate-180" />
                      </CardContent>
                    </Card>
                  ));
                })()}
              </div>
            )}
          </div>
        )}

        {/* Step 4-5: 校舎選択 */}
        {(step === 4 || step === 5) && (
          <div className="flex flex-col h-full">
            {/* コンパクトな選択状況表示 */}
            <div className="flex items-center gap-2 mb-3 text-sm">
              <span className="text-gray-500">選択中:</span>
              <span className="font-medium text-gray-800">{selectedChild?.fullName} {selectedChild && <span className="text-gray-600">({getDisplayGrade(selectedChild)})</span>}</span>
              <span className="text-gray-400">›</span>
              <span className="text-blue-600">{selectedCategory?.categoryName}</span>
            </div>

            <h2 className="text-base font-semibold text-gray-800 mb-1">校舎を選択</h2>
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

        {/* Step 6: コースタイプ選択（単品/パック） */}
        {step === 6 && !courseType && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName} {selectedChild && <span className="text-gray-600">({getDisplayGrade(selectedChild)})</span>}</p>
                  <p className="text-sm text-gray-700 mt-1">{selectedCategory?.categoryName} → {selectedSchool?.name}</p>
                </CardContent>
              </Card>
            </div>

            <h2 className="text-base font-semibold text-gray-800 mb-3">コースタイプを選択</h2>
            <div className="space-y-2">
              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-blue-500"
                onClick={() => {
                  setCourseType('single');
                }}
              >
                <CardContent className="p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center">
                      <Package className="h-5 w-5 text-orange-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-sm text-gray-800">単品コース</h3>
                      <p className="text-xs text-gray-600">回数券・都度利用</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600">
                    必要な時に必要な分だけ購入できる、柔軟な利用プランです。
                  </p>
                </CardContent>
              </Card>

              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-blue-500"
                onClick={() => {
                  setCourseType('pack');
                }}
              >
                <CardContent className="p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                      <Sparkles className="h-5 w-5 text-green-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-sm text-gray-800">お得パックコース</h3>
                      <p className="text-xs text-gray-600">月額制・定期コース</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600">
                    定期的に通う方にお得な月額制プランです。入会金もこちらから。
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {/* Step 6: 頻度選択（コースタイプ選択後） */}
        {step === 6 && courseType && !frequency && (
          <div>
            <div className="mb-4">
              <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">選択中</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName} {selectedChild && <span className="text-gray-600">({getDisplayGrade(selectedChild)})</span>}</p>
                  <p className="text-sm text-gray-700 mt-1">{selectedCategory?.categoryName} → {selectedSchool?.name}</p>
                  <Badge className="mt-1 text-xs">
                    {courseType === 'single' ? '単品コース' : 'お得パックコース'}
                  </Badge>
                </CardContent>
              </Card>
            </div>

            <h2 className="text-base font-semibold text-gray-800 mb-3">回数を選択</h2>
            <div className="space-y-2">
              <div
                className="border-2 border-blue-500 rounded-lg px-4 py-3 cursor-pointer hover:bg-blue-50 transition-colors"
                onClick={() => {
                  setFrequency('weekly');
                  setStep(7);
                }}
              >
                <span className="text-base font-semibold text-gray-800">① 週1回</span>
              </div>

              <div
                className="border-2 border-blue-500 rounded-lg px-4 py-3 cursor-pointer hover:bg-blue-50 transition-colors"
                onClick={() => {
                  setFrequency('other');
                  setStep(7);
                }}
              >
                <span className="text-base font-semibold text-gray-800">② 複数回</span>
              </div>
            </div>
          </div>
        )}

        {/* Step 7: コース/講習会/検定選択 */}
        {step === 7 && (
          <div>
            <div className="mb-1.5 bg-gray-50 border border-gray-200 rounded px-2 py-1 text-[10px]">
              <span className="text-gray-500">選択中: </span>
              <span className="font-medium text-gray-800">{selectedChild?.fullName}</span>
              <span className="text-gray-500"> ({selectedChild && getDisplayGrade(selectedChild)}) </span>
              <span className="text-gray-600">{selectedCategory?.categoryName} → {selectedSchool?.name}</span>
              {itemType === 'regular' && (
                <Badge className="text-[8px] px-1 py-0 ml-1 h-3.5">{courseType === 'single' ? '単品' : 'パック'}</Badge>
              )}
            </div>

            <h2 className="text-[11px] font-semibold text-gray-800 mb-1">コースを選択</h2>

            {/* 講習会選択 */}
            {itemType === 'seminar' && (
              <>
                {seminarsError && (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 mb-4">
                    <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                    <p className="text-sm text-red-800">{seminarsError}</p>
                  </div>
                )}
                {isLoadingSeminars ? (
                  <div className="flex flex-col items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-purple-500 mb-3" />
                    <p className="text-sm text-gray-600">講習会を読み込み中...</p>
                  </div>
                ) : seminars.length === 0 ? (
                  <p className="text-center text-gray-600 py-8">講習会がありません</p>
                ) : (
                  <div className="space-y-3">
                    {seminars.map((seminar) => (
                      <Card
                        key={seminar.id}
                        className={`rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer border-2 ${
                          selectedSeminars.includes(seminar.id) ? 'border-purple-500 bg-purple-50' : 'border-transparent'
                        }`}
                        onClick={() => {
                          setSelectedSeminars(prev =>
                            prev.includes(seminar.id)
                              ? prev.filter(id => id !== seminar.id)
                              : [...prev, seminar.id]
                          );
                        }}
                      >
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <Checkbox checked={selectedSeminars.includes(seminar.id)} />
                                <h3 className="font-semibold text-gray-800">{seminar.seminar_name}</h3>
                              </div>
                              <p className="text-sm text-gray-600 mt-1">{seminar.seminar_type}</p>
                              {seminar.start_date && seminar.end_date && (
                                <p className="text-xs text-gray-500 mt-1">
                                  {seminar.start_date} 〜 {seminar.end_date}
                                </p>
                              )}
                            </div>
                            <div className="text-right">
                              <span className="text-xl font-bold text-purple-600">
                                ¥{seminar.base_price.toLocaleString()}
                              </span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                    {selectedSeminars.length > 0 && (
                      <Button
                        onClick={() => setStep(10)}
                        className="w-full h-12 rounded-full bg-purple-600 hover:bg-purple-700 text-white font-semibold mt-4"
                      >
                        次へ（{selectedSeminars.length}件選択中）
                      </Button>
                    )}
                  </div>
                )}
              </>
            )}

            {/* 検定選択 */}
            {itemType === 'certification' && (
              <>
                {certificationsError && (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 mb-4">
                    <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                    <p className="text-sm text-red-800">{certificationsError}</p>
                  </div>
                )}
                {isLoadingCertifications ? (
                  <div className="flex flex-col items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-amber-500 mb-3" />
                    <p className="text-sm text-gray-600">検定を読み込み中...</p>
                  </div>
                ) : certifications.length === 0 ? (
                  <p className="text-center text-gray-600 py-8">検定がありません</p>
                ) : (
                  <div className="space-y-3">
                    {certifications.map((cert) => (
                      <Card
                        key={cert.id}
                        className={`rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer border-2 ${
                          selectedCertifications.includes(cert.id) ? 'border-amber-500 bg-amber-50' : 'border-transparent'
                        }`}
                        onClick={() => {
                          setSelectedCertifications(prev =>
                            prev.includes(cert.id)
                              ? prev.filter(id => id !== cert.id)
                              : [...prev, cert.id]
                          );
                        }}
                      >
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <Checkbox checked={selectedCertifications.includes(cert.id)} />
                                <h3 className="font-semibold text-gray-800">{cert.certification_name}</h3>
                              </div>
                              <p className="text-sm text-gray-600 mt-1">{cert.certification_type}</p>
                              {cert.exam_date && (
                                <p className="text-xs text-gray-500 mt-1">試験日: {cert.exam_date}</p>
                              )}
                              {cert.application_deadline && (
                                <p className="text-xs text-red-500 mt-1">申込締切: {cert.application_deadline}</p>
                              )}
                            </div>
                            <div className="text-right">
                              <span className="text-xl font-bold text-amber-600">
                                ¥{cert.exam_fee.toLocaleString()}
                              </span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                    {selectedCertifications.length > 0 && (
                      <Button
                        onClick={() => setStep(10)}
                        className="w-full h-12 rounded-full bg-amber-600 hover:bg-amber-700 text-white font-semibold mt-4"
                      >
                        次へ（{selectedCertifications.length}件選択中）
                      </Button>
                    )}
                  </div>
                )}
              </>
            )}

            {/* 通常コース選択（既存の実装） */}
            {itemType === 'regular' && (
              <>

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
              <div className="space-y-1">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="border border-gray-200 rounded px-1.5 py-1 animate-pulse">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-1 flex-1">
                        <div className="w-3 h-3 bg-gray-200 rounded" />
                        <div className="h-3 bg-gray-200 rounded w-40" />
                      </div>
                      <div className="h-3 bg-gray-200 rounded w-14" />
                    </div>
                  </div>
                ))}
                <p className="text-[10px] text-gray-400 text-center pt-1">読み込み中...</p>
              </div>
            ) : availableItems.length === 0 ? (
              <p className="text-center text-gray-600 py-8">
                {courseType === 'single'
                  ? '単品コースがありません'
                  : 'パック/月額コースがありません'}
              </p>
            ) : (
              <div className="space-y-1">
                {availableItems.map((item, index) => {
                  // パックの場合はコース一覧を表示
                  const packCourses = 'courses' in item ? item.courses : [];
                  const packTickets = 'tickets' in item ? item.tickets : [];
                  // 番号を丸数字で表示（①②③...）
                  const circledNumber = String.fromCharCode(0x2460 + index);

                  return (
                    <div
                      key={item.id}
                      className="border border-gray-200 rounded px-1.5 py-1 hover:bg-gray-50 transition-colors cursor-pointer"
                      onClick={() => handleCourseSelect(item)}
                    >
                      <div className="flex justify-between items-center">
                        <div className="flex-1 min-w-0 flex items-center gap-1">
                          <span className="text-xs font-bold text-blue-600">{circledNumber}</span>
                          <span className="text-[11px] font-medium text-gray-800 truncate">{getCourseName(item)}</span>
                          {isMonthlyItem(item) && (
                            <Badge className="bg-green-500 text-white text-[8px] px-1 py-0 h-3.5 shrink-0">月額</Badge>
                          )}
                        </div>
                        <span className="text-xs font-bold text-blue-600 shrink-0 ml-1">
                          ¥{('tuitionPrice' in item && item.tuitionPrice ? item.tuitionPrice : getTuitionPrice(item)).toLocaleString()}
                        </span>
                      </div>
                      {item.gradeName && (
                        <p className="text-[9px] text-gray-400 ml-4">対象: {item.gradeName}</p>
                      )}

                      {/* パックの場合：含まれるコース */}
                      {packCourses && packCourses.length > 0 && (
                        <div className="flex flex-wrap gap-0.5 mt-0.5 ml-4">
                          {packCourses.map((pc: { courseId: string; courseName: string }) => (
                            <Badge key={pc.courseId} variant="outline" className="text-[8px] bg-blue-50 text-blue-700 px-1 py-0 h-3.5">
                              {pc.courseName}
                            </Badge>
                          ))}
                        </div>
                      )}

                      {/* パックの場合：チケット情報 */}
                      {packTickets && packTickets.length > 0 && (
                        <div className="flex flex-wrap gap-0.5 mt-0.5 ml-4">
                          {packTickets.map((pt: { ticketId: string; ticketName: string; perWeek?: number }) => (
                            <Badge key={pt.ticketId} variant="outline" className="text-[8px] bg-orange-50 text-orange-700 px-1 py-0 h-3.5">
                              {pt.ticketName}{pt.perWeek ? ` ×週${pt.perWeek}回` : ''}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
            </>
            )}
          </div>
        )}

        {/* Step 8: 開始日選択 */}
        {step === 8 && (
          <div>
            {/* コンパクトな選択状況表示 */}
            <div className="flex items-center gap-1 mb-3 text-xs text-gray-500 flex-wrap">
              <span className="font-medium text-gray-700">{selectedChild?.fullName} {selectedChild && `(${getDisplayGrade(selectedChild)})`}</span>
              <span>›</span>
              <span className="text-blue-600">{selectedSchool?.name}</span>
              <span>›</span>
              <span className="text-blue-600">{selectedCourse && getCourseName(selectedCourse)}</span>
            </div>

            <h2 className="text-base font-semibold text-gray-800 mb-2">開始日を選択</h2>

            <Card className="rounded-xl shadow-md mb-3">
              <CardContent className="p-2">
                <Calendar
                  mode="single"
                  selected={startDate}
                  onSelect={async (date) => {
                    if (date) setStartDate(date);
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
            {billingInfo && billingInfo.first_billable_month && (
              <div className="mb-3 p-3 rounded-lg border bg-blue-50 border-blue-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-blue-600" />
                    <span className="text-sm text-blue-800">請求月</span>
                  </div>
                  <span className="text-lg font-bold text-blue-800">
                    {billingInfo.first_billable_month.month}月請求
                  </span>
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
                    // 単体コースの複数週次選択用stateもリセット
                    setCurrentWeeklyIndex(0);
                    setSelectedWeeklySchedules([]);

                    // パックの場合は最初のアイテムで開講時間割を取得
                    if (hasPackItems) {
                      fetchClassSchedules(packItems[0].ticketCode);
                    } else {
                      fetchClassSchedules();
                    }
                    setStep(9); // クラス選択ステップへ
                  } else {
                    // 単品コースは直接規約確認へ
                    setStep(10);
                  }
                }}
                className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg"
              >
                次へ
              </Button>
            )}
          </div>
        )}

        {/* Step 9: 月額コースの場合のクラス選択（購入前） */}
        {step === 9 && preSelectClassMode && (() => {
          const dayLabels = classScheduleData?.dayLabels || ['月', '火', '水', '木', '金', '土', '日'];

          // パックアイテム（tickets または courses）を取得
          const isPack = selectedCourse && ('tickets' in selectedCourse || 'courses' in selectedCourse);
          const packItems = isPack ? getPackItems(selectedCourse as PublicPack) : [];
          const hasPackItems = packItems.length > 0;
          const currentItem = hasPackItems ? packItems[currentTicketIndex] : null;
          const totalItems = packItems.length;
          const isLastItem = currentTicketIndex >= totalItems - 1;

          // 単体コースの週あたり回数を取得
          const singleCoursePerWeek = !isPack && selectedCourse && 'perWeek' in selectedCourse
            ? (selectedCourse as PublicCourse).perWeek || 1
            : 1;
          const hasSingleCourseMultipleWeekly = !isPack && singleCoursePerWeek > 1;
          const isLastWeeklyItem = currentWeeklyIndex >= singleCoursePerWeek - 1;

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

          const handleTimeSlotSelect = async (time: string, dayOfWeek: string) => {
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

            // 曜日選択後に料金プレビューを再取得（回数割計算のため）
            if (startDate && selectedCourse && selectedChild) {
              setIsLoadingPricing(true);
              try {
                const preview = await previewPricing({
                  studentId: selectedChild.id,
                  productIds: [selectedCourse.id],
                  courseId: selectedCourse.id,
                  startDate: format(startDate, 'yyyy-MM-dd'),
                  dayOfWeek: dayOfWeekToBackendNumber(dayOfWeek),
                });
                setPricingPreview(preview);
              } catch (err) {
                console.error('料金プレビュー再取得エラー:', err);
              } finally {
                setIsLoadingPricing(false);
              }
            }
          };

          // パックの次のアイテムに進む / 単体コースの次の週次選択に進む
          const handleNextItem = () => {
            // パックの場合
            if (hasPackItems) {
              // 現在のアイテムの選択を保存（曜日と時間も含む）
              if (currentItem && selectedScheduleItem && selectedDayOfWeek && selectedTime) {
                const currentSchool = schools.find(s => s.id === currentScheduleSchoolId);
                const newMap = new Map(selectedClassesPerTicket);
                newMap.set(currentItem.id, {
                  schedule: selectedScheduleItem,
                  dayOfWeek: selectedDayOfWeek,
                  time: selectedTime,
                  schoolId: currentScheduleSchoolId || selectedSchoolId || '',
                  schoolName: currentSchool?.name || selectedSchool?.name || '',
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
                setStep(10);
              }
            }
            // 単体コースで週あたり複数回の場合
            else if (hasSingleCourseMultipleWeekly) {
              // 現在の週次選択を保存
              if (selectedScheduleItem && selectedDayOfWeek && selectedTime) {
                const currentSchool = schools.find(s => s.id === currentScheduleSchoolId);
                const newSchedules = [...selectedWeeklySchedules];
                // 配列の末尾に追加（currentWeeklyIndexは使わない）
                newSchedules.push({
                  schedule: selectedScheduleItem,
                  dayOfWeek: selectedDayOfWeek,
                  time: selectedTime,
                  schoolId: currentScheduleSchoolId || selectedSchoolId || '',
                  schoolName: currentSchool?.name || selectedSchool?.name || '',
                });
                setSelectedWeeklySchedules(newSchedules);

                // まだ選択可能枠が残っている場合は次の選択へ
                if (newSchedules.length < singleCoursePerWeek) {
                  setSelectedTime(null);
                  setSelectedDayOfWeek(null);
                  setSelectedScheduleItem(null);
                } else {
                  // 最大枠まで選択したら料金プレビューを更新してから規約確認へ
                  if (selectedCourse && selectedChild && startDate) {
                    const daysOfWeek = newSchedules.map(s => dayOfWeekToBackendNumber(s.dayOfWeek)).filter((d): d is number => d !== undefined);
                    previewPricing({
                      studentId: selectedChild.id,
                      productIds: [selectedCourse.id],
                      courseId: selectedCourse.id,
                      startDate: format(startDate, 'yyyy-MM-dd'),
                      daysOfWeek: daysOfWeek,
                    }).then(preview => {
                      setPricingPreview(preview);
                      setStep(10);
                    }).catch(err => {
                      console.error('料金プレビュー再取得エラー:', err);
                      setStep(10);
                    });
                  } else {
                    setStep(10);
                  }
                }
              }
            }
            // 単体コースで週1回の場合（従来通り）
            else {
              setStep(10);
            }
          };

          // 週次選択を完了して次へ進む（最大枠を満たさなくてもOK）
          const handleCompleteWeeklySelection = async () => {
            // 現在選択中のものがあれば保存
            let finalSchedules = [...selectedWeeklySchedules];
            if (selectedScheduleItem && selectedDayOfWeek && selectedTime) {
              const currentSchool = schools.find(s => s.id === currentScheduleSchoolId);
              finalSchedules.push({
                schedule: selectedScheduleItem,
                dayOfWeek: selectedDayOfWeek,
                time: selectedTime,
                schoolId: currentScheduleSchoolId || selectedSchoolId || '',
                schoolName: currentSchool?.name || selectedSchool?.name || '',
              });
              setSelectedWeeklySchedules(finalSchedules);
            }

            // 複数曜日で料金プレビューを再取得
            if (selectedCourse && selectedChild && startDate && finalSchedules.length > 0) {
              try {
                const daysOfWeek = finalSchedules.map(s => dayOfWeekToBackendNumber(s.dayOfWeek)).filter((d): d is number => d !== undefined);
                const preview = await previewPricing({
                  studentId: selectedChild.id,
                  productIds: [selectedCourse.id],
                  courseId: selectedCourse.id,
                  startDate: format(startDate, 'yyyy-MM-dd'),
                  daysOfWeek: daysOfWeek,
                });
                setPricingPreview(preview);
              } catch (err) {
                console.error('料金プレビュー再取得エラー:', err);
              }
            }

            // 規約確認へ
            setStep(10);
          };

          return (
            <div>
              <div className="mb-4">
                <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                  <CardContent className="p-3">
                    <p className="text-xs text-gray-600 mb-1">選択中</p>
                    <p className="font-semibold text-gray-800">{selectedChild?.fullName} {selectedChild && <span className="text-gray-600">({getDisplayGrade(selectedChild)})</span>}</p>
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

              {/* 単体コースで週あたり複数回の場合は進捗を表示 */}
              {hasSingleCourseMultipleWeekly && (
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-gray-700">
                      授業 {selectedWeeklySchedules.length + (selectedTime ? 1 : 0)} / {singleCoursePerWeek} (最大週{singleCoursePerWeek}回まで)
                    </p>
                    <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700">
                      {selectedTime
                        ? `${selectedWeeklySchedules.length + 1}回目を選択済み`
                        : `${selectedWeeklySchedules.length + 1}回目を選択中`}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500 mb-2">
                    ※ 1回以上選択すれば次に進めます
                  </p>
                  <div className="flex gap-1">
                    {Array.from({ length: singleCoursePerWeek }).map((_, idx) => (
                      <div
                        key={idx}
                        className={`h-2 flex-1 rounded-full ${
                          idx < selectedWeeklySchedules.length
                            ? 'bg-green-500'
                            : idx === selectedWeeklySchedules.length && selectedTime
                            ? 'bg-blue-500'
                            : 'bg-gray-200'
                        }`}
                      />
                    ))}
                  </div>
                  {/* 選択済みの曜日・時間帯を表示（校舎名も含む） */}
                  {selectedWeeklySchedules.length > 0 && (
                    <div className="mt-3 space-y-1.5">
                      <p className="text-xs font-semibold text-gray-700 mb-1">選択した時間割</p>
                      {selectedWeeklySchedules.map((s, idx) => {
                        const isOtherSchool = s.schoolId !== selectedSchoolId;
                        return (
                          <div
                            key={idx}
                            className={`flex items-center justify-between px-2 py-1.5 rounded border ${
                              isOtherSchool ? 'border-green-400 bg-green-50' : 'border-gray-200 bg-white'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <span className={`text-xs font-bold ${isOtherSchool ? 'text-green-600' : 'text-gray-700'}`}>
                                □{idx + 1}コマ目
                              </span>
                              <span className={`text-xs font-semibold ${isOtherSchool ? 'text-green-700' : 'text-gray-800'}`}>
                                {s.schoolName}
                              </span>
                              <span className={`text-xs ${isOtherSchool ? 'text-green-600' : 'text-gray-600'}`}>
                                {s.dayOfWeek.replace('曜日', '')}
                              </span>
                              <span className={`text-xs font-medium ${isOtherSchool ? 'text-green-700' : 'text-gray-800'}`}>
                                {s.time}～
                              </span>
                            </div>
                            <button
                              onClick={() => {
                                setSelectedWeeklySchedules(prev => prev.filter((_, i) => i !== idx));
                              }}
                              className="text-red-500 hover:text-red-700 text-xs px-1"
                            >
                              ✕
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              <h2 className="text-lg font-semibold text-gray-800 mb-2">
                {hasPackItems
                  ? `${currentItem?.name} の曜日・時間帯を選択`
                  : hasSingleCourseMultipleWeekly
                  ? (selectedTime
                    ? `${selectedWeeklySchedules.length + 1}回目の曜日・時間帯`
                    : `${selectedWeeklySchedules.length + 1}回目の曜日・時間帯を選択`)
                  : '曜日・時間帯を選択'}
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                希望する曜日と時間帯を選択してください。
                {hasSingleCourseMultipleWeekly && <span className="text-blue-600">（別の校舎を選んで通うこともできます）</span>}
              </p>

              {/* 複数校舎対応：校舎選択タブ */}
              {hasSingleCourseMultipleWeekly && (
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2 overflow-x-auto pb-2">
                    {selectedSchoolIds.map((schoolId) => {
                      const school = schools.find(s => s.id === schoolId);
                      const isActive = currentScheduleSchoolId === schoolId;
                      return (
                        <button
                          key={schoolId}
                          onClick={() => handleSwitchScheduleSchool(schoolId, hasPackItems ? packItems[currentTicketIndex]?.ticketCode : undefined)}
                          className={`flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                            isActive
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {school?.name || '校舎'}
                        </button>
                      );
                    })}
                    {/* 別の校舎を追加ボタン */}
                    <div className="relative flex-shrink-0">
                      <button
                        onClick={() => {
                          const addSchoolEl = document.getElementById('add-school-dropdown');
                          if (addSchoolEl) {
                            addSchoolEl.classList.toggle('hidden');
                          }
                        }}
                        className="px-4 py-2 rounded-full text-sm font-medium bg-green-100 text-green-700 hover:bg-green-200 flex items-center gap-1"
                      >
                        <span>＋ 別の校舎</span>
                      </button>
                      <div id="add-school-dropdown" className="hidden absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 min-w-[200px] max-h-60 overflow-y-auto">
                        {schools.filter(s => !selectedSchoolIds.includes(s.id)).map((school) => (
                          <button
                            key={school.id}
                            onClick={() => {
                              handleAddSchool(school.id);
                              document.getElementById('add-school-dropdown')?.classList.add('hidden');
                            }}
                            className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 border-b border-gray-100 last:border-b-0"
                          >
                            {school.name}
                          </button>
                        ))}
                        {schools.filter(s => !selectedSchoolIds.includes(s.id)).length === 0 && (
                          <p className="px-4 py-2 text-sm text-gray-500">追加できる校舎がありません</p>
                        )}
                      </div>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500">
                    現在の校舎: <span className="font-semibold">{schools.find(s => s.id === currentScheduleSchoolId)?.name || selectedSchool?.name}</span>
                  </p>
                </div>
              )}

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
                  <CardContent className="p-4 text-center">
                    <CalendarIcon className="h-10 w-10 text-gray-400 mx-auto mb-2" />
                    <p className="text-sm text-gray-600 mb-1">この校舎では現在開講枠がありません</p>
                    <p className="text-xs text-gray-500">
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
                                const dayOfWeekName = label + '曜日';
                                // 既に選択済みかどうかチェック（同じ曜日・時間帯の重複選択を防止）
                                // 単体コースの複数週次選択と、パックの複数チケット選択の両方をチェック
                                // dayOfWeekは「水曜日」形式で保存されているため、dayOfWeekNameと比較する
                                const isAlreadySelectedWeekly = selectedWeeklySchedules.some(
                                  s => s.time === timeSlot.time && s.dayOfWeek === dayOfWeekName
                                );
                                const isAlreadySelectedPack = Array.from(selectedClassesPerTicket.values()).some(
                                  s => s.time === timeSlot.time && s.dayOfWeek === dayOfWeekName
                                );
                                // 現在選択中（まだ確定していない）のスロットもチェック
                                const isCurrentlySelected = selectedTime === timeSlot.time && selectedDayOfWeek === dayOfWeekName;
                                const isAlreadySelected = isAlreadySelectedWeekly || isAlreadySelectedPack;
                                // 選択不可: 空席なし、満席、既に確定済み、または現在選択中
                                const canSelect = status !== 'none' && status !== 'full' && !isAlreadySelected && !isCurrentlySelected;
                                const isSelected = isCurrentlySelected;

                                return (
                                  <td
                                    key={dayIdx}
                                    className={`text-center py-3 px-2 ${canSelect ? 'cursor-pointer hover:bg-blue-50' : ''
                                      } ${isSelected ? 'bg-blue-100' : ''
                                      } ${isAlreadySelected ? 'bg-green-100' : ''
                                      }`}
                                    onClick={() => {
                                      if (canSelect) {
                                        handleTimeSlotSelect(timeSlot.time, dayOfWeekName);
                                      }
                                    }}
                                  >
                                    {isAlreadySelected ? <CheckCircle2 className="h-4 w-4 text-green-600 mx-auto" /> : getStatusIcon(status)}
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
                {/* メインボタン：追加選択 or 次へ */}
                <Button
                  onClick={() => {
                    // パック、単体コース複数週次、単体コース週1回の全てに対応
                    handleNextItem();
                  }}
                  disabled={!selectedTime && classScheduleData?.timeSlots.length !== undefined && classScheduleData.timeSlots.length > 0}
                  className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg disabled:opacity-50"
                >
                  {selectedTime
                    ? (hasPackItems && !isLastItem
                        ? '次のコースへ'
                        : hasSingleCourseMultipleWeekly && selectedWeeklySchedules.length + 1 < singleCoursePerWeek
                        ? `この曜日を追加してさらに選択`
                        : '次へ')
                    : (!classScheduleData || classScheduleData.timeSlots.length === 0)
                      ? (hasPackItems && !isLastItem
                          ? '次のコースへ（後で予約）'
                          : '次へ（後で予約）')
                      : '曜日・時間帯を選択してください'}
                </Button>

                {/* 週次複数選択の場合: 選択完了ボタン（1つ以上選択済みなら有効） */}
                {hasSingleCourseMultipleWeekly && (selectedWeeklySchedules.length > 0 || selectedTime) && (
                  <Button
                    onClick={handleCompleteWeeklySelection}
                    variant="outline"
                    className="w-full h-12 rounded-full border-blue-600 text-blue-600 hover:bg-blue-50 font-semibold"
                  >
                    {selectedTime
                      ? `この曜日を追加して完了（計${selectedWeeklySchedules.length + 1}回）`
                      : `選択を完了（計${selectedWeeklySchedules.length}回）`}
                  </Button>
                )}
              </div>
            </div>
          );
        })()}

        {/* Step 10: 利用規約 */}
        {step === 10 && (
          <div>
            <h2 className="text-base font-semibold text-gray-800 mb-3">入会規約の確認</h2>

            <Card className="rounded-xl shadow-md mb-4">
              <CardContent className="p-4">
                <div
                  ref={termsRef}
                  onScroll={handleTermsScroll}
                  className="h-96 overflow-y-auto bg-gray-50 rounded-lg p-4 text-sm text-gray-700 space-y-4"
                >
                  <h3 className="font-bold text-lg text-gray-800 text-center">【入会規約】</h3>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅰ．生徒遵守事項</h4>
                    <p className="mb-2">授業を円滑に進め、学力向上を図るため、以下の事項を守ってください。</p>
                    <ol className="list-decimal ml-5 space-y-1">
                      <li>入室・退室時には、元気よく挨拶をしましょう。</li>
                      <li>授業開始時間に遅れないようにしてください。</li>
                      <li>講師が「休み時間です」と伝えるまでは、集中して学習に取り組みましょう。</li>
                      <li>授業中の私語や、必要のない立ち歩きは控えてください。</li>
                      <li>授業時間と休憩時間の区別をしっかりつけましょう。</li>
                      <li>宿題は自分のために、必ず取り組んでください。</li>
                      <li>定期テストや通知表の結果は、必ず報告してください。</li>
                      <li>塾内では携帯電話の使用・操作は禁止です。</li>
                    </ol>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅱ．禁止事項</h4>
                    <p className="mb-2">以下の行為が確認された場合、退塾処分となることがあります。</p>
                    <ol className="list-decimal ml-5 space-y-1">
                      <li>長期間の無断欠席</li>
                      <li>学習に関係のない書籍・ゲームの持ち込みや視聴、音楽鑑賞</li>
                      <li>いじめ行為（単独・複数を問わず）</li>
                      <li>小中高生にふさわしくない物品の持参</li>
                      <li>他の生徒や保護者に危害を及ぼす可能性のある物品の持参</li>
                      <li>塾が指定する勉強会・講習会・模試等を、塾長の許可なく欠席すること</li>
                      <li>授業中の飲食（お菓子・ジュース等）</li>
                      <li>授業中の携帯電話使用</li>
                      <li>校舎や備品の破損（故意・過失を問わず弁償対象）</li>
                      <li>机・壁・PC等への落書き（原状回復が必要）</li>
                      <li>講師の注意を素直に受け入れられない態度</li>
                      <li>講師の指示に従わない行為</li>
                    </ol>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅲ．授業料納入について</h4>
                    <ol className="list-decimal ml-5 space-y-1">
                      <li>授業料は翌月分を前月末日までにご納入ください。</li>
                      <li>授業料は口座振替にてお支払いいただきます。現金での納入はお受けできません。</li>
                      <li>口座振替日は毎月27日（金融機関休業日の場合は翌営業日）です。</li>
                      <li>入会後1ヶ月以内に、口座振替依頼書をご提出ください。</li>
                      <li>手続き完了までに2～3ヶ月かかる場合があります。</li>
                      <li>手続き完了までの授業料は銀行振込にてご納入ください（振込手数料は保護者様ご負担）。</li>
                      <li>コース変更に伴う授業料の変更反映には、最大2ヶ月かかる場合があります。</li>
                      <li>中高生は3月度（2/27振替分）より、その他のコースは4月度（3/27振替分）より新学年の授業料が適用されます。※一部コースは異なる場合があります。</li>
                    </ol>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅳ．ご家庭と塾とのご連絡について</h4>
                    <ol className="list-decimal ml-5 space-y-1">
                      <li>欠席の際は、専用サイトよりご連絡ください。</li>
                      <li>授業中にお子様へのご連絡が必要な場合は、総合受付（0561-54-4449）までご連絡ください。</li>
                    </ol>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅴ．指導日について</h4>
                    <p className="mb-2">アンイングリッシュグループでは、毎年指導日を年間カレンダーによって指定しております。（但し年度中でも指導上の都合により変更されることがあります。）</p>
                    <ol className="list-decimal ml-5 space-y-1">
                      <li>年間42回の授業を基本としたカリキュラムを編成しています。</li>
                      <li>祝日であっても授業を行う場合があります。</li>
                      <li>学習塾に通う小4～中3は、春・夏・冬の講習会に必ずご参加ください（カリキュラムの一環です）。</li>
                      <li>上記以外の学年及びカルチャー生の講習会は任意参加になります。</li>
                    </ol>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅵ．授業の振替について</h4>
                    <ol className="list-decimal ml-5 space-y-1">
                      <li>欠席のご連絡および振替予約は、専用サイトにて承ります。</li>
                      <li>お電話でのご連絡・予約につきましては、1授業ごとに110円（税込）の「入力代行手数料」を申し受けます。</li>
                      <li>振替予約後に同クラスへ新規入会者があった場合、別日への振替をお願いすることがあります。</li>
                    </ol>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅶ．割引制度</h4>
                    <ul className="list-disc ml-5 space-y-1">
                      <li><span className="font-medium">フレンドシップ割引：</span>ご紹介により入会された場合、紹介者・入会者双方のご家庭に毎月割引が適用されます。</li>
                      <li><span className="font-medium">家族割引：</span>兄弟や複数コース受講の場合、毎月割引が適用されます。</li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅷ．休会規約</h4>
                    <ol className="list-decimal ml-5 space-y-1">
                      <li>休会希望月の前月末日までに、専用サイトより休会手続きを行ってください。</li>
                      <li>休会中の座席確保をされる場合は、休会費880円(税込)が発生します。</li>
                      <li>休会希望月の前月5日を過ぎると翌月分の請求が発生します。休会費が発生する場合、納入済授業料から休会費を差し引いた金額を、復会後に充当いたします。</li>
                    </ol>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅸ．退会規約</h4>
                    <ol className="list-decimal ml-5 space-y-1">
                      <li>退会希望月の5日までに、専用サイトより退会手続きを行ってください。</li>
                      <li>5日を過ぎると翌月分の請求が発生します。返金は事務手数料を差し引いた上で、翌々月末に行います。</li>
                      <li>当月に入ってからの前月末での退会はお受けできません。納入済授業料の返金もできません。</li>
                      <li>未納授業料がある場合、全額納入後に退会手続きが可能です。</li>
                    </ol>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅹ．アンイングリッシュクラブ教材について</h4>
                    <ol className="list-decimal ml-5 space-y-1">
                      <li>教科書は必ずご購入いただきます。音声教材はオンラインでご利用いただけます（教材費に含む）。</li>
                      <li>お申込み後の教材の返品・返金はできません。</li>
                    </ol>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅺ．保護者様へのお願い</h4>
                    <ol className="list-decimal ml-5 space-y-1">
                      <li>授業開始5分以上前の入室はご遠慮ください。</li>
                      <li>お迎えの際は、授業終了時に校舎内までお越しください。</li>
                      <li>授業中は講師が電話に出られません。緊急時は総合受付（0561-54-4449）までご連絡ください。</li>
                    </ol>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Ⅻ．大型店舗内の校舎の休講について</h4>
                    <p>大型店舗内にある校舎は、店舗の休館により、アンイングリッシュグループの開講日であっても休講となる場合がございます。その際は、振替対応にて授業回数を調整させていただきます。</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {!hasScrolledToBottom && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200 mb-4">
                <AlertCircle className="h-5 w-5 text-amber-600 shrink-0" />
                <p className="text-sm text-amber-800">規約を最後までスクロールしてください</p>
              </div>
            )}

            <div className={`flex items-start gap-3 mb-4 p-4 bg-gray-50 rounded-lg ${!hasScrolledToBottom ? 'opacity-50' : ''}`}>
              <Checkbox
                checked={agreedToTerms}
                onCheckedChange={(checked) => setAgreedToTerms(!!checked)}
                id="terms"
                disabled={!hasScrolledToBottom}
              />
              <label htmlFor="terms" className={`text-sm text-gray-700 ${hasScrolledToBottom ? 'cursor-pointer' : 'cursor-not-allowed'}`}>
                入会規約を確認し、同意します
              </label>
            </div>

            <Button
              onClick={() => setStep(11)}
              disabled={!agreedToTerms}
              className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              同意して次へ
            </Button>
          </div>
        )}

        {/* Step 11: 購入内容の確認 */}
        {step === 11 && (
          <div>
            <h2 className="text-base font-semibold text-gray-800 mb-3">購入内容の確認</h2>

            {confirmError && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 mb-4">
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                <p className="text-sm text-red-800">{confirmError}</p>
              </div>
            )}

            <Card className="rounded-xl shadow-md mb-4">
              <CardContent className="p-4 space-y-3">
                <div>
                  <p className="text-sm text-gray-600 mb-1">お子様</p>
                  <p className="font-semibold text-gray-800">{selectedChild?.fullName} {selectedChild && <span className="text-gray-600">({getDisplayGrade(selectedChild)})</span>}</p>
                </div>
                <div className="border-t pt-4">
                  <p className="text-sm text-gray-600 mb-1">カテゴリ</p>
                  <p className="font-semibold text-gray-800">
                    {selectedCategory?.categoryName}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">校舎</p>
                  {/* 複数校舎がある場合は一覧表示 */}
                  {selectedSchoolIds.length > 1 ? (
                    <div className="space-y-1">
                      {selectedSchoolIds.map(schoolId => {
                        const school = schools.find(s => s.id === schoolId);
                        return (
                          <p key={schoolId} className="font-semibold text-gray-800">{school?.name}</p>
                        );
                      })}
                    </div>
                  ) : (
                    <>
                      <p className="font-semibold text-gray-800">{selectedSchool?.name}</p>
                      <p className="text-sm text-gray-600">{selectedSchool?.address}</p>
                    </>
                  )}
                </div>
                {itemType === 'regular' && (
                  <>
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
                  </>
                )}

                {/* 講習会の場合 */}
                {itemType === 'seminar' && (
                  <div className="border-t pt-4">
                    <p className="text-sm text-gray-600 mb-1">選択した講習会</p>
                    <div className="space-y-2">
                      {seminars.filter(s => selectedSeminars.includes(s.id)).map(seminar => (
                        <div key={seminar.id} className="bg-purple-50 rounded-lg p-3">
                          <p className="font-semibold text-gray-800">{seminar.seminar_name}</p>
                          <p className="text-sm text-gray-600">{seminar.seminar_type}</p>
                          <p className="text-purple-600 font-semibold">¥{seminar.base_price.toLocaleString()}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 検定の場合 */}
                {itemType === 'certification' && (
                  <div className="border-t pt-4">
                    <p className="text-sm text-gray-600 mb-1">選択した検定</p>
                    <div className="space-y-2">
                      {certifications.filter(c => selectedCertifications.includes(c.id)).map(cert => (
                        <div key={cert.id} className="bg-amber-50 rounded-lg p-3">
                          <p className="font-semibold text-gray-800">{cert.certification_name}</p>
                          <p className="text-sm text-gray-600">{cert.certification_type}</p>
                          {cert.exam_date && <p className="text-xs text-gray-500">試験日: {cert.exam_date}</p>}
                          <p className="text-amber-600 font-semibold">¥{cert.exam_fee.toLocaleString()}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 選択したクラス（曜日・時間帯） - 複数校舎対応 */}
                {(selectedWeeklySchedules.length > 0 || (selectedDayOfWeek && selectedTime)) && (
                  <div className="border-t pt-4">
                    <p className="text-sm text-gray-600 mb-1">選択クラス</p>
                    {selectedWeeklySchedules.length > 0 ? (
                      <div className="space-y-2">
                        {selectedWeeklySchedules.map((schedule, idx) => (
                          <div key={idx} className="bg-blue-50 rounded-lg p-3">
                            <p className="font-semibold text-gray-800">
                              {schedule.dayOfWeek} {schedule.time}～
                            </p>
                            {schedule.schoolName && (
                              <p className="text-sm text-blue-600">📍 {schedule.schoolName}</p>
                            )}
                            {schedule.schedule?.className && (
                              <p className="text-sm text-gray-600 mt-1">
                                {schedule.schedule.className}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : selectedDayOfWeek && selectedTime && (
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
                    )}
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

                {/* 教材費選択セクション */}
                {pricingPreview?.textbookOptions && pricingPreview.textbookOptions.length > 0 && (
                  <div className="border-t pt-4">
                    <div className="flex items-center gap-2 mb-3">
                      <BookOpen className="h-4 w-4 text-amber-600" />
                      <span className="text-sm font-medium text-gray-800">教材費の支払い方法</span>
                    </div>
                    <div className="space-y-2">
                      {pricingPreview.textbookOptions.map((option) => {
                        const isSelected = selectedTextbookIds.includes(option.productId);
                        const paymentLabel = option.paymentType === 'monthly' ? '月払い' :
                          option.paymentType === 'semi_annual' ? '半年払い' : '年払い';
                        const billingDesc = option.billingMonths.length > 0
                          ? `${option.billingMonths.map(m => `${m}月`).join('・')}請求`
                          : '毎月請求';

                        return (
                          <div
                            key={option.productId}
                            onClick={() => {
                              if (isSelected) {
                                setSelectedTextbookIds(prev => prev.filter(id => id !== option.productId));
                              } else {
                                // 他の教材費オプションを解除して新しいものを選択（排他選択）
                                setSelectedTextbookIds([option.productId]);
                              }
                            }}
                            className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                              isSelected
                                ? 'border-amber-500 bg-amber-50'
                                : 'border-gray-200 bg-white hover:border-amber-300'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                                  isSelected ? 'border-amber-500 bg-amber-500' : 'border-gray-300'
                                }`}>
                                  {isSelected && <CheckCircle2 className="h-4 w-4 text-white" />}
                                </div>
                                <div>
                                  {/* 入会時教材費を先に表示 */}
                                  {option.enrollmentPriceWithTax !== undefined && option.enrollmentPriceWithTax > 0 && (
                                    <p className="font-medium text-gray-800">入会時教材費（{option.enrollmentMonth}月入会）</p>
                                  )}
                                  <p className={`text-gray-600 ${option.enrollmentPriceWithTax ? 'text-xs mt-1' : 'font-medium text-gray-800'}`}>
                                    {paymentLabel}（2ヶ月目以降: {billingDesc}）
                                  </p>
                                </div>
                              </div>
                              <div className="text-right">
                                {/* 入会時教材費の金額を先に表示 */}
                                {option.enrollmentPriceWithTax !== undefined && option.enrollmentPriceWithTax > 0 && (
                                  <p className="font-semibold text-amber-600">¥{option.enrollmentPriceWithTax.toLocaleString()}</p>
                                )}
                                <p className={`${option.enrollmentPriceWithTax ? 'text-xs text-gray-500 mt-1' : 'font-semibold text-amber-600'}`}>
                                  {option.enrollmentPriceWithTax ? `${paymentLabel}: ` : ''}¥{option.priceWithTax.toLocaleString()}
                                  {!option.enrollmentPriceWithTax && <span className="text-xs text-gray-500 ml-1">（税込/回）</span>}
                                </p>
                              </div>
                            </div>
                          </div>
                        );
                      })}

                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      ※ 入会時教材費は入会月に応じた料金が適用されます
                    </p>
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
                      {/* 入会時費用（選択した教材費の入会時教材費を含む） */}
                      {(() => {
                        // 選択した教材費の入会時教材費を取得
                        const selectedTextbookOption = pricingPreview.textbookOptions?.find(
                          opt => selectedTextbookIds.includes(opt.productId)
                        );
                        const enrollmentTextbookPrice = selectedTextbookOption?.enrollmentPriceWithTax || 0;

                        // APIから返される入会時教材費と当月分項目を除外
                        // - 入会時教材費: 選択した教材費で置き換えるため
                        // - 当月分授業料/月会費/設備費: 月別請求セクションで表示するため
                        const filteredEnrollmentItems = pricingPreview.billingByMonth.enrollment.items.filter(
                          (item: any) => {
                            if (item.itemType === 'enrollment_textbook') return false;
                            const name = item.billingCategoryName || item.productName || '';
                            if (name.includes('当月分授業料')) return false;
                            if (name.includes('当月分月会費')) return false;
                            if (name.includes('当月分設備費')) return false;
                            return true;
                          }
                        );
                        const filteredEnrollmentTotal = filteredEnrollmentItems.reduce(
                          (sum: number, item: any) => sum + (item.priceWithTax || 0), 0
                        );

                        // 入会時費用合計（フィルタ後の合計 + 選択した教材の入会時教材費）
                        const enrollmentTotal = filteredEnrollmentTotal + enrollmentTextbookPrice;

                        // 入会時費用を表示するかどうか（フィルタ後のアイテムがあるか、または入会時教材費がある場合）
                        const hasEnrollmentFees = filteredEnrollmentItems.length > 0 || enrollmentTextbookPrice > 0;

                        if (!hasEnrollmentFees) return null;

                        return (
                          <div className="bg-blue-50 rounded-lg p-3 space-y-2">
                            <div className="flex justify-between items-center border-b border-blue-200 pb-2 mb-2">
                              <span className="font-semibold text-blue-800">{pricingPreview.billingByMonth.enrollment.label || '入会時費用'}</span>
                              <span className="font-semibold text-blue-800">¥{enrollmentTotal.toLocaleString()}</span>
                            </div>
                            {filteredEnrollmentItems.map((item: any, index: number) => (
                              <div key={index} className="flex justify-between text-sm">
                                <span className="text-gray-700">{item.billingCategoryName || item.productName}</span>
                                <span className="text-gray-800">¥{item.priceWithTax.toLocaleString()}</span>
                              </div>
                            ))}
                            {/* 選択した教材費の入会時教材費を表示 */}
                            {enrollmentTextbookPrice > 0 && selectedTextbookOption && (
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-700">入会時教材費（{selectedTextbookOption.enrollmentMonth}月入会）</span>
                                <span className="text-gray-800">¥{enrollmentTextbookPrice.toLocaleString()}</span>
                              </div>
                            )}
                          </div>
                        );
                      })()}

                      {/* 当月分（回数割） - 設備費は既存契約より高い場合のみ差額を請求 */}
                      {(() => {
                        const existingFacilityMax = pricingPreview.existingFacilityFee?.maxFee || 0;
                        const processedItems = pricingPreview.billingByMonth.currentMonth.items.map((item: any) => {
                          if (item.itemType === 'facility') {
                            const newFee = item.priceWithTax || 0;
                            if (existingFacilityMax >= newFee) {
                              return null;
                            }
                            const diff = newFee - existingFacilityMax;
                            return { ...item, priceWithTax: diff, originalPrice: newFee };
                          }
                          return item;
                        }).filter(Boolean);
                        const filteredTotal = processedItems.reduce(
                          (sum: number, item: any) => sum + (item.priceWithTax || 0), 0
                        );
                        if (processedItems.length === 0) return null;
                        return (
                          <div className="bg-amber-50 rounded-lg p-3 space-y-2">
                            <div className="flex justify-between items-center border-b border-amber-200 pb-2 mb-2">
                              <span className="font-semibold text-amber-800">{pricingPreview.billingByMonth.currentMonth.label}</span>
                              <span className="font-semibold text-amber-800">¥{filteredTotal.toLocaleString()}</span>
                            </div>
                            {processedItems.map((item: any, index: number) => (
                              <div key={index} className="flex justify-between text-sm">
                                <span className="text-gray-700">{item.billingCategoryName || item.productName}</span>
                                <span className="text-gray-800">¥{item.priceWithTax.toLocaleString()}</span>
                              </div>
                            ))}
                          </div>
                        );
                      })()}

                      {/* 翌月分 - 設備費は既存契約より高い場合のみ差額を請求 */}
                      {(() => {
                        const existingFacilityMax = pricingPreview.existingFacilityFee?.maxFee || 0;
                        const processedItems = pricingPreview.billingByMonth.month1.items.map((item: any) => {
                          if (item.itemType === 'facility') {
                            const newFee = item.priceWithTax || 0;
                            if (existingFacilityMax >= newFee) {
                              // 既存の方が高いか同じ場合は表示しない
                              return null;
                            }
                            // 新規の方が高い場合は差額を表示
                            const diff = newFee - existingFacilityMax;
                            return { ...item, priceWithTax: diff, originalPrice: newFee };
                          }
                          return item;
                        }).filter(Boolean);
                        const filteredTotal = processedItems.reduce(
                          (sum: number, item: any) => sum + (item.priceWithTax || 0), 0
                        );
                        if (processedItems.length === 0) return null;
                        return (
                          <div className="bg-green-50 rounded-lg p-3 space-y-2">
                            <div className="flex justify-between items-center border-b border-green-200 pb-2 mb-2">
                              <span className="font-semibold text-green-800">{pricingPreview.billingByMonth.month1.label}</span>
                              <span className="font-semibold text-green-800">¥{filteredTotal.toLocaleString()}</span>
                            </div>
                            {processedItems.map((item: any, index: number) => (
                              <div key={index} className="flex justify-between text-sm">
                                <span className="text-gray-700">{item.billingCategoryName || item.productName}</span>
                                <span className="text-gray-800">¥{item.priceWithTax.toLocaleString()}</span>
                              </div>
                            ))}
                          </div>
                        );
                      })()}

                      {/* 翌々月分 - 設備費は既存契約より高い場合のみ差額を請求 */}
                      {(() => {
                        const existingFacilityMax = pricingPreview.existingFacilityFee?.maxFee || 0;
                        const processedItems = pricingPreview.billingByMonth.month2.items.map((item: any) => {
                          if (item.itemType === 'facility') {
                            const newFee = item.priceWithTax || 0;
                            if (existingFacilityMax >= newFee) {
                              return null;
                            }
                            const diff = newFee - existingFacilityMax;
                            return { ...item, priceWithTax: diff, originalPrice: newFee };
                          }
                          return item;
                        }).filter(Boolean);
                        const filteredTotal = processedItems.reduce(
                          (sum: number, item: any) => sum + (item.priceWithTax || 0), 0
                        );
                        if (processedItems.length === 0) return null;
                        return (
                          <div className="bg-purple-50 rounded-lg p-3 space-y-2">
                            <div className="flex justify-between items-center border-b border-purple-200 pb-2 mb-2">
                              <span className="font-semibold text-purple-800">{pricingPreview.billingByMonth.month2.label}</span>
                              <span className="font-semibold text-purple-800">¥{filteredTotal.toLocaleString()}</span>
                            </div>
                            {processedItems.map((item: any, index: number) => (
                              <div key={index} className="flex justify-between text-sm">
                                <span className="text-gray-700">{item.billingCategoryName || item.productName}</span>
                                <span className="text-gray-800">¥{item.priceWithTax.toLocaleString()}</span>
                              </div>
                            ))}
                          </div>
                        );
                      })()}

                      {/* 3ヶ月目〜（締日後のみ） - 設備費は既存契約より高い場合のみ差額を請求 */}
                      {(() => {
                        if (!pricingPreview.billingByMonth.month3) return null;
                        const existingFacilityMax = pricingPreview.existingFacilityFee?.maxFee || 0;
                        const processedItems = pricingPreview.billingByMonth.month3.items.map((item: any) => {
                          if (item.itemType === 'facility') {
                            const newFee = item.priceWithTax || 0;
                            if (existingFacilityMax >= newFee) {
                              return null;
                            }
                            const diff = newFee - existingFacilityMax;
                            return { ...item, priceWithTax: diff, originalPrice: newFee };
                          }
                          return item;
                        }).filter(Boolean);
                        const filteredTotal = processedItems.reduce(
                          (sum: number, item: any) => sum + (item.priceWithTax || 0), 0
                        );
                        if (processedItems.length === 0) return null;
                        return (
                          <div className="bg-pink-50 rounded-lg p-3 space-y-2">
                            <div className="flex justify-between items-center border-b border-pink-200 pb-2 mb-2">
                              <span className="font-semibold text-pink-800">{pricingPreview.billingByMonth.month3.label}</span>
                              <span className="font-semibold text-pink-800">¥{filteredTotal.toLocaleString()}</span>
                            </div>
                            {processedItems.map((item: any, index: number) => (
                              <div key={index} className="flex justify-between text-sm">
                                <span className="text-gray-700">{item.billingCategoryName || item.productName}</span>
                                <span className="text-gray-800">¥{item.priceWithTax.toLocaleString()}</span>
                              </div>
                            ))}
                          </div>
                        );
                      })()}
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

            {/* 教材選択が必要な場合の警告 */}
            {pricingPreview?.textbookOptions && pricingPreview.textbookOptions.length > 0 && selectedTextbookIds.length === 0 && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200 mb-4">
                <AlertCircle className="h-5 w-5 text-amber-600 shrink-0" />
                <p className="text-sm text-amber-800">教材費の支払い方法を選択してください</p>
              </div>
            )}

            {/* 料金について質問するボタン */}
            <Button
              onClick={saveStateAndGoToChat}
              variant="outline"
              className="w-full h-12 rounded-full border-2 border-gray-300 text-gray-700 font-medium mb-3 flex items-center justify-center gap-2 hover:bg-gray-50"
            >
              <MessageSquare className="h-5 w-5" />
              料金について質問する
            </Button>

            <Button
              onClick={handleConfirmPurchase}
              disabled={
                isConfirming ||
                (itemType === 'regular' && pricingPreview?.textbookOptions && pricingPreview.textbookOptions.length > 0 && selectedTextbookIds.length === 0) ||
                (itemType === 'seminar' && selectedSeminars.length === 0) ||
                (itemType === 'certification' && selectedCertifications.length === 0)
              }
              className={`w-full h-14 rounded-full text-white font-semibold text-lg disabled:opacity-70 ${
                itemType === 'seminar' ? 'bg-purple-600 hover:bg-purple-700' :
                itemType === 'certification' ? 'bg-amber-600 hover:bg-amber-700' :
                'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {isConfirming ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  処理中...
                </span>
              ) : (
                itemType === 'seminar' ? '講習会を申し込む' :
                itemType === 'certification' ? '検定を申し込む' :
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
