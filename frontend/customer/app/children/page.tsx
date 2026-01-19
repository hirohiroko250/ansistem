'use client';

import { useState, useEffect, useRef } from 'react';
import { ChevronLeft, User, Plus, ChevronRight, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getChildren, createStudent, CreateStudentRequest, CreateStudentResponse } from '@/lib/api/students';
import { useToast } from '@/hooks/use-toast';

// ひらがなをカタカナに変換
const hiraganaToKatakana = (str: string): string => {
  return str.replace(/[\u3041-\u3096]/g, (match) => {
    return String.fromCharCode(match.charCodeAt(0) + 0x60);
  });
};

// 文字列がひらがな/カタカナかどうかをチェック
const isKana = (str: string): boolean => {
  return /^[\u3040-\u309F\u30A0-\u30FF\u30FC]+$/.test(str);
};

type Child = {
  id: string;
  student_no: string;
  last_name: string;
  first_name: string;
  full_name: string;
  birth_date?: string;
  gender?: string;
  grade?: string;
  grade_name?: string;
  school_name?: string;
  status: string;
  enrollment_date?: string;
  guardian_id?: string;
  guardian_name?: string;
};

export default function ChildrenPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [children, setChildren] = useState<Child[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);

  // Form state
  const [newChildLastName, setNewChildLastName] = useState('');
  const [newChildFirstName, setNewChildFirstName] = useState('');
  const [newChildLastNameKana, setNewChildLastNameKana] = useState('');
  const [newChildFirstNameKana, setNewChildFirstNameKana] = useState('');
  const [newChildBirthDate, setNewChildBirthDate] = useState('');
  const [newChildGender, setNewChildGender] = useState('');
  const [newChildSchoolName, setNewChildSchoolName] = useState('');
  const [newChildGrade, setNewChildGrade] = useState('');

  // IME composition tracking for auto-kana
  const lastNameCompositionRef = useRef<string>('');
  const firstNameCompositionRef = useRef<string>('');

  // 姓の入力ハンドラー（カナ自動入力）
  const handleLastNameCompositionUpdate = (e: React.CompositionEvent<HTMLInputElement>) => {
    // IME入力中のひらがなを保存
    lastNameCompositionRef.current = e.data || '';
  };

  const handleLastNameCompositionEnd = (e: React.CompositionEvent<HTMLInputElement>) => {
    const compositionData = lastNameCompositionRef.current;
    // 変換前のひらがなをカタカナに変換してセット（カナが空の場合のみ）
    if (compositionData && isKana(compositionData) && !newChildLastNameKana) {
      setNewChildLastNameKana(hiraganaToKatakana(compositionData));
    }
    lastNameCompositionRef.current = '';
  };

  // 名の入力ハンドラー（カナ自動入力）
  const handleFirstNameCompositionUpdate = (e: React.CompositionEvent<HTMLInputElement>) => {
    // IME入力中のひらがなを保存
    firstNameCompositionRef.current = e.data || '';
  };

  const handleFirstNameCompositionEnd = (e: React.CompositionEvent<HTMLInputElement>) => {
    const compositionData = firstNameCompositionRef.current;
    // 変換前のひらがなをカタカナに変換してセット（カナが空の場合のみ）
    if (compositionData && isKana(compositionData) && !newChildFirstNameKana) {
      setNewChildFirstNameKana(hiraganaToKatakana(compositionData));
    }
    firstNameCompositionRef.current = '';
  };

  // Fetch children on mount
  useEffect(() => {
    fetchChildren();
  }, []);

  const fetchChildren = async () => {
    try {
      setLoading(true);
      const data = await getChildren();
      // Map API response to our Child type
      const mappedChildren: Child[] = data.map((child: any) => ({
        id: child.id,
        student_no: child.student_no || child.studentNo || '',
        last_name: child.last_name || child.lastName || '',
        first_name: child.first_name || child.firstName || '',
        full_name: child.full_name || child.fullName || `${child.last_name || child.lastName || ''} ${child.first_name || child.firstName || ''}`,
        birth_date: child.birth_date || child.birthDate,
        gender: child.gender,
        grade: child.grade || child.gradeText || '',
        grade_name: child.grade_name || child.gradeName || child.grade || child.gradeText || '',
        school_name: child.school_name || child.schoolName,
        status: child.status || 'active',
        enrollment_date: child.enrollment_date || child.enrollmentDate,
        guardian_id: child.guardian_id || child.guardianId,
        guardian_name: child.guardian_name || child.guardianName,
      }));
      setChildren(mappedChildren);
    } catch (error: any) {
      console.error('Failed to fetch children:', error);
      toast({
        title: 'エラー',
        description: error.message || 'お子様情報の取得に失敗しました',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const calculateAge = (birthDate: string): number | null => {
    if (!birthDate) return null;
    const birth = new Date(birthDate);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  };

  // 生年月日から学年を自動計算（日本の学年制度: 4月2日〜翌年4月1日生まれが同学年）
  const calculateGradeFromBirthDate = (birthDate: string): string => {
    if (!birthDate) return '';

    const birth = new Date(birthDate);
    const today = new Date();
    const currentYear = today.getFullYear();
    const currentMonth = today.getMonth() + 1; // 0-indexed to 1-indexed

    // 学年度の開始は4月
    // 現在が1-3月なら前年度として計算
    const fiscalYear = currentMonth >= 4 ? currentYear : currentYear - 1;

    const birthYear = birth.getFullYear();
    const birthMonth = birth.getMonth() + 1;
    const birthDay = birth.getDate();

    // 「早生まれ」判定（1月1日〜4月1日生まれ）
    // 早生まれは前年度の学年に入る
    const isEarlyBorn = birthMonth < 4 || (birthMonth === 4 && birthDay === 1);

    // 小学1年生に入学する年度を計算
    // 日本の学年制度: 4月2日〜翌年4月1日生まれが同学年
    // 4月2日〜12月31日生まれ: 翌年度の4月に満7歳になる年に入学（birthYear + 7年度）
    // 1月1日〜4月1日生まれ（早生まれ）: 同年度の4月に満6歳で入学（birthYear + 6年度）
    let firstGradeYear: number;
    if (isEarlyBorn) {
      // 早生まれ: 例) 2014年2月生まれ → 2020年度に小1入学（2014+6=2020）
      firstGradeYear = birthYear + 6;
    } else {
      // 通常: 例) 2014年5月生まれ → 2021年度に小1入学（2014+7=2021）
      firstGradeYear = birthYear + 7;
    }

    // 現在の学年度から入学年度を引いて学年を計算
    const gradeNumber = fiscalYear - firstGradeYear + 1;

    // 学年を決定
    if (gradeNumber < -5) return '未就園';
    if (gradeNumber === -5) return '年少';
    if (gradeNumber === -4) return '年中';
    if (gradeNumber === -3) return '年長';
    if (gradeNumber === -2) return '年長'; // まだ入学前
    if (gradeNumber === -1) return '年長'; // まだ入学前
    if (gradeNumber === 0) return '年長'; // まだ入学前
    if (gradeNumber === 1) return '小学1年生';
    if (gradeNumber === 2) return '小学2年生';
    if (gradeNumber === 3) return '小学3年生';
    if (gradeNumber === 4) return '小学4年生';
    if (gradeNumber === 5) return '小学5年生';
    if (gradeNumber === 6) return '小学6年生';
    if (gradeNumber === 7) return '中学1年生';
    if (gradeNumber === 8) return '中学2年生';
    if (gradeNumber === 9) return '中学3年生';
    if (gradeNumber === 10) return '高校1年生';
    if (gradeNumber === 11) return '高校2年生';
    if (gradeNumber === 12) return '高校3年生';
    if (gradeNumber >= 13) return '高校卒業以上';

    return '';
  };

  // 生年月日が変更されたときに学年を自動設定
  const handleBirthDateChange = (birthDate: string) => {
    setNewChildBirthDate(birthDate);
    if (birthDate) {
      const calculatedGrade = calculateGradeFromBirthDate(birthDate);
      setNewChildGrade(calculatedGrade);
    }
  };

  const resetForm = () => {
    setNewChildLastName('');
    setNewChildFirstName('');
    setNewChildLastNameKana('');
    setNewChildFirstNameKana('');
    setNewChildBirthDate('');
    setNewChildGender('');
    setNewChildSchoolName('');
    setNewChildGrade('');
  };

  const handleAddChild = async () => {
    if (!newChildLastName || !newChildFirstName) {
      toast({
        title: 'エラー',
        description: '姓と名は必須です',
        variant: 'destructive',
      });
      return;
    }

    try {
      setCreating(true);

      const requestData: CreateStudentRequest = {
        last_name: newChildLastName,
        first_name: newChildFirstName,
        last_name_kana: newChildLastNameKana || undefined,
        first_name_kana: newChildFirstNameKana || undefined,
        birth_date: newChildBirthDate || undefined,
        gender: newChildGender as 'male' | 'female' | 'other' | undefined,
        school_name: newChildSchoolName || undefined,
        grade: newChildGrade || undefined,
      };

      const response = await createStudent(requestData);

      // Add new child to list
      const newChild: Child = {
        id: response.id,
        student_no: response.student_no,
        last_name: response.last_name,
        first_name: response.first_name,
        full_name: response.full_name,
        birth_date: response.birth_date,
        gender: response.gender,
        grade: response.grade,
        grade_name: response.grade_name,
        school_name: response.school_name,
        status: response.status,
        enrollment_date: response.enrollment_date,
        guardian_id: response.guardian_id,
        guardian_name: response.guardian_name,
      };

      setChildren([...children, newChild]);
      setShowAddDialog(false);
      resetForm();

      toast({
        title: '登録が完了しました',
        description: `${newChild.full_name}さんをお子様として登録しました`,
      });
    } catch (error: any) {
      console.error('Failed to create student:', error);
      toast({
        title: 'エラー',
        description: error.message || 'お子様の登録に失敗しました',
        variant: 'destructive',
      });
    } finally {
      setCreating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { label: string; className: string }> = {
      registered: { label: '登録のみ', className: 'bg-gray-100 text-gray-700' },
      trial: { label: '体験', className: 'bg-purple-100 text-purple-700' },
      enrolled: { label: '入会', className: 'bg-green-100 text-green-700' },
      suspended: { label: '休会', className: 'bg-yellow-100 text-yellow-700' },
      withdrawn: { label: '退会', className: 'bg-red-100 text-red-700' },
      // 旧ステータス（互換性のため）
      active: { label: '在籍中', className: 'bg-green-100 text-green-700' },
      resting: { label: '休塾中', className: 'bg-yellow-100 text-yellow-700' },
      graduated: { label: '卒業', className: 'bg-blue-100 text-blue-700' },
      prospective: { label: '見込み', className: 'bg-purple-100 text-purple-700' },
    };
    const statusInfo = statusMap[status] || { label: status, className: 'bg-gray-100 text-gray-700' };
    return <Badge className={statusInfo.className}>{statusInfo.label}</Badge>;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center">
            <Link href="/" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <h1 className="text-xl font-bold text-gray-800">お子様管理</h1>
          </div>
          <Button
            size="sm"
            className="rounded-full bg-blue-600 hover:bg-blue-700"
            onClick={() => setShowAddDialog(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            追加
          </Button>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        <Card className="rounded-xl shadow-md bg-blue-50 border-blue-200 mb-6">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <User className="h-6 w-6 text-blue-600" />
              <div>
                <h3 className="font-semibold text-gray-800 mb-1">お子様情報</h3>
                <p className="text-sm text-gray-600">
                  {loading ? '読み込み中...' : `登録されているお子様: ${children.length}名`}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : (
          <div className="space-y-3">
            {children.map((child) => {
              const age = child.birth_date ? calculateAge(child.birth_date) : null;
              return (
                <Card
                  key={child.id}
                  className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => router.push(`/children/${child.id}`)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-4">
                      <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center shrink-0">
                        <User className="h-7 w-7 text-blue-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-gray-800 text-lg">
                            {child.student_no} {child.full_name}
                          </h3>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">
                          {age !== null && `${age}歳`}
                          {age !== null && (child.grade_name || child.grade) && ' / '}
                          {child.grade_name || child.grade || ''}
                        </p>
                        {child.school_name && (
                          <p className="text-xs text-gray-500">{child.school_name}</p>
                        )}
                      </div>
                      <ChevronRight className="h-5 w-5 text-gray-400 mt-3" />
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {!loading && children.length === 0 && (
          <div className="text-center py-12">
            <User className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-600 mb-4">お子様が登録されていません</p>
            <Button
              className="rounded-full bg-blue-600 hover:bg-blue-700"
              onClick={() => setShowAddDialog(true)}
            >
              <Plus className="h-4 w-4 mr-2" />
              お子様を追加
            </Button>
          </div>
        )}
      </main>

      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="max-w-[340px] rounded-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>お子様を追加</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label htmlFor="lastName">姓 *</Label>
                <Input
                  id="lastName"
                  placeholder="山田"
                  value={newChildLastName}
                  onChange={(e) => setNewChildLastName(e.target.value)}
                  onCompositionUpdate={handleLastNameCompositionUpdate}
                  onCompositionEnd={handleLastNameCompositionEnd}
                  className="rounded-xl mt-1"
                />
              </div>
              <div>
                <Label htmlFor="firstName">名 *</Label>
                <Input
                  id="firstName"
                  placeholder="太郎"
                  value={newChildFirstName}
                  onChange={(e) => setNewChildFirstName(e.target.value)}
                  onCompositionUpdate={handleFirstNameCompositionUpdate}
                  onCompositionEnd={handleFirstNameCompositionEnd}
                  className="rounded-xl mt-1"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label htmlFor="lastNameKana">姓（カナ）</Label>
                <Input
                  id="lastNameKana"
                  placeholder="ヤマダ"
                  value={newChildLastNameKana}
                  onChange={(e) => setNewChildLastNameKana(e.target.value)}
                  className="rounded-xl mt-1"
                />
              </div>
              <div>
                <Label htmlFor="firstNameKana">名（カナ）</Label>
                <Input
                  id="firstNameKana"
                  placeholder="タロウ"
                  value={newChildFirstNameKana}
                  onChange={(e) => setNewChildFirstNameKana(e.target.value)}
                  className="rounded-xl mt-1"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="birthDate">生年月日</Label>
              <Input
                id="birthDate"
                type="date"
                value={newChildBirthDate}
                onChange={(e) => handleBirthDateChange(e.target.value)}
                className="rounded-xl mt-1"
              />
            </div>
            <div>
              <Label htmlFor="gender">性別</Label>
              <Select value={newChildGender} onValueChange={setNewChildGender}>
                <SelectTrigger className="rounded-xl mt-1">
                  <SelectValue placeholder="選択してください" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="male">男性</SelectItem>
                  <SelectItem value="female">女性</SelectItem>
                  <SelectItem value="other">その他</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="schoolName">在籍学校名</Label>
              <Input
                id="schoolName"
                placeholder="○○小学校"
                value={newChildSchoolName}
                onChange={(e) => setNewChildSchoolName(e.target.value)}
                className="rounded-xl mt-1"
              />
            </div>
            <div>
              <Label htmlFor="grade">学年（自動計算）</Label>
              <Input
                id="grade"
                placeholder="生年月日から自動計算されます"
                value={newChildGrade}
                onChange={(e) => setNewChildGrade(e.target.value)}
                className="rounded-xl mt-1 bg-gray-50"
                readOnly={!!newChildBirthDate}
              />
              {newChildBirthDate && (
                <p className="text-xs text-gray-500 mt-1">生年月日から自動計算されました</p>
              )}
            </div>
            <div className="flex gap-2 pt-4">
              <Button
                variant="outline"
                className="flex-1 rounded-xl"
                onClick={() => {
                  setShowAddDialog(false);
                  resetForm();
                }}
                disabled={creating}
              >
                キャンセル
              </Button>
              <Button
                className="flex-1 rounded-xl bg-blue-600 hover:bg-blue-700"
                onClick={handleAddChild}
                disabled={!newChildLastName || !newChildFirstName || creating}
              >
                {creating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    登録中...
                  </>
                ) : (
                  '追加'
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <BottomTabBar />
    </div>
  );
}
