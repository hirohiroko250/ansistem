"use client";

import { Task } from "@/lib/api/staff";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { Calendar, AlertCircle } from "lucide-react";

interface TaskListProps {
  tasks: Task[];
  selectedTaskId?: string;
  onSelectTask: (taskId: string) => void;
}

const taskTypeLabels: Record<string, string> = {
  lesson_prep: "授業準備",
  parent_contact: "保護者連絡",
  admin: "事務処理",
  follow_up: "フォローアップ",
};

const statusLabels: Record<string, string> = {
  pending: "未着手",
  in_progress: "進行中",
  completed: "完了",
};

const priorityConfig: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" }
> = {
  high: { label: "高", variant: "destructive" },
  medium: { label: "中", variant: "default" },
  low: { label: "低", variant: "secondary" },
};

export function TaskList({ tasks, selectedTaskId, onSelectTask }: TaskListProps) {
  return (
    <div className="space-y-2">
      {tasks.map((task) => {
        const priorityInfo = priorityConfig[task.priority] || priorityConfig.medium;
        const isOverdue =
          task.due_date && new Date(task.due_date) < new Date() && task.status !== "completed";

        return (
          <Card
            key={task.id}
            className={cn(
              "p-4 cursor-pointer hover:shadow-md transition-all",
              selectedTaskId === task.id
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200",
              isOverdue && "border-l-4 border-l-red-500"
            )}
            onClick={() => onSelectTask(task.id)}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-gray-900">{task.title}</h3>
                  {isOverdue && <AlertCircle className="w-4 h-4 text-red-500" />}
                </div>
                <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                  {task.description}
                </p>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Badge variant="outline">
                    {taskTypeLabels[task.task_type] || task.task_type}
                  </Badge>
                  {task.student_name && (
                    <span>生徒：{task.student_name}</span>
                  )}
                  {!task.student_name && task.guardian_name && (
                    <span>保護者：{task.guardian_name}</span>
                  )}
                  {task.due_date && (
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {format(new Date(task.due_date), "M/d HH:mm", {
                        locale: ja,
                      })}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <Badge variant={priorityInfo.variant}>{priorityInfo.label}</Badge>
                <Badge variant="secondary" className="text-xs">
                  {statusLabels[task.status] || task.status}
                </Badge>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
