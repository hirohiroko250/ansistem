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
} from 'lucide-react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';

export default function ConfirmedBillingPage() {
  const router = useRouter();
  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1;

  const [year, setYear] = useState(currentYear);
  const [month, setMonth] = useState(currentMonth);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [confirmedBillings, setConfirmedBillings] = useState<ConfirmedBilling[]>([]);
  const [summary, setSummary] = useState<ConfirmedBillingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 20;

  // 詳細ダイアログ
  const [selectedBilling, setSelectedBilling] = useState<ConfirmedBilling | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  // 入金記録ダイアログ
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [recordingPayment, setRecordingPayment] = useState(false);

  // データ取得
  useEffect(() => {
    fetchData();
  }, [year, month, statusFilter, page]);

  const fetchData = async () => {
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

      const queryString = new URLSearchParams(params).toString();
      const response = await apiClient.get<{
        count: number;
        results: ConfirmedBilling[];
      }>(`/billing/confirmed/?${queryString}`);

      setConfirmedBillings(response.results || []);
      setTotalCount(response.count || 0);

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

  // 確定データ生成
  const handleGenerateConfirmedBilling = async () => {
    if (!confirm(`${year}年${month}月分の請求確定データを生成しますか？`)) {
      return;
    }

    setGenerating(true);
    try {
      const response = await apiClient.post<{
        success: boolean;
        createdCount: number;
        updatedCount: number;
        skippedCount: number;
        errorCount: number;
        errors: Array<{ studentName: string; error: string }>;
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
    } catch (error) {
      console.error('Failed to generate confirmed billing:', error);
      alert('請求確定データの生成に失敗しました');
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

  // 月の選択肢を生成
  const monthOptions = [];
  for (let y = currentYear; y >= currentYear - 2; y--) {
    for (let m = 12; m >= 1; m--) {
      if (y === currentYear && m > currentMonth + 2) continue;
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
                value={`${year}-${month}`}
                onValueChange={(value) => {
                  const [y, m] = value.split('-').map(Number);
                  setYear(y);
                  setMonth(m);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-[160px]">
                  <SelectValue />
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
              <p className="text-2xl font-bold">{summary.total_count ?? 0}件</p>
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
                {(summary.total_amount ?? 0).toLocaleString()}円
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
                {(summary.total_paid ?? 0).toLocaleString()}円
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
                {summary.collection_rate ?? 0}%
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
            {year}年{month}月分 請求確定一覧
            <span className="text-sm font-normal text-muted-foreground ml-2">
              ({totalCount}件)
            </span>
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
                    <TableHead>生徒名</TableHead>
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
                      <TableCell className="font-medium">
                        {billing.student_name || '-'}
                      </TableCell>
                      <TableCell>{billing.guardian_name}</TableCell>
                      <TableCell className="text-right">
                        {(billing.total_amount ?? 0).toLocaleString()}円
                      </TableCell>
                      <TableCell className="text-right text-green-600">
                        {(billing.paid_amount ?? 0).toLocaleString()}円
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
                      <TableCell>{billing.payment_method_display}</TableCell>
                      <TableCell>
                        {getStatusBadge(billing.status, billing.status_display)}
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
              {selectedBilling?.student_name}
            </DialogDescription>
          </DialogHeader>
          {selectedBilling && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-muted-foreground">生徒名</Label>
                  <p className="font-medium">
                    {selectedBilling.student_name || '-'}
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">保護者名</Label>
                  <p className="font-medium">{selectedBilling.guardian_name}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">請求額</Label>
                  <p className="font-medium">
                    {(selectedBilling.total_amount ?? 0).toLocaleString()}円
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">ステータス</Label>
                  <p>
                    {getStatusBadge(
                      selectedBilling.status,
                      selectedBilling.status_display
                    )}
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">入金済</Label>
                  <p className="font-medium text-green-600">
                    {(selectedBilling.paid_amount ?? 0).toLocaleString()}円
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
                  <p>{selectedBilling.payment_method_display}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">確定日時</Label>
                  <p>
                    {format(
                      new Date(selectedBilling.confirmed_at),
                      'yyyy/MM/dd HH:mm',
                      { locale: ja }
                    )}
                  </p>
                </div>
              </div>

              {/* 明細 */}
              {selectedBilling.items_snapshot &&
                selectedBilling.items_snapshot.length > 0 && (
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
                          {selectedBilling.items_snapshot.map((item, idx) => (
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
              {selectedBilling?.student_name} - 残高:{' '}
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
