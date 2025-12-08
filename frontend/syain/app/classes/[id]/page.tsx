'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { ArrowLeft, Clock, MapPin, Users } from 'lucide-react';

interface Student {
  id: string;
  name: string;
  grade: string;
  is_substitute: boolean;
  attendance_status?: string;
}

interface ClassDetail {
  id: string;
  class_name: string;
  classroom: string;
  start_time: string;
  end_time: string;
  campus: { name: string };
}

export default function ClassDetailPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const classId = params.id as string;

  const [classDetail, setClassDetail] = useState<ClassDetail | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [reportContent, setReportContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    loadData();
  }, [user, loading, classId]);

  const loadData = async () => {
    if (!user) return;

    const { data: classData } = await supabase
      .from('classes')
      .select(`
        id,
        class_name,
        classroom,
        start_time,
        end_time,
        campus:campuses(name)
      `)
      .eq('id', classId)
      .single();

    if (classData) {
      setClassDetail(classData as any);
    }

    const { data: classStudentsData } = await supabase
      .from('class_students')
      .select(`
        student_id,
        is_substitute,
        students:student_id (
          id,
          name,
          grade
        )
      `)
      .eq('class_id', classId);

    if (classStudentsData) {
      const studentsList: Student[] = classStudentsData.map((cs: any) => ({
        id: cs.students.id,
        name: cs.students.name,
        grade: cs.students.grade,
        is_substitute: cs.is_substitute,
      }));

      const { data: attendanceData } = await supabase
        .from('attendance')
        .select('student_id, status')
        .eq('class_id', classId);

      if (attendanceData) {
        const attendanceMap = new Map(
          attendanceData.map((a) => [a.student_id, a.status])
        );

        studentsList.forEach((student) => {
          student.attendance_status = attendanceMap.get(student.id) || 'present';
        });
      } else {
        studentsList.forEach((student) => {
          student.attendance_status = 'present';
        });
      }

      setStudents(studentsList);
    }

    const { data: reportData } = await supabase
      .from('daily_reports')
      .select('report_content')
      .eq('class_id', classId)
      .maybeSingle();

    if (reportData) {
      setReportContent(reportData.report_content);
    }
  };

  const handleAttendanceChange = async (studentId: string, status: string) => {
    setStudents((prev) =>
      prev.map((s) =>
        s.id === studentId ? { ...s, attendance_status: status } : s
      )
    );

    await supabase
      .from('attendance')
      .upsert({
        class_id: classId,
        student_id: studentId,
        status,
        updated_at: new Date().toISOString(),
      });
  };

  const handleSubmitReport = async () => {
    if (!user || !reportContent.trim()) {
      alert('日報内容を入力してください');
      return;
    }

    setSubmitting(true);

    const { error } = await supabase
      .from('daily_reports')
      .upsert({
        class_id: classId,
        instructor_id: user.id,
        report_content: reportContent,
      });

    if (!error) {
      alert('日報を送信しました');
      router.push('/home');
    }

    setSubmitting(false);
  };

  if (loading || !classDetail) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100" />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-24">
      <div className="max-w-[390px] mx-auto">
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
            <h1 className="text-2xl font-bold text-gray-900">{classDetail.class_name}</h1>
          </div>
        </div>

        <div className="p-4 space-y-4">
          <Card className="shadow-md border-0">
            <CardHeader>
              <CardTitle className="text-lg">授業情報</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <Clock className="w-4 h-4 text-gray-500" />
                <span>
                  {classDetail.start_time.substring(0, 5)} - {classDetail.end_time.substring(0, 5)}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <MapPin className="w-4 h-4 text-gray-500" />
                <span>{classDetail.classroom}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Users className="w-4 h-4 text-gray-500" />
                <span>{students.length}名</span>
              </div>
            </CardContent>
          </Card>

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
                        <p className="text-sm text-gray-600">{student.grade}</p>
                      </div>
                      {student.is_substitute && (
                        <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">
                          振替
                        </Badge>
                      )}
                    </div>

                    <RadioGroup
                      value={student.attendance_status}
                      onValueChange={(value) =>
                        handleAttendanceChange(student.id, value)
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
