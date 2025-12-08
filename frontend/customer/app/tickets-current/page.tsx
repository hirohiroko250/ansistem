'use client';

import { ChevronLeft, Ticket } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';

type TicketItem = {
  id: number;
  brand: string;
  company: string;
  school: string;
  course: string;
  totalTickets: number;
  usedTickets: number;
  validUntil: string;
  color: string;
};

const currentMonthTickets: TicketItem[] = [
  {
    id: 1,
    brand: 'そろばん',
    company: 'ABC教育グループ',
    school: '○○そろばん教室 本校',
    course: '週2コース',
    totalTickets: 8,
    usedTickets: 3,
    validUntil: '2025/01/31',
    color: 'from-blue-500 to-blue-600',
  },
  {
    id: 2,
    brand: '英会話',
    company: 'English Education Co.',
    school: 'イングリッシュスクール○○',
    course: '週1コース',
    totalTickets: 4,
    usedTickets: 1,
    validUntil: '2025/01/31',
    color: 'from-orange-500 to-orange-600',
  },
  {
    id: 3,
    brand: '小学生塾',
    company: '進学塾ABCグループ',
    school: '進学塾ABC 渋谷校',
    course: '週2コース',
    totalTickets: 8,
    usedTickets: 5,
    validUntil: '2025/01/31',
    color: 'from-green-500 to-green-600',
  },
  {
    id: 4,
    brand: '学童保育',
    company: '学童クラブ○○運営会社',
    school: '学童クラブ○○',
    course: '週5コース',
    totalTickets: 20,
    usedTickets: 12,
    validUntil: '2025/01/31',
    color: 'from-purple-500 to-purple-600',
  },
];

export default function PurchaseHistoryPage() {
  const remainingTickets = currentMonthTickets.reduce((sum, ticket) =>
    sum + (ticket.totalTickets - ticket.usedTickets), 0
  );
  const totalTickets = currentMonthTickets.reduce((sum, ticket) => sum + ticket.totalTickets, 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">今月のチケット</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        <Card className="rounded-xl shadow-md mb-6 bg-gradient-to-br from-blue-600 to-blue-700 text-white">
          <CardContent className="p-6">
            <p className="text-sm opacity-90 mb-1">今月の残りチケット</p>
            <div className="flex items-baseline gap-2">
              <p className="text-4xl font-bold">{remainingTickets}</p>
              <p className="text-lg opacity-90">/ {totalTickets}枚</p>
            </div>
          </CardContent>
        </Card>

        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          {format(new Date(), 'yyyy年M月', { locale: ja })}のチケット
        </h2>

        <div className="space-y-4">
          {currentMonthTickets.map((ticket) => {
            const remaining = ticket.totalTickets - ticket.usedTickets;
            const percentage = (remaining / ticket.totalTickets) * 100;

            return (
              <Card key={ticket.id} className="rounded-xl shadow-md overflow-hidden">
                <div className={`h-2 bg-gradient-to-r ${ticket.color}`} />
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge className={`bg-gradient-to-r ${ticket.color} text-white`}>
                          {ticket.brand}
                        </Badge>
                        <span className="text-xs text-gray-500">
                          有効期限: {ticket.validUntil}
                        </span>
                      </div>
                      <h3 className="font-semibold text-gray-800">{ticket.course}</h3>
                      <p className="text-sm text-gray-600">{ticket.company}</p>
                      <p className="text-xs text-gray-500">{ticket.school}</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">使用状況</span>
                      <span className="font-semibold text-gray-800">
                        {ticket.usedTickets} / {ticket.totalTickets}枚使用
                      </span>
                    </div>

                    <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${ticket.color} transition-all duration-300`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between pt-2">
                      <div className="flex items-center gap-2">
                        <Ticket className="h-5 w-5 text-gray-500" />
                        <span className="text-lg font-bold text-gray-800">
                          残り {remaining}枚
                        </span>
                      </div>
                      {remaining <= 2 && remaining > 0 && (
                        <Badge variant="outline" className="text-orange-600 border-orange-600">
                          残りわずか
                        </Badge>
                      )}
                      {remaining === 0 && (
                        <Badge variant="outline" className="text-red-600 border-red-600">
                          使用済み
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </main>

      <BottomTabBar />
    </div>
  );
}
