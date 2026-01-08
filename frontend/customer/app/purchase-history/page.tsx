'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, FileText, ChevronRight, Loader2, Download, RotateCcw } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import { useRouter } from 'next/navigation';
import { getAllStudentItems, downloadAndSaveReceipt, type PurchasedItem } from '@/lib/api/students';
import { isAuthenticated } from '@/lib/api/auth';

// 月別集計データ型
type MonthSummary = {
  month: string; // YYYY-MM形式
  displayMonth: string; // 表示用 (2024年9月)
  category: string; // 区分（入金、請求など）
  billingAmount: number; // 請求金額
  paymentAmount: number; // 入金金額
  description: string; // 摘要
  balance: number; // 預り金過不足
  cumulative: number; // 累計
  hasReceipt: boolean; // 領収書発行可能か
};

export default function PassbookListPage() {
  const router = useRouter();
  const [allItems, setAllItems] = useState<PurchasedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [monthSummaries, setMonthSummaries] = useState<MonthSummary[]>([]);
  const [isPortrait, setIsPortrait] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // 画面向き検出
  useEffect(() => {
    const checkOrientation = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) {
        setIsPortrait(window.innerHeight > window.innerWidth);
      } else {
        setIsPortrait(false);
      }
    };

    checkOrientation();
    window.addEventListener('resize', checkOrientation);
    window.addEventListener('orientationchange', checkOrientation);

    return () => {
      window.removeEventListener('resize', checkOrientation);
      window.removeEventListener('orientationchange', checkOrientation);
    };
  }, []);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }
    fetchData();
  }, [router]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const items = await getAllStudentItems();
      setAllItems(items);

      // 月別に集計
      const summaries = createMonthSummaries(items);
      setMonthSummaries(summaries);
      setError(null);
    } catch (err: unknown) {
      console.error('Failed to fetch purchase history:', err);
      if (err && typeof err === 'object' && 'message' in err) {
        const errorMessage = (err as { message: string }).message;
        if (errorMessage.includes('401') || errorMessage.includes('認証')) {
          router.push('/login');
          return;
        }
      }
      setError('通帳データの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // 月別集計データを作成
  const createMonthSummaries = (items: PurchasedItem[]): MonthSummary[] => {
    // 月ごとにグループ化
    const monthMap = new Map<string, PurchasedItem[]>();

    items.forEach(item => {
      const month = item.billingMonth;
      if (!monthMap.has(month)) {
        monthMap.set(month, []);
      }
      monthMap.get(month)!.push(item);
    });

    // 集計データを作成
    const summaries: MonthSummary[] = [];
    let cumulative = 0;

    // 月を昇順でソート
    const sortedMonths = Array.from(monthMap.keys()).sort();

    sortedMonths.forEach(month => {
      const monthItems = monthMap.get(month)!;
      const totalAmount = monthItems.reduce((sum, item) => sum + item.finalPrice, 0);

      // 入金があったかどうか（仮に請求月の翌月に入金とする）
      const isPaid = new Date(month) < new Date();

      cumulative += totalAmount;

      const displayMonth = format(new Date(month + '-01'), 'yyyy年M月', { locale: ja });

      summaries.push({
        month,
        displayMonth,
        category: isPaid ? '入金' : '請求',
        billingAmount: totalAmount,
        paymentAmount: isPaid ? totalAmount : 0,
        description: isPaid ? '請求' : '請求予定',
        balance: 0,
        cumulative,
        hasReceipt: isPaid,
      });
    });

    // 新しい順に並べ替え
    return summaries.reverse();
  };

  // 領収書ダウンロード
  const [downloadingMonth, setDownloadingMonth] = useState<string | null>(null);

  const handleDownloadReceipt = async (month: string) => {
    try {
      setDownloadingMonth(month);
      // month は "YYYY-MM" 形式
      const [yearStr, monthStr] = month.split('-');
      const year = parseInt(yearStr, 10);
      const monthNum = parseInt(monthStr, 10);

      await downloadAndSaveReceipt(year, monthNum);
    } catch (err: unknown) {
      console.error('領収書のダウンロードに失敗しました:', err);
      const errorMessage = err && typeof err === 'object' && 'message' in err
        ? (err as { message: string }).message
        : '領収書のダウンロードに失敗しました';
      alert(errorMessage);
    } finally {
      setDownloadingMonth(null);
    }
  };

  // スマホ縦向き時は回転を促すメッセージ
  if (isMobile && isPortrait) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center">
        <div className="text-center text-white p-8">
          <RotateCcw className="h-16 w-16 mx-auto mb-6 animate-pulse" />
          <h2 className="text-xl font-bold mb-3">画面を横向きにしてください</h2>
          <p className="text-blue-200 text-sm">
            通帳画面は横向き表示に最適化されています
          </p>
          <div className="mt-8">
            <Link href="/">
              <Button variant="outline" className="text-white border-white hover:bg-white/20">
                <ChevronLeft className="h-4 w-4 mr-1" />
                ホームに戻る
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-full mx-auto px-4 h-14 flex items-center">
            <Link href="/" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <h1 className="text-lg font-bold text-gray-800 flex-1 text-center">通帳</h1>
            <div className="w-9" />
          </div>
        </header>
        <main className="px-4 py-6 flex items-center justify-center min-h-[50vh]">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-2" />
            <p className="text-gray-500">読み込み中...</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* コンパクトなヘッダー（横向き時） */}
      <header className="sticky top-0 z-40 bg-blue-600 text-white shadow-sm">
        <div className="max-w-full mx-auto px-4 h-10 flex items-center">
          <Link href="/" className="mr-3 hover:bg-blue-700 rounded p-1">
            <ChevronLeft className="h-5 w-5" />
          </Link>
          <h1 className="text-sm font-bold flex-1">通帳</h1>
          <span className="text-xs text-blue-200">横スクロールで全項目表示</span>
        </div>
      </header>

      <main className="px-2 py-2">
        {error && (
          <Card className="rounded-lg shadow-md bg-red-50 border-red-200 mb-2 mx-1">
            <CardContent className="p-3">
              <p className="text-red-600 text-sm">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* 横スクロール可能なテーブル */}
        <div className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-50px)]">
          <table className="w-full min-w-[900px] bg-white shadow-md text-xs">
            <thead className="sticky top-0">
              <tr className="bg-blue-600 text-white">
                <th className="px-2 py-1.5 text-left font-semibold whitespace-nowrap">No</th>
                <th className="px-2 py-1.5 text-left font-semibold whitespace-nowrap">区分</th>
                <th className="px-2 py-1.5 text-left font-semibold whitespace-nowrap">請求年月</th>
                <th className="px-2 py-1.5 text-right font-semibold whitespace-nowrap">請求金額</th>
                <th className="px-2 py-1.5 text-right font-semibold whitespace-nowrap">入金金額</th>
                <th className="px-2 py-1.5 text-left font-semibold whitespace-nowrap">摘要</th>
                <th className="px-2 py-1.5 text-right font-semibold whitespace-nowrap">預り金過不足</th>
                <th className="px-2 py-1.5 text-right font-semibold whitespace-nowrap">累計</th>
                <th className="px-2 py-1.5 text-center font-semibold whitespace-nowrap">領収書</th>
                <th className="px-2 py-1.5 text-center font-semibold whitespace-nowrap">詳細</th>
              </tr>
            </thead>
            <tbody>
              {monthSummaries.length > 0 ? (
                monthSummaries.map((summary, index) => (
                  <tr
                    key={summary.month}
                    className={`border-b border-gray-200 hover:bg-blue-50 transition-colors ${
                      index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                    }`}
                  >
                    <td className="px-2 py-1.5 text-gray-700">{monthSummaries.length - index}</td>
                    <td className="px-2 py-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        summary.category === '入金'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-orange-100 text-orange-700'
                      }`}>
                        {summary.category}
                      </span>
                    </td>
                    <td className="px-2 py-1.5 text-gray-700 whitespace-nowrap">{summary.displayMonth}</td>
                    <td className="px-2 py-1.5 text-right text-gray-700 tabular-nums">
                      ¥{summary.billingAmount.toLocaleString()}
                    </td>
                    <td className="px-2 py-1.5 text-right tabular-nums">
                      {summary.paymentAmount > 0 ? (
                        <span className="text-green-600 font-medium">
                          ¥{summary.paymentAmount.toLocaleString()}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-2 py-1.5 text-gray-700">{summary.description}</td>
                    <td className="px-2 py-1.5 text-right tabular-nums">
                      {summary.balance !== 0 ? (
                        <span className={summary.balance > 0 ? 'text-green-600' : 'text-red-600'}>
                          ¥{summary.balance.toLocaleString()}
                        </span>
                      ) : (
                        <span className="text-gray-400">¥0</span>
                      )}
                    </td>
                    <td className="px-2 py-1.5 text-right text-gray-700 tabular-nums">
                      ¥{summary.cumulative.toLocaleString()}
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      {summary.hasReceipt ? (
                        <button
                          onClick={() => handleDownloadReceipt(summary.month)}
                          disabled={downloadingMonth === summary.month}
                          className={`text-[10px] font-medium ${
                            downloadingMonth === summary.month
                              ? 'text-gray-400 cursor-wait'
                              : 'text-blue-600 hover:text-blue-700 hover:underline'
                          }`}
                        >
                          {downloadingMonth === summary.month ? '発行中...' : '領収書発行'}
                        </button>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      <Link
                        href={`/purchase-history/${summary.month}`}
                        className="text-blue-600 hover:text-blue-700 hover:underline text-[10px] font-medium"
                      >
                        詳細→
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={10} className="px-4 py-6 text-center text-gray-500">
                    取引履歴がありません
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

      </main>
    </div>
  );
}
