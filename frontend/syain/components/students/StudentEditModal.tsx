'use client';

import { useState, useEffect } from 'react';
import { X, Save, Loader2, AlertCircle, User, School, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { updateStudent, type UpdateStudentRequest } from '@/lib/api/students';
import type { Student } from '@/lib/api/types';

interface StudentEditModalProps {
  student: Student;
  onClose: () => void;
  onSuccess?: (student: Student) => void;
}

const STATUS_OPTIONS = [
  { value: 'inquiry', label: '問い合わせ' },
  { value: 'trial', label: '体験' },
  { value: 'enrolled', label: '在籍' },
  { value: 'suspended', label: '休会' },
  { value: 'withdrawn', label: '退会' },
];

const GRADE_OPTIONS = [
  { value: 'preschool_1', label: '年少' },
  { value: 'preschool_2', label: '年中' },
  { value: 'preschool_3', label: '年長' },
  { value: 'elementary_1', label: '小学1年生' },
  { value: 'elementary_2', label: '小学2年生' },
  { value: 'elementary_3', label: '小学3年生' },
  { value: 'elementary_4', label: '小学4年生' },
  { value: 'elementary_5', label: '小学5年生' },
  { value: 'elementary_6', label: '小学6年生' },
  { value: 'junior_high_1', label: '中学1年生' },
  { value: 'junior_high_2', label: '中学2年生' },
  { value: 'junior_high_3', label: '中学3年生' },
  { value: 'high_school_1', label: '高校1年生' },
  { value: 'high_school_2', label: '高校2年生' },
  { value: 'high_school_3', label: '高校3年生' },
  { value: 'university', label: '大学生' },
  { value: 'adult', label: '社会人' },
];

export function StudentEditModal({ student, onClose, onSuccess }: StudentEditModalProps) {
  const [formData, setFormData] = useState<UpdateStudentRequest>({
    studentNumber: student.student_no || '',
    grade: student.grade || '',
    schoolName: student.school_name || '',
    enrollmentDate: student.enrollment_date || '',
    withdrawalDate: student.withdrawal_date || '',
    status: student.status || 'enrolled',
    notes: student.notes || '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (field: keyof UpdateStudentRequest, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      const updateData: Record<string, any> = {};

      // Only include changed fields
      if (formData.studentNumber !== student.student_no) {
        updateData.student_no = formData.studentNumber;
      }
      if (formData.grade !== student.grade) {
        updateData.grade = formData.grade;
      }
      if (formData.schoolName !== student.school_name) {
        updateData.school_name = formData.schoolName;
      }
      if (formData.enrollmentDate !== student.enrollment_date) {
        updateData.enrollment_date = formData.enrollmentDate || null;
      }
      if (formData.withdrawalDate !== student.withdrawal_date) {
        updateData.withdrawal_date = formData.withdrawalDate || null;
      }
      if (formData.status !== student.status) {
        updateData.status = formData.status;
      }
      if (formData.notes !== student.notes) {
        updateData.notes = formData.notes;
      }

      if (Object.keys(updateData).length === 0) {
        onClose();
        return;
      }

      const updatedStudent = await updateStudent(student.id, updateData);
      onSuccess?.(updatedStudent);
      onClose();
    } catch (err: any) {
      console.error('Failed to update student:', err);
      setError(err.message || '生徒情報の更新に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  const studentName = student.full_name || `${student.last_name || ''} ${student.first_name || ''}`.trim() || '名前未設定';

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 bg-gradient-to-r from-green-600 to-green-700 text-white px-5 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                <User className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">生徒情報の編集</h2>
                <p className="text-green-100 text-sm">{studentName}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Error message */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* 基本情報 */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2 text-sm">
              <User className="w-4 h-4 text-green-600" />
              基本情報
            </h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="studentNumber" className="text-sm">生徒番号</Label>
                <Input
                  id="studentNumber"
                  value={formData.studentNumber}
                  onChange={(e) => handleChange('studentNumber', e.target.value)}
                  placeholder="例: STD001"
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="grade" className="text-sm">学年</Label>
                <Select
                  value={formData.grade}
                  onValueChange={(value) => handleChange('grade', value)}
                >
                  <SelectTrigger id="grade" className="mt-1">
                    <SelectValue placeholder="学年を選択" />
                  </SelectTrigger>
                  <SelectContent>
                    {GRADE_OPTIONS.map(option => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label htmlFor="schoolName" className="text-sm">学校名</Label>
              <Input
                id="schoolName"
                value={formData.schoolName}
                onChange={(e) => handleChange('schoolName', e.target.value)}
                placeholder="例: ○○小学校"
                className="mt-1"
              />
            </div>
          </div>

          {/* 在籍情報 */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2 text-sm">
              <School className="w-4 h-4 text-green-600" />
              在籍情報
            </h3>

            <div>
              <Label htmlFor="status" className="text-sm">ステータス</Label>
              <Select
                value={formData.status}
                onValueChange={(value) => handleChange('status', value)}
              >
                <SelectTrigger id="status" className="mt-1">
                  <SelectValue placeholder="ステータスを選択" />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.map(option => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="enrollmentDate" className="text-sm">入塾日</Label>
                <Input
                  id="enrollmentDate"
                  type="date"
                  value={formData.enrollmentDate}
                  onChange={(e) => handleChange('enrollmentDate', e.target.value)}
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="withdrawalDate" className="text-sm">退塾日</Label>
                <Input
                  id="withdrawalDate"
                  type="date"
                  value={formData.withdrawalDate}
                  onChange={(e) => handleChange('withdrawalDate', e.target.value)}
                  className="mt-1"
                />
              </div>
            </div>
          </div>

          {/* 備考 */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2 text-sm">
              <FileText className="w-4 h-4 text-green-600" />
              その他
            </h3>

            <div>
              <Label htmlFor="notes" className="text-sm">特記事項・備考</Label>
              <textarea
                id="notes"
                value={formData.notes}
                onChange={(e) => handleChange('notes', e.target.value)}
                placeholder="特記事項があれば入力してください"
                className="mt-1 w-full p-2 border rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-green-500 min-h-[100px]"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex-shrink-0 border-t bg-gray-50 px-5 py-3">
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1"
            >
              キャンセル
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="flex-1 bg-green-600 hover:bg-green-700"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  保存中...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  保存する
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
