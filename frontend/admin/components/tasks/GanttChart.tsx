"use client";

import { useState, useMemo } from "react";
import { Task } from "@/lib/api/staff";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { ChevronLeft, ChevronRight, Calendar } from "lucide-react";
import {
  format,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
  addMonths,
  subMonths,
  isWeekend,
  differenceInDays,
  startOfWeek,
  endOfWeek,
  addWeeks,
  subWeeks,
  eachWeekOfInterval,
} from "date-fns";
import { ja } from "date-fns/locale";
import { cn } from "@/lib/utils";

interface GanttChartProps {
  tasks: Task[];
  selectedTaskId?: string;
  onSelectTask: (taskId: string) => void;
}

type ViewMode = "month" | "week";

const priorityColors: Record<string, string> = {
  urgent: "bg-red-500",
  high: "bg-orange-500",
  normal: "bg-blue-500",
  medium: "bg-blue-500",
  low: "bg-gray-400",
};

const statusColors: Record<string, string> = {
  new: "bg-blue-100 border-blue-300",
  pending: "bg-blue-100 border-blue-300",
  in_progress: "bg-yellow-100 border-yellow-300",
  waiting: "bg-purple-100 border-purple-300",
  completed: "bg-green-100 border-green-300",
};

export function GanttChart({
  tasks,
  selectedTaskId,
  onSelectTask,
}: GanttChartProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("month");
  const [currentDate, setCurrentDate] = useState(new Date());

  // 期限があるタスクのみ（有効な日付のみ）
  const tasksWithDueDate = useMemo(() => {
    return tasks.filter((task) => {
      if (!task.due_date) return false;
      const date = new Date(task.due_date);
      return !isNaN(date.getTime());
    });
  }, [tasks]);

  // 表示期間の日付を取得
  const dateRange = useMemo(() => {
    if (viewMode === "month") {
      const start = startOfMonth(currentDate);
      const end = endOfMonth(currentDate);
      return eachDayOfInterval({ start, end });
    } else {
      const start = startOfWeek(currentDate, { weekStartsOn: 1 });
      const end = endOfWeek(addWeeks(currentDate, 3), { weekStartsOn: 1 });
      return eachDayOfInterval({ start, end });
    }
  }, [currentDate, viewMode]);

  // 週の区切り（月表示用）
  const weeks = useMemo(() => {
    if (viewMode === "month") {
      return eachWeekOfInterval(
        {
          start: startOfMonth(currentDate),
          end: endOfMonth(currentDate),
        },
        { weekStartsOn: 1 }
      );
    }
    return [];
  }, [currentDate, viewMode]);

  // ナビゲーション
  const goToPrevious = () => {
    if (viewMode === "month") {
      setCurrentDate(subMonths(currentDate, 1));
    } else {
      setCurrentDate(subWeeks(currentDate, 4));
    }
  };

  const goToNext = () => {
    if (viewMode === "month") {
      setCurrentDate(addMonths(currentDate, 1));
    } else {
      setCurrentDate(addWeeks(currentDate, 4));
    }
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  // セル幅
  const cellWidth = viewMode === "month" ? 32 : 40;
  const taskListWidth = 280;

  // タスクのバー位置と幅を計算
  const getTaskBarStyle = (task: Task) => {
    if (!task.due_date) return null;

    const dueDate = new Date(task.due_date);
    if (isNaN(dueDate.getTime())) return null;

    const createdDate = task.created_at ? new Date(task.created_at) : new Date();
    const validCreatedDate = isNaN(createdDate.getTime()) ? new Date() : createdDate;

    // 開始日（作成日または期間の開始日のいずれか遅い方）
    const rangeStart = dateRange[0];
    const rangeEnd = dateRange[dateRange.length - 1];

    // 作成日が範囲外なら範囲の開始日を使用
    const barStart = validCreatedDate < rangeStart ? rangeStart : validCreatedDate;
    // 期限が範囲外なら範囲の終了日を使用
    const barEnd = dueDate > rangeEnd ? rangeEnd : dueDate;

    if (barStart > rangeEnd || barEnd < rangeStart) {
      return null; // 完全に範囲外
    }

    const startOffset = differenceInDays(barStart, rangeStart);
    const duration = Math.max(1, differenceInDays(barEnd, barStart) + 1);

    return {
      left: `${startOffset * cellWidth}px`,
      width: `${duration * cellWidth - 4}px`,
    };
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg border">
      {/* ヘッダー */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-gray-500" />
          <h3 className="font-semibold">ガントチャート</h3>
          <Badge variant="secondary" className="ml-2">
            {tasksWithDueDate.length}件
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          {/* ビューモード切替 */}
          <div className="flex rounded-lg border p-1">
            <Button
              variant={viewMode === "month" ? "secondary" : "ghost"}
              size="sm"
              className="h-7 px-3"
              onClick={() => setViewMode("month")}
            >
              月
            </Button>
            <Button
              variant={viewMode === "week" ? "secondary" : "ghost"}
              size="sm"
              className="h-7 px-3"
              onClick={() => setViewMode("week")}
            >
              週
            </Button>
          </div>

          {/* ナビゲーション */}
          <Button variant="outline" size="sm" onClick={goToPrevious}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={goToToday}>
            今日
          </Button>
          <Button variant="outline" size="sm" onClick={goToNext}>
            <ChevronRight className="h-4 w-4" />
          </Button>

          <span className="ml-2 font-medium">
            {format(currentDate, "yyyy年M月", { locale: ja })}
          </span>
        </div>
      </div>

      {/* チャート本体 */}
      <div className="flex flex-1 overflow-hidden">
        {/* タスクリスト */}
        <div
          className="flex-shrink-0 border-r"
          style={{ width: `${taskListWidth}px` }}
        >
          {/* ヘッダー */}
          <div className="h-12 px-3 flex items-center border-b bg-gray-50">
            <span className="text-sm font-medium text-gray-600">タスク名</span>
          </div>
          {/* タスク行 */}
          <ScrollArea className="h-[calc(100%-48px)]">
            {tasksWithDueDate.length === 0 ? (
              <div className="p-4 text-center text-gray-400 text-sm">
                期限が設定されたタスクがありません
              </div>
            ) : (
              tasksWithDueDate.map((task) => (
                <div
                  key={task.id}
                  className={cn(
                    "h-10 px-3 flex items-center border-b cursor-pointer hover:bg-gray-50 transition-colors",
                    selectedTaskId === task.id && "bg-blue-50"
                  )}
                  onClick={() => onSelectTask(task.id)}
                >
                  <div
                    className={cn(
                      "w-2 h-2 rounded-full mr-2 flex-shrink-0",
                      priorityColors[task.priority] || priorityColors.normal
                    )}
                  />
                  <span className="text-sm truncate">{task.title}</span>
                </div>
              ))
            )}
          </ScrollArea>
        </div>

        {/* ガントチャート部分 */}
        <ScrollArea className="flex-1">
          <div style={{ minWidth: `${dateRange.length * cellWidth}px` }}>
            {/* 日付ヘッダー */}
            <div className="h-12 flex border-b bg-gray-50 sticky top-0 z-10">
              {dateRange.map((date, index) => {
                const isToday = isSameDay(date, new Date());
                const isCurrentMonth = isSameMonth(date, currentDate);
                const weekend = isWeekend(date);

                return (
                  <div
                    key={index}
                    className={cn(
                      "flex-shrink-0 flex flex-col items-center justify-center border-r text-xs",
                      weekend && "bg-gray-100",
                      isToday && "bg-blue-100",
                      !isCurrentMonth && "text-gray-300"
                    )}
                    style={{ width: `${cellWidth}px` }}
                  >
                    <span className="text-gray-500">
                      {format(date, "E", { locale: ja })}
                    </span>
                    <span className={cn(isToday && "font-bold text-blue-600")}>
                      {format(date, "d")}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* タスクバー */}
            {tasksWithDueDate.map((task) => {
              const barStyle = getTaskBarStyle(task);
              const isSelected = selectedTaskId === task.id;

              return (
                <div
                  key={task.id}
                  className="h-10 relative border-b"
                  style={{
                    backgroundImage: `repeating-linear-gradient(90deg, transparent, transparent ${cellWidth - 1}px, #f3f4f6 ${cellWidth - 1}px, #f3f4f6 ${cellWidth}px)`,
                  }}
                >
                  {/* 今日の線 */}
                  {dateRange.some((d) => isSameDay(d, new Date())) && (
                    <div
                      className="absolute top-0 bottom-0 w-0.5 bg-blue-500 z-10"
                      style={{
                        left: `${differenceInDays(new Date(), dateRange[0]) * cellWidth + cellWidth / 2}px`,
                      }}
                    />
                  )}

                  {/* タスクバー */}
                  {barStyle && (
                    <div
                      className={cn(
                        "absolute top-1.5 h-7 rounded border-2 cursor-pointer transition-all",
                        statusColors[task.status] || statusColors.new,
                        isSelected && "ring-2 ring-blue-500 ring-offset-1"
                      )}
                      style={barStyle}
                      onClick={() => onSelectTask(task.id)}
                      title={`${task.title}\n期限: ${task.due_date && !isNaN(new Date(task.due_date).getTime()) ? format(new Date(task.due_date), "yyyy/MM/dd") : "-"}`}
                    >
                      <div className="h-full flex items-center px-2 overflow-hidden">
                        <span className="text-xs truncate">{task.title}</span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
      </div>
    </div>
  );
}
