'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { isAuthenticated, getMe } from '@/lib/api/auth';
import {
  getStaffLessonSchedules,
  getStaffCalendarSchedules,
  StaffLessonSchedule,
  StaffCalendarEvent,
  StaffScheduleSearchParams,
} from '@/lib/api/lessons';
import {
  Calendar,
  Clock,
  MapPin,
  Users,
  ChevronLeft,
  ChevronRight,
  List,
  Grid,
  User,
  AlertCircle,
} from 'lucide-react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay, addMonths, subMonths } from 'date-fns';
import { ja } from 'date-fns/locale';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  scheduled: { label: '予定', color: 'bg-blue-100 text-blue-800' },
  in_progress: { label: '進行中', color: 'bg-green-100 text-green-800' },
  completed: { label: '完了', color: 'bg-gray-100 text-gray-600' },
  cancelled: { label: '中止', color: 'bg-red-100 text-red-800' },
};

type ViewMode = 'list' | 'calendar';

export default function SchedulePage() {
  const router = useRouter();
  const [authChecking, setAuthChecking] = useState(true);
  const [isStaff, setIsStaff] = useState(false);

  const [lessons, setLessons] = useState<StaffLessonSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  // 認証チェック
  useEffect(() => {
    const checkAuth = async () => {
      if (!isAuthenticated()) {
        router.push('/login');
        return;
      }

      try {
        const profile = await getMe();
        const userType = profile.userType;
        if (userType === 'staff' || userType === 'teacher') {
          setIsStaff(true);
        } else {
          // 保護者・生徒はこのページにアクセス不可
          router.push('/feed');
          return;
        }
      } catch {
        router.push('/login');
        return;
      }

      setAuthChecking(false);
    };

    checkAuth();
  }, [router]);

  const fetchListData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const startDate = format(startOfMonth(currentDate), 'yyyy-MM-dd');
      const endDate = format(endOfMonth(currentDate), 'yyyy-MM-dd');

      const params: StaffScheduleSearchParams = {
        startDate,
        endDate,
        pageSize: 100,
      };

      const response = await getStaffLessonSchedules(params);
      setLessons(response.results || []);
    } catch (err) {
      console.error('Failed to fetch lessons:', err);
      setError('スケジュールの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  }, [currentDate]);

  const fetchCalendarData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // カレンダービューでもリストデータを使用（表示用）
      const startDate = format(startOfMonth(currentDate), 'yyyy-MM-dd');
      const endDate = format(endOfMonth(currentDate), 'yyyy-MM-dd');

      const response = await getStaffLessonSchedules({
        startDate,
        endDate,
        pageSize: 100,
      });
      setLessons(response.results || []);
    } catch (err) {
      console.error('Failed to fetch calendar:', err);
      setError('カレンダーデータの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  }, [currentDate]);

  useEffect(() => {
    if (!authChecking && isStaff) {
      if (viewMode === 'list') {
        fetchListData();
      } else {
        fetchCalendarData();
      }
    }
  }, [authChecking, isStaff, viewMode, fetchListData, fetchCalendarData]);

  const handlePrevMonth = () => {
    setCurrentDate(subMonths(currentDate, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(addMonths(currentDate, 1));
  };

  const handleToday = () => {
    setCurrentDate(new Date());
    setSelectedDate(new Date());
  };

  const getStatusBadge = (status: string) => {
    const statusInfo = STATUS_LABELS[status] || { label: status, color: 'bg-gray-100 text-gray-800' };
    return (
      <Badge className={`${statusInfo.color} font-medium text-xs`}>
        {statusInfo.label}
      </Badge>
    );
  };

  const formatTime = (time: string) => {
    return time.substring(0, 5);
  };

  // カレンダー用のデータ
  const calendarDays = eachDayOfInterval({
    start: startOfMonth(currentDate),
    end: endOfMonth(currentDate),
  });

  const getEventsForDate = (date: Date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return lessons.filter((lesson) => lesson.scheduledDate === dateStr);
  };

  // 選択された日の授業
  const selectedDateLessons = selectedDate ? getEventsForDate(selectedDate) : [];

  if (authChecking) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100" />;
  }

  if (!isStaff) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center">
        <Card className="max-w-md mx-4">
          <CardContent className="p-6 text-center">
            <AlertCircle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
            <p className="text-gray-600">このページは講師専用です</p>
            <Button className="mt-4" onClick={() => router.push('/feed')}>
              フィードに戻る
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-6 h-6 text-blue-600" />
                <h1 className="text-2xl font-bold text-gray-900">授業スケジュール</h1>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant={viewMode === 'list' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('list')}
                >
                  <List className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === 'calendar' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('calendar')}
                >
                  <Grid className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Month Navigation */}
        <div className="p-4 flex items-center justify-between">
          <Button variant="outline" size="sm" onClick={handlePrevMonth}>
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">
              {format(currentDate, 'yyyy年 M月', { locale: ja })}
            </h2>
            <Button variant="ghost" size="sm" onClick={handleToday}>
              今日
            </Button>
          </div>
          <Button variant="outline" size="sm" onClick={handleNextMonth}>
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-4 pt-0">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="animate-pulse">
                  <CardContent className="p-4">
                    <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : error ? (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="p-4">
                <p className="text-red-600">{error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={viewMode === 'list' ? fetchListData : fetchCalendarData}
                >
                  再読み込み
                </Button>
              </CardContent>
            </Card>
          ) : viewMode === 'list' ? (
            // リスト表示
            <div className="space-y-3">
              {lessons.length === 0 ? (
                <Card>
                  <CardContent className="p-8 text-center">
                    <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500">この月の授業はありません</p>
                  </CardContent>
                </Card>
              ) : (
                lessons.map((lesson) => (
                  <Card
                    key={lesson.id}
                    className="shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => router.push(`/classes/${lesson.id}`)}
                  >
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold text-gray-900">
                              {lesson.course?.name || 'コース未設定'}
                            </h3>
                            {getStatusBadge(lesson.status)}
                          </div>

                          <div className="flex flex-wrap gap-3 text-sm text-gray-600 mt-2">
                            <div className="flex items-center gap-1">
                              <Calendar className="w-3.5 h-3.5" />
                              <span>
                                {format(new Date(lesson.scheduledDate), 'M/d (E)', { locale: ja })}
                              </span>
                            </div>
                            <div className="flex items-center gap-1">
                              <Clock className="w-3.5 h-3.5" />
                              <span>
                                {formatTime(lesson.startTime)} - {formatTime(lesson.endTime)}
                              </span>
                            </div>
                            {lesson.school && (
                              <div className="flex items-center gap-1">
                                <MapPin className="w-3.5 h-3.5" />
                                <span>{lesson.school.shortName || lesson.school.name}</span>
                              </div>
                            )}
                          </div>

                          <div className="flex items-center gap-3 mt-2 text-sm">
                            {lesson.instructor && (
                              <div className="flex items-center gap-1 text-gray-500">
                                <User className="w-3.5 h-3.5" />
                                <span>{lesson.instructor.fullName}</span>
                              </div>
                            )}
                            <div className="flex items-center gap-1 text-gray-500">
                              <Users className="w-3.5 h-3.5" />
                              <span>
                                {lesson.currentEnrollment}
                                {lesson.capacity && `/${lesson.capacity}`}名
                              </span>
                            </div>
                          </div>
                        </div>

                        <ChevronRight className="w-5 h-5 text-gray-400 mt-1" />
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          ) : (
            // カレンダー表示
            <div className="space-y-4">
              {/* カレンダーグリッド */}
              <Card>
                <CardContent className="p-4">
                  <div className="grid grid-cols-7 gap-1 mb-2">
                    {['日', '月', '火', '水', '木', '金', '土'].map((day, i) => (
                      <div
                        key={day}
                        className={`text-center text-xs font-medium py-1 ${i === 0 ? 'text-red-500' : i === 6 ? 'text-blue-500' : 'text-gray-500'
                          }`}
                      >
                        {day}
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-7 gap-1">
                    {/* 月初の空白を埋める */}
                    {Array.from({ length: startOfMonth(currentDate).getDay() }).map((_, i) => (
                      <div key={`empty-${i}`} className="h-12" />
                    ))}

                    {calendarDays.map((day) => {
                      const dayEvents = getEventsForDate(day);
                      const isToday = isSameDay(day, new Date());
                      const isSelected = selectedDate && isSameDay(day, selectedDate);
                      const dayOfWeek = day.getDay();

                      return (
                        <button
                          key={day.toISOString()}
                          onClick={() => setSelectedDate(day)}
                          className={`h-12 p-1 rounded-lg text-sm relative transition-colors ${isSelected
                              ? 'bg-blue-600 text-white'
                              : isToday
                                ? 'bg-blue-100 text-blue-600'
                                : 'hover:bg-gray-100'
                            } ${dayOfWeek === 0 ? 'text-red-500' : dayOfWeek === 6 ? 'text-blue-500' : ''
                            } ${isSelected ? 'text-white' : ''}`}
                        >
                          <span className="block">{format(day, 'd')}</span>
                          {dayEvents.length > 0 && (
                            <span
                              className={`absolute bottom-1 left-1/2 transform -translate-x-1/2 w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-white' : 'bg-blue-500'
                                }`}
                            />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* 選択日の授業一覧 */}
              {selectedDate && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">
                      {format(selectedDate, 'M月d日 (E)', { locale: ja })}の授業
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    {selectedDateLessons.length === 0 ? (
                      <p className="text-sm text-gray-500 py-4 text-center">
                        この日の授業はありません
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {selectedDateLessons.map((lesson) => (
                          <div
                            key={lesson.id}
                            className="p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
                            onClick={() => router.push(`/classes/${lesson.id}`)}
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-sm">
                                    {lesson.course?.name}
                                  </span>
                                  {getStatusBadge(lesson.status)}
                                </div>
                                <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                                  <span>
                                    {formatTime(lesson.startTime)} - {formatTime(lesson.endTime)}
                                  </span>
                                  {lesson.school && (
                                    <span>@{lesson.school.shortName || lesson.school.name}</span>
                                  )}
                                </div>
                              </div>
                              <ChevronRight className="w-4 h-4 text-gray-400" />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>

      <BottomTabBar />
    </div>
  );
}
