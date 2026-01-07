"use client";

import { Task } from "@/lib/api/staff";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { ja } from "date-fns/locale";

interface TaskListProps {
  tasks: Task[];
  selectedTaskId?: string;
  onSelectTask: (taskId: string) => void;
}

const statusConfig: Record<string, { label: string; className: string }> = {
  pending: { label: "未対応", className: "bg-red-100 text-red-800 border-red-300" },
  new: { label: "未対応", className: "bg-red-100 text-red-800 border-red-300" },
  in_progress: { label: "対応中", className: "bg-yellow-100 text-yellow-800 border-yellow-300" },
  completed: { label: "完了", className: "bg-green-100 text-green-800 border-green-300" },
  closed: { label: "クローズ", className: "bg-gray-100 text-gray-800 border-gray-300" },
};

const taskTypeLabels: Record<string, string> = {
  inquiry: "問い合わせ",
  trial_request: "体験希望",
  enrollment: "新規入会",
  lesson_prep: "授業準備",
  parent_contact: "保護者連絡",
  admin: "事務処理",
  follow_up: "フォローアップ",
  billing: "請求関連",
  absence: "お休み連絡",
  invoice: "請求書関連",
  other: "その他",
};

export function TaskList({ tasks, selectedTaskId, onSelectTask }: TaskListProps) {
  return (
    <div className="overflow-x-auto border rounded-lg">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">No.</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">登録日時</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">状態</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">担当者</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">カテゴリー</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">ブランド</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap min-w-[200px]">お問合せ内容</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap min-w-[150px]">件名</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">生徒ID</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">生徒名</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">保護者ID</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">保護者名</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">校舎</th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap">期限</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {tasks.map((task, index) => {
            const statusInfo = statusConfig[task.status] || statusConfig.pending;
            const isOverdue =
              task.due_date && new Date(task.due_date) < new Date() && task.status !== "completed";

            return (
              <tr
                key={task.id}
                className={cn(
                  "hover:bg-blue-50 cursor-pointer transition-colors",
                  selectedTaskId === task.id && "bg-blue-100",
                  isOverdue && "bg-red-50"
                )}
                onClick={() => onSelectTask(task.id)}
              >
                <td className="px-2 py-2 whitespace-nowrap text-gray-900">{index + 1}</td>
                <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                  {format(new Date(task.created_at), "yyyy/MM/dd HH:mm", { locale: ja })}
                </td>
                <td className="px-2 py-2 whitespace-nowrap">
                  <Badge variant="outline" className={cn("text-xs", statusInfo.className)}>
                    {task.status_display || statusInfo.label}
                  </Badge>
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                  {task.assigned_to_name || "未割当て"}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                  {task.category_name || taskTypeLabels[task.task_type] || task.task_type_display || task.task_type || "---"}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                  {task.brand_name || "---"}
                </td>
                <td className="px-2 py-2 text-gray-600 max-w-[300px] truncate" title={task.description}>
                  {task.description || "---"}
                </td>
                <td className="px-2 py-2 text-gray-900 font-medium max-w-[200px] truncate" title={task.title}>
                  {task.title}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                  {task.student ? task.student.substring(0, 8) : "---"}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                  {task.student_name || "---"}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                  {task.guardian ? task.guardian.substring(0, 8) : "---"}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                  {task.guardian_name || "---"}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                  {task.school_name || "---"}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                  {task.due_date
                    ? format(new Date(task.due_date), "MM/dd HH:mm", { locale: ja })
                    : "---"
                  }
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {tasks.length === 0 && (
        <div className="text-center text-gray-500 py-8">
          タスクがありません
        </div>
      )}
    </div>
  );
}
