'use client';

import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight, X, AlertCircle, RefreshCw, User, ChevronDown, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Calendar } from '@/components/ui/calendar';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { AuthGuard } from '@/components/auth';
import { useRouter } from 'next/navigation';
import { format, startOfMonth, endOfMonth, addMonths, subMonths, getDate, getDaysInMonth, getDay, parseISO } from 'date-fns';
import { ja } from 'date-fns/locale';
import { useStudents } from '@/lib/hooks/use-students';
import { getStudentItems } from '@/lib/api/students';
import { getChildTicketBalance } from '@/lib/api/students';
import { getCalendarEvents, requestMakeup, getMakeupAvailableDates, markAbsenceFromCalendar, getAbsenceTickets, cancelAbsence, cancelMakeup, type AbsenceTicket } from '@/lib/api/lessons';
import { getLessonCalendar, getCalendarSeats, type LessonCalendarDay, type DailySeatInfo } from '@/lib/api/schools';
import type { Child, MakeupAvailableDate, ApiError } from '@/lib/api/types';

type DisplayEvent = {
  id: string;
  date: number;
  fullDate: string;
  title: string;
  time: string;
  color: string;
  status: 'scheduled' | 'confirmed' | 'absent' | 'makeup' | 'completed' | 'cancelled';
  school: string;
  scheduleId: string;
  courseId?: string;
  classScheduleId?: string;  // 欠席登録用
  brandName?: string;
  brandId?: string;  // 休校日取得用
  schoolId?: string;  // 休校日取得用
  calendarPattern?: string;  // カレンダーパターン（例: 1011_AEC_A）
  absenceTicketId?: string;  // 欠席チケットID（APIから取得）
};

// 状態別の色設定（シンプル化：科目ごとの色分けは不要）
// - 受講日（通常）: 青
// - 欠席: ピンク
// - 振替: 紫
// - 休校日: グレー

function CalendarContent() {
  const router = useRouter();
  const [currentDate, setCurrentDate] = useState(new Date());

  // 子ども関連 - React Query使用
  const { data: children = [], isLoading: isLoadingChildren, error: childrenQueryError } = useStudents();
  const [selectedChild, setSelectedChild] = useState<Child | null>(null);
  const [showChildSelector, setShowChildSelector] = useState(false);
  const childrenError = childrenQueryError ? 'お子様情報の取得に失敗しました' : null;

  // イベント関連 state
  const [events, setEvents] = useState<DisplayEvent[]>([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [eventsError, setEventsError] = useState<string | null>(null);

  // 開講カレンダー（休校日）関連 state
  const [lessonCalendar, setLessonCalendar] = useState<LessonCalendarDay[]>([]);
  const [closedDates, setClosedDates] = useState<Set<number>>(new Set());
  const [holidayDates, setHolidayDates] = useState<Map<number, string>>(new Map());

  // 座席状況 state
  const [seatInfo, setSeatInfo] = useState<Map<number, DailySeatInfo>>(new Map());

  // 選択中のイベント
  const [selectedEvent, setSelectedEvent] = useState<DisplayEvent | null>(null);

  // 選択中の日付（カレンダーからのクリック用）
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [showDayEventsDialog, setShowDayEventsDialog] = useState(false);

  // 欠席ダイアログ
  const [showAbsentDialog, setShowAbsentDialog] = useState(false);
  const [isSubmittingAbsent, setIsSubmittingAbsent] = useState(false);
  const [absentError, setAbsentError] = useState<string | null>(null);

  // 振替ダイアログ
  const [showMakeupDialog, setShowMakeupDialog] = useState(false);
  const [makeupDate, setMakeupDate] = useState<Date>();
  const [makeupTicketBalance, setMakeupTicketBalance] = useState<number>(0);
  const [availableDates, setAvailableDates] = useState<MakeupAvailableDate[]>([]);
  const [isLoadingAvailableDates, setIsLoadingAvailableDates] = useState(false);
  const [isSubmittingMakeup, setIsSubmittingMakeup] = useState(false);
  const [makeupError, setMakeupError] = useState<string | null>(null);

  // 欠席チケット（キャンセル用）
  const [absenceTickets, setAbsenceTickets] = useState<AbsenceTicket[]>([]);

  // キャンセル処理
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [showCancelSuccessDialog, setShowCancelSuccessDialog] = useState(false);
  const [cancelSuccessMessage, setCancelSuccessMessage] = useState<string>('');

  // カレンダー計算
  const daysInMonth = getDaysInMonth(currentDate);
  const firstDayOfWeek = getDay(startOfMonth(currentDate));
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const emptyDays = Array.from({ length: firstDayOfWeek }, (_, i) => i);
  const currentMonthStr = format(currentDate, 'yyyy年M月', { locale: ja });

  // 子ども一覧が読み込まれたら最初の子どもを選択
  useEffect(() => {
    if (children.length > 0 && !selectedChild) {
      setSelectedChild(children[0]);
    }
  }, [children, selectedChild]);

  // イベントを取得
  const fetchEvents = useCallback(async () => {
    if (!selectedChild) return;

    setIsLoadingEvents(true);
    setEventsError(null);
    try {
      const from = format(startOfMonth(currentDate), 'yyyy-MM-dd');
      const to = format(endOfMonth(currentDate), 'yyyy-MM-dd');
      const calendarEvents = await getCalendarEvents(selectedChild.id, from, to);

      // CalendarEvent を DisplayEvent に変換
      const displayEvents: DisplayEvent[] = calendarEvents.map((event) => {
        const eventDate = parseISO(event.start);
        const endTime = event.end ? parseISO(event.end) : eventDate;

        let color = 'bg-blue-100 text-blue-700';
        if (event.status === 'cancelled') color = 'bg-gray-100 text-gray-500';
        else if (event.status === 'completed') color = 'bg-green-100 text-green-700';

        return {
          id: event.id,
          date: getDate(eventDate),
          fullDate: event.start,
          title: event.title,
          time: `${format(eventDate, 'HH:mm')}-${format(endTime, 'HH:mm')}`,
          color,
          status: event.status as DisplayEvent['status'],
          school: event.schoolName || '',
          scheduleId: event.id,
          courseId: event.resourceId,
          classScheduleId: event.classScheduleId,
          brandName: event.brandName,
          brandId: event.brandId,
          schoolId: event.schoolId,
          calendarPattern: event.calendarPattern,
          absenceTicketId: event.absenceTicketId,
        };
      });

      setEvents(displayEvents);
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.status === 401) {
        router.push('/login');
        return;
      }
      setEventsError(apiError.message || 'イベントの取得に失敗しました');
    } finally {
      setIsLoadingEvents(false);
    }
  }, [selectedChild, currentDate, router]);

  // 子ども選択または月変更時にイベントを再取得
  useEffect(() => {
    if (selectedChild) {
      fetchEvents();
    }
  }, [selectedChild, currentDate, fetchEvents]);

  // 開講カレンダー（休校日）を取得
  const fetchLessonCalendar = useCallback(async (options: { calendarPattern?: string; brandId?: string; schoolId?: string }) => {
    try {
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth() + 1;

      console.log('[Calendar] fetchLessonCalendar:', { ...options, year, month });
      const calendarData = await getLessonCalendar({
        calendarCode: options.calendarPattern,
        brandId: options.brandId,
        schoolId: options.schoolId,
        year,
        month,
      });
      console.log('[Calendar] API response:', {
        calendarLength: calendarData.calendar?.length,
        closedDays: calendarData.calendar?.filter(d => !d.isOpen).map(d => d.date)
      });
      setLessonCalendar(calendarData.calendar || []);

      // 休校日のセットを作成
      const closed = new Set<number>();
      const holidays = new Map<number, string>();

      (calendarData.calendar || []).forEach(day => {
        const dayNum = parseInt(day.date.split('-')[2], 10);
        if (!day.isOpen) {
          closed.add(dayNum);
        }
        if (day.holidayName) {
          holidays.set(dayNum, day.holidayName);
        }
      });

      setClosedDates(closed);
      setHolidayDates(holidays);

      // 座席状況を取得
      try {
        const seatsData = await getCalendarSeats(options.brandId || '', options.schoolId || '', year, month);
        const seatsMap = new Map<number, DailySeatInfo>();
        (seatsData.days || []).forEach(day => {
          const dayNum = parseInt(day.date.split('-')[2], 10);
          seatsMap.set(dayNum, day);
        });
        setSeatInfo(seatsMap);
      } catch (seatsError) {
        console.error('Failed to fetch seat info:', seatsError);
      }
    } catch (error) {
      console.error('Failed to fetch lesson calendar:', error);
    }
  }, [currentDate]);

  // イベントまたは購入アイテムから休校日を取得
  useEffect(() => {
    const loadLessonCalendar = async () => {
      if (!selectedChild) return;

      console.log('[Calendar] loadLessonCalendar called, events:', events.length);

      // 1. まずイベントからcalendarPatternを取得（最優先）
      const eventWithPattern = events.find(e => e.calendarPattern);
      if (eventWithPattern?.calendarPattern) {
        console.log('[Calendar] Using calendarPattern from event:', eventWithPattern.calendarPattern);
        await fetchLessonCalendar({ calendarPattern: eventWithPattern.calendarPattern });
        return;
      }

      // 2. calendarPatternがなければbrandIdで検索
      const eventWithBrand = events.find(e => e.brandId);
      if (eventWithBrand?.brandId) {
        console.log('[Calendar] Using brandId from event:', eventWithBrand.brandId);
        await fetchLessonCalendar({ brandId: eventWithBrand.brandId, schoolId: eventWithBrand.schoolId });
        return;
      }

      // 3. イベントにない場合は購入アイテムから取得
      try {
        console.log('[Calendar] No event data, trying student items');
        const items = await getStudentItems(selectedChild.id);
        const item = items.find(i => i.brandId);
        if (item?.brandId) {
          console.log('[Calendar] Using brandId from student items:', item.brandId);
          await fetchLessonCalendar({ brandId: item.brandId, schoolId: item.schoolId });
        } else {
          console.log('[Calendar] No valid brandId found');
        }
      } catch (error) {
        console.error('Failed to get student items for calendar:', error);
      }
    };

    loadLessonCalendar();
  }, [selectedChild, currentDate, events, fetchLessonCalendar]);

  // 振替チケット残高を取得
  const fetchTicketBalance = useCallback(async () => {
    if (!selectedChild) return;
    try {
      const balance = await getChildTicketBalance(selectedChild.id);
      setMakeupTicketBalance(balance.totalAvailable);
    } catch {
      setMakeupTicketBalance(0);
    }
  }, [selectedChild]);

  useEffect(() => {
    if (selectedChild) {
      fetchTicketBalance();
    }
  }, [selectedChild, fetchTicketBalance]);

  // 欠席チケット一覧を取得
  const fetchAbsenceTickets = useCallback(async () => {
    try {
      const tickets = await getAbsenceTickets();
      setAbsenceTickets(tickets);
    } catch {
      setAbsenceTickets([]);
    }
  }, []);

  useEffect(() => {
    fetchAbsenceTickets();
  }, [fetchAbsenceTickets]);

  // イベントに対応する欠席チケットを取得するヘルパー（欠席キャンセル用）
  const getAbsenceTicketForEvent = useCallback((event: DisplayEvent): AbsenceTicket | undefined => {
    if (!event.classScheduleId || !event.fullDate) return undefined;
    const eventDate = format(parseISO(event.fullDate), 'yyyy-MM-dd');
    // issuedステータスのチケットを探す（欠席キャンセル用）
    return absenceTickets.find(
      t => t.classScheduleId === event.classScheduleId &&
           t.absenceDate === eventDate &&
           t.status === 'issued'
    );
  }, [absenceTickets]);

  const getEventsForDay = (day: number) => {
    return events.filter((event) => event.date === day);
  };

  const handleEventClick = (event: DisplayEvent) => {
    setSelectedEvent(event);
    setCancelError(null);
    setAbsentError(null);
  };

  // カレンダーの日付クリック（授業がある日のみ）
  const handleDayClick = (day: number) => {
    const dayEvents = getEventsForDay(day);
    if (dayEvents.length > 0) {
      setSelectedDay(day);
      setShowDayEventsDialog(true);
    }
  };

  // 日付ダイアログから欠席登録
  const handleAbsentFromDayDialog = (event: DisplayEvent) => {
    setShowDayEventsDialog(false);
    setSelectedEvent(event);
    setCancelError(null);
    setAbsentError(null);
  };

  // 欠席登録（振替チケット自動発行）
  const handleMarkAbsent = async () => {
    if (!selectedEvent || !selectedChild) return;

    // classScheduleIdがない場合は欠席登録できない
    if (!selectedEvent.classScheduleId) {
      setAbsentError('この授業は欠席登録に対応していません');
      return;
    }

    setIsSubmittingAbsent(true);
    setAbsentError(null);

    try {
      // 新しいAPIを使用（振替チケットも自動発行）
      const result = await markAbsenceFromCalendar({
        studentId: selectedChild.id,
        lessonDate: format(parseISO(selectedEvent.fullDate), 'yyyy-MM-dd'),
        classScheduleId: selectedEvent.classScheduleId,
        reason: '保護者からの欠席連絡',
      });

      setSelectedEvent(null);
      setShowAbsentDialog(true);

      // イベントを再取得
      await fetchEvents();
      // チケット残高も再取得
      await fetchTicketBalance();
    } catch (err) {
      const apiError = err as ApiError;
      setAbsentError(apiError.message || '欠席登録に失敗しました');
    } finally {
      setIsSubmittingAbsent(false);
    }
  };

  // 振替ダイアログを開く
  const handleOpenMakeupDialog = async () => {
    if (!selectedEvent) return;

    setShowMakeupDialog(true);
    setMakeupError(null);
    setIsLoadingAvailableDates(true);

    try {
      // 振替可能日を取得
      if (selectedEvent.courseId) {
        const dates = await getMakeupAvailableDates(
          selectedEvent.courseId,
          undefined,
          format(new Date(), 'yyyy-MM-dd'),
          format(addMonths(new Date(), 2), 'yyyy-MM-dd')
        );
        setAvailableDates(dates);
      }
    } catch (err) {
      const apiError = err as ApiError;
      setMakeupError(apiError.message || '振替可能日の取得に失敗しました');
    } finally {
      setIsLoadingAvailableDates(false);
    }
  };

  // 振替申請
  const handleRequestMakeup = async () => {
    if (!selectedEvent || !makeupDate || !selectedChild) return;

    setIsSubmittingMakeup(true);
    setMakeupError(null);

    try {
      await requestMakeup({
        originalScheduleId: selectedEvent.scheduleId,
        studentId: selectedChild.id,
        preferredDate: format(makeupDate, 'yyyy-MM-dd'),
        reason: '振替希望',
      });

      setSelectedEvent(null);
      setShowMakeupDialog(false);
      setMakeupDate(undefined);

      // イベントを再取得
      await fetchEvents();
      await fetchTicketBalance();
    } catch (err) {
      const apiError = err as ApiError;
      setMakeupError(apiError.message || '振替申請に失敗しました');
    } finally {
      setIsSubmittingMakeup(false);
    }
  };

  // 欠席キャンセル
  const handleCancelAbsence = async () => {
    if (!selectedEvent) return;

    // イベントから直接absenceTicketIdを使用
    if (!selectedEvent.absenceTicketId) {
      setCancelError('欠席チケットが見つかりません');
      return;
    }

    setIsCancelling(true);
    setCancelError(null);

    try {
      await cancelAbsence(selectedEvent.absenceTicketId);
      setSelectedEvent(null);
      setCancelSuccessMessage('欠席をキャンセルしました');
      setShowCancelSuccessDialog(true);

      // データを再取得
      await Promise.all([fetchEvents(), fetchAbsenceTickets(), fetchTicketBalance()]);
    } catch (err) {
      const apiError = err as ApiError;
      setCancelError(apiError.message || '欠席キャンセルに失敗しました');
    } finally {
      setIsCancelling(false);
    }
  };

  // 振替キャンセル
  const handleCancelMakeup = async () => {
    if (!selectedEvent) return;

    // 振替のイベントから欠席チケット（used状態）を探す
    // usedDateが振替先の日付と一致するチケットを検索
    const eventDate = format(parseISO(selectedEvent.fullDate), 'yyyy-MM-dd');
    const ticket = absenceTickets.find(
      t => t.status === 'used' && t.usedDate === eventDate
    );

    if (!ticket) {
      setCancelError('振替チケットが見つかりません');
      return;
    }

    setIsCancelling(true);
    setCancelError(null);

    try {
      await cancelMakeup(ticket.id);
      setSelectedEvent(null);
      setCancelSuccessMessage('振替をキャンセルしました。欠席チケットが復活しました。');
      setShowCancelSuccessDialog(true);

      // データを再取得
      await Promise.all([fetchEvents(), fetchAbsenceTickets(), fetchTicketBalance()]);
    } catch (err) {
      const apiError = err as ApiError;
      setCancelError(apiError.message || '振替キャンセルに失敗しました');
    } finally {
      setIsCancelling(false);
    }
  };

  const handlePrevMonth = () => {
    setCurrentDate(subMonths(currentDate, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(addMonths(currentDate, 1));
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'scheduled':
      case 'confirmed':
        return <Badge className="bg-green-500 text-white">予約済</Badge>;
      case 'absent':
        return <Badge className="bg-red-500 text-white">欠席</Badge>;
      case 'makeup':
        return <Badge className="bg-purple-500 text-white">振替</Badge>;
      case 'completed':
        return <Badge className="bg-blue-500 text-white">完了</Badge>;
      case 'cancelled':
        return <Badge className="bg-gray-400 text-white">キャンセル</Badge>;
      default:
        return null;
    }
  };

  // 初期ローディング
  if (isLoadingChildren) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <div className="flex flex-col items-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-3" />
          <p className="text-sm text-gray-600">読み込み中...</p>
        </div>
      </div>
    );
  }

  // エラー表示
  if (childrenError) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center px-4">
        <div className="flex flex-col items-center">
          <div className="flex items-center gap-2 p-4 rounded-lg bg-red-50 border border-red-200 mb-4">
            <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
            <p className="text-sm text-red-800">{childrenError}</p>
          </div>
          <Button onClick={() => window.location.reload()} variant="outline">
            再読み込み
          </Button>
        </div>
      </div>
    );
  }

  // 子どもがいない場合
  if (children.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
            <h1 className="text-xl font-bold text-blue-600">Calendar</h1>
          </div>
        </header>
        <main className="max-w-[390px] mx-auto px-4 py-6 pb-24 flex flex-col items-center justify-center min-h-[60vh]">
          <p className="text-gray-600 mb-4">登録されているお子様がいません</p>
          <Button onClick={() => router.push('/children')}>お子様を登録する</Button>
        </main>
        <BottomTabBar />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-blue-600">Calendar</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        {/* 子ども選択 */}
        <Card
          className="rounded-xl shadow-md mb-4 cursor-pointer hover:shadow-lg transition-shadow"
          onClick={() => setShowChildSelector(!showChildSelector)}
        >
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <User className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs text-gray-600">表示中</p>
                  <p className="font-semibold text-gray-800">
                    {selectedChild?.fullName} {selectedChild?.grade && `(${selectedChild.grade})`}
                  </p>
                </div>
              </div>
              <ChevronDown className={`h-5 w-5 text-gray-600 transition-transform ${showChildSelector ? 'rotate-180' : ''}`} />
            </div>
          </CardContent>
        </Card>

        {showChildSelector && (
          <Card className="rounded-xl shadow-md mb-4">
            <CardContent className="p-3">
              <div className="space-y-2">
                {children.map((child) => (
                  <button
                    key={child.id}
                    onClick={() => {
                      setSelectedChild(child);
                      setShowChildSelector(false);
                    }}
                    className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${selectedChild?.id === child.id ? 'bg-blue-50 border-2 border-blue-500' : 'hover:bg-gray-50'
                      }`}
                  >
                    <div className={`w-8 h-8 ${selectedChild?.id === child.id ? 'bg-blue-500' : 'bg-gray-200'} rounded-full flex items-center justify-center`}>
                      <User className={`h-4 w-4 ${selectedChild?.id === child.id ? 'text-white' : 'text-gray-600'}`} />
                    </div>
                    <div className="flex-1 text-left">
                      <p className={`font-semibold ${selectedChild?.id === child.id ? 'text-blue-600' : 'text-gray-800'}`}>
                        {child.fullName} {child.grade && `(${child.grade})`}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* カレンダー */}
        <Card className="rounded-xl shadow-md mb-6">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-4">
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handlePrevMonth}>
                <ChevronLeft className="h-5 w-5" />
              </Button>
              <h2 className="text-lg font-semibold text-gray-800">{currentMonthStr}</h2>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleNextMonth}>
                <ChevronRight className="h-5 w-5" />
              </Button>
            </div>

            <div className="grid grid-cols-7 gap-1 mb-2">
              {['日', '月', '火', '水', '木', '金', '土'].map((day) => (
                <div key={day} className="text-center text-xs font-semibold text-gray-600 py-2">
                  {day}
                </div>
              ))}
            </div>

            {isLoadingEvents ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
              </div>
            ) : (
              <div className="grid grid-cols-7 gap-1">
                {emptyDays.map((_, index) => (
                  <div key={`empty-${index}`} className="aspect-square" />
                ))}
                {days.map((day) => {
                  const dayEvents = getEventsForDay(day);
                  const hasEvents = dayEvents.length > 0;
                  const hasAbsent = dayEvents.some(e => e.status === 'absent');
                  const hasMakeup = dayEvents.some(e => e.status === 'makeup');
                  const hasScheduled = dayEvents.some(e => e.status === 'scheduled' || e.status === 'confirmed');
                  const isClosed = closedDates.has(day);
                  const holidayName = holidayDates.get(day);
                  const seats = seatInfo.get(day);

                  return (
                    <div
                      key={day}
                      onClick={() => handleDayClick(day)}
                      className={`aspect-square flex flex-col items-center justify-center rounded-lg text-sm ${isClosed ? 'bg-gray-200 text-gray-500' :
                        hasAbsent ? 'bg-pink-400 text-white font-semibold' :
                          hasMakeup ? 'bg-purple-500 text-white font-semibold' :
                            hasScheduled || hasEvents ? 'bg-blue-500 text-white font-semibold' :
                              'text-gray-700 hover:bg-gray-100'
                        } ${hasEvents && !isClosed ? 'cursor-pointer hover:opacity-80' : 'cursor-default'} transition-colors relative`}
                      title={holidayName || (isClosed ? '休校日' : seats?.isOpen ? `受講${seats.enrolledCount}人 / 残${seats.availableSeats}席` : undefined)}
                    >
                      <span className="text-xs">{day}</span>
                      {seats?.isOpen && seats.totalCapacity > 0 && !isClosed && (
                        <span className={`text-[8px] leading-none ${hasEvents ? 'text-white/80' : seats.availableSeats <= 2 ? 'text-red-500' : 'text-green-600'}`}>
                          {seats.enrolledCount}/{seats.totalCapacity}
                        </span>
                      )}
                      {hasEvents && !isClosed && (
                        <div className="flex gap-0.5 mt-0.5">
                          {dayEvents.slice(0, 3).map((_, i) => (
                            <div key={i} className="w-1 h-1 rounded-full bg-current opacity-70" />
                          ))}
                        </div>
                      )}
                      {isClosed && (
                        <div className="absolute bottom-0.5 w-4 h-0.5 bg-gray-400 rounded" />
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* カレンダー凡例 */}
        <div className="flex flex-wrap gap-4 mb-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-blue-500" />
            <span className="text-gray-600">受講日</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-pink-400" />
            <span className="text-gray-600">欠席</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-purple-500" />
            <span className="text-gray-600">振替</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-gray-200" />
            <span className="text-gray-600">休校日</span>
          </div>
        </div>

        {/* エラー表示 */}
        {eventsError && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 mb-4">
            <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
            <p className="text-sm text-red-800">{eventsError}</p>
          </div>
        )}

        {/* 今月の予定一覧 */}
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-3">今月の予定</h3>
          {isLoadingEvents ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
            </div>
          ) : events.length === 0 ? (
            <Card className="rounded-xl shadow-md">
              <CardContent className="p-4 text-center">
                <p className="text-sm text-gray-500">今月の予定はありません</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {events
                .sort((a, b) => a.date - b.date)
                .map((event) => (
                  <Card
                    key={event.id}
                    className="rounded-xl shadow-md cursor-pointer hover:shadow-lg transition-shadow"
                    onClick={() => handleEventClick(event)}
                  >
                    <CardContent className="p-3 flex items-center gap-3">
                      <div className="text-center">
                        <div className="text-xl font-bold text-gray-800">{event.date}</div>
                        <div className="text-xs text-gray-500">{format(currentDate, 'M月', { locale: ja })}</div>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-gray-800">{event.title}</h4>
                          {event.brandName && (
                            <Badge className="bg-blue-100 text-blue-700 text-xs px-1.5 py-0.5">{event.brandName}</Badge>
                          )}
                        </div>
                        <p className="text-sm text-gray-600">{event.time}</p>
                        <p className="text-xs text-gray-500">{event.school}</p>
                      </div>
                      {getStatusBadge(event.status)}
                    </CardContent>
                  </Card>
                ))}
            </div>
          )}
        </div>
      </main>

      {/* 日付クリック時のイベント一覧ダイアログ */}
      <Dialog open={showDayEventsDialog} onOpenChange={setShowDayEventsDialog}>
        <DialogContent className="max-w-[340px] rounded-2xl">
          <DialogHeader>
            <DialogTitle>
              {format(currentDate, 'M月', { locale: ja })}{selectedDay}日の予定
            </DialogTitle>
            <DialogDescription>
              授業を選択して欠席登録ができます
            </DialogDescription>
          </DialogHeader>
          {selectedDay && (
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {getEventsForDay(selectedDay).map((event) => (
                <Card
                  key={event.id}
                  className={`cursor-pointer transition-all hover:shadow-md ${event.status === 'absent' ? 'bg-pink-50 border-pink-200' :
                    event.status === 'makeup' ? 'bg-purple-50 border-purple-200' :
                      'hover:bg-gray-50'
                    }`}
                  onClick={() => handleAbsentFromDayDialog(event)}
                >
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-semibold text-sm text-gray-800">{event.title}</p>
                          {event.brandName && (
                            <Badge className="bg-blue-100 text-blue-700 text-xs px-1.5 py-0">{event.brandName}</Badge>
                          )}
                        </div>
                        <p className="text-xs text-gray-600">{event.time}</p>
                        <p className="text-xs text-gray-500">{event.school}</p>
                      </div>
                      <div className="ml-2">
                        {getStatusBadge(event.status)}
                      </div>
                    </div>
                    {(event.status === 'scheduled' || event.status === 'confirmed') && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <p className="text-xs text-blue-600">タップして欠席登録</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
          <Button
            variant="outline"
            className="w-full rounded-xl"
            onClick={() => setShowDayEventsDialog(false)}
          >
            閉じる
          </Button>
        </DialogContent>
      </Dialog>

      {/* イベント詳細ダイアログ */}
      <Dialog open={selectedEvent !== null} onOpenChange={() => setSelectedEvent(null)}>
        <DialogContent className="max-w-[340px] rounded-2xl">
          <DialogHeader>
            <DialogTitle>授業の詳細</DialogTitle>
          </DialogHeader>
          {selectedEvent && (
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-600 mb-1">日時</p>
                <p className="font-semibold text-gray-800">
                  {format(currentDate, 'yyyy年M月', { locale: ja })} {selectedEvent.date}日 {selectedEvent.time}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">授業名</p>
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-gray-800">{selectedEvent.title}</p>
                  {selectedEvent.brandName && (
                    <Badge className="bg-blue-100 text-blue-700 text-xs">{selectedEvent.brandName}</Badge>
                  )}
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">教室</p>
                <p className="font-semibold text-gray-800">{selectedEvent.school || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">ステータス</p>
                {getStatusBadge(selectedEvent.status)}
              </div>

              {absentError && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
                  <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                  <p className="text-sm text-red-800">{absentError}</p>
                </div>
              )}

              {cancelError && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
                  <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
                  <p className="text-sm text-red-800">{cancelError}</p>
                </div>
              )}

              {/* 予約済み：欠席登録ボタン */}
              {(selectedEvent.status === 'scheduled' || selectedEvent.status === 'confirmed') && (
                <div className="pt-2">
                  <Button
                    variant="outline"
                    className="w-full rounded-xl"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleMarkAbsent();
                    }}
                    disabled={isSubmittingAbsent}
                  >
                    {isSubmittingAbsent ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <X className="h-4 w-4 mr-2" />
                    )}
                    欠席登録
                  </Button>
                </div>
              )}

              {/* 欠席：欠席キャンセルボタン */}
              {selectedEvent.status === 'absent' && (
                <div className="pt-2 space-y-2">
                  <p className="text-xs text-gray-500">
                    欠席をキャンセルすると、発行された振替チケットも取り消されます。
                  </p>
                  <Button
                    variant="outline"
                    className="w-full rounded-xl border-red-300 text-red-600 hover:bg-red-50"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCancelAbsence();
                    }}
                    disabled={isCancelling}
                  >
                    {isCancelling ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <X className="h-4 w-4 mr-2" />
                    )}
                    欠席をキャンセル
                  </Button>
                </div>
              )}

              {/* 振替：振替キャンセルボタン */}
              {selectedEvent.status === 'makeup' && (
                <div className="pt-2 space-y-2">
                  <p className="text-xs text-gray-500">
                    振替をキャンセルすると、使用した振替チケットが復活します。
                  </p>
                  <Button
                    variant="outline"
                    className="w-full rounded-xl border-purple-300 text-purple-600 hover:bg-purple-50"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCancelMakeup();
                    }}
                    disabled={isCancelling}
                  >
                    {isCancelling ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <X className="h-4 w-4 mr-2" />
                    )}
                    振替をキャンセル
                  </Button>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 欠席登録完了ダイアログ */}
      <Dialog open={showAbsentDialog} onOpenChange={setShowAbsentDialog}>
        <DialogContent className="max-w-[340px] rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-green-600" />
              <DialogTitle>欠席登録完了</DialogTitle>
            </div>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-gray-700">
              欠席登録が完了しました。
            </p>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 border border-blue-200">
              <RefreshCw className="h-5 w-5 text-blue-600 shrink-0" />
              <p className="text-sm text-blue-800">
                振替チケット1枚が発行されました。チケット画面から確認できます。
              </p>
            </div>
          </div>
          <Button
            className="w-full rounded-xl bg-blue-600 hover:bg-blue-700"
            onClick={() => setShowAbsentDialog(false)}
          >
            閉じる
          </Button>
        </DialogContent>
      </Dialog>

      {/* 振替申請ダイアログ */}
      <Dialog open={showMakeupDialog} onOpenChange={setShowMakeupDialog}>
        <DialogContent className="max-w-[340px] rounded-2xl">
          <DialogHeader>
            <DialogTitle>振替授業の日程選択</DialogTitle>
            <DialogDescription>
              振替授業の希望日を選択してください。振替チケット1枚を使用します。
            </DialogDescription>
          </DialogHeader>

          <Card className="rounded-xl bg-blue-50 border-blue-200 mb-4">
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-semibold text-gray-800">振替チケット残高</span>
                </div>
                <Badge className="bg-blue-600 text-white">{makeupTicketBalance}枚</Badge>
              </div>
            </CardContent>
          </Card>

          {makeupError && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 mb-4">
              <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
              <p className="text-sm text-red-800">{makeupError}</p>
            </div>
          )}

          {isLoadingAvailableDates ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
            </div>
          ) : (
            <div className="flex justify-center">
              <Calendar
                mode="single"
                selected={makeupDate}
                onSelect={setMakeupDate}
                disabled={(date) => {
                  if (date < new Date()) return true;
                  // 振替可能日のみ選択可能
                  if (availableDates.length > 0) {
                    const dateStr = format(date, 'yyyy-MM-dd');
                    return !availableDates.some(d => d.date === dateStr);
                  }
                  return false;
                }}
                className="rounded-md border"
              />
            </div>
          )}

          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1 rounded-xl"
              onClick={() => {
                setShowMakeupDialog(false);
                setMakeupDate(undefined);
                setMakeupError(null);
              }}
              disabled={isSubmittingMakeup}
            >
              キャンセル
            </Button>
            <Button
              className="flex-1 rounded-xl bg-blue-600 hover:bg-blue-700"
              onClick={handleRequestMakeup}
              disabled={!makeupDate || isSubmittingMakeup || makeupTicketBalance <= 0}
            >
              {isSubmittingMakeup ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : null}
              振替チケット使用
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* キャンセル成功ダイアログ */}
      <Dialog open={showCancelSuccessDialog} onOpenChange={setShowCancelSuccessDialog}>
        <DialogContent className="max-w-[340px] rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-green-600" />
              <DialogTitle>キャンセル完了</DialogTitle>
            </div>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-gray-700">
              {cancelSuccessMessage}
            </p>
          </div>
          <Button
            className="w-full rounded-xl bg-blue-600 hover:bg-blue-700"
            onClick={() => setShowCancelSuccessDialog(false)}
          >
            閉じる
          </Button>
        </DialogContent>
      </Dialog>

      <BottomTabBar />
    </div>
  );
}

export default function CalendarPage() {
  return (
    <AuthGuard>
      <CalendarContent />
    </AuthGuard>
  );
}
