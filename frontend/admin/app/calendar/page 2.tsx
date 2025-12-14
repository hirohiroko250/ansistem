"use client";

import { useState, useEffect } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ChevronLeft,
  ChevronRight,
  Users,
  Clock,
  MapPin,
  Loader2,
  UserCheck,
  UserX,
  Phone,
} from "lucide-react";
import {
  getBrands,
  getCampuses,
  getCalendar,
  getCalendarEventDetail,
  Brand,
  CalendarDay,
  CalendarEvent,
  CalendarEventDetail,
} from "@/lib/api/staff";
import type { School } from "@/lib/api/types";

export default function CalendarPage() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [selectedSchool, setSelectedSchool] = useState<string>("");
  const [selectedBrand, setSelectedBrand] = useState<string>("all");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [calendarDays, setCalendarDays] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<{
    event: CalendarEvent;
    date: string;
  } | null>(null);
  const [eventDetail, setEventDetail] = useState<CalendarEventDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(true);

  // 会社名（固定値として設定、必要に応じてAPIから取得）
  const companyName = "アンイングループ";

  // 初期データ読み込み
  useEffect(() => {
    async function loadInitialData() {
      setDataLoading(true);
      try {
        const [brandsData, schoolsData] = await Promise.all([
          getBrands(),
          getCampuses(),
        ]);
        console.log("Brands loaded:", brandsData.length, brandsData);
        console.log("Schools loaded:", schoolsData.length, schoolsData);
        setBrands(brandsData);
        setSchools(schoolsData);
        if (schoolsData.length > 0) {
          setSelectedSchool(schoolsData[0].id);
        }
      } catch (error) {
        console.error("Error loading initial data:", error);
      } finally {
        setDataLoading(false);
      }
    }
    loadInitialData();
  }, []);

  // カレンダーデータ読み込み
  useEffect(() => {
    async function loadCalendar() {
      if (!selectedSchool) return;
      setLoading(true);
      const data = await getCalendar({
        schoolId: selectedSchool,
        year: currentDate.getFullYear(),
        month: currentDate.getMonth() + 1,
        brandId: selectedBrand !== "all" ? selectedBrand : undefined,
      });
      if (data) {
        setCalendarDays(data.days);
      }
      setLoading(false);
    }
    loadCalendar();
  }, [selectedSchool, selectedBrand, currentDate]);

  // イベント詳細読み込み
  useEffect(() => {
    async function loadEventDetail() {
      if (!selectedEvent) {
        setEventDetail(null);
        return;
      }
      setDetailLoading(true);
      const detail = await getCalendarEventDetail({
        scheduleId: selectedEvent.event.id,
        date: selectedEvent.date,
      });
      setEventDetail(detail);
      setDetailLoading(false);
    }
    loadEventDetail();
  }, [selectedEvent]);

  // 月移動
  function prevMonth() {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  }
  function nextMonth() {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  }
  function goToToday() {
    setCurrentDate(new Date());
  }

  // 曜日ヘッダー
  const weekDays = ["日", "月", "火", "水", "木", "金", "土"];

  // カレンダーグリッド生成
  function getCalendarGrid() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const grid: (CalendarDay | null)[] = [];

    // 前月の空白
    for (let i = 0; i < firstDay; i++) {
      grid.push(null);
    }

    // 当月の日付
    for (let day = 1; day <= daysInMonth; day++) {
      const dayData = calendarDays.find((d) => d.day === day);
      grid.push(dayData || null);
    }

    return grid;
  }

  const calendarGrid = getCalendarGrid();

  // レッスンタイプの色
  function getLessonTypeColor(lessonType: string): string {
    switch (lessonType) {
      case "A":
        return "bg-blue-500";
      case "B":
        return "bg-orange-500";
      case "P":
        return "bg-purple-500";
      case "Y":
        return "bg-green-500";
      default:
        return "bg-gray-500";
    }
  }

  return (
    <ThreePaneLayout>
      <div className="flex flex-col h-full">
        {/* ヘッダー */}
        <div className="p-3 border-b bg-white">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={prevMonth}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <h2 className="text-lg font-bold min-w-[120px] text-center">
                {currentDate.getFullYear()}年{currentDate.getMonth() + 1}月
              </h2>
              <Button variant="outline" size="sm" onClick={nextMonth}>
                <ChevronRight className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={goToToday}>
                今日
              </Button>
            </div>
            <div className="flex items-center gap-2">
              {/* 会社名 */}
              <div className="px-3 py-1 bg-blue-50 border border-blue-200 rounded text-sm font-medium text-blue-800">
                {companyName}
              </div>
              <Select value={selectedSchool} onValueChange={setSelectedSchool} disabled={dataLoading}>
                <SelectTrigger className="w-[150px] h-8 text-xs">
                  <SelectValue placeholder={dataLoading ? "読込中..." : "校舎選択"} />
                </SelectTrigger>
                <SelectContent>
                  {schools.map((school) => (
                    <SelectItem key={school.id} value={school.id}>
                      {school.schoolName || school.school_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={selectedBrand} onValueChange={setSelectedBrand} disabled={dataLoading}>
                <SelectTrigger className="w-[120px] h-8 text-xs">
                  <SelectValue placeholder={dataLoading ? "読込中..." : "ブランド"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全ブランド</SelectItem>
                  {brands.map((brand) => (
                    <SelectItem key={brand.id} value={brand.id}>
                      {brand.brandName || brand.brand_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          {/* 凡例 */}
          <div className="flex items-center gap-3 text-xs text-gray-600">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-500" />A: 外国人あり
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-orange-500" />B: 日本人のみ
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-500" />P: ペア
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500" />Y: インター
            </span>
          </div>
        </div>

        {/* カレンダーグリッド */}
        <div className="flex-1 overflow-auto p-2">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          ) : (
            <div className="grid grid-cols-7 gap-px bg-gray-200 rounded overflow-hidden">
              {/* 曜日ヘッダー */}
              {weekDays.map((day, i) => (
                <div
                  key={day}
                  className={`p-1 text-center text-xs font-medium bg-gray-100 ${
                    i === 0 ? "text-red-500" : i === 6 ? "text-blue-500" : "text-gray-700"
                  }`}
                >
                  {day}
                </div>
              ))}

              {/* 日付セル */}
              {calendarGrid.map((dayData, index) => {
                const dayOfWeek = index % 7;
                const isToday =
                  dayData &&
                  new Date().toDateString() ===
                    new Date(currentDate.getFullYear(), currentDate.getMonth(), dayData.day).toDateString();

                return (
                  <div
                    key={index}
                    className={`min-h-[100px] bg-white p-1 ${
                      dayData?.isClosed ? "bg-gray-50" : ""
                    } ${isToday ? "ring-2 ring-blue-400 ring-inset" : ""}`}
                  >
                    {dayData ? (
                      <>
                        <div className="flex items-center justify-between mb-1">
                          <span
                            className={`text-xs font-medium ${
                              dayOfWeek === 0
                                ? "text-red-500"
                                : dayOfWeek === 6
                                ? "text-blue-500"
                                : "text-gray-700"
                            }`}
                          >
                            {dayData.day}
                          </span>
                          {dayData.isClosed && (
                            <Badge variant="secondary" className="text-[9px] px-1 py-0">
                              休
                            </Badge>
                          )}
                        </div>

                        {/* イベント一覧 */}
                        <div className="space-y-0.5 max-h-[80px] overflow-y-auto">
                          {dayData.events.slice(0, 5).map((event) => (
                            <button
                              key={event.id}
                              onClick={() =>
                                setSelectedEvent({ event, date: dayData.date })
                              }
                              className="w-full text-left p-0.5 rounded text-[10px] hover:opacity-80 transition-opacity truncate flex items-center gap-0.5"
                              style={{
                                backgroundColor: event.brandColor
                                  ? `${event.brandColor}20`
                                  : "#f3f4f6",
                                borderLeft: `2px solid ${event.brandColor || "#9ca3af"}`,
                              }}
                            >
                              <span
                                className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${getLessonTypeColor(
                                  event.lessonType
                                )}`}
                              />
                              <span className="truncate">{event.startTime}</span>
                              <span className="truncate flex-1">{event.className}</span>
                              <span className="text-gray-500 flex-shrink-0">
                                {event.enrolledCount}/{event.capacity}
                              </span>
                            </button>
                          ))}
                          {dayData.events.length > 5 && (
                            <div className="text-[9px] text-gray-500 text-center">
                              +{dayData.events.length - 5}件
                            </div>
                          )}
                        </div>
                      </>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* イベント詳細ダイアログ */}
      <Dialog
        open={!!selectedEvent}
        onOpenChange={(open) => !open && setSelectedEvent(null)}
      >
        <DialogContent className="max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>
                {selectedEvent?.event.className} - {selectedEvent?.date}
              </span>
              {selectedEvent && (
                <Badge className={getLessonTypeColor(selectedEvent.event.lessonType)}>
                  {selectedEvent.event.lessonTypeLabel}
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          {detailLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : eventDetail ? (
            <div className="flex-1 overflow-auto space-y-4">
              {/* スケジュール情報 */}
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <span>
                    {eventDetail.schedule.startTime} - {eventDetail.schedule.endTime}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-gray-400" />
                  <span>{eventDetail.schedule.roomName || "未設定"}</span>
                </div>
              </div>

              {/* サマリー */}
              <div className="grid grid-cols-4 gap-2">
                <Card className="p-2 text-center">
                  <div className="text-lg font-bold text-blue-600">
                    {eventDetail.summary.totalEnrolled}
                  </div>
                  <div className="text-[10px] text-gray-500">登録</div>
                </Card>
                <Card className="p-2 text-center">
                  <div className="text-lg font-bold text-green-600">
                    {eventDetail.summary.presentCount}
                  </div>
                  <div className="text-[10px] text-gray-500">出席</div>
                </Card>
                <Card className="p-2 text-center">
                  <div className="text-lg font-bold text-red-600">
                    {eventDetail.summary.absentCount}
                  </div>
                  <div className="text-[10px] text-gray-500">欠席</div>
                </Card>
                <Card className="p-2 text-center">
                  <div className="text-lg font-bold text-gray-600">
                    {eventDetail.summary.unknownCount}
                  </div>
                  <div className="text-[10px] text-gray-500">未確認</div>
                </Card>
              </div>

              {/* 生徒一覧 */}
              <div>
                <h4 className="text-sm font-medium mb-2 flex items-center gap-1">
                  <Users className="w-4 h-4" />
                  受講者一覧 ({eventDetail.students.length}名)
                </h4>
                <div className="space-y-1 max-h-[300px] overflow-auto">
                  {eventDetail.students.length > 0 ? (
                    eventDetail.students.map((student) => (
                      <div
                        key={student.id}
                        className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm"
                      >
                        <div className="flex items-center gap-2">
                          {student.attendanceStatus === "present" ? (
                            <UserCheck className="w-4 h-4 text-green-500" />
                          ) : student.attendanceStatus === "absent" ? (
                            <UserX className="w-4 h-4 text-red-500" />
                          ) : (
                            <Users className="w-4 h-4 text-gray-400" />
                          )}
                          <div>
                            <div className="font-medium">{student.name}</div>
                            <div className="text-[10px] text-gray-500">
                              {student.studentNo} | {student.grade}
                            </div>
                          </div>
                        </div>
                        <div className="text-right text-[10px] text-gray-500">
                          {student.guardianName && (
                            <div>{student.guardianName}</div>
                          )}
                          {student.guardianPhone && (
                            <div className="flex items-center gap-1">
                              <Phone className="w-3 h-3" />
                              {student.guardianPhone}
                            </div>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-4 text-gray-500 text-sm">
                      登録されている生徒がいません
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </ThreePaneLayout>
  );
}
