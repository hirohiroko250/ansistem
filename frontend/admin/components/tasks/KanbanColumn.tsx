"use client";

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { Task } from "@/lib/api/staff";
import { TaskCard } from "./TaskCard";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";

export interface ColumnConfig {
  id: string;
  title: string;
  color: string;
  bgColor: string;
}

interface KanbanColumnProps {
  column: ColumnConfig;
  tasks: Task[];
  selectedTaskId?: string;
  onSelectTask: (taskId: string) => void;
}

export function KanbanColumn({
  column,
  tasks,
  selectedTaskId,
  onSelectTask,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });

  return (
    <div
      className={cn(
        "flex flex-col bg-gray-100 rounded-lg min-w-[300px] max-w-[300px]",
        isOver && "ring-2 ring-blue-400"
      )}
    >
      {/* カラムヘッダー */}
      <div
        className={cn(
          "px-3 py-2 rounded-t-lg flex items-center justify-between",
          column.bgColor
        )}
      >
        <div className="flex items-center gap-2">
          <div className={cn("w-3 h-3 rounded-full", column.color)} />
          <h3 className="font-semibold text-sm text-gray-800">{column.title}</h3>
        </div>
        <span className="bg-white/80 px-2 py-0.5 rounded-full text-xs font-medium text-gray-600">
          {tasks.length}
        </span>
      </div>

      {/* タスクリスト */}
      <ScrollArea className="flex-1 p-2" style={{ height: "calc(100vh - 280px)" }}>
        <div
          ref={setNodeRef}
          className="space-y-2 min-h-[100px]"
        >
          <SortableContext
            items={tasks.map((t) => t.id)}
            strategy={verticalListSortingStrategy}
          >
            {tasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                isSelected={selectedTaskId === task.id}
                onClick={() => onSelectTask(task.id)}
              />
            ))}
          </SortableContext>

          {tasks.length === 0 && (
            <div className="text-center text-gray-400 py-8 text-sm">
              タスクがありません
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
