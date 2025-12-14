"use client";

import { useEffect, useState } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Calendar, Clock } from "lucide-react";
import { getLessons, Lesson } from "@/lib/api/staff";
import { format } from "date-fns";
import { ja } from "date-fns/locale";

// Helper to get scheduled datetime from lesson
function getLessonDateTime(lesson: Lesson): Date {
  if (lesson.scheduled_at) return new Date(lesson.scheduled_at);
  const dateStr = lesson.date;
  const timeStr = lesson.time_slot?.start_time || "00:00:00";
  return new Date(`${dateStr}T${timeStr}`);
}

// Helper to get student display name
function getStudentName(student: Lesson["student"]): string {
  if (!student) return "";
  return student.name || student.full_name || `${student.last_name}${student.first_name}`;
}

// Helper to get student grade
function getStudentGrade(student: Lesson["student"]): string {
  if (!student) return "";
  return student.grade || student.grade_text || "";
}

export default function LessonsPage() {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLessons();
  }, []);

  async function loadLessons() {
    setLoading(true);
    const data = await getLessons();
    setLessons(data);
    setLoading(false);
  }

  const upcomingLessons = lessons.filter(
    (lesson) => getLessonDateTime(lesson) > new Date()
  );
  const pastLessons = lessons.filter(
    (lesson) => getLessonDateTime(lesson) <= new Date()
  );

  return (
    <ThreePaneLayout>
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">授業管理</h1>
          <p className="text-gray-600">
            {upcomingLessons.length}件の今後の授業があります
          </p>
        </div>

        {loading ? (
          <div className="text-center text-gray-500 py-8">読み込み中...</div>
        ) : (
          <div className="space-y-8">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                今後の授業
              </h2>
              {upcomingLessons.length > 0 ? (
                <div className="space-y-2">
                  {upcomingLessons.map((lesson) => (
                    <Card
                      key={lesson.id}
                      className="p-4 hover:shadow-md transition-all"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 mb-1">
                            {lesson.subject || "授業"}
                          </h3>
                          {lesson.student && (
                            <p className="text-sm text-gray-600 mb-2">
                              {getStudentName(lesson.student)}{getStudentGrade(lesson.student) ? `（${getStudentGrade(lesson.student)}）` : ""}
                            </p>
                          )}
                          <div className="flex items-center gap-4 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                              <Calendar className="w-4 h-4" />
                              {format(
                                getLessonDateTime(lesson),
                                "yyyy年M月d日（E）HH:mm",
                                { locale: ja }
                              )}
                            </div>
                            {lesson.duration_minutes && (
                              <div className="flex items-center gap-1">
                                <Clock className="w-4 h-4" />
                                {lesson.duration_minutes}分
                              </div>
                            )}
                          </div>
                          {lesson.staff && (
                            <p className="text-xs text-gray-500 mt-2">
                              講師：{lesson.staff.name}
                            </p>
                          )}
                        </div>
                        <Badge
                          variant={
                            lesson.status === "scheduled"
                              ? "default"
                              : lesson.status === "completed"
                              ? "secondary"
                              : "outline"
                          }
                        >
                          {lesson.status === "scheduled"
                            ? "予定"
                            : lesson.status === "completed"
                            ? "完了"
                            : lesson.status}
                        </Badge>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 text-center py-8">
                  今後の授業はありません
                </p>
              )}
            </div>

            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                過去の授業
              </h2>
              {pastLessons.length > 0 ? (
                <div className="space-y-2">
                  {pastLessons.slice(0, 10).map((lesson) => (
                    <Card
                      key={lesson.id}
                      className="p-4 hover:shadow-md transition-all opacity-70"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 mb-1">
                            {lesson.subject || "授業"}
                          </h3>
                          {lesson.student && (
                            <p className="text-sm text-gray-600 mb-2">
                              {getStudentName(lesson.student)}{getStudentGrade(lesson.student) ? `（${getStudentGrade(lesson.student)}）` : ""}
                            </p>
                          )}
                          <div className="flex items-center gap-4 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                              <Calendar className="w-4 h-4" />
                              {format(
                                getLessonDateTime(lesson),
                                "yyyy年M月d日（E）HH:mm",
                                { locale: ja }
                              )}
                            </div>
                            {lesson.duration_minutes && (
                              <div className="flex items-center gap-1">
                                <Clock className="w-4 h-4" />
                                {lesson.duration_minutes}分
                              </div>
                            )}
                          </div>
                          {lesson.staff && (
                            <p className="text-xs text-gray-500 mt-2">
                              講師：{lesson.staff.name}
                            </p>
                          )}
                        </div>
                        <Badge variant="secondary">完了</Badge>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 text-center py-8">
                  過去の授業はありません
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </ThreePaneLayout>
  );
}
