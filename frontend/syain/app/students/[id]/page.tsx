'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { BottomNav } from '@/components/bottom-nav';
import { useRequireAuth } from '@/lib/auth';
import { getStudent } from '@/lib/api/students';
import type { StudentDetail, Course } from '@/lib/api/types';
import api from '@/lib/api/client';
import {
  ArrowLeft,
  User,
  GraduationCap,
  Phone,
  Mail,
  Ticket,
  Calendar,
  Clock,
  BookOpen,
  Plus,
  Edit,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, addMonths, subMonths, isSameDay, getDay } from 'date-fns';
import { ja } from 'date-fns/locale';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  inquiry: { label: '問い合わせ', color: 'bg-yellow-100 text-yellow-800' },
  trial: { label: '体験', color: 'bg-blue-100 text-blue-800' },
  enrolled: { label: '在籍', color: 'bg-green-100 text-green-800' },
  suspended: { label: '休会', color: 'bg-orange-100 text-orange-800' },
  withdrawn: { label: '退会', color: 'bg-gray-100 text-gray-800' },
};

const DAY_OF_WEEK = ['日', '月', '火', '水', '木', '金', '土'];

interface LessonSchedule {
  id: string;
  course?: { id: string; name: string };
  subject?: { id: string; name: string };
  date: string;
  start_time: string;
  end_time: string;
  day_of_week?: number;
  status: string;
}

interface ClassRegistration {
  id: string;
  course: Course;
  day_of_week: number;
  start_time: string;
  end_time: string;
  start_date: string;
  status: string;
}

export default function StudentDetailPage() {
  const { loading: authLoading } = useRequireAuth();
  const router = useRouter();
  const params = useParams();
  const studentId = params.id as string;

  const [student, setStudent] = useState<StudentDetail | null>(null);
  const [schedules, setSchedules] = useState<LessonSchedule[]>([]);
  const [registrations, setRegistrations] = useState<ClassRegistration[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // クラス登録モーダル
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingRegistration, setEditingRegistration] = useState<ClassRegistration | null>(null);

  // 登録フォーム
  const [selectedCourse, setSelectedCourse] = useState<string>('');
  const [selectedDayOfWeek, setSelectedDayOfWeek] = useState<string>('');
  const [selectedStartTime, setSelectedStartTime] = useState<string>('');
  const [selectedEndTime, setSelectedEndTime] = useState<string>('');
  const [selectedStartDate, setSelectedStartDate] = useState<Date | null>(null);
  const [calendarMonth, setCalendarMonth] = useState(new Date());
  const [submitting, setSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const studentData = await getStudent(studentId);
      setStudent(studentData);

      // コース一覧取得
      try {
        const coursesRes = await api.get('/contracts/courses/');
        setCourses(coursesRes.results || coursesRes || []);
      } catch {
        setCourses([]);
      }

      // 授業スケジュール取得
      try {
        const schedulesRes = await api.get(`/lessons/schedules/?student_id=${studentId}`);
        setSchedules(schedulesRes.results || schedulesRes || []);
      } catch {
        setSchedules([]);
      }

      // クラス登録情報取得（契約から）
      try {
        const contractsRes = await api.get(`/contracts/?student_id=${studentId}&status=active`);
        const contracts = contractsRes.results || contractsRes || [];
        const regs: ClassRegistration[] = contracts.map((c: any) => ({
          id: c.id,
          course: c.course,
          day_of_week: c.day_of_week || 0,
          start_time: c.start_time || '16:00',
          end_time: c.end_time || '17:00',
          start_date: c.start_date,
          status: c.status,
        }));
        setRegistrations(regs);
      } catch {
        setRegistrations([]);
      }
    } catch (err) {
      console.error('Failed to fetch student data:', err);
      setError('生徒情報の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  }, [studentId]);

  useEffect(() => {
    if (!authLoading && studentId) {
      fetchData();
    }
  }, [authLoading, studentId, fetchData]);

  const getStatusBadge = (status: string) => {
    const statusInfo = STATUS_LABELS[status] || { label: status, color: 'bg-gray-100 text-gray-800' };
    return (
      <Badge className={`${statusInfo.color} font-medium`}>
        {statusInfo.label}
      </Badge>
    );
  };

  // カレンダー日付選択
  const calendarDays = eachDayOfInterval({
    start: startOfMonth(calendarMonth),
    end: endOfMonth(calendarMonth),
  });

  const handleSelectDate = (date: Date) => {
    setSelectedStartDate(date);
    // 曜日を自動設定
    setSelectedDayOfWeek(String(getDay(date)));
  };

  // クラス登録
  const handleRegisterClass = async () => {
    if (!selectedCourse || !selectedStartDate || !selectedStartTime || !selectedEndTime) {
      alert('必須項目を入力してください');
      return;
    }

    try {
      setSubmitting(true);

      // 契約を作成
      await api.post('/contracts/', {
        student_id: studentId,
        course_id: selectedCourse,
        start_date: format(selectedStartDate, 'yyyy-MM-dd'),
        day_of_week: parseInt(selectedDayOfWeek),
        start_time: selectedStartTime,
        end_time: selectedEndTime,
        status: 'active',
      });

      setShowRegisterModal(false);
      resetForm();
      fetchData();
      alert('クラスを登録しました');
    } catch (err) {
      console.error('Failed to register class:', err);
      alert('クラス登録に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  // クラス編集
  const handleEditRegistration = (reg: ClassRegistration) => {
    setEditingRegistration(reg);
    setSelectedCourse(reg.course?.id || '');
    setSelectedDayOfWeek(String(reg.day_of_week));
    setSelectedStartTime(reg.start_time);
    setSelectedEndTime(reg.end_time);
    setSelectedStartDate(new Date(reg.start_date));
    setShowEditModal(true);
  };

  const handleUpdateClass = async () => {
    if (!editingRegistration || !selectedStartTime || !selectedEndTime) {
      alert('必須項目を入力してください');
      return;
    }

    try {
      setSubmitting(true);

      await api.patch(`/contracts/${editingRegistration.id}/`, {
        day_of_week: parseInt(selectedDayOfWeek),
        start_time: selectedStartTime,
        end_time: selectedEndTime,
      });

      setShowEditModal(false);
      setEditingRegistration(null);
      resetForm();
      fetchData();
      alert('クラス情報を更新しました');
    } catch (err) {
      console.error('Failed to update class:', err);
      alert('クラス更新に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setSelectedCourse('');
    setSelectedDayOfWeek('');
    setSelectedStartTime('');
    setSelectedEndTime('');
    setSelectedStartDate(null);
  };

  // 時間選択オプション
  const timeOptions = [];
  for (let h = 9; h <= 21; h++) {
    for (let m = 0; m < 60; m += 30) {
      const time = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
      timeOptions.push(time);
    }
  }

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error || !student) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
        <div className="max-w-4xl mx-auto p-4">
          <Button variant="ghost" onClick={() => router.back()} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            戻る
          </Button>
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-6 text-center">
              <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <p className="text-red-600">{error || '生徒情報が見つかりません'}</p>
            </CardContent>
          </Card>
        </div>
        <BottomNav />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <Button variant="ghost" size="sm" onClick={() => router.back()} className="mb-2">
              <ArrowLeft className="w-4 h-4 mr-2" />
              戻る
            </Button>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                  <User className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">
                    {student.user?.full_name || '名前未設定'}
                  </h1>
                  <div className="flex items-center gap-2 mt-1">
                    {getStatusBadge(student.status)}
                    {student.student_number && (
                      <span className="text-xs text-gray-500">#{student.student_number}</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {/* 基本情報 */}
          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">基本情報</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {student.grade && (
                <div className="flex items-center gap-2 text-sm">
                  <GraduationCap className="w-4 h-4 text-gray-500" />
                  <span>{student.grade}</span>
                </div>
              )}
              {student.school_name && (
                <div className="flex items-center gap-2 text-sm">
                  <BookOpen className="w-4 h-4 text-gray-500" />
                  <span>{student.school_name}</span>
                </div>
              )}
              {student.user?.email && (
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="w-4 h-4 text-gray-500" />
                  <span>{student.user.email}</span>
                </div>
              )}
              {student.user?.phone_number && (
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="w-4 h-4 text-gray-500" />
                  <span>{student.user.phone_number}</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* チケット残高 */}
          {student.tickets && (
            <Card className="shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Ticket className="w-4 h-4" />
                  チケット残高
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-3xl font-bold text-blue-600">
                      {student.tickets.total_available}
                    </span>
                    <span className="text-sm text-gray-500 ml-1">枚</span>
                  </div>
                  {student.tickets.expiring_soon > 0 && (
                    <Badge variant="outline" className="text-orange-600 border-orange-300">
                      {student.tickets.expiring_soon}枚 期限間近
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 登録クラス */}
          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <BookOpen className="w-4 h-4" />
                  登録クラス
                </CardTitle>
                <Button size="sm" onClick={() => setShowRegisterModal(true)}>
                  <Plus className="w-4 h-4 mr-1" />
                  クラス登録
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {registrations.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">登録クラスはありません</p>
              ) : (
                <div className="space-y-3">
                  {registrations.map((reg) => (
                    <div
                      key={reg.id}
                      className="p-3 bg-gray-50 rounded-lg flex items-center justify-between"
                    >
                      <div>
                        <h4 className="font-medium text-sm">{reg.course?.name || 'コース未設定'}</h4>
                        <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            毎週{DAY_OF_WEEK[reg.day_of_week]}曜日
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {reg.start_time?.substring(0, 5)} - {reg.end_time?.substring(0, 5)}
                          </span>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => handleEditRegistration(reg)}>
                        <Edit className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 授業スケジュール */}
          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                授業スケジュール
              </CardTitle>
            </CardHeader>
            <CardContent>
              {schedules.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">スケジュールはありません</p>
              ) : (
                <div className="space-y-2">
                  {schedules.slice(0, 5).map((schedule) => (
                    <div
                      key={schedule.id}
                      className="p-3 bg-gray-50 rounded-lg flex items-center justify-between"
                    >
                      <div>
                        <h4 className="font-medium text-sm">
                          {schedule.course?.name || schedule.subject?.name || '授業'}
                        </h4>
                        <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
                          <span>
                            {format(new Date(schedule.date), 'M/d (E)', { locale: ja })}
                          </span>
                          <span>
                            {schedule.start_time?.substring(0, 5)} - {schedule.end_time?.substring(0, 5)}
                          </span>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {schedule.status === 'scheduled' ? '予定' : schedule.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* クラス登録モーダル */}
      <Dialog open={showRegisterModal} onOpenChange={setShowRegisterModal}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>クラス登録</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* コース選択 */}
            <div>
              <Label>コース *</Label>
              <Select value={selectedCourse} onValueChange={setSelectedCourse}>
                <SelectTrigger>
                  <SelectValue placeholder="コースを選択" />
                </SelectTrigger>
                <SelectContent>
                  {courses.map((course) => (
                    <SelectItem key={course.id} value={course.id}>
                      {course.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* 開始日（カレンダー） */}
            <div>
              <Label>開始日 *</Label>
              <Card className="mt-2">
                <CardContent className="p-3">
                  {/* 月選択 */}
                  <div className="flex items-center justify-between mb-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setCalendarMonth(subMonths(calendarMonth, 1))}
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <span className="font-medium">
                      {format(calendarMonth, 'yyyy年 M月', { locale: ja })}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setCalendarMonth(addMonths(calendarMonth, 1))}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>

                  {/* 曜日ヘッダー */}
                  <div className="grid grid-cols-7 gap-1 mb-1">
                    {DAY_OF_WEEK.map((day, i) => (
                      <div
                        key={day}
                        className={`text-center text-xs py-1 ${
                          i === 0 ? 'text-red-500' : i === 6 ? 'text-blue-500' : 'text-gray-500'
                        }`}
                      >
                        {day}
                      </div>
                    ))}
                  </div>

                  {/* カレンダー */}
                  <div className="grid grid-cols-7 gap-1">
                    {Array.from({ length: startOfMonth(calendarMonth).getDay() }).map((_, i) => (
                      <div key={`empty-${i}`} className="h-8" />
                    ))}
                    {calendarDays.map((day) => {
                      const isSelected = selectedStartDate && isSameDay(day, selectedStartDate);
                      const isToday = isSameDay(day, new Date());
                      const dayOfWeek = getDay(day);
                      const isPast = day < new Date(new Date().setHours(0, 0, 0, 0));

                      return (
                        <button
                          key={day.toISOString()}
                          type="button"
                          onClick={() => !isPast && handleSelectDate(day)}
                          disabled={isPast}
                          className={`h-8 text-sm rounded transition-colors ${
                            isSelected
                              ? 'bg-blue-600 text-white'
                              : isToday
                              ? 'bg-blue-100 text-blue-600'
                              : isPast
                              ? 'text-gray-300 cursor-not-allowed'
                              : 'hover:bg-gray-100'
                          } ${
                            dayOfWeek === 0 ? 'text-red-500' : dayOfWeek === 6 ? 'text-blue-500' : ''
                          } ${isSelected ? 'text-white' : ''}`}
                        >
                          {format(day, 'd')}
                        </button>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
              {selectedStartDate && (
                <p className="text-sm text-gray-600 mt-2">
                  選択: {format(selectedStartDate, 'yyyy年M月d日 (E)', { locale: ja })}
                </p>
              )}
            </div>

            {/* 曜日選択 */}
            <div>
              <Label>授業曜日 *</Label>
              <Select value={selectedDayOfWeek} onValueChange={setSelectedDayOfWeek}>
                <SelectTrigger>
                  <SelectValue placeholder="曜日を選択" />
                </SelectTrigger>
                <SelectContent>
                  {DAY_OF_WEEK.map((day, i) => (
                    <SelectItem key={i} value={String(i)}>
                      {day}曜日
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* 時間選択 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>開始時間 *</Label>
                <Select value={selectedStartTime} onValueChange={setSelectedStartTime}>
                  <SelectTrigger>
                    <SelectValue placeholder="開始時間" />
                  </SelectTrigger>
                  <SelectContent>
                    {timeOptions.map((time) => (
                      <SelectItem key={time} value={time}>
                        {time}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>終了時間 *</Label>
                <Select value={selectedEndTime} onValueChange={setSelectedEndTime}>
                  <SelectTrigger>
                    <SelectValue placeholder="終了時間" />
                  </SelectTrigger>
                  <SelectContent>
                    {timeOptions.map((time) => (
                      <SelectItem key={time} value={time}>
                        {time}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowRegisterModal(false)}>
              キャンセル
            </Button>
            <Button onClick={handleRegisterClass} disabled={submitting}>
              {submitting ? '登録中...' : '登録'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* クラス編集モーダル */}
      <Dialog open={showEditModal} onOpenChange={setShowEditModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>クラス情報編集</DialogTitle>
            <CardDescription>
              授業曜日と時間を変更できます
            </CardDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* コース表示（変更不可） */}
            <div>
              <Label>コース</Label>
              <Input
                value={editingRegistration?.course?.name || ''}
                disabled
                className="bg-gray-50"
              />
            </div>

            {/* 曜日選択 */}
            <div>
              <Label>授業曜日 *</Label>
              <Select value={selectedDayOfWeek} onValueChange={setSelectedDayOfWeek}>
                <SelectTrigger>
                  <SelectValue placeholder="曜日を選択" />
                </SelectTrigger>
                <SelectContent>
                  {DAY_OF_WEEK.map((day, i) => (
                    <SelectItem key={i} value={String(i)}>
                      {day}曜日
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* 時間選択 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>開始時間 *</Label>
                <Select value={selectedStartTime} onValueChange={setSelectedStartTime}>
                  <SelectTrigger>
                    <SelectValue placeholder="開始時間" />
                  </SelectTrigger>
                  <SelectContent>
                    {timeOptions.map((time) => (
                      <SelectItem key={time} value={time}>
                        {time}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>終了時間 *</Label>
                <Select value={selectedEndTime} onValueChange={setSelectedEndTime}>
                  <SelectTrigger>
                    <SelectValue placeholder="終了時間" />
                  </SelectTrigger>
                  <SelectContent>
                    {timeOptions.map((time) => (
                      <SelectItem key={time} value={time}>
                        {time}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowEditModal(false)}>
              キャンセル
            </Button>
            <Button onClick={handleUpdateClass} disabled={submitting}>
              {submitting ? '更新中...' : '更新'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <BottomNav />
    </div>
  );
}
