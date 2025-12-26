'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { BottomNav } from '@/components/bottom-nav';
import {
  Calendar,
  Send,
  CheckCircle2,
  Clock,
  AlertTriangle,
  MessageCircle,
  Plus,
  User,
  Users,
  ArrowRight,
  Loader2,
  RefreshCw,
  Flag,
} from 'lucide-react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import { getAccessToken } from '@/lib/api/client';
import {
  getTasks,
  getMyTasks,
  getTask,
  createTask,
  updateTask,
  completeTask,
  getTaskComments,
  addTaskComment,
  getStaffForAssignment,
  type Task,
  type TaskComment,
  type Staff,
} from '@/lib/api/tasks';

type FilterType = 'all' | 'my' | 'assigned_by_me';

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [comments, setComments] = useState<TaskComment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [filterType, setFilterType] = useState<FilterType>('my');
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [staffList, setStaffList] = useState<Staff[]>([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [currentUserId, setCurrentUserId] = useState<string>('');

  // 新規タスクフォーム
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    taskType: 'other',
    priority: 'normal',
    assignedToId: '',
    dueDate: '',
  });

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.push('/login');
      return;
    }

    // JWTからユーザーIDを取得
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      setCurrentUserId(payload.user_id || '');
    } catch {
      console.error('Failed to decode token');
    }

    loadStaffList();
  }, [router]);

  useEffect(() => {
    loadTasks();
  }, [filterStatus, filterType]);

  useEffect(() => {
    if (selectedTask) {
      loadComments();
    }
  }, [selectedTask?.id]);

  const loadTasks = async () => {
    try {
      setIsLoading(true);
      let data: Task[];

      if (filterType === 'my') {
        data = await getMyTasks({ status: filterStatus || undefined });
      } else {
        data = await getTasks({
          status: filterStatus || undefined,
          assignedToId: filterType === 'assigned_by_me' ? currentUserId : undefined,
        });
      }

      setTasks(data);
    } catch (error) {
      console.error('Failed to load tasks:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadComments = async () => {
    if (!selectedTask) return;
    try {
      const data = await getTaskComments(selectedTask.id);
      setComments(data);
    } catch (error) {
      console.error('Failed to load comments:', error);
    }
  };

  const loadStaffList = async () => {
    try {
      const data = await getStaffForAssignment();
      setStaffList(data);
    } catch (error) {
      console.error('Failed to load staff list:', error);
    }
  };

  const handleSendComment = async () => {
    if (!selectedTask || !newComment.trim() || isSending) return;

    setIsSending(true);
    try {
      await addTaskComment(selectedTask.id, newComment.trim());
      setNewComment('');
      await loadComments();
    } catch (error) {
      console.error('Failed to send comment:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleUpdateStatus = async (status: string) => {
    if (!selectedTask) return;

    try {
      if (status === 'completed') {
        const updated = await completeTask(selectedTask.id);
        setSelectedTask(updated);
      } else {
        const updated = await updateTask(selectedTask.id, { status });
        setSelectedTask(updated);
      }
      await loadTasks();
    } catch (error) {
      console.error('Failed to update status:', error);
    }
  };

  const handleCreateTask = async () => {
    if (!newTask.title.trim()) return;

    try {
      await createTask({
        title: newTask.title,
        description: newTask.description,
        taskType: newTask.taskType,
        priority: newTask.priority,
        assignedToId: newTask.assignedToId || undefined,
        dueDate: newTask.dueDate || undefined,
      });

      setNewTask({
        title: '',
        description: '',
        taskType: 'other',
        priority: 'normal',
        assignedToId: '',
        dueDate: '',
      });
      setShowCreateDialog(false);
      await loadTasks();
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { label: string; className: string }> = {
      new: { label: '新規', className: 'bg-blue-500' },
      in_progress: { label: '対応中', className: 'bg-yellow-500' },
      waiting: { label: '保留', className: 'bg-gray-500' },
      completed: { label: '完了', className: 'bg-green-500' },
      cancelled: { label: 'キャンセル', className: 'bg-red-500' },
    };
    return statusMap[status] || { label: status, className: 'bg-gray-400' };
  };

  const getPriorityBadge = (priority: string) => {
    const priorityMap: Record<string, { label: string; className: string; icon: any }> = {
      low: { label: '低', className: 'bg-gray-400', icon: null },
      normal: { label: '通常', className: 'bg-blue-400', icon: null },
      high: { label: '高', className: 'bg-orange-500', icon: AlertTriangle },
      urgent: { label: '緊急', className: 'bg-red-500', icon: AlertTriangle },
    };
    return priorityMap[priority] || priorityMap.normal;
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-[420px] mx-auto">
        {/* ヘッダー */}
        <div className="bg-white/90 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4 flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">タスク管理</h1>
              <p className="text-xs text-gray-500">担当・割り当てタスク</p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={loadTasks}
                disabled={isLoading}
              >
                <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
              </Button>
              <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
                <DialogTrigger asChild>
                  <Button size="sm">
                    <Plus className="w-4 h-4 mr-1" />
                    新規
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-[360px]">
                  <DialogHeader>
                    <DialogTitle>新規タスク作成</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div>
                      <Label>タイトル *</Label>
                      <Input
                        value={newTask.title}
                        onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                        placeholder="タスクのタイトル"
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label>説明</Label>
                      <Textarea
                        value={newTask.description}
                        onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                        placeholder="タスクの詳細..."
                        rows={3}
                        className="mt-1"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>種別</Label>
                        <Select
                          value={newTask.taskType}
                          onValueChange={(v) => setNewTask({ ...newTask, taskType: v })}
                        >
                          <SelectTrigger className="mt-1">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="inquiry">問い合わせ</SelectItem>
                            <SelectItem value="request">依頼</SelectItem>
                            <SelectItem value="trouble">トラブル</SelectItem>
                            <SelectItem value="follow_up">フォローアップ</SelectItem>
                            <SelectItem value="other">その他</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>優先度</Label>
                        <Select
                          value={newTask.priority}
                          onValueChange={(v) => setNewTask({ ...newTask, priority: v })}
                        >
                          <SelectTrigger className="mt-1">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="low">低</SelectItem>
                            <SelectItem value="normal">通常</SelectItem>
                            <SelectItem value="high">高</SelectItem>
                            <SelectItem value="urgent">緊急</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div>
                      <Label className="flex items-center gap-1">
                        <User className="w-4 h-4" />
                        担当者を割り当て
                      </Label>
                      <Select
                        value={newTask.assignedToId}
                        onValueChange={(v) => setNewTask({ ...newTask, assignedToId: v })}
                      >
                        <SelectTrigger className="mt-1">
                          <SelectValue placeholder="担当者を選択..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">未割り当て</SelectItem>
                          {staffList.map((staff) => (
                            <SelectItem key={staff.id} value={staff.id}>
                              {staff.fullName}
                              {staff.position && ` (${staff.position})`}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>期限日</Label>
                      <Input
                        type="date"
                        value={newTask.dueDate}
                        onChange={(e) => setNewTask({ ...newTask, dueDate: e.target.value })}
                        className="mt-1"
                      />
                    </div>
                    <Button onClick={handleCreateTask} className="w-full" disabled={!newTask.title.trim()}>
                      作成する
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </div>

          {/* フィルタータブ */}
          <div className="flex border-b">
            {[
              { key: 'my', label: '自分宛', icon: User },
              { key: 'all', label: 'すべて', icon: Users },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setFilterType(tab.key as FilterType)}
                className={`flex-1 py-2 text-sm font-medium transition-colors relative ${
                  filterType === tab.key
                    ? 'text-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <div className="flex items-center justify-center gap-1">
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </div>
                {filterType === tab.key && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="p-4">
          {/* ステータスフィルター */}
          <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
            <Button
              variant={filterStatus === '' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterStatus('')}
              className="whitespace-nowrap"
            >
              すべて
            </Button>
            <Button
              variant={filterStatus === 'new' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterStatus('new')}
              className="whitespace-nowrap"
            >
              <Clock className="w-4 h-4 mr-1" />
              新規
            </Button>
            <Button
              variant={filterStatus === 'in_progress' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterStatus('in_progress')}
              className="whitespace-nowrap"
            >
              対応中
            </Button>
            <Button
              variant={filterStatus === 'completed' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterStatus('completed')}
              className="whitespace-nowrap"
            >
              <CheckCircle2 className="w-4 h-4 mr-1" />
              完了
            </Button>
          </div>

          {/* タスク一覧 */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            </div>
          ) : tasks.length === 0 ? (
            <Card className="p-8 text-center text-gray-500">
              <p>タスクがありません</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => setShowCreateDialog(true)}
              >
                <Plus className="w-4 h-4 mr-1" />
                タスクを作成
              </Button>
            </Card>
          ) : (
            <div className="space-y-3">
              {tasks.map((task) => {
                const statusBadge = getStatusBadge(task.status);
                const priorityBadge = getPriorityBadge(task.priority);

                return (
                  <Card
                    key={task.id}
                    className={`cursor-pointer transition-all hover:shadow-md ${
                      selectedTask?.id === task.id
                        ? 'ring-2 ring-blue-500 bg-blue-50'
                        : ''
                    }`}
                    onClick={() => setSelectedTask(task)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge className={`${statusBadge.className} text-white text-xs`}>
                              {statusBadge.label}
                            </Badge>
                            {task.priority !== 'normal' && (
                              <Badge className={`${priorityBadge.className} text-white text-xs`}>
                                {priorityBadge.icon && <priorityBadge.icon className="w-3 h-3 mr-0.5" />}
                                {priorityBadge.label}
                              </Badge>
                            )}
                          </div>
                          <h3 className="font-semibold text-gray-900 truncate">
                            {task.title}
                          </h3>

                          {/* 割り当て情報 */}
                          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                            {task.createdByName && (
                              <span className="flex items-center gap-1">
                                <User className="w-3 h-3" />
                                {task.createdByName}
                              </span>
                            )}
                            {task.assignedToName && (
                              <>
                                <ArrowRight className="w-3 h-3" />
                                <span className="flex items-center gap-1 text-blue-600 font-medium">
                                  <User className="w-3 h-3" />
                                  {task.assignedToName}
                                </span>
                              </>
                            )}
                          </div>

                          {task.dueDate && (
                            <div className="flex items-center gap-1 text-xs text-gray-500 mt-1">
                              <Calendar className="w-3 h-3" />
                              <span>期限: {format(new Date(task.dueDate), 'M/d(E)', { locale: ja })}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {/* タスク詳細 */}
          {selectedTask && (
            <Card className="shadow-lg border-0 mt-4">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-lg">{selectedTask.title}</CardTitle>
                  <Badge className={`${getStatusBadge(selectedTask.status).className} text-white`}>
                    {getStatusBadge(selectedTask.status).label}
                  </Badge>
                </div>

                {/* 詳細情報 */}
                <div className="space-y-2 mt-3">
                  {selectedTask.createdByName && (
                    <p className="text-sm text-gray-600 flex items-center gap-2">
                      <User className="w-4 h-4" />
                      <span>作成者: {selectedTask.createdByName}</span>
                    </p>
                  )}
                  {selectedTask.assignedToName && (
                    <p className="text-sm text-blue-600 flex items-center gap-2">
                      <User className="w-4 h-4" />
                      <span>担当者: {selectedTask.assignedToName}</span>
                    </p>
                  )}
                  {selectedTask.dueDate && (
                    <p className="text-sm text-gray-600 flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      <span>期限: {format(new Date(selectedTask.dueDate), 'yyyy年M月d日(E)', { locale: ja })}</span>
                    </p>
                  )}
                  {selectedTask.studentName && (
                    <p className="text-sm text-gray-600">
                      生徒: {selectedTask.studentName}
                    </p>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {selectedTask.description && (
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                      {selectedTask.description}
                    </p>
                  </div>
                )}

                {/* アクションボタン */}
                <div className="flex gap-2 flex-wrap">
                  {selectedTask.status === 'new' && (
                    <Button
                      size="sm"
                      onClick={() => handleUpdateStatus('in_progress')}
                      className="bg-yellow-500 hover:bg-yellow-600"
                    >
                      着手する
                    </Button>
                  )}
                  {selectedTask.status === 'in_progress' && (
                    <Button
                      size="sm"
                      onClick={() => handleUpdateStatus('completed')}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      <CheckCircle2 className="w-4 h-4 mr-1" />
                      完了にする
                    </Button>
                  )}
                  {selectedTask.status === 'in_progress' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleUpdateStatus('waiting')}
                    >
                      保留にする
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => router.push('/chat?tab=staff')}
                    className="text-purple-600 border-purple-200 hover:bg-purple-50"
                  >
                    <MessageCircle className="w-4 h-4 mr-1" />
                    チャットで相談
                  </Button>
                </div>

                {/* コメント */}
                <div className="border-t pt-4">
                  <h4 className="font-semibold text-sm mb-3">コメント・対応履歴</h4>
                  <ScrollArea className="h-48 mb-3">
                    <div className="space-y-3">
                      {comments.map((comment) => (
                        <div
                          key={comment.id}
                          className={`p-3 rounded-lg ${
                            comment.isInternal
                              ? 'bg-yellow-50 border border-yellow-200'
                              : 'bg-gray-50'
                          }`}
                        >
                          {comment.isInternal && (
                            <Badge variant="outline" className="text-xs mb-1 text-yellow-700 border-yellow-400">
                              内部メモ
                            </Badge>
                          )}
                          <p className="text-sm text-gray-900">{comment.comment}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            {format(new Date(comment.createdAt), 'M/d HH:mm')}
                          </p>
                        </div>
                      ))}
                      {comments.length === 0 && (
                        <p className="text-sm text-gray-500 text-center py-4">
                          コメントがありません
                        </p>
                      )}
                    </div>
                  </ScrollArea>

                  <div className="flex gap-2">
                    <Textarea
                      placeholder="コメントを入力..."
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      rows={2}
                      className="flex-1"
                    />
                    <Button
                      onClick={handleSendComment}
                      disabled={!newComment.trim() || isSending}
                      size="icon"
                      className="bg-blue-600 hover:bg-blue-700 self-end"
                    >
                      {isSending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
