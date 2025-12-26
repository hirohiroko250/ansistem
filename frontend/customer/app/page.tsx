'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Bell, CreditCard, QrCode, Building2, MessageSquare, Receipt, Calendar, ChevronRight, Ticket, UserPlus, Star, Loader2, AlertCircle, Banknote } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import Image from 'next/image';
import { getLatestNews, type NewsItem } from '@/lib/api/announcements';
import { posts as fallbackPosts } from '@/lib/feed-data';
import { isAuthenticated } from '@/lib/api/auth';
import { getMyPayment, type PaymentInfo } from '@/lib/api/payment';
import { getMyContracts, type MyContract, type MyStudent } from '@/lib/api/contracts';

const shortcuts = [
  { id: 1, name: 'チケット', icon: Ticket, href: '/tickets', color: 'bg-blue-500' },
  { id: 2, name: 'チケット購入', icon: CreditCard, href: '/ticket-purchase', color: 'bg-green-500' },
  { id: 3, name: 'QR読み取り', icon: QrCode, href: '/qr-reader', color: 'bg-orange-500' },
  { id: 4, name: 'クラス', icon: Building2, href: '/class-registration', color: 'bg-teal-500' },
  { id: 5, name: '体験', icon: Star, href: '/trial', color: 'bg-yellow-500' },
  { id: 6, name: '子供追加', icon: UserPlus, href: '/children', color: 'bg-pink-500' },
  { id: 7, name: 'チャット質問', icon: MessageSquare, href: '/chat', color: 'bg-cyan-500' },
  { id: 8, name: '購入履歴', icon: Receipt, href: '/purchase-history', color: 'bg-emerald-500' },
  { id: 9, name: 'カレンダー', icon: Calendar, href: '/calendar', color: 'bg-sky-500' },
];

// 作業一覧の項目型
type TaskItem = {
  id: string;
  title: string;
  description: string;
  href: string;
  icon: typeof Banknote;
  priority: 'high' | 'medium' | 'low';
};

export default function Home() {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [newsLoading, setNewsLoading] = useState(true);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [students, setStudents] = useState<MyStudent[]>([]);
  const [contracts, setContracts] = useState<MyContract[]>([]);
  const [contractsLoading, setContractsLoading] = useState(true);

  // 曜日ラベル
  const DAY_LABELS = ['日', '月', '火', '水', '木', '金', '土'];

  useEffect(() => {
    // 認証チェック
    if (!isAuthenticated()) {
      router.replace('/login');
    } else {
      setIsChecking(false);
      // お知らせを取得
      fetchNews();
      // 作業一覧を取得
      fetchTasks();
      // 契約（受講中のクラス）を取得
      fetchContracts();
    }
  }, [router]);

  const fetchContracts = async () => {
    try {
      setContractsLoading(true);
      const response = await getMyContracts();
      setStudents(response.students || []);
      setContracts(response.contracts || []);
    } catch (error) {
      console.error('Failed to fetch contracts:', error);
    } finally {
      setContractsLoading(false);
    }
  };

  const fetchTasks = async () => {
    try {
      setTasksLoading(true);
      const pendingTasks: TaskItem[] = [];

      // 支払い情報を確認
      const paymentInfo = await getMyPayment();
      if (!paymentInfo || !paymentInfo.paymentRegistered) {
        pendingTasks.push({
          id: 'payment-registration',
          title: '銀行口座を登録してください',
          description: '月謝の引き落としに必要な口座情報を登録してください',
          href: '/settings/payment/edit',
          icon: Banknote,
          priority: 'high',
        });
      }

      setTasks(pendingTasks);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    } finally {
      setTasksLoading(false);
    }
  };

  const fetchNews = async () => {
    try {
      setNewsLoading(true);
      const latestNews = await getLatestNews(5);
      if (latestNews.length > 0) {
        setNews(latestNews);
      } else {
        // APIからデータがない場合はフォールバック
        setNews(fallbackPosts.filter(post => post.type).slice(0, 2).map(p => ({
          id: String(p.id),
          type: p.type as '新着' | 'お知らせ' | 'イベント',
          caption: p.caption,
          date: p.date,
          source: 'feed' as const,
        })));
      }
    } catch (error) {
      console.error('Failed to fetch news:', error);
      // エラー時はフォールバック
      setNews(fallbackPosts.filter(post => post.type).slice(0, 2).map(p => ({
        id: String(p.id),
        type: p.type as '新着' | 'お知らせ' | 'イベント',
        caption: p.caption,
        date: p.date,
        source: 'feed' as const,
      })));
    } finally {
      setNewsLoading(false);
    }
  };

  // 認証チェック中はローディング表示
  if (isChecking) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center justify-between">
          <Image
            src="/oza-logo-header.svg"
            alt="OZA"
            width={120}
            height={40}
            className="h-10 w-auto"
            priority
          />
          <button className="p-2 rounded-full hover:bg-gray-100 transition-colors relative">
            <Bell className="h-6 w-6 text-gray-700" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        {/* 作業一覧セクション */}
        {!tasksLoading && tasks.length > 0 && (
          <section className="mb-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-orange-500" />
                やることリスト
              </h2>
            </div>
            <div className="space-y-3">
              {tasks.map((task) => {
                const Icon = task.icon;
                return (
                  <Link key={task.id} href={task.href}>
                    <Card className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer border-l-4 border-orange-500 bg-orange-50">
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 bg-orange-500 rounded-lg flex items-center justify-center shrink-0">
                            <Icon className="h-5 w-5 text-white" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-gray-800 mb-1">{task.title}</h3>
                            <p className="text-sm text-gray-600">{task.description}</p>
                          </div>
                          <ChevronRight className="h-5 w-5 text-gray-400 shrink-0" />
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                );
              })}
            </div>
          </section>
        )}

        {/* 受講中のクラス */}
        <section className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <Calendar className="h-5 w-5 text-teal-500" />
              受講中のクラス
            </h2>
            <Link href="/class-management" className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1">
              管理
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
          {contractsLoading ? (
            <div className="flex justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-teal-500" />
            </div>
          ) : contracts.length > 0 ? (
            <div className="space-y-3">
              {/* 生徒ごとにグループ化 */}
              {students.map((student) => {
                const studentContracts = contracts.filter(c => c.student.id === student.id && c.status === 'active');
                if (studentContracts.length === 0) return null;

                return (
                  <Card key={student.id} className="rounded-xl shadow-md overflow-hidden">
                    <div className="bg-teal-500 px-4 py-2">
                      <h3 className="text-white font-semibold text-sm">{student.fullName}</h3>
                      {student.grade && (
                        <p className="text-teal-100 text-xs">{student.grade}</p>
                      )}
                    </div>
                    <CardContent className="p-0">
                      {studentContracts.map((contract, idx) => (
                        <div
                          key={contract.id}
                          className={`p-3 ${idx < studentContracts.length - 1 ? 'border-b border-gray-100' : ''}`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-gray-800">{contract.brand.brandName}</span>
                                {contract.ticket && (
                                  <Badge className="bg-blue-100 text-blue-700 text-xs">
                                    {contract.ticket.ticketName}
                                  </Badge>
                                )}
                              </div>
                              <div className="flex items-center gap-3 mt-1 text-sm text-gray-600">
                                <span className="flex items-center gap-1">
                                  <Building2 className="h-3.5 w-3.5" />
                                  {contract.school.schoolName}
                                </span>
                              </div>
                              {contract.dayOfWeek !== undefined && contract.dayOfWeek !== null && contract.startTime && (
                                <div className="mt-1 text-sm font-medium text-teal-600">
                                  {DAY_LABELS[contract.dayOfWeek]}曜日 {contract.startTime.slice(0, 5)}〜
                                  {contract.endTime && contract.endTime.slice(0, 5)}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          ) : (
            <Card className="rounded-xl shadow-md">
              <CardContent className="p-6 text-center">
                <Calendar className="h-10 w-10 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-500 text-sm">受講中のクラスはありません</p>
                <Link href="/class-registration" className="text-blue-600 text-sm mt-2 inline-block">
                  クラスを探す →
                </Link>
              </CardContent>
            </Card>
          )}
        </section>

        <section className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-800">最新情報</h2>
            <Link href="/feed" className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1">
              すべて見る
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="space-y-3">
            {newsLoading ? (
              <div className="flex justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
              </div>
            ) : news.length > 0 ? (
              news.slice(0, 2).map((item) => (
                <Link key={item.id} href="/feed">
                  <Card className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer">
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <Badge className={`${
                          item.type === '新着' ? 'bg-blue-500' :
                          item.type === 'お知らせ' ? 'bg-orange-500' :
                          'bg-green-500'
                        } text-white text-xs shrink-0`}>
                          {item.type}
                        </Badge>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-gray-800 mb-1 line-clamp-2">{item.caption}</h3>
                          <p className="text-xs text-gray-500">{item.date}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))
            ) : (
              <p className="text-center text-gray-500 text-sm py-4">お知らせはありません</p>
            )}
          </div>
        </section>

        <section>
          <div className="grid grid-cols-3 gap-4">
            {shortcuts.map((shortcut) => {
              const Icon = shortcut.icon;
              return (
                <Link key={shortcut.id} href={shortcut.href}>
                  <div className="flex flex-col items-center cursor-pointer">
                    <div className={`w-14 h-14 ${shortcut.color} rounded-2xl flex items-center justify-center mb-2 shadow-md hover:shadow-lg transition-all hover:scale-105`}>
                      <Icon className="h-7 w-7 text-white" />
                    </div>
                    <span className="text-xs text-center text-gray-700 font-medium leading-tight">{shortcut.name}</span>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      </main>

      <BottomTabBar />
    </div>
  );
}
