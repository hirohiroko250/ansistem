'use client';

import { useState } from 'react';
import { ChevronLeft, Building2, Edit, Loader2, BookOpen, ArrowUpCircle, ArrowDownCircle, ChevronRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { getAccountTypeLabel, getNextWithdrawalDate } from '@/lib/api/payment';
import { AuthGuard } from '@/components/auth';
import { usePaymentInfo, usePassbookData } from '@/lib/hooks/use-payment';

function PaymentContent() {
  // React Queryフックを使用
  const { data: payment, isLoading: loading } = usePaymentInfo();

  // 通帳（入出金履歴）用の状態
  const [isPassbookOpen, setIsPassbookOpen] = useState(false);
  const { data: passbookData, isLoading: isLoadingPassbook } = usePassbookData(isPassbookOpen);

  // 通帳を開く
  const openPassbook = () => {
    setIsPassbookOpen(true);
  };

  // 取引タイプに応じたアイコンと色を取得
  const getTransactionStyle = (type: string) => {
    switch (type) {
      case 'deposit':
        return { icon: ArrowDownCircle, color: 'text-green-600', bgColor: 'bg-green-100', label: '入金' };
      case 'offset':
        return { icon: ArrowUpCircle, color: 'text-blue-600', bgColor: 'bg-blue-100', label: '相殺' };
      case 'refund':
        return { icon: ArrowUpCircle, color: 'text-orange-600', bgColor: 'bg-orange-100', label: '返金' };
      case 'adjustment':
        return { icon: ArrowUpCircle, color: 'text-gray-600', bgColor: 'bg-gray-100', label: '調整' };
      default:
        return { icon: ArrowUpCircle, color: 'text-gray-600', bgColor: 'bg-gray-100', label: type };
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const hasPaymentInfo = payment?.paymentRegistered && payment?.bankName;

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
                      <span className="font-medium text-gray-800">{payment?.bankName || '-'}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">支店名</span>
                      <span className="font-medium text-gray-800">{payment?.branchName || '-'}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">口座種別</span>
                      <span className="font-medium text-gray-800">
                        {payment?.accountType ? getAccountTypeLabel(payment.accountType) : '-'}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">口座番号</span>
                      <span className="font-medium text-gray-800">{payment?.accountNumberMasked || '-'}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">口座名義</span>
                      <span className="font-medium text-gray-800">{payment?.accountHolderKana || payment?.accountHolder || '-'}</span>
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
                    {payment?.withdrawalDay ? `毎月${payment.withdrawalDay}日` : '-'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">次回引き落とし</span>
                  <span className="font-medium text-gray-800">
                    {getNextWithdrawalDate(payment?.withdrawalDay ?? null)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 入出金履歴（通帳）カード */}
        <Card
          className="rounded-xl shadow-md mb-6 border-indigo-200 bg-gradient-to-r from-indigo-50 to-purple-50 cursor-pointer hover:shadow-lg transition-shadow"
          onClick={openPassbook}
        >
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center">
                  <BookOpen className="h-5 w-5 text-indigo-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-indigo-900">入出金履歴（通帳）</h3>
                  <p className="text-xs text-indigo-600">預り金残高・取引履歴を確認</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {passbookData && (
                  <Badge className="bg-indigo-100 text-indigo-700">
                    残高: ¥{passbookData.current_balance.toLocaleString()}
                  </Badge>
                )}
                <ChevronRight className="h-5 w-5 text-indigo-400" />
              </div>
            </div>
          </CardContent>
        </Card>

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

      {/* 通帳モーダル */}
      <Dialog open={isPassbookOpen} onOpenChange={setIsPassbookOpen}>
        <DialogContent className="max-w-[95vw] max-h-[85vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-indigo-600" />
              入出金履歴（通帳）
            </DialogTitle>
          </DialogHeader>

          {isLoadingPassbook ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
            </div>
          ) : passbookData ? (
            <div className="flex-1 overflow-auto">
              {/* 残高表示 */}
              <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-4 mb-4 text-white">
                <p className="text-sm opacity-90">現在の預り金残高</p>
                <p className="text-3xl font-bold">
                  ¥{passbookData.current_balance.toLocaleString()}
                </p>
              </div>

              {/* 取引履歴 */}
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">取引履歴</h4>
                {passbookData.transactions.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    取引履歴がありません
                  </div>
                ) : (
                  passbookData.transactions.map((tx) => {
                    const style = getTransactionStyle(tx.transaction_type);
                    const Icon = style.icon;
                    return (
                      <div
                        key={tx.id}
                        className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-100 shadow-sm"
                      >
                        <div className={`w-9 h-9 rounded-full ${style.bgColor} flex items-center justify-center`}>
                          <Icon className={`w-5 h-5 ${style.color}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded ${style.bgColor} ${style.color}`}>
                              {tx.transaction_type_display || style.label}
                            </span>
                            <span className="text-xs text-gray-500">
                              {new Date(tx.created_at).toLocaleDateString('ja-JP')}
                            </span>
                          </div>
                          <p className="text-sm text-gray-700 truncate mt-1">
                            {tx.invoice_billing_label || tx.reason || '-'}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className={`font-semibold ${tx.transaction_type === 'deposit' ? 'text-green-600' : 'text-gray-800'}`}>
                            {tx.transaction_type === 'deposit' ? '+' : '-'}¥{Math.abs(tx.amount).toLocaleString()}
                          </p>
                          <p className="text-xs text-gray-500">
                            残高: ¥{tx.balance_after.toLocaleString()}
                          </p>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              データを取得できませんでした
            </div>
          )}
        </DialogContent>
      </Dialog>

      <BottomTabBar />
    </div>
  );
}

export default function PaymentPage() {
  return (
    <AuthGuard>
      <PaymentContent />
    </AuthGuard>
  );
}
