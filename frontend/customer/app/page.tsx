'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Bell, CreditCard, QrCode, Building2, MessageSquare, Receipt, Calendar, ChevronRight, Ticket, UserPlus, Star, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { getLatestNews, type NewsItem } from '@/lib/api/announcements';
import { posts as fallbackPosts } from '@/lib/feed-data';
import { isAuthenticated } from '@/lib/api/auth';

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

export default function Home() {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [newsLoading, setNewsLoading] = useState(true);

  useEffect(() => {
    // 認証チェック
    if (!isAuthenticated()) {
      router.replace('/login');
    } else {
      setIsChecking(false);
      // お知らせを取得
      fetchNews();
    }
  }, [router]);

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
          <h1 className="text-2xl font-bold text-blue-600">MyLesson</h1>
          <button className="p-2 rounded-full hover:bg-gray-100 transition-colors relative">
            <Bell className="h-6 w-6 text-gray-700" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
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
