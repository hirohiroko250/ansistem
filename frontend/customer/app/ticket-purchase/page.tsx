'use client';

import { useState } from 'react';
import { ChevronLeft, Calendar as CalendarIcon, Ticket } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function TicketPurchaseSelectionPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">チケット購入方法を選択</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        <div className="space-y-4">
          <Card
            className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-blue-500"
            onClick={() => router.push('/ticket-purchase/from-ticket')}
          >
            <CardContent className="p-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
                  <Ticket className="h-8 w-8 text-blue-600" />
                </div>
                <div className="flex-1">
                  <h2 className="text-lg font-bold text-gray-800 mb-1">チケットから選択</h2>
                  <p className="text-sm text-gray-600">
                    回数券や月額コースを選択
                  </p>
                </div>
              </div>
              <div className="bg-blue-50 rounded-lg p-3">
                <p className="text-xs text-gray-700">
                  ブランド → 地区 → 運営会社 → コース選択
                </p>
              </div>
            </CardContent>
          </Card>

          <Card
            className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-green-500"
            onClick={() => router.push('/ticket-purchase/from-class')}
          >
            <CardContent className="p-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
                  <CalendarIcon className="h-8 w-8 text-green-600" />
                </div>
                <div className="flex-1">
                  <h2 className="text-lg font-bold text-gray-800 mb-1">クラスから選択</h2>
                  <p className="text-sm text-gray-600">
                    曜日・時間を指定してクラスを予約
                  </p>
                </div>
              </div>
              <div className="bg-green-50 rounded-lg p-3">
                <p className="text-xs text-gray-700">
                  ブランド → 地区 → 運営会社 → 校舎 → カレンダー選択
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-8 p-4 bg-gray-50 rounded-xl">
          <h3 className="font-semibold text-gray-800 mb-2 text-sm">購入方法の違い</h3>
          <ul className="space-y-2 text-xs text-gray-600">
            <li className="flex gap-2">
              <span className="text-blue-600">•</span>
              <span><span className="font-semibold">チケットから</span>：コースを選んでから日時を調整したい方向け</span>
            </li>
            <li className="flex gap-2">
              <span className="text-green-600">•</span>
              <span><span className="font-semibold">クラスから</span>：希望の曜日・時間が決まっている方向け</span>
            </li>
          </ul>
        </div>
      </main>

      <BottomTabBar />
    </div>
  );
}
