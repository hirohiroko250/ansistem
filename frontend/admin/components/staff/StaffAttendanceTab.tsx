"use client";

import { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
} from "lucide-react";
import apiClient from "@/lib/api/client";

interface HRAttendance {
  id: string;
  date: string;
  clockInTime?: string;
  clockOutTime?: string;
  breakMinutes: number;
  workMinutes: number;
  overtimeMinutes: number;
  status: string;
  school?: { id: string; name: string };
  dailyReport?: string;
  notes?: string;
}

interface AttendanceSummary {
  totalWorkDays: number;
  totalWorkMinutes: number;
  totalOvertimeMinutes: number;
  totalBreakMinutes: number;
  absentDays: number;
  leaveDays: number;
  averageWorkMinutes: number;
}

interface StaffAttendanceTabProps {
  staffId: string;
  userId?: string;
}

const statusConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  working: { label: "勤務中", color: "bg-green-100 text-green-800", icon: <Clock className="w-4 h-4" /> },
  completed: { label: "退勤済", color: "bg-blue-100 text-blue-800", icon: <CheckCircle className="w-4 h-4" /> },
  absent: { label: "欠勤", color: "bg-red-100 text-red-800", icon: <XCircle className="w-4 h-4" /> },
  leave: { label: "休暇", color: "bg-purple-100 text-purple-800", icon: <AlertCircle className="w-4 h-4" /> },
  holiday: { label: "休日", color: "bg-gray-100 text-gray-800", icon: null },
};

function formatMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}時間${m > 0 ? `${m}分` : ""}`;
}

function formatTime(isoString?: string): string {
  if (!isoString) return "-";
  const date = new Date(isoString);
  return date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
}

export function StaffAttendanceTab({ staffId, userId }: StaffAttendanceTabProps) {
  const [attendances, setAttendances] = useState<HRAttendance[]>([]);
  const [summary, setSummary] = useState<AttendanceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1);
  const [viewMode, setViewMode] = useState<"list" | "calendar">("calendar");

  useEffect(() => {
    loadAttendance();
  }, [staffId, userId, currentYear, currentMonth]);

  async function loadAttendance() {
    setLoading(true);
    try {
      // 勤怠データを取得（userIdがある場合はそれを使用）
      const startDate = `${currentYear}-${String(currentMonth).padStart(2, "0")}-01`;
      const lastDay = new Date(currentYear, currentMonth, 0).getDate();
      const endDate = `${currentYear}-${String(currentMonth).padStart(2, "0")}-${lastDay}`;

      const response = await apiClient.get<{ results?: HRAttendance[] } | HRAttendance[]>(
        `/hr/attendances/?start_date=${startDate}&end_date=${endDate}`
      );
      if (Array.isArray(response)) {
        setAttendances(response);
      } else {
        setAttendances(response.results || []);
      }

      // サマリーを取得
      const summaryResponse = await apiClient.get<AttendanceSummary>(
        `/hr/attendances/summary/?year=${currentYear}&month=${currentMonth}`
      );
      setSummary(summaryResponse);
    } catch (err) {
      console.error("Failed to load attendance:", err);
    }
    setLoading(false);
  }

  function handlePrevMonth() {
    if (currentMonth === 1) {
      setCurrentYear(currentYear - 1);
      setCurrentMonth(12);
    } else {
      setCurrentMonth(currentMonth - 1);
    }
  }

  function handleNextMonth() {
    if (currentMonth === 12) {
      setCurrentYear(currentYear + 1);
      setCurrentMonth(1);
    } else {
      setCurrentMonth(currentMonth + 1);
    }
  }

  // カレンダー表示用データ
  const calendarData = useMemo(() => {
    const firstDay = new Date(currentYear, currentMonth - 1, 1);
    const lastDay = new Date(currentYear, currentMonth, 0);
    const days = [];

    // 月初の空白
    for (let i = 0; i < firstDay.getDay(); i++) {
      days.push({ date: null, attendance: null });
    }

    // 日付
    for (let d = 1; d <= lastDay.getDate(); d++) {
      const dateStr = `${currentYear}-${String(currentMonth).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const attendance = attendances.find((a) => a.date === dateStr);
      days.push({ date: d, dateStr, attendance });
    }

    return days;
  }, [currentYear, currentMonth, attendances]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handlePrevMonth}>
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <span className="font-semibold min-w-[120px] text-center">
            {currentYear}年{currentMonth}月
          </span>
          <Button variant="outline" size="sm" onClick={handleNextMonth}>
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
        <Select value={viewMode} onValueChange={(v: "list" | "calendar") => setViewMode(v)}>
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="calendar">カレンダー</SelectItem>
            <SelectItem value="list">リスト</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* サマリー */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-blue-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-blue-600">{summary.totalWorkDays}</div>
            <div className="text-xs text-blue-600">出勤日数</div>
          </div>
          <div className="bg-green-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-green-600">
              {formatMinutes(summary.totalWorkMinutes)}
            </div>
            <div className="text-xs text-green-600">総勤務時間</div>
          </div>
          <div className="bg-orange-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-orange-600">
              {formatMinutes(summary.totalOvertimeMinutes)}
            </div>
            <div className="text-xs text-orange-600">残業時間</div>
          </div>
          <div className="bg-purple-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-purple-600">{summary.leaveDays}</div>
            <div className="text-xs text-purple-600">休暇日数</div>
          </div>
        </div>
      )}

      {/* カレンダー表示 */}
      {viewMode === "calendar" && (
        <div className="border rounded-lg p-4">
          <div className="grid grid-cols-7 gap-1">
            {["日", "月", "火", "水", "木", "金", "土"].map((day, i) => (
              <div
                key={day}
                className={`text-center text-sm font-medium py-2 ${
                  i === 0 ? "text-red-500" : i === 6 ? "text-blue-500" : "text-gray-500"
                }`}
              >
                {day}
              </div>
            ))}
            {calendarData.map((day, index) => {
              if (day.date === null) {
                return <div key={`empty-${index}`} className="h-20" />;
              }

              const isToday =
                day.dateStr === new Date().toISOString().split("T")[0];
              const att = day.attendance;
              const config = att ? statusConfig[att.status] : null;

              return (
                <div
                  key={day.date}
                  className={`h-20 p-1 border rounded text-sm ${
                    isToday ? "bg-blue-50 border-blue-300" : ""
                  }`}
                >
                  <div
                    className={`font-medium ${
                      new Date(currentYear, currentMonth - 1, day.date).getDay() === 0
                        ? "text-red-500"
                        : new Date(currentYear, currentMonth - 1, day.date).getDay() === 6
                        ? "text-blue-500"
                        : ""
                    }`}
                  >
                    {day.date}
                  </div>
                  {att && config && (
                    <div className="mt-1">
                      <Badge className={`${config.color} text-[10px] px-1`}>
                        {config.label}
                      </Badge>
                      {att.clockInTime && (
                        <div className="text-[10px] text-gray-500 mt-0.5">
                          {formatTime(att.clockInTime)}〜{formatTime(att.clockOutTime)}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* リスト表示 */}
      {viewMode === "list" && (
        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24">日付</TableHead>
                <TableHead className="w-20">ステータス</TableHead>
                <TableHead>出勤</TableHead>
                <TableHead>退勤</TableHead>
                <TableHead>勤務時間</TableHead>
                <TableHead>残業</TableHead>
                <TableHead>校舎</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {attendances.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-gray-500 py-8">
                    勤怠データがありません
                  </TableCell>
                </TableRow>
              ) : (
                attendances.map((att) => {
                  const config = statusConfig[att.status];
                  return (
                    <TableRow key={att.id}>
                      <TableCell className="font-medium">
                        {new Date(att.date).toLocaleDateString("ja-JP", {
                          month: "short",
                          day: "numeric",
                          weekday: "short",
                        })}
                      </TableCell>
                      <TableCell>
                        <Badge className={config?.color}>
                          {config?.icon}
                          <span className="ml-1">{config?.label}</span>
                        </Badge>
                      </TableCell>
                      <TableCell>{formatTime(att.clockInTime)}</TableCell>
                      <TableCell>{formatTime(att.clockOutTime)}</TableCell>
                      <TableCell>
                        {att.workMinutes > 0 ? formatMinutes(att.workMinutes) : "-"}
                      </TableCell>
                      <TableCell>
                        {att.overtimeMinutes > 0 ? (
                          <span className="text-orange-600">
                            {formatMinutes(att.overtimeMinutes)}
                          </span>
                        ) : (
                          "-"
                        )}
                      </TableCell>
                      <TableCell>{att.school?.name || "-"}</TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* 凡例 */}
      <div className="flex items-center gap-4 text-sm">
        <span className="text-gray-500">ステータス:</span>
        {Object.entries(statusConfig).map(([key, config]) => (
          <Badge key={key} className={config.color}>
            {config.icon}
            <span className="ml-1">{config.label}</span>
          </Badge>
        ))}
      </div>
    </div>
  );
}
