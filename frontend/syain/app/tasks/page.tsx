'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAuth } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { BottomNav } from '@/components/bottom-nav';
import { Calendar, Send, CheckCircle2, Clock, Archive, MessageCircle } from 'lucide-react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';

interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  due_date: string | null;
  created_at: string;
}

interface TaskComment {
  id: string;
  content: string;
  created_at: string;
  user: { full_name: string };
  user_id: string;
}

export default function TasksPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [comments, setComments] = useState<TaskComment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('not_started');

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    loadTasks();
  }, [user, loading, filterStatus]);

  useEffect(() => {
    if (selectedTask) {
      loadComments();
    }
  }, [selectedTask]);

  const loadTasks = async () => {
    if (!user) return;

    let query = supabase
      .from('tasks')
      .select('*')
      .eq('assigned_to', user.id)
      .order('due_date', { ascending: true });

    if (filterStatus !== 'all') {
      query = query.eq('status', filterStatus);
    }

    const { data } = await query;

    if (data) {
      setTasks(data);
      if (data.length > 0 && !selectedTask) {
        setSelectedTask(data[0]);
      }
    }
  };

  const loadComments = async () => {
    if (!selectedTask) return;

    const { data } = await supabase
      .from('task_comments')
      .select(`
        id,
        content,
        created_at,
        user_id,
        user:profiles!task_comments_user_id_fkey (
          full_name
        )
      `)
      .eq('task_id', selectedTask.id)
      .order('created_at', { ascending: true });

    if (data) {
      setComments(data as any);
    }
  };

  const handleSendComment = async () => {
    if (!user || !selectedTask || !newComment.trim()) return;

    const { error } = await supabase
      .from('task_comments')
      .insert({
        task_id: selectedTask.id,
        user_id: user.id,
        content: newComment,
      });

    if (!error) {
      setNewComment('');
      loadComments();
    }
  };

  const handleUpdateStatus = async (status: string) => {
    if (!selectedTask) return;

    const { error } = await supabase
      .from('tasks')
      .update({ status, updated_at: new Date().toISOString() })
      .eq('id', selectedTask.id);

    if (!error) {
      setSelectedTask({ ...selectedTask, status });
      loadTasks();
    }
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { label: string; className: string }> = {
      not_started: { label: '未着手', className: 'bg-gray-500' },
      in_progress: { label: '進行中', className: 'bg-blue-500' },
      completed: { label: '完了', className: 'bg-green-500' },
      archived: { label: 'アーカイブ', className: 'bg-gray-400' },
    };
    return statusMap[status] || statusMap.not_started;
  };

  if (loading) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100" />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-[390px] mx-auto">
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <h1 className="text-2xl font-bold text-gray-900">タスク管理</h1>
          </div>
        </div>

        <div className="p-4">
          <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
            <Button
              variant={filterStatus === 'not_started' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterStatus('not_started')}
              className="whitespace-nowrap"
            >
              <Clock className="w-4 h-4 mr-1" />
              未着手
            </Button>
            <Button
              variant={filterStatus === 'in_progress' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterStatus('in_progress')}
              className="whitespace-nowrap"
            >
              進行中
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
            <Button
              variant={filterStatus === 'archived' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterStatus('archived')}
              className="whitespace-nowrap"
            >
              <Archive className="w-4 h-4 mr-1" />
              アーカイブ
            </Button>
          </div>

          {tasks.length === 0 ? (
            <Card className="p-8 text-center text-gray-500">
              タスクがありません
            </Card>
          ) : (
            <div className="space-y-4">
              <Card className="shadow-md border-0">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">タスク一覧</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-48">
                    <div className="space-y-2">
                      {tasks.map((task) => (
                        <div
                          key={task.id}
                          className={`p-3 rounded-lg cursor-pointer transition-all ${
                            selectedTask?.id === task.id
                              ? 'bg-blue-100 border-2 border-blue-500'
                              : 'bg-gray-50 hover:bg-gray-100'
                          }`}
                          onClick={() => setSelectedTask(task)}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="font-semibold text-sm text-gray-900 flex-1">
                              {task.title}
                            </h3>
                            <Badge className={`${getStatusBadge(task.status).className} text-white text-xs`}>
                              {getStatusBadge(task.status).label}
                            </Badge>
                          </div>
                          {task.due_date && (
                            <div className="flex items-center gap-1 text-xs text-gray-600 mt-1">
                              <Calendar className="w-3 h-3" />
                              <span>
                                期限: {format(new Date(task.due_date), 'MM/dd HH:mm')}
                              </span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>

              {selectedTask && (
                <Card className="shadow-md border-0">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-lg">{selectedTask.title}</CardTitle>
                      <Badge className={`${getStatusBadge(selectedTask.status).className} text-white`}>
                        {getStatusBadge(selectedTask.status).label}
                      </Badge>
                    </div>
                    {selectedTask.due_date && (
                      <p className="text-sm text-gray-600 flex items-center gap-1 mt-2">
                        <Calendar className="w-4 h-4" />
                        期限: {format(new Date(selectedTask.due_date), 'yyyy年MM月dd日 HH:mm', { locale: ja })}
                      </p>
                    )}
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {selectedTask.description && (
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">
                          {selectedTask.description}
                        </p>
                      </div>
                    )}

                    <div className="flex gap-2 flex-wrap">
                      {selectedTask.status === 'not_started' && (
                        <Button
                          size="sm"
                          onClick={() => handleUpdateStatus('in_progress')}
                          className="bg-blue-600 hover:bg-blue-700"
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
                          完了にする
                        </Button>
                      )}
                      {selectedTask.status === 'completed' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleUpdateStatus('archived')}
                        >
                          アーカイブ
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

                    <div className="border-t pt-4">
                      <h4 className="font-semibold text-sm mb-3">コメント</h4>
                      <ScrollArea className="h-48 mb-3">
                        <div className="space-y-3">
                          {comments.map((comment) => (
                            <div
                              key={comment.id}
                              className={`p-3 rounded-lg ${
                                comment.user_id === user?.id
                                  ? 'bg-blue-50 ml-4'
                                  : 'bg-gray-50 mr-4'
                              }`}
                            >
                              <p className="text-xs font-semibold text-gray-700 mb-1">
                                {comment.user.full_name}
                              </p>
                              <p className="text-sm text-gray-900">{comment.content}</p>
                              <p className="text-xs text-gray-500 mt-1">
                                {format(new Date(comment.created_at), 'MM/dd HH:mm')}
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
                          disabled={!newComment.trim()}
                          size="icon"
                          className="bg-blue-600 hover:bg-blue-700 self-end"
                        >
                          <Send className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
