"use client";

import { useState, useEffect, useMemo } from "react";
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
  Calendar as CalendarIcon,
  LayoutGrid,
  List,
  PanelLeftClose,
  PanelLeft,
  LayoutDashboard,
  CheckSquare,
  UserCircle,
  BookOpen,
  FileText,
  MessageSquare,
  Settings,
  Menu,
  ArrowLeftRight,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  getBrands,
  getCampuses,
  getCalendar,
  getCalendarEventDetail,
  performABSwap,
  createClosure,
  exportCalendarCSV,
  importCalendarCSV,
  markAttendance,
  getTenants,
  Brand,
  Tenant,
  CalendarDay,
  CalendarEvent,
  CalendarEventDetail,
} from "@/lib/api/staff";
import CalendarAgent from "@/components/calendar-agent";
import type { School } from "@/lib/api/types";
import {
  getGoogleCalendarEventsForMonth,
  getGoogleCalendarEventsForWeek,
  getGoogleCalendars,
  GoogleCalendarEvent,
  GoogleCalendar,
} from "@/lib/api/google-calendar";

type ViewMode = "month" | "week";

// ナビゲーションメニュー
const menuItems = [
  { name: "ダッシュボード", href: "/dashboard", icon: LayoutDashboard },
  { name: "カレンダー", href: "/calendar", icon: CalendarIcon },
  { name: "タスク", href: "/tasks", icon: CheckSquare },
  { name: "生徒", href: "/students", icon: Users },
  { name: "保護者", href: "/parents", icon: UserCircle },
  { name: "授業", href: "/lessons", icon: BookOpen },
  { name: "契約", href: "/contracts", icon: FileText },
  { name: "メッセージ", href: "/messages", icon: MessageSquare },
  { name: "設定", href: "/settings", icon: Settings },
];

export default function CalendarPage() {
  const pathname = usePathname();
  const [brands, setBrands] = useState<Brand[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
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
  const [viewMode, setViewMode] = useState<ViewMode>("month");
  const [googleEvents, setGoogleEvents] = useState<GoogleCalendarEvent[]>([]);
  const [googleCalendars, setGoogleCalendars] = useState<GoogleCalendar[]>([]);
  const [selectedGoogleCalendar, setSelectedGoogleCalendar] = useState<string>("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<string>("all");
  const [swapLoading, setSwapLoading] = useState(false);
  const [clickedDate, setClickedDate] = useState<string | null>(null);

  // ABスワップモード
  const [abSwapMode, setAbSwapMode] = useState(false);
  const [selectedSwapEvents, setSelectedSwapEvents] = useState<
    Array<{ event: CalendarEvent; date: string; calendarPattern?: string }>
  >([]);


  // 時間スロット（週表示用）
  const timeSlots = useMemo(() => {
    const slots = [];
    for (let hour = 9; hour <= 21; hour++) {
      slots.push(`${hour}:00`);
    }
    return slots;
  }, []);

  // 初期データ読み込み
  useEffect(() => {
    async function loadInitialData() {
      setDataLoading(true);
      try {
        const [brandsData, schoolsData, calendarsData, tenantsData] = await Promise.all([
          getBrands(),
          getCampuses(),
          getGoogleCalendars(),
          getTenants(),
        ]);
        setBrands(brandsData);
        setSchools(schoolsData);
        setGoogleCalendars(calendarsData);
        setTenants(tenantsData);
        if (schoolsData.length > 0) {
          setSelectedSchool(schoolsData[0].id);
        }
        const primaryCalendar = calendarsData.find((c) => c.primary);
        if (primaryCalendar) {
          setSelectedGoogleCalendar(primaryCalendar.id);
        } else if (calendarsData.length > 0) {
          setSelectedGoogleCalendar(calendarsData[0].id);
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

  // 週の開始日を計算
  const weekStartDate = useMemo(() => {
    const startOfWeek = new Date(currentDate);
    const day = startOfWeek.getDay();
    startOfWeek.setDate(startOfWeek.getDate() - day);
    return startOfWeek;
  }, [currentDate]);

  // Google Calendar イベント読み込み
  useEffect(() => {
    async function loadGoogleEvents() {
      if (!selectedGoogleCalendar) return;

      try {
        if (viewMode === "month") {
          const events = await getGoogleCalendarEventsForMonth(
            selectedGoogleCalendar,
            currentDate.getFullYear(),
            currentDate.getMonth() + 1
          );
          setGoogleEvents(events);
        } else {
          const events = await getGoogleCalendarEventsForWeek(
            selectedGoogleCalendar,
            weekStartDate
          );
          setGoogleEvents(events);
        }
      } catch (error) {
        console.error("Error loading Google Calendar events:", error);
      }
    }
    loadGoogleEvents();
  }, [selectedGoogleCalendar, currentDate, viewMode, weekStartDate]);

  // 日付ごとのGoogleイベントを取得
  function getGoogleEventsForDate(date: Date): GoogleCalendarEvent[] {
    const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    return googleEvents.filter((event) => {
      if (event.isAllDay) {
        return event.startTime === dateStr;
      } else {
        return event.startTime?.startsWith(dateStr);
      }
    });
  }

  // 終日イベントを取得
  function getAllDayEventsForDate(date: Date): GoogleCalendarEvent[] {
    return getGoogleEventsForDate(date).filter((e) => e.isAllDay);
  }

  // 時刻付きGoogleイベントを取得
  function getTimedGoogleEventsForDate(date: Date): GoogleCalendarEvent[] {
    return getGoogleEventsForDate(date).filter((e) => !e.isAllDay);
  }

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

  // ナビゲーション
  function navigate(direction: "prev" | "next") {
    if (viewMode === "month") {
      setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + (direction === "next" ? 1 : -1), 1));
    } else {
      const days = direction === "next" ? 7 : -7;
      const newDate = new Date(currentDate);
      newDate.setDate(newDate.getDate() + days);
      setCurrentDate(newDate);
    }
  }

  function goToToday() {
    setCurrentDate(new Date());
  }

  // 曜日ヘッダー
  const weekDays = ["日", "月", "火", "水", "木", "金", "土"];

  // 現在の週の日付を取得
  function getWeekDates() {
    const startOfWeek = new Date(currentDate);
    const day = startOfWeek.getDay();
    startOfWeek.setDate(startOfWeek.getDate() - day);

    const dates = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek);
      date.setDate(startOfWeek.getDate() + i);
      dates.push(date);
    }
    return dates;
  }

  const weekDates = useMemo(() => getWeekDates(), [currentDate]);

  // 月表示用カレンダーグリッド生成
  function getCalendarGrid() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const grid: (CalendarDay | null)[] = [];

    for (let i = 0; i < firstDay; i++) {
      grid.push(null);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const dayData = calendarDays.find((d) => d.day === day);
      grid.push(dayData || null);
    }

    return grid;
  }

  const calendarGrid = getCalendarGrid();

  // 日付に対応するイベントを取得
  function getEventsForDate(date: Date): CalendarEvent[] {
    const dayData = calendarDays.find(d => d.day === date.getDate() &&
      date.getMonth() === currentDate.getMonth());
    return dayData?.events || [];
  }

  // レッスンタイプの色
  function getLessonTypeColor(lessonType: string): string {
    switch (lessonType) {
      case "A": return "bg-blue-500";
      case "B": return "bg-orange-500";
      case "P": return "bg-purple-500";
      case "Y": return "bg-green-500";
      default: return "bg-gray-500";
    }
  }

  // 日付フォーマット
  function formatDateRange() {
    if (viewMode === "month") {
      return `${currentDate.getFullYear()}年${currentDate.getMonth() + 1}月`;
    } else {
      const start = weekDates[0];
      const end = weekDates[6];
      if (start.getMonth() === end.getMonth()) {
        return `${start.getFullYear()}年${start.getMonth() + 1}月${start.getDate()}日〜${end.getDate()}日`;
      }
      return `${start.getMonth() + 1}/${start.getDate()} 〜 ${end.getMonth() + 1}/${end.getDate()}`;
    }
  }

  // ブランドIDから色を取得
  function getBrandColor(brandId: string | null): string {
    if (!brandId) return "#9ca3af";
    const brand = brands.find((b) => b.id === brandId);
    return brand?.colorPrimary || brand?.brand_color || "#9ca3af";
  }

  // ABスワップを実行
  async function handleABSwap(newType?: "A" | "B" | "P" | "Y") {
    if (!selectedEvent || !eventDetail?.schedule?.calendarPattern) return;

    setSwapLoading(true);
    try {
      const result = await performABSwap({
        calendarPattern: eventDetail.schedule.calendarPattern,
        date: selectedEvent.date,
        newType,
      });

      if (result?.success) {
        // カレンダーを再読み込み
        const data = await getCalendar({
          schoolId: selectedSchool,
          year: currentDate.getFullYear(),
          month: currentDate.getMonth() + 1,
          brandId: selectedBrand !== "all" ? selectedBrand : undefined,
        });
        if (data) {
          setCalendarDays(data.days);
        }
        // イベント詳細を再読み込み
        const updatedDetail = await getCalendarEventDetail({
          scheduleId: selectedEvent.event.id,
          date: selectedEvent.date,
        });
        setEventDetail(updatedDetail);
      }
    } catch (error) {
      console.error("Error performing AB swap:", error);
    } finally {
      setSwapLoading(false);
    }
  }

  // エージェント用: ABスワップ
  async function handleAgentABSwap(params: { calendarPattern: string; date: string; newType?: string }): Promise<boolean> {
    try {
      const result = await performABSwap({
        calendarPattern: params.calendarPattern,
        date: params.date,
        newType: params.newType as "A" | "B" | "P" | "Y" | undefined,
      });

      if (result?.success) {
        // カレンダーを再読み込み
        const data = await getCalendar({
          schoolId: selectedSchool,
          year: currentDate.getFullYear(),
          month: currentDate.getMonth() + 1,
          brandId: selectedBrand !== "all" ? selectedBrand : undefined,
        });
        if (data) {
          setCalendarDays(data.days);
        }
        return true;
      }
      return false;
    } catch (error) {
      console.error("Error in agent AB swap:", error);
      return false;
    }
  }

  // エージェント用: 休校設定
  async function handleAgentSetClosure(params: { schoolId: string; date: string; reason?: string }): Promise<boolean> {
    try {
      const result = await createClosure({
        schoolId: params.schoolId,
        closureDate: params.date,
        closureType: "school_closed",
        reason: params.reason,
      });

      if (result) {
        // カレンダーを再読み込み
        const data = await getCalendar({
          schoolId: selectedSchool,
          year: currentDate.getFullYear(),
          month: currentDate.getMonth() + 1,
          brandId: selectedBrand !== "all" ? selectedBrand : undefined,
        });
        if (data) {
          setCalendarDays(data.days);
        }
        return true;
      }
      return false;
    } catch (error) {
      console.error("Error in agent set closure:", error);
      return false;
    }
  }

  // エージェント用: CSVエクスポート（出席情報）
  async function handleAgentExportCSV(params: {
    brandId?: string;
    schoolId?: string;
    startDate: string;
    endDate: string;
  }): Promise<string | null> {
    try {
      const url = await exportCalendarCSV({
        schoolId: params.schoolId || selectedSchool,
        year: currentDate.getFullYear(),
        month: currentDate.getMonth() + 1,
        brandId: params.brandId || (selectedBrand !== "all" ? selectedBrand : undefined),
      });
      return url;
    } catch (error) {
      console.error("Error in agent export CSV:", error);
      return null;
    }
  }

  // エージェント用: CSVインポート
  async function handleAgentImportCSV(file: File): Promise<boolean> {
    try {
      const result = await importCalendarCSV(file);

      if (result.success) {
        // カレンダーを再読み込み
        const data = await getCalendar({
          schoolId: selectedSchool,
          year: currentDate.getFullYear(),
          month: currentDate.getMonth() + 1,
          brandId: selectedBrand !== "all" ? selectedBrand : undefined,
        });
        if (data) {
          setCalendarDays(data.days);
        }
        return true;
      }
      return false;
    } catch (error) {
      console.error("Error in agent import CSV:", error);
      return false;
    }
  }

  // ABスワップモード開始
  function startABSwapMode() {
    setAbSwapMode(true);
    setSelectedSwapEvents([]);
    setSelectedEvent(null); // 詳細ダイアログを閉じる
  }

  // ABスワップモード終了
  function cancelABSwapMode() {
    setAbSwapMode(false);
    setSelectedSwapEvents([]);
  }

  // イベント選択/解除（ABスワップモード中）
  function toggleSwapEventSelection(event: CalendarEvent, date: string) {
    setSelectedSwapEvents((prev) => {
      const exists = prev.find(
        (e) => e.event.id === event.id && e.date === date
      );
      if (exists) {
        // 解除
        return prev.filter(
          (e) => !(e.event.id === event.id && e.date === date)
        );
      } else {
        // 追加
        return [
          ...prev,
          {
            event,
            date,
            calendarPattern: event.calendarPattern || undefined,
          },
        ];
      }
    });
  }

  // 選択したイベントが選択されているかチェック
  function isEventSelectedForSwap(eventId: string, date: string): boolean {
    return selectedSwapEvents.some(
      (e) => e.event.id === eventId && e.date === date
    );
  }

  // 日付の全イベントを選択/解除
  function toggleDateSelection(date: string, events: CalendarEvent[]) {
    const dateEvents = events.filter((e) => e.calendarPattern); // スワップ可能なイベントのみ
    if (dateEvents.length === 0) return;

    // この日付の全イベントが選択されているかチェック
    const allSelected = dateEvents.every((e) =>
      selectedSwapEvents.some((se) => se.event.id === e.id && se.date === date)
    );

    if (allSelected) {
      // 全解除
      setSelectedSwapEvents((prev) =>
        prev.filter((e) => e.date !== date)
      );
    } else {
      // 全選択（既存の他の日付は保持）
      setSelectedSwapEvents((prev) => {
        // この日付の既存選択を削除
        const otherDates = prev.filter((e) => e.date !== date);
        // この日付の全イベントを追加
        const newEvents = dateEvents.map((event) => ({
          event,
          date,
          calendarPattern: event.calendarPattern || undefined,
        }));
        return [...otherDates, ...newEvents];
      });
    }
  }

  // 日付の選択状態をチェック（全選択/一部選択/未選択）
  function getDateSelectionState(date: string, events: CalendarEvent[]): "all" | "some" | "none" {
    const dateEvents = events.filter((e) => e.calendarPattern);
    if (dateEvents.length === 0) return "none";

    const selectedCount = dateEvents.filter((e) =>
      selectedSwapEvents.some((se) => se.event.id === e.id && se.date === date)
    ).length;

    if (selectedCount === 0) return "none";
    if (selectedCount === dateEvents.length) return "all";
    return "some";
  }

  // ABスワップを実行
  async function executeABSwap() {
    if (selectedSwapEvents.length === 0) return;

    setSwapLoading(true);
    try {
      // 選択された全てのイベントをスワップ
      const results = await Promise.all(
        selectedSwapEvents.map((item) =>
          item.calendarPattern
            ? performABSwap({
                calendarPattern: item.calendarPattern,
                date: item.date,
              })
            : Promise.resolve(null)
        )
      );

      const successCount = results.filter((r) => r?.success).length;

      // カレンダーを再読み込み
      const data = await getCalendar({
        schoolId: selectedSchool,
        year: currentDate.getFullYear(),
        month: currentDate.getMonth() + 1,
        brandId: selectedBrand !== "all" ? selectedBrand : undefined,
      });
      if (data) {
        setCalendarDays(data.days);
      }

      // モード終了
      setAbSwapMode(false);
      setSelectedSwapEvents([]);

      console.log(`AB swap completed: ${successCount}/${selectedSwapEvents.length} events`);
    } catch (error) {
      console.error("Error executing AB swap:", error);
    } finally {
      setSwapLoading(false);
    }
  }

  // 出欠記録
  async function handleMarkAttendance(studentId: string, status: "present" | "absent") {
    if (!selectedEvent || !eventDetail) return;

    try {
      // Backend APIを呼び出し（AbsenceTicketを作成/削除）
      const result = await markAttendance({
        studentId,
        scheduleId: selectedEvent.event.id,
        date: selectedEvent.date,
        status
      });

      if (result?.success) {
        // ローカルで即時反映
        setEventDetail((prev) => {
          if (!prev) return prev;
          const currentStudent = prev.students.find((s) => s.id === studentId);
          const prevStatus = currentStudent?.attendanceStatus;

          return {
            ...prev,
            students: prev.students.map((s) =>
              s.id === studentId ? { ...s, attendanceStatus: status } : s
            ),
            summary: {
              ...prev.summary,
              presentCount:
                status === "present"
                  ? (prevStatus !== "present" ? prev.summary.presentCount + 1 : prev.summary.presentCount)
                  : (prevStatus === "present" ? prev.summary.presentCount - 1 : prev.summary.presentCount),
              absentCount:
                status === "absent"
                  ? (prevStatus !== "absent" ? prev.summary.absentCount + 1 : prev.summary.absentCount)
                  : (prevStatus === "absent" ? prev.summary.absentCount - 1 : prev.summary.absentCount),
            },
          };
        });
      }
    } catch (error) {
      console.error("Error marking attendance:", error);
    }
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* ナビゲーションサイドバー */}
      <div className={`${sidebarCollapsed ? "w-16" : "w-64"} transition-all duration-300 bg-white border-r flex flex-col`}>
        {/* ロゴ/タイトル */}
        <div className="p-4 border-b flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="h-8 w-8 p-0 flex-shrink-0"
          >
            <Menu className="w-5 h-5" />
          </Button>
          {!sidebarCollapsed && (
            <h1 className="text-lg font-bold text-gray-900 truncate">社員管理画面</h1>
          )}
        </div>

        {/* ナビゲーションメニュー */}
        <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                  isActive
                    ? "bg-blue-100 text-blue-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
                  sidebarCollapsed && "justify-center px-2"
                )}
                title={sidebarCollapsed ? item.name : undefined}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!sidebarCollapsed && <span>{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        {/* 凡例（展開時のみ） */}
        {!sidebarCollapsed && (
          <div className="p-4 border-t bg-gray-50">
            <div className="text-xs font-medium text-gray-700 mb-2">ブランド凡例</div>
            <div className="space-y-1 text-xs max-h-32 overflow-y-auto">
              {brands.slice(0, 6).map((brand) => (
                <div key={brand.id} className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: brand.colorPrimary || brand.brand_color || "#9ca3af" }}
                  />
                  <span className="truncate">{brand.brandName || brand.brand_name}</span>
                </div>
              ))}
            </div>
            <div className="mt-2 pt-2 border-t flex items-center gap-2 text-red-600 text-xs">
              <CalendarIcon className="w-3 h-3" />
              <span>Google Calendar</span>
            </div>
          </div>
        )}
      </div>

      {/* メインコンテンツ */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* ヘッダー */}
        <div className="p-3 border-b bg-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* 表示切替 */}
            <div className="flex bg-gray-100 rounded-lg p-0.5">
              <Button
                variant={viewMode === "month" ? "default" : "ghost"}
                size="sm"
                className="h-7 px-3"
                onClick={() => setViewMode("month")}
              >
                <LayoutGrid className="w-4 h-4 mr-1" />
                月
              </Button>
              <Button
                variant={viewMode === "week" ? "default" : "ghost"}
                size="sm"
                className="h-7 px-3"
                onClick={() => setViewMode("week")}
              >
                <List className="w-4 h-4 mr-1" />
                週
              </Button>
            </div>

            <div className="w-px h-6 bg-gray-300 mx-1" />

            <Button variant="outline" size="sm" onClick={() => navigate("prev")} className="h-8 w-8 p-0">
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <h2 className="text-lg font-bold min-w-[200px] text-center">
              {formatDateRange()}
            </h2>
            <Button variant="outline" size="sm" onClick={() => navigate("next")} className="h-8 w-8 p-0">
              <ChevronRight className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={goToToday} className="h-8">
              今日
            </Button>
          </div>

          <div className="flex items-center gap-2">
            {/* テナント選択 */}
            <Select value={selectedTenant} onValueChange={setSelectedTenant}>
              <SelectTrigger className="w-[180px] h-8 text-xs bg-blue-50 border-blue-200">
                <SelectValue placeholder="テナント選択" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全テナント</SelectItem>
                {tenants.map((tenant) => (
                  <SelectItem key={tenant.id} value={tenant.id}>
                    {tenant.tenant_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={selectedSchool} onValueChange={setSelectedSchool} disabled={dataLoading}>
              <SelectTrigger className="w-[160px] h-8 text-xs">
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
              <SelectTrigger className="w-[140px] h-8 text-xs">
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

        {/* ABスワップモードバー */}
        {abSwapMode && (
          <div className="bg-gradient-to-r from-blue-500 to-purple-500 text-white px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ArrowLeftRight className="w-5 h-5" />
              <div>
                <span className="font-medium">ABスワップモード</span>
                <span className="ml-2 text-sm opacity-90">
                  スワップしたい授業をクリックして選択してください
                </span>
              </div>
              {selectedSwapEvents.length > 0 && (
                <Badge className="bg-white/20 text-white">
                  {selectedSwapEvents.length}件選択中
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={cancelABSwapMode}
                className="text-white hover:bg-white/20"
              >
                キャンセル
              </Button>
              <Button
                size="sm"
                onClick={executeABSwap}
                disabled={selectedSwapEvents.length === 0 || swapLoading}
                className="bg-white text-blue-600 hover:bg-gray-100"
              >
                {swapLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-1" />
                ) : (
                  <RefreshCw className="w-4 h-4 mr-1" />
                )}
                スワップ実行 ({selectedSwapEvents.length}件)
              </Button>
            </div>
          </div>
        )}

        {/* カレンダー本体 */}
        <div className="flex-1 overflow-auto p-3">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          ) : viewMode === "month" ? (
            /* 月表示 */
            <div className="h-full flex flex-col">
              <div className="grid grid-cols-7 gap-px bg-gray-300 rounded-t overflow-hidden">
                {/* 曜日ヘッダー */}
                {weekDays.map((day, i) => (
                  <div
                    key={day}
                    className={`p-2 text-center text-sm font-medium bg-gray-100 ${
                      i === 0 ? "text-red-500" : i === 6 ? "text-blue-500" : "text-gray-700"
                    }`}
                  >
                    {day}
                  </div>
                ))}
              </div>

              {/* 日付セル */}
              <div className="flex-1 grid grid-cols-7 grid-rows-6 gap-px bg-gray-300">
                {calendarGrid.map((dayData, index) => {
                  const dayOfWeek = index % 7;
                  const isToday =
                    dayData &&
                    new Date().toDateString() ===
                      new Date(currentDate.getFullYear(), currentDate.getMonth(), dayData.day).toDateString();

                  // この日のGoogleカレンダーイベント
                  const dayDate = dayData
                    ? new Date(currentDate.getFullYear(), currentDate.getMonth(), dayData.day)
                    : null;
                  const allDayEvents = dayDate ? getAllDayEventsForDate(dayDate) : [];
                  const timedGoogleEvents = dayDate ? getTimedGoogleEventsForDate(dayDate) : [];

                  // ABスワップモード用: 日付の選択状態
                  const dateSelectionState = dayData
                    ? getDateSelectionState(dayData.date, dayData.events)
                    : "none";

                  return (
                    <div
                      key={index}
                      className={cn(
                        "bg-white p-1 flex flex-col min-h-0",
                        dayData?.isClosed && "bg-gray-50",
                        isToday && "ring-2 ring-blue-400 ring-inset",
                        abSwapMode && dateSelectionState === "all" && "bg-blue-50",
                        abSwapMode && dateSelectionState === "some" && "bg-blue-50/50"
                      )}
                    >
                      {dayData ? (
                        <>
                          <div className="flex items-center justify-between mb-1 flex-shrink-0">
                            {/* ABスワップモード時は日付クリックで全選択 */}
                            {abSwapMode ? (
                              <button
                                onClick={() => toggleDateSelection(dayData.date, dayData.events)}
                                className={cn(
                                  "text-sm font-medium w-6 h-6 flex items-center justify-center rounded-full transition-colors",
                                  dateSelectionState === "all" && "bg-blue-500 text-white",
                                  dateSelectionState === "some" && "bg-blue-300 text-white",
                                  dateSelectionState === "none" && "hover:bg-gray-200",
                                  dayOfWeek === 0 && dateSelectionState === "none" && "text-red-500",
                                  dayOfWeek === 6 && dateSelectionState === "none" && "text-blue-500"
                                )}
                                title="この日の全授業を選択/解除"
                              >
                                {dayData.day}
                              </button>
                            ) : (
                              <span
                                className={`text-sm font-medium w-6 h-6 flex items-center justify-center rounded-full ${
                                  isToday ? "bg-blue-500 text-white" : ""
                                } ${
                                !isToday && dayOfWeek === 0
                                  ? "text-red-500"
                                  : !isToday && dayOfWeek === 6
                                  ? "text-blue-500"
                                  : !isToday ? "text-gray-700" : ""
                              }`}
                              >
                                {dayData.day}
                              </span>
                            )}
                            {dayData.isClosed && (
                              <Badge variant="secondary" className="text-[9px] px-1 py-0">
                                休
                              </Badge>
                            )}
                          </div>

                          {/* 終日イベント（Google Calendar） */}
                          {allDayEvents.length > 0 && (
                            <div className="space-y-0.5 mb-1 flex-shrink-0">
                              {allDayEvents.slice(0, 2).map((event) => (
                                <a
                                  key={event.id}
                                  href={event.htmlLink}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="block w-full text-left px-1 py-0.5 rounded text-[10px] bg-red-100 text-red-800 hover:bg-red-200 truncate"
                                >
                                  {event.title}
                                </a>
                              ))}
                              {allDayEvents.length > 2 && (
                                <div className="text-[9px] text-red-500">+{allDayEvents.length - 2}件</div>
                              )}
                            </div>
                          )}

                          {/* 時刻付きイベント一覧 */}
                          <div className="space-y-0.5 overflow-y-auto flex-1 min-h-0">
                            {/* Googleカレンダーの時刻付きイベント */}
                            {timedGoogleEvents.slice(0, 2).map((event) => (
                              <a
                                key={event.id}
                                href={event.htmlLink}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="w-full text-left p-0.5 rounded text-[10px] hover:opacity-80 transition-opacity truncate flex items-center gap-0.5 bg-red-50 border-l-2 border-red-400"
                              >
                                <CalendarIcon className="w-2.5 h-2.5 text-red-500 flex-shrink-0" />
                                <span className="truncate">{event.startTime.slice(11, 16)}</span>
                                <span className="truncate flex-1 text-red-700">{event.title}</span>
                              </a>
                            ))}

                            {/* 授業イベント */}
                            {dayData.events.slice(0, 4).map((event) => {
                              const brandColor = event.brandColor || getBrandColor(event.brandId);
                              const isSelected = isEventSelectedForSwap(event.id, dayData.date);
                              return (
                                <button
                                  key={event.id}
                                  onClick={() => {
                                    if (abSwapMode) {
                                      toggleSwapEventSelection(event, dayData.date);
                                    } else {
                                      setSelectedEvent({ event, date: dayData.date });
                                    }
                                  }}
                                  className={cn(
                                    "w-full text-left p-1 rounded text-[10px] hover:opacity-80 transition-all truncate flex items-center gap-1",
                                    abSwapMode && "cursor-pointer ring-offset-1",
                                    isSelected && "ring-2 ring-blue-500 shadow-md scale-[1.02]"
                                  )}
                                  style={{
                                    backgroundColor: isSelected ? `${brandColor}60` : `${brandColor}30`,
                                    borderLeft: `3px solid ${brandColor}`,
                                  }}
                                >
                                  {abSwapMode && (
                                    <span className={cn(
                                      "w-3 h-3 rounded-full border-2 flex-shrink-0 flex items-center justify-center",
                                      isSelected ? "bg-blue-500 border-blue-500" : "border-gray-400"
                                    )}>
                                      {isSelected && <span className="w-1.5 h-1.5 bg-white rounded-full" />}
                                    </span>
                                  )}
                                  <span className="truncate font-medium" style={{ color: brandColor }}>
                                    {event.startTime}
                                  </span>
                                  <span className="truncate flex-1">{event.className}</span>
                                  {event.lessonType && (
                                    <Badge
                                      variant="outline"
                                      className={cn(
                                        "text-[8px] px-1 py-0 h-3 flex-shrink-0",
                                        event.lessonType === "A" && "bg-red-100 text-red-700 border-red-300",
                                        event.lessonType === "B" && "bg-blue-100 text-blue-700 border-blue-300"
                                      )}
                                    >
                                      {event.lessonType}
                                    </Badge>
                                  )}
                                  <span className="text-gray-500 flex-shrink-0 text-[9px]">
                                    {event.enrolledCount}/{event.capacity}
                                  </span>
                                </button>
                              );
                            })}
                            {(dayData.events.length > 4 || timedGoogleEvents.length > 2) && (
                              <div className="text-[9px] text-gray-500 text-center">
                                +{Math.max(0, dayData.events.length - 4) + Math.max(0, timedGoogleEvents.length - 2)}件
                              </div>
                            )}
                          </div>
                        </>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            /* 週表示 */
            <div className="h-full flex flex-col bg-white rounded overflow-hidden">
              {/* 終日イベントエリア */}
              <div className="flex-shrink-0 border-b">
                <div className="grid grid-cols-8 gap-px bg-gray-200">
                  <div className="bg-gray-50 p-2 text-xs text-gray-500">
                    終日
                  </div>
                  {weekDates.map((date, i) => {
                    const allDayEvents = getAllDayEventsForDate(date);
                    return (
                      <div key={i} className="bg-white p-1 min-h-[40px]">
                        {allDayEvents.slice(0, 2).map((event) => (
                          <a
                            key={event.id}
                            href={event.htmlLink}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block px-1 py-0.5 mb-0.5 rounded text-[10px] bg-red-100 text-red-800 hover:bg-red-200 truncate"
                          >
                            {event.title}
                          </a>
                        ))}
                        {allDayEvents.length > 2 && (
                          <div className="text-[9px] text-red-500">+{allDayEvents.length - 2}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 曜日ヘッダー */}
              <div className="grid grid-cols-8 gap-px bg-gray-200 flex-shrink-0">
                <div className="bg-gray-100 p-2 text-xs font-medium text-gray-500 text-center">
                  時間
                </div>
                {weekDates.map((date, i) => {
                  const isToday = date.toDateString() === new Date().toDateString();
                  const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
                  const eventsOnDate = getEventsForDate(date);
                  const weekDateSelectionState = abSwapMode
                    ? getDateSelectionState(dateStr, eventsOnDate)
                    : "none";

                  return (
                    <div
                      key={i}
                      className={cn(
                        "bg-gray-100 p-2 text-center",
                        isToday && "bg-blue-100",
                        abSwapMode && weekDateSelectionState === "all" && "bg-blue-200",
                        abSwapMode && weekDateSelectionState === "some" && "bg-blue-100"
                      )}
                    >
                      <div className={`text-xs font-medium ${
                        i === 0 ? "text-red-500" : i === 6 ? "text-blue-500" : "text-gray-700"
                      }`}>
                        {weekDays[i]}
                      </div>
                      {/* ABスワップモード時は日付クリックで全選択 */}
                      {abSwapMode ? (
                        <button
                          onClick={() => toggleDateSelection(dateStr, eventsOnDate)}
                          className={cn(
                            "text-xl font-bold w-8 h-8 flex items-center justify-center mx-auto rounded-full transition-colors",
                            weekDateSelectionState === "all" && "bg-blue-500 text-white",
                            weekDateSelectionState === "some" && "bg-blue-300 text-white",
                            weekDateSelectionState === "none" && "hover:bg-gray-200 text-gray-900"
                          )}
                          title="この日の全授業を選択/解除"
                        >
                          {date.getDate()}
                        </button>
                      ) : (
                        <div className={`text-xl font-bold ${
                          isToday ? "text-blue-600 bg-blue-500 text-white rounded-full w-8 h-8 flex items-center justify-center mx-auto" : "text-gray-900"
                        }`}>
                          {date.getDate()}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* 時間グリッド */}
              <div className="flex-1 overflow-auto">
                <div className="grid grid-cols-8 gap-px bg-gray-200">
                  {timeSlots.map((time) => (
                    <>
                      {/* 時間ラベル */}
                      <div key={`time-${time}`} className="bg-gray-50 p-1 text-xs text-gray-500 text-right pr-2 h-20 sticky left-0">
                        {time}
                      </div>
                      {/* 各曜日のセル */}
                      {weekDates.map((date, dayIndex) => {
                        const events = getEventsForDate(date);
                        const hour = parseInt(time.split(":")[0]);
                        const eventsAtTime = events.filter((e) => {
                          const eventHour = parseInt(e.startTime.split(":")[0]);
                          return eventHour === hour;
                        });
                        const googleEventsAtTime = getTimedGoogleEventsForDate(date).filter((e) => {
                          const eventHour = parseInt(e.startTime.slice(11, 13));
                          return eventHour === hour;
                        });

                        return (
                          <div
                            key={`${time}-${dayIndex}`}
                            className="bg-white p-0.5 h-20 overflow-y-auto border-t border-gray-100"
                          >
                            {/* Googleカレンダーイベント */}
                            {googleEventsAtTime.map((event) => (
                              <a
                                key={event.id}
                                href={event.htmlLink}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block w-full text-left p-1 rounded text-[9px] hover:opacity-80 transition-opacity mb-0.5 bg-red-50 border-l-3 border-red-400"
                              >
                                <div className="font-medium truncate text-red-700 flex items-center gap-1">
                                  <CalendarIcon className="w-3 h-3" />
                                  {event.title}
                                </div>
                                <div className="text-red-500">
                                  {event.startTime.slice(11, 16)}
                                </div>
                              </a>
                            ))}
                            {/* 授業イベント */}
                            {eventsAtTime.map((event) => {
                              const brandColor = event.brandColor || getBrandColor(event.brandId);
                              const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
                              const isSelected = isEventSelectedForSwap(event.id, dateStr);
                              return (
                                <button
                                  key={event.id}
                                  onClick={() => {
                                    if (abSwapMode) {
                                      toggleSwapEventSelection(event, dateStr);
                                    } else {
                                      setSelectedEvent({ event, date: dateStr });
                                    }
                                  }}
                                  className={cn(
                                    "w-full text-left p-1 rounded text-[9px] hover:opacity-80 transition-all mb-0.5",
                                    abSwapMode && "cursor-pointer",
                                    isSelected && "ring-2 ring-blue-500 shadow-md scale-[1.02]"
                                  )}
                                  style={{
                                    backgroundColor: isSelected ? `${brandColor}50` : `${brandColor}25`,
                                    borderLeft: `4px solid ${brandColor}`,
                                  }}
                                >
                                  <div className="flex items-center gap-1">
                                    {abSwapMode && (
                                      <span className={cn(
                                        "w-3 h-3 rounded-full border-2 flex-shrink-0 flex items-center justify-center",
                                        isSelected ? "bg-blue-500 border-blue-500" : "border-gray-400"
                                      )}>
                                        {isSelected && <span className="w-1.5 h-1.5 bg-white rounded-full" />}
                                      </span>
                                    )}
                                    <div className="font-medium truncate flex-1" style={{ color: brandColor }}>
                                      {event.className}
                                    </div>
                                    {event.lessonType && (
                                      <Badge
                                        variant="outline"
                                        className={cn(
                                          "text-[8px] px-1 py-0 h-3 flex-shrink-0",
                                          event.lessonType === "A" && "bg-red-100 text-red-700 border-red-300",
                                          event.lessonType === "B" && "bg-blue-100 text-blue-700 border-blue-300"
                                        )}
                                      >
                                        {event.lessonType}
                                      </Badge>
                                    )}
                                  </div>
                                  <div className="text-gray-600 flex items-center gap-1">
                                    <span>{event.startTime}</span>
                                    <span className="text-gray-400">|</span>
                                    <span>{event.enrolledCount}/{event.capacity}</span>
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        );
                      })}
                    </>
                  ))}
                </div>
              </div>
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

          {/* ABスワップセクション */}
          {eventDetail?.schedule?.calendarPattern && (
            <div className="border rounded-lg p-3 bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ArrowLeftRight className="w-4 h-4 text-gray-500" />
                  <span className="text-sm font-medium">レッスンタイプ変更</span>
                </div>
                <div className="flex items-center gap-1">
                  {["A", "B", "P", "Y"].map((type) => (
                    <Button
                      key={type}
                      variant={eventDetail.schedule.lessonType === type ? "default" : "outline"}
                      size="sm"
                      className={`h-7 px-2 text-xs ${
                        eventDetail.schedule.lessonType === type
                          ? getLessonTypeColor(type) + " text-white"
                          : ""
                      }`}
                      disabled={swapLoading || eventDetail.schedule.lessonType === type}
                      onClick={() => handleABSwap(type as "A" | "B" | "P" | "Y")}
                    >
                      {swapLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : type}
                    </Button>
                  ))}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 ml-1"
                    disabled={swapLoading}
                    onClick={() => handleABSwap()}
                    title="A↔B 自動切り替え"
                  >
                    {swapLoading ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3 h-3" />
                    )}
                  </Button>
                </div>
              </div>
              <div className="text-[10px] text-gray-500 mt-1">
                A: 外国人あり / B: 日本人のみ / P: プログラミング / Y: 休講
              </div>
            </div>
          )}

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
                        <Link
                          href={`/students?id=${student.id}`}
                          className="flex items-center gap-2 hover:bg-gray-100 rounded p-1 -m-1 flex-1 cursor-pointer"
                          onClick={() => setSelectedEvent(null)}
                        >
                          {student.attendanceStatus === "present" ? (
                            <UserCheck className="w-4 h-4 text-green-500" />
                          ) : student.attendanceStatus === "absent" ? (
                            <UserX className="w-4 h-4 text-red-500" />
                          ) : (
                            <Users className="w-4 h-4 text-gray-400" />
                          )}
                          <div>
                            <div className="font-medium hover:text-blue-600 underline-offset-2 hover:underline">{student.name}</div>
                            <div className="text-[10px] text-gray-500">
                              {student.studentNo} | {student.grade}
                            </div>
                          </div>
                        </Link>
                        <div className="flex items-center gap-2">
                          {/* 出欠ボタン */}
                          <div className="flex gap-1">
                            <Button
                              variant={student.attendanceStatus === "present" ? "default" : "outline"}
                              size="sm"
                              className="h-6 px-2 text-xs"
                              onClick={() => handleMarkAttendance(student.id, "present")}
                            >
                              出席
                            </Button>
                            <Button
                              variant={student.attendanceStatus === "absent" ? "destructive" : "outline"}
                              size="sm"
                              className="h-6 px-2 text-xs"
                              onClick={() => handleMarkAttendance(student.id, "absent")}
                            >
                              欠席
                            </Button>
                          </div>
                          <div className="text-right text-[10px] text-gray-500 min-w-[80px]">
                            {student.guardianName && (
                              <div>{student.guardianName}</div>
                            )}
                            {student.guardianPhone && (
                              <div className="flex items-center gap-1 justify-end">
                                <Phone className="w-3 h-3" />
                                {student.guardianPhone}
                              </div>
                            )}
                          </div>
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

      {/* カレンダーエージェント */}
      <CalendarAgent
        onABSwap={handleAgentABSwap}
        onSetClosure={handleAgentSetClosure}
        onExportCSV={handleAgentExportCSV}
        onImportCSV={handleAgentImportCSV}
        onStartABSwapMode={startABSwapMode}
        selectedSchool={selectedSchool}
        selectedDate={selectedEvent?.date || clickedDate || undefined}
        selectedEvent={
          selectedEvent && eventDetail
            ? {
                calendarPattern: eventDetail.schedule.calendarPattern || undefined,
                lessonType: eventDetail.schedule.lessonType,
              }
            : null
        }
        brands={brands.map((b) => ({
          id: b.id,
          name: b.brandName || b.brand_name || "",
        }))}
        schools={schools.map((s) => ({
          id: s.id,
          name: s.schoolName || s.school_name || "",
        }))}
        currentYear={currentDate.getFullYear()}
        currentMonth={currentDate.getMonth() + 1}
      />
    </div>
  );
}
