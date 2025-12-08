'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAuth } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { BottomNav } from '@/components/bottom-nav';
import { Search, Sparkles, Calendar, User, Filter } from 'lucide-react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';

interface SmartNoteTask {
  id: string;
  title: string;
  ai_summary: string;
  status: string;
  due_date: string | null;
  updated_at: string;
  assigned_by_profile: { full_name: string } | null;
}

export default function SmartNotePage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [tasks, setTasks] = useState<SmartNoteTask[]>([]);
  const [filteredTasks, setFilteredTasks] = useState<SmartNoteTask[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    loadTasks();
  }, [user, loading]);

  useEffect(() => {
    filterTasks();
  }, [searchQuery, statusFilter, tasks]);

  const loadTasks = async () => {
    if (!user) return;

    const { data } = await supabase
      .from('tasks')
      .select(`
        id,
        title,
        ai_summary,
        status,
        due_date,
        updated_at,
        assigned_by_profile:profiles!tasks_assigned_by_fkey (
          full_name
        )
      `)
      .eq('assigned_to', user.id)
      .order('updated_at', { ascending: false });

    if (data) {
      const tasksWithDefaults = data.map((task: any) => ({
        ...task,
        ai_summary: task.ai_summary || 'AI要約はまだ生成されていません。タスクのコメントを追加すると自動生成されます。',
      }));
      setTasks(tasksWithDefaults);
    }
  };

  const filterTasks = () => {
    let filtered = [...tasks];

    if (searchQuery) {
      filtered = filtered.filter(
        (task) =>
          task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          task.ai_summary.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter((task) => task.status === statusFilter);
    }

    setFilteredTasks(filtered);
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
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-6 h-6 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">Smart Note</h1>
            </div>
            <p className="text-sm text-gray-600">AI要約タスクノート</p>
          </div>
        </div>

        <div className="p-4 space-y-4">
          <Card className="shadow-md border-0">
            <CardContent className="pt-4 space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="タスクを検索..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 h-11"
                />
              </div>

              <div className="flex gap-2 overflow-x-auto pb-2">
                <Button
                  variant={statusFilter === 'all' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setStatusFilter('all')}
                  className="whitespace-nowrap"
                >
                  すべて
                </Button>
                <Button
                  variant={statusFilter === 'not_started' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setStatusFilter('not_started')}
                  className="whitespace-nowrap"
                >
                  未着手
                </Button>
                <Button
                  variant={statusFilter === 'in_progress' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setStatusFilter('in_progress')}
                  className="whitespace-nowrap"
                >
                  進行中
                </Button>
                <Button
                  variant={statusFilter === 'completed' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setStatusFilter('completed')}
                  className="whitespace-nowrap"
                >
                  完了
                </Button>
              </div>
            </CardContent>
          </Card>

          <ScrollArea className="h-[calc(100vh-300px)]">
            <div className="space-y-3">
              {filteredTasks.length === 0 ? (
                <Card className="shadow-md border-0">
                  <CardContent className="py-12 text-center text-gray-500">
                    <Sparkles className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                    <p>タスクが見つかりません</p>
                  </CardContent>
                </Card>
              ) : (
                filteredTasks.map((task) => {
                  const statusBadge = getStatusBadge(task.status);
                  return (
                    <Card
                      key={task.id}
                      className="shadow-md border-0 hover:shadow-lg transition-shadow cursor-pointer"
                      onClick={() => router.push(`/smart-note/${task.id}`)}
                    >
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between gap-2">
                          <CardTitle className="text-base leading-tight flex-1">
                            {task.title}
                          </CardTitle>
                          <Badge className={`${statusBadge.className} text-white text-xs shrink-0`}>
                            {statusBadge.label}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="p-3 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-100">
                          <div className="flex items-start gap-2">
                            <Sparkles className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                            <p className="text-sm text-gray-700 leading-relaxed">
                              {task.ai_summary}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center justify-between text-xs text-gray-600">
                          <div className="flex items-center gap-4">
                            {task.assigned_by_profile && (
                              <div className="flex items-center gap-1">
                                <User className="w-3 h-3" />
                                <span>{task.assigned_by_profile.full_name}</span>
                              </div>
                            )}
                            {task.due_date && (
                              <div className="flex items-center gap-1">
                                <Calendar className="w-3 h-3" />
                                <span>{format(new Date(task.due_date), 'MM/dd')}</span>
                              </div>
                            )}
                          </div>
                          <span className="text-gray-400">
                            {format(new Date(task.updated_at), 'MM/dd HH:mm')}
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })
              )}
            </div>
          </ScrollArea>
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
