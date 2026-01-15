'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { isAuthenticated, getMe } from '@/lib/api/auth';
import {
  getTodayAttendance,
  clockIn,
  clockOut,
  getMyMonthlyAttendances,
  formatWorkTime,
  AttendanceRecord,
  getMyQRCode,
  StaffQRCodeInfo,
} from '@/lib/api/hr';
import { getTodayLessons, StaffLessonSchedule } from '@/lib/api/lessons';
import {
  QrCode,
  LogIn,
  LogOut,
  Clock,
  MapPin,
  Camera,
  Calendar,
  ChevronRight,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay } from 'date-fns';
import { ja } from 'date-fns/locale';
import { QRCodeCanvas } from 'qrcode.react';

type WorkStatus = {
  label: string;
  color: string;
  canClockIn: boolean;
  canClockOut: boolean;
};

export default function AttendancePage() {
  const router = useRouter();
  const [authChecking, setAuthChecking] = useState(true);
  const [isStaff, setIsStaff] = useState(false);

  const [todayRecord, setTodayRecord] = useState<AttendanceRecord | null>(null);
  const [monthlyRecords, setMonthlyRecords] = useState<AttendanceRecord[]>([]);
  const [todayLessons, setTodayLessons] = useState<StaffLessonSchedule[]>([]);
  const [dailyReport, setDailyReport] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentDate] = useState(new Date());
  const [qrCodeInfo, setQrCodeInfo] = useState<StaffQRCodeInfo | null>(null);
  const [qrLoading, setQrLoading] = useState(false);

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

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [attendance, lessons, monthly, qrCode] = await Promise.all([
        getTodayAttendance(),
        getTodayLessons(),
        getMyMonthlyAttendances(),
        getMyQRCode().catch(() => null),
      ]);

      setTodayRecord(attendance);
      setTodayLessons(lessons);
      setMonthlyRecords(monthly);
      setQrCodeInfo(qrCode);

      if (attendance?.dailyReport) {
        setDailyReport(attendance.dailyReport);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('データの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authChecking && isStaff) {
      loadData();
    }
  }, [authChecking, isStaff, loadData]);

  const handleClockIn = async () => {
    try {
      setSubmitting(true);
      setError(null);

      const response = await clockIn({});

      alert(response.message || '出勤打刻が完了しました');
      await loadData();
    } catch (err: unknown) {
      console.error('Clock in failed:', err);
      const error = err as { message?: string };
      alert(error.message || '出勤打刻に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClockOut = async () => {
    try {
      setSubmitting(true);
      setError(null);

      const response = await clockOut({
        dailyReport,
      });

      alert(response.message || '退勤打刻が完了しました');
      await loadData();
    } catch (err: unknown) {
      console.error('Clock out failed:', err);
      const error = err as { message?: string };
      alert(error.message || '退勤打刻に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  const getWorkStatus = (): WorkStatus => {
    if (!todayRecord) {
      return { label: '出勤前', color: 'bg-gray-500', canClockIn: true, canClockOut: false };
    }
    if (todayRecord.clockInTime && !todayRecord.clockOutTime) {
      return { label: '出勤中', color: 'bg-green-500', canClockIn: false, canClockOut: true };
    }
    if (todayRecord.clockOutTime) {
      return { label: '退勤済', color: 'bg-blue-500', canClockIn: false, canClockOut: false };
    }
    return { label: '出勤前', color: 'bg-gray-500', canClockIn: true, canClockOut: false };
  };

  const formatTime = (timeString: string | undefined) => {
    if (!timeString) return '--:--';
    try {
      // ISO形式またはHH:mm:ss形式に対応
      if (timeString.includes('T')) {
        return format(new Date(timeString), 'HH:mm');
      }
      return timeString.substring(0, 5);
    } catch {
      return timeString;
    }
  };

  // カレンダー用データ
  const calendarDays = eachDayOfInterval({
    start: startOfMonth(currentDate),
    end: endOfMonth(currentDate),
  });

  const getAttendanceForDate = (date: Date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return monthlyRecords.find((r) => r.date === dateStr);
  };

  if (authChecking || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
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

  const workStatus = getWorkStatus();

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-[420px] mx-auto">
        {/* Header */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <h1 className="text-2xl font-bold text-gray-900">勤怠管理</h1>
            <p className="text-sm text-gray-600 mt-1">QR打刻システム</p>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {error && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="p-4">
                <p className="text-red-600 text-sm">{error}</p>
              </CardContent>
            </Card>
          )}

          {/* 勤務状況カード */}
          <Card className="shadow-md border-0">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">勤務状況</CardTitle>
                <Badge className={`${workStatus.color} text-white`}>
                  {workStatus.label}
                </Badge>
              </div>
              <CardDescription>
                {format(new Date(), 'yyyy年M月d日 (E)', { locale: ja })}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {todayRecord?.clockInTime && (
                  <div className="flex items-center gap-2 text-sm p-3 bg-green-50 rounded-lg">
                    <LogIn className="w-4 h-4 text-green-600" />
                    <span className="font-medium">出勤時刻:</span>
                    <span>{formatTime(todayRecord.clockInTime)}</span>
                  </div>
                )}
                {todayRecord?.clockOutTime && (
                  <div className="flex items-center gap-2 text-sm p-3 bg-blue-50 rounded-lg">
                    <LogOut className="w-4 h-4 text-blue-600" />
                    <span className="font-medium">退勤時刻:</span>
                    <span>{formatTime(todayRecord.clockOutTime)}</span>
                  </div>
                )}
                {todayRecord?.workMinutes && (
                  <div className="flex items-center gap-2 text-sm p-3 bg-gray-50 rounded-lg">
                    <Clock className="w-4 h-4 text-gray-600" />
                    <span className="font-medium">勤務時間:</span>
                    <span>{formatWorkTime(todayRecord.workMinutes)}</span>
                  </div>
                )}

                <div className="pt-2">
                  {workStatus.canClockIn && (
                    <div className="space-y-3">
                      <div className="flex flex-col items-center justify-center p-6 bg-gradient-to-br from-green-50 to-green-100 rounded-xl">
                        {qrCodeInfo ? (
                          <>
                            <QRCodeCanvas
                              value={qrCodeInfo.qr_code}
                              size={180}
                              level="H"
                              includeMargin={true}
                              bgColor="#f0fdf4"
                            />
                            <p className="mt-2 text-sm text-gray-600 font-medium">
                              {qrCodeInfo.user_name}
                            </p>
                            {qrCodeInfo.user_no && (
                              <p className="text-xs text-gray-500">
                                ID: {qrCodeInfo.user_no}
                              </p>
                            )}
                          </>
                        ) : qrLoading ? (
                          <div className="flex items-center gap-2 py-8">
                            <RefreshCw className="w-6 h-6 animate-spin text-green-600" />
                            <span className="text-gray-600">読み込み中...</span>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center py-4">
                            <QrCode className="w-24 h-24 text-green-600 mb-2" />
                            <p className="text-sm text-gray-500">QRコードが取得できません</p>
                          </div>
                        )}
                      </div>
                      <p className="text-center text-xs text-gray-500">
                        このQRコードをタブレットにかざして出勤打刻
                      </p>
                      <Button
                        onClick={handleClockIn}
                        disabled={submitting}
                        className="w-full h-12 bg-green-600 hover:bg-green-700"
                      >
                        <Camera className="w-4 h-4 mr-2" />
                        {submitting ? '処理中...' : '手動で出勤打刻'}
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 今日の授業 */}
          {workStatus.canClockOut && todayLessons.length > 0 && (
            <Card className="shadow-md border-0">
              <CardHeader>
                <CardTitle className="text-lg">今日の授業</CardTitle>
                <CardDescription>担当コマ一覧</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {todayLessons.map((lesson) => (
                    <div
                      key={lesson.id}
                      className="p-3 bg-blue-50 rounded-xl cursor-pointer hover:bg-blue-100 transition-colors"
                      onClick={() => router.push(`/classes/${lesson.id}`)}
                    >
                      <h3 className="font-semibold text-gray-900">
                        {lesson.course?.name || 'コース未設定'}
                      </h3>
                      <div className="flex items-center gap-3 text-sm text-gray-600 mt-1">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          <span>
                            {lesson.startTime?.substring(0, 5)} - {lesson.endTime?.substring(0, 5)}
                          </span>
                        </div>
                        {lesson.school && (
                          <div className="flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            <span>{lesson.school.shortName || lesson.school.name}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 日報入力・退勤 */}
          {workStatus.canClockOut && (
            <Card className="shadow-md border-0">
              <CardHeader>
                <CardTitle className="text-lg">日報入力</CardTitle>
                <CardDescription>退勤前に必ず入力してください</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <Label htmlFor="dailyReport">本日の業務内容 *</Label>
                    <Textarea
                      id="dailyReport"
                      placeholder="今日の授業内容、気づいたこと、申し送り事項などを記入してください"
                      value={dailyReport}
                      onChange={(e) => setDailyReport(e.target.value)}
                      rows={6}
                      className="mt-2"
                    />
                  </div>
                  <Button
                    onClick={handleClockOut}
                    disabled={submitting || !dailyReport.trim()}
                    className="w-full h-12 bg-blue-600 hover:bg-blue-700"
                  >
                    <Camera className="w-4 h-4 mr-2" />
                    {submitting ? '処理中...' : '退勤打刻'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 月別勤怠カレンダー */}
          <Card className="shadow-md border-0">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                {format(currentDate, 'yyyy年M月', { locale: ja })}の勤怠
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-7 gap-1 mb-2">
                {['日', '月', '火', '水', '木', '金', '土'].map((day, i) => (
                  <div
                    key={day}
                    className={`text-center text-xs font-medium py-1 ${
                      i === 0 ? 'text-red-500' : i === 6 ? 'text-blue-500' : 'text-gray-500'
                    }`}
                  >
                    {day}
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-7 gap-1">
                {/* 月初の空白 */}
                {Array.from({ length: startOfMonth(currentDate).getDay() }).map((_, i) => (
                  <div key={`empty-${i}`} className="h-10" />
                ))}

                {calendarDays.map((day) => {
                  const attendance = getAttendanceForDate(day);
                  const isToday = isSameDay(day, new Date());
                  const dayOfWeek = day.getDay();

                  let bgColor = '';
                  if (attendance?.clockInTime && attendance?.clockOutTime) {
                    bgColor = 'bg-green-100';
                  } else if (attendance?.clockInTime) {
                    bgColor = 'bg-yellow-100';
                  } else if (attendance?.status === 'absent') {
                    bgColor = 'bg-red-100';
                  } else if (attendance?.status === 'leave') {
                    bgColor = 'bg-purple-100';
                  }

                  return (
                    <div
                      key={day.toISOString()}
                      className={`h-10 flex items-center justify-center text-sm rounded-lg ${bgColor} ${
                        isToday ? 'ring-2 ring-blue-500' : ''
                      } ${
                        dayOfWeek === 0
                          ? 'text-red-500'
                          : dayOfWeek === 6
                          ? 'text-blue-500'
                          : ''
                      }`}
                    >
                      {format(day, 'd')}
                    </div>
                  );
                })}
              </div>

              <div className="flex flex-wrap gap-2 mt-4 text-xs">
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded bg-green-100" />
                  <span>出勤済</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded bg-yellow-100" />
                  <span>勤務中</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded bg-red-100" />
                  <span>欠勤</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded bg-purple-100" />
                  <span>休暇</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <BottomTabBar />
    </div>
  );
}
