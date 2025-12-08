'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { BottomNav } from '@/components/bottom-nav';
import { Clock, MapPin, Users, MessageCircle, CheckSquare, LogIn, LogOut } from 'lucide-react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';

interface TodayClass {
  id: string;
  class_name: string;
  classroom: string;
  start_time: string;
  end_time: string;
  campus: { name: string };
}

interface WorkLog {
  check_in_time: string | null;
  check_out_time: string | null;
}

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<any>(null);
  const [todayClasses, setTodayClasses] = useState<TodayClass[]>([]);
  const [workLog, setWorkLog] = useState<WorkLog | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [taskCount, setTaskCount] = useState(0);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    loadData();
  }, [user, loading]);

  const loadData = async () => {
    if (!user) return;

    const { data: profileData } = await supabase
      .from('profiles')
      .select('*')
      .eq('id', user.id)
      .single();

    if (profileData) {
      setProfile(profileData);
    }

    const today = format(new Date(), 'yyyy-MM-dd');

    const { data: classesData } = await supabase
      .from('classes')
      .select(`
        id,
        class_name,
        classroom,
        start_time,
        end_time,
        campus:campuses(name)
      `)
      .eq('instructor_id', user.id)
      .eq('date', today)
      .order('start_time');

    if (classesData) {
      setTodayClasses(classesData as any);
    }

    const { data: workLogData } = await supabase
      .from('work_logs')
      .select('check_in_time, check_out_time')
      .eq('instructor_id', user.id)
      .eq('date', today)
      .maybeSingle();

    setWorkLog(workLogData);

    const { count: taskCountData } = await supabase
      .from('tasks')
      .select('*', { count: 'exact', head: true })
      .eq('assigned_to', user.id)
      .neq('status', 'completed');

    setTaskCount(taskCountData || 0);
  };

  const getWorkStatus = () => {
    if (!workLog) return { label: '出勤前', color: 'bg-gray-500' };
    if (workLog.check_in_time && !workLog.check_out_time) {
      return { label: '出勤中', color: 'bg-green-500' };
    }
    if (workLog.check_out_time) {
      return { label: '退勤済', color: 'bg-blue-500' };
    }
    return { label: '出勤前', color: 'bg-gray-500' };
  };

  if (loading || !profile) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100" />;
  }

  const workStatus = getWorkStatus();

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-[390px] mx-auto">
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <h1 className="text-2xl font-bold text-gray-900">ホーム</h1>
            <p className="text-sm text-gray-600 mt-1">
              {format(new Date(), 'yyyy年MM月dd日 (E)', { locale: ja })}
            </p>
          </div>
        </div>

        <div className="p-4 space-y-4">
          <Card className="shadow-md border-0">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">勤務状況</CardTitle>
            </CardHeader>
            <CardContent>
              {!workLog?.check_in_time ? (
                <div className="text-center py-4">
                  <div className="mb-4">
                    <Badge className="bg-gray-500 text-white text-base px-4 py-1">
                      出勤前
                    </Badge>
                  </div>
                  <Button
                    className="w-full"
                    size="lg"
                    onClick={() => router.push('/attendance')}
                  >
                    <LogIn className="w-4 h-4 mr-2" />
                    出勤する
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <LogIn className="w-4 h-4 text-green-600" />
                      <span className="text-sm font-medium text-gray-700">出勤時刻</span>
                    </div>
                    <span className="text-sm font-bold text-gray-900">
                      {format(new Date(workLog.check_in_time), 'HH:mm')}
                    </span>
                  </div>
                  {workLog.check_out_time ? (
                    <>
                      <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                        <div className="flex items-center gap-2">
                          <LogOut className="w-4 h-4 text-blue-600" />
                          <span className="text-sm font-medium text-gray-700">退勤時刻</span>
                        </div>
                        <span className="text-sm font-bold text-gray-900">
                          {format(new Date(workLog.check_out_time), 'HH:mm')}
                        </span>
                      </div>
                      <div className="text-center pt-2">
                        <Badge className="bg-blue-500 text-white text-base px-4 py-1">
                          退勤済
                        </Badge>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="text-center">
                        <Badge className="bg-green-500 text-white text-base px-4 py-1">
                          出勤中
                        </Badge>
                      </div>
                      <Button
                        className="w-full"
                        variant="outline"
                        onClick={() => router.push('/attendance')}
                      >
                        <LogOut className="w-4 h-4 mr-2" />
                        退勤する
                      </Button>
                    </>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="shadow-md border-0">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="w-5 h-5" />
                今日の授業
              </CardTitle>
            </CardHeader>
            <CardContent>
              {todayClasses.length > 0 ? (
                <div className="space-y-3">
                  {todayClasses.map((cls) => (
                    <div
                      key={cls.id}
                      className="p-3 bg-blue-50 rounded-xl hover:bg-blue-100 transition-colors cursor-pointer"
                      onClick={() => router.push(`/classes/${cls.id}`)}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-semibold text-gray-900">{cls.class_name}</h3>
                          <div className="flex items-center gap-2 text-sm text-gray-600 mt-1">
                            <MapPin className="w-3 h-3" />
                            <span>{cls.classroom}</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-medium text-blue-600">
                            {cls.start_time.substring(0, 5)} - {cls.end_time.substring(0, 5)}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 text-center py-4">
                  今日の授業はありません
                </p>
              )}
            </CardContent>
          </Card>

          <div className="grid grid-cols-2 gap-4">
            <Card
              className="shadow-md border-0 cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => router.push('/chat')}
            >
              <CardContent className="pt-6">
                <div className="flex flex-col items-center gap-2">
                  <MessageCircle className="w-8 h-8 text-blue-600" />
                  <div className="text-center">
                    <p className="text-sm font-medium text-gray-700">未読チャット</p>
                    <p className="text-2xl font-bold text-gray-900">{unreadCount}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card
              className="shadow-md border-0 cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => router.push('/tasks')}
            >
              <CardContent className="pt-6">
                <div className="flex flex-col items-center gap-2">
                  <CheckSquare className="w-8 h-8 text-orange-600" />
                  <div className="text-center">
                    <p className="text-sm font-medium text-gray-700">未完了タスク</p>
                    <p className="text-2xl font-bold text-gray-900">{taskCount}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {taskCount > 0 && (
            <Card className="shadow-md border-0 bg-gradient-to-r from-blue-500 to-blue-600 text-white">
              <CardHeader>
                <CardTitle className="text-lg">タスクリマインダー</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <p>未完了のタスクが {taskCount} 件あります。</p>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="w-full mt-2"
                    onClick={() => router.push('/tasks')}
                  >
                    タスクを確認する
                  </Button>
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
