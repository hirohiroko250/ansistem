'use client';

import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight, X, AlertCircle, RefreshCw, User, ChevronDown, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Calendar } from '@/components/ui/calendar';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { useRouter } from 'next/navigation';
import { format, startOfMonth, endOfMonth, addMonths, subMonths, getDate, getDaysInMonth, getDay, parseISO } from 'date-fns';
import { ja } from 'date-fns/locale';
import { getChildren, getStudentItems } from '@/lib/api/students';
import { getChildTicketBalance } from '@/lib/api/students';
import { getCalendarEvents, markAbsent, requestMakeup, getMakeupAvailableDates } from '@/lib/api/lessons';
import { getLessonCalendar, type LessonCalendarDay } from '@/lib/api/schools';
import type { Child, CalendarEvent, TicketBalance, MakeupAvailableDate, ApiError } from '@/lib/api/types';

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
};

export default function CalendarPage() {
  const router = useRouter();
  const [currentDate, setCurrentDate] = useState(new Date());

  // 子ども関連 state
  const [children, setChildren] = useState<Child[]>([]);
  const [selectedChild, setSelectedChild] = useState<Child | null>(null);
  const [showChildSelector, setShowChildSelector] = useState(false);
  const [isLoadingChildren, setIsLoadingChildren] = useState(true);
  const [childrenError, setChildrenError] = useState<string | null>(null);

  // イベント関連 state
  const [events, setEvents] = useState<DisplayEvent[]>([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [eventsError, setEventsError] = useState<string | null>(null);

  // 開講カレンダー（休校日）関連 state
  const [lessonCalendar, setLessonCalendar] = useState<LessonCalendarDay[]>([]);
  const [closedDates, setClosedDates] = useState<Set<number>>(new Set());
  const [holidayDates, setHolidayDates] = useState<Map<number, string>>(new Map());

  // 選択中のイベント
  const [selectedEvent, setSelectedEvent] = useState<DisplayEvent | null>(null);

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

  // カレンダー計算
  const daysInMonth = getDaysInMonth(currentDate);
  const firstDayOfWeek = getDay(startOfMonth(currentDate));
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const emptyDays = Array.from({ length: firstDayOfWeek }, (_, i) => i);
  const currentMonthStr = format(currentDate, 'yyyy年M月', { locale: ja });

  // 子ども一覧を取得
  useEffect(() => {
    const fetchChildren = async () => {
      setIsLoadingChildren(true);
      setChildrenError(null);
      try {
        const data = await getChildren();
        setChildren(data);
        if (data.length > 0) {
          setSelectedChild(data[0]);
        }
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
          school: event.resourceId || '',
          scheduleId: event.id,
          courseId: event.resourceId,
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
  const fetchLessonCalendar = useCallback(async () => {
    if (!selectedChild) return;

    try {
      // 子どもの購入アイテムからブランドと校舎を取得
      const items = await getStudentItems(selectedChild.id);
      if (items.length === 0) return;

      // 最初のアイテムのブランドと校舎を使用
      const item = items.find(i => i.brandId && i.schoolId);
      if (!item?.brandId || !item?.schoolId) return;

      const year = currentDate.getFullYear();
      const month = currentDate.getMonth() + 1;

      const calendarData = await getLessonCalendar(item.brandId, item.schoolId, year, month);
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
    } catch (error) {
      console.error('Failed to fetch lesson calendar:', error);
    }
  }, [selectedChild, currentDate]);

  useEffect(() => {
    if (selectedChild) {
      fetchLessonCalendar();
    }
  }, [selectedChild, currentDate, fetchLessonCalendar]);

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

  const getEventsForDay = (day: number) => {
    return events.filter((event) => event.date === day);
  };

  const handleEventClick = (event: DisplayEvent) => {
    setSelectedEvent(event);
  };

  // 欠席登録
  const handleMarkAbsent = async () => {
    if (!selectedEvent || !selectedChild) return;

    setIsSubmittingAbsent(true);
    setAbsentError(null);

    try {
      await markAbsent(selectedEvent.scheduleId, {
        absenceReason: '保護者からの欠席連絡',
      });

      setSelectedEvent(null);
      setShowAbsentDialog(true);

      // イベントを再取得
      await fetchEvents();
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
            <h1 className="text-2xl font-bold text-blue-600">Calendar</h1>
          </div>
        </header>
        <main className="max-w-[390px] mx-auto px-4 py-6 pb-24 flex flex-col items-center justify-center min-h-[60vh]">
          <p className="text-gray-600 mb-4">登録されているお子様がいません</p>
          <Button onClick={() => router.push('/children/add')}>お子様を登録する</Button>
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
                    className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${
                      selectedChild?.id === child.id ? 'bg-blue-50 border-2 border-blue-500' : 'hover:bg-gray-50'
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
                  const isClosed = closedDates.has(day);
                  const holidayName = holidayDates.get(day);

                  return (
                    <div
                      key={day}
                      className={`aspect-square flex flex-col items-center justify-center rounded-lg text-sm ${
                        isClosed ? 'bg-gray-200 text-gray-500' :
                        hasAbsent ? 'bg-red-100 text-red-700 font-semibold' :
                        hasMakeup ? 'bg-purple-100 text-purple-700 font-semibold' :
                        hasEvents ? 'bg-blue-500 text-white font-semibold' :
                        'text-gray-700 hover:bg-gray-100'
                      } cursor-pointer transition-colors relative`}
                      title={holidayName || (isClosed ? '休校日' : undefined)}
                    >
                      {day}
                      {hasEvents && !isClosed && (
                        <div className="flex gap-0.5 mt-1">
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
        <div className="flex flex-wrap gap-3 mb-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-blue-500" />
            <span className="text-gray-600">授業予定</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-gray-200" />
            <span className="text-gray-600">休校日</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-red-100" />
            <span className="text-gray-600">欠席</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-purple-100" />
            <span className="text-gray-600">振替</span>
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
              <CardContent className="p-6 text-center">
                <p className="text-gray-500">今月の予定はありません</p>
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
                  <CardContent className="p-4 flex items-center gap-3">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-gray-800">{event.date}</div>
                      <div className="text-xs text-gray-500">{format(currentDate, 'M月', { locale: ja })}</div>
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-800">{event.title}</h4>
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
                <p className="font-semibold text-gray-800">{selectedEvent.title}</p>
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

              {(selectedEvent.status === 'scheduled' || selectedEvent.status === 'confirmed') && (
                <div className="flex gap-2 pt-2">
                  <Button
                    variant="outline"
                    className="flex-1 rounded-xl"
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
                  <Button
                    className="flex-1 rounded-xl bg-blue-600 hover:bg-blue-700"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleOpenMakeupDialog();
                    }}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    振替申請
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
              <AlertCircle className="h-5 w-5 text-orange-600" />
              <DialogTitle>欠席登録完了</DialogTitle>
            </div>
          </DialogHeader>
          <DialogDescription>
            欠席登録が完了しました。振替授業をご希望の場合は、カレンダーから振替申請を行ってください。
          </DialogDescription>
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

      <BottomTabBar />
    </div>
  );
}
