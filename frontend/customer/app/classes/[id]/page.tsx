'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { isAuthenticated, getMe } from '@/lib/api/auth';
import {
  getClassDetail,
  getClassStudents,
  updateClassAttendance,
  getClassDailyReport,
  submitClassDailyReport,
  ClassDetail,
  ClassStudent,
} from '@/lib/api/lessons';
import { ArrowLeft, Clock, MapPin, Users, AlertCircle } from 'lucide-react';

export default function ClassDetailPage() {
  const router = useRouter();
  const params = useParams();
  const classId = params.id as string;

  const [authChecking, setAuthChecking] = useState(true);
  const [isStaff, setIsStaff] = useState(false);
  const [classDetail, setClassDetail] = useState<ClassDetail | null>(null);
  const [students, setStudents] = useState<ClassStudent[]>([]);
  const [reportContent, setReportContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    if (!classId) return;

    try {
      setLoading(true);
      setError(null);

      const [detail, studentsList, report] = await Promise.all([
        getClassDetail(classId),
        getClassStudents(classId),
        getClassDailyReport(classId),
      ]);

      setClassDetail(detail);
      setStudents(studentsList);
      if (report?.reportContent) {
        setReportContent(report.reportContent);
      }
    } catch (err) {
      console.error('Failed to load class data:', err);
      setError('クラス情報の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  }, [classId]);

  useEffect(() => {
    if (!authChecking && isStaff && classId) {
      loadData();
    }
  }, [authChecking, isStaff, classId, loadData]);

  const handleAttendanceChange = async (studentId: string, status: 'present' | 'absent' | 'late' | 'excused') => {
    // 楽観的更新
    setStudents((prev) =>
      prev.map((s) =>
        s.id === studentId ? { ...s, attendanceStatus: status } : s
      )
    );

    try {
      await updateClassAttendance(classId, { studentId, status });
    } catch (err) {
      console.error('Failed to update attendance:', err);
      // 失敗した場合は元に戻す
      loadData();
    }
  };

  const handleSubmitReport = async () => {
    if (!reportContent.trim()) {
      alert('日報内容を入力してください');
      return;
    }

    try {
      setSubmitting(true);
      await submitClassDailyReport(classId, reportContent);
      alert('日報を送信しました');
      router.push('/schedule');
    } catch (err) {
      console.error('Failed to submit report:', err);
      alert('日報の送信に失敗しました');
    } finally {
      setSubmitting(false);
    }
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

  if (error || !classDetail) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center">
        <Card className="max-w-md mx-4">
          <CardContent className="p-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-gray-600">{error || 'クラス情報が見つかりません'}</p>
            <Button className="mt-4" onClick={() => router.back()}>
              戻る
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-24">
      <div className="max-w-[420px] mx-auto">
        {/* Header */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.back()}
              className="mb-2"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              戻る
            </Button>
            <h1 className="text-2xl font-bold text-gray-900">
              {classDetail.className || classDetail.course?.name || 'クラス詳細'}
            </h1>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {/* 授業情報カード */}
          <Card className="shadow-md border-0">
            <CardHeader>
              <CardTitle className="text-lg">授業情報</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <Clock className="w-4 h-4 text-gray-500" />
                <span>
                  {classDetail.startTime?.substring(0, 5)} - {classDetail.endTime?.substring(0, 5)}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <MapPin className="w-4 h-4 text-gray-500" />
                <span>{classDetail.classroom || classDetail.campus?.name || '教室未設定'}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Users className="w-4 h-4 text-gray-500" />
                <span>{students.length}名</span>
              </div>
            </CardContent>
          </Card>

          {/* 出欠管理カード */}
          <Card className="shadow-md border-0">
            <CardHeader>
              <CardTitle className="text-lg">出欠管理</CardTitle>
              <CardDescription>生徒の出席状況を記録してください</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {students.map((student) => (
                  <div
                    key={student.id}
                    className="p-4 bg-gray-50 rounded-xl space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-900">{student.name}</h3>
                        {student.grade && (
                          <p className="text-sm text-gray-600">{student.grade}</p>
                        )}
                      </div>
                      {student.isSubstitute && (
                        <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">
                          振替
                        </Badge>
                      )}
                    </div>

                    <RadioGroup
                      value={student.attendanceStatus || 'present'}
                      onValueChange={(value) =>
                        handleAttendanceChange(student.id, value as 'present' | 'absent' | 'late' | 'excused')
                      }
                    >
                      <div className="flex gap-4">
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="present" id={`${student.id}-present`} />
                          <Label htmlFor={`${student.id}-present`} className="cursor-pointer">
                            出席
                          </Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="absent" id={`${student.id}-absent`} />
                          <Label htmlFor={`${student.id}-absent`} className="cursor-pointer">
                            欠席
                          </Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="late" id={`${student.id}-late`} />
                          <Label htmlFor={`${student.id}-late`} className="cursor-pointer">
                            遅刻
                          </Label>
                        </div>
                      </div>
                    </RadioGroup>
                  </div>
                ))}
                {students.length === 0 && (
                  <p className="text-sm text-gray-500 text-center py-4">
                    生徒が登録されていません
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 授業日報カード */}
          <Card className="shadow-md border-0">
            <CardHeader>
              <CardTitle className="text-lg">授業日報</CardTitle>
              <CardDescription>授業内容や気づいたことを記録してください</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="授業内容、生徒の様子、特記事項などを入力してください"
                value={reportContent}
                onChange={(e) => setReportContent(e.target.value)}
                rows={8}
                className="mb-4"
              />
              <Button
                onClick={handleSubmitReport}
                disabled={submitting || !reportContent.trim()}
                className="w-full h-12 bg-blue-600 hover:bg-blue-700"
              >
                {submitting ? '送信中...' : '日報を送信'}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
