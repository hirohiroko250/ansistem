'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { BottomNav } from '@/components/bottom-nav';
import { useRequireAuth, useAuth } from '@/lib/auth';
import {
  getTodayAttendance,
  clockIn,
  clockOut,
  getMyMonthlyAttendances,
  formatWorkTime,
  AttendanceRecord,
} from '@/lib/api/hr';
import { getTodayLessons, LessonSchedule } from '@/lib/api/lessons';
import { getMyQRCode, MyQRCodeResponse } from '@/lib/api/auth';
import { QRCodeSVG } from 'qrcode.react';
import {
  QrCode,
  LogIn,
  LogOut,
  Clock,
  MapPin,
  Camera,
  X,
  Calendar,
  ChevronRight,
} from 'lucide-react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay } from 'date-fns';
import { ja } from 'date-fns/locale';

declare global {
  interface Window {
    Html5QrcodeScanner: any;
  }
}

type WorkStatus = {
  label: string;
  color: string;
  canClockIn: boolean;
  canClockOut: boolean;
};

export default function AttendancePage() {
  const { loading: authLoading } = useRequireAuth();
  const { user } = useAuth();
  const router = useRouter();

  const [todayRecord, setTodayRecord] = useState<AttendanceRecord | null>(null);
  const [monthlyRecords, setMonthlyRecords] = useState<AttendanceRecord[]>([]);
  const [todayLessons, setTodayLessons] = useState<LessonSchedule[]>([]);
  const [myQRCode, setMyQRCode] = useState<MyQRCodeResponse | null>(null);
  const [dailyReport, setDailyReport] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showScanner, setShowScanner] = useState(false);
  const [scanType, setScanType] = useState<'clockin' | 'clockout' | null>(null);
  const [currentDate] = useState(new Date());
  const scannerRef = useRef<any>(null);

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
      setMyQRCode(qrCode);

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
    if (!authLoading && user) {
      loadData();
    }
  }, [authLoading, user, loadData]);

  useEffect(() => {
    if (showScanner) {
      initScanner();
    }
    return () => {
      if (scannerRef.current) {
        scannerRef.current.clear().catch(() => {});
      }
    };
  }, [showScanner]);

  const initScanner = async () => {
    if (scannerRef.current) {
      await scannerRef.current.clear().catch(() => {});
    }

    // Html5QrcodeScannerが利用可能かチェック
    if (typeof window !== 'undefined' && window.Html5QrcodeScanner) {
      const scanner = new window.Html5QrcodeScanner(
        'qr-reader',
        {
          fps: 10,
          qrbox: { width: 250, height: 250 },
          aspectRatio: 1.0,
        },
        false
      );

      scanner.render(
        (decodedText: string) => {
          handleQrScanned(decodedText);
          scanner.clear().catch(() => {});
          setShowScanner(false);
        },
        (errorMessage: string) => {
          console.log(errorMessage);
        }
      );

      scannerRef.current = scanner;
    }
  };

  const handleQrScanned = async (qrData: string) => {
    if (scanType === 'clockin') {
      await handleClockIn(qrData);
    } else if (scanType === 'clockout') {
      await handleClockOut(qrData);
    }
  };

  const startQrScan = (type: 'clockin' | 'clockout') => {
    if (type === 'clockout' && !dailyReport.trim()) {
      alert('日報を入力してください');
      return;
    }
    setScanType(type);
    setShowScanner(true);
  };

  const handleClockIn = async (qrCode?: string) => {
    try {
      setSubmitting(true);
      setError(null);

      const response = await clockIn({ qrCode });

      alert(response.message || '出勤打刻が完了しました');
      await loadData();
    } catch (err: any) {
      console.error('Clock in failed:', err);
      alert(err.message || '出勤打刻に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClockOut = async (qrCode?: string) => {
    try {
      setSubmitting(true);
      setError(null);

      const response = await clockOut({
        qrCode,
        dailyReport,
      });

      alert(response.message || '退勤打刻が完了しました');
      await loadData();
    } catch (err: any) {
      console.error('Clock out failed:', err);
      alert(err.message || '退勤打刻に失敗しました');
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

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
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
                      <div className="flex justify-center p-4 bg-gradient-to-br from-green-50 to-green-100 rounded-xl">
                        {myQRCode ? (
                          <div className="bg-white p-3 rounded-lg shadow-inner">
                            <QRCodeSVG
                              value={myQRCode.qr_code}
                              size={160}
                              level="M"
                              includeMargin={false}
                              imageSettings={{
                                src: "/favicon-32.png",
                                x: undefined,
                                y: undefined,
                                height: 28,
                                width: 28,
                                excavate: true,
                              }}
                            />
                            <p className="text-center text-xs text-gray-500 mt-2">
                              {myQRCode.user_name}
                            </p>
                          </div>
                        ) : (
                          <QrCode className="w-32 h-32 text-green-600" />
                        )}
                      </div>
                      <Button
                        onClick={() => startQrScan('clockin')}
                        disabled={submitting}
                        className="w-full h-12 bg-green-600 hover:bg-green-700"
                      >
                        <Camera className="w-4 h-4 mr-2" />
                        {submitting ? '処理中...' : 'QRコードをスキャンして出勤'}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handleClockIn()}
                        disabled={submitting}
                        className="w-full"
                      >
                        QRなしで出勤
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
                    onClick={() => startQrScan('clockout')}
                    disabled={submitting || !dailyReport.trim()}
                    className="w-full h-12 bg-blue-600 hover:bg-blue-700"
                  >
                    <Camera className="w-4 h-4 mr-2" />
                    {submitting ? '処理中...' : 'QRコードをスキャンして退勤'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => handleClockOut()}
                    disabled={submitting || !dailyReport.trim()}
                    className="w-full"
                  >
                    QRなしで退勤
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

      {/* QRスキャナーモーダル */}
      {showScanner && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-[420px] w-full overflow-hidden">
            <div className="p-4 bg-gradient-to-r from-blue-500 to-blue-600 flex items-center justify-between">
              <h2 className="text-white font-bold text-lg">
                {scanType === 'clockin' ? '出勤QRスキャン' : '退勤QRスキャン'}
              </h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  setShowScanner(false);
                  if (scannerRef.current) {
                    scannerRef.current.clear().catch(() => {});
                  }
                }}
                className="text-white hover:bg-white/20"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
            <div className="p-4">
              <div id="qr-reader" className="w-full"></div>
              <p className="text-sm text-gray-600 text-center mt-4">
                カメラを校舎のQRコードに向けてください
              </p>
            </div>
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  );
}
