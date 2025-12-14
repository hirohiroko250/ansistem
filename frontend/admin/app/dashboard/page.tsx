"use client";

import { useState, useEffect } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
} from "lucide-react";
import { getTasks, completeTask, reopenTask, Task } from "@/lib/api/staff";

// カテゴリーアイコンを取得
function getCategoryIcon(taskType: string) {
  switch (taskType) {
    case "student_registration":
    case "guardian_registration":
      return <User className="w-3 h-3" />;
    case "enrollment":
    case "withdrawal":
    case "contract_change":
      return <FileText className="w-3 h-3" />;
    case "inquiry":
    case "chat":
      return <MessageSquare className="w-3 h-3" />;
    case "trial_registration":
      return <Building className="w-3 h-3" />;
    default:
      return <AlertCircle className="w-3 h-3" />;
  }
}

// カテゴリー名を取得
function getCategoryName(taskType: string, taskTypeDisplay?: string) {
  return taskTypeDisplay || taskType;
}

// 優先度のバッジを取得
function getPriorityBadge(priority: string, priorityDisplay?: string) {
  const label = priorityDisplay || priority;
  switch (priority) {
    case "urgent":
      return <Badge variant="destructive" className="text-[10px] px-1">{label}</Badge>;
    case "high":
      return <Badge variant="destructive" className="text-[10px] px-1">{label}</Badge>;
    case "normal":
      return <Badge variant="default" className="text-[10px] px-1">{label}</Badge>;
    case "low":
      return <Badge variant="secondary" className="text-[10px] px-1">{label}</Badge>;
    default:
      return <Badge variant="secondary" className="text-[10px] px-1">{label}</Badge>;
  }
}

// ステータスアイコンを取得
function getStatusIcon(status: string) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    case "in_progress":
      return <Clock className="w-4 h-4 text-yellow-500" />;
    case "waiting":
      return <Clock className="w-4 h-4 text-orange-500" />;
    case "cancelled":
      return <Circle className="w-4 h-4 text-gray-400" />;
    default:
      return <Circle className="w-4 h-4 text-blue-400" />;
  }
}

export default function DashboardPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [showCompleted, setShowCompleted] = useState(false);

  useEffect(() => {
    loadTasks();
  }, []);

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
      }
    } else {
      const result = await completeTask(taskId);
      if (result) {
        loadTasks();
      }
    }
  }

  return (
    <ThreePaneLayout>
      <div className="p-4 space-y-4 h-full overflow-auto">
        {/* ヘッダー */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">作業一覧</h1>
            <p className="text-sm text-gray-600">本日の作業と未完了タスク</p>
          </div>
          <Button size="sm">
            <Plus className="w-3 h-3 mr-1" />
            追加
          </Button>
        </div>

        {/* 統計カード */}
        <div className="grid grid-cols-4 gap-2">
          <Card className="p-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-600">新規</p>
                <p className="text-xl font-bold text-gray-900">{newCount}</p>
              </div>
              <Circle className="w-5 h-5 text-blue-400" />
            </div>
          </Card>
          <Card className="p-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-600">対応中</p>
                <p className="text-xl font-bold text-yellow-600">{inProgressCount}</p>
              </div>
              <Clock className="w-5 h-5 text-yellow-500" />
            </div>
          </Card>
          <Card className="p-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-600">完了</p>
                <p className="text-xl font-bold text-green-600">{completedCount}</p>
              </div>
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            </div>
          </Card>
          <Card className={`p-2 ${urgentCount > 0 ? "border-red-200 bg-red-50" : ""}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-600">要対応</p>
                <p className="text-xl font-bold text-red-600">{urgentCount}</p>
              </div>
              <AlertCircle className="w-5 h-5 text-red-500" />
            </div>
          </Card>
        </div>

        {/* フィルター */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <Filter className="w-3 h-3 text-gray-500" />
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="w-[120px] h-8 text-xs">
                <SelectValue placeholder="種別" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">すべて</SelectItem>
                <SelectItem value="inquiry">問い合わせ</SelectItem>
                <SelectItem value="enrollment">入会申請</SelectItem>
                <SelectItem value="withdrawal">退会申請</SelectItem>
                <SelectItem value="trial_registration">体験登録</SelectItem>
                <SelectItem value="contract_change">契約変更</SelectItem>
                <SelectItem value="chat">チャット</SelectItem>
                <SelectItem value="other">その他</SelectItem>
              </SelectContent>
            </Select>
          </div>
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

        {/* 作業リスト */}
        <Card>
          <CardHeader className="py-2 px-3">
            <CardTitle className="text-sm">作業リスト ({filteredTasks.length}件)</CardTitle>
          </CardHeader>
          <CardContent className="p-2">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : filteredTasks.length > 0 ? (
              <div className="space-y-1">
                {filteredTasks.map((task) => (
                  <div
                    key={task.id}
                    className={`flex items-start gap-2 p-2 rounded border transition-colors ${
                      task.status === "completed"
                        ? "bg-gray-50 opacity-60"
                        : task.priority === "urgent" || task.priority === "high"
                        ? "bg-red-50 border-red-200"
                        : "bg-white hover:bg-gray-50"
                    }`}
                  >
                    {/* チェックボックス */}
                    <button
                      onClick={() => toggleTaskStatus(task.id, task.status)}
                      className="mt-0.5 flex-shrink-0"
                    >
                      {getStatusIcon(task.status)}
                    </button>

                    {/* メインコンテンツ */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-1 mb-0.5">
                        <h4
                          className={`text-sm font-medium truncate ${
                            task.status === "completed"
                              ? "text-gray-500 line-through"
                              : "text-gray-900"
                          }`}
                        >
                          {task.title}
                        </h4>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          {getPriorityBadge(task.priority, task.priority_display)}
                        </div>
                      </div>
                      {task.description && (
                        <p className="text-xs text-gray-600 truncate mb-0.5">{task.description}</p>
                      )}
                      <div className="flex items-center gap-2 text-[10px] text-gray-500 flex-wrap">
                        <span className="flex items-center gap-0.5">
                          {getCategoryIcon(task.task_type)}
                          {getCategoryName(task.task_type, task.task_type_display)}
                        </span>
                        {task.due_date && (
                          <span className="flex items-center gap-0.5">
                            <Clock className="w-2.5 h-2.5" />
                            {task.due_date}
                          </span>
                        )}
                        {task.student_name && (
                          <span className="flex items-center gap-0.5">
                            <User className="w-2.5 h-2.5" />
                            {task.student_name}
                          </span>
                        )}
                        {task.guardian_name && !task.student_name && (
                          <span className="flex items-center gap-0.5">
                            <User className="w-2.5 h-2.5" />
                            {task.guardian_name}
                          </span>
                        )}
                        {task.school_name && (
                          <span className="flex items-center gap-0.5">
                            <Building className="w-2.5 h-2.5" />
                            {task.school_name}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">作業がありません</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </ThreePaneLayout>
  );
}
