"use client";

import { useState } from "react";
import { Task, approveEmployeeTask, rejectEmployeeTask, completeTask } from "@/lib/api/staff";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Calendar, User, CheckCircle, Edit, UserCheck, UserX, Loader2 } from "lucide-react";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface TaskDetailProps {
  task: Task;
  onTaskUpdated?: () => void;
}

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
  staff_registration: "社員登録",
  other: "その他",
};

const statusLabels: Record<string, string> = {
  new: "新規",
  pending: "未着手",
  in_progress: "進行中",
  waiting: "保留",
  completed: "完了",
  cancelled: "キャンセル",
};

const priorityConfig: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" }
> = {
  urgent: { label: "緊急", variant: "destructive" },
  high: { label: "高", variant: "destructive" },
  normal: { label: "通常", variant: "default" },
  medium: { label: "中", variant: "default" },
  low: { label: "低", variant: "secondary" },
};

export function TaskDetail({ task, onTaskUpdated }: TaskDetailProps) {
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);

  const priorityInfo = priorityConfig[task.priority] || priorityConfig.normal;

  // 日付の有効性チェック
  const dueDate = task.due_date ? new Date(task.due_date) : null;
  const isValidDueDate = dueDate && !isNaN(dueDate.getTime());
  const createdDate = task.created_at ? new Date(task.created_at) : null;
  const isValidCreatedDate = createdDate && !isNaN(createdDate.getTime());

  const isOverdue =
    isValidDueDate && dueDate < new Date() && task.status !== "completed";

  // 社員登録承認タスクかどうか
  const isStaffRegistrationTask = task.task_type === "staff_registration" && task.source_type === "employee";
  const isActionable = task.status !== "completed" && task.status !== "cancelled";

  const handleApprove = async () => {
    if (!isStaffRegistrationTask) return;

    setIsApproving(true);
    try {
      const result = await approveEmployeeTask(task.id);
      if (result?.success) {
        alert(result.message);
        onTaskUpdated?.();
      }
    } catch (error) {
      console.error("承認エラー:", error);
      alert("承認に失敗しました");
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    if (!isStaffRegistrationTask) return;

    setIsRejecting(true);
    try {
      const result = await rejectEmployeeTask(task.id);
      if (result?.success) {
        alert(result.message);
        onTaskUpdated?.();
      }
    } catch (error) {
      console.error("却下エラー:", error);
      alert("却下に失敗しました");
    } finally {
      setIsRejecting(false);
      setShowRejectDialog(false);
    }
  };

  const handleComplete = async () => {
    setIsCompleting(true);
    try {
      await completeTask(task.id);
      onTaskUpdated?.();
    } catch (error) {
      console.error("完了エラー:", error);
      alert("完了処理に失敗しました");
    } finally {
      setIsCompleting(false);
    }
  };

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
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="outline">
            {taskTypeLabels[task.task_type] || task.task_type_display || task.task_type}
          </Badge>
          <Badge variant={priorityInfo.variant}>{priorityInfo.label}</Badge>
          <Badge variant={task.status === "completed" ? "default" : task.status === "cancelled" ? "secondary" : "outline"}>
            {statusLabels[task.status] || task.status_display || task.status}
          </Badge>
        </div>
      </div>

      {/* 社員登録承認タスクの場合、承認/却下ボタンを表示 */}
      {isStaffRegistrationTask && isActionable && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800 mb-3">
            この社員登録を承認しますか？承認すると社員一覧に表示されます。
          </p>
          <div className="flex gap-2">
            <Button
              onClick={handleApprove}
              disabled={isApproving || isRejecting}
              className="flex-1 bg-green-600 hover:bg-green-700"
            >
              {isApproving ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <UserCheck className="w-4 h-4 mr-2" />
              )}
              承認する
            </Button>
            <Button
              variant="destructive"
              onClick={() => setShowRejectDialog(true)}
              disabled={isApproving || isRejecting}
              className="flex-1"
            >
              {isRejecting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <UserX className="w-4 h-4 mr-2" />
              )}
              却下する
            </Button>
          </div>
        </div>
      )}

      {/* 通常のタスクの場合、完了/編集ボタンを表示 */}
      {!isStaffRegistrationTask && isActionable && (
        <div className="flex gap-2">
          <Button
            className="flex-1"
            onClick={handleComplete}
            disabled={isCompleting}
          >
            {isCompleting ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <CheckCircle className="w-4 h-4 mr-2" />
            )}
            完了にする
          </Button>
          <Button variant="outline" className="flex-1">
            <Edit className="w-4 h-4 mr-2" />
            編集
          </Button>
        </div>
      )}

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
          {isValidDueDate && dueDate && (
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-gray-600">期限</p>
                <p className="font-medium text-gray-900">
                  {format(dueDate, "yyyy年M月d日 HH:mm", { locale: ja })}
                </p>
              </div>
            </div>
          )}

          {(task.assigned_to_id || task.assigned_to_name) && (
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-gray-600">担当者</p>
                <p className="font-medium text-gray-900">{task.assigned_to_name || task.assigned_to_id}</p>
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

          {task.school_name && (
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-gray-600">校舎</p>
                <p className="font-medium text-gray-900">{task.school_name}</p>
              </div>
            </div>
          )}

          {task.brand_name && (
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-gray-600">ブランド</p>
                <p className="font-medium text-gray-900">{task.brand_name}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <Separator />

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">作成日時</h3>
        <p className="text-sm text-gray-600">
          {isValidCreatedDate && createdDate
            ? format(createdDate, "yyyy年M月d日 HH:mm", { locale: ja })
            : "---"}
        </p>
      </div>

      {/* 却下確認ダイアログ */}
      <AlertDialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>社員登録を却下しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              この操作は取り消せません。社員データとユーザーアカウントが削除されます。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isRejecting}>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleReject}
              disabled={isRejecting}
              className="bg-red-600 hover:bg-red-700"
            >
              {isRejecting ? "処理中..." : "却下する"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
