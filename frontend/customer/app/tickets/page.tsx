'use client';

import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, Ticket, Calendar, RefreshCw, Clock, Loader2, MapPin, X, ChevronRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getAllStudentItems, type PurchasedItem } from '@/lib/api/students';
import { getAbsenceTickets, getTransferAvailableClasses, useAbsenceTicket, type AbsenceTicket, type TransferAvailableClass } from '@/lib/api/lessons';
import { getBrandSchools, type BrandSchool } from '@/lib/api/schools';
import { format, addDays, startOfWeek, isSameDay, startOfMonth, endOfMonth, eachDayOfInterval, getDay, addMonths, subMonths } from 'date-fns';
import { ja } from 'date-fns/locale';

type TicketType = {
  id: string;
  type: 'course' | 'transfer' | 'event';
  school: string;
  brand: string;
  count: number;
  expiryDate: string;
  status: 'active' | 'expiring';
  studentName?: string;
  productName?: string;
  billingMonth?: string;
  // 振替チケット専用
  absenceDate?: string;
  consumptionSymbol?: string;
  originalTicketName?: string;
  brandId?: string;
  schoolId?: string;
};

// チケットとして表示すべき商品タイプかどうか判定
// 授業料（tuition）のみがチケット対象
// 月会費、教材費、入会金などは購入履歴（通帳）に表示
function isTicketType(productType: string): boolean {
  return productType === 'tuition';
}

// 商品タイプからチケットタイプへの変換（授業料のみ）
function getTicketType(productType: string): 'course' | 'transfer' | 'event' {
  // 授業料はコースチケット（通常）と振替チケットがある
  // ここでは全てコースチケットとして扱う（振替はまた別の仕組みで管理）
  return 'course';
}

// 有効期限計算（請求月の末日から3ヶ月後）
function calculateExpiryDate(billingMonth: string): string {
  const [year, month] = billingMonth.split('-').map(Number);
  const expiry = new Date(year, month + 2, 0); // 3ヶ月後の末日
  return expiry.toISOString().split('T')[0];
}

// 期限間近チェック（30日以内）
function isExpiringSoon(expiryDate: string): boolean {
  const expiry = new Date(expiryDate);
  const now = new Date();
  const diffDays = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  return diffDays <= 30 && diffDays > 0;
}

export default function TicketsPage() {
  const router = useRouter();
  const [tickets, setTickets] = useState<TicketType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 振替予約モーダル用の状態
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [transferStep, setTransferStep] = useState<'school' | 'calendar'>('school');
  const [selectedTicket, setSelectedTicket] = useState<TicketType | null>(null);
  const [schools, setSchools] = useState<BrandSchool[]>([]);
  const [selectedSchool, setSelectedSchool] = useState<BrandSchool | null>(null);
  const [availableClasses, setAvailableClasses] = useState<TransferAvailableClass[]>([]);
  const [loadingSchools, setLoadingSchools] = useState(false);
  const [loadingClasses, setLoadingClasses] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedClass, setSelectedClass] = useState<TransferAvailableClass | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [transferError, setTransferError] = useState<string | null>(null);
  const [transferSuccess, setTransferSuccess] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(() => new Date());

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        setLoading(true);

        // コースチケット（StudentItems）と振替チケット（AbsenceTickets）を並行取得
        const [itemsResponse, absenceTickets] = await Promise.all([
          getAllStudentItems(),
          getAbsenceTickets('issued').catch(() => [] as AbsenceTicket[]), // エラー時は空配列
        ]);

        // 授業料（tuition）のみをチケットとして表示
        // 月会費、教材費、入会金などは購入履歴ページで表示
        const ticketItems = itemsResponse.items.filter((item: PurchasedItem) => isTicketType(item.productType));

        // PurchasedItemをTicketTypeに変換
        const convertedTickets: TicketType[] = ticketItems.map((item: PurchasedItem) => {
          const expiryDate = calculateExpiryDate(item.billingMonth);
          return {
            id: item.id,
            type: getTicketType(item.productType),
            school: item.schoolName || '未指定',
            brand: item.brandName || item.productName,
            count: item.quantity,
            expiryDate,
            status: isExpiringSoon(expiryDate) ? 'expiring' : 'active',
            studentName: item.studentName,
            productName: item.productName,
            billingMonth: item.billingMonth,
          };
        });

        // AbsenceTicketをTicketTypeに変換（振替チケット）
        const transferTicketsConverted: TicketType[] = absenceTickets.map((ticket: AbsenceTicket) => ({
          id: ticket.id,
          type: 'transfer' as const,
          school: ticket.schoolName || '未指定',
          brand: ticket.brandName || '振替チケット',
          count: 1,
          expiryDate: ticket.validUntil || '',
          status: ticket.validUntil && isExpiringSoon(ticket.validUntil) ? 'expiring' : 'active',
          studentName: ticket.studentName,
          productName: ticket.originalTicketName || '振替チケット',
          absenceDate: ticket.absenceDate || undefined,
          consumptionSymbol: ticket.consumptionSymbol,
          originalTicketName: ticket.originalTicketName,
          brandId: ticket.brandId || undefined,
          schoolId: ticket.schoolId || undefined,
        }));

        setTickets([...convertedTickets, ...transferTicketsConverted]);
        setError(null);
      } catch (err: unknown) {
        console.error('Failed to fetch tickets:', err);
        // 401エラーの場合はログインページにリダイレクト
        if (err && typeof err === 'object' && 'message' in err) {
          const errorMessage = (err as { message: string }).message;
          if (errorMessage.includes('401') || errorMessage.includes('認証')) {
            router.push('/login');
            return;
          }
        }
        setError('チケット情報の取得に失敗しました');
      } finally {
        setLoading(false);
      }
    };

    fetchTickets();
  }, [router]);

  // 振替予約モーダルを開く
  const openTransferModal = useCallback(async (ticket: TicketType) => {
    setSelectedTicket(ticket);
    setShowTransferModal(true);
    setTransferStep('school');
    setSelectedSchool(null);
    setSelectedDate(null);
    setSelectedClass(null);
    setTransferError(null);
    setTransferSuccess(false);
    setCurrentMonth(new Date());

    // ブランドの校舎一覧を取得
    if (ticket.brandId) {
      setLoadingSchools(true);
      try {
        const brandSchools = await getBrandSchools(ticket.brandId);
        setSchools(brandSchools);
        // デフォルトで通っている校舎を選択
        if (ticket.schoolId) {
          const currentSchool = brandSchools.find(s => s.id === ticket.schoolId);
          if (currentSchool) {
            setSelectedSchool(currentSchool);
          }
        }
      } catch (err) {
        console.error('Failed to fetch schools:', err);
        setTransferError('校舎情報の取得に失敗しました');
      } finally {
        setLoadingSchools(false);
      }
    }
  }, []);

  // 校舎選択後、カレンダーステップへ
  const goToCalendarStep = useCallback(async () => {
    if (!selectedSchool || !selectedTicket) return;

    setTransferStep('calendar');
    setLoadingClasses(true);
    setTransferError(null);

    try {
      const classes = await getTransferAvailableClasses(selectedTicket.id);
      // 選択した校舎のクラスのみフィルタ
      const filteredClasses = classes.filter(c => c.schoolId === selectedSchool.id);
      setAvailableClasses(filteredClasses);
    } catch (err) {
      console.error('Failed to fetch available classes:', err);
      setTransferError('振替可能クラスの取得に失敗しました');
    } finally {
      setLoadingClasses(false);
    }
  }, [selectedSchool, selectedTicket]);

  // 振替予約を実行
  const submitTransfer = useCallback(async () => {
    if (!selectedTicket || !selectedDate || !selectedClass) return;

    setIsSubmitting(true);
    setTransferError(null);

    try {
      await useAbsenceTicket({
        absenceTicketId: selectedTicket.id,
        targetDate: format(selectedDate, 'yyyy-MM-dd'),
        targetClassScheduleId: selectedClass.id,
      });
      setTransferSuccess(true);
      // チケット一覧を再取得
      const [itemsResponse, absenceTickets] = await Promise.all([
        getAllStudentItems(),
        getAbsenceTickets('issued').catch(() => [] as AbsenceTicket[]),
      ]);
      const ticketItems = itemsResponse.items.filter((item: PurchasedItem) => isTicketType(item.productType));
      const convertedTickets: TicketType[] = ticketItems.map((item: PurchasedItem) => {
        const expiryDate = calculateExpiryDate(item.billingMonth);
        return {
          id: item.id,
          type: getTicketType(item.productType),
          school: item.schoolName || '未指定',
          brand: item.brandName || item.productName,
          count: item.quantity,
          expiryDate,
          status: isExpiringSoon(expiryDate) ? 'expiring' : 'active',
          studentName: item.studentName,
          productName: item.productName,
          billingMonth: item.billingMonth,
        };
      });
      const transferTicketsConverted: TicketType[] = absenceTickets.map((ticket: AbsenceTicket) => ({
        id: ticket.id,
        type: 'transfer' as const,
        school: ticket.schoolName || '未指定',
        brand: ticket.brandName || '振替チケット',
        count: 1,
        expiryDate: ticket.validUntil || '',
        status: ticket.validUntil && isExpiringSoon(ticket.validUntil) ? 'expiring' : 'active',
        studentName: ticket.studentName,
        productName: ticket.originalTicketName || '振替チケット',
        absenceDate: ticket.absenceDate || undefined,
        consumptionSymbol: ticket.consumptionSymbol,
        originalTicketName: ticket.originalTicketName,
        brandId: ticket.brandId || undefined,
        schoolId: ticket.schoolId || undefined,
      }));
      setTickets([...convertedTickets, ...transferTicketsConverted]);
    } catch (err) {
      console.error('Failed to submit transfer:', err);
      const apiError = err as { message?: string };
      setTransferError(apiError.message || '振替予約に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  }, [selectedTicket, selectedDate, selectedClass]);

  // モーダルを閉じる
  const closeTransferModal = useCallback(() => {
    setShowTransferModal(false);
    setSelectedTicket(null);
    setTransferStep('school');
    setSelectedSchool(null);
    setSelectedDate(null);
    setSelectedClass(null);
    setTransferError(null);
    setTransferSuccess(false);
  }, []);

  // 月のカレンダー日付を取得（前月・翌月の日付も含む）
  const getMonthCalendarDays = useCallback(() => {
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(currentMonth);
    const days = eachDayOfInterval({ start: monthStart, end: monthEnd });

    // 月初の曜日に合わせて前月の日付を追加（月曜始まり）
    const startDayOfWeek = getDay(monthStart);
    // 日曜日(0)なら6日分、月曜日(1)なら0日分...を追加
    const prefixDays = startDayOfWeek === 0 ? 6 : startDayOfWeek - 1;

    const prefix: (Date | null)[] = Array(prefixDays).fill(null);

    // 月末の曜日に合わせて翌月の日付を追加
    const endDayOfWeek = getDay(monthEnd);
    // 日曜日(0)なら0日分、月曜日(1)なら6日分...を追加
    const suffixDays = endDayOfWeek === 0 ? 0 : 7 - endDayOfWeek;
    const suffix: (Date | null)[] = Array(suffixDays).fill(null);

    return [...prefix, ...days, ...suffix];
  }, [currentMonth]);

  // 曜日名を取得
  const getDayOfWeekName = (dayOfWeek: number) => {
    const days = ['日', '月', '火', '水', '木', '金', '土'];
    return days[dayOfWeek];
  };

  const courseTickets = tickets.filter(t => t.type === 'course');
  const transferTickets = tickets.filter(t => t.type === 'transfer');
  const eventTickets = tickets.filter(t => t.type === 'event');

  const totalCourse = courseTickets.reduce((sum, t) => sum + t.count, 0);
  const totalTransfer = transferTickets.reduce((sum, t) => sum + t.count, 0);
  const totalEvent = eventTickets.reduce((sum, t) => sum + t.count, 0);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
            <Link href="/" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <h1 className="text-xl font-bold text-gray-800">保有チケット</h1>
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
          <Link href="/" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">保有チケット</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        {error && (
          <Card className="rounded-xl shadow-md bg-red-50 border-red-200 mb-6">
            <CardContent className="p-4">
              <p className="text-red-600 text-sm">{error}</p>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-3 gap-3 mb-6">
          <Card className="rounded-xl shadow-md border-blue-200 bg-blue-50">
            <CardContent className="p-3 text-center">
              <Ticket className="h-6 w-6 text-blue-600 mx-auto mb-1" />
              <p className="text-xs text-gray-600 mb-1">コース</p>
              <p className="text-2xl font-bold text-blue-600">{totalCourse}</p>
              <p className="text-xs text-gray-500">枚</p>
            </CardContent>
          </Card>

          <Card className="rounded-xl shadow-md border-amber-200 bg-amber-50">
            <CardContent className="p-3 text-center">
              <RefreshCw className="h-6 w-6 text-amber-600 mx-auto mb-1" />
              <p className="text-xs text-gray-600 mb-1">振替</p>
              <p className="text-2xl font-bold text-amber-600">{totalTransfer}</p>
              <p className="text-xs text-gray-500">枚</p>
            </CardContent>
          </Card>

          <Card className="rounded-xl shadow-md border-purple-200 bg-purple-50">
            <CardContent className="p-3 text-center">
              <Calendar className="h-6 w-6 text-purple-600 mx-auto mb-1" />
              <p className="text-xs text-gray-600 mb-1">イベント</p>
              <p className="text-2xl font-bold text-purple-600">{totalEvent}</p>
              <p className="text-xs text-gray-500">枚</p>
            </CardContent>
          </Card>
        </div>

        {tickets.length === 0 && !error && (
          <Card className="rounded-xl shadow-md bg-gray-50 border-gray-200 mb-6">
            <CardContent className="p-6 text-center">
              <Ticket className="h-12 w-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-600 font-medium mb-2">まだチケットがありません</p>
              <p className="text-sm text-gray-500">
                チケットを購入すると、ここに表示されます
              </p>
              <Link href="/ticket-purchase" className="inline-block mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium">
                チケットを購入する
              </Link>
            </CardContent>
          </Card>
        )}

        {courseTickets.length > 0 && (
          <section className="mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">コースチケット</h2>
            <div className="space-y-3">
              {courseTickets.map((ticket) => (
                <Card key={ticket.id} className="rounded-xl shadow-md hover:shadow-lg transition-shadow">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className="bg-blue-500 text-white text-xs">
                            {ticket.brand}
                          </Badge>
                          {ticket.status === 'expiring' && (
                            <Badge className="bg-orange-500 text-white text-xs">
                              期限間近
                            </Badge>
                          )}
                        </div>
                        <h3 className="font-semibold text-gray-800 mb-1">{ticket.school}</h3>
                        {ticket.studentName && (
                          <p className="text-xs text-gray-500">{ticket.studentName}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-blue-600">
                          <Ticket className="h-5 w-5" />
                          <span className="text-2xl font-bold">{ticket.count}</span>
                        </div>
                        <p className="text-xs text-gray-500">枚</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Calendar className="h-4 w-4" />
                      <span>有効期限: {ticket.expiryDate}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        {transferTickets.length > 0 && (
          <section className="mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">振替チケット</h2>
            <div className="space-y-3">
              {transferTickets.map((ticket) => (
                <Card key={ticket.id} className="rounded-xl shadow-md hover:shadow-lg transition-shadow border-amber-200">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className="bg-amber-500 text-white text-xs">
                            {ticket.brand}
                          </Badge>
                          <Badge className="bg-purple-500 text-white text-xs">
                            振替専用
                          </Badge>
                          {ticket.consumptionSymbol && (
                            <Badge className="bg-blue-500 text-white text-xs">
                              {ticket.consumptionSymbol}
                            </Badge>
                          )}
                        </div>
                        <h3 className="font-semibold text-gray-800 mb-1">{ticket.school}</h3>
                        {ticket.studentName && (
                          <p className="text-xs text-gray-500">{ticket.studentName}</p>
                        )}
                        {ticket.originalTicketName && (
                          <p className="text-xs text-gray-500">元チケット: {ticket.originalTicketName}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-amber-600">
                          <RefreshCw className="h-5 w-5" />
                          <span className="text-2xl font-bold">{ticket.count}</span>
                        </div>
                        <p className="text-xs text-gray-500">枚</p>
                      </div>
                    </div>
                    {ticket.absenceDate && (
                      <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
                        <Calendar className="h-4 w-4" />
                        <span>欠席日: {ticket.absenceDate}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
                      <Clock className="h-4 w-4" />
                      <span>有効期限: {ticket.expiryDate}</span>
                    </div>
                    <Button
                      onClick={() => openTransferModal(ticket)}
                      className="w-full bg-amber-500 hover:bg-amber-600 text-white"
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      振替予約する
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        {eventTickets.length > 0 && (
          <section className="mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">イベントチケット</h2>
            <div className="space-y-3">
              {eventTickets.map((ticket) => (
                <Card key={ticket.id} className="rounded-xl shadow-md hover:shadow-lg transition-shadow border-purple-200">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className="bg-purple-500 text-white text-xs">
                            {ticket.brand}
                          </Badge>
                        </div>
                        <h3 className="font-semibold text-gray-800 mb-1">{ticket.school}</h3>
                        {ticket.studentName && (
                          <p className="text-xs text-gray-500">{ticket.studentName}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-purple-600">
                          <Calendar className="h-5 w-5" />
                          <span className="text-2xl font-bold">{ticket.count}</span>
                        </div>
                        <p className="text-xs text-gray-500">枚</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Calendar className="h-4 w-4" />
                      <span>有効期限: {ticket.expiryDate}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        <Card className="rounded-xl shadow-md bg-blue-50 border-blue-200">
          <CardContent className="p-4">
            <div className="flex gap-3">
              <Clock className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-blue-900 mb-1">チケットについて</h3>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• コースチケットは授業の予約に使用できます</li>
                  <li>• 振替チケットは欠席した授業の振替に使用できます</li>
                  <li>• イベントチケットは特別イベントに使用できます</li>
                  <li>• 各チケットには有効期限があります</li>
                  <li>• 有効期限が近いチケットから使用されます</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>

      {/* 振替予約モーダル */}
      {showTransferModal && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col">
            {/* ヘッダー */}
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-bold text-gray-800">
                {transferStep === 'school' ? '校舎を選択' : '日時を選択'}
              </h2>
              <button onClick={closeTransferModal} className="p-1 hover:bg-gray-100 rounded-full">
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>

            {/* コンテンツ */}
            <div className="flex-1 overflow-y-auto p-4">
              {transferSuccess ? (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <RefreshCw className="h-8 w-8 text-green-600" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-800 mb-2">振替予約完了</h3>
                  <p className="text-gray-600 mb-4">
                    {selectedDate && format(selectedDate, 'M月d日(E)', { locale: ja })}の授業に振替予約しました
                  </p>
                  <Button onClick={closeTransferModal} className="bg-blue-500 hover:bg-blue-600">
                    閉じる
                  </Button>
                </div>
              ) : transferStep === 'school' ? (
                <>
                  {/* 校舎選択ステップ */}
                  {loadingSchools ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-sm text-gray-600 mb-4">
                        振替先の校舎を選択してください。他校舎への振替も可能です。
                      </p>
                      {schools.map((school) => (
                        <button
                          key={school.id}
                          onClick={() => setSelectedSchool(school)}
                          className={`w-full p-4 rounded-lg border-2 text-left transition-all ${
                            selectedSchool?.id === school.id
                              ? 'border-amber-500 bg-amber-50'
                              : 'border-gray-200 hover:border-amber-300'
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <MapPin className={`h-5 w-5 mt-0.5 ${
                              selectedSchool?.id === school.id ? 'text-amber-500' : 'text-gray-400'
                            }`} />
                            <div className="flex-1">
                              <p className="font-semibold text-gray-800">{school.name}</p>
                              {school.address && (
                                <p className="text-sm text-gray-500 mt-1">{school.address}</p>
                              )}
                              {selectedTicket?.schoolId === school.id && (
                                <Badge className="mt-2 bg-blue-500 text-white text-xs">通常校舎</Badge>
                              )}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <>
                  {/* カレンダーステップ */}
                  {loadingClasses ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* 選択中の校舎表示 */}
                      <div className="flex items-center gap-2 p-2 bg-amber-50 rounded-lg">
                        <MapPin className="h-4 w-4 text-amber-600" />
                        <span className="text-sm font-medium text-amber-800">{selectedSchool?.name}</span>
                      </div>

                      {/* 注意事項 */}
                      <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <p className="text-sm text-blue-700">
                          <Clock className="h-4 w-4 inline-block mr-1 -mt-0.5" />
                          当日の振替予約は<span className="font-semibold">授業開始30分前まで</span>となります。
                        </p>
                      </div>

                      {/* 月間カレンダー */}
                      <div className="bg-white rounded-xl border shadow-sm p-4">
                        <div className="flex items-center justify-between mb-4">
                          <button
                            onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
                            className="p-2 hover:bg-gray-100 rounded-lg"
                          >
                            <ChevronLeft className="h-5 w-5" />
                          </button>
                          <span className="font-semibold text-lg">
                            {format(currentMonth, 'yyyy年M月', { locale: ja })}
                          </span>
                          <button
                            onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
                            className="p-2 hover:bg-gray-100 rounded-lg"
                          >
                            <ChevronRight className="h-5 w-5" />
                          </button>
                        </div>

                        <div className="grid grid-cols-7 gap-1 text-center text-sm mb-2">
                          {['日', '月', '火', '水', '木', '金', '土'].map((day, i) => (
                            <div key={day} className={`py-1 font-semibold ${
                              i === 0 ? 'text-red-500' : i === 6 ? 'text-blue-500' : 'text-gray-600'
                            }`}>
                              {day}
                            </div>
                          ))}
                        </div>

                        <div className="grid grid-cols-7 gap-1">
                          {(() => {
                            // 日曜始まりのカレンダーを生成
                            const monthStart = startOfMonth(currentMonth);
                            const monthEnd = endOfMonth(currentMonth);
                            const days = eachDayOfInterval({ start: monthStart, end: monthEnd });
                            const startDayOfWeek = getDay(monthStart); // 0=日曜
                            const prefix: (Date | null)[] = Array(startDayOfWeek).fill(null);
                            const endDayOfWeek = getDay(monthEnd);
                            const suffixDays = endDayOfWeek === 6 ? 0 : 6 - endDayOfWeek;
                            const suffix: (Date | null)[] = Array(suffixDays).fill(null);
                            const calendarDays = [...prefix, ...days, ...suffix];

                            return calendarDays.map((date, i) => {
                              if (!date) {
                                return <div key={`empty-${i}`} className="aspect-square" />;
                              }

                              const dayOfWeek = date.getDay();
                              const classesOnDay = availableClasses.filter(c => c.dayOfWeek === dayOfWeek);
                              const hasAvailable = classesOnDay.some(c => c.availableSeats > 0);
                              const isSelected = selectedDate && isSameDay(date, selectedDate);
                              const isPast = date < new Date(new Date().setHours(0, 0, 0, 0));
                              const isCurrentMonth = date.getMonth() === currentMonth.getMonth();
                              const colIndex = i % 7; // 0=日, 6=土

                              return (
                                <button
                                  key={date.toISOString()}
                                  onClick={() => {
                                    if (!isPast && hasAvailable && isCurrentMonth) {
                                      setSelectedDate(date);
                                      setSelectedClass(null);
                                    }
                                  }}
                                  disabled={isPast || !hasAvailable || !isCurrentMonth}
                                  className={`aspect-square flex items-center justify-center rounded-lg text-sm transition-all ${
                                    isSelected
                                      ? 'bg-amber-500 text-white font-bold'
                                      : !isCurrentMonth
                                      ? 'text-gray-200'
                                      : isPast
                                      ? 'text-gray-300'
                                      : hasAvailable
                                      ? 'hover:bg-amber-100 text-gray-800 font-medium bg-amber-50'
                                      : 'text-gray-300'
                                  } ${colIndex === 0 && !isSelected && isCurrentMonth && !isPast ? 'text-red-500' : ''} ${colIndex === 6 && !isSelected && isCurrentMonth && !isPast ? 'text-blue-500' : ''}`}
                                >
                                  {format(date, 'd')}
                                </button>
                              );
                            });
                          })()}
                        </div>
                      </div>

                      {/* 選択日の時間割一覧 */}
                      {selectedDate && (
                        <div className="space-y-3">
                          <h4 className="font-semibold text-gray-700 flex items-center gap-2">
                            <Clock className="h-4 w-4" />
                            {format(selectedDate, 'M月d日(E)', { locale: ja })}の時間割
                          </h4>
                          <div className="space-y-2">
                            {availableClasses
                              .filter(c => c.dayOfWeek === selectedDate.getDay())
                              .sort((a, b) => a.period - b.period)
                              .map((cls) => (
                                <button
                                  key={cls.id}
                                  onClick={() => cls.availableSeats > 0 && setSelectedClass(cls)}
                                  disabled={cls.availableSeats <= 0}
                                  className={`w-full p-4 rounded-xl border-2 text-left transition-all ${
                                    selectedClass?.id === cls.id
                                      ? 'border-amber-500 bg-amber-50 shadow-md'
                                      : cls.availableSeats > 0
                                      ? 'border-gray-200 hover:border-amber-300 hover:shadow-sm bg-white'
                                      : 'border-gray-100 bg-gray-50 cursor-not-allowed opacity-60'
                                  }`}
                                >
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                                        selectedClass?.id === cls.id ? 'bg-amber-500 text-white' : 'bg-gray-100 text-gray-600'
                                      }`}>
                                        <Clock className="h-5 w-5" />
                                      </div>
                                      <div>
                                        <p className="font-semibold text-gray-800">{cls.periodDisplay}</p>
                                        <p className="text-sm text-gray-500">{cls.className}</p>
                                      </div>
                                    </div>
                                    <div className="text-right">
                                      {cls.availableSeats <= 0 ? (
                                        <Badge className="bg-gray-400 text-white">満席</Badge>
                                      ) : cls.availableSeats <= 3 ? (
                                        <Badge className="bg-orange-500 text-white">
                                          残り{cls.availableSeats}席
                                        </Badge>
                                      ) : null}
                                    </div>
                                  </div>
                                </button>
                              ))}
                            {availableClasses.filter(c => c.dayOfWeek === selectedDate.getDay()).length === 0 && (
                              <div className="text-center py-8 bg-gray-50 rounded-xl">
                                <p className="text-gray-500">この日に振替可能な時間割はありません</p>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {!selectedDate && (
                        <div className="text-center py-4">
                          <p className="text-sm text-gray-500">カレンダーから振替希望日を選択してください</p>
                          <p className="text-xs text-gray-400 mt-1">色付きの日が振替可能日です</p>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}

              {transferError && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{transferError}</p>
                </div>
              )}
            </div>

            {/* フッター */}
            {!transferSuccess && (
              <div className="p-4 border-t flex gap-3">
                {transferStep === 'school' ? (
                  <>
                    <Button
                      variant="outline"
                      onClick={closeTransferModal}
                      className="flex-1"
                    >
                      キャンセル
                    </Button>
                    <Button
                      onClick={goToCalendarStep}
                      disabled={!selectedSchool}
                      className="flex-1 bg-amber-500 hover:bg-amber-600"
                    >
                      次へ
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      onClick={() => setTransferStep('school')}
                      className="flex-1"
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      戻る
                    </Button>
                    <Button
                      onClick={submitTransfer}
                      disabled={!selectedClass || isSubmitting}
                      className="flex-1 bg-amber-500 hover:bg-amber-600"
                    >
                      {isSubmitting ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        '振替予約する'
                      )}
                    </Button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <BottomTabBar />
    </div>
  );
}
