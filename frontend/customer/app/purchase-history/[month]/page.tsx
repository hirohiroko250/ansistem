'use client';

import { useState, useMemo } from 'react';
import { ChevronLeft, ChevronRight, MessageCircle, Check, X, Tag, User, Loader2, Star, Gift, Users } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { InquiryDialog } from '../inquiry-dialog';
import Link from 'next/link';
import { format, addMonths, subMonths, parse } from 'date-fns';
import { ja } from 'date-fns/locale';
import { useRouter, useParams } from 'next/navigation';
import { type PurchasedItem, type MileInfo, type FSDiscount } from '@/lib/api/students';
import { usePurchaseHistory } from '@/lib/hooks/use-history';
import { useUser } from '@/lib/hooks/use-user';
import { AuthGuard } from '@/components/auth';

type TicketItem = {
  id: string;
  description: string;
  productType: string;
  originalAmount?: number;
  amount: number;
  checked: boolean;
};

type Ticket = {
  id: string;
  brandName: string;
  purchaseDate: string;
  items: TicketItem[];
  originalTotal?: number;
  discountAmount?: number;
  discountRate?: number;
  finalTotal: number;
};

type StudentGroup = {
  studentId: string;
  studentName: string;
  tickets: Ticket[];
  totalAmount: number;
  totalDiscount: number;
  totalOriginal: number;
};

// マイル計算用の型
type CourseInfo = {
  studentId: string;
  studentName: string;
  courseName: string;
  brandName: string;
  is1000YenPokiri: boolean;  // 1000円ポッキリコースかどうか
  price: number;
};

type MileCalculation = {
  totalCourses: number;           // 全コース数（兄弟合計）
  totalMiles: number;             // 合計マイル数
  effectiveMiles: number;         // 有効マイル数（2コース以上なら-2）
  mileDiscount: number;           // マイル割引額
  courses: CourseInfo[];          // コース詳細
  is1000PokiriDoubleCourse: boolean; // 1000円ポッキリ2コース特例
};

// 生徒ごとのマイル情報
type StudentMileInfo = {
  studentId: string;
  courseCount: number;            // この生徒のコース数
  courses: CourseInfo[];          // この生徒のコース詳細
};

// 1000円ポッキリコースかを判定（商品名に「ポッキリ」「1000円」が含まれる場合）
function is1000YenPokiri(productName: string, price: number): boolean {
  const lowerName = productName.toLowerCase();
  return (
    (lowerName.includes('ポッキリ') || lowerName.includes('ぽっきり')) ||
    (lowerName.includes('1000円') && price <= 1100) ||
    price === 1000 ||
    price === 1100  // 税込み
  );
}

// マイル計算（兄弟合計）
// 授業料1つにつき1マイル（同じコース名でも別カウント）
function calculateMiles(items: PurchasedItem[], billingMonth: string): MileCalculation {
  // 対象月のアイテムのみフィルタ
  const monthItems = items.filter(item => item.billingMonth === billingMonth);

  // 授業料（tuition）をすべてカウント（ユニーク化しない）
  const tuitionItems = monthItems.filter(item => item.productType === 'tuition');

  // コース情報を抽出（各授業料を1マイルとしてカウント）
  const courses: CourseInfo[] = tuitionItems.map(item => ({
    studentId: item.studentId || '',
    studentName: item.studentName || '',
    courseName: item.courseName || item.productName,
    brandName: item.brandName || '',
    is1000YenPokiri: is1000YenPokiri(item.productName, item.unitPrice),
    price: item.unitPrice,
  }));

  const totalCourses = courses.length;

  // 各授業料に1マイル
  const totalMiles = totalCourses;

  // 1000円ポッキリコースのカウント
  const pokiriCourses = courses.filter(c => c.is1000YenPokiri);
  const normalCourses = courses.filter(c => !c.is1000YenPokiri);

  // 特例: 1000円ポッキリのみで2コース以上の場合は500円引き
  const is1000PokiriDoubleCourse = pokiriCourses.length >= 2 && normalCourses.length === 0;

  // 有効マイル数: 2コース以上なら合計マイル数から-2
  let effectiveMiles = 0;
  if (totalCourses >= 2) {
    effectiveMiles = Math.max(0, totalMiles - 2);
  }

  // マイル割引計算
  let mileDiscount = 0;
  if (is1000PokiriDoubleCourse) {
    // 1000円ポッキリ2コース特例: 500円引き
    mileDiscount = 500;
  } else if (effectiveMiles > 0) {
    // 2マイルごとに500円引き
    mileDiscount = Math.floor(effectiveMiles / 2) * 500;
  }

  return {
    totalCourses,
    totalMiles,
    effectiveMiles,
    mileDiscount,
    courses,
    is1000PokiriDoubleCourse,
  };
}

// 生徒ごとのマイル情報を取得
function getStudentMileInfo(mileCalculation: MileCalculation, studentId: string): StudentMileInfo {
  const studentCourses = mileCalculation.courses.filter(c => c.studentId === studentId);
  return {
    studentId,
    courseCount: studentCourses.length,
    courses: studentCourses,
  };
}

// 商品種別の日本語表示
function getProductTypeName(productType: string): string {
  switch (productType) {
    case 'tuition': return '授業料';
    case 'monthly_fee': return '月会費';
    case 'textbook': return '教材費';
    case 'enrollment': return '入会金';
    case 'facility': return '設備費';
    case 'expense': return '諸経費';
    default: return 'その他';
  }
}

// PurchasedItemからStudentGroupに変換
function convertToStudentGroups(items: PurchasedItem[], billingMonth: string): StudentGroup[] {
  // 対象月のアイテムのみフィルタ
  const monthItems = items.filter(item => item.billingMonth === billingMonth);

  // 生徒ごとにグループ化
  const studentMap = new Map<string, {
    studentId: string;
    studentName: string;
    items: PurchasedItem[];
  }>();

  monthItems.forEach(item => {
    const studentId = item.studentId || 'unknown';
    const studentName = item.studentName || '未指定';

    if (!studentMap.has(studentId)) {
      studentMap.set(studentId, {
        studentId,
        studentName,
        items: [],
      });
    }
    studentMap.get(studentId)!.items.push(item);
  });

  // StudentGroup形式に変換
  const studentGroups: StudentGroup[] = [];

  studentMap.forEach(({ studentId, studentName, items: studentItems }) => {
    // 設備費の重複排除: 生徒ごとに最高額の設備費のみを有効にする
    const facilityItems = studentItems.filter(item => item.productType === 'facility');
    const highestFacility = facilityItems.length > 0
      ? facilityItems.reduce((max, item) => item.finalPrice > max.finalPrice ? item : max, facilityItems[0])
      : null;
    const excludedFacilityIds = new Set(
      facilityItems
        .filter(item => highestFacility && item.id !== highestFacility.id)
        .map(item => item.id)
    );

    // 除外された設備費を除いたアイテムリスト
    const filteredItems = studentItems.filter(item => !excludedFacilityIds.has(item.id));

    // ブランドごとにグループ化
    const brandMap = new Map<string, PurchasedItem[]>();
    filteredItems.forEach(item => {
      const brandKey = item.brandName || item.productName;
      if (!brandMap.has(brandKey)) {
        brandMap.set(brandKey, []);
      }
      brandMap.get(brandKey)!.push(item);
    });

    const tickets: Ticket[] = [];
    let totalAmount = 0;
    let totalDiscount = 0;
    let totalOriginal = 0;

    brandMap.forEach((brandItems, brandName) => {
      const ticketItems: TicketItem[] = brandItems.map(item => ({
        id: item.id,
        description: getProductTypeName(item.productType),
        productType: item.productType,
        amount: item.finalPrice,
        originalAmount: item.discountAmount > 0 ? item.unitPrice * item.quantity : undefined,
        checked: true,
      }));

      const ticketTotal = ticketItems.reduce((sum, t) => sum + t.amount, 0);
      const ticketOriginal = ticketItems.reduce((sum, t) => sum + (t.originalAmount || t.amount), 0);
      const ticketDiscount = ticketOriginal - ticketTotal;

      tickets.push({
        id: `${studentId}-${brandName}`,
        brandName,
        purchaseDate: brandItems[0].createdAt ? format(new Date(brandItems[0].createdAt), 'yyyy/MM/dd') : billingMonth,
        items: ticketItems,
        originalTotal: ticketDiscount > 0 ? ticketOriginal : undefined,
        discountAmount: ticketDiscount > 0 ? ticketDiscount : undefined,
        discountRate: ticketDiscount > 0 ? Math.round((ticketDiscount / ticketOriginal) * 100) : undefined,
        finalTotal: ticketTotal,
      });

      totalAmount += ticketTotal;
      totalDiscount += ticketDiscount;
      totalOriginal += ticketOriginal;
    });

    studentGroups.push({
      studentId,
      studentName,
      tickets,
      totalAmount,
      totalDiscount,
      totalOriginal,
    });
  });

  return studentGroups;
}

function PassbookDetailContent() {
  const router = useRouter();
  const params = useParams();
  const monthParam = params.month as string; // Format: YYYY-MM

  // URLパラメータから日付を取得
  const currentDate = useMemo(() => {
    if (monthParam) {
      try {
        return parse(monthParam, 'yyyy-MM', new Date());
      } catch {
        return new Date();
      }
    }
    return new Date();
  }, [monthParam]);

  // React Queryフックを使用
  const { data: purchaseData, isLoading: purchaseLoading, error: purchaseError } = usePurchaseHistory(monthParam);
  const { data: profile } = useUser();

  const allItems = purchaseData?.items || [];
  const mileInfo: MileInfo = purchaseData?.mileInfo || { balance: 0, potentialDiscount: 0 };
  const fsDiscounts: FSDiscount[] = purchaseData?.fsDiscounts || [];

  const loading = purchaseLoading;
  const error = purchaseError ? '購入履歴の取得に失敗しました' : null;

  const [inquiryDialog, setInquiryDialog] = useState<{
    open: boolean;
    studentName: string;
    brandName: string;
    itemDescription: string;
    itemAmount: number;
  }>({
    open: false,
    studentName: '',
    brandName: '',
    itemDescription: '',
    itemAmount: 0,
  });

  const monthKey = format(currentDate, 'yyyy-MM');
  const studentGroups = convertToStudentGroups(allItems, monthKey);
  const mileCalculation = calculateMiles(allItems, monthKey);

  const totalAmount = studentGroups.reduce((sum, group) => sum + group.totalAmount, 0);
  const totalDiscount = studentGroups.reduce((sum, group) => sum + group.totalDiscount, 0);
  const totalOriginal = studentGroups.reduce((sum, group) => sum + group.totalOriginal, 0);

  // FS割引の合計額を計算
  const totalFsDiscount = fsDiscounts.reduce((sum, fs) => sum + fs.discountValue, 0);

  // マイル割引額（APIから取得した値を使用、なければローカル計算）
  const mileDiscount = mileInfo.potentialDiscount > 0 ? mileInfo.potentialDiscount : mileCalculation.mileDiscount;

  // 最終金額（商品割引 + マイル割引 + FS割引を適用後）
  const finalAmount = Math.max(0, totalAmount - mileDiscount - totalFsDiscount);

  const handlePrevMonth = () => {
    const prevMonth = subMonths(currentDate, 1);
    router.push(`/purchase-history/${format(prevMonth, 'yyyy-MM')}`);
  };

  const handleNextMonth = () => {
    const nextMonth = addMonths(currentDate, 1);
    router.push(`/purchase-history/${format(nextMonth, 'yyyy-MM')}`);
  };

  const handleOpenInquiry = (studentName: string, brandName: string, itemDescription: string, itemAmount: number) => {
    setInquiryDialog({
      open: true,
      studentName,
      brandName,
      itemDescription,
      itemAmount,
    });
  };

  const handleCloseInquiry = () => {
    setInquiryDialog({
      open: false,
      studentName: '',
      brandName: '',
      itemDescription: '',
      itemAmount: 0,
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
            <Link href="/purchase-history" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <h1 className="text-lg font-bold text-gray-800 flex-1 text-center">購入明細</h1>
            <div className="w-9" />
          </div>
        </header>
        <main className="max-w-[390px] mx-auto px-4 py-6 pb-24 flex items-center justify-center min-h-[50vh]">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-2" />
            <p className="text-gray-500">読み込み中...</p>
          </div>
        </main>
        <BottomTabBar />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/purchase-history" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <div className="flex-1 flex items-center justify-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={handlePrevMonth}
              className="h-8 w-8"
            >
              <ChevronLeft className="h-5 w-5" />
            </Button>
            <h1 className="text-lg font-bold text-gray-800 min-w-[120px] text-center">
              {format(currentDate, 'yyyy年M月', { locale: ja })}
            </h1>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleNextMonth}
              className="h-8 w-8"
            >
              <ChevronRight className="h-5 w-5" />
            </Button>
          </div>
          <div className="w-9" />
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-4 pb-24">
        {error && (
          <Card className="rounded-xl shadow-md bg-red-50 border-red-200 mb-4">
            <CardContent className="p-4">
              <p className="text-red-600 text-sm">{error}</p>
            </CardContent>
          </Card>
        )}

        <Card className="rounded-xl shadow-md mb-4 bg-gradient-to-br from-blue-600 to-blue-700 text-white">
          <CardContent className="p-4">
            <p className="text-xs opacity-90 mb-1">今月のお支払い金額</p>
            <div className="flex items-baseline gap-2">
              <p className="text-2xl font-bold">¥{finalAmount.toLocaleString()}</p>
              {(totalDiscount > 0 || mileDiscount > 0 || totalFsDiscount > 0) && (
                <p className="text-sm opacity-70 line-through">¥{totalOriginal.toLocaleString()}</p>
              )}
            </div>
            {(totalDiscount > 0 || mileDiscount > 0 || totalFsDiscount > 0) && (() => {
              const totalSaved = totalDiscount + mileDiscount + totalFsDiscount;
              const savingsPercent = totalOriginal > 0 ? Math.round((totalSaved / totalOriginal) * 100) : 0;
              return (
                <div className="mt-2 inline-flex items-center gap-1.5 bg-red-500 text-white px-2 py-1 rounded text-xs font-bold">
                  <Tag className="h-3.5 w-3.5" />
                  <span>{savingsPercent}% OFF</span>
                  <span className="opacity-90">（¥{totalSaved.toLocaleString()}お得）</span>
                </div>
              );
            })()}
          </CardContent>
        </Card>

        {/* マイル割引（兄弟割引）カード */}
        {mileDiscount > 0 && (
          <Card className="rounded-xl shadow-md mb-4 overflow-hidden">
            <div className="bg-gradient-to-r from-purple-600 to-purple-700 text-white px-3 py-2.5">
              <div className="flex items-center gap-2">
                <Star className="h-4 w-4" />
                <h2 className="font-bold text-sm">マイル割引（兄弟割引）</h2>
              </div>
              <div className="flex justify-between items-center mt-1.5">
                <span className="text-[10px] opacity-80">割引額</span>
                <div className="text-sm font-bold">
                  -¥{mileDiscount.toLocaleString()}
                </div>
              </div>
            </div>

            <div className="bg-white">
              <div className="bg-purple-50 px-3 py-2 flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Gift className="h-4 w-4 text-purple-600" />
                    <h3 className="font-semibold text-xs text-purple-900">兄弟割引</h3>
                  </div>
                  <div className="text-[10px] text-gray-600 mt-0.5">
                    {mileInfo.balance > 0
                      ? `${mileInfo.balance}マイル保有中`
                      : `${mileCalculation.totalCourses}コース受講中 → ${mileCalculation.effectiveMiles}マイル獲得`}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-purple-900">
                    -¥{mileDiscount.toLocaleString()}
                  </div>
                </div>
              </div>

              <div className="px-3 py-2 border-t border-gray-100">
                <div className="flex items-center justify-between">
                  <div className="text-xs text-gray-700">
                    {mileInfo.balance > 0
                      ? `マイル割引（${mileInfo.balance}マイル）`
                      : mileCalculation.is1000PokiriDoubleCourse
                        ? '1000円ポッキリ2コース特例'
                        : `マイル割引（${Math.floor(mileCalculation.effectiveMiles / 2)}回 × 500円）`}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-bold text-gray-900 tabular-nums">
                      -¥{mileDiscount.toLocaleString()}
                    </span>
                    <div className="w-5 flex justify-center">
                      <button
                        onClick={() => handleOpenInquiry(
                          profile?.fullName || '保護者',
                          'マイル割引（兄弟割引）',
                          `マイル割引 -¥${mileDiscount.toLocaleString()}`,
                          -mileDiscount
                        )}
                        className="hover:bg-red-100 rounded p-0.5"
                      >
                        <X className="h-3.5 w-3.5 text-red-600" />
                      </button>
                    </div>
                    <button
                      onClick={() => handleOpenInquiry(
                        profile?.fullName || '保護者',
                        'マイル割引（兄弟割引）',
                        `マイル割引 -¥${mileDiscount.toLocaleString()}`,
                        -mileDiscount
                      )}
                      className="hover:bg-blue-100 rounded p-0.5"
                    >
                      <MessageCircle className="h-3.5 w-3.5 text-blue-600" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* FS割引（友達紹介割引）カード */}
        {totalFsDiscount > 0 && (
          <Card className="rounded-xl shadow-md mb-4 overflow-hidden">
            <div className="bg-gradient-to-r from-green-600 to-green-700 text-white px-3 py-2.5">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                <h2 className="font-bold text-sm">友達紹介割引（FS割引）</h2>
              </div>
              <div className="flex justify-between items-center mt-1.5">
                <span className="text-[10px] opacity-80">割引額</span>
                <div className="text-sm font-bold">
                  -¥{totalFsDiscount.toLocaleString()}
                </div>
              </div>
            </div>

            <div className="bg-white divide-y divide-gray-100">
              {fsDiscounts.map((fs) => (
                <div key={fs.id} className="px-3 py-2">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="text-xs text-gray-700">
                        {fs.discountType === 'percent'
                          ? `${fs.discountValue}%割引`
                          : `友達紹介割引`}
                      </div>
                      {(fs.validFrom || fs.validUntil) && (
                        <div className="text-[10px] text-gray-500 mt-0.5">
                          {fs.validFrom && `${fs.validFrom}〜`}
                          {fs.validUntil && `${fs.validUntil}まで`}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-gray-900 tabular-nums">
                        -¥{fs.discountValue.toLocaleString()}
                      </span>
                      <div className="w-5 flex justify-center">
                        <button
                          onClick={() => handleOpenInquiry(
                            profile?.fullName || '保護者',
                            '友達紹介割引（FS割引）',
                            `友達紹介割引 -¥${fs.discountValue.toLocaleString()}`,
                            -fs.discountValue
                          )}
                          className="hover:bg-red-100 rounded p-0.5"
                        >
                          <X className="h-3.5 w-3.5 text-red-600" />
                        </button>
                      </div>
                      <button
                        onClick={() => handleOpenInquiry(
                          profile?.fullName || '保護者',
                          '友達紹介割引（FS割引）',
                          `友達紹介割引 -¥${fs.discountValue.toLocaleString()}`,
                          -fs.discountValue
                        )}
                        className="hover:bg-blue-100 rounded p-0.5"
                      >
                        <MessageCircle className="h-3.5 w-3.5 text-blue-600" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        <div className="space-y-4">
          {studentGroups.length > 0 ? (
            studentGroups.map((studentGroup) => (
              <Card key={studentGroup.studentId} className="rounded-xl shadow-md overflow-hidden">
                <div className="bg-gradient-to-r from-slate-700 to-slate-800 text-white px-3 py-2.5">
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    <h2 className="font-bold text-sm">{studentGroup.studentName}</h2>
                  </div>
                  <div className="flex justify-between items-center mt-1.5">
                    <span className="text-[10px] opacity-80">月額合計</span>
                    <div className="text-right">
                      {studentGroup.totalDiscount > 0 && (
                        <div className="text-[10px] opacity-80 line-through">
                          ¥{studentGroup.totalOriginal.toLocaleString()}
                        </div>
                      )}
                      <div className="text-sm font-bold">
                        ¥{studentGroup.totalAmount.toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="divide-y divide-gray-200">
                  {studentGroup.tickets.map((ticket) => (
                    <div key={ticket.id} className="bg-white">
                      <div className="bg-blue-50 px-3 py-2 flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-xs text-blue-900">{ticket.brandName}</h3>
                            {ticket.discountRate && (
                              <div className="bg-green-500 text-white px-1.5 py-0.5 rounded-full text-[10px] font-bold">
                                {ticket.discountRate}% OFF
                              </div>
                            )}
                          </div>
                          <div className="text-[10px] text-gray-600 mt-0.5">{ticket.purchaseDate}</div>
                        </div>
                        <div className="text-right">
                          {ticket.originalTotal && (
                            <div className="text-[10px] text-gray-500 line-through">
                              ¥{ticket.originalTotal.toLocaleString()}
                            </div>
                          )}
                          <div className="text-sm font-bold text-blue-900">
                            ¥{ticket.finalTotal.toLocaleString()}
                          </div>
                        </div>
                      </div>

                      {ticket.discountAmount && (
                        <div className="bg-green-50 border-l-4 border-green-500 px-3 py-1.5">
                          <div className="flex justify-between items-center text-[10px]">
                            <span className="text-green-700 font-semibold">割引額</span>
                            <div className="flex items-center gap-1.5">
                              <span className="text-green-700 font-bold">-¥{ticket.discountAmount.toLocaleString()}</span>
                              <button
                                onClick={() => handleOpenInquiry(
                                  studentGroup.studentName,
                                  ticket.brandName,
                                  `割引額 -¥${ticket.discountAmount?.toLocaleString()}`,
                                  -(ticket.discountAmount || 0)
                                )}
                                className="hover:bg-red-100 rounded p-0.5"
                              >
                                <X className="h-3.5 w-3.5 text-red-600" />
                              </button>
                              <button
                                onClick={() => handleOpenInquiry(
                                  studentGroup.studentName,
                                  ticket.brandName,
                                  `割引額 -¥${ticket.discountAmount?.toLocaleString()}`,
                                  -(ticket.discountAmount || 0)
                                )}
                                className="hover:bg-blue-100 rounded p-0.5"
                              >
                                <MessageCircle className="h-3.5 w-3.5 text-blue-600" />
                              </button>
                            </div>
                          </div>
                        </div>
                      )}

                      <div className="divide-y divide-gray-100">
                        {ticket.items.map((item) => (
                          <div key={item.id} className="flex items-center px-3 py-2 hover:bg-gray-50">
                            <div className="flex-1 min-w-0 mr-2">
                              <div className="text-xs text-gray-900">{item.description}</div>
                              {item.originalAmount && (
                                <div className="text-[10px] text-gray-500 line-through mt-0.5">
                                  ¥{item.originalAmount.toLocaleString()}
                                </div>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5 shrink-0">
                              <span className="text-xs font-bold text-gray-900 tabular-nums">
                                ¥{item.amount.toLocaleString()}
                              </span>
                              <div className="w-5 flex justify-center">
                                {item.checked ? (
                                  <Check className="h-3.5 w-3.5 text-green-600" />
                                ) : (
                                  <X className="h-3.5 w-3.5 text-red-600" />
                                )}
                              </div>
                              <button
                                onClick={() => handleOpenInquiry(studentGroup.studentName, ticket.brandName, item.description, item.amount)}
                                className="hover:bg-blue-100 rounded p-0.5"
                              >
                                <MessageCircle className="h-3.5 w-3.5 text-blue-600" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            ))
          ) : (
            <Card className="rounded-xl shadow-sm">
              <CardContent className="p-8 text-center text-gray-500 text-sm">
                この月の記録はありません
              </CardContent>
            </Card>
          )}
        </div>

        <div className="mt-4 text-xs text-gray-600 px-2">
          ※ 詳細のご質問は各チケットの明細横のチャットアイコンからお問い合わせください。
        </div>
      </main>

      <InquiryDialog
        open={inquiryDialog.open}
        onClose={handleCloseInquiry}
        brandName={`${inquiryDialog.studentName} - ${inquiryDialog.brandName}`}
        itemDescription={inquiryDialog.itemDescription}
        itemAmount={inquiryDialog.itemAmount}
      />

      <BottomTabBar />
    </div>
  );
}

export default function PassbookDetailPage() {
  return (
    <AuthGuard>
      <PassbookDetailContent />
    </AuthGuard>
  );
}
