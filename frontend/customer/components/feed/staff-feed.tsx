'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import {
  Heart,
  MessageCircle,
  Bookmark,
  Plus,
  Users,
  Calendar,
  ClipboardList,
  Bell,
  ChevronRight
} from 'lucide-react';

interface TodayLesson {
  id: string;
  time: string;
  studentName: string;
  subject: string;
  status: 'upcoming' | 'ongoing' | 'completed';
}

interface Announcement {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  isImportant: boolean;
}

// モックデータ（後でAPIに置き換え）
const todayLessons: TodayLesson[] = [
  { id: '1', time: '10:00', studentName: '山田 花子', subject: '英語', status: 'completed' },
  { id: '2', time: '11:00', studentName: '佐藤 太郎', subject: '数学', status: 'ongoing' },
  { id: '3', time: '14:00', studentName: '鈴木 美咲', subject: '国語', status: 'upcoming' },
  { id: '4', time: '15:00', studentName: '田中 健太', subject: '理科', status: 'upcoming' },
];

const staffAnnouncements: Announcement[] = [
  {
    id: '1',
    title: '月次ミーティングのお知らせ',
    content: '12月10日（火）14:00より月次ミーティングを実施します。全員参加でお願いします。',
    createdAt: '2025-12-05',
    isImportant: true,
  },
  {
    id: '2',
    title: '冬期講習シフト確定',
    content: '冬期講習のシフトが確定しました。マイページよりご確認ください。',
    createdAt: '2025-12-04',
    isImportant: false,
  },
];

export function StaffFeed() {
  const router = useRouter();
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  const getStatusColor = (status: TodayLesson['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-gray-100 text-gray-600';
      case 'ongoing':
        return 'bg-green-100 text-green-700';
      case 'upcoming':
        return 'bg-blue-100 text-blue-700';
    }
  };

  const getStatusText = (status: TodayLesson['status']) => {
    switch (status) {
      case 'completed':
        return '完了';
      case 'ongoing':
        return '授業中';
      case 'upcoming':
        return '予定';
    }
  };

  return (
    <>
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-sm border-b border-gray-200">
        <div className="max-w-[420px] mx-auto px-4 h-16 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">フィード</h1>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              <span className="absolute -top-1 -right-1 h-4 w-4 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center">
                3
              </span>
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-[420px] mx-auto pb-24">
        {/* クイックアクション */}
        <div className="px-4 py-4">
          <div className="grid grid-cols-4 gap-3">
            <button
              onClick={() => router.push('/students')}
              className="flex flex-col items-center gap-2 p-3 rounded-xl bg-blue-50 hover:bg-blue-100 transition-colors"
            >
              <Users className="h-6 w-6 text-blue-600" />
              <span className="text-xs font-medium text-blue-700">生徒管理</span>
            </button>
            <button
              onClick={() => router.push('/schedule')}
              className="flex flex-col items-center gap-2 p-3 rounded-xl bg-green-50 hover:bg-green-100 transition-colors"
            >
              <Calendar className="h-6 w-6 text-green-600" />
              <span className="text-xs font-medium text-green-700">スケジュール</span>
            </button>
            <button
              onClick={() => router.push('/attendance')}
              className="flex flex-col items-center gap-2 p-3 rounded-xl bg-purple-50 hover:bg-purple-100 transition-colors"
            >
              <ClipboardList className="h-6 w-6 text-purple-600" />
              <span className="text-xs font-medium text-purple-700">出欠管理</span>
            </button>
            <button
              onClick={() => router.push('/chat')}
              className="flex flex-col items-center gap-2 p-3 rounded-xl bg-amber-50 hover:bg-amber-100 transition-colors"
            >
              <MessageCircle className="h-6 w-6 text-amber-600" />
              <span className="text-xs font-medium text-amber-700">チャット</span>
            </button>
          </div>
        </div>

        {/* 業務連絡 */}
        <div className="px-4 py-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold text-gray-900">業務連絡</h2>
            <Button variant="ghost" size="sm" className="text-blue-600">
              すべて見る
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
          <div className="space-y-3">
            {staffAnnouncements.map((announcement) => (
              <Card
                key={announcement.id}
                className={`rounded-xl shadow-sm ${
                  announcement.isImportant ? 'border-l-4 border-l-red-500' : ''
                }`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-gray-800">{announcement.title}</h3>
                        {announcement.isImportant && (
                          <Badge variant="destructive" className="text-xs">重要</Badge>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 line-clamp-2">{announcement.content}</p>
                      <p className="text-xs text-gray-400 mt-2">{announcement.createdAt}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* 本日の授業 */}
        <div className="px-4 py-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold text-gray-900">本日の授業</h2>
            <Badge variant="outline" className="text-xs">
              {todayLessons.length}件
            </Badge>
          </div>
          <Card className="rounded-xl shadow-sm">
            <CardContent className="p-0 divide-y">
              {todayLessons.map((lesson) => (
                <div
                  key={lesson.id}
                  className="flex items-center gap-4 p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => router.push(`/classes/${lesson.id}`)}
                >
                  <div className="text-center min-w-[50px]">
                    <p className="text-lg font-bold text-gray-900">{lesson.time}</p>
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-800">{lesson.studentName}</p>
                    <p className="text-sm text-gray-500">{lesson.subject}</p>
                  </div>
                  <Badge className={getStatusColor(lesson.status)}>
                    {getStatusText(lesson.status)}
                  </Badge>
                </div>
              ))}
              {todayLessons.length === 0 && (
                <div className="p-8 text-center text-gray-500">
                  本日の授業はありません
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 投稿セクション */}
        <div className="px-4 py-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold text-gray-900">最新の投稿</h2>
            <Button size="sm" className="rounded-full">
              <Plus className="w-4 h-4 mr-1" />
              投稿
            </Button>
          </div>
          <Card className="rounded-xl shadow-sm">
            <CardContent className="p-6 text-center text-gray-500">
              <MessageCircle className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>まだ投稿がありません</p>
              <Button variant="outline" className="mt-4">
                最初の投稿をする
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </>
  );
}
