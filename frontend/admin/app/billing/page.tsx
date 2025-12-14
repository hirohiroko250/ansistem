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
} from "lucide-react";
import {
  getInvoices,
  exportDirectDebitCSV,
  importDirectDebitResult,
  type InvoiceFilters,
  type DirectDebitResult,
} from "@/lib/api/staff";
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
  const [exportYear, setExportYear] = useState(new Date().getFullYear());
  const [exportMonth, setExportMonth] = useState(new Date().getMonth() + 1);
  const [exportProvider, setExportProvider] = useState("jaccs");

  // 引落結果インポートダイアログ
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<{ success: boolean; imported: number; errors: string[] } | null>(null);

  // 年月のオプション
  const years = useMemo(() => {
    const currentYear = new Date().getFullYear();
    return Array.from({ length: 5 }, (_, i) => currentYear - 2 + i);
  }, []);

  const months = useMemo(() => Array.from({ length: 12 }, (_, i) => i + 1), []);

  useEffect(() => {
    loadInvoices();
  }, [filters]);

  async function loadInvoices() {
    setLoading(true);
    const data = await getInvoices(filters);
    setResult(data);
    setLoading(false);
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
        billing_year: exportYear,
        billing_month: exportMonth,
        provider: exportProvider,
      });

      if (blob) {
        // CSVダウンロード
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `debit_export_${exportYear}${String(exportMonth).padStart(2, "0")}_${exportProvider}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
      setExportDialogOpen(false);
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

  const startResult = (result.page - 1) * result.pageSize + 1;
  const endResult = Math.min(result.page * result.pageSize, result.count);

  return (
    <ThreePaneLayout>
      <div className="p-6 h-full flex flex-col">
        {/* ヘッダー */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">請求管理</h1>
          <p className="text-gray-600">
            {result.count.toLocaleString()}件の請求書があります
          </p>
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
                結果取込
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
                  <label className="text-sm font-medium">年</label>
                  <Select
                    value={exportYear.toString()}
                    onValueChange={(v) => setExportYear(parseInt(v))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {years.map((year) => (
                        <SelectItem key={year} value={year.toString()}>
                          {year}年
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-sm font-medium">月</label>
                  <Select
                    value={exportMonth.toString()}
                    onValueChange={(v) => setExportMonth(parseInt(v))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {months.map((month) => (
                        <SelectItem key={month} value={month.toString()}>
                          {month}月
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">決済代行会社</label>
                <Select
                  value={exportProvider}
                  onValueChange={setExportProvider}
                >
                  <SelectTrigger>
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
      </div>
    </ThreePaneLayout>
  );
}
