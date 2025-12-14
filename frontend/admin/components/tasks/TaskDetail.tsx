"use client";

import { Task } from "@/lib/api/staff";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Calendar, User, CheckCircle, Edit } from "lucide-react";
import { format } from "date-fns";
import { ja } from "date-fns/locale";

interface TaskDetailProps {
  task: Task;
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

export function TaskDetail({ task }: TaskDetailProps) {
  const priorityInfo = priorityConfig[task.priority] || priorityConfig.medium;
  const isOverdue =
    task.due_date && new Date(task.due_date) < new Date() && task.status !== "completed";

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-start gap-2 mb-2">
          <h2 className="text-2xl font-bold text-gray-900 flex-1">{task.title}</h2>
          {isOverdue && (
            <Badge variant="destructive" className="text-xs">
              期限超過
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">
            {taskTypeLabels[task.task_type] || task.task_type}
          </Badge>
          <Badge variant={priorityInfo.variant}>{priorityInfo.label}</Badge>
          <Badge variant="secondary">
            {statusLabels[task.status] || task.status}
          </Badge>
        </div>
      </div>

      <div className="flex gap-2">
        <Button className="flex-1">
          <CheckCircle className="w-4 h-4 mr-2" />
          完了にする
        </Button>
        <Button variant="outline" className="flex-1">
          <Edit className="w-4 h-4 mr-2" />
          編集
        </Button>
      </div>

      <Separator />

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">詳細</h3>
        <p className="text-sm text-gray-600 whitespace-pre-wrap">
          {task.description || "説明がありません"}
        </p>
      </div>

      <Separator />

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">タスク情報</h3>
        <div className="space-y-3 text-sm">
          {task.due_date && (
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-gray-600">期限</p>
                <p className="font-medium text-gray-900">
                  {format(new Date(task.due_date), "yyyy年M月d日 HH:mm", {
                    locale: ja,
                  })}
                </p>
              </div>
            </div>
          )}

          {task.assigned_to_id && (
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-gray-600">担当者</p>
                <p className="font-medium text-gray-900">{task.assigned_to_id}</p>
              </div>
            </div>
          )}

          {(task.student_name || task.guardian_name) && (
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-gray-600">関連{task.student_name ? "生徒" : "保護者"}</p>
                <p className="font-medium text-gray-900">
                  {task.student_name || task.guardian_name}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      <Separator />

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">作成日時</h3>
        <p className="text-sm text-gray-600">
          {format(new Date(task.created_at), "yyyy年M月d日 HH:mm", {
            locale: ja,
          })}
        </p>
      </div>
    </div>
  );
}
