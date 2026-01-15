'use client';

import { Suspense, useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, Ticket, Calendar, Home, GraduationCap, Trophy } from 'lucide-react';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { format, parseISO } from 'date-fns';
import { ja } from 'date-fns/locale';

interface BookedClass {
  id: string;
  date: string;
  time: string;
  schoolName: string;
}

interface PurchaseResult {
  orderId: string;
  childName: string;
  childId: string;
  courseName: string;
  courseId: string;
  brandId?: string;
  schoolId?: string;
  amount: number;
  startDate: string | null;
  bookedClass?: BookedClass | null;
  type?: 'regular' | 'seminar' | 'certification';
}

function PurchaseCompleteContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [purchaseResult, setPurchaseResult] = useState<PurchaseResult | null>(null);
  const purchaseType = searchParams.get('type') as 'regular' | 'seminar' | 'certification' | null;

  useEffect(() => {
    const stored = sessionStorage.getItem('purchaseResult');
    if (stored) {
      try {
        setPurchaseResult(JSON.parse(stored));
        // 読み取り後に削除（リロード時の重複防止）
        sessionStorage.removeItem('purchaseResult');
      } catch {
        // パース失敗時はホームへ
        router.push('/');
      }
    } else {
      // 購入情報がない場合はホームへ
      router.push('/');
    }
  }, [router]);

  const getTypeConfig = () => {
    const type = purchaseResult?.type || purchaseType || 'regular';
    switch (type) {
      case 'seminar':
        return {
          title: '講習会申込が完了しました',
          subtitle: 'お申込みありがとうございます',
          itemLabel: '講習会',
          icon: GraduationCap,
          iconColor: 'text-purple-600',
          iconBg: 'bg-purple-100',
        };
      case 'certification':
        return {
          title: '検定申込が完了しました',
          subtitle: 'お申込みありがとうございます',
          itemLabel: '検定',
          icon: Trophy,
          iconColor: 'text-amber-600',
          iconBg: 'bg-amber-100',
        };
      default:
        return {
          title: '購入が完了しました',
          subtitle: 'ご購入ありがとうございます',
          itemLabel: 'コース',
          icon: CheckCircle2,
          iconColor: 'text-green-600',
          iconBg: 'bg-green-100',
        };
    }
  };

  const typeConfig = getTypeConfig();

  if (!purchaseResult) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <div className="animate-pulse text-gray-500">読み込み中...</div>
      </div>
    );
  }

  const TypeIcon = typeConfig.icon;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <main className="max-w-[390px] mx-auto px-4 py-8 pb-24">
        <div className="text-center mb-8">
          <div className={`inline-flex items-center justify-center w-24 h-24 rounded-full ${typeConfig.iconBg} mb-6`}>
            <TypeIcon className={`h-14 w-14 ${typeConfig.iconColor}`} />
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">{typeConfig.title}</h1>
          <p className="text-gray-600">{typeConfig.subtitle}</p>
        </div>

        <Card className="rounded-2xl shadow-lg mb-6">
          <CardContent className="p-6 space-y-4">
            <div className="text-center pb-4 border-b">
              <p className="text-sm text-gray-500 mb-1">注文番号</p>
              <p className="text-lg font-mono font-semibold text-gray-800">
                {purchaseResult.orderId}
              </p>
            </div>

            <div>
              <p className="text-sm text-gray-500 mb-1">お子様</p>
              <p className="font-semibold text-gray-800">{purchaseResult.childName}</p>
            </div>

            <div>
              <p className="text-sm text-gray-500 mb-1">{typeConfig.itemLabel}</p>
              <p className="font-semibold text-gray-800">{purchaseResult.courseName}</p>
            </div>

            {purchaseResult.startDate && (
              <div>
                <p className="text-sm text-gray-500 mb-1">契約開始日</p>
                <p className="font-semibold text-gray-800">
                  {format(parseISO(purchaseResult.startDate), 'yyyy年MM月dd日（E）', { locale: ja })}
                </p>
              </div>
            )}

            {purchaseResult.bookedClass && (
              <div className="border-t pt-4">
                <p className="text-sm text-gray-500 mb-1">予約済みレッスン</p>
                <div className="bg-green-50 rounded-lg p-3 border border-green-200">
                  <p className="font-semibold text-green-800">
                    {format(parseISO(purchaseResult.bookedClass.date), 'M月d日（E）', { locale: ja })}
                  </p>
                  <p className="text-sm text-green-700">{purchaseResult.bookedClass.time}</p>
                  <p className="text-xs text-green-600">{purchaseResult.bookedClass.schoolName}</p>
                </div>
              </div>
            )}

            <div className="pt-4 border-t">
              <div className="flex justify-between items-center">
                <span className="text-lg font-semibold text-gray-800">お支払い金額</span>
                <span className="text-2xl font-bold text-blue-600">
                  ¥{purchaseResult.amount.toLocaleString()}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-xl shadow-md bg-blue-50 border-blue-200 mb-6">
          <CardContent className="p-4">
            <h3 className="font-semibold text-gray-800 mb-2">次のステップ</h3>
            <ul className="space-y-2 text-sm text-gray-700">
              {(purchaseResult.type === 'seminar' || purchaseType === 'seminar') ? (
                <>
                  <li className="flex items-start gap-2">
                    <GraduationCap className="h-4 w-4 text-purple-600 mt-0.5 shrink-0" />
                    <span>講習会の詳細は後日ご連絡いたします</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Calendar className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                    <span>講習日程は「カレンダー」画面から確認できます</span>
                  </li>
                </>
              ) : (purchaseResult.type === 'certification' || purchaseType === 'certification') ? (
                <>
                  <li className="flex items-start gap-2">
                    <Trophy className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                    <span>検定の詳細は後日ご連絡いたします</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Calendar className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                    <span>検定日程は「カレンダー」画面から確認できます</span>
                  </li>
                </>
              ) : (
                <>
                  <li className="flex items-start gap-2">
                    <Ticket className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                    <span>チケットは「チケット」画面から確認できます</span>
                  </li>
                  {purchaseResult.bookedClass ? (
                    <li className="flex items-start gap-2">
                      <Calendar className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
                      <span>初回レッスンの予約が完了しています</span>
                    </li>
                  ) : (
                    <li className="flex items-start gap-2">
                      <Calendar className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                      <span>レッスンの予約は「カレンダー」画面から行えます</span>
                    </li>
                  )}
                </>
              )}
            </ul>
          </CardContent>
        </Card>

        <div className="space-y-3">
          {!(purchaseResult.type === 'seminar' || purchaseType === 'seminar' || purchaseResult.type === 'certification' || purchaseType === 'certification') && (
            <Link href="/tickets" className="block">
              <Button className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg">
                <Ticket className="h-5 w-5 mr-2" />
                チケットを確認する
              </Button>
            </Link>
          )}

          <Link href="/calendar" className="block">
            <Button
              variant={(purchaseResult.type === 'seminar' || purchaseType === 'seminar' || purchaseResult.type === 'certification' || purchaseType === 'certification') ? 'default' : 'outline'}
              className={`w-full h-14 rounded-full font-semibold text-lg ${(purchaseResult.type === 'seminar' || purchaseType === 'seminar' || purchaseResult.type === 'certification' || purchaseType === 'certification') ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'border-2'}`}
            >
              <Calendar className="h-5 w-5 mr-2" />
              カレンダーを確認する
            </Button>
          </Link>

          <Link href="/" className="block">
            <Button
              variant="ghost"
              className="w-full h-12 text-gray-600 font-medium"
            >
              <Home className="h-5 w-5 mr-2" />
              ホームに戻る
            </Button>
          </Link>
        </div>
      </main>

      <BottomTabBar />
    </div>
  );
}

export default function PurchaseCompletePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <div className="animate-pulse text-gray-500">読み込み中...</div>
      </div>
    }>
      <PurchaseCompleteContent />
    </Suspense>
  );
}
