'use client';

import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight, User, Calendar as CalendarIcon, MapPin, Clock, Building2, RefreshCw, LogOut, PauseCircle, AlertCircle, Loader2, CheckCircle, Circle, Triangle, X as XIcon, Minus } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import {
  getMyContracts,
  changeClass,
  changeSchool,
  requestSuspension,
  requestCancellation,
  type MyContract,
  type MyStudent,
  type MyTicket,
} from '@/lib/api/contracts';
import { getClassSchedules, getBrandSchools, type ClassScheduleResponse, type ClassScheduleItem, type BrandSchool } from '@/lib/api/schools';
import { MapSchoolSelector } from '@/components/map-school-selector';
import { isAuthenticated } from '@/lib/api/auth';

const DAY_LABELS = ['日', '月', '火', '水', '木', '金', '土'];

// 月末日のリストを生成（6ヶ月分）
const getEndOfMonthOptions = (): { value: string; label: string }[] => {
  const options: { value: string; label: string }[] = [];
  const today = new Date();

  for (let i = 0; i < 6; i++) {
    const date = new Date(today.getFullYear(), today.getMonth() + i + 1, 0); // 月末日
    const value = date.toISOString().split('T')[0];
    const label = `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
    options.push({ value, label });
  }

  return options;
};

// 年月選択肢を生成（1日付で保存）- 休会・復会用
const getYearMonthOptions = (startOffset: number = 0): { value: string; label: string }[] => {
  const options: { value: string; label: string }[] = [];
  const today = new Date();

  for (let i = startOffset; i < startOffset + 12; i++) {
    const date = new Date(today.getFullYear(), today.getMonth() + i, 1); // 月初1日
    // ローカルタイムゾーンで日付を文字列に変換（toISOStringはUTCなのでずれる）
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const value = `${year}-${month}-01`;
    const label = `${year}年${date.getMonth() + 1}月`;
    options.push({ value, label });
  }

  return options;
};

type ActionMode = 'list' | 'detail' | 'change-class' | 'change-school' | 'change-school-class' | 'suspend' | 'cancel' | 'confirm';

export default function ClassRegistrationPage() {
  const router = useRouter();
  const [mode, setMode] = useState<ActionMode>('list');
  const [selectedContract, setSelectedContract] = useState<MyContract | null>(null);

  // API data
  const [students, setStudents] = useState<MyStudent[]>([]);
  const [contracts, setContracts] = useState<MyContract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // クラス変更用
  const [classSchedules, setClassSchedules] = useState<ClassScheduleResponse | null>(null);
  const [loadingSchedules, setLoadingSchedules] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState<{
    dayOfWeek: number;
    startTime: string;
    scheduleId: string;
  } | null>(null);

  // 校舎変更用
  const [availableSchools, setAvailableSchools] = useState<BrandSchool[]>([]);
  const [loadingSchools, setLoadingSchools] = useState(false);
  const [selectedNewSchool, setSelectedNewSchool] = useState<BrandSchool | null>(null);
  const [newSchoolSchedules, setNewSchoolSchedules] = useState<ClassScheduleResponse | null>(null);
  const [selectedNewSchedule, setSelectedNewSchedule] = useState<{
    dayOfWeek: number;
    startTime: string;
    scheduleId: string;
  } | null>(null);

  // 休会申請用
  const [suspendFrom, setSuspendFrom] = useState<string>('');
  const [suspendUntil, setSuspendUntil] = useState<string>('');
  const [returnDay, setReturnDay] = useState<string>(''); // 復会日（任意）
  const [keepSeat, setKeepSeat] = useState<boolean>(false);
  const [billingConfirmed, setBillingConfirmed] = useState<boolean>(false);

  // 退会申請用
  const [cancelDate, setCancelDate] = useState<string>('');
  const [cancelReason, setCancelReason] = useState<string>('');

  // 認証チェック
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
    }
  }, [router]);

  // Load data on mount
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getMyContracts();
      setStudents(response.students || []);
      setContracts(response.contracts || []);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('データの読み込みに失敗しました');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 開講時間割取得（クラス変更用）
  const fetchClassSchedules = useCallback(async (contract: MyContract) => {
    if (!contract.school) {
      setError('校舎情報がありません');
      return;
    }
    try {
      setLoadingSchedules(true);
      // チケットコードがある場合はチケットでフィルタリング
      // ticketCodeはTi10000063などの形式でClassScheduleのticket_idと一致
      const ticketId = contract.ticket?.ticketCode;
      const response = await getClassSchedules(
        contract.school.id,
        contract.brand.id,
        undefined,  // brandCategoryId
        ticketId    // ticketId（実際はticketCode）
      );
      setClassSchedules(response);
    } catch (err) {
      console.error('Failed to fetch class schedules:', err);
      setError('開講時間割の取得に失敗しました');
    } finally {
      setLoadingSchedules(false);
    }
  }, []);

  // 校舎一覧取得（校舎変更用）
  const fetchAvailableSchools = useCallback(async (contract: MyContract) => {
    try {
      setLoadingSchools(true);
      const schools = await getBrandSchools(contract.brand.id);
      const filteredSchools = schools.filter(s => s.id !== contract.school?.id);
      setAvailableSchools(filteredSchools);
    } catch (err) {
      console.error('Failed to fetch schools:', err);
      setError('校舎情報の取得に失敗しました');
    } finally {
      setLoadingSchools(false);
    }
  }, []);

  // 新しい校舎の時間割を取得
  const fetchNewSchoolSchedules = useCallback(async (schoolId: string, brandId: string, ticketId?: string) => {
    try {
      setLoadingSchedules(true);
      const response = await getClassSchedules(
        schoolId,
        brandId,
        undefined,  // brandCategoryId
        ticketId    // ticketId
      );
      setNewSchoolSchedules(response);
    } catch (err) {
      console.error('Failed to fetch new school schedules:', err);
      setError('開講時間割の取得に失敗しました');
    } finally {
      setLoadingSchedules(false);
    }
  }, []);

  const handleContractSelect = (contract: MyContract) => {
    setSelectedContract(contract);
    setMode('detail');
  };

  const handleAction = async (action: 'change-class' | 'change-school' | 'suspend' | 'cancel') => {
    if (!selectedContract) return;

    if (action === 'change-class') {
      await fetchClassSchedules(selectedContract);
      setSelectedSchedule(null);
      setMode('change-class');
    } else if (action === 'change-school') {
      await fetchAvailableSchools(selectedContract);
      setSelectedNewSchool(null);
      setSelectedNewSchedule(null);
      setMode('change-school');
    } else if (action === 'suspend') {
      setSuspendFrom('');
      setSuspendUntil('');
      setReturnDay('');
      setKeepSeat(false);
      setBillingConfirmed(false);
      setMode('suspend');
    } else if (action === 'cancel') {
      setCancelDate('');
      setCancelReason('');
      setMode('cancel');
    }
  };

  // 校舎選択時
  const handleSelectNewSchool = async (schoolId: string) => {
    const school = availableSchools.find(s => s.id === schoolId);
    if (school && selectedContract) {
      setSelectedNewSchool(school);
      setSelectedNewSchedule(null);
      // チケットコードがある場合はチケットでフィルタリング
      const ticketId = selectedContract.ticket?.ticketCode;
      await fetchNewSchoolSchedules(school.id, selectedContract.brand.id, ticketId);
      setMode('change-school-class');
    }
  };

  // クラス変更確定
  const handleConfirmClassChange = async () => {
    if (!selectedContract || !selectedSchedule) return;

    setProcessing(true);
    setError(null);

    try {
      const response = await changeClass(selectedContract.id, {
        newDayOfWeek: selectedSchedule.dayOfWeek,
        newStartTime: selectedSchedule.startTime,
        newClassScheduleId: selectedSchedule.scheduleId,
      });
      setSuccessMessage(response.message);
      setMode('confirm');
    } catch (err) {
      console.error('Failed to change class:', err);
      setError('クラス変更に失敗しました');
    } finally {
      setProcessing(false);
    }
  };

  // 校舎変更確定
  const handleConfirmSchoolChange = async () => {
    if (!selectedContract || !selectedNewSchool || !selectedNewSchedule) return;

    setProcessing(true);
    setError(null);

    try {
      const response = await changeSchool(selectedContract.id, {
        newSchoolId: selectedNewSchool.id,
        newDayOfWeek: selectedNewSchedule.dayOfWeek,
        newStartTime: selectedNewSchedule.startTime,
        newClassScheduleId: selectedNewSchedule.scheduleId,
      });
      setSuccessMessage(response.message);
      setMode('confirm');
    } catch (err) {
      console.error('Failed to change school:', err);
      setError('校舎変更に失敗しました');
    } finally {
      setProcessing(false);
    }
  };

  // 休会申請確定
  const handleConfirmSuspension = async () => {
    if (!selectedContract || !suspendFrom || !suspendUntil || !billingConfirmed) return;

    setProcessing(true);
    setError(null);

    try {
      const response = await requestSuspension(selectedContract.id, {
        suspendFrom,
        suspendUntil,
        returnDay: returnDay || undefined,  // 復会日（任意）
        keepSeat,
        reason: '',
      });
      setSuccessMessage(response.message);
      setMode('confirm');
    } catch (err) {
      console.error('Failed to request suspension:', err);
      setError('休会申請に失敗しました');
    } finally {
      setProcessing(false);
    }
  };

  // 退会申請確定
  const handleConfirmCancellation = async () => {
    if (!selectedContract || !cancelDate) return;

    setProcessing(true);
    setError(null);

    try {
      const response = await requestCancellation(selectedContract.id, {
        cancelDate,
        reason: cancelReason,
      });
      setSuccessMessage(response.message);
      setMode('confirm');
    } catch (err) {
      console.error('Failed to request cancellation:', err);
      setError('退会申請に失敗しました');
    } finally {
      setProcessing(false);
    }
  };

  const handleBack = () => {
    if (mode === 'confirm') {
      setMode('list');
      setSelectedContract(null);
      loadData();
    } else if (mode === 'change-school-class') {
      setMode('change-school');
      setSelectedNewSchedule(null);
    } else if (['change-class', 'change-school', 'suspend', 'cancel'].includes(mode)) {
      setMode('detail');
    } else if (mode === 'detail') {
      setMode('list');
      setSelectedContract(null);
    }
  };

  const getStatusBadge = (status: MyContract['status']) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-green-500 text-white">受講中</Badge>;
      case 'paused':
        return <Badge className="bg-gray-500 text-white">休会中</Badge>;
      case 'cancelled':
        return <Badge className="bg-red-500 text-white">退会済</Badge>;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          <p className="text-gray-600">読み込み中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          {mode !== 'list' ? (
            <button onClick={handleBack} className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </button>
          ) : (
            <Link href="/" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
          )}
          <h1 className="text-xl font-bold text-gray-800">クラス管理</h1>
          {/* 注: URLはclass-registrationだがタイトルはクラス管理 */}
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        {error && (
          <Card className="rounded-xl shadow-md bg-red-50 border-red-200 mb-4">
            <CardContent className="p-4 flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
              <p className="text-red-600 text-sm">{error}</p>
            </CardContent>
          </Card>
        )}

        {successMessage && mode !== 'confirm' && (
          <Card className="rounded-xl shadow-md bg-green-50 border-green-200 mb-4">
            <CardContent className="p-4 flex items-center gap-3">
              <CheckCircle className="h-5 w-5 text-green-600 shrink-0" />
              <p className="text-green-600 text-sm">{successMessage}</p>
            </CardContent>
          </Card>
        )}

        {/* 受講中クラス一覧 */}
        {mode === 'list' && (
          <section>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">受講中のクラス</h2>

            {contracts.length === 0 ? (
              <Card className="rounded-xl shadow-md bg-gray-50 border-gray-200">
                <CardContent className="p-4 text-center">
                  <CalendarIcon className="h-10 w-10 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">受講中のクラスがありません</p>
                  <Link href="/ticket-purchase">
                    <Button className="mt-3" size="sm">コースを探す</Button>
                  </Link>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {contracts.map((contract) => (
                  <Card
                    key={contract.id}
                    className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                    onClick={() => handleContractSelect(contract)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <User className="h-5 w-5 text-blue-600" />
                          <span className="font-semibold text-gray-800">{contract.student.fullName}</span>
                        </div>
                        {getStatusBadge(contract.status)}
                      </div>

                      {/* コース/ブランド情報（メイン） */}
                      <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-3 mb-3">
                        <p className="text-xs text-blue-600 font-medium mb-1">{contract.brand.brandName}</p>
                        <p className="font-bold text-gray-800">
                          {contract.course?.courseName || contract.ticket?.ticketName || '未設定'}
                        </p>
                        {contract.ticket?.durationMinutes && (
                          <p className="text-sm text-gray-600">{contract.ticket.durationMinutes}分レッスン</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        {contract.school?.schoolName && (
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                          <MapPin className="h-4 w-4" />
                          <span>{contract.school.schoolName}</span>
                        </div>
                        )}
                        {contract.dayOfWeek !== undefined && contract.startTime && (
                          <div className="flex items-center gap-2 text-sm text-gray-600">
                            <Clock className="h-4 w-4" />
                            <span>{DAY_LABELS[contract.dayOfWeek]}曜日 {contract.startTime?.slice(0, 5)}〜{contract.endTime?.slice(0, 5)}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center justify-end mt-3">
                        <ChevronRight className="h-5 w-5 text-gray-400" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </section>
        )}

        {/* クラス詳細 */}
        {mode === 'detail' && selectedContract && (
          <section>
            <Card className="rounded-xl shadow-md mb-6">
              <CardContent className="p-4">
                <div className="space-y-4">
                  {/* 生徒情報 */}
                  <div className="flex items-center gap-3 p-3 bg-gray-100 rounded-lg">
                    <User className="h-5 w-5 text-blue-600" />
                    <div>
                      <p className="text-xs text-gray-500">生徒</p>
                      <p className="font-semibold text-gray-800">{selectedContract.student.fullName}</p>
                    </div>
                    {getStatusBadge(selectedContract.status)}
                  </div>

                  {/* コース情報（メイン） */}
                  <div className="bg-gradient-to-r from-blue-100 to-blue-200 rounded-lg p-4">
                    <p className="text-xs text-blue-700 font-medium mb-1">受講中のコース</p>
                    <p className="text-lg font-bold text-gray-800">
                      {selectedContract.course?.courseName || selectedContract.ticket?.ticketName || '未設定'}
                    </p>
                    {selectedContract.ticket?.durationMinutes && (
                      <p className="text-sm text-gray-600 mt-1">レッスン時間: {selectedContract.ticket.durationMinutes}分</p>
                    )}
                  </div>

                  <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <Building2 className="h-5 w-5 text-blue-600" />
                    <div>
                      <p className="text-xs text-gray-500">ブランド</p>
                      <p className="font-semibold text-gray-800">{selectedContract.brand.brandName}</p>
                    </div>
                  </div>

                  {selectedContract.school?.schoolName && (
                  <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <MapPin className="h-5 w-5 text-blue-600" />
                    <div>
                      <p className="text-xs text-gray-500">校舎</p>
                      <p className="font-semibold text-gray-800">{selectedContract.school.schoolName}</p>
                    </div>
                  </div>
                  )}

                  {selectedContract.dayOfWeek !== undefined && selectedContract.startTime && (
                    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <CalendarIcon className="h-5 w-5 text-blue-600" />
                      <div>
                        <p className="text-xs text-gray-500">クラス・時間</p>
                        <p className="font-semibold text-gray-800">
                          {DAY_LABELS[selectedContract.dayOfWeek]}曜日 {selectedContract.startTime?.slice(0, 5)}〜{selectedContract.endTime?.slice(0, 5)}
                        </p>
                      </div>
                    </div>
                  )}

                  {selectedContract.startDate && (
                    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <Clock className="h-5 w-5 text-blue-600" />
                      <div>
                        <p className="text-xs text-gray-500">受講開始日</p>
                        <p className="font-semibold text-gray-800">
                          {format(new Date(selectedContract.startDate), 'yyyy年MM月dd日', { locale: ja })}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <h3 className="text-md font-semibold text-gray-700 mb-3">変更・手続き</h3>
            <div className="space-y-3">
              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => handleAction('change-class')}
              >
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                      <RefreshCw className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-800">クラス変更</p>
                      <p className="text-xs text-gray-500">曜日・時間帯を変更</p>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </CardContent>
              </Card>

              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => handleAction('change-school')}
              >
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                      <MapPin className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-800">校舎変更</p>
                      <p className="text-xs text-gray-500">通う校舎を変更</p>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </CardContent>
              </Card>

              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => handleAction('suspend')}
              >
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center">
                      <PauseCircle className="h-5 w-5 text-yellow-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-800">休会</p>
                      <p className="text-xs text-gray-500">一時的に休会する</p>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </CardContent>
              </Card>

              <Card
                className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer border-red-100"
                onClick={() => handleAction('cancel')}
              >
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                      <LogOut className="h-5 w-5 text-red-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-red-700">退会</p>
                      <p className="text-xs text-gray-500">コースを退会する</p>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </CardContent>
              </Card>
            </div>
          </section>
        )}

        {/* クラス変更 */}
        {mode === 'change-class' && selectedContract && (() => {
          const dayLabels = classSchedules?.dayLabels || ['月', '火', '水', '木', '金', '土', '日'];

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

          const handleTimeSlotSelect = (time: string, dayLabel: string) => {
            const timeSlot = classSchedules?.timeSlots.find(ts => ts.time === time);
            if (!timeSlot) return;
            const dayData = timeSlot.days[dayLabel];
            if (!dayData || dayData.status === 'none' || dayData.status === 'full' || dayData.schedules.length === 0) return;

            const schedule = dayData.schedules[0];
            // 月=1, 火=2... の形式で曜日番号を計算
            const dayIdx = dayLabels.indexOf(dayLabel);
            const dayOfWeekNum = dayIdx === dayLabels.length - 1 ? 0 : dayIdx + 1; // 日曜=0, 月曜=1...

            setSelectedSchedule({
              dayOfWeek: dayOfWeekNum,
              startTime: schedule.startTime,
              scheduleId: schedule.id,
            });
          };

          return (
          <section className="space-y-4">
            <div className="bg-blue-100 rounded-lg p-3 mb-4">
              <p className="text-sm text-blue-800">
                <span className="font-semibold">クラス変更</span>
              </p>
              <p className="text-xs text-blue-700 mt-1">
                現在: {selectedContract.school?.schoolName || '未設定'} / {selectedContract.dayOfWeek !== undefined && selectedContract.dayOfWeek !== null ? `${DAY_LABELS[selectedContract.dayOfWeek]}曜日 ${selectedContract.startTime?.slice(0, 5) || ''}` : '未設定'}
              </p>
            </div>

            <h2 className="text-lg font-semibold text-gray-800">新しい曜日・時間を選択</h2>

            {/* 凡例 */}
            <div className="flex items-center justify-center gap-4 text-sm mb-2">
              <div className="flex items-center gap-1">
                <Circle className="h-4 w-4 text-green-600 fill-green-600" />
                <span>空きあり</span>
              </div>
              <div className="flex items-center gap-1">
                <Triangle className="h-4 w-4 text-orange-500 fill-orange-500" />
                <span>残りわずか</span>
              </div>
              <div className="flex items-center gap-1">
                <XIcon className="h-4 w-4 text-red-600" />
                <span>満席</span>
              </div>
            </div>

            {loadingSchedules ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-3" />
                <p className="text-sm text-gray-600">開講時間割を読み込み中...</p>
              </div>
            ) : classSchedules && classSchedules.timeSlots.length > 0 ? (
              <Card className="rounded-xl shadow-md overflow-hidden">
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
                        {[...classSchedules.timeSlots].sort((a, b) => a.time.localeCompare(b.time)).map((timeSlot, timeIdx) => (
                          <tr key={timeIdx} className="border-b border-gray-200 hover:bg-gray-50">
                            <td className="text-xs font-semibold py-3 px-2 bg-gray-50 sticky left-0 z-10">
                              {timeSlot.time}
                            </td>
                            {dayLabels.map((label, dayIdx) => {
                              const dayData = timeSlot.days[label];
                              const status = dayData?.status || 'none';
                              const canSelect = status !== 'none' && status !== 'full';
                              // 選択中の判定
                              const dayOfWeekNum = dayIdx === dayLabels.length - 1 ? 0 : dayIdx + 1;
                              const isSelected = selectedSchedule?.dayOfWeek === dayOfWeekNum &&
                                                 selectedSchedule?.startTime?.slice(0, 5) === timeSlot.time;
                              // 現在の曜日・時間の判定
                              const isCurrent = selectedContract.dayOfWeek === dayOfWeekNum &&
                                                selectedContract.startTime?.slice(0, 5) === timeSlot.time;

                              return (
                                <td
                                  key={dayIdx}
                                  className={`text-center py-3 px-2 ${canSelect ? 'cursor-pointer hover:bg-blue-50' : ''
                                    } ${isSelected ? 'bg-blue-100 ring-2 ring-blue-500 ring-inset' : ''
                                    } ${isCurrent ? 'bg-green-100' : ''
                                    }`}
                                  onClick={() => {
                                    if (canSelect) {
                                      handleTimeSlotSelect(timeSlot.time, label);
                                    }
                                  }}
                                >
                                  <div className="flex flex-col items-center">
                                    {getStatusIcon(status)}
                                    {isCurrent && <span className="text-[10px] text-green-700 mt-0.5">現在</span>}
                                  </div>
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
            ) : (
              <Card>
                <CardContent className="p-4 text-center">
                  <CalendarIcon className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">開講時間割がありません</p>
                </CardContent>
              </Card>
            )}

            {/* 選択中の情報 */}
            {selectedSchedule && (
              <Card className="rounded-xl shadow-sm bg-blue-50 border-blue-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">変更後のクラス</p>
                  <p className="font-semibold text-gray-800">
                    {DAY_LABELS[selectedSchedule.dayOfWeek]}曜日 {selectedSchedule.startTime.slice(0, 5)}〜
                  </p>
                </CardContent>
              </Card>
            )}

            {selectedSchedule && (
              <div className="mt-4">
                <Button
                  className="w-full bg-blue-600 hover:bg-blue-700"
                  onClick={handleConfirmClassChange}
                  disabled={processing}
                >
                  {processing ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      処理中...
                    </>
                  ) : (
                    'クラス変更を確定する'
                  )}
                </Button>
                <p className="text-xs text-gray-500 text-center mt-2">
                  ※ 変更は翌週から適用されます
                </p>
              </div>
            )}
          </section>
          );
        })()}

        {/* 校舎変更 - 校舎選択 */}
        {mode === 'change-school' && selectedContract && (
          <section className="space-y-4">
            <div className="bg-purple-100 rounded-lg p-3 mb-4">
              <p className="text-sm text-purple-800">
                <span className="font-semibold">校舎変更</span> - 校舎選択
              </p>
              <p className="text-xs text-purple-700 mt-1">
                現在: {selectedContract.school?.schoolName || '未設定'}
              </p>
            </div>

            <h2 className="text-lg font-semibold text-gray-800">新しい校舎を選択</h2>

            {loadingSchools ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
              </div>
            ) : availableSchools.length > 0 ? (
              <>
                <MapSchoolSelector
                  schools={availableSchools}
                  selectedSchoolId={selectedNewSchool?.id || null}
                  onSelectSchool={handleSelectNewSchool}
                />
                <div className="mt-4 space-y-2">
                  <h3 className="text-sm font-semibold text-gray-700">校舎一覧</h3>
                  {availableSchools.map((school) => (
                    <Card
                      key={school.id}
                      className={`cursor-pointer transition-all ${
                        selectedNewSchool?.id === school.id
                          ? 'border-2 border-purple-500 bg-purple-50'
                          : 'hover:shadow-md'
                      }`}
                      onClick={() => handleSelectNewSchool(school.id)}
                    >
                      <CardContent className="p-3">
                        <div className="flex justify-between items-center">
                          <div>
                            <h4 className="font-semibold text-gray-900">{school.name}</h4>
                            <p className="text-xs text-gray-500">{school.address}</p>
                          </div>
                          {selectedNewSchool?.id === school.id && (
                            <CheckCircle className="w-5 h-5 text-purple-500" />
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </>
            ) : (
              <Card>
                <CardContent className="p-4 text-center">
                  <MapPin className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">他に開講校舎がありません</p>
                </CardContent>
              </Card>
            )}
          </section>
        )}

        {/* 校舎変更 - クラス選択 */}
        {mode === 'change-school-class' && selectedContract && selectedNewSchool && (() => {
          const dayLabels = newSchoolSchedules?.dayLabels || ['月', '火', '水', '木', '金', '土', '日'];

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

          const handleTimeSlotSelect = (time: string, dayLabel: string) => {
            const timeSlot = newSchoolSchedules?.timeSlots.find(ts => ts.time === time);
            if (!timeSlot) return;
            const dayData = timeSlot.days[dayLabel];
            if (!dayData || dayData.status === 'none' || dayData.status === 'full' || dayData.schedules.length === 0) return;

            const schedule = dayData.schedules[0];
            const dayIdx = dayLabels.indexOf(dayLabel);
            const dayOfWeekNum = dayIdx === dayLabels.length - 1 ? 0 : dayIdx + 1;

            setSelectedNewSchedule({
              dayOfWeek: dayOfWeekNum,
              startTime: schedule.startTime,
              scheduleId: schedule.id,
            });
          };

          return (
          <section className="space-y-4">
            <div className="bg-purple-100 rounded-lg p-3 mb-4">
              <p className="text-sm text-purple-800">
                <span className="font-semibold">校舎変更</span> - クラス選択
              </p>
              <p className="text-xs text-purple-700 mt-1">
                {selectedContract.school?.schoolName || '未設定'} → {selectedNewSchool.name}
              </p>
            </div>

            <h2 className="text-lg font-semibold text-gray-800">{selectedNewSchool.name}のクラスを選択</h2>

            {/* 凡例 */}
            <div className="flex items-center justify-center gap-4 text-sm mb-2">
              <div className="flex items-center gap-1">
                <Circle className="h-4 w-4 text-green-600 fill-green-600" />
                <span>空きあり</span>
              </div>
              <div className="flex items-center gap-1">
                <Triangle className="h-4 w-4 text-orange-500 fill-orange-500" />
                <span>残りわずか</span>
              </div>
              <div className="flex items-center gap-1">
                <XIcon className="h-4 w-4 text-red-600" />
                <span>満席</span>
              </div>
            </div>

            {loadingSchedules ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-purple-500 mb-3" />
                <p className="text-sm text-gray-600">開講時間割を読み込み中...</p>
              </div>
            ) : newSchoolSchedules && newSchoolSchedules.timeSlots.length > 0 ? (
              <Card className="rounded-xl shadow-md overflow-hidden">
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-gradient-to-r from-purple-600 to-purple-700 text-white">
                          <th className="text-xs font-semibold py-3 px-2 text-left sticky left-0 bg-purple-600 z-10">時間</th>
                          {dayLabels.map((label, idx) => (
                            <th key={idx} className="text-xs font-semibold py-3 px-2 text-center min-w-[50px]">
                              {label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {newSchoolSchedules.timeSlots.map((timeSlot, timeIdx) => (
                          <tr key={timeIdx} className="border-b border-gray-200 hover:bg-gray-50">
                            <td className="text-xs font-semibold py-3 px-2 bg-gray-50 sticky left-0 z-10">
                              {timeSlot.time}
                            </td>
                            {dayLabels.map((label, dayIdx) => {
                              const dayData = timeSlot.days[label];
                              const status = dayData?.status || 'none';
                              const canSelect = status !== 'none' && status !== 'full';
                              const dayOfWeekNum = dayIdx === dayLabels.length - 1 ? 0 : dayIdx + 1;
                              const isSelected = selectedNewSchedule?.dayOfWeek === dayOfWeekNum &&
                                                 selectedNewSchedule?.startTime?.slice(0, 5) === timeSlot.time;

                              return (
                                <td
                                  key={dayIdx}
                                  className={`text-center py-3 px-2 ${canSelect ? 'cursor-pointer hover:bg-purple-50' : ''
                                    } ${isSelected ? 'bg-purple-100 ring-2 ring-purple-500 ring-inset' : ''
                                    }`}
                                  onClick={() => {
                                    if (canSelect) {
                                      handleTimeSlotSelect(timeSlot.time, label);
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
            ) : (
              <Card>
                <CardContent className="p-4 text-center">
                  <CalendarIcon className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">この校舎では開講していません</p>
                </CardContent>
              </Card>
            )}

            {/* 選択中の情報 */}
            {selectedNewSchedule && (
              <Card className="rounded-xl shadow-sm bg-purple-50 border-purple-200">
                <CardContent className="p-3">
                  <p className="text-xs text-gray-600 mb-1">変更後のクラス</p>
                  <p className="font-semibold text-gray-800">
                    {selectedNewSchool.name} / {DAY_LABELS[selectedNewSchedule.dayOfWeek]}曜日 {selectedNewSchedule.startTime.slice(0, 5)}〜
                  </p>
                </CardContent>
              </Card>
            )}

            {selectedNewSchedule && (
              <div className="mt-4">
                <Button
                  className="w-full bg-purple-600 hover:bg-purple-700"
                  onClick={handleConfirmSchoolChange}
                  disabled={processing}
                >
                  {processing ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      処理中...
                    </>
                  ) : (
                    '校舎変更を確定する'
                  )}
                </Button>
                <p className="text-xs text-gray-500 text-center mt-2">
                  ※ 変更は翌週から適用されます
                </p>
              </div>
            )}
          </section>
          );
        })()}

        {/* 休会申請 */}
        {mode === 'suspend' && selectedContract && (
          <section className="space-y-4">
            <div className="bg-orange-100 rounded-lg p-3 mb-4">
              <p className="text-sm text-orange-800">
                <span className="font-semibold">休会申請</span>
              </p>
              <p className="text-xs text-orange-700 mt-1">
                {selectedContract.brand?.brandName || ''} / {selectedContract.school?.schoolName || '未設定'}
              </p>
            </div>

            <Card className="rounded-xl shadow-md">
              <CardContent className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    休会開始月 <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={suspendFrom}
                    onChange={(e) => {
                      setSuspendFrom(e.target.value);
                      setSuspendUntil('');
                    }}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  >
                    <option value="">選択してください</option>
                    {getYearMonthOptions(1).map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    選択した月から休会となります
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    復会月 <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={suspendUntil}
                    onChange={(e) => {
                      setSuspendUntil(e.target.value);
                      setReturnDay('');
                    }}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  >
                    <option value="">選択してください</option>
                    {getYearMonthOptions(2)
                      .filter((option) => !suspendFrom || option.value > suspendFrom)
                      .map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    選択した月から復会となります
                  </p>
                </div>

                {suspendUntil && (
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      復会日（任意）
                    </label>
                    <input
                      type="date"
                      value={returnDay}
                      onChange={(e) => setReturnDay(e.target.value)}
                      min={suspendUntil}
                      max={(() => {
                        const [year, month] = suspendUntil.split('-').map(Number);
                        const lastDay = new Date(year, month, 0).getDate();
                        return `${year}-${String(month).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
                      })()}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {(() => {
                        const [year, month] = suspendUntil.split('-').map(Number);
                        return `${year}年${month}月内の日付を選択できます（未選択は月初扱い）`;
                      })()}
                    </p>
                  </div>
                )}

                <div className="bg-orange-50 p-4 rounded-lg">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={keepSeat}
                      onChange={(e) => setKeepSeat(e.target.checked)}
                      className="mt-1 h-5 w-5 rounded border-gray-300 text-orange-500 focus:ring-orange-500"
                    />
                    <div>
                      <span className="font-semibold text-gray-800">席を残す</span>
                      <p className="text-sm text-gray-600 mt-1">
                        休会中も座席を確保し、再開時に同じクラスに戻れます
                      </p>
                      <p className="text-sm text-orange-600 font-semibold mt-1">
                        ※ 座席保持料：月額800円
                      </p>
                    </div>
                  </label>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={billingConfirmed}
                      onChange={(e) => setBillingConfirmed(e.target.checked)}
                      className="mt-1 h-5 w-5 rounded border-gray-300 text-blue-500 focus:ring-blue-500"
                    />
                    <div>
                      <span className="font-semibold text-gray-800">復会月から請求が開始されることを確認しました</span>
                      <p className="text-sm text-gray-600 mt-1">
                        {suspendUntil && (() => {
                          const date = new Date(suspendUntil);
                          return `${date.getFullYear()}年${date.getMonth() + 1}月分から請求が再開されます`;
                        })()}
                      </p>
                    </div>
                  </label>
                </div>
              </CardContent>
            </Card>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <div className="flex gap-2">
                <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0" />
                <div className="text-sm text-yellow-800">
                  <p className="font-semibold">ご注意</p>
                  <p>休会申請はスタッフの承認後に確定します。</p>
                </div>
              </div>
            </div>

            {suspendFrom && suspendUntil && billingConfirmed && (
              <Button
                className="w-full bg-orange-500 hover:bg-orange-600"
                onClick={handleConfirmSuspension}
                disabled={processing}
              >
                {processing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    処理中...
                  </>
                ) : (
                  '休会を申請する'
                )}
              </Button>
            )}
          </section>
        )}

        {/* 退会申請 */}
        {mode === 'cancel' && selectedContract && (
          <section className="space-y-4">
            <div className="bg-red-100 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-800">
                <span className="font-semibold">退会申請</span>
              </p>
              <p className="text-xs text-red-700 mt-1">
                {selectedContract.brand?.brandName || ''} / {selectedContract.school?.schoolName || '未設定'}
              </p>
            </div>

            <Card className="rounded-xl shadow-md">
              <CardContent className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    退会日（月末） <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={cancelDate}
                    onChange={(e) => setCancelDate(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  >
                    <option value="">選択してください</option>
                    {getEndOfMonthOptions().map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    退会は月末付けとなります
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    退会理由（任意）
                  </label>
                  <textarea
                    value={cancelReason}
                    onChange={(e) => setCancelReason(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    rows={3}
                    placeholder="差し支えなければ、退会理由をお聞かせください"
                  />
                </div>
              </CardContent>
            </Card>

            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="flex gap-2">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                <div className="text-sm text-red-800">
                  <p className="font-semibold">ご注意</p>
                  <ul className="list-disc list-inside mt-1 space-y-1">
                    <li>退会申請はスタッフの承認後に確定します</li>
                    <li>退会後の再入会には入会金が必要になる場合があります</li>
                    <li>未使用のチケットは退会日まで使用可能です</li>
                  </ul>
                </div>
              </div>
            </div>

            {cancelDate && (
              <Button
                className="w-full bg-red-500 hover:bg-red-600"
                onClick={handleConfirmCancellation}
                disabled={processing}
              >
                {processing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    処理中...
                  </>
                ) : (
                  '退会を申請する'
                )}
              </Button>
            )}
          </section>
        )}

        {/* 完了画面 */}
        {mode === 'confirm' && (
          <section>
            <Card className="rounded-xl shadow-md border-green-200 bg-green-50">
              <CardContent className="p-4 text-center">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <h2 className="text-lg font-bold text-green-800 mb-2">申請完了</h2>
                <p className="text-sm text-green-700">{successMessage}</p>
              </CardContent>
            </Card>
            <Button
              className="w-full mt-4"
              onClick={() => router.push('/feed')}
            >
              ホームに戻る
            </Button>
          </section>
        )}
      </main>

      <BottomTabBar />
    </div>
  );
}
