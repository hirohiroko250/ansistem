'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth';
import { BottomNav } from '@/components/bottom-nav';
import { Clock, MapPin, MessageCircle, CheckSquare, LogIn, LogOut } from 'lucide-react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import Image from 'next/image';

interface TodayClass {
  id: string;
  className: string;
  classroom: string;
  startTime: string;
  endTime: string;
  campusName: string;
}

interface WorkLog {
  checkInTime: string | null;
  checkOutTime: string | null;
}

export default function HomePage() {
  const { user, loading, isAuthenticated } = useAuth();
  const router = useRouter();
  const [todayClasses, setTodayClasses] = useState<TodayClass[]>([]);
  const [workLog, setWorkLog] = useState<WorkLog | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [taskCount, setTaskCount] = useState(0);

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    loadData();
  }, [isAuthenticated, loading, router]);

  const loadData = async () => {
    // TODO: Django APIから取得するように変更
    // 現在はダミーデータ
    setTodayClasses([
      {
        id: '1',
        className: '英会話入門クラス',
        classroom: 'A教室',
        startTime: '10:00',
        endTime: '11:00',
        campusName: '本校',
      },
      {
        id: '2',
        className: 'そろばん中級',
        classroom: 'B教室',
        startTime: '14:00',
        endTime: '15:00',
        campusName: '本校',
      },
    ]);
    setWorkLog(null); // 出勤前
    setTaskCount(3);
    setUnreadCount(2);
  };

  const getWorkStatus = () => {
    if (!workLog) return { label: '出勤前', color: 'bg-gray-500' };
    if (workLog.checkInTime && !workLog.checkOutTime) {
      return { label: '出勤中', color: 'bg-green-500' };
    }
    if (workLog.checkOutTime) {
      return { label: '退勤済', color: 'bg-blue-500' };
    }
    return { label: '出勤前', color: 'bg-gray-500' };
  };

  if (loading || !isAuthenticated) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100" />;
  }

  const workStatus = getWorkStatus();
  const userName = user && 'fullName' in user ? user.fullName : '';

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-[390px] mx-auto">
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4 flex items-center justify-between">
            <Image
              src="/oza-logo-header.svg"
              alt="OZA"
              width={100}
              height={36}
              className="h-9 w-auto"
              priority
            />
            <p className="text-sm text-gray-600">
              {format(new Date(), 'yyyy年MM月dd日 (E)', { locale: ja })}
            </p>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {/* ユーザー情報 */}
          <Card className="shadow-md border-0 bg-gradient-to-r from-blue-500 to-blue-600 text-white">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center text-xl font-bold">
                  {userName ? userName.charAt(0) : 'U'}
                </div>
                <div>
                  <p className="font-bold text-lg">{userName || 'ユーザー'}</p>
                  <p className="text-sm text-blue-100">{user?.email}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 勤務状況 */}
          <Card className="shadow-md border-0">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">勤務状況</CardTitle>
            </CardHeader>
            <CardContent>
              {!workLog?.checkInTime ? (
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
                      {workLog.checkInTime}
                    </span>
                  </div>
                  {workLog.checkOutTime ? (
                    <>
                      <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                        <div className="flex items-center gap-2">
                          <LogOut className="w-4 h-4 text-blue-600" />
                          <span className="text-sm font-medium text-gray-700">退勤時刻</span>
                        </div>
                        <span className="text-sm font-bold text-gray-900">
                          {workLog.checkOutTime}
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

          {/* 今日の授業 */}
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
                          <h3 className="font-semibold text-gray-900">{cls.className}</h3>
                          <div className="flex items-center gap-2 text-sm text-gray-600 mt-1">
                            <MapPin className="w-3 h-3" />
                            <span>{cls.classroom}</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-medium text-blue-600">
                            {cls.startTime} - {cls.endTime}
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


          {/* タスクリマインダー */}
          {taskCount > 0 && (
            <Card className="shadow-md border-0 bg-gradient-to-r from-orange-500 to-orange-600 text-white">
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
