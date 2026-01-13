"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Task } from "@/lib/api/staff";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { Calendar, User, AlertCircle } from "lucide-react";

interface TaskCardProps {
  task: Task;
  isSelected?: boolean;
  onClick?: () => void;
}

const priorityConfig: Record<string, { label: string; color: string }> = {
  urgent: { label: "緊急", color: "bg-red-500 text-white" },
  high: { label: "高", color: "bg-orange-500 text-white" },
  normal: { label: "通常", color: "bg-blue-500 text-white" },
  medium: { label: "中", color: "bg-blue-500 text-white" },
  low: { label: "低", color: "bg-gray-400 text-white" },
};

const taskTypeLabels: Record<string, string> = {
  customer_inquiry: "客問い合わせ",
  inquiry: "問い合わせ",
  chat: "チャット",
  trial_registration: "体験登録",
  enrollment: "入会申請",
  withdrawal: "退会",
  suspension: "休会",
  contract_change: "契約変更",
  tuition_operation: "授業料操作",
  debit_failure: "引落失敗",
  refund_request: "返金申請",
  bank_account_request: "口座申請",
  event_registration: "イベント",
  referral: "友人紹介",
  guardian_registration: "保護者登録",
  student_registration: "生徒登録",
  staff_registration: "社員登録",
  request: "依頼",
  trouble: "トラブル",
  follow_up: "フォローアップ",
  other: "その他",
};

export function TaskCard({ task, isSelected, onClick }: TaskCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const priorityInfo = priorityConfig[task.priority] || priorityConfig.normal;

  // 日付の有効性チェック
  const dueDate = task.due_date ? new Date(task.due_date) : null;
  const isValidDueDate = dueDate && !isNaN(dueDate.getTime());
  const isOverdue =
    isValidDueDate &&
    dueDate < new Date() &&
    task.status !== "completed";

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className={cn(
        "bg-white rounded-lg border shadow-sm p-3 cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow",
        isDragging && "opacity-50 shadow-lg",
        isSelected && "ring-2 ring-blue-500",
        isOverdue && "border-red-300 bg-red-50"
      )}
    >
      {/* タスクタイプ & 優先度 */}
      <div className="flex items-center gap-1 mb-2 flex-wrap">
        <Badge variant="outline" className="text-xs">
          {task.category_name || taskTypeLabels[task.task_type] || task.task_type}
        </Badge>
        <Badge className={cn("text-xs", priorityInfo.color)}>
          {priorityInfo.label}
        </Badge>
        {isOverdue && (
          <Badge variant="destructive" className="text-xs">
            <AlertCircle className="w-3 h-3 mr-1" />
            期限超過
          </Badge>
        )}
      </div>

      {/* タイトル */}
      <h4 className="font-medium text-sm text-gray-900 mb-2 line-clamp-2">
        {task.title}
      </h4>

      {/* 説明（省略表示） */}
      {task.description && (
        <p className="text-xs text-gray-500 mb-2 line-clamp-2">
          {task.description}
        </p>
      )}

      {/* メタ情報 */}
      <div className="flex items-center gap-3 text-xs text-gray-500">
        {task.assigned_to_name && (
          <div className="flex items-center gap-1">
            <User className="w-3 h-3" />
            <span className="truncate max-w-[80px]">{task.assigned_to_name}</span>
          </div>
        )}
        {isValidDueDate && dueDate && (
          <div className={cn("flex items-center gap-1", isOverdue && "text-red-600")}>
            <Calendar className="w-3 h-3" />
            <span>{format(dueDate, "M/d", { locale: ja })}</span>
          </div>
        )}
      </div>

      {/* 関連情報 */}
      {(task.student_name || task.guardian_name || task.school_name) && (
        <div className="mt-2 pt-2 border-t text-xs text-gray-400">
          {task.student_name && <span className="mr-2">生徒: {task.student_name}</span>}
          {task.guardian_name && <span className="mr-2">保護者: {task.guardian_name}</span>}
          {task.school_name && <span>校舎: {task.school_name}</span>}
        </div>
      )}
    </div>
  );
}

// ドラッグ中のオーバーレイ用
export function TaskCardOverlay({ task }: { task: Task }) {
  const priorityInfo = priorityConfig[task.priority] || priorityConfig.normal;

  return (
    <div className="bg-white rounded-lg border shadow-lg p-3 w-[280px] rotate-3">
      <div className="flex items-center gap-1 mb-2">
        <Badge variant="outline" className="text-xs">
          {taskTypeLabels[task.task_type] || task.task_type}
        </Badge>
        <Badge className={cn("text-xs", priorityInfo.color)}>
          {priorityInfo.label}
        </Badge>
      </div>
      <h4 className="font-medium text-sm text-gray-900 line-clamp-2">
        {task.title}
      </h4>
    </div>
  );
}
