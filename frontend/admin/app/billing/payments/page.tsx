"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  ChevronLeft,
  Link as LinkIcon,
  CheckCircle,
  AlertCircle,
  Loader2,
  RefreshCw,
  Target,
  Upload,
  FileSpreadsheet,
  Search,
  User,
  Check,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import apiClient from "@/lib/api/client";
import {
  getUnmatchedPayments,
  getMatchCandidates,
  matchPaymentToInvoice,
  type PaymentData,
  type MatchCandidate,
} from "@/lib/api/staff";

// 振込データ型
interface BankTransfer {
  id: string;
  transferDate: string;
  amount: number | string;
  payerName: string;
  payerNameKana?: string;
  guardianNoHint?: string;
  sourceBankName?: string;
  sourceBranchName?: string;
  status: 'pending' | 'matched' | 'applied' | 'unmatched' | 'cancelled';
  statusDisplay: string;
  guardian?: string;
  guardianName?: string;
  invoice?: string;
  invoiceNo?: string;
  importBatchId?: string;
  importRowNo?: number;
  candidateGuardians?: CandidateGuardian[];
}

// 照合候補
interface CandidateGuardian {
  guardianId: string;
  guardianName: string;
  guardianNameKana?: string;
  invoices: {
    invoiceId: string;
    invoiceNo: string;
    billingLabel: string;
    totalAmount: number;
    balanceDue: number;
  }[];
}

// インポートバッチ
interface ImportBatch {
  id: string;
  batchNo: string;
  fileName: string;
  totalCount: number;
  matchedCount: number;
  unmatchedCount: number;
  status: string;
  statusDisplay: string;
  importedAt: string;
  confirmedAt?: string;
  transfers?: BankTransfer[];
}

export default function PaymentMatchingPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // タブ状態
  const [activeTab, setActiveTab] = useState<string>(() => {
    const tab = searchParams.get("tab");
    return tab === "import" ? "import" : "unmatched";
  });

  // === 未消込入金タブ ===
  const [payments, setPayments] = useState<PaymentData[]>([]);
  const [pendingTransfers, setPendingTransfers] = useState<BankTransfer[]>([]);
  const [loadingPayments, setLoadingPayments] = useState(true);
  const [paymentCount, setPaymentCount] = useState(0);
  const [pendingTransferCount, setPendingTransferCount] = useState(0);

  // 消込ダイアログ
  const [matchDialogOpen, setMatchDialogOpen] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState<PaymentData | null>(null);
  const [candidates, setCandidates] = useState<MatchCandidate[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [matchingInvoice, setMatchingInvoice] = useState<string | null>(null);

  // === 振込取込タブ ===
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    success: boolean;
    batch_id?: string;
    total_count?: number;
    auto_matched_count?: number;
    error_count?: number;
    errors?: { row: number; error: string }[];
  } | null>(null);

  // インポートバッチ一覧
  const [importBatches, setImportBatches] = useState<ImportBatch[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<ImportBatch | null>(null);
  const [loadingBatches, setLoadingBatches] = useState(false);

  // 照合ダイアログ（振込用）
  const [transferMatchDialogOpen, setTransferMatchDialogOpen] = useState(false);
  const [matchingTransfer, setMatchingTransfer] = useState<BankTransfer | null>(null);
  const [guardianSearchQuery, setGuardianSearchQuery] = useState("");
  const [guardianSearchResults, setGuardianSearchResults] = useState<CandidateGuardian[]>([]);
  const [searchingGuardians, setSearchingGuardians] = useState(false);
  const [selectedGuardian, setSelectedGuardian] = useState<CandidateGuardian | null>(null);
  const [selectedMatchInvoice, setSelectedMatchInvoice] = useState<string | null>(null);
  const [matching, setMatching] = useState(false);

  // URLパラメータの変更を監視
  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab === "import") {
      setActiveTab("import");
    }
  }, [searchParams]);

  // 未消込入金を読み込み（Payment + 未確認BankTransfer）
  async function loadUnmatchedPayments() {
    setLoadingPayments(true);
    try {
      // 既存のPaymentデータを取得
      const data = await getUnmatchedPayments();
      setPayments(data.payments);
      setPaymentCount(data.count);

      // 未確認のBankTransferも取得
      const transferRes = await apiClient.get<{ results?: BankTransfer[]; count?: number }>('/billing/transfers/', {
        status: 'pending',
      });
      const transfers = transferRes.results || [];
      setPendingTransfers(transfers);
      setPendingTransferCount(transfers.length);
    } catch (error) {
      console.error("Error loading payments:", error);
    } finally {
      setLoadingPayments(false);
    }
  }

  // インポートバッチ一覧を読み込み
  const loadImportBatches = useCallback(async () => {
    console.log('[loadImportBatches] Starting...');
    setLoadingBatches(true);
    try {
      const res = await apiClient.get<{ results?: ImportBatch[]; data?: ImportBatch[] }>('/billing/transfer-imports/');
      console.log('[loadImportBatches] Response:', res);
      const batches = res.results || res.data || [];
      console.log('[loadImportBatches] Batches count:', batches.length);
      setImportBatches(batches);
    } catch (error) {
      console.error('[loadImportBatches] Failed:', error);
    } finally {
      setLoadingBatches(false);
    }
  }, []);

  // バッチ詳細を読み込み
  const loadBatchDetail = useCallback(async (batchId: string) => {
    console.log('[loadBatchDetail] Loading batch:', batchId);
    try {
      const res = await apiClient.get<ImportBatch>(`/billing/transfer-imports/${batchId}/`);
      console.log('[loadBatchDetail] Response:', res);
      console.log('[loadBatchDetail] Transfers count:', res.transfers?.length);
      setSelectedBatch(res);
    } catch (error) {
      console.error('[loadBatchDetail] Failed to load batch detail:', error);
    }
  }, []);

  useEffect(() => {
    console.log('[useEffect] activeTab changed:', activeTab);
    if (activeTab === "unmatched") {
      console.log('[useEffect] Loading unmatched payments...');
      loadUnmatchedPayments();
    } else if (activeTab === "import") {
      console.log('[useEffect] Loading import batches...');
      loadImportBatches();
    }
  }, [activeTab, loadImportBatches]);

  // === 未消込入金の処理 ===
  async function openMatchDialog(payment: PaymentData) {
    setSelectedPayment(payment);
    setMatchDialogOpen(true);
    setLoadingCandidates(true);
    setCandidates([]);

    try {
      const data = await getMatchCandidates(payment.id);
      setCandidates(data.candidates);
    } catch (error) {
      console.error("Error loading candidates:", error);
    } finally {
      setLoadingCandidates(false);
    }
  }

  async function handleMatch(invoiceId: string) {
    if (!selectedPayment) return;

    setMatchingInvoice(invoiceId);
    try {
      await matchPaymentToInvoice(selectedPayment.id, invoiceId);
      setMatchDialogOpen(false);
      loadUnmatchedPayments();
    } catch (error) {
      console.error("Error matching payment:", error);
    } finally {
      setMatchingInvoice(null);
    }
  }

  // === 振込インポートの処理 ===
  const handleImport = async () => {
    if (!importFile) return;

    setImporting(true);
    setImportResult(null);

    try {
      const formData = new FormData();
      formData.append('file', importFile);

      const res = await apiClient.upload<{
        success: boolean;
        batch_id: string;
        batch_no: string;
        total_count: number;
        auto_matched_count: number;
        error_count: number;
        errors: { row: number; error: string }[];
      }>('/billing/transfer-imports/upload/', formData);

      setImportResult({
        success: res.success,
        batch_id: res.batch_id,
        total_count: res.total_count,
        auto_matched_count: res.auto_matched_count,
        error_count: res.error_count,
        errors: res.errors,
      });

      loadImportBatches();

      if (res.batch_id) {
        loadBatchDetail(res.batch_id);
      }
    } catch (error) {
      console.error('Import error:', error);
      setImportResult({ success: false });
    } finally {
      setImporting(false);
    }
  };

  // 保護者検索（照合用）
  const handleSearchGuardians = async () => {
    if (!guardianSearchQuery.trim() || guardianSearchQuery.length < 2) return;

    setSearchingGuardians(true);
    try {
      const res = await apiClient.get<{ guardians: CandidateGuardian[] }>('/billing/transfer-imports/search_guardians/', {
        q: guardianSearchQuery,
      });
      setGuardianSearchResults(res.guardians || []);
    } catch (error) {
      console.error('Guardian search error:', error);
    } finally {
      setSearchingGuardians(false);
    }
  };

  // 照合ダイアログを開く
  const openTransferMatchDialog = (transfer: BankTransfer) => {
    setMatchingTransfer(transfer);
    setGuardianSearchQuery(transfer.payerName || '');
    setGuardianSearchResults(transfer.candidateGuardians || []);
    setSelectedGuardian(null);
    setSelectedMatchInvoice(null);
    setTransferMatchDialogOpen(true);
  };

  // 照合実行
  const handleTransferMatch = async () => {
    if (!matchingTransfer || !selectedGuardian) return;

    setMatching(true);
    try {
      await apiClient.post(`/billing/transfers/${matchingTransfer.id}/match/`, {
        guardian_id: selectedGuardian.guardianId,
      });

      if (selectedMatchInvoice) {
        await apiClient.post(`/billing/transfers/${matchingTransfer.id}/apply/`, {
          invoice_id: selectedMatchInvoice,
        });
      }

      setTransferMatchDialogOpen(false);

      if (selectedBatch) {
        loadBatchDetail(selectedBatch.id);
      }
      // 未消込入金タブも更新
      loadUnmatchedPayments();
    } catch (error) {
      console.error('Match error:', error);
    } finally {
      setMatching(false);
    }
  };

  // 入金確認のみ（未消込として確定）
  const handleConfirmPaymentOnly = async () => {
    if (!matchingTransfer) return;

    setMatching(true);
    try {
      // 請求書なしで入金確認
      await apiClient.post(`/billing/transfers/${matchingTransfer.id}/apply/`, {});

      setTransferMatchDialogOpen(false);

      if (selectedBatch) {
        loadBatchDetail(selectedBatch.id);
      }
      // 未消込入金タブも更新
      loadUnmatchedPayments();
    } catch (error) {
      console.error('Confirm payment error:', error);
    } finally {
      setMatching(false);
    }
  };

  // バッチ確定
  const handleConfirmBatch = async () => {
    if (!selectedBatch) return;

    try {
      await apiClient.post(`/billing/transfer-imports/${selectedBatch.id}/confirm/`);
      loadBatchDetail(selectedBatch.id);
      loadImportBatches();
    } catch (error) {
      console.error('Confirm error:', error);
    }
  };

  // ID番号クリック時に保護者ページへ遷移（別タブで開く）
  const handleIdClick = async (guardianNo: string) => {
    if (!guardianNo) return;

    try {
      // guardian_noで保護者を検索
      const res = await apiClient.get<{ results?: { id: string }[] }>('/students/guardians/', {
        guardian_no: guardianNo,
      });

      const guardians = res.results || [];
      if (guardians.length > 0) {
        // 保護者が見つかったらそのページを別タブで開く
        window.open(`/parents?selected=${guardians[0].id}`, '_blank');
      } else {
        // 見つからない場合は検索クエリで別タブを開く
        window.open(`/parents?search=${guardianNo}`, '_blank');
      }
    } catch (error) {
      console.error('Guardian search error:', error);
      // エラー時も検索クエリで別タブを開く
      window.open(`/parents?search=${guardianNo}`, '_blank');
    }
  };

  // === ユーティリティ関数 ===
  function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return "-";
    try {
      const date = new Date(dateStr);
      return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, "0")}/${String(date.getDate()).padStart(2, "0")}`;
    } catch {
      return "-";
    }
  }

  const formatAmount = (amount: number | string | undefined): string => {
    const num = Number(amount || 0);
    return `¥${num.toLocaleString()}`;
  };

  const getTransferStatusBadge = (status: string) => {
    const config: Record<string, { label: string; color: string }> = {
      pending: { label: '未確認', color: 'bg-yellow-100 text-yellow-700' },
      matched: { label: '確認済', color: 'bg-blue-100 text-blue-700' },
      applied: { label: '入金済', color: 'bg-green-100 text-green-700' },
      unmatched: { label: '不明', color: 'bg-red-100 text-red-700' },
      cancelled: { label: '取消', color: 'bg-gray-100 text-gray-500' },
    };
    const conf = config[status] || { label: status, color: 'bg-gray-100 text-gray-700' };
    return <Badge className={conf.color}>{conf.label}</Badge>;
  };

  return (
    <ThreePaneLayout>
      <div className="p-6 h-full flex flex-col">
        {/* ヘッダー */}
        <div className="mb-6">
          <div className="flex items-center gap-4 mb-2">
            <Link href="/billing">
              <Button variant="ghost" size="sm">
                <ChevronLeft className="w-4 h-4 mr-1" />
                請求管理
              </Button>
            </Link>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">入金消込</h1>
          <p className="text-gray-600">
            振込データの取込と入金消込を行います
          </p>
        </div>

        {/* タブ切り替え */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="mb-4">
            <TabsTrigger value="unmatched" className="flex items-center gap-2">
              <Target className="w-4 h-4" />
              未消込入金
              {(paymentCount + pendingTransferCount) > 0 && (
                <Badge variant="destructive" className="ml-1">{paymentCount + pendingTransferCount}</Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="import" className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              振込取込
            </TabsTrigger>
          </TabsList>

          {/* 未消込入金タブ */}
          <TabsContent value="unmatched" className="flex-1 flex flex-col overflow-auto">
            {/* 説明カード */}
            <Card className="mb-6 bg-blue-50 border-blue-200">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-blue-900">入金消込について</p>
                    <p className="text-sm text-blue-700 mt-1">
                      銀行振込などで入金された金額を、対応する請求書と紐付けます。
                      振込名義と金額をもとに自動で候補を表示します。
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-end mb-4">
              <Button variant="outline" size="sm" onClick={loadUnmatchedPayments}>
                <RefreshCw className="w-4 h-4 mr-1" />
                更新
              </Button>
            </div>

            {loadingPayments ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
              </div>
            ) : (paymentCount + pendingTransferCount) === 0 ? (
              <Card>
                <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                  <CheckCircle className="w-12 h-12 text-green-400 mb-4" />
                  <p className="text-lg font-medium">未消込の入金はありません</p>
                  <p className="text-sm">全ての入金が請求書に紐付けられています</p>
                </div>
              </Card>
            ) : (
              <div className="space-y-6">
                {/* 未確認の振込データ（インポート分） */}
                {pendingTransferCount > 0 && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <FileSpreadsheet className="w-5 h-5" />
                        未確認の振込データ
                        <Badge variant="destructive">{pendingTransferCount}件</Badge>
                      </CardTitle>
                    </CardHeader>
                    <div className="overflow-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[100px]">振込日</TableHead>
                            <TableHead className="w-[90px]">ID番号</TableHead>
                            <TableHead>振込人名義</TableHead>
                            <TableHead className="w-[120px] text-right">金額</TableHead>
                            <TableHead className="w-[100px]">操作</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {pendingTransfers.map((transfer) => (
                            <TableRow key={transfer.id} className="hover:bg-gray-50">
                              <TableCell className="text-sm">
                                {formatDate(transfer.transferDate)}
                              </TableCell>
                              <TableCell className="font-mono text-sm">
                                {transfer.guardianNoHint ? (
                                  <button
                                    onClick={() => handleIdClick(transfer.guardianNoHint!)}
                                    className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                                  >
                                    {transfer.guardianNoHint}
                                  </button>
                                ) : (
                                  <span className="text-gray-400">-</span>
                                )}
                              </TableCell>
                              <TableCell className="font-medium">
                                {transfer.payerName || "-"}
                              </TableCell>
                              <TableCell className="text-right font-medium">
                                {formatAmount(transfer.amount)}
                              </TableCell>
                              <TableCell>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => openTransferMatchDialog(transfer)}
                                >
                                  <LinkIcon className="w-3 h-3 mr-1" />
                                  照合
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </Card>
                )}

                {/* 既存の未消込入金（Paymentデータ） */}
                {paymentCount > 0 && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg">
                        その他の未消込入金
                        <Badge variant="outline" className="ml-2">{paymentCount}件</Badge>
                      </CardTitle>
                    </CardHeader>
                    <div className="overflow-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[120px]">入金番号</TableHead>
                            <TableHead className="w-[100px]">入金日</TableHead>
                            <TableHead>振込名義</TableHead>
                            <TableHead className="w-[120px] text-right">金額</TableHead>
                            <TableHead className="w-[100px]">入金方法</TableHead>
                            <TableHead className="w-[100px]">ステータス</TableHead>
                            <TableHead className="w-[100px]">操作</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {payments.map((payment) => (
                            <TableRow key={payment.id} className="hover:bg-gray-50">
                              <TableCell className="font-mono text-sm">
                                {payment.payment_no}
                              </TableCell>
                              <TableCell>{formatDate(payment.payment_date)}</TableCell>
                              <TableCell className="font-medium">
                                {payment.payer_name || "-"}
                                {payment.bank_name && (
                                  <span className="text-sm text-gray-500 ml-2">
                                    ({payment.bank_name})
                                  </span>
                                )}
                              </TableCell>
                              <TableCell className="text-right font-medium">
                                ¥{Number(payment.amount).toLocaleString()}
                              </TableCell>
                              <TableCell>
                                <Badge variant="outline">
                                  {payment.method_display || payment.method}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <Badge
                                  className={
                                    payment.status === "success"
                                      ? "bg-green-100 text-green-700"
                                      : payment.status === "pending"
                                      ? "bg-yellow-100 text-yellow-700"
                                      : "bg-gray-100 text-gray-700"
                                  }
                                >
                                  {payment.status_display || payment.status}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => openMatchDialog(payment)}
                                >
                                  <Target className="w-4 h-4 mr-1" />
                                  消込
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </Card>
                )}
              </div>
            )}
          </TabsContent>

          {/* 振込取込タブ */}
          <TabsContent value="import" className="mt-0">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-280px)]">
              {/* インポートバッチ一覧 */}
              <Card className="flex flex-col overflow-hidden">
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <FileSpreadsheet className="w-5 h-5" />
                      取込履歴
                    </CardTitle>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={loadImportBatches}>
                        <RefreshCw className="w-4 h-4" />
                      </Button>
                      <Button size="sm" onClick={() => {
                        setImportFile(null);
                        setImportResult(null);
                        setImportDialogOpen(true);
                      }}>
                        <Upload className="w-4 h-4 mr-1" />
                        取込
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-0">
                  {loadingBatches ? (
                    <div className="flex items-center justify-center h-32">
                      <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                    </div>
                  ) : importBatches.length > 0 ? (
                    <div className="divide-y">
                      {importBatches.map((batch) => (
                        <div
                          key={batch.id}
                          className={`p-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                            selectedBatch?.id === batch.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                          }`}
                          onClick={() => {
                            console.log('[Click] Batch clicked:', batch.id, batch.fileName);
                            loadBatchDetail(batch.id);
                          }}
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-medium text-sm">{batch.fileName}</p>
                              <p className="text-xs text-gray-500 mt-1">
                                {formatDate(batch.importedAt)}
                              </p>
                            </div>
                            {getTransferStatusBadge(batch.status)}
                          </div>
                          <div className="flex gap-4 mt-2 text-xs text-gray-600">
                            <span>総件数: {batch.totalCount}</span>
                            <span className="text-green-600">確認済: {batch.matchedCount}</span>
                            <span className="text-yellow-600">未確認: {batch.unmatchedCount}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                      <FileSpreadsheet className="w-8 h-8 mb-2 text-gray-300" />
                      <p>取込履歴がありません</p>
                      <Button
                        size="sm"
                        className="mt-2"
                        onClick={() => setImportDialogOpen(true)}
                      >
                        <Upload className="w-4 h-4 mr-1" />
                        ファイルを取込
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* 振込データ一覧 */}
              <Card className="lg:col-span-2 flex flex-col overflow-hidden">
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-lg flex items-center gap-2">
                      振込データ
                      {selectedBatch && (
                        <span className="text-sm font-normal text-gray-500">
                          - {selectedBatch.fileName}
                        </span>
                      )}
                    </CardTitle>
                    {selectedBatch && !selectedBatch.confirmedAt && selectedBatch.matchedCount > 0 && (
                      <Button size="sm" onClick={handleConfirmBatch}>
                        <CheckCircle className="w-4 h-4 mr-1" />
                        確定して入金処理
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-0">
                  {selectedBatch ? (
                    selectedBatch.transfers && selectedBatch.transfers.length > 0 ? (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[100px]">振込日</TableHead>
                            <TableHead className="w-[90px]">ID番号</TableHead>
                            <TableHead>振込人名義</TableHead>
                            <TableHead className="text-right">金額</TableHead>
                            <TableHead className="w-[80px]">状態</TableHead>
                            <TableHead>照合先</TableHead>
                            <TableHead className="w-[80px]">操作</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectedBatch.transfers.map((transfer) => (
                            <TableRow key={transfer.id}>
                              <TableCell className="text-sm">
                                {formatDate(transfer.transferDate)}
                              </TableCell>
                              <TableCell className="font-mono text-sm">
                                {transfer.guardianNoHint ? (
                                  <button
                                    onClick={() => handleIdClick(transfer.guardianNoHint!)}
                                    className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                                  >
                                    {transfer.guardianNoHint}
                                  </button>
                                ) : (
                                  <span className="text-gray-400">-</span>
                                )}
                              </TableCell>
                              <TableCell>
                                <div>
                                  <p className="font-medium">{transfer.payerName}</p>
                                  {transfer.payerNameKana && transfer.payerNameKana !== transfer.payerName && (
                                    <p className="text-xs text-gray-500">{transfer.payerNameKana}</p>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell className="text-right font-medium">
                                {formatAmount(transfer.amount)}
                              </TableCell>
                              <TableCell>
                                {getTransferStatusBadge(transfer.status)}
                              </TableCell>
                              <TableCell>
                                {transfer.guardianName ? (
                                  <div>
                                    <p className="font-medium text-sm">{transfer.guardianName}</p>
                                    {transfer.invoiceNo && (
                                      <p className="text-xs text-gray-500">{transfer.invoiceNo}</p>
                                    )}
                                  </div>
                                ) : (
                                  <span className="text-gray-400">-</span>
                                )}
                              </TableCell>
                              <TableCell>
                                {transfer.status === 'pending' && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => openTransferMatchDialog(transfer)}
                                  >
                                    <LinkIcon className="w-3 h-3 mr-1" />
                                    照合
                                  </Button>
                                )}
                                {transfer.status === 'matched' && (
                                  <Button
                                    size="sm"
                                    variant="default"
                                    onClick={() => openTransferMatchDialog(transfer)}
                                  >
                                    <Check className="w-3 h-3 mr-1" />
                                    入金
                                  </Button>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    ) : (
                      <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                        <FileSpreadsheet className="w-8 h-8 mb-2 text-gray-300" />
                        <p>振込データがありません</p>
                      </div>
                    )
                  ) : (
                    <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                      <FileSpreadsheet className="w-8 h-8 mb-2 text-gray-300" />
                      <p>左側から取込履歴を選択してください</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* 消込ダイアログ（未消込入金用） */}
        <Dialog open={matchDialogOpen} onOpenChange={setMatchDialogOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <LinkIcon className="w-5 h-5" />
                入金消込
              </DialogTitle>
            </DialogHeader>

            {selectedPayment && (
              <div className="space-y-4">
                <Card className="bg-blue-50 border-blue-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-blue-900">消込対象の入金</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-blue-700">入金番号:</span>
                        <span className="font-medium ml-2">{selectedPayment.payment_no}</span>
                      </div>
                      <div>
                        <span className="text-blue-700">入金日:</span>
                        <span className="font-medium ml-2">{formatDate(selectedPayment.payment_date)}</span>
                      </div>
                      <div>
                        <span className="text-blue-700">振込名義:</span>
                        <span className="font-medium ml-2">{selectedPayment.payer_name || "-"}</span>
                      </div>
                      <div>
                        <span className="text-blue-700">金額:</span>
                        <span className="font-bold ml-2 text-blue-900">
                          ¥{Number(selectedPayment.amount).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <div>
                  <h4 className="font-medium mb-2">消込候補の請求書</h4>
                  {loadingCandidates ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                    </div>
                  ) : candidates.length > 0 ? (
                    <div className="space-y-2 max-h-[300px] overflow-auto">
                      {candidates.map((candidate) => (
                        <Card
                          key={candidate.invoice.id}
                          className={`cursor-pointer transition-all hover:border-blue-400 ${
                            candidate.match_score >= 100 ? "border-green-300 bg-green-50" : ""
                          }`}
                        >
                          <CardContent className="p-3">
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="font-mono text-sm">
                                    {candidate.invoice.invoice_no || candidate.invoice.invoiceNo}
                                  </span>
                                  <Badge
                                    className={
                                      candidate.match_score >= 100
                                        ? "bg-green-100 text-green-700"
                                        : "bg-yellow-100 text-yellow-700"
                                    }
                                  >
                                    {candidate.match_reason}
                                  </Badge>
                                </div>
                                <div className="text-sm text-gray-600">
                                  <span>
                                    {candidate.invoice.guardian?.full_name ||
                                      (candidate.invoice as any).guardian_name ||
                                      "-"}
                                  </span>
                                  <span className="mx-2">|</span>
                                  <span>
                                    {candidate.invoice.billing_month ||
                                      (candidate.invoice as any).billingMonth}
                                  </span>
                                  <span className="mx-2">|</span>
                                  <span className="font-medium">
                                    未払: ¥
                                    {Number(
                                      candidate.invoice.balance_due ||
                                        (candidate.invoice as any).balanceDue ||
                                        0
                                    ).toLocaleString()}
                                  </span>
                                </div>
                              </div>
                              <Button
                                size="sm"
                                onClick={() => handleMatch(candidate.invoice.id)}
                                disabled={matchingInvoice !== null}
                              >
                                {matchingInvoice === candidate.invoice.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <>
                                    <CheckCircle className="w-4 h-4 mr-1" />
                                    消込
                                  </>
                                )}
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <AlertCircle className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                      <p>消込候補が見つかりませんでした</p>
                      <p className="text-sm">請求一覧から手動で選択してください</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={() => setMatchDialogOpen(false)}>
                閉じる
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* インポートダイアログ */}
        <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5" />
                振込データ取込
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div>
                <Label>ファイル選択</Label>
                <div className="mt-2 border-2 border-dashed border-gray-200 rounded-lg p-6 text-center">
                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                    className="hidden"
                    id="import-file"
                  />
                  <label htmlFor="import-file" className="cursor-pointer">
                    <FileSpreadsheet className="w-12 h-12 mx-auto text-gray-400 mb-2" />
                    <p className="text-sm text-gray-600">
                      {importFile ? importFile.name : 'クリックしてファイルを選択'}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      銀行からダウンロードしたCSVファイルをそのまま取込できます
                    </p>
                  </label>
                </div>
              </div>

              {importResult && (
                <div className={`p-3 rounded-lg ${
                  importResult.success
                    ? 'bg-green-50 text-green-800'
                    : 'bg-red-50 text-red-800'
                }`}>
                  {importResult.success ? (
                    <div>
                      <p className="font-medium flex items-center gap-2">
                        <CheckCircle className="w-5 h-5" />
                        取込完了
                      </p>
                      <div className="mt-2 text-sm space-y-1">
                        <p>取込件数: {importResult.total_count}件</p>
                        <p>自動照合: {importResult.auto_matched_count}件</p>
                        {(importResult.error_count ?? 0) > 0 && (
                          <p className="text-red-600">エラー: {importResult.error_count}件</p>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="flex items-center gap-2">
                      <AlertCircle className="w-5 h-5" />
                      取込に失敗しました
                    </p>
                  )}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setImportDialogOpen(false)}
                disabled={importing}
              >
                閉じる
              </Button>
              <Button
                onClick={handleImport}
                disabled={importing || !importFile}
              >
                {importing ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Upload className="w-4 h-4 mr-2" />
                )}
                取込開始
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 照合ダイアログ（振込用） */}
        <Dialog open={transferMatchDialogOpen} onOpenChange={setTransferMatchDialogOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <LinkIcon className="w-5 h-5" />
                振込データの照合
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {matchingTransfer && (
                <Card className="bg-gray-50">
                  <CardContent className="p-3">
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div>
                        <span className="text-gray-500">振込日:</span>
                        <span className="font-medium ml-2">
                          {formatDate(matchingTransfer.transferDate)}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">金額:</span>
                        <span className="font-medium ml-2">
                          {formatAmount(matchingTransfer.amount)}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">振込人:</span>
                        <span className="font-medium ml-2">{matchingTransfer.payerName}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              <div>
                <Label>保護者検索</Label>
                <div className="flex gap-2 mt-1">
                  <Input
                    value={guardianSearchQuery}
                    onChange={(e) => setGuardianSearchQuery(e.target.value)}
                    placeholder="保護者名で検索..."
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSearchGuardians();
                    }}
                  />
                  <Button
                    variant="outline"
                    onClick={handleSearchGuardians}
                    disabled={searchingGuardians}
                  >
                    {searchingGuardians ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Search className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>

              <div className="border rounded-lg max-h-64 overflow-auto">
                {guardianSearchResults.length > 0 ? (
                  <div className="divide-y">
                    {guardianSearchResults.map((guardian) => (
                      <div
                        key={guardian.guardianId}
                        className={`p-3 hover:bg-gray-50 cursor-pointer ${
                          selectedGuardian?.guardianId === guardian.guardianId
                            ? 'bg-blue-50 border-l-4 border-blue-500'
                            : ''
                        }`}
                        onClick={() => {
                          setSelectedGuardian(guardian);
                          setSelectedMatchInvoice(null);
                        }}
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">{guardian.guardianName}</p>
                            {guardian.guardianNameKana && (
                              <p className="text-xs text-gray-500">{guardian.guardianNameKana}</p>
                            )}
                          </div>
                          {selectedGuardian?.guardianId === guardian.guardianId && (
                            <Check className="w-5 h-5 text-blue-500" />
                          )}
                        </div>
                        {guardian.invoices.length > 0 && selectedGuardian?.guardianId === guardian.guardianId && (
                          <div className="mt-2 space-y-1">
                            {guardian.invoices.map((inv) => (
                              <div
                                key={inv.invoiceId}
                                className={`p-2 rounded text-sm flex justify-between items-center ${
                                  selectedMatchInvoice === inv.invoiceId
                                    ? 'bg-blue-100'
                                    : 'bg-gray-100 hover:bg-gray-200'
                                }`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedMatchInvoice(
                                    selectedMatchInvoice === inv.invoiceId ? null : inv.invoiceId
                                  );
                                }}
                              >
                                <span>{inv.billingLabel}</span>
                                <span className={inv.balanceDue > 0 ? 'text-red-600' : ''}>
                                  未払: {formatAmount(inv.balanceDue)}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center text-gray-500">
                    <User className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                    <p>保護者を検索してください</p>
                  </div>
                )}
              </div>
            </div>

            <DialogFooter className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setTransferMatchDialogOpen(false)}
                disabled={matching}
              >
                キャンセル
              </Button>
              {/* 照合済みの場合は「入金確認（未消込）」ボタンを表示 */}
              {matchingTransfer?.status === 'matched' && (
                <Button
                  variant="secondary"
                  onClick={handleConfirmPaymentOnly}
                  disabled={matching}
                >
                  {matching ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <Check className="w-4 h-4 mr-2" />
                  )}
                  入金確認（未消込）
                </Button>
              )}
              <Button
                onClick={handleTransferMatch}
                disabled={matching || !selectedGuardian}
              >
                {matching ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                {selectedMatchInvoice ? '照合して入金処理' : '照合のみ'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </ThreePaneLayout>
  );
}
