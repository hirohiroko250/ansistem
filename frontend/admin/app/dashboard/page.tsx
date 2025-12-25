"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  CheckCircle2,
  Circle,
  Clock,
  Plus,
  Filter,
  User,
  FileText,
  MessageSquare,
  AlertCircle,
  Building,
  Loader2,
  Calendar,
  Lock,
  Unlock,
  CreditCard,
  Pause,
  Undo2,
  X,
  ChevronRight,
  ExternalLink,
  UserPlus,
  Send,
  Landmark,
} from "lucide-react";
import { getTasks, completeTask, reopenTask, updateTask, Task } from "@/lib/api/staff";
import apiClient from "@/lib/api/client";
import { Sidebar } from "@/components/layout/Sidebar";

// カテゴリーアイコンを取得
function getCategoryIcon(taskType: string, size: "sm" | "md" = "sm") {
  const className = size === "sm" ? "w-3 h-3" : "w-4 h-4";
  switch (taskType) {
    case "student_registration":
    case "guardian_registration":
      return <User className={className} />;
    case "enrollment":
    case "withdrawal":
    case "contract_change":
      return <FileText className={className} />;
    case "inquiry":
    case "chat":
      return <MessageSquare className={className} />;
    case "trial_registration":
      return <Building className={className} />;
    case "suspension":
      return <Pause className={className} />;
    case "debit_failure":
      return <CreditCard className={className} />;
    case "refund_request":
      return <Undo2 className={className} />;
    case "bank_account_request":
      return <Landmark className={className} />;
    default:
      return <AlertCircle className={className} />;
  }
}

// 優先度のバッジを取得
function getPriorityBadge(priority: string, priorityDisplay?: string) {
  const label = priorityDisplay || priority;
  switch (priority) {
    case "urgent":
      return <Badge variant="destructive">{label}</Badge>;
    case "high":
      return <Badge variant="destructive">{label}</Badge>;
    case "normal":
      return <Badge variant="default">{label}</Badge>;
    case "low":
      return <Badge variant="secondary">{label}</Badge>;
    default:
      return <Badge variant="secondary">{label}</Badge>;
  }
}

// ステータスのバッジを取得
function getStatusBadge(status: string, statusDisplay?: string) {
  const label = statusDisplay || status;
  switch (status) {
    case "completed":
      return <Badge className="bg-green-100 text-green-800">{label}</Badge>;
    case "in_progress":
      return <Badge className="bg-yellow-100 text-yellow-800">{label}</Badge>;
    case "waiting":
      return <Badge className="bg-orange-100 text-orange-800">{label}</Badge>;
    case "cancelled":
      return <Badge variant="secondary">{label}</Badge>;
    default:
      return <Badge className="bg-blue-100 text-blue-800">{label}</Badge>;
  }
}

// 締日情報の型
interface DeadlineInfo {
  providerId: string;
  providerName: string;
  closingDay: number;
  closingDate: string;
  closingDateDisplay: string;
  debitDay: number;
  debitDateDisplay: string;
  isClosed: boolean;
  daysUntilClosing: number;
  canEdit: boolean;
}

// スタッフの型
interface Staff {
  id: string;
  name: string;
  email?: string;
}

export default function DashboardPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [showCompleted, setShowCompleted] = useState(false);
  const [deadlines, setDeadlines] = useState<DeadlineInfo[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [staffList, setStaffList] = useState<Staff[]>([]);
  const [comment, setComment] = useState("");

  useEffect(() => {
    loadTasks();
    loadDeadlines();
    loadStaff();
  }, []);

  async function loadDeadlines() {
    try {
      const data = await apiClient.get<{ deadlines: DeadlineInfo[] }>('/billing/providers/current_deadlines/');
      setDeadlines(data.deadlines || []);
    } catch (error) {
      console.error('Failed to load deadlines:', error);
    }
  }

  async function loadStaff() {
    // TODO: スタッフ一覧APIを実装
    setStaffList([
      { id: "1", name: "山田 太郎", email: "yamada@example.com" },
      { id: "2", name: "佐藤 花子", email: "sato@example.com" },
      { id: "3", name: "鈴木 一郎", email: "suzuki@example.com" },
    ]);
  }

  async function loadTasks() {
    setLoading(true);
    const data = await getTasks();
    setTasks(data);
    setLoading(false);
  }

  // フィルタリングされたタスク
  const filteredTasks = tasks.filter((task) => {
    if (!showCompleted && (task.status === "completed" || task.status === "cancelled")) return false;
    if (filter === "all") return true;
    return task.task_type === filter;
  });

  // 統計
  const newCount = tasks.filter((t) => t.status === "new").length;
  const inProgressCount = tasks.filter((t) => t.status === "in_progress").length;
  const completedCount = tasks.filter((t) => t.status === "completed").length;
  const urgentCount = tasks.filter(
    (t) => (t.priority === "urgent" || t.priority === "high") && t.status !== "completed" && t.status !== "cancelled"
  ).length;

  // タスクのステータスを切り替え
  async function toggleTaskStatus(taskId: string, currentStatus: string) {
    if (currentStatus === "completed") {
      const result = await reopenTask(taskId);
      if (result) {
        loadTasks();
        if (selectedTask?.id === taskId) {
          setSelectedTask(result);
        }
      }
    } else {
      const result = await completeTask(taskId);
      if (result) {
        loadTasks();
        if (selectedTask?.id === taskId) {
          setSelectedTask(result);
        }
      }
    }
  }

  // タスクを選択
  function selectTask(task: Task) {
    setSelectedTask(task);
    setComment("");
  }

  // 担当者を割り当て
  async function assignTask(staffId: string) {
    if (!selectedTask) return;

    const result = await updateTask(selectedTask.id, {
      assigned_to_id: staffId,
      status: selectedTask.status === "new" ? "in_progress" : selectedTask.status,
    });

    if (result) {
      loadTasks();
      setSelectedTask(result);
    }
  }

  // ソースURLに移動
  function goToSource() {
    if (!selectedTask) return;

    // source_typeに基づいてURLを生成
    let url = "";
    switch (selectedTask.source_type) {
      case "bank_account_request":
        url = `/billing/bank-requests?id=${selectedTask.source_id}`;
        break;
      case "suspension_request":
      case "withdrawal_request":
        url = `/students?request=${selectedTask.source_id}`;
        break;
      case "student":
        url = `/students/${selectedTask.student}`;
        break;
      case "guardian":
        url = `/parents/${selectedTask.guardian}`;
        break;
      default:
        if (selectedTask.source_url) {
          url = selectedTask.source_url;
        }
    }

    if (url) {
      window.location.href = url;
    }
  }

  // 日時フォーマット
  function formatDate(dateStr?: string) {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    return date.toLocaleString("ja-JP", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  // 相対時間フォーマット（Gmail風）
  function formatRelativeTime(dateStr?: string) {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return "たった今";
    if (diffMins < 60) return `${diffMins}分前`;
    if (diffHours < 24) return `${diffHours}時間前`;
    if (diffDays < 7) return `${diffDays}日前`;

    // 1週間以上前は日付表示
    return date.toLocaleDateString("ja-JP", {
      month: "short",
      day: "numeric",
    });
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar />

      {/* メインコンテンツ */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左側: タスクリスト */}
        <div className={`${selectedTask ? 'w-1/2 border-r' : 'w-full'} flex flex-col bg-white transition-all`}>
          {/* ヘッダー */}
          <div className="p-4 border-b">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h1 className="text-xl font-bold text-gray-900">作業一覧</h1>
                <p className="text-xs text-gray-500">本日の作業と未完了タスク</p>
              </div>
              <Button size="sm">
                <Plus className="w-4 h-4 mr-1" />
                新規作成
              </Button>
            </div>

            {/* 締日情報 */}
            {deadlines.length > 0 && (
              <div className="flex items-center gap-2 mb-3 overflow-x-auto pb-1">
                <Calendar className="w-4 h-4 text-gray-400 flex-shrink-0" />
                {deadlines.map((deadline) => (
                  <div
                    key={deadline.providerId}
                    className={`flex items-center gap-1 px-2 py-1 rounded text-xs whitespace-nowrap ${
                      deadline.isClosed
                        ? 'bg-gray-100 text-gray-600'
                        : deadline.daysUntilClosing <= 3
                        ? 'bg-red-100 text-red-700'
                        : deadline.daysUntilClosing <= 7
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-green-100 text-green-700'
                    }`}
                  >
                    {deadline.isClosed ? <Lock className="w-3 h-3" /> : <Unlock className="w-3 h-3" />}
                    <span className="font-medium">{deadline.providerName}</span>
                    <span>{deadline.closingDateDisplay}</span>
                    {!deadline.isClosed && deadline.daysUntilClosing > 0 && (
                      <span className="font-bold">あと{deadline.daysUntilClosing}日</span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* 統計 */}
            <div className="flex items-center gap-4 mb-3">
              <div className="flex items-center gap-1">
                <Circle className="w-3 h-3 text-blue-400" />
                <span className="text-xs text-gray-600">新規</span>
                <span className="text-sm font-bold">{newCount}</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-yellow-500" />
                <span className="text-xs text-gray-600">対応中</span>
                <span className="text-sm font-bold">{inProgressCount}</span>
              </div>
              <div className="flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-green-500" />
                <span className="text-xs text-gray-600">完了</span>
                <span className="text-sm font-bold">{completedCount}</span>
              </div>
              {urgentCount > 0 && (
                <div className="flex items-center gap-1 text-red-600">
                  <AlertCircle className="w-3 h-3" />
                  <span className="text-xs">要対応</span>
                  <span className="text-sm font-bold">{urgentCount}</span>
                </div>
              )}
            </div>

            {/* フィルター */}
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <Select value={filter} onValueChange={setFilter}>
                <SelectTrigger className="w-[130px] h-8 text-xs">
                  <SelectValue placeholder="種別" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">すべて</SelectItem>
                  <SelectItem value="bank_account_request">口座申請</SelectItem>
                  <SelectItem value="inquiry">問い合わせ</SelectItem>
                  <SelectItem value="chat">チャット</SelectItem>
                  <SelectItem value="trial_registration">体験登録</SelectItem>
                  <SelectItem value="enrollment">入会申請</SelectItem>
                  <SelectItem value="withdrawal">退会申請</SelectItem>
                  <SelectItem value="suspension">休会申請</SelectItem>
                  <SelectItem value="contract_change">契約変更</SelectItem>
                  <SelectItem value="debit_failure">引落失敗</SelectItem>
                  <SelectItem value="refund_request">返金申請</SelectItem>
                </SelectContent>
              </Select>
              <div className="flex items-center gap-1">
                <Checkbox
                  id="showCompleted"
                  checked={showCompleted}
                  onCheckedChange={(checked) => setShowCompleted(checked === true)}
                />
                <label htmlFor="showCompleted" className="text-xs text-gray-600 cursor-pointer">
                  完了を表示
                </label>
              </div>
            </div>
          </div>

          {/* タスクリスト */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : filteredTasks.length > 0 ? (
              <div className="divide-y">
                {filteredTasks.map((task) => (
                  <div
                    key={task.id}
                    onClick={() => selectTask(task)}
                    className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors ${
                      selectedTask?.id === task.id
                        ? "bg-blue-50 border-l-4 border-l-blue-500"
                        : task.status === "completed"
                        ? "bg-gray-50 opacity-60 hover:bg-gray-100"
                        : task.priority === "urgent" || task.priority === "high"
                        ? "bg-red-50 hover:bg-red-100"
                        : "hover:bg-gray-50"
                    }`}
                  >
                    {/* チェックボックス */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleTaskStatus(task.id, task.status);
                      }}
                      className="flex-shrink-0"
                    >
                      {task.status === "completed" ? (
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                      ) : task.status === "in_progress" ? (
                        <Clock className="w-5 h-5 text-yellow-500" />
                      ) : (
                        <Circle className="w-5 h-5 text-gray-300 hover:text-blue-400" />
                      )}
                    </button>

                    {/* カテゴリアイコン */}
                    <div className={`flex-shrink-0 p-1.5 rounded ${
                      task.task_type === "bank_account_request" ? "bg-purple-100 text-purple-600" :
                      task.task_type === "withdrawal" ? "bg-red-100 text-red-600" :
                      task.task_type === "suspension" ? "bg-orange-100 text-orange-600" :
                      "bg-gray-100 text-gray-600"
                    }`}>
                      {getCategoryIcon(task.task_type, "md")}
                    </div>

                    {/* メインコンテンツ */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium truncate ${
                          task.status === "completed" ? "text-gray-500 line-through" : "text-gray-900"
                        }`}>
                          {task.title}
                        </span>
                        {(task.priority === "urgent" || task.priority === "high") && (
                          <Badge variant="destructive" className="text-[10px] px-1 py-0">
                            {task.priority_display || task.priority}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500">
                        <span>{task.task_type_display}</span>
                        {(task.student_name || task.guardian_name) && (
                          <>
                            <span>•</span>
                            <span>{task.student_name || task.guardian_name}</span>
                          </>
                        )}
                        <span>•</span>
                        <span className="text-gray-400" title={formatDate(task.created_at)}>
                          {formatRelativeTime(task.created_at)}
                        </span>
                      </div>
                    </div>

                    {/* 時刻 */}
                    <div className="flex-shrink-0 text-right" title={formatDate(task.created_at)}>
                      <div className="text-xs font-medium text-gray-600">
                        {task.created_at ? new Date(task.created_at).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" }) : "-"}
                      </div>
                      <div className="text-[10px] text-gray-400">
                        {task.created_at ? new Date(task.created_at).toLocaleDateString("ja-JP", { month: "short", day: "numeric" }) : "-"}
                      </div>
                    </div>

                    <ChevronRight className="w-4 h-4 text-gray-300 flex-shrink-0" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                <CheckCircle2 className="w-12 h-12 mb-3 text-gray-300" />
                <p className="text-sm">作業がありません</p>
              </div>
            )}
          </div>
        </div>

        {/* 右側: 詳細パネル */}
        {selectedTask && (
          <div className="w-1/2 flex flex-col bg-white">
            {/* 詳細ヘッダー */}
            <div className="flex items-center justify-between p-4 border-b">
              <div className="flex items-center gap-2">
                {getStatusBadge(selectedTask.status, selectedTask.status_display)}
                {getPriorityBadge(selectedTask.priority, selectedTask.priority_display)}
              </div>
              <Button variant="ghost" size="sm" onClick={() => setSelectedTask(null)}>
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* 詳細コンテンツ */}
            <div className="flex-1 overflow-y-auto p-4">
              {/* タイトル */}
              <h2 className="text-lg font-bold text-gray-900 mb-2">{selectedTask.title}</h2>

              {/* カテゴリ */}
              <div className="flex items-center gap-2 mb-4">
                <div className={`p-1.5 rounded ${
                  selectedTask.task_type === "bank_account_request" ? "bg-purple-100 text-purple-600" :
                  "bg-gray-100 text-gray-600"
                }`}>
                  {getCategoryIcon(selectedTask.task_type, "md")}
                </div>
                <span className="text-sm text-gray-600">{selectedTask.task_type_display}</span>
              </div>

              {/* 説明 */}
              {selectedTask.description && (
                <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">{selectedTask.description}</p>
                </div>
              )}

              {/* 詳細情報 */}
              <div className="space-y-3 mb-6">
                {selectedTask.student_name && (
                  <div className="flex items-center gap-2 text-sm">
                    <User className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-500">生徒:</span>
                    <span className="font-medium">{selectedTask.student_name}</span>
                  </div>
                )}
                {selectedTask.guardian_name && (
                  <div className="flex items-center gap-2 text-sm">
                    <User className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-500">保護者:</span>
                    <span className="font-medium">{selectedTask.guardian_name}</span>
                  </div>
                )}
                {selectedTask.school_name && (
                  <div className="flex items-center gap-2 text-sm">
                    <Building className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-500">校舎:</span>
                    <span className="font-medium">{selectedTask.school_name}</span>
                  </div>
                )}
                {selectedTask.due_date && (
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-500">期限:</span>
                    <span className="font-medium">{selectedTask.due_date}</span>
                  </div>
                )}
                <div className="flex items-center gap-2 text-sm">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <span className="text-gray-500">作成日時:</span>
                  <span className="font-medium">{formatDate(selectedTask.created_at)}</span>
                </div>
              </div>

              {/* 担当者割り当て */}
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-2">
                  <UserPlus className="w-4 h-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-700">担当者を割り当て</span>
                </div>
                <Select onValueChange={assignTask}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="担当者を選択..." />
                  </SelectTrigger>
                  <SelectContent>
                    {staffList.map((staff) => (
                      <SelectItem key={staff.id} value={staff.id}>
                        {staff.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* ソースリンク */}
              {selectedTask.source_type && (
                <Button
                  variant="outline"
                  className="w-full mb-6"
                  onClick={goToSource}
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  詳細ページを開く
                </Button>
              )}

              {/* コメント入力 */}
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <MessageSquare className="w-4 h-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-700">コメント</span>
                </div>
                <Textarea
                  placeholder="コメントを入力..."
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={3}
                />
              </div>
            </div>

            {/* アクションボタン */}
            <div className="p-4 border-t bg-gray-50 space-y-2">
              {selectedTask.status !== "completed" ? (
                <Button
                  className="w-full"
                  onClick={() => toggleTaskStatus(selectedTask.id, selectedTask.status)}
                >
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  完了にする
                </Button>
              ) : (
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => toggleTaskStatus(selectedTask.id, selectedTask.status)}
                >
                  <Undo2 className="w-4 h-4 mr-2" />
                  再開する
                </Button>
              )}
              {comment && (
                <Button variant="outline" className="w-full">
                  <Send className="w-4 h-4 mr-2" />
                  コメントを送信
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
