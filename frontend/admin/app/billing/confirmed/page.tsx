'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/lib/api/client';
import { ConfirmedBilling, ConfirmedBillingSummary } from '@/lib/api/types';
import {
  FileCheck,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Eye,
  CreditCard,
  RefreshCw,
  Download,
  Search,
  Building2,
  Plus,
} from 'lucide-react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';

export default function ConfirmedBillingPage() {
  const router = useRouter();
  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1;

  const [year, setYear] = useState<number | null>(null);
  const [month, setMonth] = useState<number | null>(null);
  const [billingYear, setBillingYear] = useState(currentYear);
  const [billingMonth, setBillingMonth] = useState(currentMonth);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [confirmedBillings, setConfirmedBillings] = useState<ConfirmedBilling[]>([]);
  const [summary, setSummary] = useState<ConfirmedBillingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const pageSize = 20;

  // 詳細ダイアログ
  const [selectedBilling, setSelectedBilling] = useState<ConfirmedBilling | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  // 入金記録ダイアログ
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [recordingPayment, setRecordingPayment] = useState(false);

  // 引落データエクスポート
  const [exportingDebit, setExportingDebit] = useState<string | null>(null);

  // 締日情報を取得して請求月を設定
  useEffect(() => {
    const fetchDeadlines = async () => {
      try {
        const data = await apiClient.get<{
          currentYear: number;
          currentMonth: number;
          billingYear?: number;
          billingMonth?: number;
        }>('/billing/deadlines/status_list/');

        // 請求月をデフォルト値として設定
        const targetYear = data.billingYear || data.currentYear || currentYear;
        const targetMonth = data.billingMonth || data.currentMonth || currentMonth;
        setBillingYear(targetYear);
        setBillingMonth(targetMonth);
        setYear(targetYear);
        setMonth(targetMonth);
      } catch (error) {
        console.error('Failed to fetch deadlines:', error);
        // フォールバック: 現在の日付を使用
        setYear(currentYear);
        setMonth(currentMonth);
      }
    };
    fetchDeadlines();
  }, []);

  // データ取得
  useEffect(() => {
    if (year !== null && month !== null) {
      fetchData();
    }
  }, [year, month, statusFilter, page, searchQuery]);

  const fetchData = async () => {
    if (year === null || month === null) return;

    setLoading(true);
    try {
      // 一覧取得
      const params: Record<string, string> = {
        year: year.toString(),
        month: month.toString(),
        page: page.toString(),
        page_size: pageSize.toString(),
      };
      if (statusFilter) {
        params.status = statusFilter;
      }
      if (searchQuery) {
        params.search = searchQuery;
      }

      const queryString = new URLSearchParams(params).toString();
      const response = await apiClient.get<{
        data: ConfirmedBilling[];
        meta: { total: number; page: number; limit: number; totalPages: number };
      }>(`/billing/confirmed/?${queryString}`);

      setConfirmedBillings(response.data || []);
      setTotalCount(response.meta?.total || 0);

      // サマリー取得
      const summaryData = await apiClient.get<ConfirmedBillingSummary>(
        `/billing/confirmed/monthly_summary/?year=${year}&month=${month}`
      );
      setSummary(summaryData);
    } catch (error) {
      console.error('Failed to fetch confirmed billings:', error);
    } finally {
      setLoading(false);
    }
  };

  // 確定データ生成（非同期）
  const handleGenerateConfirmedBilling = async () => {
    if (year === null || month === null) return;

    if (!confirm(`${year}年${month}月分の請求確定データを生成しますか？\n\n※処理には数分かかる場合があります。`)) {
      return;
    }

    setGenerating(true);
    try {
      // 非同期APIを呼び出し
      const startResponse = await apiClient.post<{
        success: boolean;
        taskId: string;
        message: string;
      }>('/billing/confirmed/create_confirmed_billing_async/', {
        year,
        month,
      });

      if (startResponse.success && startResponse.taskId) {
        // タスクの完了をポーリング
        const taskId = startResponse.taskId;
        let attempts = 0;
        const maxAttempts = 120; // 最大10分（5秒×120回）

        while (attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, 5000)); // 5秒待機
          attempts++;

          try {
            const statusResponse = await apiClient.get<{
              taskId: string;
              status: string;
              result?: {
                success: boolean;
                createdCount: number;
                updatedCount: number;
                errorCount: number;
                totalBillings: number;
                totalAmount: number;
              };
              error?: string;
              progress?: { current: number; total: number };
            }>(`/billing/confirmed/task_status/${taskId}/`);

            if (statusResponse.status === 'SUCCESS' && statusResponse.result) {
              const result = statusResponse.result;
              alert(
                `請求確定データを生成しました。\n` +
                  `新規作成: ${result.createdCount ?? 0}件\n` +
                  `更新: ${result.updatedCount ?? 0}件\n` +
                  `合計: ${result.totalBillings ?? 0}件\n` +
                  `総額: ${(result.totalAmount ?? 0).toLocaleString()}円` +
                  ((result.errorCount ?? 0) > 0
                    ? `\nエラー: ${result.errorCount}件`
                    : '')
              );
              fetchData();
              break;
            } else if (statusResponse.status === 'FAILURE') {
              throw new Error(statusResponse.error || '処理に失敗しました');
            }
            // PENDING or PROGRESS - continue polling
          } catch (pollError) {
            console.error('Polling error:', pollError);
            // ポーリングエラーは無視して継続
          }
        }

        if (attempts >= maxAttempts) {
          alert('処理がタイムアウトしました。しばらく待ってから更新ボタンを押してください。');
          fetchData();
        }
      }
    } catch (error: unknown) {
      console.error('Failed to generate confirmed billing:', error);
      // 同期APIにフォールバック
      try {
        const response = await apiClient.post<{
          success: boolean;
          createdCount: number;
          updatedCount: number;
          skippedCount: number;
          errorCount: number;
        }>('/billing/confirmed/create_confirmed_billing/', {
          year,
          month,
        });

        if (response.success) {
          alert(
            `請求確定データを生成しました。\n` +
              `新規作成: ${response.createdCount ?? 0}件\n` +
              `更新: ${response.updatedCount ?? 0}件\n` +
              `スキップ: ${response.skippedCount ?? 0}件` +
              ((response.errorCount ?? 0) > 0
                ? `\nエラー: ${response.errorCount}件`
                : '')
          );
          fetchData();
        }
      } catch (fallbackError) {
        console.error('Fallback also failed:', fallbackError);
        alert('請求確定データの生成に失敗しました');
      }
    } finally {
      setGenerating(false);
    }
  };

  // 入金記録
  const handleRecordPayment = async () => {
    if (!selectedBilling || !paymentAmount) return;

    const amount = parseInt(paymentAmount, 10);
    if (isNaN(amount) || amount <= 0) {
      alert('有効な金額を入力してください');
      return;
    }

    setRecordingPayment(true);
    try {
      await apiClient.post(`/billing/confirmed/${selectedBilling.id}/record_payment/`, {
        amount,
      });
      alert('入金を記録しました');
      setPaymentDialogOpen(false);
      setPaymentAmount('');
      fetchData();
    } catch (error) {
      console.error('Failed to record payment:', error);
      alert('入金の記録に失敗しました');
    } finally {
      setRecordingPayment(false);
    }
  };

  // 検索実行
  const handleSearch = () => {
    setSearchQuery(searchInput);
    setPage(1);
  };

  // 検索クリア
  const handleClearSearch = () => {
    setSearchInput('');
    setSearchQuery('');
    setPage(1);
  };

  // 引落データダウンロード
  const handleExportDebit = async (provider: 'jaccs' | 'ufj_factor' | 'chukyo_finance') => {
    if (year === null || month === null) return;

    const providerNames = {
      jaccs: 'JACCS',
      ufj_factor: 'UFJファクター',
      chukyo_finance: '中京ファイナンス',
    };

    setExportingDebit(provider);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/billing/confirmed/export-debit/?year=${year}&month=${month}&provider=${provider}`,
        {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('引落データダウンロードに失敗しました');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `debit_${provider}_${year}_${month}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to export debit data:', error);
      alert(`${providerNames[provider]}引落データのダウンロードに失敗しました`);
    } finally {
      setExportingDebit(null);
    }
  };

  // CSVダウンロード
  const handleDownloadCSV = async () => {
    if (year === null || month === null) return;

    setDownloading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/billing/confirmed/export_csv/?year=${year}&month=${month}`,
        {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('CSVダウンロードに失敗しました');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `confirmed_billing_${year}_${month}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download CSV:', error);
      alert('CSVダウンロードに失敗しました');
    } finally {
      setDownloading(false);
    }
  };

  // ステータスバッジの色
  const getStatusBadge = (status: string, statusDisplay: string) => {
    const colors: Record<string, string> = {
      confirmed: 'bg-blue-100 text-blue-800',
      unpaid: 'bg-yellow-100 text-yellow-800',
      partial: 'bg-orange-100 text-orange-800',
      paid: 'bg-green-100 text-green-800',
      cancelled: 'bg-gray-100 text-gray-800',
    };
    return (
      <Badge className={colors[status] || 'bg-gray-100 text-gray-800'}>
        {statusDisplay}
      </Badge>
    );
  };

  // 月の選択肢を生成（請求年月を基準に前後の月を含める）
  const monthOptions = [];
  const baseYear = billingYear || currentYear;
  const baseMonth = billingMonth || currentMonth;

  // 請求月から2年先までと2年前までを含める
  for (let y = baseYear + 1; y >= baseYear - 2; y--) {
    for (let m = 12; m >= 1; m--) {
      // 請求月より1年以上先の月はスキップ
      if (y > baseYear + 1 || (y === baseYear + 1 && m > baseMonth)) continue;
      monthOptions.push({ year: y, month: m });
    }
  }

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="container mx-auto py-6 px-4">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">請求確定データ</h1>
          <p className="text-muted-foreground text-sm">
            締日確定時に保存された請求データのスナップショット
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => router.push('/billing')}
        >
          請求管理へ戻る
        </Button>
      </div>

      {/* フィルター */}
      <Card className="mb-6">
        <CardContent className="pt-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Label>対象月:</Label>
              <Select
                value={year && month ? `${year}-${month}` : ''}
                onValueChange={(value) => {
                  const [y, m] = value.split('-').map(Number);
                  setYear(y);
                  setMonth(m);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="読み込み中..." />
                </SelectTrigger>
                <SelectContent>
                  {monthOptions.map((opt) => (
                    <SelectItem
                      key={`${opt.year}-${opt.month}`}
                      value={`${opt.year}-${opt.month}`}
                    >
                      {opt.year}年{opt.month}月分
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Label>ステータス:</Label>
              <Select
                value={statusFilter || 'all'}
                onValueChange={(value) => {
                  setStatusFilter(value === 'all' ? '' : value);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="すべて" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">すべて</SelectItem>
                  <SelectItem value="confirmed">確定</SelectItem>
                  <SelectItem value="unpaid">未入金</SelectItem>
                  <SelectItem value="partial">一部入金</SelectItem>
                  <SelectItem value="paid">入金済</SelectItem>
                  <SelectItem value="cancelled">取消</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Label>検索:</Label>
              <div className="flex items-center gap-1">
                <Input
                  className="w-[200px]"
                  placeholder="ID・名前で検索..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSearch();
                  }}
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleSearch}
                  disabled={loading}
                >
                  <Search className="w-4 h-4" />
                </Button>
                {searchQuery && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearSearch}
                  >
                    クリア
                  </Button>
                )}
              </div>
            </div>

            <div className="flex-1" />

            <Button
              variant="outline"
              onClick={fetchData}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              更新
            </Button>

            <Button
              variant="outline"
              onClick={handleDownloadCSV}
              disabled={downloading || !confirmedBillings.length}
            >
              {downloading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Download className="w-4 h-4 mr-2" />
              )}
              CSVダウンロード
            </Button>

            {/* 引落データ出力ドロップダウン */}
            <Select
              value=""
              onValueChange={(value) => {
                if (value === 'jaccs' || value === 'ufj_factor' || value === 'chukyo_finance') {
                  handleExportDebit(value);
                }
              }}
              disabled={!!exportingDebit || !confirmedBillings.length}
            >
              <SelectTrigger className="w-[180px]">
                {exportingDebit ? (
                  <div className="flex items-center">
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    エクスポート中...
                  </div>
                ) : (
                  <div className="flex items-center">
                    <Building2 className="w-4 h-4 mr-2" />
                    引落データ出力
                  </div>
                )}
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="jaccs">JACCS</SelectItem>
                <SelectItem value="ufj_factor">UFJファクター</SelectItem>
                <SelectItem value="chukyo_finance">中京ファイナンス</SelectItem>
              </SelectContent>
            </Select>

            <Button
              variant="outline"
              onClick={() => router.push('/billing/add-item')}
            >
              <Plus className="w-4 h-4 mr-2" />
              追加請求登録
            </Button>

            <Button
              onClick={handleGenerateConfirmedBilling}
              disabled={generating}
            >
              {generating ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <FileCheck className="w-4 h-4 mr-2" />
              )}
              確定データ生成
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* サマリー */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">
                請求件数
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{summary.totalCount ?? 0}件</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">
                請求総額
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {(summary.totalAmount ?? 0).toLocaleString()}円
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">
                入金済
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-green-600">
                {(summary.totalPaid ?? 0).toLocaleString()}円
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">
                回収率
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {summary.collectionRate ?? 0}%
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 一覧テーブル */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileCheck className="w-5 h-5" />
            {year && month ? `${year}年${month}月分` : ''} 請求確定一覧
            <span className="text-sm font-normal text-muted-foreground ml-2">
              ({totalCount}件)
            </span>
            {searchQuery && (
              <span className="text-sm font-normal text-blue-600 ml-2">
                「{searchQuery}」で検索中
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
          ) : confirmedBillings.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileCheck className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>確定データがありません</p>
              <p className="text-sm mt-1">
                「確定データ生成」ボタンで請求データを確定してください
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>生徒番号</TableHead>
                    <TableHead>生徒名</TableHead>
                    <TableHead>保護者番号</TableHead>
                    <TableHead>保護者名</TableHead>
                    <TableHead className="text-right">請求額</TableHead>
                    <TableHead className="text-right">入金済</TableHead>
                    <TableHead className="text-right">残高</TableHead>
                    <TableHead>支払方法</TableHead>
                    <TableHead>ステータス</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {confirmedBillings.map((billing) => (
                    <TableRow key={billing.id}>
                      <TableCell className="text-muted-foreground text-sm">
                        {billing.studentNo || '-'}
                      </TableCell>
                      <TableCell className="font-medium">
                        {billing.studentName || '-'}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {billing.guardianNo || '-'}
                      </TableCell>
                      <TableCell>{billing.guardianName}</TableCell>
                      <TableCell className="text-right">
                        {(billing.totalAmount ?? 0).toLocaleString()}円
                      </TableCell>
                      <TableCell className="text-right text-green-600">
                        {(billing.paidAmount ?? 0).toLocaleString()}円
                      </TableCell>
                      <TableCell className="text-right">
                        {(billing.balance ?? 0) > 0 ? (
                          <span className="text-red-600">
                            {(billing.balance ?? 0).toLocaleString()}円
                          </span>
                        ) : (
                          <span className="text-muted-foreground">0円</span>
                        )}
                      </TableCell>
                      <TableCell>{billing.paymentMethodDisplay}</TableCell>
                      <TableCell>
                        {getStatusBadge(billing.status, billing.statusDisplay)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedBilling(billing);
                              setDetailDialogOpen(true);
                            }}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          {billing.status !== 'paid' &&
                            billing.status !== 'cancelled' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setSelectedBilling(billing);
                                  setPaymentDialogOpen(true);
                                }}
                              >
                                <CreditCard className="w-4 h-4" />
                              </Button>
                            )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* ページネーション */}
              {totalPages > 1 && (
                <div className="flex justify-center items-center gap-2 mt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {page} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* 詳細ダイアログ */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>請求確定詳細</DialogTitle>
            <DialogDescription>
              {selectedBilling?.year}年{selectedBilling?.month}月分 -{' '}
              {selectedBilling?.studentName}
            </DialogDescription>
          </DialogHeader>
          {selectedBilling && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-muted-foreground">生徒名</Label>
                  <p className="font-medium">
                    {selectedBilling.studentName || '-'}
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">保護者名</Label>
                  <p className="font-medium">{selectedBilling.guardianName}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">請求額</Label>
                  <p className="font-medium">
                    {(selectedBilling.totalAmount ?? 0).toLocaleString()}円
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">ステータス</Label>
                  <p>
                    {getStatusBadge(
                      selectedBilling.status,
                      selectedBilling.statusDisplay
                    )}
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">入金済</Label>
                  <p className="font-medium text-green-600">
                    {(selectedBilling.paidAmount ?? 0).toLocaleString()}円
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">残高</Label>
                  <p
                    className={`font-medium ${
                      (selectedBilling.balance ?? 0) > 0
                        ? 'text-red-600'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {(selectedBilling.balance ?? 0).toLocaleString()}円
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">支払方法</Label>
                  <p>{selectedBilling.paymentMethodDisplay}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">確定日時</Label>
                  <p>
                    {format(
                      new Date(selectedBilling.confirmedAt),
                      'yyyy/MM/dd HH:mm',
                      { locale: ja }
                    )}
                  </p>
                </div>
              </div>

              {/* 明細 */}
              {selectedBilling.itemsSnapshot &&
                selectedBilling.itemsSnapshot.length > 0 && (
                  <div>
                    <Label className="text-muted-foreground mb-2 block">
                      明細
                    </Label>
                    <div className="border rounded-md">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>品目</TableHead>
                            <TableHead className="text-right">単価</TableHead>
                            <TableHead className="text-right">数量</TableHead>
                            <TableHead className="text-right">金額</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectedBilling.itemsSnapshot.map((item, idx) => (
                            <TableRow key={idx}>
                              <TableCell>
                                {item.product_name ||
                                  item.course_name ||
                                  item.brand_name ||
                                  '-'}
                              </TableCell>
                              <TableCell className="text-right">
                                {(parseInt(item.unit_price) || 0).toLocaleString()}円
                              </TableCell>
                              <TableCell className="text-right">
                                {item.quantity ?? 0}
                              </TableCell>
                              <TableCell className="text-right">
                                {(parseInt(item.final_price) || 0).toLocaleString()}円
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailDialogOpen(false)}>
              閉じる
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 入金記録ダイアログ */}
      <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>入金記録</DialogTitle>
            <DialogDescription>
              {selectedBilling?.studentName} - 残高:{' '}
              {(selectedBilling?.balance ?? 0).toLocaleString()}円
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="paymentAmount">入金額</Label>
              <Input
                id="paymentAmount"
                type="number"
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
                placeholder="金額を入力"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setPaymentDialogOpen(false);
                setPaymentAmount('');
              }}
            >
              キャンセル
            </Button>
            <Button
              onClick={handleRecordPayment}
              disabled={!paymentAmount || recordingPayment}
            >
              {recordingPayment && (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              )}
              記録する
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
