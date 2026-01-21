'use client';

import { AuthGuard } from '@/components/auth';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { useUser } from '@/lib/hooks/use-user';
import { useStaffStudents } from '@/lib/hooks/use-staff-students';
import type { StudentSearchParams } from '@/lib/api/students';
import { Search, Users, ChevronLeft, ChevronRight, GraduationCap, Phone, Mail, AlertCircle } from 'lucide-react';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  inquiry: { label: '問い合わせ', color: 'bg-yellow-100 text-yellow-800' },
  trial: { label: '体験', color: 'bg-blue-100 text-blue-800' },
  enrolled: { label: '在籍', color: 'bg-green-100 text-green-800' },
  suspended: { label: '休会', color: 'bg-orange-100 text-orange-800' },
  withdrawn: { label: '退会', color: 'bg-gray-100 text-gray-800' },
};

const GRADE_OPTIONS = [
  { value: '', label: '全学年' },
  { value: '小1', label: '小学1年' },
  { value: '小2', label: '小学2年' },
  { value: '小3', label: '小学3年' },
  { value: '小4', label: '小学4年' },
  { value: '小5', label: '小学5年' },
  { value: '小6', label: '小学6年' },
  { value: '中1', label: '中学1年' },
  { value: '中2', label: '中学2年' },
  { value: '中3', label: '中学3年' },
  { value: '高1', label: '高校1年' },
  { value: '高2', label: '高校2年' },
  { value: '高3', label: '高校3年' },
];

const STATUS_OPTIONS = [
  { value: '', label: '全ステータス' },
  { value: 'enrolled', label: '在籍' },
  { value: 'trial', label: '体験' },
  { value: 'inquiry', label: '問い合わせ' },
  { value: 'suspended', label: '休会' },
  { value: 'withdrawn', label: '退会' },
];

function StudentsContent() {
  const router = useRouter();
  const [searchParams, setSearchParams] = useState<StudentSearchParams>({
    page: 1,
    pageSize: 20,
    search: '',
    status: '',
    grade: '',
  });

  // ユーザー情報を取得
  const { data: user, isLoading: userLoading } = useUser();
  const isStaff = user?.userType === 'staff' || user?.userType === 'teacher';

  // 生徒一覧を取得
  const { data: studentsData, isLoading: studentsLoading, error: studentsError, refetch } = useStaffStudents(searchParams);

  const students = studentsData?.students || [];
  const pagination = {
    count: studentsData?.count || 0,
    hasNext: studentsData?.hasNext || false,
    hasPrev: studentsData?.hasPrev || false,
  };
  const loading = userLoading || studentsLoading;
  const error = studentsError ? '生徒情報の取得に失敗しました' : null;

  const handleSearchChange = (value: string) => {
    setSearchParams((prev) => ({ ...prev, search: value, page: 1 }));
  };

  const handleStatusChange = (value: string) => {
    setSearchParams((prev) => ({ ...prev, status: value, page: 1 }));
  };

  const handleGradeChange = (value: string) => {
    setSearchParams((prev) => ({ ...prev, grade: value, page: 1 }));
  };

  const handlePageChange = (newPage: number) => {
    setSearchParams((prev) => ({ ...prev, page: newPage }));
  };

  const getStatusBadge = (status: string) => {
    const statusInfo = STATUS_LABELS[status] || { label: status, color: 'bg-gray-100 text-gray-800' };
    return (
      <Badge className={`${statusInfo.color} font-medium`}>
        {statusInfo.label}
      </Badge>
    );
  };

  if (userLoading) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100" />;
  }

  if (user && !isStaff) {
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
            <div className="flex items-center gap-2">
              <Users className="w-6 h-6 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">生徒一覧</h1>
            </div>
            <p className="text-sm text-gray-600 mt-1">
              {pagination.count}名の生徒
            </p>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="p-4 space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              type="text"
              placeholder="名前で検索..."
              value={searchParams.search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-10"
            />
          </div>

          <div className="flex gap-2">
            <Select value={searchParams.status} onValueChange={handleStatusChange}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="ステータス" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={searchParams.grade} onValueChange={handleGradeChange}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="学年" />
              </SelectTrigger>
              <SelectContent>
                {GRADE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
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
                  onClick={() => refetch()}
                >
                  再読み込み
                </Button>
              </CardContent>
            </Card>
          ) : students.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">生徒が見つかりません</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {students.map((student) => (
                <Card
                  key={student.id}
                  className="shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => router.push(`/students/${student.id}`)}
                >
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-gray-900">
                            {student.user?.full_name || `${student.user?.last_name || ''} ${student.user?.first_name || ''}`}
                          </h3>
                          {getStatusBadge(student.status)}
                        </div>

                        <div className="flex flex-wrap gap-3 text-sm text-gray-600 mt-2">
                          {student.grade && (
                            <div className="flex items-center gap-1">
                              <GraduationCap className="w-3.5 h-3.5" />
                              <span>{student.grade}</span>
                            </div>
                          )}
                          {student.school_name && (
                            <span className="text-gray-500">{student.school_name}</span>
                          )}
                          {student.student_number && (
                            <span className="text-gray-400">#{student.student_number}</span>
                          )}
                        </div>

                        {student.user && (
                          <div className="flex flex-wrap gap-3 text-sm text-gray-500 mt-2">
                            {student.user.email && (
                              <div className="flex items-center gap-1">
                                <Mail className="w-3.5 h-3.5" />
                                <span className="truncate max-w-[180px]">{student.user.email}</span>
                              </div>
                            )}
                            {student.user.phone_number && (
                              <div className="flex items-center gap-1">
                                <Phone className="w-3.5 h-3.5" />
                                <span>{student.user.phone_number}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      <ChevronRight className="w-5 h-5 text-gray-400 mt-1" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Pagination */}
          {!loading && !error && pagination.count > 0 && (
            <div className="flex justify-between items-center mt-4 px-2">
              <p className="text-sm text-gray-600">
                {((searchParams.page || 1) - 1) * (searchParams.pageSize || 20) + 1} - {Math.min((searchParams.page || 1) * (searchParams.pageSize || 20), pagination.count)} / {pagination.count}件
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!pagination.hasPrev}
                  onClick={() => handlePageChange((searchParams.page || 1) - 1)}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!pagination.hasNext}
                  onClick={() => handlePageChange((searchParams.page || 1) + 1)}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      <BottomTabBar />
    </div>
  );
}

export default function StudentsPage() {
  return (
    <AuthGuard>
      <StudentsContent />
    </AuthGuard>
  );
}
