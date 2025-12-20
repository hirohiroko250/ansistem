"use client";

import { useEffect, useState, useMemo } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Search,
  Download,
  Upload,
  FileText,
  ChevronLeft,
  ChevronRight,
  Calendar,
  AlertCircle,
  CheckCircle,
  Clock,
  Settings,
  Lock,
  Unlock,
  Banknote,
  FileCheck,
} from "lucide-react";
import {
  getInvoices,
  exportDirectDebitCSV,
  importDirectDebitResult,
  type InvoiceFilters,
  type DirectDebitResult,
} from "@/lib/api/staff";
import apiClient from "@/lib/api/client";
import type { Invoice, PaginatedResult } from "@/lib/api/types";

// ステータスラベルとカラー
const statusConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  draft: { label: "下書き", color: "bg-gray-100 text-gray-700", icon: <FileText className="w-3 h-3" /> },
  issued: { label: "発行済", color: "bg-blue-100 text-blue-700", icon: <Clock className="w-3 h-3" /> },
  paid: { label: "支払済", color: "bg-green-100 text-green-700", icon: <CheckCircle className="w-3 h-3" /> },
  partial: { label: "一部入金", color: "bg-yellow-100 text-yellow-700", icon: <AlertCircle className="w-3 h-3" /> },
  overdue: { label: "滞納", color: "bg-red-100 text-red-700", icon: <AlertCircle className="w-3 h-3" /> },
  cancelled: { label: "取消", color: "bg-gray-100 text-gray-500", icon: <FileText className="w-3 h-3" /> },
};

export default function BillingPage() {
  const [result, setResult] = useState<PaginatedResult<Invoice>>({
    data: [],
    count: 0,
    page: 1,
    pageSize: 50,
    totalPages: 0,
  });
  const [filters, setFilters] = useState<InvoiceFilters>({
    page: 1,
    page_size: 50,
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  // 引落エクスポートダイアログ
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportStartDate, setExportStartDate] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
  });
  const [exportEndDate, setExportEndDate] = useState(() => {
    const now = new Date();
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
  });
  const [exportProvider, setExportProvider] = useState("jaccs");

  // 引落結果インポートダイアログ
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<{ success: boolean; imported: number; errors: string[] } | null>(null);

  // 振込CSVインポートダイアログ
  const [transferImportDialogOpen, setTransferImportDialogOpen] = useState(false);
  const [transferFile, setTransferFile] = useState<File | null>(null);
  const [transferImporting, setTransferImporting] = useState(false);
  interface TransferImportResult {
    success: boolean;
    batch_id?: string;
    batch_no?: string;
    total_count: number;
    matched_count: number;
    unmatched_count: number;
    total_amount: number;
    errors?: string[];
  }
  const [transferImportResult, setTransferImportResult] = useState<TransferImportResult | null>(null);

  // 内部締日情報（MonthlyBillingDeadline）
  interface MonthlyDeadline {
    id: string;
    year: number;
    month: number;
    label: string;
    closing_day: number;
    closing_date: string;
    is_closed: boolean;
    can_edit: boolean;
    is_manually_closed: boolean;
    is_reopened: boolean;
    is_current: boolean;
  }
  const [monthlyDeadlines, setMonthlyDeadlines] = useState<MonthlyDeadline[]>([]);
  const [currentYear, setCurrentYear] = useState<number>(new Date().getFullYear());
  const [currentMonth, setCurrentMonth] = useState<number>(new Date().getMonth() + 1);
  const [defaultClosingDay, setDefaultClosingDay] = useState<number>(25);

  // 締日設定ダイアログ
  const [deadlineSettingOpen, setDeadlineSettingOpen] = useState(false);
  const [editingDeadline, setEditingDeadline] = useState<MonthlyDeadline | null>(null);
  const [editClosingDay, setEditClosingDay] = useState<number>(25);

  // 手動締め・締め解除ダイアログ
  const [closeDialogOpen, setCloseDialogOpen] = useState(false);
  const [reopenDialogOpen, setReopenDialogOpen] = useState(false);
  const [reopenReason, setReopenReason] = useState("");
  const [closeNotes, setCloseNotes] = useState("");

  // 年月のオプション
  const years = useMemo(() => {
    const currentYear = new Date().getFullYear();
    return Array.from({ length: 5 }, (_, i) => currentYear - 2 + i);
  }, []);

  const months = useMemo(() => Array.from({ length: 12 }, (_, i) => i + 1), []);

  useEffect(() => {
    loadInvoices();
    loadDeadlines();
  }, [filters]);

  async function loadInvoices() {
    setLoading(true);
    const data = await getInvoices(filters);
    setResult(data);
    setLoading(false);
  }

  async function loadDeadlines() {
    try {
      const data = await apiClient.get<{
        current_year: number;
        current_month: number;
        default_closing_day: number;
        months: MonthlyDeadline[];
      }>('/billing/deadlines/status_list/');
      if (data.months) {
        setMonthlyDeadlines(data.months);
      }
      if (data.current_year) {
        setCurrentYear(data.current_year);
      }
      if (data.current_month) {
        setCurrentMonth(data.current_month);
      }
      if (data.default_closing_day) {
        setDefaultClosingDay(data.default_closing_day);
      }
    } catch (error) {
      console.error('Failed to load deadlines:', error);
    }
  }

  function openDeadlineSetting(deadline: MonthlyDeadline) {
    setEditingDeadline(deadline);
    setEditClosingDay(deadline.closing_day);
    setDeadlineSettingOpen(true);
  }

  async function saveDeadlineSetting() {
    try {
      await apiClient.post('/billing/deadlines/set_default_closing_day/', {
        closing_day: editClosingDay,
      });
      setDefaultClosingDay(editClosingDay);
      setDeadlineSettingOpen(false);
      loadDeadlines();
    } catch (error) {
      console.error('Failed to save deadline:', error);
    }
  }

  // 手動締め
  async function handleManualClose() {
    if (!editingDeadline) return;
    try {
      await apiClient.post(`/billing/deadlines/${editingDeadline.id}/close_manually/`, {
        notes: closeNotes,
      });
      setCloseDialogOpen(false);
      setCloseNotes("");
      loadDeadlines();
    } catch (error) {
      console.error('Failed to close:', error);
    }
  }

  // 締め解除
  async function handleReopen() {
    if (!editingDeadline) return;
    try {
      await apiClient.post(`/billing/deadlines/${editingDeadline.id}/reopen/`, {
        reason: reopenReason,
      });
      setReopenDialogOpen(false);
      setReopenReason("");
      loadDeadlines();
    } catch (error) {
      console.error('Failed to reopen:', error);
    }
  }

  // 締日までの残り日数を計算
  function getDaysUntilClosing(closingDateStr: string): number {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const closingDate = new Date(closingDateStr);
    closingDate.setHours(0, 0, 0, 0);
    return Math.ceil((closingDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  }

  function handleSearch() {
    setFilters((prev) => ({
      ...prev,
      search: searchQuery || undefined,
      page: 1,
    }));
  }

  function handleYearChange(year: string) {
    setFilters((prev) => ({
      ...prev,
      billing_year: year === "all" ? undefined : parseInt(year),
      page: 1,
    }));
  }

  function handleMonthChange(month: string) {
    setFilters((prev) => ({
      ...prev,
      billing_month: month === "all" ? undefined : parseInt(month),
      page: 1,
    }));
  }

  function handleStatusChange(status: string) {
    setFilters((prev) => ({
      ...prev,
      status: status === "all" ? undefined : status,
      page: 1,
    }));
  }

  function handlePageChange(newPage: number) {
    setFilters((prev) => ({
      ...prev,
      page: newPage,
    }));
  }

  // 引落データエクスポート
  const [exporting, setExporting] = useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      const blob = await exportDirectDebitCSV({
        start_date: exportStartDate,
        end_date: exportEndDate,
        provider: exportProvider,
      });

      if (blob) {
        // CSVダウンロード
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `debit_export_${exportStartDate}_${exportEndDate}_${exportProvider}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
      setExportDialogOpen(false);
      // 一覧を更新（ロック状態を反映）
      loadInvoices();
    } catch (error) {
      console.error("Export error:", error);
    } finally {
      setExporting(false);
    }
  }

  // 引落結果インポート
  async function handleImport() {
    if (!importFile) return;

    setImportResult(null);
    const result = await importDirectDebitResult(importFile);
    setImportResult(result);

    if (result.success) {
      loadInvoices(); // 一覧を更新
    }
  }

  // 振込CSVインポート
  async function handleTransferImport() {
    if (!transferFile) return;

    setTransferImporting(true);
    setTransferImportResult(null);

    try {
      const formData = new FormData();
      formData.append('file', transferFile);

      const result = await apiClient.upload<TransferImportResult>('/billing/transfer-imports/upload/', formData);
      setTransferImportResult({
        success: true,
        batch_id: result.batch_id,
        batch_no: result.batch_no,
        total_count: result.total_count,
        matched_count: result.matched_count,
        unmatched_count: result.unmatched_count,
        total_amount: result.total_amount,
      });
    } catch (error: unknown) {
      console.error('Transfer import error:', error);
      const errorMessage = error instanceof Error ? error.message : '不明なエラー';
      setTransferImportResult({
        success: false,
        total_count: 0,
        matched_count: 0,
        unmatched_count: 0,
        total_amount: 0,
        errors: [errorMessage],
      });
    } finally {
      setTransferImporting(false);
    }
  }

  const startResult = (result.page - 1) * result.pageSize + 1;
  const endResult = Math.min(result.page * result.pageSize, result.count);

  return (
    <ThreePaneLayout>
      <div className="p-6 h-full flex flex-col">
        {/* ヘッダー */}
        <div className="mb-4 flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">請求管理</h1>
            <p className="text-gray-600">
              {result.count.toLocaleString()}件の請求書があります
            </p>
          </div>
          <div className="flex gap-2">
            <a href="/billing/transfers">
              <Button variant="outline">
                <Banknote className="w-4 h-4 mr-2" />
                振込入金確認
              </Button>
            </a>
            <a href="/billing/payments">
              <Button variant="outline">
                <Clock className="w-4 h-4 mr-2" />
                入金消込
              </Button>
            </a>
            <a href="/billing/bank-requests">
              <Button variant="outline">
                <FileText className="w-4 h-4 mr-2" />
                口座申請管理
              </Button>
            </a>
            <a href="/billing/confirmed">
              <Button variant="outline">
                <FileCheck className="w-4 h-4 mr-2" />
                請求確定データ
              </Button>
            </a>
          </div>
        </div>

        {/* 締日設定・締め処理 */}
        <div className="mb-4 flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            className="bg-blue-50 text-blue-700 border-blue-300"
            onClick={() => {
              setEditClosingDay(defaultClosingDay);
              setDeadlineSettingOpen(true);
            }}
          >
            <Calendar className="w-4 h-4 mr-1" />
            締日設定
            <span className="ml-1 text-xs">(毎月{defaultClosingDay}日)</span>
          </Button>

          {/* 当月の締め状況と締めボタン */}
          {monthlyDeadlines.length > 0 && (() => {
            const currentDeadline = monthlyDeadlines.find(d => d.is_current);
            if (!currentDeadline) return null;

            return currentDeadline.is_closed ? (
              <div className="flex items-center gap-2">
                <Badge className="bg-green-100 text-green-700 flex items-center gap-1">
                  <Lock className="w-3 h-3" />
                  {currentDeadline.year}年{currentDeadline.month}月 締め済
                </Badge>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setEditingDeadline(currentDeadline);
                    setReopenDialogOpen(true);
                  }}
                >
                  <Unlock className="w-4 h-4 mr-1" />
                  締め解除
                </Button>
              </div>
            ) : (
              <Button
                variant="default"
                size="sm"
                className="bg-orange-600 hover:bg-orange-700"
                onClick={() => {
                  setEditingDeadline(currentDeadline);
                  setCloseDialogOpen(true);
                }}
              >
                <Lock className="w-4 h-4 mr-1" />
                {currentDeadline.year}年{currentDeadline.month}月分を締める
              </Button>
            );
          })()}
        </div>


        {/* フィルター＆アクション */}
        <div className="space-y-4 mb-6">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <Input
                type="text"
                placeholder="保護者名、請求番号で検索..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSearch();
                }}
                className="pl-10"
              />
            </div>
            <Button onClick={handleSearch}>検索</Button>
          </div>

          <div className="flex gap-3 items-center justify-between">
            <div className="flex gap-3 items-center">
              <Calendar className="w-4 h-4 text-gray-500" />

              <Select
                value={filters.billing_year?.toString() || "all"}
                onValueChange={handleYearChange}
              >
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="年" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全年</SelectItem>
                  {years.map((year) => (
                    <SelectItem key={year} value={year.toString()}>
                      {year}年
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select
                value={filters.billing_month?.toString() || "all"}
                onValueChange={handleMonthChange}
              >
                <SelectTrigger className="w-[100px]">
                  <SelectValue placeholder="月" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全月</SelectItem>
                  {months.map((month) => (
                    <SelectItem key={month} value={month.toString()}>
                      {month}月
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select
                value={filters.status || "all"}
                onValueChange={handleStatusChange}
              >
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="状態" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全て</SelectItem>
                  <SelectItem value="draft">下書き</SelectItem>
                  <SelectItem value="issued">発行済</SelectItem>
                  <SelectItem value="paid">支払済</SelectItem>
                  <SelectItem value="partial">一部入金</SelectItem>
                  <SelectItem value="overdue">滞納</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setExportDialogOpen(true)}
              >
                <Download className="w-4 h-4 mr-2" />
                引落データ出力
              </Button>
              <Button
                variant="outline"
                onClick={() => setImportDialogOpen(true)}
              >
                <Upload className="w-4 h-4 mr-2" />
                引落結果取込
              </Button>
              <Button
                variant="outline"
                onClick={() => setTransferImportDialogOpen(true)}
              >
                <Banknote className="w-4 h-4 mr-2" />
                振込結果取込
              </Button>
            </div>
          </div>
        </div>

        {/* テーブル */}
        <Card className="flex-1 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-gray-500">読み込み中...</div>
            </div>
          ) : result.data.length > 0 ? (
            <div className="overflow-auto h-full">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[140px]">請求番号</TableHead>
                    <TableHead>保護者</TableHead>
                    <TableHead className="w-[100px]">請求月</TableHead>
                    <TableHead className="w-[100px]">ステータス</TableHead>
                    <TableHead className="w-[120px] text-right">請求額</TableHead>
                    <TableHead className="w-[120px] text-right">入金額</TableHead>
                    <TableHead className="w-[120px] text-right">未払額</TableHead>
                    <TableHead className="w-[100px] text-right">預り金</TableHead>
                    <TableHead className="w-[100px]">支払方法</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.data.map((invoice) => {
                    const status = statusConfig[invoice.status || "draft"];
                    const guardianName = invoice.guardian?.full_name ||
                      `${invoice.guardian?.last_name || ""}${invoice.guardian?.first_name || ""}` ||
                      "-";
                    const totalAmount = Number(invoice.totalAmount || invoice.total_amount || 0);
                    const paidAmount = Number(invoice.paidAmount || invoice.paid_amount || 0);
                    const balanceDue = Number(invoice.carryOverAmount || invoice.carry_over_amount || totalAmount - paidAmount);
                    const guardianBalance = Number(invoice.guardianBalance || invoice.guardian_balance || 0);

                    return (
                      <TableRow key={invoice.id} className="cursor-pointer hover:bg-gray-50">
                        <TableCell className="font-mono text-sm">
                          {invoice.invoiceNo || invoice.invoice_no || "-"}
                        </TableCell>
                        <TableCell>{guardianName}</TableCell>
                        <TableCell>
                          {invoice.billingMonth || invoice.billing_month || "-"}
                        </TableCell>
                        <TableCell>
                          <Badge className={`${status?.color} flex items-center gap-1 w-fit`}>
                            {status?.icon}
                            {status?.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          ¥{totalAmount.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right text-green-600">
                          ¥{paidAmount.toLocaleString()}
                        </TableCell>
                        <TableCell className={`text-right ${balanceDue > 0 ? "text-red-600 font-medium" : ""}`}>
                          ¥{balanceDue.toLocaleString()}
                        </TableCell>
                        <TableCell className={`text-right ${guardianBalance > 0 ? "text-indigo-600 font-medium" : "text-gray-400"}`}>
                          ¥{guardianBalance.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-sm text-gray-600">
                          {invoice.paymentMethod || invoice.payment_method || "-"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-gray-500">請求書が見つかりませんでした</div>
            </div>
          )}
        </Card>

        {/* ページネーション */}
        {result.totalPages > 1 && (
          <div className="flex items-center justify-between pt-4 border-t mt-4">
            <p className="text-sm text-gray-600">
              {startResult}〜{endResult}件 / 全{result.count.toLocaleString()}件
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(result.page - 1)}
                disabled={result.page === 1}
              >
                <ChevronLeft className="w-4 h-4" />
                前へ
              </Button>
              <span className="text-sm text-gray-600">
                {result.page} / {result.totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(result.page + 1)}
                disabled={result.page === result.totalPages}
              >
                次へ
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}

        {/* 引落データエクスポートダイアログ */}
        <Dialog open={exportDialogOpen} onOpenChange={setExportDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>引落データ出力</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">開始日</label>
                  <Input
                    type="date"
                    value={exportStartDate}
                    onChange={(e) => setExportStartDate(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">終了日</label>
                  <Input
                    type="date"
                    value={exportEndDate}
                    onChange={(e) => setExportEndDate(e.target.value)}
                    className="mt-1"
                  />
                </div>
              </div>
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                <p className="font-medium mb-1">注意</p>
                <p>エクスポートを実行すると、選択した期間以前の全ての請求データは編集不可になります。</p>
              </div>
              <div>
                <label className="text-sm font-medium">決済代行会社</label>
                <Select
                  value={exportProvider}
                  onValueChange={setExportProvider}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="jaccs">JACCS</SelectItem>
                    <SelectItem value="ufj_factor">UFJファクター</SelectItem>
                    <SelectItem value="chukyo_finance">中京ファイナンス</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setExportDialogOpen(false)} disabled={exporting}>
                キャンセル
              </Button>
              <Button onClick={handleExport} disabled={exporting}>
                <Download className="w-4 h-4 mr-2" />
                {exporting ? "出力中..." : "エクスポート"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 引落結果インポートダイアログ */}
        <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>引落結果取込</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <label className="text-sm font-medium">CSVファイル</label>
                <Input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                  className="mt-1"
                />
              </div>
              {importResult && (
                <div className={`p-3 rounded-lg ${importResult.success ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`}>
                  {importResult.success ? (
                    <p>{importResult.imported}件の結果を取り込みました</p>
                  ) : (
                    <div>
                      <p className="font-medium">エラーが発生しました</p>
                      <ul className="list-disc list-inside mt-1 text-sm">
                        {importResult.errors.map((err, i) => (
                          <li key={i}>{err}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => {
                setImportDialogOpen(false);
                setImportFile(null);
                setImportResult(null);
              }}>
                閉じる
              </Button>
              <Button onClick={handleImport} disabled={!importFile}>
                <Upload className="w-4 h-4 mr-2" />
                取り込み
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 振込CSVインポートダイアログ */}
        <Dialog open={transferImportDialogOpen} onOpenChange={setTransferImportDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>振込データ取込</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                <p className="font-medium mb-1">対応フォーマット</p>
                <p>銀行振込データのCSVまたはExcelファイルを取り込めます。</p>
                <p className="mt-1 text-xs">
                  必須項目: 振込人名、振込金額、振込日
                </p>
              </div>
              <div>
                <label className="text-sm font-medium">ファイル選択</label>
                <Input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(e) => setTransferFile(e.target.files?.[0] || null)}
                  className="mt-1"
                />
              </div>
              {transferImportResult && (
                <div className={`p-3 rounded-lg ${transferImportResult.success ? "bg-green-50 text-green-800 border border-green-200" : "bg-red-50 text-red-800 border border-red-200"}`}>
                  {transferImportResult.success ? (
                    <div>
                      <p className="font-medium mb-2">取込完了</p>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>バッチ番号: {transferImportResult.batch_no}</div>
                        <div>総件数: {transferImportResult.total_count}件</div>
                        <div className="text-green-700">照合済: {transferImportResult.matched_count}件</div>
                        <div className="text-orange-700">未照合: {transferImportResult.unmatched_count}件</div>
                        <div className="col-span-2">総金額: ¥{transferImportResult.total_amount.toLocaleString()}</div>
                      </div>
                      <div className="mt-3 flex gap-2">
                        <a href={`/billing/transfers?batch=${transferImportResult.batch_id}`}>
                          <Button size="sm" variant="outline">
                            照合画面へ
                          </Button>
                        </a>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <p className="font-medium">エラーが発生しました</p>
                      <ul className="list-disc list-inside mt-1 text-sm">
                        {transferImportResult.errors?.map((err, i) => (
                          <li key={i}>{err}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => {
                setTransferImportDialogOpen(false);
                setTransferFile(null);
                setTransferImportResult(null);
              }}>
                閉じる
              </Button>
              <Button onClick={handleTransferImport} disabled={!transferFile || transferImporting}>
                <Upload className="w-4 h-4 mr-2" />
                {transferImporting ? "取込中..." : "取り込み"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 締日設定ダイアログ */}
        <Dialog open={deadlineSettingOpen} onOpenChange={setDeadlineSettingOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>締日設定</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <p className="text-sm text-gray-600">
                毎月の請求締日を設定します
              </p>
              <div>
                <label className="text-sm font-medium">締日（毎月）</label>
                <Select
                  value={editClosingDay.toString()}
                  onValueChange={(v) => setEditClosingDay(parseInt(v))}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Array.from({ length: 31 }, (_, i) => i + 1).map((day) => (
                      <SelectItem key={day} value={day.toString()}>
                        {day}日
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500 mt-1">
                  この日までに請求データを確定してください
                </p>
              </div>
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                <p className="font-medium mb-1">設定の反映</p>
                <p>
                  締日を変更すると、今後の全ての月に適用されます。
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeadlineSettingOpen(false)}>
                キャンセル
              </Button>
              <Button onClick={saveDeadlineSetting}>
                <Settings className="w-4 h-4 mr-2" />
                保存
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 手動締めダイアログ */}
        <Dialog open={closeDialogOpen} onOpenChange={setCloseDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>手動締め</DialogTitle>
            </DialogHeader>
            {editingDeadline && (
              <div className="space-y-4 py-4">
                <p className="text-sm text-gray-600">
                  {editingDeadline.year}年{editingDeadline.month}月分を手動で締め処理します
                </p>
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                  <p className="font-medium mb-1">注意</p>
                  <p>締め処理を行うと、この月の請求データは編集不可になります。</p>
                  <p className="mt-1">締め後でも「締め解除」で再度編集可能にできます。</p>
                </div>
                <div>
                  <label className="text-sm font-medium">備考（任意）</label>
                  <Input
                    value={closeNotes}
                    onChange={(e) => setCloseNotes(e.target.value)}
                    placeholder="締め処理の理由など"
                    className="mt-1"
                  />
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setCloseDialogOpen(false)}>
                キャンセル
              </Button>
              <Button onClick={handleManualClose} className="bg-orange-600 hover:bg-orange-700">
                <Lock className="w-4 h-4 mr-2" />
                締め処理を実行
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 締め解除ダイアログ */}
        <Dialog open={reopenDialogOpen} onOpenChange={setReopenDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>締め解除</DialogTitle>
            </DialogHeader>
            {editingDeadline && (
              <div className="space-y-4 py-4">
                <p className="text-sm text-gray-600">
                  {editingDeadline.year}年{editingDeadline.month}月分の締めを解除して編集可能にします
                </p>
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                  <p className="font-medium mb-1">締め解除について</p>
                  <p>締め解除を行うと、この月の請求データを再度編集できるようになります。</p>
                  <p className="mt-1">修正が完了したら、再度締め処理を行ってください。</p>
                </div>
                <div>
                  <label className="text-sm font-medium">解除理由（必須）</label>
                  <Input
                    value={reopenReason}
                    onChange={(e) => setReopenReason(e.target.value)}
                    placeholder="締め解除の理由を入力"
                    className="mt-1"
                  />
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setReopenDialogOpen(false)}>
                キャンセル
              </Button>
              <Button onClick={handleReopen} disabled={!reopenReason}>
                <Unlock className="w-4 h-4 mr-2" />
                締め解除を実行
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </ThreePaneLayout>
  );
}
