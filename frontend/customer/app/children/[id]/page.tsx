'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import { useParams } from 'next/navigation';
import { ChevronLeft, User, Loader2, Edit2, Save, X, Ticket, QrCode, Mail, Phone, Camera } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { useToast } from '@/hooks/use-toast';
import { QRCodeCanvas } from 'qrcode.react';
import { AuthGuard } from '@/components/auth';
import { useStudent, useUpdateStudent, useStudentQRCode, useUploadStudentPhoto } from '@/lib/hooks/use-students';

type ChildDetail = {
  id: string;
  student_no: string;
  last_name: string;
  first_name: string;
  full_name: string;
  last_name_kana?: string;
  first_name_kana?: string;
  full_name_kana?: string;
  display_name?: string;
  birth_date?: string;
  gender?: string;
  email?: string;
  phone?: string;
  line_id?: string;
  school_name?: string;
  school_type?: string;
  grade?: string;
  grade_name?: string;
  profile_image_url?: string;
  status: string;
  registered_date?: string;
  trial_date?: string;
  enrollment_date?: string;
  suspended_date?: string;
  withdrawal_date?: string;
  withdrawal_reason?: string;
  notes?: string;
  tags?: string[];
  primary_school_name?: string;
  primary_brand_name?: string;
  brand_names?: string[];
  guardian_id?: string;
  guardian_name?: string;
  created_at?: string;
  updated_at?: string;
};

function ChildDetailContent() {
  const params = useParams();
  const { toast } = useToast();
  const childId = params.id as string;

  // React Queryフックを使用
  const { data: studentData, isLoading: studentLoading, error: studentError } = useStudent(childId);
  const { data: qrCodeInfo } = useStudentQRCode(childId);
  const updateMutation = useUpdateStudent();
  const uploadPhotoMutation = useUploadStudentPhoto();

  const [isEditing, setIsEditing] = useState(false);
  const photoInputRef = useRef<HTMLInputElement>(null);

  // 編集用のstate
  const [editLastName, setEditLastName] = useState('');
  const [editFirstName, setEditFirstName] = useState('');
  const [editBirthDate, setEditBirthDate] = useState('');
  const [editGender, setEditGender] = useState('');

  // APIレスポンスをChildDetail型にマッピング
  const child = useMemo((): ChildDetail | null => {
    if (!studentData) return null;
    const data: any = studentData;
    return {
      id: data.id,
      student_no: data.student_no || data.studentNo || '',
      last_name: data.last_name || data.lastName || '',
      first_name: data.first_name || data.firstName || '',
      full_name: data.full_name || data.fullName || '',
      last_name_kana: data.last_name_kana || data.lastNameKana,
      first_name_kana: data.first_name_kana || data.firstNameKana,
      full_name_kana: data.full_name_kana || data.fullNameKana,
      display_name: data.display_name || data.displayName,
      birth_date: data.birth_date || data.birthDate,
      gender: data.gender,
      email: data.email,
      phone: data.phone,
      line_id: data.line_id || data.lineId,
      school_name: data.school_name || data.schoolName,
      school_type: data.school_type || data.schoolType,
      grade: data.grade || data.gradeText,
      grade_name: data.grade_name || data.gradeName || data.gradeText,
      profile_image_url: data.profile_image_url || data.profileImageUrl,
      status: data.status || 'registered',
      registered_date: data.registered_date || data.registeredDate,
      trial_date: data.trial_date || data.trialDate,
      enrollment_date: data.enrollment_date || data.enrollmentDate,
      suspended_date: data.suspended_date || data.suspendedDate,
      withdrawal_date: data.withdrawal_date || data.withdrawalDate,
      withdrawal_reason: data.withdrawal_reason || data.withdrawalReason,
      notes: data.notes,
      tags: data.tags,
      primary_school_name: data.primary_school_name || data.primarySchoolName,
      primary_brand_name: data.primary_brand_name || data.primaryBrandName,
      brand_names: data.brand_names || data.brandNames || [],
      guardian_id: data.guardian_id || data.guardianId,
      guardian_name: data.guardian_name || data.guardianName,
      created_at: data.created_at || data.createdAt,
      updated_at: data.updated_at || data.updatedAt,
    };
  }, [studentData]);

  // 編集用stateを初期化
  useEffect(() => {
    if (child) {
      setEditLastName(child.last_name);
      setEditFirstName(child.first_name);
      setEditBirthDate(child.birth_date || '');
      setEditGender(child.gender || '');
    }
  }, [child]);

  const loading = studentLoading;

  // エラー表示
  useEffect(() => {
    if (studentError) {
      toast({
        title: 'エラー',
        description: 'お子様情報の取得に失敗しました',
        variant: 'destructive',
      });
    }
  }, [studentError, toast]);

  const handleSave = async () => {
    if (!child) return;

    try {
      await updateMutation.mutateAsync({
        id: child.id,
        data: {
          lastName: editLastName,
          firstName: editFirstName,
          birthDate: editBirthDate || undefined,
          gender: editGender as 'male' | 'female' | 'other' | undefined,
        },
      });

      setIsEditing(false);
      toast({
        title: '更新完了',
        description: 'お子様情報を更新しました',
      });
    } catch (error: any) {
      console.error('Failed to update child:', error);
      toast({
        title: 'エラー',
        description: error.message || 'お子様情報の更新に失敗しました',
        variant: 'destructive',
      });
    }
  };

  const handleCancelEdit = () => {
    if (child) {
      setEditLastName(child.last_name);
      setEditFirstName(child.first_name);
      setEditBirthDate(child.birth_date || '');
      setEditGender(child.gender || '');
    }
    setIsEditing(false);
  };

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !child) return;

    // ファイルサイズチェック（5MB）
    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: 'エラー',
        description: 'ファイルサイズは5MB以下にしてください',
        variant: 'destructive',
      });
      return;
    }

    // ファイル形式チェック
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast({
        title: 'エラー',
        description: 'JPG, PNG, GIF, WEBPファイルのみアップロード可能です',
        variant: 'destructive',
      });
      return;
    }

    try {
      await uploadPhotoMutation.mutateAsync({ id: child.id, file });
      toast({
        title: '完了',
        description: '写真をアップロードしました',
      });
    } catch (error: any) {
      console.error('Photo upload error:', error);
      toast({
        title: 'エラー',
        description: error.message || '写真のアップロードに失敗しました',
        variant: 'destructive',
      });
    } finally {
      // inputをリセット
      if (photoInputRef.current) {
        photoInputRef.current.value = '';
      }
    }
  };

  const saving = updateMutation.isPending;
  const uploadingPhoto = uploadPhotoMutation.isPending;

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

  const formatDate = (dateString?: string): string => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getGenderLabel = (gender?: string): string => {
    const genderMap: Record<string, string> = {
      male: '男性',
      female: '女性',
      other: 'その他',
    };
    return gender ? genderMap[gender] || gender : '-';
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { label: string; className: string }> = {
      registered: { label: '登録のみ', className: 'bg-gray-100 text-gray-700' },
      trial: { label: '体験', className: 'bg-purple-100 text-purple-700' },
      enrolled: { label: '入会', className: 'bg-green-100 text-green-700' },
      suspended: { label: '休会', className: 'bg-yellow-100 text-yellow-700' },
      withdrawn: { label: '退会', className: 'bg-red-100 text-red-700' },
    };
    const statusInfo = statusMap[status] || { label: status, className: 'bg-gray-100 text-gray-700' };
    return <Badge className={statusInfo.className}>{statusInfo.label}</Badge>;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!child) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
            <Link href="/children" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <h1 className="text-xl font-bold text-gray-800">お子様詳細</h1>
          </div>
        </header>
        <main className="max-w-[390px] mx-auto px-4 py-6 text-center">
          <p className="text-gray-600">お子様情報が見つかりませんでした</p>
        </main>
        <BottomTabBar />
      </div>
    );
  }

  const age = child.birth_date ? calculateAge(child.birth_date) : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center">
            <Link href="/children" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <h1 className="text-xl font-bold text-gray-800">お子様詳細</h1>
          </div>
          {!isEditing && (
            <Button
              size="sm"
              variant="outline"
              className="rounded-full"
              onClick={() => setIsEditing(true)}
            >
              <Edit2 className="h-4 w-4 mr-1" />
              編集
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24 space-y-4">
        {/* プロフィールカード */}
        <Card className="rounded-xl shadow-md">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              {/* 写真アップロード */}
              <input
                type="file"
                ref={photoInputRef}
                onChange={handlePhotoUpload}
                accept="image/jpeg,image/png,image/gif,image/webp"
                className="hidden"
              />
              <button
                onClick={() => photoInputRef.current?.click()}
                disabled={uploadingPhoto}
                className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center shrink-0 relative cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 border-2 border-dashed border-blue-300"
              >
                {child.profile_image_url ? (
                  <img
                    src={child.profile_image_url}
                    alt={child.full_name}
                    className="w-full h-full rounded-full object-cover"
                  />
                ) : (
                  <div className="flex flex-col items-center">
                    {uploadingPhoto ? (
                      <Loader2 className="h-6 w-6 text-blue-600 animate-spin" />
                    ) : (
                      <>
                        <Camera className="h-6 w-6 text-blue-600" />
                        <span className="text-[10px] text-blue-600 mt-1">写真</span>
                      </>
                    )}
                  </div>
                )}
                {/* アップロード中オーバーレイ */}
                {uploadingPhoto && child.profile_image_url && (
                  <div className="absolute inset-0 rounded-full bg-black/40 flex items-center justify-center">
                    <Loader2 className="w-6 h-6 text-white animate-spin" />
                  </div>
                )}
              </button>
              <div className="flex-1">
                {isEditing ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label className="text-xs text-gray-500">姓</Label>
                        <Input
                          value={editLastName}
                          onChange={(e) => setEditLastName(e.target.value)}
                          className="h-9 rounded-lg"
                        />
                      </div>
                      <div>
                        <Label className="text-xs text-gray-500">名</Label>
                        <Input
                          value={editFirstName}
                          onChange={(e) => setEditFirstName(e.target.value)}
                          className="h-9 rounded-lg"
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2 mb-1">
                      <h2 className="text-xl font-bold text-gray-800">{child.full_name}</h2>
                      {getStatusBadge(child.status)}
                    </div>
                    {child.full_name_kana && (
                      <p className="text-sm text-gray-500 mb-1">{child.full_name_kana}</p>
                    )}
                    <p className="text-sm text-gray-600">
                      生徒番号: {child.student_no}
                    </p>
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* QRコード */}
        <Card className="rounded-xl shadow-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-gray-700 flex items-center gap-2">
              <QrCode className="h-5 w-5 text-blue-600" />
              出席用QRコード
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center">
              {qrCodeInfo ? (
                <>
                  <div className="p-4 bg-white rounded-xl border-2 border-blue-100">
                    <QRCodeCanvas
                      value={qrCodeInfo.qr_code}
                      size={160}
                      level="H"
                      includeMargin={true}
                    />
                  </div>
                  <p className="mt-3 text-sm text-gray-600 font-medium">
                    {qrCodeInfo.student_name}
                  </p>
                  <p className="text-xs text-gray-500">
                    生徒番号: {qrCodeInfo.student_no}
                  </p>
                  <p className="mt-3 text-xs text-gray-400 text-center">
                    このQRコードを校舎のタブレットにかざして出席
                  </p>
                </>
              ) : (
                <div className="py-6 text-center">
                  <QrCode className="h-12 w-12 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">QRコードを取得できません</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 基本情報 */}
        <Card className="rounded-xl shadow-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-gray-700">基本情報</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {isEditing ? (
              <>
                <div className="py-2 border-b border-gray-100">
                  <Label className="text-sm text-gray-500">生年月日</Label>
                  <Input
                    type="date"
                    value={editBirthDate}
                    onChange={(e) => setEditBirthDate(e.target.value)}
                    className="mt-1 rounded-lg"
                  />
                </div>
                <div className="py-2 border-b border-gray-100">
                  <Label className="text-sm text-gray-500">性別</Label>
                  <Select value={editGender} onValueChange={setEditGender}>
                    <SelectTrigger className="mt-1 rounded-lg">
                      <SelectValue placeholder="選択してください" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male">男性</SelectItem>
                      <SelectItem value="female">女性</SelectItem>
                      <SelectItem value="other">その他</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">学年</span>
                  <span className="text-sm font-medium text-gray-800">{child.grade_name || child.grade || '-'}</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm text-gray-500">在籍学校</span>
                  <span className="text-sm font-medium text-gray-800">{child.school_name || '-'}</span>
                </div>
              </>
            ) : (
              <>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">生年月日</span>
                  <span className="text-sm font-medium text-gray-800">
                    {formatDate(child.birth_date)}
                    {age !== null && ` (${age}歳)`}
                  </span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">性別</span>
                  <span className="text-sm font-medium text-gray-800">{getGenderLabel(child.gender)}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">学年</span>
                  <span className="text-sm font-medium text-gray-800">{child.grade_name || child.grade || '-'}</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm text-gray-500">在籍学校</span>
                  <span className="text-sm font-medium text-gray-800">{child.school_name || '-'}</span>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* 編集ボタン */}
        {isEditing && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1 rounded-xl"
              onClick={handleCancelEdit}
              disabled={saving}
            >
              <X className="h-4 w-4 mr-1" />
              キャンセル
            </Button>
            <Button
              className="flex-1 rounded-xl bg-blue-600 hover:bg-blue-700"
              onClick={handleSave}
              disabled={saving || !editLastName || !editFirstName}
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  保存中...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-1" />
                  保存
                </>
              )}
            </Button>
          </div>
        )}

        {/* 連絡先 */}
        {(child.email || child.phone || child.line_id) && (
          <Card className="rounded-xl shadow-md">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold text-gray-700">連絡先</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {child.email && (
                <div className="flex items-center gap-3 py-2 border-b border-gray-100">
                  <Mail className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-800">{child.email}</span>
                </div>
              )}
              {child.phone && (
                <div className="flex items-center gap-3 py-2 border-b border-gray-100">
                  <Phone className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-800">{child.phone}</span>
                </div>
              )}
              {child.line_id && (
                <div className="flex items-center gap-3 py-2">
                  <span className="text-xs text-gray-400 font-medium">LINE</span>
                  <span className="text-sm text-gray-800">{child.line_id}</span>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* 所属情報 */}
        <Card className="rounded-xl shadow-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-gray-700">所属情報</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-sm text-gray-500">主所属校舎</span>
              <span className="text-sm font-medium text-gray-800">{child.primary_school_name || '-'}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-sm text-gray-500">主所属ブランド</span>
              <span className="text-sm font-medium text-gray-800">{child.primary_brand_name || '-'}</span>
            </div>
            {child.brand_names && child.brand_names.length > 0 && (
              <div className="py-2">
                <span className="text-sm text-gray-500 block mb-2">所属ブランド</span>
                <div className="flex flex-wrap gap-2">
                  {child.brand_names.map((brand, index) => (
                    <Badge key={index} variant="secondary" className="bg-blue-50 text-blue-700">
                      {brand}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* チケット購入リンク */}
        <Card className="rounded-xl shadow-md bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
          <CardContent className="p-4">
            <Link href={`/ticket-purchase/from-ticket?childId=${child.id}&childName=${encodeURIComponent(child.full_name)}&grade=${encodeURIComponent(child.grade_name || child.grade || '')}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                    <Ticket className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-800">チケット購入</h3>
                    <p className="text-sm text-gray-500">このお子様のチケットを購入</p>
                  </div>
                </div>
                <ChevronLeft className="h-5 w-5 text-gray-400 rotate-180" />
              </div>
            </Link>
          </CardContent>
        </Card>

        {/* ステータス履歴 */}
        <Card className="rounded-xl shadow-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-gray-700">ステータス履歴</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {child.registered_date && (
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">登録日</span>
                <span className="text-sm font-medium text-gray-800">{formatDate(child.registered_date)}</span>
              </div>
            )}
            {child.trial_date && (
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">体験日</span>
                <span className="text-sm font-medium text-gray-800">{formatDate(child.trial_date)}</span>
              </div>
            )}
            {child.enrollment_date && (
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">入会日</span>
                <span className="text-sm font-medium text-gray-800">{formatDate(child.enrollment_date)}</span>
              </div>
            )}
            {child.suspended_date && (
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">休会日</span>
                <span className="text-sm font-medium text-gray-800">{formatDate(child.suspended_date)}</span>
              </div>
            )}
            {child.withdrawal_date && (
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">退会日</span>
                <span className="text-sm font-medium text-gray-800">{formatDate(child.withdrawal_date)}</span>
              </div>
            )}
            {child.withdrawal_reason && (
              <div className="py-2">
                <span className="text-sm text-gray-500 block mb-1">退会理由</span>
                <span className="text-sm text-gray-800">{child.withdrawal_reason}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 備考 */}
        {child.notes && (
          <Card className="rounded-xl shadow-md">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold text-gray-700">備考</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-800 whitespace-pre-wrap">{child.notes}</p>
            </CardContent>
          </Card>
        )}
      </main>

      <BottomTabBar />
    </div>
  );
}


export default function ChildDetailPage() {
  return (
    <AuthGuard>
      <ChildDetailContent />
    </AuthGuard>
  );
}
