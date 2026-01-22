"use client";

import { Student, PaginatedResult } from "@/lib/api/staff";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { GraduationCap, MessageCircle } from "lucide-react";

interface StudentListProps {
  result: PaginatedResult<Student>;
  selectedStudentId?: string;
  onSelectStudent: (studentId: string) => void;
  unreadCounts?: Record<string, number>; // 生徒IDごとの未読件数
}

// ステータスの日本語変換
function getStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    registered: "登録済",
    enrolled: "在籍",
    suspended: "休会",
    withdrawn: "退会",
    graduated: "卒業",
  };
  return statusMap[status] || status;
}

function getStatusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  if (status === "enrolled") return "default";
  if (status === "suspended") return "secondary";
  if (status === "withdrawn" || status === "graduated") return "outline";
  return "secondary";
}

export function StudentList({ result, selectedStudentId, onSelectStudent, unreadCounts = {} }: StudentListProps) {
  const { data: students } = result;

  if (students.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 py-12">
        <GraduationCap className="w-16 h-16 mb-4 text-gray-300" />
        <p>生徒が見つかりません</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {students.map((student) => {
        // 名前を生成（fullNameがあれば使用、なければ姓名を結合）
        // APIはcamelCase（lastName, firstName）またはsnake_case（last_name, first_name）で返す
        const lastName = student.lastName || student.last_name || "";
        const firstName = student.firstName || student.first_name || "";
        const studentName = student.fullName || student.full_name || `${lastName} ${firstName}`.trim();
        // 学年
        const gradeText = student.gradeText || student.grade_text || student.gradeName || "";
        // 生徒番号
        const studentNo = student.studentNo || student.student_no || "";
        // 保護者番号（家族ID）
        const guardianNo = (student as any).guardianNo || (student as any).guardian_no || student.guardian?.guardian_no || "";
        // 未読件数
        const unreadCount = unreadCounts[student.id] || 0;

        return (
          <div
            key={student.id}
            className={cn(
              "px-2 py-1 cursor-pointer hover:bg-blue-50 transition-all border-b border-gray-100",
              selectedStudentId === student.id && "bg-blue-50 border-l-4 border-l-blue-500",
              unreadCount > 0 && "bg-red-50"
            )}
            onClick={() => onSelectStudent(student.id)}
          >
            <div className="flex items-center gap-1.5">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-medium text-gray-900 text-xs truncate">{studentName || "名前未設定"}</span>
                  {gradeText && <span className="text-[10px] text-gray-500">{gradeText}</span>}
                  <Badge
                    variant={getStatusVariant(student.status)}
                    className="text-[9px] px-1 py-0 h-4"
                  >
                    {getStatusLabel(student.status)}
                  </Badge>
                  {unreadCount > 0 && (
                    <span className="flex items-center gap-0.5 bg-red-500 text-white text-[9px] px-1 py-0 rounded-full">
                      <MessageCircle className="w-2.5 h-2.5" />
                      {unreadCount}
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-gray-400 flex gap-2">
                  {guardianNo && <span>家族ID {guardianNo}</span>}
                  {studentNo && <span>生徒ID {studentNo}</span>}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
