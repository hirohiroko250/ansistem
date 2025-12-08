'use client';

import { useEffect, useState } from 'react';
import { ChevronLeft, Building2, Edit, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import {
  getMyPayment,
  getAccountTypeLabel,
  getNextWithdrawalDate,
  type PaymentInfo
} from '@/lib/api/payment';

export default function PaymentPage() {
  const [payment, setPayment] = useState<PaymentInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPayment();
  }, []);

  const fetchPayment = async () => {
    try {
      setLoading(true);
      const data = await getMyPayment();
      setPayment(data);
    } catch (error) {
      console.error('Failed to fetch payment:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const hasPaymentInfo = payment?.payment_registered && payment?.bank_name;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/settings" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">支払い方法</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        <Card className="rounded-xl shadow-md mb-6">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <h2 className="text-lg font-bold text-gray-800">現在の支払い方法</h2>
                  <Badge className={hasPaymentInfo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}>
                    {hasPaymentInfo ? '登録済み' : '未登録'}
                  </Badge>
                </div>
                <p className="text-sm text-gray-600">メインの支払い方法</p>
              </div>
            </div>

            {hasPaymentInfo ? (
              <Card className="rounded-lg border-2 border-blue-200 bg-blue-50">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                      <Building2 className="h-6 w-6 text-blue-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-800">銀行口座</h3>
                      <p className="text-sm text-gray-600">口座振替</p>
                    </div>
                  </div>
                  <div className="space-y-2 bg-white rounded-lg p-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">金融機関</span>
                      <span className="font-medium text-gray-800">{payment?.bank_name || '-'}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">支店名</span>
                      <span className="font-medium text-gray-800">{payment?.branch_name || '-'}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">口座種別</span>
                      <span className="font-medium text-gray-800">
                        {payment?.account_type ? getAccountTypeLabel(payment.account_type) : '-'}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">口座番号</span>
                      <span className="font-medium text-gray-800">{payment?.account_number_masked || '-'}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">口座名義</span>
                      <span className="font-medium text-gray-800">{payment?.account_holder_kana || payment?.account_holder || '-'}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="rounded-lg border-2 border-dashed border-gray-300 bg-gray-50">
                <CardContent className="p-6 text-center">
                  <Building2 className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                  <p className="text-gray-600 mb-2">支払い方法が登録されていません</p>
                  <p className="text-sm text-gray-500">
                    銀行口座を登録して、口座振替での支払いを設定してください
                  </p>
                </CardContent>
              </Card>
            )}
          </CardContent>
        </Card>

        {hasPaymentInfo && (
          <Card className="rounded-xl shadow-md mb-6">
            <CardContent className="p-6">
              <h3 className="text-base font-semibold text-gray-800 mb-3">支払いスケジュール</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">引き落とし日</span>
                  <span className="font-medium text-gray-800">
                    {payment?.withdrawal_day ? `毎月${payment.withdrawal_day}日` : '-'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">次回引き落とし</span>
                  <span className="font-medium text-gray-800">
                    {getNextWithdrawalDate(payment?.withdrawal_day ?? null)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <Card className="rounded-xl shadow-md mb-6 border-orange-200 bg-orange-50">
          <CardContent className="p-4">
            <h3 className="text-sm font-semibold text-orange-900 mb-2">ご注意</h3>
            <ul className="text-xs text-orange-800 space-y-1">
              <li>• 引き落とし日が金融機関の休業日の場合、翌営業日に引き落とされます</li>
              <li>• 残高不足の場合、再度引き落としが実施される場合があります</li>
              <li>• 支払い方法の変更は、次回請求から適用されます</li>
            </ul>
          </CardContent>
        </Card>

        <Link href="/settings/payment/edit">
          <Button className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg flex items-center justify-center gap-2">
            <Edit className="h-5 w-5" />
            {hasPaymentInfo ? '支払い方法を変更する' : '支払い方法を登録する'}
          </Button>
        </Link>
      </main>

      <BottomTabBar />
    </div>
  );
}
