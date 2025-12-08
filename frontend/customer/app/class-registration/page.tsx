'use client';

import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, User, Ticket, Calendar as CalendarIcon, MapPin, QrCode, Clock, Globe, Users } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar } from '@/components/ui/calendar';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import { getChildren, type PurchasedItem, getAllStudentItems } from '@/lib/api/students';
import { getBrandSchools, getLessonCalendar, type BrandSchool, type LessonCalendarDay } from '@/lib/api/schools';
import type { Child } from '@/lib/api/types';
import { brands } from '@/lib/ticket-data';

type TicketInfo = {
  id: string;
  type: 'course' | 'transfer' | 'event';
  brandId: string;
  brandName: string;
  schoolId?: string;
  schoolName: string;
  studentId?: string;
  studentName?: string;
  courseName?: string;
  count: number;
  expiryDate: string;
  status: 'active' | 'expiring';
  eventName?: string;
};

type SchoolWithCalendar = BrandSchool & {
  calendarDays?: LessonCalendarDay[];
};

export default function ClassRegistrationPage() {
  const [step, setStep] = useState<'ticket' | 'child' | 'brand' | 'school' | 'date' | 'time' | 'qr'>('ticket');
  const [selectedTicket, setSelectedTicket] = useState<TicketInfo | null>(null);
  const [selectedChild, setSelectedChild] = useState<Child | null>(null);
  const [selectedBrand, setSelectedBrand] = useState<typeof brands[0] | null>(null);
  const [selectedSchool, setSelectedSchool] = useState<SchoolWithCalendar | null>(null);
  const [selectedTime, setSelectedTime] = useState<string>('');
  const [selectedDate, setSelectedDate] = useState<Date>();
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date());

  // API data
  const [children, setChildren] = useState<Child[]>([]);
  const [tickets, setTickets] = useState<TicketInfo[]>([]);
  const [schools, setSchools] = useState<SchoolWithCalendar[]>([]);
  const [calendarData, setCalendarData] = useState<LessonCalendarDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load children and tickets on mount
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        // Get children
        const childrenData = await getChildren();
        setChildren(childrenData);

        // Get purchase items (tickets come from tuition type products)
        const items = await getAllStudentItems();

        // Transform purchase items into tickets
        // tuition type = チケットとして表示
        const ticketData: TicketInfo[] = items
          .filter((item: PurchasedItem) => item.productType === 'tuition')
          .map((item: PurchasedItem) => {
            // 有効期限を計算（請求月の翌月末）
            let expiryDate = '';
            if (item.billingMonth) {
              const [year, month] = item.billingMonth.split('-').map(Number);
              const nextMonth = month === 12 ? 1 : month + 1;
              const nextYear = month === 12 ? year + 1 : year;
              const lastDay = new Date(nextYear, nextMonth, 0).getDate();
              expiryDate = `${nextYear}-${String(nextMonth).padStart(2, '0')}-${lastDay}`;
            }

            // 表示名を決定（優先順: コース名 > ブランド名 > 商品名）
            const displayName = item.courseName || item.brandName || item.productName || 'コース';
            const brandDisplay = item.brandName || item.productName?.split(' ')[0] || 'コース';

            return {
              id: item.id,
              type: 'course' as const,
              brandId: item.brandId || '',
              brandName: brandDisplay,
              schoolId: item.schoolId,
              schoolName: item.schoolName || displayName,
              studentId: item.studentId,
              studentName: item.studentName,
              courseName: item.courseName || '',
              count: item.quantity,
              expiryDate,
              status: 'active' as const,
            };
          });

        setTickets(ticketData);
      } catch (err) {
        console.error('Failed to load data:', err);
        setError('データの読み込みに失敗しました');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  // Load schools when brand is selected
  useEffect(() => {
    async function loadSchools() {
      if (!selectedBrand) return;

      try {
        const schoolsData = await getBrandSchools(selectedBrand.id);
        setSchools(schoolsData);
      } catch (err) {
        console.error('Failed to load schools:', err);
      }
    }

    loadSchools();
  }, [selectedBrand]);

  // Load calendar when school is selected
  const loadCalendar = useCallback(async (month: Date) => {
    if (!selectedSchool || !selectedBrand) return;

    try {
      const year = month.getFullYear();
      const monthNum = month.getMonth() + 1;
      const calendar = await getLessonCalendar(
        selectedBrand.id,
        selectedSchool.id,
        year,
        monthNum
      );
      setCalendarData(calendar.calendar);
    } catch (err) {
      console.error('Failed to load calendar:', err);
      // If API fails, generate empty calendar
      setCalendarData([]);
    }
  }, [selectedSchool, selectedBrand]);

  useEffect(() => {
    if (selectedSchool && selectedBrand) {
      loadCalendar(currentMonth);
    }
  }, [selectedSchool, selectedBrand, currentMonth, loadCalendar]);

  const courseTickets = tickets.filter(t => t.type === 'course');
  const transferTickets = tickets.filter(t => t.type === 'transfer');
  const eventTickets = tickets.filter(t => t.type === 'event');

  const getCalendarDayInfo = (date: Date): LessonCalendarDay | undefined => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return calendarData.find(d => d.date === dateStr);
  };

  const isDateAvailable = (date: Date): boolean => {
    const dayInfo = getCalendarDayInfo(date);
    return dayInfo?.isOpen ?? false;
  };

  const getDayModifiers = (date: Date) => {
    const dayInfo = getCalendarDayInfo(date);
    if (!dayInfo) return {};

    return {
      isNativeDay: dayInfo.isNativeDay,
      isJapaneseOnly: dayInfo.isJapaneseOnly,
      isClosed: !dayInfo.isOpen,
    };
  };

  // 選択した日付から有効期限までに必要なチケット数を計算
  const calculateRequiredTickets = useCallback((startDate: Date): { required: number; available: number; additional: number; lessonDates: string[] } => {
    if (!selectedTicket || !calendarData.length) {
      return { required: 0, available: 0, additional: 0, lessonDates: [] };
    }

    const available = selectedTicket.count;
    const expiryDate = selectedTicket.expiryDate ? new Date(selectedTicket.expiryDate) : null;
    const startDateStr = format(startDate, 'yyyy-MM-dd');

    // 開始日から有効期限（または月末）までの開講日を数える
    const lessonDates: string[] = [];
    for (const day of calendarData) {
      if (!day.isOpen) continue;

      // 開始日以降
      if (day.date >= startDateStr) {
        // 有効期限がある場合はそれまで、なければ月末まで
        if (!expiryDate || day.date <= format(expiryDate, 'yyyy-MM-dd')) {
          lessonDates.push(day.date);
        }
      }
    }

    const required = lessonDates.length;
    const additional = Math.max(0, required - available);

    return { required, available, additional, lessonDates };
  }, [selectedTicket, calendarData]);

  // Time slots (would come from API in production)
  const timeSlots = ['15:00-16:00', '16:00-17:00', '17:00-18:00', '18:00-19:00'];

  const handleTicketSelect = async (ticket: TicketInfo) => {
    setSelectedTicket(ticket);

    if (ticket.type === 'event') {
      setStep('qr');
      return;
    }

    // チケットから生徒情報を設定（購入時の生徒情報）
    if (ticket.studentId && ticket.studentName) {
      // childrenから該当する生徒を検索、なければチケットの情報で仮作成
      const child = children.find(c => c.id === ticket.studentId);
      if (child) {
        setSelectedChild(child);
      } else {
        setSelectedChild({
          id: ticket.studentId,
          fullName: ticket.studentName,
          studentNumber: '',
        } as Child);
      }
    }

    // チケットからブランド情報を設定
    if (ticket.brandId) {
      const brand = brands.find(b => b.id === ticket.brandId);
      if (brand) {
        setSelectedBrand(brand);
      } else {
        setSelectedBrand({
          id: ticket.brandId,
          name: ticket.brandName,
          icon: User,
          color: 'bg-blue-500',
        });
      }
    }

    // チケット購入時に校舎情報があれば、校舎選択をスキップして日付選択へ
    if (ticket.schoolId || ticket.schoolName) setSelectedSchool({
      id: ticket.schoolId || ticket.id,
      name: ticket.schoolName,
      school_name: ticket.schoolName,
    } as unknown as SchoolWithCalendar);
    // 生徒情報があれば直接日付選択へ、なければ子供選択へ
    if (ticket.studentId) {
      setStep('date');
    } else {
      setStep('child');
    }
  } else {
    // 校舎情報がない場合は子供選択へ（まれなケース）
    setStep('child');
}
  };

const handleChildSelect = (child: Child) => {
  setSelectedChild(child);
  // 既に校舎情報がセットされていれば日付選択へ
  if (selectedSchool) {
    setStep('date');
  } else if (selectedTicket?.schoolId || selectedTicket?.schoolName) setSelectedSchool({
    id: selectedTicket.schoolId || selectedTicket.id,
    name: selectedTicket.schoolName,
    school_name: selectedTicket.schoolName,
  } as unknown as SchoolWithCalendar);
  setStep('date');
} else if (selectedTicket?.brandId) {
  setStep('school');
} else {
  setStep('brand');
}
  };

const handleBrandSelect = (brand: typeof brands[0]) => {
  setSelectedBrand(brand);
  setStep('school');
};

const handleSchoolSelect = (school: SchoolWithCalendar) => {
  setSelectedSchool(school);
  setStep('date');
};

const handleDateSelect = (date: Date | undefined) => {
  setSelectedDate(date);
  if (date) {
    setStep('time');
  }
};

const handleTimeSelect = (time: string) => {
  setSelectedTime(time);
};

const handleConfirm = () => {
  alert('予約が完了しました');
};

const handleMonthChange = (date: Date) => {
  setCurrentMonth(date);
};

const generateQRCode = () => {
  return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0id2hpdGUiLz48cmVjdCB4PSIyMCIgeT0iMjAiIHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCIvPjxyZWN0IHg9IjYwIiB5PSIyMCIgd2lkdGg9IjIwIiBoZWlnaHQ9IjIwIi8+PHJlY3QgeD0iMTAwIiB5PSIyMCIgd2lkdGg9IjIwIiBoZWlnaHQ9IjIwIi8+PHJlY3QgeD0iMTQwIiB5PSIyMCIgd2lkdGg9IjIwIiBoZWlnaHQ9IjIwIi8+PHJlY3QgeD0iMjAiIHk9IjYwIiB3aWR0aD0iMjAiIGhlaWdodD0iMjAiLz48cmVjdCB4PSIxMDAiIHk9IjYwIiB3aWR0aD0iMjAiIGhlaWdodD0iMjAiLz48cmVjdCB4PSIxNDAiIHk9IjYwIiB3aWR0aD0iMjAiIGhlaWdodD0iMjAiLz48L3N2Zz4=';
};

const getBrandColor = (brandId: string) => {
  const brand = brands.find(b => b.id === brandId);
  return brand?.color || 'bg-gray-100 text-gray-600';
};

if (loading) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
      <div className="text-gray-600">読み込み中...</div>
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
        <h1 className="text-xl font-bold text-gray-800">クラス予約</h1>
      </div>
    </header>

    <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
      {error && (
        <Card className="rounded-xl shadow-md bg-red-50 border-red-200 mb-4">
          <CardContent className="p-4">
            <p className="text-red-600 text-sm">{error}</p>
          </CardContent>
        </Card>
      )}

      {step === 'ticket' && (
        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">チケットを選択</h2>

          {courseTickets.length === 0 && transferTickets.length === 0 && eventTickets.length === 0 ? (
            <Card className="rounded-xl shadow-md bg-gray-50 border-gray-200">
              <CardContent className="p-6 text-center">
                <Ticket className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600">利用可能なチケットがありません</p>
                <p className="text-sm text-gray-500 mt-2">コースを購入するとチケットが付与されます</p>
              </CardContent>
            </Card>
          ) : (
            <>
              {courseTickets.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-md font-semibold text-gray-700 mb-3">コースチケット</h3>
                  <div className="space-y-3">
                    {courseTickets.map((ticket) => (
                      <Card
                        key={ticket.id}
                        className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                        onClick={() => handleTicketSelect(ticket)}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <Badge className={getBrandColor(ticket.brandId)}>
                                  {ticket.brandName}
                                </Badge>
                              </div>
                              <h3 className="font-semibold text-gray-800">{ticket.schoolName}</h3>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center gap-1 text-blue-600">
                                <Ticket className="h-5 w-5" />
                                <span className="text-2xl font-bold">{ticket.count}</span>
                              </div>
                              <p className="text-xs text-gray-500">枚</p>
                            </div>
                          </div>
                          {ticket.expiryDate && (
                            <p className="text-sm text-gray-600">有効期限: {ticket.expiryDate}</p>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}

              {transferTickets.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-md font-semibold text-gray-700 mb-3">振替チケット</h3>
                  <div className="space-y-3">
                    {transferTickets.map((ticket) => (
                      <Card
                        key={ticket.id}
                        className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer border-amber-200"
                        onClick={() => handleTicketSelect(ticket)}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1">
                              <Badge className="bg-amber-500 text-white text-xs mb-1">
                                {ticket.brandName}
                              </Badge>
                              <h3 className="font-semibold text-gray-800">{ticket.schoolName}</h3>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center gap-1 text-amber-600">
                                <Ticket className="h-5 w-5" />
                                <span className="text-2xl font-bold">{ticket.count}</span>
                              </div>
                              <p className="text-xs text-gray-500">枚</p>
                            </div>
                          </div>
                          {ticket.expiryDate && (
                            <p className="text-sm text-gray-600">有効期限: {ticket.expiryDate}</p>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}

              {eventTickets.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-md font-semibold text-gray-700 mb-3">イベントチケット</h3>
                  <div className="space-y-3">
                    {eventTickets.map((ticket) => (
                      <Card
                        key={ticket.id}
                        className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer border-purple-200"
                        onClick={() => handleTicketSelect(ticket)}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1">
                              <Badge className="bg-purple-500 text-white text-xs mb-1">
                                {ticket.brandName}
                              </Badge>
                              <h3 className="font-semibold text-gray-800">{ticket.eventName}</h3>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center gap-1 text-purple-600">
                                <Ticket className="h-5 w-5" />
                                <span className="text-2xl font-bold">{ticket.count}</span>
                              </div>
                              <p className="text-xs text-gray-500">枚</p>
                            </div>
                          </div>
                          {ticket.expiryDate && (
                            <p className="text-sm text-gray-600">有効期限: {ticket.expiryDate}</p>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </section>
      )}

      {step === 'child' && (
        <section>
          <Button variant="ghost" className="mb-4" onClick={() => setStep('ticket')}>
            <ChevronLeft className="h-4 w-4 mr-2" />
            戻る
          </Button>

          <Card className="rounded-xl shadow-md bg-blue-50 border-blue-200 mb-6">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Ticket className="h-5 w-5 text-blue-600" />
                <div>
                  <p className="text-sm text-gray-600">選択中のチケット</p>
                  <p className="font-semibold text-gray-800">{selectedTicket?.brandName} - {selectedTicket?.schoolName}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <h2 className="text-lg font-semibold text-gray-800 mb-4">お子様を選択</h2>
          <div className="space-y-3">
            {children.map((child) => (
              <Card
                key={child.id}
                className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => handleChildSelect(child)}
              >
                <CardContent className="p-4 flex items-center gap-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                    <User className="h-6 w-6 text-blue-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-800">{child.studentNumber} {child.fullName}</h3>
                    <p className="text-sm text-gray-600">{child.grade || ''}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {step === 'brand' && (
        <section>
          <Button variant="ghost" className="mb-4" onClick={() => setStep('child')}>
            <ChevronLeft className="h-4 w-4 mr-2" />
            戻る
          </Button>

          <Card className="rounded-xl shadow-md bg-blue-50 border-blue-200 mb-6">
            <CardContent className="p-4 space-y-2">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-blue-600" />
                <p className="text-sm text-gray-800">{selectedChild?.studentNumber} {selectedChild?.fullName}</p>
              </div>
              <div className="flex items-center gap-2">
                <Ticket className="h-4 w-4 text-blue-600" />
                <p className="text-sm text-gray-800">{selectedTicket?.type === 'course' ? 'コース' : '振替'}チケット</p>
              </div>
            </CardContent>
          </Card>

          <h2 className="text-lg font-semibold text-gray-800 mb-4">ブランドを選択</h2>
          <div className="space-y-3">
            {brands.map((brand) => {
              const Icon = brand.icon;
              return (
                <Card
                  key={brand.id}
                  className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => handleBrandSelect(brand)}
                >
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${brand.color}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="font-semibold text-gray-800">{brand.name}</h3>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>
      )}

      {step === 'school' && (
        <section>
          <Button variant="ghost" className="mb-4" onClick={() => setStep('brand')}>
            <ChevronLeft className="h-4 w-4 mr-2" />
            戻る
          </Button>

          <h2 className="text-lg font-semibold text-gray-800 mb-4">教室を選択</h2>
          <div className="space-y-3">
            {/* チケットに校舎情報がある場合はそれを表示 */}
            {selectedTicket?.schoolId && selectedTicket?.schoolName ? (
              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer border-blue-200"
                onClick={() => handleSchoolSelect({
                  id: selectedTicket.schoolId!,
                  name: selectedTicket.schoolName,
                  school_name: selectedTicket.schoolName,
                } as unknown as SchoolWithCalendar)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <MapPin className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div>
                      <Badge className="bg-blue-100 text-blue-700 text-xs mb-1">ご契約の校舎</Badge>
                      <h3 className="font-semibold text-gray-800 mb-1">{selectedTicket.schoolName}</h3>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : schools.length === 0 ? (
              <Card className="rounded-xl shadow-md bg-gray-50">
                <CardContent className="p-6 text-center">
                  <MapPin className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                  <p className="text-gray-600">校舎が見つかりません</p>
                </CardContent>
              </Card>
            ) : (
              schools.map((school) => (
                <Card
                  key={school.id}
                  className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => handleSchoolSelect(school)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <MapPin className="h-5 w-5 text-blue-600 mt-0.5" />
                      <div>
                        <h3 className="font-semibold text-gray-800 mb-1">{school.name}</h3>
                        <p className="text-sm text-gray-600">{school.address}</p>
                        {school.phone && (
                          <p className="text-sm text-gray-500 mt-1">{school.phone}</p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </section>
      )}

      {step === 'date' && (
        <section>
          <Button variant="ghost" className="mb-4" onClick={() => setStep('school')}>
            <ChevronLeft className="h-4 w-4 mr-2" />
            戻る
          </Button>

          <Card className="rounded-xl shadow-md bg-blue-50 border-blue-200 mb-6">
            <CardContent className="p-4 space-y-2">
              <p className="text-sm"><span className="font-semibold">お子様:</span> {selectedChild?.studentNumber} {selectedChild?.fullName}</p>
              <p className="text-sm"><span className="font-semibold">教室:</span> {selectedSchool?.name}</p>
            </CardContent>
          </Card>

          <h2 className="text-lg font-semibold text-gray-800 mb-4">日付を選択</h2>

          {/* Legend */}
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

          <Card className="rounded-xl shadow-md mb-6">
            <CardContent className="p-4">
              <div className="flex justify-center">
                <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={handleDateSelect}
                  onMonthChange={handleMonthChange}
                  disabled={(date) => date < new Date() || !isDateAvailable(date)}
                  className="rounded-md border"
                  modifiers={{
                    nativeDay: (date) => getCalendarDayInfo(date)?.isNativeDay ?? false,
                    japaneseOnly: (date) => getCalendarDayInfo(date)?.isJapaneseOnly ?? false,
                  }}
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
                />
              </div>
            </CardContent>
          </Card>

          {selectedDate && (
            <Card className="rounded-xl shadow-md bg-amber-50 border-amber-200">
              <CardContent className="p-4">
                <p className="text-sm text-gray-700 font-semibold mb-2">
                  {format(selectedDate, 'yyyy年MM月dd日(E)', { locale: ja })}
                </p>
                {(() => {
                  const dayInfo = getCalendarDayInfo(selectedDate);
                  if (dayInfo) {
                    return (
                      <div className="flex items-center gap-2">
                        {dayInfo.isNativeDay ? (
                          <>
                            <Globe className="h-4 w-4 text-orange-600" />
                            <span className="text-sm text-orange-700">外国人講師の日</span>
                          </>
                        ) : dayInfo.isJapaneseOnly ? (
                          <>
                            <Users className="h-4 w-4 text-blue-600" />
                            <span className="text-sm text-blue-700">日本人講師の日</span>
                          </>
                        ) : null}
                        {dayInfo.displayLabel && (
                          <Badge variant="outline" className="ml-2">{dayInfo.displayLabel}</Badge>
                        )}
                      </div>
                    );
                  }
                  return null;
                })()}
              </CardContent>
            </Card>
          )}
        </section>
      )}

      {step === 'time' && (
        <section>
          <Button variant="ghost" className="mb-4" onClick={() => setStep('date')}>
            <ChevronLeft className="h-4 w-4 mr-2" />
            戻る
          </Button>

          <Card className="rounded-xl shadow-md bg-blue-50 border-blue-200 mb-6">
            <CardContent className="p-4 space-y-2">
              <p className="text-sm"><span className="font-semibold">お子様:</span> {selectedChild?.studentNumber} {selectedChild?.fullName}</p>
              <p className="text-sm"><span className="font-semibold">教室:</span> {selectedSchool?.name}</p>
              <p className="text-sm"><span className="font-semibold">日付:</span> {selectedDate ? format(selectedDate, 'yyyy年MM月dd日(E)', { locale: ja }) : ''}</p>
              {(() => {
                const dayInfo = selectedDate ? getCalendarDayInfo(selectedDate) : null;
                if (dayInfo) {
                  return (
                    <p className="text-sm">
                      <span className="font-semibold">タイプ:</span>{' '}
                      {dayInfo.isNativeDay ? '外国人講師の日' : dayInfo.isJapaneseOnly ? '日本人講師の日' : ''}
                    </p>
                  );
                }
                return null;
              })()}
            </CardContent>
          </Card>

          <h2 className="text-lg font-semibold text-gray-800 mb-4">時間帯を選択</h2>
          <div className="space-y-3">
            {timeSlots.map((time, index) => (
              <Card
                key={index}
                className={`rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer ${selectedTime === time ? 'border-blue-500 border-2 bg-blue-50' : ''
                  }`}
                onClick={() => handleTimeSelect(time)}
              >
                <CardContent className="p-4 flex items-center gap-3">
                  <Clock className={`h-5 w-5 ${selectedTime === time ? 'text-blue-600' : 'text-gray-600'}`} />
                  <h3 className={`font-semibold ${selectedTime === time ? 'text-blue-600' : 'text-gray-800'}`}>
                    {time}
                  </h3>
                </CardContent>
              </Card>
            ))}
          </div>

          <Button
            onClick={handleConfirm}
            className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg mt-6"
            disabled={!selectedTime}
          >
            予約を確定する
          </Button>
        </section>
      )}

      {step === 'qr' && (
        <section>
          <Button variant="ghost" className="mb-4" onClick={() => setStep('ticket')}>
            <ChevronLeft className="h-4 w-4 mr-2" />
            戻る
          </Button>

          <div className="text-center">
            <Card className="rounded-xl shadow-md bg-purple-50 border-purple-200 mb-6">
              <CardContent className="p-6">
                <div className="flex items-center justify-center gap-3 mb-4">
                  <QrCode className="h-6 w-6 text-purple-600" />
                  <h2 className="text-xl font-bold text-gray-800">イベントチケット</h2>
                </div>
                <p className="text-sm text-gray-600 mb-2">{selectedTicket?.eventName}</p>
                <Badge className="bg-purple-500 text-white">
                  残り{selectedTicket?.count}枚
                </Badge>
              </CardContent>
            </Card>

            <Card className="rounded-xl shadow-md mb-6">
              <CardContent className="p-8">
                <div className="bg-white p-4 rounded-xl inline-block">
                  <img
                    src={generateQRCode()}
                    alt="QR Code"
                    className="w-48 h-48 mx-auto"
                  />
                </div>
                <p className="text-sm text-gray-600 mt-4">
                  このQRコードを会場で提示してください
                </p>
              </CardContent>
            </Card>

            <Card className="rounded-xl shadow-md bg-blue-50 border-blue-200">
              <CardContent className="p-4">
                <p className="text-sm text-gray-700">
                  ※ QRコードは画面を明るくしてご提示ください<br />
                  ※ 1回の使用で1枚消費されます
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
      )}
    </main>

    <BottomTabBar />
  </div >
);
}
