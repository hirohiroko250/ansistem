"use client";

import { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Calendar,
  Clock,
  ChevronLeft,
  ChevronRight,
  Plus,
  Loader2,
  Users,
  Video,
  MapPin,
  Trash2,
} from "lucide-react";
import apiClient from "@/lib/api/client";

interface StaffAvailability {
  id: string;
  employee_id: string;
  employee_name: string;
  date: string;
  start_time: string;
  end_time: string;
  status: string;
  capacity: number;
  current_bookings: number;
  cancel_deadline_minutes: number;
  school_id?: string;
  school_name?: string;
  online_available: boolean;
  meeting_url?: string;
  notes?: string;
  is_bookable: boolean;
  remaining_slots: number;
}

interface StaffScheduleTabProps {
  staffId: string;
}

const statusColors: Record<string, string> = {
  available: "bg-green-100 text-green-800",
  booked: "bg-blue-100 text-blue-800",
  cancelled: "bg-gray-100 text-gray-800",
  blocked: "bg-red-100 text-red-800",
};

const statusLabels: Record<string, string> = {
  available: "空き",
  booked: "予約済",
  cancelled: "キャンセル",
  blocked: "ブロック",
};

export function StaffScheduleTab({ staffId }: StaffScheduleTabProps) {
  const [availabilities, setAvailabilities] = useState<StaffAvailability[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState<"week" | "month">("week");
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // 新規作成フォーム
  const [newSlot, setNewSlot] = useState({
    date: "",
    start_time: "09:00",
    end_time: "10:00",
    capacity: 1,
    cancel_deadline_minutes: 15,
    online_available: false,
    meeting_url: "",
    notes: "",
  });

  useEffect(() => {
    loadAvailabilities();
  }, [staffId, currentDate, viewMode]);

  async function loadAvailabilities() {
    setLoading(true);
    try {
      // 週または月の範囲を計算
      let startDate: Date, endDate: Date;

      if (viewMode === "week") {
        const dayOfWeek = currentDate.getDay();
        startDate = new Date(currentDate);
        startDate.setDate(currentDate.getDate() - dayOfWeek);
        endDate = new Date(startDate);
        endDate.setDate(startDate.getDate() + 6);
      } else {
        startDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
        endDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
      }

      const startStr = startDate.toISOString().split("T")[0];
      const endStr = endDate.toISOString().split("T")[0];

      const response = await apiClient.get<{ results?: StaffAvailability[] } | StaffAvailability[]>(
        `/hr/availabilities/?employee_id=${staffId}&start_date=${startStr}&end_date=${endStr}`
      );
      if (Array.isArray(response)) {
        setAvailabilities(response);
      } else {
        setAvailabilities(response.results || []);
      }
    } catch (err) {
      console.error("Failed to load availabilities:", err);
    }
    setLoading(false);
  }

  function handlePrev() {
    const newDate = new Date(currentDate);
    if (viewMode === "week") {
      newDate.setDate(newDate.getDate() - 7);
    } else {
      newDate.setMonth(newDate.getMonth() - 1);
    }
    setCurrentDate(newDate);
  }

  function handleNext() {
    const newDate = new Date(currentDate);
    if (viewMode === "week") {
      newDate.setDate(newDate.getDate() + 7);
    } else {
      newDate.setMonth(newDate.getMonth() + 1);
    }
    setCurrentDate(newDate);
  }

  function handleToday() {
    setCurrentDate(new Date());
  }

  function openCreateModal(date?: string) {
    setNewSlot({
      date: date || new Date().toISOString().split("T")[0],
      start_time: "09:00",
      end_time: "10:00",
      capacity: 1,
      cancel_deadline_minutes: 15,
      online_available: false,
      meeting_url: "",
      notes: "",
    });
    setSelectedDate(date || null);
    setCreateModalOpen(true);
  }

  async function handleCreate() {
    setSaving(true);
    try {
      await apiClient.post<StaffAvailability>("/hr/availabilities/", {
        ...newSlot,
        employee_id: staffId,
      });
      setCreateModalOpen(false);
      await loadAvailabilities();
    } catch (err) {
      console.error("Failed to create availability:", err);
    }
    setSaving(false);
  }

  async function handleDelete(id: string) {
    if (!confirm("この空き時間を削除しますか？")) return;
    try {
      await apiClient.delete<void>(`/hr/availabilities/${id}/`);
      await loadAvailabilities();
    } catch (err) {
      console.error("Failed to delete availability:", err);
    }
  }

  // 週表示用のデータを生成
  const weekData = useMemo(() => {
    if (viewMode !== "week") return [];

    const dayOfWeek = currentDate.getDay();
    const startOfWeek = new Date(currentDate);
    startOfWeek.setDate(currentDate.getDate() - dayOfWeek);

    const days = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek);
      date.setDate(startOfWeek.getDate() + i);
      const dateStr = date.toISOString().split("T")[0];
      const slots = availabilities.filter((a) => a.date === dateStr);
      days.push({
        date,
        dateStr,
        dayName: ["日", "月", "火", "水", "木", "金", "土"][date.getDay()],
        isToday: dateStr === new Date().toISOString().split("T")[0],
        slots,
      });
    }
    return days;
  }, [currentDate, availabilities, viewMode]);

  // 時間帯の配列（5:30 ~ 23:30）
  const timeSlots = useMemo(() => {
    const slots = [];
    for (let h = 5; h <= 23; h++) {
      slots.push(`${h.toString().padStart(2, "0")}:00`);
      slots.push(`${h.toString().padStart(2, "0")}:30`);
    }
    return slots;
  }, []);

  function getSlotPosition(time: string) {
    const [h, m] = time.split(":").map(Number);
    return ((h - 5) * 2 + (m >= 30 ? 1 : 0)) * 24; // 24px per 30min
  }

  function getSlotHeight(startTime: string, endTime: string) {
    const startPos = getSlotPosition(startTime);
    const endPos = getSlotPosition(endTime);
    return endPos - startPos;
  }

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
          <Button variant="outline" size="sm" onClick={handlePrev}>
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={handleToday}>
            今日
          </Button>
          <Button variant="outline" size="sm" onClick={handleNext}>
            <ChevronRight className="w-4 h-4" />
          </Button>
          <span className="ml-2 font-semibold">
            {currentDate.getFullYear()}年{currentDate.getMonth() + 1}月
            {viewMode === "week" && (
              <span className="text-gray-500 ml-1">
                第{Math.ceil((currentDate.getDate() + new Date(currentDate.getFullYear(), currentDate.getMonth(), 1).getDay()) / 7)}週
              </span>
            )}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Select value={viewMode} onValueChange={(v: "week" | "month") => setViewMode(v)}>
            <SelectTrigger className="w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="week">週</SelectItem>
              <SelectItem value="month">月</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={() => openCreateModal()}>
            <Plus className="w-4 h-4 mr-1" />
            空き時間追加
          </Button>
        </div>
      </div>

      {/* 週表示カレンダー */}
      {viewMode === "week" && (
        <div className="border rounded-lg overflow-hidden">
          {/* 曜日ヘッダー */}
          <div className="grid grid-cols-8 border-b bg-gray-50">
            <div className="p-2 text-xs font-medium text-gray-500 border-r" />
            {weekData.map((day) => (
              <div
                key={day.dateStr}
                className={`p-2 text-center border-r last:border-r-0 ${
                  day.isToday ? "bg-blue-50" : ""
                }`}
              >
                <div className={`text-xs ${day.date.getDay() === 0 ? "text-red-500" : day.date.getDay() === 6 ? "text-blue-500" : "text-gray-500"}`}>
                  {day.dayName}
                </div>
                <div className={`text-lg font-semibold ${day.isToday ? "text-blue-600" : ""}`}>
                  {day.date.getDate()}
                </div>
              </div>
            ))}
          </div>

          {/* スケジュールグリッド */}
          <div className="grid grid-cols-8 h-[500px] overflow-y-auto">
            {/* 時間軸 */}
            <div className="border-r">
              {timeSlots.map((time) => (
                <div key={time} className="h-6 text-xs text-gray-400 text-right pr-2 border-b">
                  {time.endsWith(":00") && time}
                </div>
              ))}
            </div>

            {/* 各日のスロット */}
            {weekData.map((day) => (
              <div
                key={day.dateStr}
                className={`relative border-r last:border-r-0 ${day.isToday ? "bg-blue-50/30" : ""}`}
                onClick={() => openCreateModal(day.dateStr)}
              >
                {/* 時間グリッド線 */}
                {timeSlots.map((time) => (
                  <div key={time} className="h-6 border-b border-gray-100" />
                ))}

                {/* 予約スロット */}
                {day.slots.map((slot) => (
                  <div
                    key={slot.id}
                    className={`absolute left-1 right-1 rounded px-1 py-0.5 text-xs cursor-pointer overflow-hidden ${statusColors[slot.status]}`}
                    style={{
                      top: `${getSlotPosition(slot.start_time)}px`,
                      height: `${Math.max(getSlotHeight(slot.start_time, slot.end_time), 24)}px`,
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate">
                        {slot.start_time.substring(0, 5)}
                      </span>
                      <button
                        className="hover:text-red-600"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(slot.id);
                        }}
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                    {getSlotHeight(slot.start_time, slot.end_time) >= 48 && (
                      <>
                        <div className="flex items-center gap-1 text-[10px] mt-0.5">
                          <Users className="w-3 h-3" />
                          {slot.current_bookings}/{slot.capacity}
                        </div>
                        {slot.online_available && (
                          <Video className="w-3 h-3 mt-0.5" />
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 月表示カレンダー（簡易版） */}
      {viewMode === "month" && (
        <div className="border rounded-lg p-4">
          <div className="grid grid-cols-7 gap-2">
            {["日", "月", "火", "水", "木", "金", "土"].map((day) => (
              <div key={day} className="text-center text-sm font-medium text-gray-500 py-2">
                {day}
              </div>
            ))}
            {/* 月のカレンダーを生成 */}
            {(() => {
              const firstDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
              const lastDay = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
              const cells = [];

              // 月初の空白
              for (let i = 0; i < firstDay.getDay(); i++) {
                cells.push(<div key={`empty-${i}`} />);
              }

              // 日付
              for (let d = 1; d <= lastDay.getDate(); d++) {
                const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), d);
                const dateStr = date.toISOString().split("T")[0];
                const daySlots = availabilities.filter((a) => a.date === dateStr);
                const isToday = dateStr === new Date().toISOString().split("T")[0];

                cells.push(
                  <div
                    key={d}
                    className={`p-2 min-h-[80px] border rounded cursor-pointer hover:bg-gray-50 ${
                      isToday ? "bg-blue-50 border-blue-200" : ""
                    }`}
                    onClick={() => openCreateModal(dateStr)}
                  >
                    <div className={`text-sm font-medium ${isToday ? "text-blue-600" : ""}`}>
                      {d}
                    </div>
                    <div className="mt-1 space-y-1">
                      {daySlots.slice(0, 3).map((slot) => (
                        <div
                          key={slot.id}
                          className={`text-xs px-1 py-0.5 rounded truncate ${statusColors[slot.status]}`}
                        >
                          {slot.start_time.substring(0, 5)}
                        </div>
                      ))}
                      {daySlots.length > 3 && (
                        <div className="text-xs text-gray-500">
                          +{daySlots.length - 3}件
                        </div>
                      )}
                    </div>
                  </div>
                );
              }

              return cells;
            })()}
          </div>
        </div>
      )}

      {/* 凡例 */}
      <div className="flex items-center gap-4 text-sm">
        <span className="text-gray-500">ステータス:</span>
        {Object.entries(statusLabels).map(([key, label]) => (
          <Badge key={key} className={statusColors[key]}>
            {label}
          </Badge>
        ))}
      </div>

      {/* 空き時間作成モーダル */}
      <Dialog open={createModalOpen} onOpenChange={setCreateModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>空き時間を追加</DialogTitle>
            <DialogDescription>
              生徒が予約できる空き時間を設定します
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>日付</Label>
              <Input
                type="date"
                value={newSlot.date}
                onChange={(e) => setNewSlot({ ...newSlot, date: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>開始時刻</Label>
                <Input
                  type="time"
                  value={newSlot.start_time}
                  onChange={(e) => setNewSlot({ ...newSlot, start_time: e.target.value })}
                />
              </div>
              <div>
                <Label>終了時刻</Label>
                <Input
                  type="time"
                  value={newSlot.end_time}
                  onChange={(e) => setNewSlot({ ...newSlot, end_time: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>定員</Label>
                <Input
                  type="number"
                  min="1"
                  value={newSlot.capacity}
                  onChange={(e) => setNewSlot({ ...newSlot, capacity: parseInt(e.target.value) || 1 })}
                />
              </div>
              <div>
                <Label>キャンセル期限（分前）</Label>
                <Input
                  type="number"
                  min="0"
                  value={newSlot.cancel_deadline_minutes}
                  onChange={(e) =>
                    setNewSlot({ ...newSlot, cancel_deadline_minutes: parseInt(e.target.value) || 0 })
                  }
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                id="online"
                checked={newSlot.online_available}
                onCheckedChange={(c) => setNewSlot({ ...newSlot, online_available: c })}
              />
              <Label htmlFor="online">オンライン対応可</Label>
            </div>
            {newSlot.online_available && (
              <div>
                <Label>ミーティングURL</Label>
                <Input
                  value={newSlot.meeting_url}
                  onChange={(e) => setNewSlot({ ...newSlot, meeting_url: e.target.value })}
                  placeholder="https://meet.google.com/..."
                />
              </div>
            )}
            <div>
              <Label>備考</Label>
              <Input
                value={newSlot.notes}
                onChange={(e) => setNewSlot({ ...newSlot, notes: e.target.value })}
                placeholder="特記事項があれば..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateModalOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleCreate} disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  保存中...
                </>
              ) : (
                "作成"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
