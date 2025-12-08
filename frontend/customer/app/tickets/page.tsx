'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, Ticket, Calendar, RefreshCw, Clock, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getAllStudentItems, type PurchasedItem } from '@/lib/api/students';

type TicketType = {
  id: string;
  type: 'course' | 'transfer' | 'event';
  school: string;
  brand: string;
  count: number;
  expiryDate: string;
  status: 'active' | 'expiring';
  studentName?: string;
  productName?: string;
  billingMonth?: string;
};

// チケットとして表示すべき商品タイプかどうか判定
// 授業料（tuition）のみがチケット対象
// 月会費、教材費、入会金などは購入履歴（通帳）に表示
function isTicketType(productType: string): boolean {
  return productType === 'tuition';
}

// 商品タイプからチケットタイプへの変換（授業料のみ）
function getTicketType(productType: string): 'course' | 'transfer' | 'event' {
  // 授業料はコースチケット（通常）と振替チケットがある
  // ここでは全てコースチケットとして扱う（振替はまた別の仕組みで管理）
  return 'course';
}

// 有効期限計算（請求月の末日から3ヶ月後）
function calculateExpiryDate(billingMonth: string): string {
  const [year, month] = billingMonth.split('-').map(Number);
  const expiry = new Date(year, month + 2, 0); // 3ヶ月後の末日
  return expiry.toISOString().split('T')[0];
}

// 期限間近チェック（30日以内）
function isExpiringSoon(expiryDate: string): boolean {
  const expiry = new Date(expiryDate);
  const now = new Date();
  const diffDays = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  return diffDays <= 30 && diffDays > 0;
}

export default function TicketsPage() {
  const router = useRouter();
  const [tickets, setTickets] = useState<TicketType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        setLoading(true);
        const items = await getAllStudentItems();

        // 授業料（tuition）のみをチケットとして表示
        // 月会費、教材費、入会金などは購入履歴ページで表示
        const ticketItems = items.filter((item: PurchasedItem) => isTicketType(item.productType));

        // PurchasedItemをTicketTypeに変換
        const convertedTickets: TicketType[] = ticketItems.map((item: PurchasedItem) => {
          const expiryDate = calculateExpiryDate(item.billingMonth);
          return {
            id: item.id,
            type: getTicketType(item.productType),
            school: item.schoolName || '未指定',
            brand: item.brandName || item.productName,
            count: item.quantity,
            expiryDate,
            status: isExpiringSoon(expiryDate) ? 'expiring' : 'active',
            studentName: item.studentName,
            productName: item.productName,
            billingMonth: item.billingMonth,
          };
        });

        setTickets(convertedTickets);
        setError(null);
      } catch (err: unknown) {
        console.error('Failed to fetch tickets:', err);
        // 401エラーの場合はログインページにリダイレクト
        if (err && typeof err === 'object' && 'message' in err) {
          const errorMessage = (err as { message: string }).message;
          if (errorMessage.includes('401') || errorMessage.includes('認証')) {
            router.push('/login');
            return;
          }
        }
        setError('チケット情報の取得に失敗しました');
      } finally {
        setLoading(false);
      }
    };

    fetchTickets();
  }, [router]);

  const courseTickets = tickets.filter(t => t.type === 'course');
  const transferTickets = tickets.filter(t => t.type === 'transfer');
  const eventTickets = tickets.filter(t => t.type === 'event');

  const totalCourse = courseTickets.reduce((sum, t) => sum + t.count, 0);
  const totalTransfer = transferTickets.reduce((sum, t) => sum + t.count, 0);
  const totalEvent = eventTickets.reduce((sum, t) => sum + t.count, 0);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
            <Link href="/" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <h1 className="text-xl font-bold text-gray-800">保有チケット</h1>
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
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">保有チケット</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        {error && (
          <Card className="rounded-xl shadow-md bg-red-50 border-red-200 mb-6">
            <CardContent className="p-4">
              <p className="text-red-600 text-sm">{error}</p>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-3 gap-3 mb-6">
          <Card className="rounded-xl shadow-md border-blue-200 bg-blue-50">
            <CardContent className="p-3 text-center">
              <Ticket className="h-6 w-6 text-blue-600 mx-auto mb-1" />
              <p className="text-xs text-gray-600 mb-1">コース</p>
              <p className="text-2xl font-bold text-blue-600">{totalCourse}</p>
              <p className="text-xs text-gray-500">枚</p>
            </CardContent>
          </Card>

          <Card className="rounded-xl shadow-md border-amber-200 bg-amber-50">
            <CardContent className="p-3 text-center">
              <RefreshCw className="h-6 w-6 text-amber-600 mx-auto mb-1" />
              <p className="text-xs text-gray-600 mb-1">振替</p>
              <p className="text-2xl font-bold text-amber-600">{totalTransfer}</p>
              <p className="text-xs text-gray-500">枚</p>
            </CardContent>
          </Card>

          <Card className="rounded-xl shadow-md border-purple-200 bg-purple-50">
            <CardContent className="p-3 text-center">
              <Calendar className="h-6 w-6 text-purple-600 mx-auto mb-1" />
              <p className="text-xs text-gray-600 mb-1">イベント</p>
              <p className="text-2xl font-bold text-purple-600">{totalEvent}</p>
              <p className="text-xs text-gray-500">枚</p>
            </CardContent>
          </Card>
        </div>

        {tickets.length === 0 && !error && (
          <Card className="rounded-xl shadow-md bg-gray-50 border-gray-200 mb-6">
            <CardContent className="p-6 text-center">
              <Ticket className="h-12 w-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-600 font-medium mb-2">まだチケットがありません</p>
              <p className="text-sm text-gray-500">
                チケットを購入すると、ここに表示されます
              </p>
              <Link href="/ticket-purchase" className="inline-block mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium">
                チケットを購入する
              </Link>
            </CardContent>
          </Card>
        )}

        {courseTickets.length > 0 && (
          <section className="mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">コースチケット</h2>
            <div className="space-y-3">
              {courseTickets.map((ticket) => (
                <Card key={ticket.id} className="rounded-xl shadow-md hover:shadow-lg transition-shadow">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className="bg-blue-500 text-white text-xs">
                            {ticket.brand}
                          </Badge>
                          {ticket.status === 'expiring' && (
                            <Badge className="bg-orange-500 text-white text-xs">
                              期限間近
                            </Badge>
                          )}
                        </div>
                        <h3 className="font-semibold text-gray-800 mb-1">{ticket.school}</h3>
                        {ticket.studentName && (
                          <p className="text-xs text-gray-500">{ticket.studentName}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-blue-600">
                          <Ticket className="h-5 w-5" />
                          <span className="text-2xl font-bold">{ticket.count}</span>
                        </div>
                        <p className="text-xs text-gray-500">枚</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Calendar className="h-4 w-4" />
                      <span>有効期限: {ticket.expiryDate}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        {transferTickets.length > 0 && (
          <section className="mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">振替チケット</h2>
            <div className="space-y-3">
              {transferTickets.map((ticket) => (
                <Card key={ticket.id} className="rounded-xl shadow-md hover:shadow-lg transition-shadow border-amber-200">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className="bg-amber-500 text-white text-xs">
                            {ticket.brand}
                          </Badge>
                          <Badge className="bg-purple-500 text-white text-xs">
                            振替専用
                          </Badge>
                        </div>
                        <h3 className="font-semibold text-gray-800 mb-1">{ticket.school}</h3>
                        {ticket.studentName && (
                          <p className="text-xs text-gray-500">{ticket.studentName}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-amber-600">
                          <RefreshCw className="h-5 w-5" />
                          <span className="text-2xl font-bold">{ticket.count}</span>
                        </div>
                        <p className="text-xs text-gray-500">枚</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Calendar className="h-4 w-4" />
                      <span>有効期限: {ticket.expiryDate}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        {eventTickets.length > 0 && (
          <section className="mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">イベントチケット</h2>
            <div className="space-y-3">
              {eventTickets.map((ticket) => (
                <Card key={ticket.id} className="rounded-xl shadow-md hover:shadow-lg transition-shadow border-purple-200">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className="bg-purple-500 text-white text-xs">
                            {ticket.brand}
                          </Badge>
                        </div>
                        <h3 className="font-semibold text-gray-800 mb-1">{ticket.school}</h3>
                        {ticket.studentName && (
                          <p className="text-xs text-gray-500">{ticket.studentName}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-purple-600">
                          <Calendar className="h-5 w-5" />
                          <span className="text-2xl font-bold">{ticket.count}</span>
                        </div>
                        <p className="text-xs text-gray-500">枚</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Calendar className="h-4 w-4" />
                      <span>有効期限: {ticket.expiryDate}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        <Card className="rounded-xl shadow-md bg-blue-50 border-blue-200">
          <CardContent className="p-4">
            <div className="flex gap-3">
              <Clock className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-blue-900 mb-1">チケットについて</h3>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• コースチケットは授業の予約に使用できます</li>
                  <li>• 振替チケットは欠席した授業の振替に使用できます</li>
                  <li>• イベントチケットは特別イベントに使用できます</li>
                  <li>• 各チケットには有効期限があります</li>
                  <li>• 有効期限が近いチケットから使用されます</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>

      <BottomTabBar />
    </div>
  );
}
