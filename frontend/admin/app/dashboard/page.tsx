"use client";

import React, { useState, useEffect, useMemo } from "react";
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
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
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
  ChevronDown,
  ExternalLink,
  UserPlus,
  Send,
  Landmark,
  ChevronsUpDown,
  Check,
  ArrowRight,
  EyeOff,
} from "lucide-react";
import { getTasks, completeTask, reopenTask, updateTask, Task, getTaskComments, createTaskComment, TaskComment } from "@/lib/api/staff";
import apiClient from "@/lib/api/client";
import { Sidebar } from "@/components/layout/Sidebar";
import { cn } from "@/lib/utils";
import {
  getOrCreateChannelForGuardian,
  getMessages,
  sendMessage,
  type Message as ChatMessage,
  type Channel,
} from "@/lib/api/chat";

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
  position?: string;
}

// グループ化されたスタッフの型
interface StaffGroup {
  type: 'school' | 'brand';
  id: string;
  name: string;
  employees: Staff[];
}

interface GroupedStaffResponse {
  // snake_case (Python) or camelCase (JS) both supported
  school_groups?: StaffGroup[];
  schoolGroups?: StaffGroup[];
  brand_groups?: StaffGroup[];
  brandGroups?: StaffGroup[];
  unassigned: Staff[];
  all_employees?: Array<{
    id: string;
    full_name?: string;
    fullName?: string;
    email?: string;
    position_name?: string;
    positionName?: string;
  }>;
  allEmployees?: Array<{
    id: string;
    full_name?: string;
    fullName?: string;
    email?: string;
    position_name?: string;
    positionName?: string;
  }>;
}

export default function DashboardPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [showCompleted, setShowCompleted] = useState(false);
  const [deadlines, setDeadlines] = useState<DeadlineInfo[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [staffList, setStaffList] = useState<Staff[]>([]);
  const [staffGroups, setStaffGroups] = useState<StaffGroup[]>([]);
  const [unassignedStaff, setUnassignedStaff] = useState<Staff[]>([]);
  const [schools, setSchools] = useState<Array<{id: string; name: string}>>([]);
  const [brands, setBrands] = useState<Array<{id: string; name: string}>>([]);
  const [selectedSchool, setSelectedSchool] = useState<string>("");  // 選択された校舎
  const [selectedBrand, setSelectedBrand] = useState<string>("");   // 選択されたブランド
  const [selectedStaff, setSelectedStaff] = useState<string>("");   // 選択された担当者
  const [comment, setComment] = useState("");
  const [currentUser, setCurrentUser] = useState<{id: string; name: string} | null>(null);
  const [isAnonymous, setIsAnonymous] = useState(false);

  // Combobox open states
  const [schoolOpen, setSchoolOpen] = useState(false);
  const [brandOpen, setBrandOpen] = useState(false);
  const [staffOpen, setStaffOpen] = useState(false);

  // タスク展開状態（コメント表示用）
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());
  const [taskCommentsCache, setTaskCommentsCache] = useState<Record<string, TaskComment[]>>({});

  // チャット関連
  const [chatChannel, setChatChannel] = useState<Channel | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [replyMessage, setReplyMessage] = useState("");
  const [sendingReply, setSendingReply] = useState(false);
  const [detailTab, setDetailTab] = useState<"info" | "chat" | "assign" | "comments">("info");

  // タスクコメント関連
  const [taskComments, setTaskComments] = useState<TaskComment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [newComment, setNewComment] = useState("");
  const [sendingComment, setSendingComment] = useState(false);

  // 承認待ち社員
  const [pendingEmployees, setPendingEmployees] = useState<any[]>([]);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);

  useEffect(() => {
    loadTasks();
    loadDeadlines();
    loadStaff();
    loadSchoolsAndBrands();
    loadCurrentUser();
    loadPendingEmployees();
  }, []);

  async function loadPendingEmployees() {
    try {
      setPendingLoading(true);
      console.log('[Pending] Loading pending employees...');
      const data = await apiClient.get<any[]>('/tenants/employees/pending/');
      console.log('[Pending] API Response:', data);
      setPendingEmployees(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('[Pending] Failed to load pending employees:', error);
      setPendingEmployees([]);
    } finally {
      setPendingLoading(false);
    }
  }

  async function approveEmployee(employeeId: string) {
    try {
      setApprovingId(employeeId);
      await apiClient.post(`/tenants/employees/${employeeId}/approve/`);
      // リストから削除
      setPendingEmployees(prev => prev.filter(e => e.id !== employeeId));
      // スタッフリストを再読み込み
      loadStaff();
    } catch (error) {
      console.error('Failed to approve employee:', error);
      alert('承認に失敗しました');
    } finally {
      setApprovingId(null);
    }
  }

  async function rejectEmployee(employeeId: string) {
    if (!confirm('この社員登録を却下しますか？この操作は取り消せません。')) return;

    try {
      setApprovingId(employeeId);
      await apiClient.post(`/tenants/employees/${employeeId}/reject/`);
      // リストから削除
      setPendingEmployees(prev => prev.filter(e => e.id !== employeeId));
    } catch (error) {
      console.error('Failed to reject employee:', error);
      alert('却下に失敗しました');
    } finally {
      setApprovingId(null);
    }
  }

  async function loadCurrentUser() {
    try {
      const response = await apiClient.get<any>('/auth/me/');
      const user = response.user || response;
      setCurrentUser({
        id: user.id,
        name: user.fullName || user.full_name || user.username || user.email || '自分',
      });
    } catch (error) {
      console.error('Failed to load current user:', error);
      // フォールバック
      setCurrentUser({ id: '', name: '自分' });
    }
  }

  async function loadSchoolsAndBrands() {
    try {
      // 校舎一覧
      const schoolsData = await apiClient.get<any>('/schools/schools/');
      console.log('[Schools] API Response:', schoolsData);
      const schoolsList = schoolsData.data || schoolsData.results || (Array.isArray(schoolsData) ? schoolsData : []);
      setSchools(schoolsList.map((s: any) => ({ id: s.id, name: s.schoolName || s.school_name })));

      // ブランド一覧
      const brandsData = await apiClient.get<any>('/schools/brands/');
      console.log('[Brands] API Response:', brandsData);
      const brandsList = brandsData.data || brandsData.results || (Array.isArray(brandsData) ? brandsData : []);
      setBrands(brandsList.map((b: any) => ({ id: b.id, name: b.brandName || b.brand_name })));
    } catch (error) {
      console.error('Failed to load schools/brands:', error);
    }
  }

  async function loadDeadlines() {
    try {
      const data = await apiClient.get<{ deadlines: DeadlineInfo[] }>('/billing/providers/current_deadlines/');
      setDeadlines(data.deadlines || []);
    } catch (error) {
      console.error('Failed to load deadlines:', error);
    }
  }

  async function loadStaff() {
    try {
      const data = await apiClient.get<GroupedStaffResponse>('/tenants/employees/grouped/');
      console.log('[Staff] API Response:', data);

      // camelCase or snake_case どちらにも対応
      const allEmployees = data.all_employees || data.allEmployees || [];
      const schoolGroups = data.school_groups || data.schoolGroups || [];
      const brandGroups = data.brand_groups || data.brandGroups || [];
      const unassigned = data.unassigned || [];

      // 全スタッフリストを設定
      if (allEmployees.length > 0) {
        const allStaff: Staff[] = allEmployees.map(e => ({
          id: String(e.id),  // 確実に文字列に変換
          name: e.full_name || e.fullName || '',
          email: e.email,
          position: e.position_name || e.positionName,
        }));
        console.log('[Staff] Loaded staff list:', allStaff.length, 'First:', allStaff[0]);
        setStaffList(allStaff);
      } else {
        console.warn('[Staff] No employees in response');
        setStaffList([]);
      }

      // グループ化されたデータを設定（校舎 + ブランド）
      const groups: StaffGroup[] = [...schoolGroups, ...brandGroups];
      setStaffGroups(groups);

      // 未割り当てスタッフを設定
      setUnassignedStaff(unassigned);
    } catch (error) {
      console.error('Failed to load staff:', error);
      setStaffList([]);
      setStaffGroups([]);
      setUnassignedStaff([]);
    }
  }

  async function loadTasks() {
    setLoading(true);
    const rawData = await getTasks();
    // APIがcamelCaseで返すので、snake_caseにも対応
    const data = rawData.map(t => ({
      ...t,
      // camelCase -> snake_case の正規化
      assigned_to_id: t.assigned_to_id || (t as any).assignedToId,
      assigned_to_name: t.assigned_to_name || (t as any).assignedToName,
      created_by_id: t.created_by_id || (t as any).createdById,
      student_no: t.student_no || (t as any).studentNo,
      student_name: t.student_name || (t as any).studentName,
      guardian_no: t.guardian_no || (t as any).guardianNo,
      guardian_name: t.guardian_name || (t as any).guardianName,
      created_at: t.created_at || (t as any).createdAt,
      school_name: t.school_name || (t as any).schoolName,
      brand_name: t.brand_name || (t as any).brandName,
    }));
    // 割り当て済みタスクを確認
    const assignedTasks = data.filter(t => t.assigned_to_id);
    console.log('[Tasks] Loaded:', data.length, 'tasks, Assigned:', assignedTasks.length);
    if (assignedTasks.length > 0) {
      console.log('[Tasks] First assigned task:', {
        id: assignedTasks[0].id,
        title: assignedTasks[0].title,
        assigned_to_id: assignedTasks[0].assigned_to_id,
        assigned_to_name: assignedTasks[0].assigned_to_name,
      });
    }
    setTasks(data);
    setLoading(false);
  }

  // 経過時間を計算（時間単位）
  function getElapsedHours(createdAt?: string): number {
    if (!createdAt) return 0;
    const created = new Date(createdAt);
    if (isNaN(created.getTime())) return 0;
    const now = new Date();
    return (now.getTime() - created.getTime()) / (1000 * 60 * 60);
  }

  // 経過時間アラートレベルを取得
  function getElapsedAlertLevel(task: Task): 'none' | 'warning' | 'danger' {
    if (task.status === 'completed' || task.status === 'cancelled') return 'none';
    const hours = getElapsedHours(task.created_at);
    if (hours >= 48) return 'danger';  // 48時間以上
    if (hours >= 24) return 'warning'; // 24時間以上
    return 'none';
  }

  // フィルタリングされたタスク
  const filteredTasks = tasks.filter((task) => {
    if (!showCompleted && (task.status === "completed" || task.status === "cancelled")) return false;
    // カテゴリフィルター
    if (filter !== "all" && task.task_type !== filter) return false;
    // 校舎フィルター
    if (selectedSchool && selectedSchool !== "all" && task.school !== selectedSchool) return false;
    // ブランドフィルター
    if (selectedBrand && selectedBrand !== "all" && task.brand !== selectedBrand) return false;
    return true;
  });

  // 統計
  const newCount = tasks.filter((t) => t.status === "new").length;
  const inProgressCount = tasks.filter((t) => t.status === "in_progress").length;
  const completedCount = tasks.filter((t) => t.status === "completed").length;
  const urgentCount = tasks.filter(
    (t) => (t.priority === "urgent" || t.priority === "high") && t.status !== "completed" && t.status !== "cancelled"
  ).length;
  // 経過時間アラートカウント
  const warningCount = tasks.filter((t) => getElapsedAlertLevel(t) === 'warning').length;
  const dangerCount = tasks.filter((t) => getElapsedAlertLevel(t) === 'danger').length;

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
  async function selectTask(task: Task) {
    setSelectedTask(task);
    setComment("");
    setReplyMessage("");
    setNewComment("");
    setDetailTab("info");
    setChatChannel(null);
    setChatMessages([]);
    setTaskComments([]);
    // 割り当て用の選択をリセット
    setSelectedSchool("");
    setSelectedBrand("");
    setSelectedStaff(task.assigned_to_id || "");

    // コメント履歴を読み込む
    loadTaskComments(task.id);

    // 保護者がいる場合はチャット履歴を読み込む
    if (task.guardian) {
      loadChatHistory(task.guardian);
    }
  }

  // タスクコメントを読み込む
  async function loadTaskComments(taskId: string) {
    try {
      setCommentsLoading(true);
      const comments = await getTaskComments(taskId);
      setTaskComments(comments);
    } catch (error) {
      console.error('Failed to load task comments:', error);
    } finally {
      setCommentsLoading(false);
    }
  }

  // タスクの展開/折りたたみを切り替え
  async function toggleTaskExpand(taskId: string, e: React.MouseEvent) {
    e.stopPropagation();
    const newExpanded = new Set(expandedTasks);
    if (newExpanded.has(taskId)) {
      newExpanded.delete(taskId);
    } else {
      newExpanded.add(taskId);
      // コメントがキャッシュされていない場合は読み込む
      if (!taskCommentsCache[taskId]) {
        try {
          const comments = await getTaskComments(taskId);
          setTaskCommentsCache(prev => ({ ...prev, [taskId]: comments }));
        } catch (error) {
          console.error('Failed to load comments:', error);
        }
      }
    }
    setExpandedTasks(newExpanded);
  }

  // コメントを投稿
  async function handleSubmitComment() {
    console.log('[Comment] Submit clicked', { selectedTask: selectedTask?.id, newComment, currentUser });
    if (!selectedTask || !newComment.trim()) {
      console.warn('[Comment] Validation failed', { selectedTask: !!selectedTask, newComment: newComment?.trim() });
      return;
    }

    try {
      setSendingComment(true);
      console.log('[Comment] Creating comment...', {
        task: selectedTask.id,
        comment: newComment.trim(),
        commented_by_id: currentUser?.id,
      });
      const comment = await createTaskComment({
        task: selectedTask.id,
        comment: newComment.trim(),
        commented_by_id: currentUser?.id,
        is_internal: false,
      });
      console.log('[Comment] Result:', comment);

      if (comment) {
        setTaskComments([...taskComments, comment]);
        setNewComment("");
      } else {
        console.error('[Comment] Comment creation returned null');
        alert('コメントの作成に失敗しました');
      }
    } catch (error) {
      console.error('[Comment] Failed to create comment:', error);
      alert('コメントの作成に失敗しました');
    } finally {
      setSendingComment(false);
    }
  }

  // チャット履歴を読み込む
  async function loadChatHistory(guardianId: string) {
    try {
      setChatLoading(true);
      const channel = await getOrCreateChannelForGuardian(guardianId);
      setChatChannel(channel);

      if (channel?.id) {
        const response = await getMessages(channel.id, { pageSize: 50 });
        const messages = response?.data || response?.results || [];
        // 古い順に並べ替え
        setChatMessages(messages.reverse());
      }
    } catch (error) {
      console.error("Failed to load chat history:", error);
    } finally {
      setChatLoading(false);
    }
  }

  // チャットメッセージを送信
  async function handleSendReply() {
    if (!chatChannel || !replyMessage.trim() || sendingReply) return;

    try {
      setSendingReply(true);
      await sendMessage({
        channelId: chatChannel.id,
        content: replyMessage.trim(),
        messageType: "text",
      });

      // メッセージリストを更新
      if (chatChannel.id) {
        const response = await getMessages(chatChannel.id, { pageSize: 50 });
        const messages = response?.data || response?.results || [];
        setChatMessages(messages.reverse());
      }

      setReplyMessage("");
    } catch (error) {
      console.error("Failed to send reply:", error);
      alert("メッセージの送信に失敗しました");
    } finally {
      setSendingReply(false);
    }
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
    if (isNaN(date.getTime())) return "";
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
    if (isNaN(date.getTime())) return "";
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

            {/* 承認待ち社員 */}
            {pendingEmployees.length > 0 && (
              <div className="mb-3 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <UserPlus className="w-4 h-4 text-orange-600" />
                  <span className="text-sm font-medium text-orange-800">
                    承認待ち社員 ({pendingEmployees.length}件)
                  </span>
                </div>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {pendingEmployees.map((emp) => (
                    <div
                      key={emp.id}
                      className="flex items-center justify-between bg-white p-2 rounded border border-orange-100"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center">
                          <User className="w-4 h-4 text-orange-600" />
                        </div>
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {emp.full_name || emp.fullName}
                          </div>
                          <div className="text-xs text-gray-500">
                            {emp.department} {emp.position_name || emp.positionName ? `/ ${emp.position_name || emp.positionName}` : ''}
                            {emp.email && <span className="ml-2">{emp.email}</span>}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs text-red-600 border-red-200 hover:bg-red-50"
                          onClick={() => rejectEmployee(emp.id)}
                          disabled={approvingId === emp.id}
                        >
                          <X className="w-3 h-3 mr-1" />
                          却下
                        </Button>
                        <Button
                          size="sm"
                          className="h-7 text-xs bg-green-600 hover:bg-green-700"
                          onClick={() => approveEmployee(emp.id)}
                          disabled={approvingId === emp.id}
                        >
                          {approvingId === emp.id ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <>
                              <Check className="w-3 h-3 mr-1" />
                              承認
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
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
              {dangerCount > 0 && (
                <div className="flex items-center gap-1 text-red-600">
                  <Clock className="w-3 h-3" />
                  <span className="text-xs">48h超</span>
                  <span className="text-sm font-bold animate-pulse">{dangerCount}</span>
                </div>
              )}
              {warningCount > 0 && (
                <div className="flex items-center gap-1 text-yellow-600">
                  <Clock className="w-3 h-3" />
                  <span className="text-xs">24h超</span>
                  <span className="text-sm font-bold">{warningCount}</span>
                </div>
              )}
            </div>

            {/* フィルター */}
            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="w-4 h-4 text-gray-400" />
              {/* カテゴリフィルター */}
              <Select value={filter} onValueChange={setFilter}>
                <SelectTrigger className="w-[140px] h-8 text-xs">
                  <SelectValue placeholder="カテゴリ" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">すべて</SelectItem>
                  <SelectItem value="customer_inquiry">客問い合わせ</SelectItem>
                  <SelectItem value="inquiry">問い合わせ</SelectItem>
                  <SelectItem value="chat">チャット</SelectItem>
                  <SelectItem value="trial_registration">体験登録</SelectItem>
                  <SelectItem value="enrollment">入会申請</SelectItem>
                  <SelectItem value="withdrawal">退会</SelectItem>
                  <SelectItem value="suspension">休会</SelectItem>
                  <SelectItem value="contract_change">契約変更</SelectItem>
                  <SelectItem value="tuition_operation">授業料操作</SelectItem>
                  <SelectItem value="debit_failure">引落失敗</SelectItem>
                  <SelectItem value="refund_request">返金申請</SelectItem>
                  <SelectItem value="bank_account_request">口座申請</SelectItem>
                  <SelectItem value="event_registration">イベント申し込み</SelectItem>
                  <SelectItem value="referral">友人紹介</SelectItem>
                  <SelectItem value="staff_registration">社員登録</SelectItem>
                </SelectContent>
              </Select>
              {/* 校舎フィルター */}
              <Select value={selectedSchool} onValueChange={setSelectedSchool}>
                <SelectTrigger className="w-[120px] h-8 text-xs">
                  <SelectValue placeholder="校舎" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全校舎</SelectItem>
                  {schools.map((school) => (
                    <SelectItem key={school.id} value={school.id}>
                      {school.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {/* ブランドフィルター */}
              <Select value={selectedBrand} onValueChange={setSelectedBrand}>
                <SelectTrigger className="w-[120px] h-8 text-xs">
                  <SelectValue placeholder="ブランド" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全ブランド</SelectItem>
                  {brands.map((brand) => (
                    <SelectItem key={brand.id} value={brand.id}>
                      {brand.name}
                    </SelectItem>
                  ))}
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

          {/* タスクリスト（テーブル形式） */}
          <div className="flex-1 overflow-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : filteredTasks.length > 0 ? (
              <table className="min-w-full text-xs">
                <thead className="bg-gray-50 border-b sticky top-0 z-10">
                  <tr>
                    <th className="px-1 py-2 text-left font-medium text-gray-500 whitespace-nowrap w-6"></th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap">No.</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap">登録日時</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap">状態</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap min-w-[120px]">担当者</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap">カテゴリー</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap">ブランド</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap min-w-[180px]">お問合せ内容</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap min-w-[120px]">件名</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap">生徒ID</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap">生徒名</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap">保護者ID</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap">保護者名</th>
                    <th className="px-2 py-2 text-left font-medium text-gray-500 whitespace-nowrap">校舎</th>
                  </tr>
                </thead>
                <tbody className="bg-white">
                  {filteredTasks.map((task, index) => {
                    const statusClass = task.status === "completed"
                      ? "bg-green-100 text-green-800 border-green-300"
                      : task.status === "in_progress"
                      ? "bg-yellow-100 text-yellow-800 border-yellow-300"
                      : "bg-red-100 text-red-800 border-red-300";
                    const isExpanded = expandedTasks.has(task.id);
                    const cachedComments = taskCommentsCache[task.id] || [];

                    // 担当者表示用のデバッグ - assigned_to_idがあるかを確認
                    const hasAssignee = task.assigned_to_id && task.assigned_to_id !== '';
                    const assigneeName = hasAssignee
                      ? (task.assigned_to_name || staffList.find(s => String(s.id) === String(task.assigned_to_id))?.name || '担当者')
                      : '未割当て';

                    return (
                      <React.Fragment key={task.id}>
                        <tr
                          onClick={() => selectTask(task)}
                          className={cn(
                            "hover:bg-blue-50 cursor-pointer transition-colors border-b border-gray-200",
                            selectedTask?.id === task.id && "bg-blue-100",
                            task.status === "completed" && "opacity-60",
                            (task.priority === "urgent" || task.priority === "high") && task.status !== "completed" && "bg-red-50",
                            isExpanded && "border-b-0"
                          )}
                        >
                          <td className="px-1 py-2 whitespace-nowrap">
                            <button
                              onClick={(e) => toggleTaskExpand(task.id, e)}
                              className="p-1 hover:bg-gray-200 rounded transition-colors"
                            >
                              <ChevronDown className={cn("w-4 h-4 text-gray-500 transition-transform", isExpanded && "rotate-180")} />
                            </button>
                          </td>
                          <td className="px-2 py-2 whitespace-nowrap text-gray-900">{index + 1}</td>
                        <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                          {task.created_at && !isNaN(new Date(task.created_at).getTime())
                            ? new Date(task.created_at).toLocaleDateString("ja-JP", { year: "numeric", month: "2-digit", day: "2-digit" })
                            : "---"}
                          {" "}
                          {task.created_at && !isNaN(new Date(task.created_at).getTime())
                            ? new Date(task.created_at).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })
                            : ""}
                        </td>
                        <td className="px-2 py-2 whitespace-nowrap">
                          <div className="flex items-center gap-1">
                            <Badge variant="outline" className={cn("text-[10px]", statusClass)}>
                              {task.status_display || (task.status === "completed" ? "完了" : task.status === "in_progress" ? "対応中" : "未対応")}
                            </Badge>
                            {/* 経過時間アラート */}
                            {(() => {
                              const alertLevel = getElapsedAlertLevel(task);
                              const hours = Math.floor(getElapsedHours(task.created_at));
                              if (alertLevel === 'danger') {
                                return (
                                  <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-[10px] font-medium animate-pulse" title={`${hours}時間経過`}>
                                    <AlertCircle className="w-3 h-3" />
                                    {hours}h
                                  </span>
                                );
                              }
                              if (alertLevel === 'warning') {
                                return (
                                  <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded text-[10px] font-medium" title={`${hours}時間経過`}>
                                    <Clock className="w-3 h-3" />
                                    {hours}h
                                  </span>
                                );
                              }
                              return null;
                            })()}
                          </div>
                        </td>
                        <td className="px-2 py-2 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                          <Select
                            value={hasAssignee ? String(task.assigned_to_id) : "__none__"}
                            onValueChange={async (value) => {
                              if (!task.id) {
                                alert('タスクIDが見つかりません');
                                return;
                              }
                              console.log('[Table Select] Value changed:', value, 'for task:', task.id);
                              const actualValue = value === "__none__" ? undefined : value;

                              // 即座にUIを更新（楽観的更新）
                              const staffName = actualValue ? staffList.find(s => String(s.id) === String(actualValue))?.name : undefined;
                              setTasks(prev => prev.map(t => t.id === task.id ? {
                                ...t,
                                assigned_to_id: actualValue,
                                assigned_to_name: staffName,
                                status: t.status === "new" && actualValue ? "in_progress" : t.status,
                              } : t));

                              const result = await updateTask(task.id, {
                                assigned_to_id: actualValue,
                                status: task.status === "new" && actualValue ? "in_progress" : task.status,
                              });
                              console.log('[Table Select] Update result:', result);
                              if (result) {
                                // APIレスポンスを正規化してから状態を更新
                                const normalizedResult = {
                                  ...result,
                                  assigned_to_id: result.assigned_to_id || (result as any).assignedToId,
                                  assigned_to_name: result.assigned_to_name || (result as any).assignedToName,
                                };
                                setTasks(prev => prev.map(t => t.id === task.id ? normalizedResult : t));
                              } else {
                                // エラー時は元に戻す
                                loadTasks();
                              }
                            }}
                          >
                            <SelectTrigger className="h-7 text-xs w-[110px] border-dashed">
                              <span className="truncate">{assigneeName}</span>
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="__none__">未割当て</SelectItem>
                              {staffList.map((staff) => (
                                <SelectItem key={staff.id} value={String(staff.id)}>
                                  {staff.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </td>
                        <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                          {task.category_name || task.task_type_display || task.task_type || "---"}
                        </td>
                        <td className="px-2 py-2 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                          <Select
                            value={task.brand || "__none__"}
                            onValueChange={async (value) => {
                              const actualValue = value === "__none__" ? undefined : value;
                              const result = await updateTask(task.id, { brand: actualValue });
                              if (result) loadTasks();
                            }}
                          >
                            <SelectTrigger className="h-7 text-xs w-[100px] border-dashed">
                              <SelectValue placeholder="---" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="__none__">---</SelectItem>
                              {brands.map((brand) => (
                                <SelectItem key={brand.id} value={brand.id}>
                                  {brand.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </td>
                        <td className="px-2 py-2 text-gray-600 max-w-[250px] truncate" title={task.description}>
                          {task.description || "---"}
                        </td>
                        <td className="px-2 py-2 text-gray-900 font-medium max-w-[180px] truncate" title={task.title}>
                          {task.title}
                        </td>
                        <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                          {task.student_no || "---"}
                        </td>
                        <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                          {task.student_name || "---"}
                        </td>
                        <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                          {task.guardian_no || "---"}
                        </td>
                        <td className="px-2 py-2 whitespace-nowrap text-gray-600">
                          {task.guardian_name || "---"}
                        </td>
                        <td className="px-2 py-2 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                          <Select
                            value={task.school || "__none__"}
                            onValueChange={async (value) => {
                              const actualValue = value === "__none__" ? undefined : value;
                              const result = await updateTask(task.id, { school: actualValue });
                              if (result) loadTasks();
                            }}
                          >
                            <SelectTrigger className="h-7 text-xs w-[100px] border-dashed">
                              <SelectValue placeholder="---" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="__none__">---</SelectItem>
                              {schools.map((school) => (
                                <SelectItem key={school.id} value={school.id}>
                                  {school.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </td>
                        </tr>
                        {/* 展開時のコメント行 */}
                        {isExpanded && (
                          <tr className="bg-gray-50 border-b border-gray-200">
                            <td colSpan={14} className="px-4 py-3">
                              <div className="ml-6 pl-4 border-l-2 border-blue-200">
                                {cachedComments.length > 0 ? (
                                  <div className="space-y-2">
                                    {cachedComments.map((comment) => {
                                      const isAssignment = comment.comment.includes("に割り当て】");
                                      return (
                                        <div key={comment.id} className="flex gap-3 items-start">
                                          <div className={cn(
                                            "w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-medium flex-shrink-0",
                                            isAssignment ? "bg-blue-500 text-white" : "bg-gray-200 text-gray-600"
                                          )}>
                                            {isAssignment ? <UserPlus className="w-3 h-3" /> : (comment.commented_by_name?.charAt(0) || "?")}
                                          </div>
                                          <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 text-xs">
                                              <span className="font-medium text-gray-700">
                                                {comment.commented_by_name || "システム"}
                                              </span>
                                              <span className="text-gray-400">
                                                {comment.created_at && !isNaN(new Date(comment.created_at).getTime())
                                                  ? new Date(comment.created_at).toLocaleString("ja-JP", {
                                                      month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit"
                                                    })
                                                  : ""}
                                              </span>
                                            </div>
                                            <div className={cn(
                                              "mt-1 text-xs p-2 rounded",
                                              isAssignment ? "bg-blue-50 text-blue-700" : "bg-white text-gray-600"
                                            )}>
                                              {comment.comment.split("\n").map((line, i) => (
                                                <div key={i}>{line}</div>
                                              ))}
                                            </div>
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  <div className="text-xs text-gray-400 py-2">
                                    対応履歴がありません
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
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

            {/* タイトル */}
            <div className="p-4 border-b">
              <h2 className="text-lg font-bold text-gray-900 mb-1">{selectedTask.title}</h2>
              <div className="flex items-center gap-2">
                <div className={`p-1 rounded ${
                  selectedTask.task_type === "bank_account_request" ? "bg-purple-100 text-purple-600" :
                  "bg-gray-100 text-gray-600"
                }`}>
                  {getCategoryIcon(selectedTask.task_type, "sm")}
                </div>
                <span className="text-xs text-gray-600">{selectedTask.task_type_display}</span>
                <span className="text-xs text-gray-400">•</span>
                <span className="text-xs text-gray-400">{formatDate(selectedTask.created_at)}</span>
              </div>
            </div>

            {/* タブ */}
            <div className="flex border-b">
              <button
                onClick={() => setDetailTab("info")}
                className={`flex-1 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  detailTab === "info"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                <FileText className="w-4 h-4 inline mr-1" />
                詳細
              </button>
              {selectedTask.guardian && (
                <button
                  onClick={() => setDetailTab("chat")}
                  className={`flex-1 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    detailTab === "chat"
                      ? "border-blue-500 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  }`}
                >
                  <MessageSquare className="w-4 h-4 inline mr-1" />
                  チャット
                  {chatMessages.length > 0 && (
                    <Badge variant="secondary" className="ml-1 text-[10px]">{chatMessages.length}</Badge>
                  )}
                </button>
              )}
              <button
                onClick={() => setDetailTab("assign")}
                className={`flex-1 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  detailTab === "assign"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                <UserPlus className="w-4 h-4 inline mr-1" />
                割り当て
              </button>
              <button
                onClick={() => setDetailTab("comments")}
                className={`flex-1 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  detailTab === "comments"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                <MessageSquare className="w-4 h-4 inline mr-1" />
                コメント
                {taskComments.length > 0 && (
                  <Badge variant="secondary" className="ml-1 text-[10px]">{taskComments.length}</Badge>
                )}
              </button>
            </div>

            {/* 詳細コンテンツ */}
            <div className="flex-1 overflow-y-auto p-4">
              {/* 情報タブ */}
              {detailTab === "info" && (
                <>
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
                    {selectedTask.assigned_to_name && (
                      <div className="flex items-center gap-2 text-sm">
                        <User className="w-4 h-4 text-blue-400" />
                        <span className="text-gray-500">担当者:</span>
                        <span className="font-medium text-blue-600">{selectedTask.assigned_to_name}</span>
                      </div>
                    )}
                  </div>

                  {/* ソースリンク */}
                  {selectedTask.source_type && (
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={goToSource}
                    >
                      <ExternalLink className="w-4 h-4 mr-2" />
                      詳細ページを開く
                    </Button>
                  )}
                </>
              )}

              {/* チャットタブ */}
              {detailTab === "chat" && selectedTask.guardian && (
                <div className="flex flex-col h-full">
                  {chatLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                    </div>
                  ) : (
                    <>
                      {/* メッセージ履歴 */}
                      <div className="flex-1 overflow-y-auto space-y-3 mb-4" style={{ maxHeight: "300px" }}>
                        {chatMessages.length > 0 ? (
                          chatMessages.map((msg) => (
                            <div
                              key={msg.id}
                              className={`flex ${msg.senderGuardian ? "justify-start" : "justify-end"}`}
                            >
                              <div
                                className={`max-w-[80%] p-3 rounded-lg ${
                                  msg.senderGuardian
                                    ? "bg-gray-100 text-gray-800"
                                    : "bg-blue-500 text-white"
                                }`}
                              >
                                <div className="text-xs opacity-70 mb-1">
                                  {msg.senderGuardianName || msg.senderName || "スタッフ"}
                                  <span className="ml-2">
                                    {msg.createdAt && !isNaN(new Date(msg.createdAt).getTime())
                                      ? new Date(msg.createdAt).toLocaleString("ja-JP", {
                                          month: "numeric",
                                          day: "numeric",
                                          hour: "2-digit",
                                          minute: "2-digit",
                                        })
                                      : ""}
                                  </span>
                                </div>
                                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="text-center text-gray-500 py-8">
                            <MessageSquare className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                            <p className="text-sm">メッセージ履歴がありません</p>
                          </div>
                        )}
                      </div>

                      {/* 返信入力 */}
                      <div className="border-t pt-3">
                        <Textarea
                          placeholder="保護者へメッセージを送信..."
                          value={replyMessage}
                          onChange={(e) => setReplyMessage(e.target.value)}
                          rows={3}
                          className="text-sm mb-2"
                        />
                        <Button
                          className="w-full"
                          onClick={handleSendReply}
                          disabled={!replyMessage.trim() || sendingReply}
                        >
                          {sendingReply ? (
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          ) : (
                            <Send className="w-4 h-4 mr-2" />
                          )}
                          送信
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* 割り当てタブ */}
              {detailTab === "assign" && (
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <UserPlus className="w-4 h-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-700">担当者を割り当て</span>
                </div>

                {/* 校舎選択（検索可能） */}
                <div className="mb-2">
                  <Popover open={schoolOpen} onOpenChange={setSchoolOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={schoolOpen}
                        className="w-full justify-between"
                      >
                        {selectedSchool
                          ? schools.find((s) => s.id === selectedSchool)?.name
                          : "🏫 校舎を選択..."}
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-full p-0" align="start">
                      <Command>
                        <CommandInput placeholder="校舎を検索..." />
                        <CommandList>
                          <CommandEmpty>見つかりません</CommandEmpty>
                          <CommandGroup>
                            <CommandItem
                              value=""
                              onSelect={() => {
                                setSelectedSchool("");
                                setSchoolOpen(false);
                              }}
                            >
                              <Check className={cn("mr-2 h-4 w-4", !selectedSchool ? "opacity-100" : "opacity-0")} />
                              未選択
                            </CommandItem>
                            {schools.map((school) => (
                              <CommandItem
                                key={school.id}
                                value={school.name}
                                onSelect={() => {
                                  setSelectedSchool(school.id);
                                  setSchoolOpen(false);
                                }}
                              >
                                <Check className={cn("mr-2 h-4 w-4", selectedSchool === school.id ? "opacity-100" : "opacity-0")} />
                                {school.name}
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </div>

                {/* ブランド選択（検索可能） */}
                <div className="mb-2">
                  <Popover open={brandOpen} onOpenChange={setBrandOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={brandOpen}
                        className="w-full justify-between"
                      >
                        {selectedBrand
                          ? brands.find((b) => b.id === selectedBrand)?.name
                          : "🏷️ ブランドを選択..."}
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-full p-0" align="start">
                      <Command>
                        <CommandInput placeholder="ブランドを検索..." />
                        <CommandList>
                          <CommandEmpty>見つかりません</CommandEmpty>
                          <CommandGroup>
                            <CommandItem
                              value=""
                              onSelect={() => {
                                setSelectedBrand("");
                                setBrandOpen(false);
                              }}
                            >
                              <Check className={cn("mr-2 h-4 w-4", !selectedBrand ? "opacity-100" : "opacity-0")} />
                              未選択
                            </CommandItem>
                            {brands.map((brand) => (
                              <CommandItem
                                key={brand.id}
                                value={brand.name}
                                onSelect={() => {
                                  setSelectedBrand(brand.id);
                                  setBrandOpen(false);
                                }}
                              >
                                <Check className={cn("mr-2 h-4 w-4", selectedBrand === brand.id ? "opacity-100" : "opacity-0")} />
                                {brand.name}
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </div>

                {/* 担当者選択 */}
                <div className="mb-3">
                  <Select
                    value={selectedStaff || "__none__"}
                    onValueChange={(value) => {
                      console.log('[Assign] Selected staff:', value);
                      setSelectedStaff(value === "__none__" ? "" : value);
                    }}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="👤 担当者を選択..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">未選択</SelectItem>
                      {staffList.map((staff) => (
                        <SelectItem key={staff.id} value={staff.id}>
                          {staff.name} {staff.position && `(${staff.position})`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* コメント入力 */}
                <div className="mb-3">
                  <div className="flex items-center gap-2 mb-2">
                    <MessageSquare className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-700">コメント</span>
                  </div>
                  <Textarea
                    placeholder="担当者へのメッセージを入力..."
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    rows={2}
                    className="text-sm"
                  />
                </div>

                {/* 匿名オプション */}
                <div className="flex items-center space-x-2 mb-3 p-2 bg-gray-50 rounded">
                  <Checkbox
                    id="anonymous"
                    checked={isAnonymous}
                    onCheckedChange={(checked) => setIsAnonymous(checked === true)}
                  />
                  <label
                    htmlFor="anonymous"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex items-center gap-1"
                  >
                    <EyeOff className="w-3 h-3" />
                    匿名でタスクを振る
                  </label>
                </div>

                {/* 誰から誰へ表示 */}
                {selectedStaff && (
                  <div className="mb-3 p-3 bg-blue-50 border border-blue-100 rounded-lg">
                    <div className="flex items-center justify-center gap-2 text-sm">
                      <div className="flex items-center gap-1 px-2 py-1 bg-white rounded shadow-sm">
                        <User className="w-3 h-3 text-gray-500" />
                        <span className="font-medium">
                          {isAnonymous ? "匿名" : (currentUser?.name || "自分")}
                        </span>
                      </div>
                      <ArrowRight className="w-4 h-4 text-blue-500" />
                      <div className="flex items-center gap-1 px-2 py-1 bg-white rounded shadow-sm">
                        <User className="w-3 h-3 text-blue-500" />
                        <span className="font-medium text-blue-700">
                          {staffList.find(s => s.id === selectedStaff)?.name}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* 確定ボタン */}
                <Button
                  className="w-full"
                  variant="default"
                  onClick={async () => {
                    if (!selectedTask) return;

                    console.log('[Confirm] Starting assignment...', {
                      taskId: selectedTask.id,
                      selectedStaff,
                      selectedSchool,
                      selectedBrand,
                    });

                    const updateData: any = {
                      status: selectedTask.status === "new" ? "in_progress" : selectedTask.status,
                    };

                    if (selectedSchool) updateData.school = selectedSchool;
                    if (selectedBrand) updateData.brand = selectedBrand;
                    if (selectedStaff) updateData.assigned_to_id = selectedStaff;
                    // 匿名でない場合は作成者IDを設定
                    if (!isAnonymous && currentUser?.id) {
                      updateData.created_by_id = currentUser.id;
                    }

                    console.log('[Confirm] Update data:', updateData);
                    const result = await updateTask(selectedTask.id, updateData);
                    console.log('[Confirm] Result:', result);

                    if (result) {
                      // APIレスポンスを正規化
                      const normalizedResult = {
                        ...result,
                        assigned_to_id: result.assigned_to_id || (result as any).assignedToId,
                        assigned_to_name: result.assigned_to_name || (result as any).assignedToName,
                      };
                      // タスク一覧を即座に更新
                      setTasks(prev => prev.map(t => t.id === selectedTask.id ? normalizedResult : t));
                      setSelectedTask(normalizedResult);

                      // 割り当て情報を常にコメントとして追加
                      try {
                        const assigneeName = staffList.find(s => s.id === selectedStaff)?.name || '担当者';
                        const fromName = isAnonymous ? '匿名' : (currentUser?.name || '自分');

                        // 割り当て情報をコメントに含める
                        let fullComment = "";
                        if (selectedStaff) {
                          fullComment = `【${fromName} → ${assigneeName} に割り当て】`;
                        }
                        if (selectedSchool) {
                          const schoolName = schools.find(s => s.id === selectedSchool)?.name || '校舎';
                          fullComment += fullComment ? `\n校舎: ${schoolName}` : `校舎: ${schoolName}`;
                        }
                        if (selectedBrand) {
                          const brandName = brands.find(b => b.id === selectedBrand)?.name || 'ブランド';
                          fullComment += fullComment ? `\nブランド: ${brandName}` : `ブランド: ${brandName}`;
                        }
                        if (comment.trim()) {
                          fullComment += fullComment ? `\n\n${comment.trim()}` : comment.trim();
                        }

                        if (fullComment) {
                          console.log('[Confirm] Creating comment:', fullComment);
                          await apiClient.post('/tasks/comments/', {
                            task: selectedTask.id,
                            comment: fullComment,
                            commented_by_id: isAnonymous ? null : currentUser?.id,
                            is_internal: false,
                          });
                        }
                      } catch (error) {
                        console.error('Failed to add comment:', error);
                      }

                      // コメントを再読み込み
                      loadTaskComments(selectedTask.id);
                      // 選択をリセット
                      setSelectedSchool("");
                      setSelectedBrand("");
                      setSelectedStaff(result.assigned_to_id || "");
                      setIsAnonymous(false);
                      setComment("");
                    }
                  }}
                  disabled={!selectedSchool && !selectedBrand && !selectedStaff}
                >
                  <Send className="w-4 h-4 mr-2" />
                  確定して割り当て{comment.trim() ? "（コメント付き）" : ""}
                </Button>

                {/* 選択中の表示 */}
                {(selectedSchool || selectedBrand) && (
                  <div className="mt-2 p-2 bg-gray-50 rounded text-xs text-gray-600">
                    {selectedSchool && <div>🏫 {schools.find(s => s.id === selectedSchool)?.name}</div>}
                    {selectedBrand && <div>🏷️ {brands.find(b => b.id === selectedBrand)?.name}</div>}
                  </div>
                )}
              </div>
              )}

              {/* コメントタブ */}
              {detailTab === "comments" && (
                <div className="flex flex-col h-full">
                  {/* コメント入力エリア */}
                  <div className="mb-4 flex items-start gap-2">
                    <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
                      {currentUser?.name?.charAt(0) || "?"}
                    </div>
                    <div className="flex-1">
                      <Textarea
                        placeholder="コメントを入力..."
                        value={newComment}
                        onChange={(e) => setNewComment(e.target.value)}
                        rows={2}
                        className="text-sm resize-none"
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                            handleSubmitComment();
                          }
                        }}
                      />
                      <div className="flex justify-between items-center mt-2">
                        <span className="text-xs text-gray-400">Ctrl+Enter で送信</span>
                        <Button
                          size="sm"
                          onClick={handleSubmitComment}
                          disabled={!newComment.trim() || sendingComment}
                        >
                          {sendingComment ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <>
                              <Send className="w-3 h-3 mr-1" />
                              投稿
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* コメント一覧（スレッド形式） */}
                  <div className="flex-1 overflow-y-auto" style={{ maxHeight: "350px" }}>
                    {commentsLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                      </div>
                    ) : taskComments.length > 0 ? (
                      <div className="relative">
                        {/* スレッドライン */}
                        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />

                        {taskComments.map((comment, index) => {
                          const isAssignment = comment.comment.includes("に割り当て】");
                          return (
                            <div key={comment.id} className="relative flex gap-3 pb-4">
                              {/* アバター */}
                              <div className={cn(
                                "relative z-10 w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium flex-shrink-0 border-2 border-white",
                                isAssignment ? "bg-blue-500 text-white" : "bg-gray-100 text-gray-600"
                              )}>
                                {isAssignment ? <UserPlus className="w-4 h-4" /> : (comment.commented_by_name?.charAt(0) || "?")}
                              </div>

                              {/* コメント内容 */}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-sm text-gray-900">
                                    {comment.commented_by_name || "システム"}
                                  </span>
                                  <span className="text-xs text-gray-400">
                                    {formatRelativeTime(comment.created_at)}
                                  </span>
                                </div>
                                <div className={cn(
                                  "mt-1 text-sm rounded-lg p-2",
                                  isAssignment ? "bg-blue-50 border border-blue-100" : "bg-gray-50"
                                )}>
                                  {isAssignment ? (
                                    <div>
                                      {comment.comment.split("\n").map((line, i) => (
                                        <div key={i} className={cn(
                                          line.startsWith("【") ? "font-medium text-blue-700" : "text-gray-600"
                                        )}>
                                          {line}
                                        </div>
                                      ))}
                                    </div>
                                  ) : (
                                    <p className="text-gray-700 whitespace-pre-wrap break-words">
                                      {comment.comment}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center py-8 text-gray-500">
                        <MessageSquare className="w-10 h-10 mb-2 text-gray-300" />
                        <p className="text-sm">コメントがありません</p>
                        <p className="text-xs text-gray-400 mt-1">最初のコメントを投稿してください</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
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
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
