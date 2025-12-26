'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { isAuthenticated } from '@/lib/api/auth';
import {
  getMyContracts,
  changeClass,
  changeSchool,
  requestSuspension,
  requestCancellation,
  type MyContract,
  type MyStudent,
} from '@/lib/api/contracts';
import { getClassSchedules, getSchoolsByTicket, type ClassScheduleResponse, type ClassScheduleItem, type BrandSchool } from '@/lib/api/schools';
import { getAbsenceTickets, getTransferAvailableClasses, useAbsenceTicket, type AbsenceTicket, type TransferAvailableClass } from '@/lib/api/lessons';
import { MapSchoolSelector } from '@/components/map-school-selector';
import {
  ChevronLeft,
  ChevronRight,
  Calendar,
  MapPin,
  Clock,
  Users,
  AlertCircle,
  CheckCircle,
  Loader2,
  Settings,
  PauseCircle,
  XCircle,
  Circle,
  Triangle,
  X as XIcon,
  Minus,
  RefreshCw,
  Ticket,
} from 'lucide-react';

// 曜日ラベル
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

// ブランドのソート順を定義
const BRAND_SORT_ORDER: Record<string, number> = {
  'AEC': 1,  // 英語
  'SOR': 2,  // そろばん
  'BMC': 3,  // 書写
  'PRO': 4,  // プログラミング
  'SHO': 5,  // 習い事
  'KID': 6,  // キッズ
  'INT': 7,  // インターナショナル
};

const getBrandSortOrder = (brandCode?: string): number => {
  if (!brandCode) return 999;
  return BRAND_SORT_ORDER[brandCode] ?? 999;
};

// 契約を校舎→ブランド→曜日→時間の順でソート
const sortContracts = (contracts: MyContract[]): MyContract[] => {
  return [...contracts].sort((a, b) => {
    // 1. 校舎名でソート
    const schoolNameA = a.school?.schoolName || '';
    const schoolNameB = b.school?.schoolName || '';
    if (schoolNameA !== schoolNameB) {
      return schoolNameA.localeCompare(schoolNameB, 'ja');
    }

    // 2. ブランドコードでソート
    const brandCodeA = a.brand?.brandCode || '';
    const brandCodeB = b.brand?.brandCode || '';
    const brandOrderA = getBrandSortOrder(brandCodeA);
    const brandOrderB = getBrandSortOrder(brandCodeB);
    if (brandOrderA !== brandOrderB) {
      return brandOrderA - brandOrderB;
    }

    // 3. 曜日でソート
    const dayOfWeekA = a.dayOfWeek ?? 7;
    const dayOfWeekB = b.dayOfWeek ?? 7;
    if (dayOfWeekA !== dayOfWeekB) {
      return dayOfWeekA - dayOfWeekB;
    }

    // 4. 開始時間でソート
    const startTimeA = a.startTime || '99:99';
    const startTimeB = b.startTime || '99:99';
    return startTimeA.localeCompare(startTimeB);
  });
};

// 校舎を校舎名順でソート
const sortSchools = (schools: BrandSchool[]): BrandSchool[] => {
  return [...schools].sort((a, b) => {
    // sortOrderがあれば優先
    const orderA = a.sortOrder ?? 9999;
    const orderB = b.sortOrder ?? 9999;
    if (orderA !== orderB) {
      return orderA - orderB;
    }
    // 次に名前でソート
    return a.name.localeCompare(b.name, 'ja');
  });
};

// ステップ定義
type Step = 'select-child' | 'select-contract' | 'select-action' | 'change-class' | 'change-school' | 'request-suspension' | 'request-cancellation' | 'transfer-reservation' | 'confirm';

// アクション定義
type ActionType = 'change-class' | 'change-school' | 'request-suspension' | 'request-cancellation' | 'transfer-reservation';

export default function ClassManagementPage() {
  const router = useRouter();
  const [authChecking, setAuthChecking] = useState(true);

  // データ
  const [students, setStudents] = useState<MyStudent[]>([]);
  const [contracts, setContracts] = useState<MyContract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 選択状態
  const [step, setStep] = useState<Step>('select-child');
  const [selectedStudent, setSelectedStudent] = useState<MyStudent | null>(null);
  const [selectedContract, setSelectedContract] = useState<MyContract | null>(null);
  const [selectedAction, setSelectedAction] = useState<ActionType | null>(null);

  // クラス変更用
  const [classSchedules, setClassSchedules] = useState<ClassScheduleResponse | null>(null);
  const [loadingSchedules, setLoadingSchedules] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState<{
    dayOfWeek: number;
    startTime: string;
    scheduleId: string;
  } | null>(null);

  // 校舎変更用
  const [schoolChangeStep, setSchoolChangeStep] = useState<'select-school' | 'select-class'>('select-school');
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
  const [keepSeat, setKeepSeat] = useState<boolean>(false);
  const [suspendReason, setSuspendReason] = useState<string>('');

  // 退会申請用
  const [cancelDate, setCancelDate] = useState<string>('');
  const [cancelReason, setCancelReason] = useState<string>('');

  // 振替予約用
  const [absenceTickets, setAbsenceTickets] = useState<AbsenceTicket[]>([]);
  const [selectedAbsenceTicket, setSelectedAbsenceTicket] = useState<AbsenceTicket | null>(null);
  const [transferAvailableClasses, setTransferAvailableClasses] = useState<TransferAvailableClass[]>([]);
  const [selectedTransferClass, setSelectedTransferClass] = useState<TransferAvailableClass | null>(null);
  const [transferDate, setTransferDate] = useState<string>('');
  const [loadingTickets, setLoadingTickets] = useState(false);
  const [loadingTransferClasses, setLoadingTransferClasses] = useState(false);
  const [transferStep, setTransferStep] = useState<'select-ticket' | 'select-class' | 'select-date'>('select-ticket');

  // 処理状態
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [submitMessage, setSubmitMessage] = useState('');

  // 認証チェック
  useEffect(() => {
    const checkAuth = async () => {
      if (!isAuthenticated()) {
        router.push('/login');
        return;
      }
      setAuthChecking(false);
    };
    checkAuth();
  }, [router]);

  // 契約データ取得
  const fetchContracts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getMyContracts();
      setStudents(response.students || []);
      setContracts(response.contracts || []);
    } catch (err) {
      console.error('Failed to fetch contracts:', err);
      setError('契約情報の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authChecking) {
      fetchContracts();
    }
  }, [authChecking, fetchContracts]);

  // 開講時間割取得（チケットでフィルタリング）
  const fetchClassSchedules = useCallback(async (contract: MyContract) => {
    if (!contract.school) {
      setError('校舎情報がありません');
      return;
    }
    try {
      setLoadingSchedules(true);
      // チケットコードがある場合はチケットでフィルタリング
      const ticketId = contract.ticket?.ticketCode;
      const response = await getClassSchedules(
        contract.school.id,
        contract.brand.id,
        undefined,  // brandCategoryId
        ticketId    // ticketId
      );
      setClassSchedules(response);
    } catch (err) {
      console.error('Failed to fetch class schedules:', err);
      setError('開講時間割の取得に失敗しました');
    } finally {
      setLoadingSchedules(false);
    }
  }, []);

  // 子ども選択
  const handleSelectStudent = (student: MyStudent) => {
    setSelectedStudent(student);
    setStep('select-contract');
  };

  // 契約選択
  const handleSelectContract = (contract: MyContract) => {
    setSelectedContract(contract);
    setStep('select-action');
  };

  // 校舎一覧取得（校舎変更用）
  const fetchAvailableSchools = useCallback(async (contract: MyContract) => {
    try {
      setLoadingSchools(true);
      // チケットIDで開講校舎を取得（チケットがない場合はブランドIDで取得）
      const ticketCode = contract.ticket?.ticketCode;
      const schools = ticketCode
        ? await getSchoolsByTicket(ticketCode, contract.brand.id)
        : await getSchoolsByTicket(contract.brand.id);
      // 現在の校舎を除外してソート
      const filteredSchools = schools.filter(s => s.id !== contract.school?.id);
      setAvailableSchools(sortSchools(filteredSchools));
    } catch (err) {
      console.error('Failed to fetch schools:', err);
      setError('校舎情報の取得に失敗しました');
    } finally {
      setLoadingSchools(false);
    }
  }, []);

  // 新しい校舎の時間割を取得（チケットでフィルタリング）
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

  // アクション選択
  const handleSelectAction = async (action: ActionType) => {
    setSelectedAction(action);
    if (action === 'change-class' && selectedContract) {
      await fetchClassSchedules(selectedContract);
    }
    if (action === 'change-school' && selectedContract) {
      setSchoolChangeStep('select-school');
      setSelectedNewSchool(null);
      setSelectedNewSchedule(null);
      await fetchAvailableSchools(selectedContract);
    }
    if (action === 'transfer-reservation') {
      setTransferStep('select-ticket');
      setSelectedAbsenceTicket(null);
      setSelectedTransferClass(null);
      setTransferDate('');
      await fetchAbsenceTickets();
    }
    setStep(action);
  };

  // クラス変更の確定
  const handleConfirmClassChange = async () => {
    if (!selectedContract || !selectedSchedule) return;

    try {
      setSubmitting(true);
      const response = await changeClass(selectedContract.id, {
        newDayOfWeek: selectedSchedule.dayOfWeek,
        newStartTime: selectedSchedule.startTime,
        newClassScheduleId: selectedSchedule.scheduleId,
      });
      setSubmitSuccess(true);
      setSubmitMessage(response.message);
      setStep('confirm');
    } catch (err) {
      console.error('Failed to change class:', err);
      setError('クラス変更に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  // 校舎選択時の処理
  const handleSelectNewSchool = async (schoolId: string) => {
    const school = availableSchools.find(s => s.id === schoolId);
    if (school && selectedContract) {
      setSelectedNewSchool(school);
      setSelectedNewSchedule(null);
      // チケットコードがある場合はチケットでフィルタリング
      const ticketId = selectedContract.ticket?.ticketCode;
      await fetchNewSchoolSchedules(school.id, selectedContract.brand.id, ticketId);
      setSchoolChangeStep('select-class');
    }
  };

  // 校舎変更の確定
  const handleConfirmSchoolChange = async () => {
    if (!selectedContract || !selectedNewSchool || !selectedNewSchedule) return;

    try {
      setSubmitting(true);
      const response = await changeSchool(selectedContract.id, {
        newSchoolId: selectedNewSchool.id,
        newDayOfWeek: selectedNewSchedule.dayOfWeek,
        newStartTime: selectedNewSchedule.startTime,
        newClassScheduleId: selectedNewSchedule.scheduleId,
      });
      setSubmitSuccess(true);
      setSubmitMessage(response.message);
      setStep('confirm');
    } catch (err) {
      console.error('Failed to change school:', err);
      setError('校舎変更に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  // 休会申請の確定
  const handleConfirmSuspension = async () => {
    if (!selectedContract || !suspendFrom) return;

    try {
      setSubmitting(true);
      const response = await requestSuspension(selectedContract.id, {
        suspendFrom,
        suspendUntil: suspendUntil || undefined,
        keepSeat,
        reason: suspendReason,
      });
      setSubmitSuccess(true);
      setSubmitMessage(response.message);
      setStep('confirm');
    } catch (err) {
      console.error('Failed to request suspension:', err);
      setError('休会申請に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  // 退会申請の確定
  const handleConfirmCancellation = async () => {
    if (!selectedContract || !cancelDate) return;

    try {
      setSubmitting(true);
      const response = await requestCancellation(selectedContract.id, {
        cancelDate,
        reason: cancelReason,
      });
      setSubmitSuccess(true);
      setSubmitMessage(response.message);
      setStep('confirm');
    } catch (err) {
      console.error('Failed to request cancellation:', err);
      setError('退会申請に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  // 欠席チケット一覧取得
  const fetchAbsenceTickets = useCallback(async () => {
    try {
      setLoadingTickets(true);
      const tickets = await getAbsenceTickets('issued');
      setAbsenceTickets(tickets);
    } catch (err) {
      console.error('Failed to fetch absence tickets:', err);
      setError('欠席チケットの取得に失敗しました');
    } finally {
      setLoadingTickets(false);
    }
  }, []);

  // 振替可能クラス取得
  const fetchTransferClasses = useCallback(async (ticketId: string) => {
    try {
      setLoadingTransferClasses(true);
      const classes = await getTransferAvailableClasses(ticketId);
      setTransferAvailableClasses(classes);
    } catch (err) {
      console.error('Failed to fetch transfer classes:', err);
      setError('振替可能クラスの取得に失敗しました');
    } finally {
      setLoadingTransferClasses(false);
    }
  }, []);

  // 欠席チケット選択
  const handleSelectAbsenceTicket = async (ticket: AbsenceTicket) => {
    setSelectedAbsenceTicket(ticket);
    await fetchTransferClasses(ticket.id);
    setTransferStep('select-class');
  };

  // 振替クラス選択
  const handleSelectTransferClass = (cls: TransferAvailableClass) => {
    setSelectedTransferClass(cls);
    setTransferStep('select-date');
  };

  // 振替予約の確定
  const handleConfirmTransfer = async () => {
    if (!selectedAbsenceTicket || !selectedTransferClass || !transferDate) return;

    try {
      setSubmitting(true);
      const response = await useAbsenceTicket({
        absenceTicketId: selectedAbsenceTicket.id,
        targetDate: transferDate,
        targetClassScheduleId: selectedTransferClass.id,
      });
      setSubmitSuccess(true);
      setSubmitMessage(response.message);
      setStep('confirm');
    } catch (err) {
      console.error('Failed to make transfer reservation:', err);
      setError('振替予約に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  // 戻るボタン
  const handleBack = () => {
    switch (step) {
      case 'select-contract':
        setSelectedStudent(null);
        setStep('select-child');
        break;
      case 'select-action':
        setSelectedContract(null);
        setStep('select-contract');
        break;
      case 'change-class':
        setSelectedAction(null);
        setSelectedSchedule(null);
        setStep('select-action');
        break;
      case 'change-school':
        if (schoolChangeStep === 'select-class') {
          // 時間割選択から校舎選択に戻る
          setSchoolChangeStep('select-school');
          setSelectedNewSchedule(null);
        } else {
          // 校舎選択からアクション選択に戻る
          setSelectedAction(null);
          setSelectedNewSchool(null);
          setSelectedNewSchedule(null);
          setStep('select-action');
        }
        break;
      case 'request-suspension':
      case 'request-cancellation':
        setSelectedAction(null);
        setSelectedSchedule(null);
        setStep('select-action');
        break;
      case 'transfer-reservation':
        if (transferStep === 'select-date') {
          setTransferStep('select-class');
          setTransferDate('');
        } else if (transferStep === 'select-class') {
          setTransferStep('select-ticket');
          setSelectedTransferClass(null);
        } else {
          setSelectedAction(null);
          setSelectedAbsenceTicket(null);
          setStep('select-action');
        }
        break;
      case 'confirm':
        router.push('/feed');
        break;
    }
  };

  // フィルタリング（校舎→ブランド→曜日→時間の順でソート）
  const studentContracts = selectedStudent
    ? sortContracts(contracts.filter(c => c.student.id === selectedStudent.id))
    : [];

  if (authChecking || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-green-50 to-green-100 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-green-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-green-50 to-green-100 pb-20">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <div className="flex items-center gap-2">
              {step !== 'select-child' && step !== 'confirm' && (
                <button onClick={handleBack} className="p-1">
                  <ChevronLeft className="w-6 h-6 text-gray-600" />
                </button>
              )}
              <Settings className="w-6 h-6 text-green-600" />
              <h1 className="text-xl font-bold text-gray-900">クラス管理</h1>
            </div>
            <div className="flex gap-1 mt-3">
              {['select-child', 'select-contract', 'select-action', 'change-class'].map((s, i) => (
                <div
                  key={s}
                  className={`h-1 flex-1 rounded ${
                    ['select-child', 'select-contract', 'select-action', 'change-class', 'change-school', 'request-suspension', 'request-cancellation', 'confirm'].indexOf(step) >= i
                      ? 'bg-green-500'
                      : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-4">
          {error && (
            <Card className="mb-4 border-red-200 bg-red-50">
              <CardContent className="p-4 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-red-500" />
                <p className="text-red-600">{error}</p>
              </CardContent>
            </Card>
          )}

          {/* Step 1: 子ども選択 */}
          {step === 'select-child' && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-800">お子様を選択</h2>
              {students.length === 0 ? (
                <Card>
                  <CardContent className="p-6 text-center">
                    <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500">登録されている生徒がいません</p>
                  </CardContent>
                </Card>
              ) : (
                students.map((student) => (
                  <Card
                    key={student.id}
                    className="cursor-pointer hover:shadow-md transition-shadow"
                    onClick={() => handleSelectStudent(student)}
                  >
                    <CardContent className="p-4">
                      <div className="flex justify-between items-center">
                        <div>
                          <h3 className="font-semibold text-gray-900">{student.fullName}</h3>
                          {student.grade && (
                            <p className="text-sm text-gray-500">{student.grade}</p>
                          )}
                        </div>
                        <ChevronRight className="w-5 h-5 text-gray-400" />
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* Step 2: 契約選択 */}
          {step === 'select-contract' && selectedStudent && (
            <div className="space-y-4">
              <div className="bg-green-100 rounded-lg p-3 mb-4">
                <p className="text-sm text-green-800">
                  <span className="font-semibold">{selectedStudent.fullName}</span>さんの契約
                </p>
              </div>

              <h2 className="text-lg font-semibold text-gray-800">契約を選択</h2>
              {studentContracts.length === 0 ? (
                <Card>
                  <CardContent className="p-6 text-center">
                    <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500">有効な契約がありません</p>
                  </CardContent>
                </Card>
              ) : (
                studentContracts.map((contract) => (
                  <Card
                    key={contract.id}
                    className="cursor-pointer hover:shadow-md transition-shadow"
                    onClick={() => handleSelectContract(contract)}
                  >
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h3 className="font-semibold text-gray-900">
                              {contract.brand.brandName}
                            </h3>
                            <Badge className="bg-green-100 text-green-800">有効</Badge>
                          </div>
                          {/* チケット情報と曜日・時間 */}
                          {contract.ticket && (
                            <div className="bg-blue-50 rounded-md px-2 py-1 mb-2">
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-blue-700">
                                  {contract.ticket.ticketName}
                                </span>
                                {contract.ticket.durationMinutes && (
                                  <span className="text-xs text-blue-600">
                                    {contract.ticket.durationMinutes}分
                                  </span>
                                )}
                              </div>
                              {contract.dayOfWeek !== undefined && contract.dayOfWeek !== null && contract.startTime && (
                                <div className="flex items-center gap-1 mt-1 text-xs text-blue-600">
                                  <Clock className="w-3 h-3" />
                                  <span className="font-semibold">
                                    {DAY_LABELS[contract.dayOfWeek]}曜 {contract.startTime.slice(0, 5)}〜
                                  </span>
                                </div>
                              )}
                            </div>
                          )}
                          <div className="space-y-1 text-sm text-gray-600">
                            <div className="flex items-center gap-2">
                              <MapPin className="w-4 h-4" />
                              <span>{contract.school?.schoolName}</span>
                            </div>
                            {contract.dayOfWeek !== undefined && contract.startTime && (
                              <div className="flex items-center gap-2">
                                <Clock className="w-4 h-4" />
                                <span>
                                  {DAY_LABELS[contract.dayOfWeek]}曜日 {contract.startTime.slice(0, 5)}
                                </span>
                              </div>
                            )}
                            {contract.course && (
                              <p className="text-xs text-gray-500">{contract.course.courseName}</p>
                            )}
                          </div>
                        </div>
                        <ChevronRight className="w-5 h-5 text-gray-400 mt-1" />
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* Step 3: アクション選択 */}
          {step === 'select-action' && selectedContract && (
            <div className="space-y-4">
              <div className="bg-green-100 rounded-lg p-3 mb-4">
                <p className="text-sm text-green-800">
                  <span className="font-semibold">{selectedStudent?.fullName}</span>さん / {selectedContract.brand?.brandName || ''}
                </p>
                {/* チケット情報 */}
                {selectedContract.ticket && (
                  <p className="text-sm text-green-700 font-medium mt-1">
                    {selectedContract.ticket.ticketName}
                    {selectedContract.ticket.durationMinutes && ` (${selectedContract.ticket.durationMinutes}分)`}
                  </p>
                )}
                <p className="text-xs text-green-700 mt-1">
                  {selectedContract.school?.schoolName || '未設定'} / {selectedContract.dayOfWeek !== undefined ? `${DAY_LABELS[selectedContract.dayOfWeek]}曜日` : ''}
                </p>
              </div>

              <h2 className="text-lg font-semibold text-gray-800">操作を選択</h2>

              <div className="space-y-3">
                <Card
                  className="cursor-pointer hover:shadow-md transition-shadow border-l-4 border-l-blue-500"
                  onClick={() => handleSelectAction('change-class')}
                >
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <Calendar className="w-6 h-6 text-blue-500" />
                        <div>
                          <h3 className="font-semibold text-gray-900">クラス変更</h3>
                          <p className="text-sm text-gray-500">曜日・時間を変更します</p>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className="cursor-pointer hover:shadow-md transition-shadow border-l-4 border-l-purple-500"
                  onClick={() => handleSelectAction('change-school')}
                >
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <MapPin className="w-6 h-6 text-purple-500" />
                        <div>
                          <h3 className="font-semibold text-gray-900">校舎変更</h3>
                          <p className="text-sm text-gray-500">通う校舎を変更します</p>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className="cursor-pointer hover:shadow-md transition-shadow border-l-4 border-l-cyan-500"
                  onClick={() => handleSelectAction('transfer-reservation')}
                >
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <RefreshCw className="w-6 h-6 text-cyan-500" />
                        <div>
                          <h3 className="font-semibold text-gray-900">振替予約</h3>
                          <p className="text-sm text-gray-500">欠席チケットで振替予約</p>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className="cursor-pointer hover:shadow-md transition-shadow border-l-4 border-l-orange-500"
                  onClick={() => handleSelectAction('request-suspension')}
                >
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <PauseCircle className="w-6 h-6 text-orange-500" />
                        <div>
                          <h3 className="font-semibold text-gray-900">休会申請</h3>
                          <p className="text-sm text-gray-500">一時的にお休みします</p>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className="cursor-pointer hover:shadow-md transition-shadow border-l-4 border-l-red-500"
                  onClick={() => handleSelectAction('request-cancellation')}
                >
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <XCircle className="w-6 h-6 text-red-500" />
                        <div>
                          <h3 className="font-semibold text-gray-900">退会申請</h3>
                          <p className="text-sm text-gray-500">契約を終了します</p>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {/* Step 4: クラス変更 */}
          {step === 'change-class' && selectedContract && (() => {
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
              const dayIdx = dayLabels.indexOf(dayLabel);
              const dayOfWeekNum = dayIdx === dayLabels.length - 1 ? 0 : dayIdx + 1;

              setSelectedSchedule({
                dayOfWeek: dayOfWeekNum,
                startTime: schedule.startTime,
                scheduleId: schedule.id,
              });
            };

            return (
            <div className="space-y-4">
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
                          {classSchedules.timeSlots.map((timeSlot, timeIdx) => (
                            <tr key={timeIdx} className="border-b border-gray-200 hover:bg-gray-50">
                              <td className="text-xs font-semibold py-3 px-2 bg-gray-50 sticky left-0 z-10">
                                {timeSlot.time}
                              </td>
                              {dayLabels.map((label, dayIdx) => {
                                const dayData = timeSlot.days[label];
                                const status = dayData?.status || 'none';
                                const canSelect = status !== 'none' && status !== 'full';
                                const dayOfWeekNum = dayIdx === dayLabels.length - 1 ? 0 : dayIdx + 1;
                                const isSelected = selectedSchedule?.dayOfWeek === dayOfWeekNum &&
                                                   selectedSchedule?.startTime?.slice(0, 5) === timeSlot.time;
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
                  <CardContent className="p-6 text-center">
                    <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500">開講時間割がありません</p>
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
                    disabled={submitting}
                  >
                    {submitting ? (
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
            </div>
            );
          })()}

          {/* Step: 校舎変更 */}
          {step === 'change-school' && selectedContract && (
            <div className="space-y-4">
              <div className="bg-purple-100 rounded-lg p-3 mb-4">
                <p className="text-sm text-purple-800">
                  <span className="font-semibold">校舎変更</span>
                  {schoolChangeStep === 'select-school' ? ' - 校舎選択' : ' - クラス選択'}
                </p>
                <p className="text-xs text-purple-700 mt-1">
                  現在: {selectedContract.school?.schoolName || '未設定'}
                  {selectedNewSchool && ` → ${selectedNewSchool.name}`}
                </p>
              </div>

              {schoolChangeStep === 'select-school' && (
                <>
                  <h2 className="text-lg font-semibold text-gray-800">新しい校舎を選択</h2>
                  {loadingSchools ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
                    </div>
                  ) : availableSchools.length > 0 ? (
                    <MapSchoolSelector
                      schools={sortSchools(availableSchools)}
                      selectedSchoolId={selectedNewSchool?.id || null}
                      onSelectSchool={handleSelectNewSchool}
                    />
                  ) : (
                    <Card>
                      <CardContent className="p-6 text-center">
                        <MapPin className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500">他に開講校舎がありません</p>
                      </CardContent>
                    </Card>
                  )}

                  {/* 校舎リスト表示（ソート済み） */}
                  {availableSchools.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <h3 className="text-sm font-semibold text-gray-700">校舎一覧</h3>
                      {sortSchools(availableSchools).map((school) => (
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
                  )}
                </>
              )}

              {schoolChangeStep === 'select-class' && selectedNewSchool && (() => {
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
                <>
                  <h2 className="text-lg font-semibold text-gray-800">
                    {selectedNewSchool.name}のクラスを選択
                  </h2>

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
                      <CardContent className="p-6 text-center">
                        <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500">この校舎では開講していません</p>
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
                        disabled={submitting}
                      >
                        {submitting ? (
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
                </>
                );
              })()}
            </div>
          )}

          {/* Step: 休会申請 */}
          {step === 'request-suspension' && selectedContract && (
            <div className="space-y-4">
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
                      休会開始月（月末） <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={suspendFrom}
                      onChange={(e) => setSuspendFrom(e.target.value)}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    >
                      <option value="">選択してください</option>
                      {getEndOfMonthOptions().map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      休会は月末からの開始となります
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      休会終了月（月末・任意）
                    </label>
                    <select
                      value={suspendUntil}
                      onChange={(e) => setSuspendUntil(e.target.value)}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    >
                      <option value="">未定</option>
                      {getEndOfMonthOptions()
                        .filter((option) => !suspendFrom || option.value > suspendFrom)
                        .map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      未選択の場合、再開時期未定となります
                    </p>
                  </div>

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

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      休会理由（任意）
                    </label>
                    <textarea
                      value={suspendReason}
                      onChange={(e) => setSuspendReason(e.target.value)}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      rows={3}
                      placeholder="例：習い事の都合、学校行事など"
                    />
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

              {suspendFrom && (
                <Button
                  className="w-full bg-orange-500 hover:bg-orange-600"
                  onClick={handleConfirmSuspension}
                  disabled={submitting}
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      処理中...
                    </>
                  ) : (
                    '休会を申請する'
                  )}
                </Button>
              )}
            </div>
          )}

          {/* Step: 退会申請 */}
          {step === 'request-cancellation' && selectedContract && (
            <div className="space-y-4">
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
                  disabled={submitting}
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      処理中...
                    </>
                  ) : (
                    '退会を申請する'
                  )}
                </Button>
              )}
            </div>
          )}

          {/* Step: 振替予約 */}
          {step === 'transfer-reservation' && (
            <div className="space-y-4">
              <div className="bg-cyan-100 rounded-lg p-3 mb-4">
                <p className="text-sm text-cyan-800">
                  <span className="font-semibold">振替予約</span>
                  {transferStep === 'select-ticket' && ' - チケット選択'}
                  {transferStep === 'select-class' && ' - クラス選択'}
                  {transferStep === 'select-date' && ' - 日程選択'}
                </p>
                {selectedAbsenceTicket && (
                  <p className="text-xs text-cyan-700 mt-1">
                    {selectedAbsenceTicket.brandName} / 欠席日: {selectedAbsenceTicket.absenceDate}
                    {selectedTransferClass && ` → ${selectedTransferClass.schoolName} ${selectedTransferClass.dayOfWeekDisplay} ${selectedTransferClass.periodDisplay}`}
                  </p>
                )}
              </div>

              {/* チケット選択 */}
              {transferStep === 'select-ticket' && (
                <>
                  <h2 className="text-lg font-semibold text-gray-800">欠席チケットを選択</h2>
                  {loadingTickets ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
                    </div>
                  ) : absenceTickets.length > 0 ? (
                    <div className="space-y-3">
                      {absenceTickets.map((ticket) => (
                        <Card
                          key={ticket.id}
                          className="cursor-pointer hover:shadow-md transition-shadow"
                          onClick={() => handleSelectAbsenceTicket(ticket)}
                        >
                          <CardContent className="p-4">
                            <div className="flex justify-between items-start">
                              <div className="flex items-start gap-3">
                                <Ticket className="w-6 h-6 text-cyan-500 mt-1" />
                                <div>
                                  <h3 className="font-semibold text-gray-900">{ticket.brandName}</h3>
                                  <p className="text-sm text-gray-600">{ticket.originalTicketName}</p>
                                  <p className="text-xs text-gray-500 mt-1">
                                    欠席日: {ticket.absenceDate}
                                  </p>
                                  <p className="text-xs text-gray-500">
                                    有効期限: {ticket.validUntil}
                                  </p>
                                  <p className="text-xs text-gray-500">
                                    校舎: {ticket.schoolName}
                                  </p>
                                </div>
                              </div>
                              <ChevronRight className="w-5 h-5 text-gray-400" />
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <Card>
                      <CardContent className="p-6 text-center">
                        <Ticket className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500">利用可能な欠席チケットがありません</p>
                        <p className="text-sm text-gray-400 mt-2">
                          カレンダーから欠席登録をすると、振替チケットが発行されます
                        </p>
                      </CardContent>
                    </Card>
                  )}
                </>
              )}

              {/* クラス選択 */}
              {transferStep === 'select-class' && selectedAbsenceTicket && (
                <>
                  <h2 className="text-lg font-semibold text-gray-800">振替先クラスを選択</h2>
                  {loadingTransferClasses ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
                    </div>
                  ) : transferAvailableClasses.length > 0 ? (
                    <div className="space-y-3">
                      {transferAvailableClasses.map((cls) => (
                        <Card
                          key={cls.id}
                          className={`cursor-pointer transition-all ${
                            selectedTransferClass?.id === cls.id
                              ? 'border-2 border-cyan-500 bg-cyan-50'
                              : 'hover:shadow-md'
                          }`}
                          onClick={() => handleSelectTransferClass(cls)}
                        >
                          <CardContent className="p-4">
                            <div className="flex justify-between items-start">
                              <div>
                                <h3 className="font-semibold text-gray-900">
                                  {cls.dayOfWeekDisplay} {cls.periodDisplay}
                                </h3>
                                <p className="text-sm text-gray-600">{cls.schoolName}</p>
                                <p className="text-xs text-gray-500 mt-1">
                                  {cls.className}
                                </p>
                                <div className="flex items-center gap-2 mt-2">
                                  <Users className="w-4 h-4 text-gray-400" />
                                  <span className={`text-sm ${cls.availableSeats > 2 ? 'text-green-600' : cls.availableSeats > 0 ? 'text-orange-500' : 'text-red-500'}`}>
                                    残り{cls.availableSeats}席
                                  </span>
                                </div>
                              </div>
                              {selectedTransferClass?.id === cls.id ? (
                                <CheckCircle className="w-5 h-5 text-cyan-500" />
                              ) : (
                                <ChevronRight className="w-5 h-5 text-gray-400" />
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <Card>
                      <CardContent className="p-6 text-center">
                        <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500">振替可能なクラスがありません</p>
                      </CardContent>
                    </Card>
                  )}
                </>
              )}

              {/* 日程選択 */}
              {transferStep === 'select-date' && selectedAbsenceTicket && selectedTransferClass && (
                <>
                  <h2 className="text-lg font-semibold text-gray-800">振替日を選択</h2>
                  <Card className="rounded-xl shadow-md">
                    <CardContent className="p-4 space-y-4">
                      <div className="bg-cyan-50 p-3 rounded-lg">
                        <p className="text-sm text-cyan-800">
                          <span className="font-semibold">振替先:</span> {selectedTransferClass.schoolName}
                        </p>
                        <p className="text-sm text-cyan-800">
                          <span className="font-semibold">クラス:</span> {selectedTransferClass.dayOfWeekDisplay} {selectedTransferClass.periodDisplay}
                        </p>
                      </div>

                      <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-2">
                          振替日 <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="date"
                          value={transferDate}
                          onChange={(e) => setTransferDate(e.target.value)}
                          min={new Date().toISOString().split('T')[0]}
                          max={selectedAbsenceTicket.validUntil || undefined}
                          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          有効期限: {selectedAbsenceTicket.validUntil}まで
                        </p>
                      </div>
                    </CardContent>
                  </Card>

                  <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-3">
                    <div className="flex gap-2">
                      <AlertCircle className="w-5 h-5 text-cyan-600 flex-shrink-0" />
                      <div className="text-sm text-cyan-800">
                        <p className="font-semibold">ご注意</p>
                        <p>振替予約後のキャンセルは教室にお問い合わせください</p>
                      </div>
                    </div>
                  </div>

                  {transferDate && (
                    <Button
                      className="w-full bg-cyan-500 hover:bg-cyan-600"
                      onClick={handleConfirmTransfer}
                      disabled={submitting}
                    >
                      {submitting ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          処理中...
                        </>
                      ) : (
                        '振替予約を確定する'
                      )}
                    </Button>
                  )}
                </>
              )}
            </div>
          )}

          {/* Step: 確認 */}
          {step === 'confirm' && (
            <div className="space-y-4">
              <Card className="border-green-200 bg-green-50">
                <CardContent className="p-6 text-center">
                  <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                  <h2 className="text-xl font-bold text-green-800 mb-2">完了しました</h2>
                  <p className="text-green-700">{submitMessage}</p>
                </CardContent>
              </Card>
              <Button
                className="w-full"
                onClick={() => router.push('/feed')}
              >
                ホームに戻る
              </Button>
            </div>
          )}
        </div>
      </div>

      <BottomTabBar />
    </div>
  );
}
