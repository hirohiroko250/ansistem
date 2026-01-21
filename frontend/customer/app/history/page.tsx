'use client';

import { AuthGuard } from '@/components/auth';

import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, Loader2, Calendar, Ticket, X, RefreshCw, CreditCard, UserMinus, PartyPopper, Filter } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { format, parseISO } from 'date-fns';
import { ja } from 'date-fns/locale';
import { useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/api/auth';
import { getAbsenceTickets, type AbsenceTicket } from '@/lib/api/lessons';
import { getAllStudentItems, type PurchasedItem } from '@/lib/api/students';

// 操作履歴の型
type HistoryItem = {
  id: string;
  type: 'absence' | 'makeup' | 'ticket_purchase' | 'event' | 'withdrawal' | 'suspension';
  title: string;
  description: string;
  date: string;
  status?: string;
  childName?: string;
};

// 履歴タイプの設定
const HISTORY_TYPE_CONFIG = {
  absence: {
    icon: X,
    bgColor: 'bg-pink-100',
    iconColor: 'text-pink-600',
    badgeColor: 'bg-pink-500',
    label: '欠席',
  },
  makeup: {
    icon: RefreshCw,
    bgColor: 'bg-purple-100',
    iconColor: 'text-purple-600',
    badgeColor: 'bg-purple-500',
    label: '振替',
  },
  ticket_purchase: {
    icon: CreditCard,
    bgColor: 'bg-green-100',
    iconColor: 'text-green-600',
    badgeColor: 'bg-green-500',
    label: '購入',
  },
  event: {
    icon: PartyPopper,
    bgColor: 'bg-blue-100',
    iconColor: 'text-blue-600',
    badgeColor: 'bg-blue-500',
    label: 'イベント',
  },
  withdrawal: {
    icon: UserMinus,
    bgColor: 'bg-gray-100',
    iconColor: 'text-gray-600',
    badgeColor: 'bg-gray-500',
    label: '退会',
  },
  suspension: {
    icon: Calendar,
    bgColor: 'bg-orange-100',
    iconColor: 'text-orange-600',
    badgeColor: 'bg-orange-500',
    label: '休会',
  },
};

// フィルターオプション
const FILTER_OPTIONS = [
  { value: 'all', label: 'すべて' },
  { value: 'absence', label: '欠席' },
  { value: 'makeup', label: '振替' },
  { value: 'ticket_purchase', label: '購入' },
  { value: 'event', label: 'イベント' },
];

function HistoryContent() {
  const router = useRouter();
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [showFilter, setShowFilter] = useState(false);

  // 履歴データを取得
  const fetchHistory = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const items: HistoryItem[] = [];

      // 欠席・振替チケットを取得
      try {
        const absenceTickets = await getAbsenceTickets();

        absenceTickets.forEach((ticket: AbsenceTicket) => {
          // 欠席履歴
          if (ticket.absenceDate) {
            items.push({
              id: `absence-${ticket.id}`,
              type: 'absence',
              title: '欠席登録',
              description: ticket.originalTicketName || ticket.brandName || '授業',
              date: ticket.absenceDate,
              status: ticket.status === 'issued' ? '振替チケット発行済' :
                      ticket.status === 'used' ? '振替済' :
                      ticket.status === 'expired' ? '期限切れ' : '',
              childName: ticket.studentName,
            });
          }

          // 振替履歴
          if (ticket.status === 'used' && ticket.usedDate) {
            items.push({
              id: `makeup-${ticket.id}`,
              type: 'makeup',
              title: '振替受講',
              description: ticket.originalTicketName || ticket.brandName || '授業',
              date: ticket.usedDate,
              childName: ticket.studentName,
            });
          }
        });
      } catch (e) {
        console.error('Failed to fetch absence tickets:', e);
      }

      // チケット購入履歴を取得
      try {
        const purchaseData = await getAllStudentItems();
        // チケット関連の購入のみフィルター
        purchaseData.items.forEach((item: PurchasedItem) => {
          // チケット購入のみを抽出
          if (item.productType === 'ticket' || item.productName.includes('チケット')) {
            items.push({
              id: `purchase-${item.id}`,
              type: 'ticket_purchase',
              title: 'チケット購入',
              description: item.productName,
              date: item.billingMonth + '-01', // 請求月の1日を日付として使用
              childName: item.studentName,
            });
          }
        });
      } catch (e) {
        console.error('Failed to fetch purchase history:', e);
      }

      // 日付で降順ソート
      items.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return dateB.getTime() - dateA.getTime();
      });

      setHistoryItems(items);
    } catch (err) {
      console.error('Failed to fetch history:', err);
      setError('履歴の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }
    fetchHistory();
  }, [router, fetchHistory]);

  // フィルター適用
  const filteredItems = filter === 'all'
    ? historyItems
    : historyItems.filter(item => item.type === filter);

  // 日付をグループ化（月ごと）
  const groupedByMonth = filteredItems.reduce((acc, item) => {
    const monthKey = item.date.substring(0, 7); // YYYY-MM
    if (!acc[monthKey]) {
      acc[monthKey] = [];
    }
    acc[monthKey].push(item);
    return acc;
  }, {} as Record<string, HistoryItem[]>);

  const sortedMonths = Object.keys(groupedByMonth).sort().reverse();

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-14 flex items-center">
            <Link href="/" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <h1 className="text-lg font-bold text-gray-800 flex-1 text-center">履歴</h1>
            <div className="w-9" />
          </div>
        </header>
        <main className="max-w-[390px] mx-auto px-4 py-6 pb-24 flex items-center justify-center min-h-[50vh]">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-2" />
            <p className="text-gray-500">読み込み中...</p>
          </div>
        </main>
        <BottomTabBar />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-14 flex items-center">
          <Link href="/" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-lg font-bold text-gray-800 flex-1 text-center">履歴</h1>
          <button
            onClick={() => setShowFilter(!showFilter)}
            className={`p-2 rounded-lg transition-colors ${showFilter ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <Filter className="h-5 w-5" />
          </button>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-4 pb-24">
        {/* フィルター */}
        {showFilter && (
          <Card className="rounded-xl shadow-md mb-4">
            <CardContent className="p-3">
              <div className="flex flex-wrap gap-2">
                {FILTER_OPTIONS.map(option => (
                  <button
                    key={option.value}
                    onClick={() => setFilter(option.value)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                      filter === option.value
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {error && (
          <Card className="rounded-xl shadow-md bg-red-50 border-red-200 mb-4">
            <CardContent className="p-4">
              <p className="text-red-600 text-sm">{error}</p>
            </CardContent>
          </Card>
        )}

        {filteredItems.length === 0 ? (
          <div className="text-center py-8">
            <Calendar className="h-10 w-10 text-gray-300 mx-auto mb-2" />
            <p className="text-gray-500 text-sm">履歴がありません</p>
          </div>
        ) : (
          <div className="space-y-4">
            {sortedMonths.map(monthKey => {
              const monthItems = groupedByMonth[monthKey];
              const monthDisplay = format(parseISO(`${monthKey}-01`), 'yyyy年M月', { locale: ja });

              return (
                <div key={monthKey}>
                  <h2 className="text-xs font-semibold text-gray-500 mb-2 px-1">{monthDisplay}</h2>
                  <Card className="rounded-xl shadow-sm overflow-hidden">
                    <div className="divide-y divide-gray-100">
                      {monthItems.map(item => {
                        const config = HISTORY_TYPE_CONFIG[item.type];
                        const Icon = config.icon;

                        return (
                          <div key={item.id} className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50">
                            <div className={`w-7 h-7 ${config.bgColor} rounded-md flex items-center justify-center shrink-0`}>
                              <Icon className={`h-3.5 w-3.5 ${config.iconColor}`} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5">
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium text-white ${config.badgeColor}`}>
                                  {config.label}
                                </span>
                                <span className="text-sm font-medium text-gray-800 truncate">{item.title}</span>
                                {item.childName && (
                                  <span className="text-[10px] text-gray-400 truncate">{item.childName}</span>
                                )}
                              </div>
                            </div>
                            <div className="text-right shrink-0">
                              <div className="text-xs text-gray-600">
                                {format(parseISO(item.date), 'M/d(E)', { locale: ja })}
                              </div>
                              {item.status && (
                                <div className="text-[10px] text-blue-500">{item.status}</div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </Card>
                </div>
              );
            })}
          </div>
        )}
      </main>

      <BottomTabBar />
    </div>
  );
}

export default function HistoryPage() {
  return (
    <AuthGuard>
      <HistoryContent />
    </AuthGuard>
  );
}
