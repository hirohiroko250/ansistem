'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { ArrowLeft, Sparkles, Calendar, CheckCircle2, Clock, Send, MessageSquare } from 'lucide-react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';

interface Task {
  id: string;
  title: string;
  description: string;
  ai_summary: string;
  ai_detailed_summary: string;
  ai_next_actions: string;
  status: string;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

interface TaskComment {
  id: string;
  content: string;
  created_at: string;
  user: { full_name: string };
  user_id: string;
}

export default function SmartNoteDetailPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const taskId = params.id as string;

  const [task, setTask] = useState<Task | null>(null);
  const [comments, setComments] = useState<TaskComment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [aiQuestion, setAiQuestion] = useState('');

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    loadData();
  }, [user, loading, taskId]);

  const loadData = async () => {
    if (!user) return;

    const { data: taskData } = await supabase
      .from('tasks')
      .select('*')
      .eq('id', taskId)
      .single();

    if (taskData) {
      setTask({
        ...taskData,
        ai_summary: taskData.ai_summary || 'AI要約はまだ生成されていません',
        ai_detailed_summary: taskData.ai_detailed_summary ||
          'このタスクは「' + taskData.title + '」に関するものです。\n\n' +
          '【概要】\n' + (taskData.description || 'タスクの詳細説明はありません。') + '\n\n' +
          '【進捗状況】\n現在のステータス: ' + getStatusLabel(taskData.status) + '\n\n' +
          'チャットでのやり取りが増えると、AIがより詳細な要約を生成します。',
        ai_next_actions: taskData.ai_next_actions ||
          '1. タスクの詳細を確認する\n2. 必要なアクションを特定する\n3. チーム内でコミュニケーションを取る\n4. 進捗を報告する',
      });
    }

    const { data: commentsData } = await supabase
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
      .eq('task_id', taskId)
      .order('created_at', { ascending: true });

    if (commentsData) {
      setComments(commentsData as any);
    }
  };

  const handleSendComment = async () => {
    if (!user || !newComment.trim()) return;

    const { error } = await supabase
      .from('task_comments')
      .insert({
        task_id: taskId,
        user_id: user.id,
        content: newComment,
      });

    if (!error) {
      setNewComment('');
      loadData();
    }
  };

  const handleAskAI = () => {
    alert('AI機能は開発中です。質問: ' + aiQuestion);
    setAiQuestion('');
  };

  const getStatusLabel = (status: string) => {
    const statusMap: Record<string, string> = {
      not_started: '未着手',
      in_progress: '進行中',
      completed: '完了',
      archived: 'アーカイブ',
    };
    return statusMap[status] || status;
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

  if (loading || !task) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100" />;
  }

  const statusBadge = getStatusBadge(task.status);

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-24">
      <div className="max-w-[390px] mx-auto">
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.back()}
              className="mb-2"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              戻る
            </Button>
            <div className="flex items-start justify-between gap-2">
              <h1 className="text-xl font-bold text-gray-900 leading-tight flex-1">
                {task.title}
              </h1>
              <Badge className={`${statusBadge.className} text-white text-xs shrink-0`}>
                {statusBadge.label}
              </Badge>
            </div>
          </div>
        </div>

        <div className="p-4 space-y-4">
          <Card className="shadow-lg border-0 bg-gradient-to-br from-blue-50 via-white to-purple-50">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-blue-600" />
                <CardTitle className="text-lg">AI要約</CardTitle>
              </div>
              <CardDescription>タスクの概要と進捗</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 bg-white rounded-xl shadow-sm border border-blue-100">
                <h3 className="font-semibold text-sm text-gray-700 mb-2 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-blue-600" />
                  概要サマリー
                </h3>
                <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
                  {task.ai_detailed_summary}
                </p>
              </div>

              <div className="p-4 bg-white rounded-xl shadow-sm border border-purple-100">
                <h3 className="font-semibold text-sm text-gray-700 mb-2 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-purple-600" />
                  次にやること
                </h3>
                <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
                  {task.ai_next_actions}
                </p>
              </div>

              {task.due_date && (
                <div className="flex items-center gap-2 text-sm text-gray-600 p-3 bg-white rounded-lg">
                  <Calendar className="w-4 h-4" />
                  <span>期限: {format(new Date(task.due_date), 'yyyy年MM月dd日 HH:mm', { locale: ja })}</span>
                </div>
              )}

              <div className="pt-2">
                <div className="flex gap-2">
                  <Input
                    placeholder="AIに質問する..."
                    value={aiQuestion}
                    onChange={(e) => setAiQuestion(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleAskAI();
                      }
                    }}
                    className="flex-1"
                  />
                  <Button
                    onClick={handleAskAI}
                    disabled={!aiQuestion.trim()}
                    size="icon"
                    className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  >
                    <Sparkles className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Separator className="my-6" />

          <Card className="shadow-lg border-0">
            <CardHeader>
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-gray-700" />
                <CardTitle className="text-lg">タスクチャット</CardTitle>
              </div>
              <CardDescription>全メッセージ履歴</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96 pr-4">
                <div className="space-y-3">
                  {comments.map((comment) => (
                    <div
                      key={comment.id}
                      className={`flex ${
                        comment.user_id === user?.id
                          ? 'justify-end'
                          : 'justify-start'
                      }`}
                    >
                      <div
                        className={`max-w-[85%] ${
                          comment.user_id === user?.id
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 text-gray-900'
                        } rounded-2xl p-3 shadow-sm`}
                      >
                        {comment.user_id !== user?.id && (
                          <p className="text-xs font-semibold mb-1 opacity-70">
                            {comment.user.full_name}
                          </p>
                        )}
                        <p className="text-sm break-words leading-relaxed">
                          {comment.content}
                        </p>
                        <p className="text-xs opacity-70 mt-1">
                          {format(new Date(comment.created_at), 'MM/dd HH:mm')}
                        </p>
                      </div>
                    </div>
                  ))}
                  {comments.length === 0 && (
                    <div className="text-center text-gray-500 py-8">
                      <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                      <p className="text-sm">まだメッセージがありません</p>
                    </div>
                  )}
                </div>
              </ScrollArea>

              <div className="mt-4 pt-4 border-t">
                <div className="flex gap-2">
                  <Input
                    placeholder="メッセージを入力..."
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleSendComment();
                      }
                    }}
                    className="flex-1"
                  />
                  <Button
                    onClick={handleSendComment}
                    disabled={!newComment.trim()}
                    size="icon"
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
