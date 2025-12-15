"use client";

import { Student, Guardian, LessonSchedule } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Mail,
  Phone,
  Calendar,
  Edit,
  MessageCircle,
  User,
  MapPin,
  School,
} from "lucide-react";
import { format } from "date-fns";
import { ja } from "date-fns/locale";

interface StudentDetailProps {
  student: Student;
  parents: Guardian[];
  lessons: LessonSchedule[];
}

// ステータスの日本語変換
function getStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    registered: "登録済",
    enrolled: "在籍中",
    suspended: "休会中",
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

export function StudentDetail({ student, parents, lessons }: StudentDetailProps) {
  // 名前を生成
  const studentName = student.full_name || `${student.last_name} ${student.first_name}`.trim();
  const studentNameKana = student.full_name_kana || `${student.last_name_kana} ${student.first_name_kana}`.trim();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">{studentName}</h2>
        {studentNameKana && (
          <p className="text-sm text-gray-500">{studentNameKana}</p>
        )}
        {student.grade_text && (
          <p className="text-sm text-gray-600 mt-1">{student.grade_text}</p>
        )}
        {student.student_no && (
          <p className="text-xs text-gray-400 mt-1">生徒番号: {student.student_no}</p>
        )}
      </div>

      <div className="flex gap-2">
        <Button className="flex-1">
          <MessageCircle className="w-4 h-4 mr-2" />
          チャット
        </Button>
        <Button variant="outline" className="flex-1">
          <Edit className="w-4 h-4 mr-2" />
          編集
        </Button>
      </div>

      <Separator />

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">基本情報</h3>
        <div className="space-y-2 text-sm">
          {student.primary_school && (
            <div className="flex justify-between">
              <span className="text-gray-600">所属校舎</span>
              <span className="font-medium">
                {student.primary_school.school_name_short || student.primary_school.school_name}
              </span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-gray-600">在籍状況</span>
            <Badge variant={getStatusVariant(student.status)}>
              {getStatusLabel(student.status)}
            </Badge>
          </div>
          {student.birth_date && (
            <div className="flex justify-between">
              <span className="text-gray-600">生年月日</span>
              <span className="font-medium">
                {format(new Date(student.birth_date), "yyyy年M月d日", { locale: ja })}
              </span>
            </div>
          )}
          {student.gender && (
            <div className="flex justify-between">
              <span className="text-gray-600">性別</span>
              <span className="font-medium">
                {student.gender === "male" ? "男性" : student.gender === "female" ? "女性" : student.gender}
              </span>
            </div>
          )}
          {student.school_name && (
            <div className="flex justify-between">
              <span className="text-gray-600">学校名</span>
              <span className="font-medium">{student.school_name}</span>
            </div>
          )}
        </div>
      </div>

      <Separator />

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">連絡先</h3>
        <div className="space-y-2 text-sm">
          {student.email && (
            <div className="flex items-center gap-2">
              <Mail className="w-4 h-4 text-gray-400" />
              <span>{student.email}</span>
            </div>
          )}
          {student.phone && (
            <div className="flex items-center gap-2">
              <Phone className="w-4 h-4 text-gray-400" />
              <span>{student.phone}</span>
            </div>
          )}
          {student.phone2 && (
            <div className="flex items-center gap-2">
              <Phone className="w-4 h-4 text-gray-400" />
              <span>{student.phone2}</span>
            </div>
          )}
          {(student.postal_code || student.prefecture || student.city || student.address1) && (
            <div className="flex items-start gap-2">
              <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
              <div>
                {student.postal_code && <span className="text-gray-500">〒{student.postal_code}</span>}
                <br />
                {`${student.prefecture || ""}${student.city || ""}${student.address1 || ""}${student.address2 || ""}`}
              </div>
            </div>
          )}
        </div>
      </div>

      <Separator />

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">保護者情報</h3>
        {parents.length > 0 ? (
          <div className="space-y-3">
            {parents.map((parent) => {
              const parentName = parent.full_name || `${parent.last_name} ${parent.first_name}`.trim();
              return (
                <Card key={parent.id} className="p-3">
                  <div className="flex items-start gap-3">
                    <User className="w-5 h-5 text-gray-400 mt-0.5" />
                    <div className="flex-1 space-y-1">
                      <p className="font-medium text-gray-900">{parentName}</p>
                      {parent.guardian_no && (
                        <p className="text-xs text-gray-400">No. {parent.guardian_no}</p>
                      )}
                      {parent.email && (
                        <div className="flex items-center gap-2 text-xs text-gray-600">
                          <Mail className="w-3 h-3" />
                          {parent.email}
                        </div>
                      )}
                      {parent.phone && (
                        <div className="flex items-center gap-2 text-xs text-gray-600">
                          <Phone className="w-3 h-3" />
                          {parent.phone}
                        </div>
                      )}
                      {parent.phone_mobile && parent.phone_mobile !== parent.phone && (
                        <div className="flex items-center gap-2 text-xs text-gray-600">
                          <Phone className="w-3 h-3" />
                          {parent.phone_mobile}（携帯）
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-gray-500">保護者情報が登録されていません</p>
        )}
      </div>

      <Separator />

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          授業予定（直近）
        </h3>
        {lessons.length > 0 ? (
          <div className="space-y-2">
            {lessons.map((lesson) => (
              <Card key={lesson.id} className="p-3">
                <div className="flex items-start gap-3">
                  <Calendar className="w-5 h-5 text-gray-400 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">
                      {lesson.date && format(new Date(lesson.date), "yyyy年M月d日", { locale: ja })}
                    </p>
                    {lesson.time_slot && (
                      <p className="text-xs text-gray-500 mt-1">
                        {lesson.time_slot.start_time} - {lesson.time_slot.end_time}
                      </p>
                    )}
                    {lesson.school && (
                      <div className="flex items-center gap-1 mt-1">
                        <School className="w-3 h-3 text-gray-400" />
                        <span className="text-xs text-gray-500">
                          {lesson.school.school_name_short || lesson.school.school_name}
                        </span>
                      </div>
                    )}
                    <Badge variant="outline" className="text-xs mt-1">
                      {lesson.status}
                    </Badge>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">予定されている授業がありません</p>
        )}
      </div>
    </div>
  );
}
