"use client";

import { useState } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
} from "@dnd-kit/core";
import { Task } from "@/lib/api/staff";
import { KanbanColumn, ColumnConfig } from "./KanbanColumn";
import { TaskCardOverlay } from "./TaskCard";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";

interface KanbanBoardProps {
  tasks: Task[];
  selectedTaskId?: string;
  onSelectTask: (taskId: string) => void;
  onStatusChange: (taskId: string, newStatus: string) => Promise<void>;
}

const columns: ColumnConfig[] = [
  {
    id: "new",
    title: "新規",
    color: "bg-blue-500",
    bgColor: "bg-blue-100",
  },
  {
    id: "in_progress",
    title: "対応中",
    color: "bg-yellow-500",
    bgColor: "bg-yellow-100",
  },
  {
    id: "waiting",
    title: "保留",
    color: "bg-purple-500",
    bgColor: "bg-purple-100",
  },
  {
    id: "completed",
    title: "完了",
    color: "bg-green-500",
    bgColor: "bg-green-100",
  },
];

export function KanbanBoard({
  tasks,
  selectedTaskId,
  onSelectTask,
  onStatusChange,
}: KanbanBoardProps) {
  const [activeTask, setActiveTask] = useState<Task | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  // ステータスでタスクをグループ化
  const getTasksByStatus = (status: string): Task[] => {
    // "new" と "pending" は同じ列に表示
    if (status === "new") {
      return tasks.filter((t) => t.status === "new" || t.status === "pending");
    }
    return tasks.filter((t) => t.status === status);
  };

  const handleDragStart = (event: DragStartEvent) => {
    const task = tasks.find((t) => t.id === event.active.id);
    if (task) {
      setActiveTask(task);
    }
  };

  const handleDragOver = (event: DragOverEvent) => {
    // オプション: ホバー時のプレビュー処理
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);

    if (!over) return;

    const taskId = active.id as string;
    const targetStatus = over.id as string;

    // カラムにドロップした場合
    if (columns.some((col) => col.id === targetStatus)) {
      const task = tasks.find((t) => t.id === taskId);
      if (task && task.status !== targetStatus) {
        await onStatusChange(taskId, targetStatus);
      }
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <ScrollArea className="w-full">
        <div className="flex gap-4 p-4 min-w-max">
          {columns.map((column) => (
            <KanbanColumn
              key={column.id}
              column={column}
              tasks={getTasksByStatus(column.id)}
              selectedTaskId={selectedTaskId}
              onSelectTask={onSelectTask}
            />
          ))}
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>

      <DragOverlay>
        {activeTask ? <TaskCardOverlay task={activeTask} /> : null}
      </DragOverlay>
    </DndContext>
  );
}
