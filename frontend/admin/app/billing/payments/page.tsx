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
  CreditCard,
  Receipt,
  PlusCircle,
} from "lucide-react";
import Link from "next/link";
import apiClient from "@/lib/api/client";
import {
  getUnmatchedPayments,
  getMatchCandidates,
  matchPaymentToInvoice,
  type PaymentData,
  type MatchCandidate,
} from "@/lib/api/staff";
import type { Invoice, Guardian, Student } from "@/lib/api/types";

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
  guardianNo?: string;
  guardianName: string;
  guardianNameKana?: string;
  invoices: {
    invoiceId: string;
    invoiceNo: string;
    billingLabel: string;
    totalAmount: number;
    balanceDue: number;
    source?: 'invoice' | 'confirmed_billing';
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

// 手動検索結果の型
interface SearchResult {
  type: 'guardian' | 'student';
  id: string;
  name: string;
  kana?: string;
  guardianId?: string;
  guardianName?: string;
  phone?: string;
  invoices: Invoice[];
}

// 入金登録リクエスト
interface PaymentRequest {
  guardian_id: string;
  invoice_id?: string;
  payment_date: string;
  amount: number;
  method: string;
  payer_name?: string;
  bank_name?: string;
  notes?: string;
}

export default function PaymentMatchingPage() {
  const searchParams = useSearchParams();

  // タブ状態
  const [activeTab, setActiveTab] = useState<string>(() => {
    const tab = searchParams.get("tab");
    if (tab === "import") return "import";
    if (tab === "manual") return "manual";
    return "unmatched";
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
  const [searchType, setSearchType] = useState<'name' | 'guardian_no' | 'amount'>('name');
  const [guardianSearchResults, setGuardianSearchResults] = useState<CandidateGuardian[]>([]);
  const [searchingGuardians, setSearchingGuardians] = useState(false);
  const [selectedGuardian, setSelectedGuardian] = useState<CandidateGuardian | null>(null);
  const [selectedMatchInvoice, setSelectedMatchInvoice] = useState<string | null>(null);
  const [matching, setMatching] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);

  // === 手動入金タブ ===
  const [manualSearchQuery, setManualSearchQuery] = useState("");
  const [manualSearchResults, setManualSearchResults] = useState<SearchResult[]>([]);
  const [manualSearching, setManualSearching] = useState(false);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);

  // 手動入金登録ダイアログ
  const [manualPaymentDialogOpen, setManualPaymentDialogOpen] = useState(false);
  const [paymentDate, setPaymentDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [paymentAmount, setPaymentAmount] = useState<string>("");
  const [payerName, setPayerName] = useState("");
  const [bankName, setBankName] = useState("");
  const [paymentNotes, setPaymentNotes] = useState("");
  const [registering, setRegistering] = useState(false);
  const [registerResult, setRegisterResult] = useState<{ success: boolean; message: string } | null>(null);

  // URLパラメータの変更を監視
  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab === "import") setActiveTab("import");
    else if (tab === "manual") setActiveTab("manual");
  }, [searchParams]);

  // 未消込入金を読み込み
  async function loadUnmatchedPayments() {
    setLoadingPayments(true);
    try {
      const data = await getUnmatchedPayments();
      setPayments(data.payments);
      setPaymentCount(data.count);

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
    setLoadingBatches(true);
    try {
      const res = await apiClient.get<{ results?: ImportBatch[]; data?: ImportBatch[] }>('/billing/transfer-imports/');
      setImportBatches(res.results || res.data || []);
    } catch (error) {
      console.error('Failed to load import batches:', error);
    } finally {
      setLoadingBatches(false);
    }
  }, []);

  // バッチ詳細を読み込み
  const loadBatchDetail = useCallback(async (batchId: string) => {
    try {
      const res = await apiClient.get<ImportBatch>(`/billing/transfer-imports/${batchId}/`);
      setSelectedBatch(res);
    } catch (error) {
      console.error('Failed to load batch detail:', error);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "unmatched") {
      loadUnmatchedPayments();
    } else if (activeTab === "import") {
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
      if (res.batch_id) loadBatchDetail(res.batch_id);
    } catch (error) {
      console.error('Import error:', error);
      setImportResult({ success: false });
    } finally {
      setImporting(false);
    }
  };

  // 保護者検索（照合用）
  const handleSearchGuardians = async (overrideQuery?: string, overrideType?: 'name' | 'guardian_no' | 'amount') => {
    const query = overrideQuery ?? guardianSearchQuery;
    const type = overrideType ?? searchType;

    if (!query.trim()) return;
    if (type === 'name' && query.length < 2) return;

    setSearchingGuardians(true);
    try {
      const params: Record<string, string> = {};
      if (type === 'name') {
        params.q = query;
      } else if (type === 'guardian_no') {
        params.guardian_no = query;
      } else if (type === 'amount') {
        params.amount = query.replace(/[,¥￥]/g, '');
      }

      const res = await apiClient.get<{ guardians: CandidateGuardian[] }>('/billing/transfer-imports/search_guardians/', params);
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
    setSearchType('name');
    setGuardianSearchResults(transfer.candidateGuardians || []);
    setSelectedGuardian(null);
    setSelectedMatchInvoice(null);
    setMatchError(null);
    setTransferMatchDialogOpen(true);

    // 金額で自動検索を実行
    const amountStr = String(transfer.amount);
    if (amountStr) {
      setTimeout(() => {
        handleSearchGuardians(amountStr, 'amount');
      }, 100);
    }
  };

  // 照合実行
  const handleTransferMatch = async () => {
    if (!matchingTransfer || !selectedGuardian) return;

    setMatching(true);
    setMatchError(null);
    try {
      await apiClient.post(`/billing/transfers/${matchingTransfer.id}/match/`, {
        guardian_id: selectedGuardian.guardianId,
      });
      await apiClient.post(`/billing/transfers/${matchingTransfer.id}/apply/`, {
        invoice_id: selectedMatchInvoice || undefined,
      });

      setTransferMatchDialogOpen(false);
      if (selectedBatch) loadBatchDetail(selectedBatch.id);
      loadUnmatchedPayments();
    } catch (error) {
      console.error('Match error:', error);
      setMatchError(error instanceof Error ? error.message : '照合に失敗しました');
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

  // ID番号クリック時
  const handleIdClick = async (guardianNo: string) => {
    if (!guardianNo) return;
    window.open(`/parents?search=${guardianNo}`, '_blank');
  };

  // === 手動入金の処理 ===
  const handleManualSearch = useCallback(async () => {
    if (!manualSearchQuery.trim()) return;

    setManualSearching(true);
    setManualSearchResults([]);
    setSelectedResult(null);
    setSelectedInvoice(null);

    try {
      const [guardiansRes, studentsRes] = await Promise.all([
        apiClient.get<{ results?: Guardian[]; data?: Guardian[] }>('/students/guardians/', {
          search: manualSearchQuery,
          page_size: 20,
        }),
        apiClient.get<{ results?: Student[]; data?: Student[] }>('/students/', {
          search: manualSearchQuery,
          page_size: 20,
        }),
      ]);

      const guardians = guardiansRes.results || guardiansRes.data || [];
      const students = studentsRes.results || studentsRes.data || [];

      const guardianIds = new Set<string>();
      const results: SearchResult[] = [];

      for (const guardian of guardians) {
        guardianIds.add(guardian.id);
        results.push({
          type: 'guardian',
          id: guardian.id,
          name: guardian.full_name || `${guardian.last_name || ''}${guardian.first_name || ''}`,
          kana: guardian.full_name_kana || `${guardian.last_name_kana || ''}${guardian.first_name_kana || ''}`,
          phone: guardian.phone || '',
          invoices: [],
        });
      }

      for (const student of students) {
        const guardianId = student.guardianId || student.guardian_id || student.guardian?.id;
        if (guardianId) guardianIds.add(guardianId);
        results.push({
          type: 'student',
          id: student.id,
          name: student.full_name || `${student.last_name || ''}${student.first_name || ''}`,
          kana: student.full_name_kana || `${student.last_name_kana || ''}${student.first_name_kana || ''}`,
          guardianId: guardianId,
          guardianName: student.guardian?.full_name || '',
          invoices: [],
        });
      }

      if (guardianIds.size > 0) {
        const invoicePromises = Array.from(guardianIds).map(async (gId) => {
          try {
            const res = await apiClient.get<{ results?: Invoice[]; data?: Invoice[] }>('/billing/invoices/', {
              guardian_id: gId,
              page_size: 50,
            });
            return { guardianId: gId, invoices: res.results || res.data || [] };
          } catch {
            return { guardianId: gId, invoices: [] };
          }
        });

        const invoiceResults = await Promise.all(invoicePromises);
        const invoiceMap = new Map<string, Invoice[]>();
        for (const { guardianId, invoices } of invoiceResults) {
          invoiceMap.set(guardianId, invoices);
        }

        for (const result of results) {
          const gId = result.type === 'guardian' ? result.id : result.guardianId;
          if (gId) result.invoices = invoiceMap.get(gId) || [];
        }
      }

      setManualSearchResults(results);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setManualSearching(false);
    }
  }, [manualSearchQuery]);

  const handleSelectResult = (result: SearchResult) => {
    setSelectedResult(result);
    setSelectedInvoice(null);
  };

  const openManualPaymentDialog = (invoice: Invoice) => {
    setSelectedInvoice(invoice);
    const balanceDue = Number(invoice.balance_due || invoice.balanceDue || invoice.total_amount || invoice.totalAmount || 0);
    setPaymentAmount(String(balanceDue));
    setPayerName(selectedResult?.name || '');
    setBankName('');
    setPaymentNotes('');
    setRegisterResult(null);
    setManualPaymentDialogOpen(true);
  };

  const handleRegisterPayment = async () => {
    if (!selectedResult || !paymentAmount) return;

    setRegistering(true);
    setRegisterResult(null);

    try {
      const guardianId = selectedResult.type === 'guardian' ? selectedResult.id : selectedResult.guardianId;
      if (!guardianId) {
        setRegisterResult({ success: false, message: '保護者情報が見つかりません' });
        return;
      }

      const request: PaymentRequest = {
        guardian_id: guardianId,
        invoice_id: selectedInvoice?.id,
        payment_date: paymentDate,
        amount: Number(paymentAmount),
        method: 'bank_transfer',
        payer_name: payerName || undefined,
        bank_name: bankName || undefined,
        notes: paymentNotes || undefined,
      };

      await apiClient.post('/billing/payments/register/', request);
      setRegisterResult({ success: true, message: '振込入金を登録しました' });

      // 請求書一覧を更新
      const gId = selectedResult.type === 'guardian' ? selectedResult.id : selectedResult.guardianId;
      if (gId) {
        const res = await apiClient.get<{ results?: Invoice[]; data?: Invoice[] }>('/billing/invoices/', {
          guardian_id: gId,
          page_size: 50,
        });
        setSelectedResult({ ...selectedResult, invoices: res.results || res.data || [] });
      }

      setTimeout(() => {
        setManualPaymentDialogOpen(false);
        setRegisterResult(null);
      }, 1500);
    } catch (error) {
      console.error('Payment registration error:', error);
      setRegisterResult({ success: false, message: '入金登録に失敗しました' });
    } finally {
      setRegistering(false);
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

  const getStatusBadge = (status: string) => {
    const config: Record<string, { label: string; color: string }> = {
      draft: { label: '下書き', color: 'bg-gray-100 text-gray-700' },
      issued: { label: '発行済', color: 'bg-blue-100 text-blue-700' },
      paid: { label: '支払済', color: 'bg-green-100 text-green-700' },
      partial: { label: '一部入金', color: 'bg-yellow-100 text-yellow-700' },
      overdue: { label: '滞納', color: 'bg-red-100 text-red-700' },
      cancelled: { label: '取消', color: 'bg-gray-100 text-gray-500' },
      pending: { label: '未確認', color: 'bg-yellow-100 text-yellow-700' },
      matched: { label: '確認済', color: 'bg-blue-100 text-blue-700' },
      applied: { label: '入金済', color: 'bg-green-100 text-green-700' },
      unmatched: { label: '不明', color: 'bg-red-100 text-red-700' },
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
            振込データの取込・照合・手動入金登録を行います
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
            <TabsTrigger value="manual" className="flex items-center gap-2">
              <PlusCircle className="w-4 h-4" />
              手動入金
            </TabsTrigger>
          </TabsList>

          {/* 未消込入金タブ */}
          <TabsContent value="unmatched" className="flex-1 flex flex-col overflow-auto">
            <Card className="mb-4 bg-blue-50 border-blue-200">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-blue-900">入金消込について</p>
                    <p className="text-sm text-blue-700 mt-1">
                      銀行振込などで入金された金額を、対応する請求書と紐付けます。
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
                </div>
              </Card>
            ) : (
              <div className="space-y-6">
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
                            <TableRow key={transfer.id}>
                              <TableCell>{formatDate(transfer.transferDate)}</TableCell>
                              <TableCell>
                                {transfer.guardianNoHint ? (
                                  <button
                                    onClick={() => handleIdClick(transfer.guardianNoHint!)}
                                    className="text-blue-600 hover:underline"
                                  >
                                    {transfer.guardianNoHint}
                                  </button>
                                ) : '-'}
                              </TableCell>
                              <TableCell className="font-medium">{transfer.payerName || "-"}</TableCell>
                              <TableCell className="text-right font-medium">{formatAmount(transfer.amount)}</TableCell>
                              <TableCell>
                                <Button size="sm" variant="outline" onClick={() => openTransferMatchDialog(transfer)}>
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

                {paymentCount > 0 && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg">その他の未消込入金 <Badge variant="outline">{paymentCount}件</Badge></CardTitle>
                    </CardHeader>
                    <div className="overflow-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>入金番号</TableHead>
                            <TableHead>入金日</TableHead>
                            <TableHead>振込名義</TableHead>
                            <TableHead className="text-right">金額</TableHead>
                            <TableHead>操作</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {payments.map((payment) => (
                            <TableRow key={payment.id}>
                              <TableCell className="font-mono text-sm">{payment.payment_no}</TableCell>
                              <TableCell>{formatDate(payment.payment_date)}</TableCell>
                              <TableCell>{payment.payer_name || "-"}</TableCell>
                              <TableCell className="text-right font-medium">¥{Number(payment.amount).toLocaleString()}</TableCell>
                              <TableCell>
                                <Button variant="outline" size="sm" onClick={() => openMatchDialog(payment)}>
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
                      <Button size="sm" onClick={() => { setImportFile(null); setImportResult(null); setImportDialogOpen(true); }}>
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
                          className={`p-3 hover:bg-gray-50 cursor-pointer ${selectedBatch?.id === batch.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''}`}
                          onClick={() => loadBatchDetail(batch.id)}
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-medium text-sm">{batch.fileName}</p>
                              <p className="text-xs text-gray-500 mt-1">{formatDate(batch.importedAt)}</p>
                            </div>
                            {getStatusBadge(batch.status)}
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
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="lg:col-span-2 flex flex-col overflow-hidden">
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-lg">
                      振込データ {selectedBatch && <span className="text-sm font-normal text-gray-500">- {selectedBatch.fileName}</span>}
                    </CardTitle>
                    {selectedBatch && !selectedBatch.confirmedAt && selectedBatch.matchedCount > 0 && (
                      <Button size="sm" onClick={handleConfirmBatch}>
                        <CheckCircle className="w-4 h-4 mr-1" />
                        確定
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-0">
                  {selectedBatch?.transfers?.length ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>振込日</TableHead>
                          <TableHead>ID番号</TableHead>
                          <TableHead>振込人名義</TableHead>
                          <TableHead className="text-right">金額</TableHead>
                          <TableHead>状態</TableHead>
                          <TableHead>照合先</TableHead>
                          <TableHead>操作</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedBatch.transfers.map((transfer) => (
                          <TableRow key={transfer.id}>
                            <TableCell>{formatDate(transfer.transferDate)}</TableCell>
                            <TableCell>
                              {transfer.guardianNoHint ? (
                                <button onClick={() => handleIdClick(transfer.guardianNoHint!)} className="text-blue-600 hover:underline">
                                  {transfer.guardianNoHint}
                                </button>
                              ) : '-'}
                            </TableCell>
                            <TableCell>{transfer.payerName}</TableCell>
                            <TableCell className="text-right font-medium">{formatAmount(transfer.amount)}</TableCell>
                            <TableCell>{getStatusBadge(transfer.status)}</TableCell>
                            <TableCell>{transfer.guardianName || '-'}</TableCell>
                            <TableCell>
                              {transfer.status === 'pending' && (
                                <Button size="sm" variant="outline" onClick={() => openTransferMatchDialog(transfer)}>
                                  <LinkIcon className="w-3 h-3 mr-1" />
                                  照合
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
                      <p>左側から取込履歴を選択してください</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* 手動入金タブ */}
          <TabsContent value="manual" className="mt-0">
            <Card className="mb-4">
              <CardContent className="p-4">
                <div className="flex gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <Input
                      type="text"
                      placeholder="生徒名・保護者名・電話番号で検索..."
                      value={manualSearchQuery}
                      onChange={(e) => setManualSearchQuery(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') handleManualSearch(); }}
                      className="pl-10"
                    />
                  </div>
                  <Button onClick={handleManualSearch} disabled={manualSearching}>
                    {manualSearching ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}
                    検索
                  </Button>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-340px)]">
              <Card className="flex flex-col overflow-hidden">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <User className="w-5 h-5" />
                    検索結果
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-0">
                  {manualSearching ? (
                    <div className="flex items-center justify-center h-32">
                      <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                    </div>
                  ) : manualSearchResults.length > 0 ? (
                    <div className="divide-y">
                      {manualSearchResults.map((result) => (
                        <div
                          key={`${result.type}-${result.id}`}
                          className={`p-3 hover:bg-gray-50 cursor-pointer ${selectedResult?.id === result.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''}`}
                          onClick={() => handleSelectResult(result)}
                        >
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className={result.type === 'student' ? 'bg-blue-50' : ''}>
                              {result.type === 'guardian' ? '保護者' : '生徒'}
                            </Badge>
                            <span className="font-medium">{result.name}</span>
                          </div>
                          {result.kana && <p className="text-xs text-gray-500 mt-0.5">{result.kana}</p>}
                          <p className="text-xs text-gray-500 mt-1">請求書: {result.invoices.length}件</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                      <Search className="w-8 h-8 mb-2 text-gray-300" />
                      <p>生徒名・保護者名で検索してください</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="flex flex-col overflow-hidden">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Receipt className="w-5 h-5" />
                    請求書一覧
                    {selectedResult && <span className="text-sm font-normal text-gray-500">- {selectedResult.name}</span>}
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-0">
                  {selectedResult?.invoices.length ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>請求月</TableHead>
                          <TableHead>状態</TableHead>
                          <TableHead className="text-right">請求額</TableHead>
                          <TableHead className="text-right">未払額</TableHead>
                          <TableHead>操作</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedResult.invoices.map((invoice) => {
                          const balanceDue = Number(invoice.balance_due || invoice.balanceDue || 0);
                          return (
                            <TableRow key={invoice.id}>
                              <TableCell>{invoice.billing_year || invoice.billingYear}/{(invoice.billing_month || invoice.billingMonth || 0).toString().padStart(2, '0')}</TableCell>
                              <TableCell>{getStatusBadge(invoice.status || 'draft')}</TableCell>
                              <TableCell className="text-right">{formatAmount(invoice.total_amount || invoice.totalAmount)}</TableCell>
                              <TableCell className={`text-right ${balanceDue > 0 ? 'text-red-600 font-medium' : ''}`}>{formatAmount(balanceDue)}</TableCell>
                              <TableCell>
                                <Button size="sm" variant={balanceDue > 0 ? 'default' : 'outline'} onClick={() => openManualPaymentDialog(invoice)}>
                                  <CreditCard className="w-3 h-3 mr-1" />
                                  入金
                                </Button>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                      <Receipt className="w-8 h-8 mb-2 text-gray-300" />
                      <p>{selectedResult ? '請求書がありません' : '左側から対象を選択してください'}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* 消込ダイアログ */}
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
                  <CardContent className="p-3">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div><span className="text-blue-700">入金番号:</span> <span className="font-medium">{selectedPayment.payment_no}</span></div>
                      <div><span className="text-blue-700">入金日:</span> <span className="font-medium">{formatDate(selectedPayment.payment_date)}</span></div>
                      <div><span className="text-blue-700">振込名義:</span> <span className="font-medium">{selectedPayment.payer_name || "-"}</span></div>
                      <div><span className="text-blue-700">金額:</span> <span className="font-bold text-blue-900">¥{Number(selectedPayment.amount).toLocaleString()}</span></div>
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
                        <Card key={candidate.invoice.id} className={`cursor-pointer hover:border-blue-400 ${candidate.match_score >= 100 ? "border-green-300 bg-green-50" : ""}`}>
                          <CardContent className="p-3 flex items-center justify-between">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-mono text-sm">{candidate.invoice.invoice_no || candidate.invoice.invoiceNo}</span>
                                <Badge className={candidate.match_score >= 100 ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}>
                                  {candidate.match_reason}
                                </Badge>
                              </div>
                              <div className="text-sm text-gray-600">
                                未払: ¥{Number(candidate.invoice.balance_due || (candidate.invoice as any).balanceDue || 0).toLocaleString()}
                              </div>
                            </div>
                            <Button size="sm" onClick={() => handleMatch(candidate.invoice.id)} disabled={matchingInvoice !== null}>
                              {matchingInvoice === candidate.invoice.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <><CheckCircle className="w-4 h-4 mr-1" />消込</>}
                            </Button>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <AlertCircle className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                      <p>消込候補が見つかりませんでした</p>
                    </div>
                  )}
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setMatchDialogOpen(false)}>閉じる</Button>
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
                  <input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => setImportFile(e.target.files?.[0] || null)} className="hidden" id="import-file" />
                  <label htmlFor="import-file" className="cursor-pointer">
                    <FileSpreadsheet className="w-12 h-12 mx-auto text-gray-400 mb-2" />
                    <p className="text-sm text-gray-600">{importFile ? importFile.name : 'クリックしてファイルを選択'}</p>
                  </label>
                </div>
              </div>
              {importResult && (
                <div className={`p-3 rounded-lg ${importResult.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                  {importResult.success ? (
                    <div>
                      <p className="font-medium flex items-center gap-2"><CheckCircle className="w-5 h-5" />取込完了</p>
                      <p className="text-sm mt-2">取込件数: {importResult.total_count}件 / 自動照合: {importResult.auto_matched_count}件</p>
                    </div>
                  ) : (
                    <p className="flex items-center gap-2"><AlertCircle className="w-5 h-5" />取込に失敗しました</p>
                  )}
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setImportDialogOpen(false)} disabled={importing}>閉じる</Button>
              <Button onClick={handleImport} disabled={importing || !importFile}>
                {importing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Upload className="w-4 h-4 mr-2" />}
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
                      <div><span className="text-gray-500">振込日:</span> <span className="font-medium">{formatDate(matchingTransfer.transferDate)}</span></div>
                      <div><span className="text-gray-500">金額:</span> <span className="font-medium">{formatAmount(matchingTransfer.amount)}</span></div>
                      <div><span className="text-gray-500">振込人:</span> <span className="font-medium">{matchingTransfer.payerName}</span></div>
                    </div>
                  </CardContent>
                </Card>
              )}
              <div>
                <Label>保護者検索</Label>
                <div className="flex gap-1 mt-1 mb-2">
                  <Button
                    variant={searchType === 'name' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSearchType('name')}
                  >
                    名前
                  </Button>
                  <Button
                    variant={searchType === 'guardian_no' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSearchType('guardian_no')}
                  >
                    ID
                  </Button>
                  <Button
                    variant={searchType === 'amount' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => {
                      setSearchType('amount');
                      if (matchingTransfer) {
                        setGuardianSearchQuery(String(matchingTransfer.amount));
                      }
                    }}
                  >
                    金額
                  </Button>
                </div>
                <div className="flex gap-2">
                  <Input
                    value={guardianSearchQuery}
                    onChange={(e) => setGuardianSearchQuery(e.target.value)}
                    placeholder={
                      searchType === 'name' ? '保護者名で検索...' :
                      searchType === 'guardian_no' ? '保護者番号で検索...' :
                      '金額で検索...'
                    }
                    onKeyDown={(e) => { if (e.key === 'Enter') handleSearchGuardians(); }}
                  />
                  <Button variant="outline" onClick={() => handleSearchGuardians()} disabled={searchingGuardians}>
                    {searchingGuardians ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
              <div className="border rounded-lg max-h-64 overflow-auto">
                {guardianSearchResults.length > 0 ? (
                  <div className="divide-y">
                    {guardianSearchResults.map((guardian) => (
                      <div
                        key={guardian.guardianId}
                        className={`p-3 hover:bg-gray-50 cursor-pointer ${selectedGuardian?.guardianId === guardian.guardianId ? 'bg-blue-50 border-l-4 border-blue-500' : ''}`}
                        onClick={() => { setSelectedGuardian(guardian); setSelectedMatchInvoice(null); }}
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">{guardian.guardianName}</p>
                            <div className="flex gap-2 text-xs text-gray-500">
                              {guardian.guardianNo && <span>ID: {guardian.guardianNo}</span>}
                              {guardian.guardianNameKana && <span>{guardian.guardianNameKana}</span>}
                            </div>
                          </div>
                          {selectedGuardian?.guardianId === guardian.guardianId && <Check className="w-5 h-5 text-blue-500" />}
                        </div>
                        {guardian.invoices.length > 0 && selectedGuardian?.guardianId === guardian.guardianId && (
                          <div className="mt-2 space-y-1">
                            {guardian.invoices.map((inv) => (
                              <div
                                key={inv.invoiceId}
                                className={`p-2 rounded text-sm flex justify-between ${selectedMatchInvoice === inv.invoiceId ? 'bg-blue-100' : 'bg-gray-100 hover:bg-gray-200'}`}
                                onClick={(e) => { e.stopPropagation(); setSelectedMatchInvoice(selectedMatchInvoice === inv.invoiceId ? null : inv.invoiceId); }}
                              >
                                <span>{inv.billingLabel}</span>
                                <span className={inv.balanceDue > 0 ? 'text-red-600' : ''}>未払: {formatAmount(inv.balanceDue)}</span>
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
              {matchError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  {matchError}
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setTransferMatchDialogOpen(false)} disabled={matching}>キャンセル</Button>
              <Button onClick={handleTransferMatch} disabled={matching || !selectedGuardian}>
                {matching ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Check className="w-4 h-4 mr-2" />}
                {selectedMatchInvoice ? '照合して入金処理' : '照合のみ'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 手動入金登録ダイアログ */}
        <Dialog open={manualPaymentDialogOpen} onOpenChange={setManualPaymentDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CreditCard className="w-5 h-5" />
                振込入金登録
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <Card className="bg-gray-50">
                <CardContent className="p-3">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div><span className="text-gray-500">対象:</span> <span className="font-medium">{selectedResult?.name}</span></div>
                    {selectedInvoice && (
                      <>
                        <div><span className="text-gray-500">請求月:</span> <span className="font-medium">{selectedInvoice.billing_year || selectedInvoice.billingYear}/{(selectedInvoice.billing_month || selectedInvoice.billingMonth || 0).toString().padStart(2, '0')}</span></div>
                        <div><span className="text-gray-500">請求額:</span> <span className="font-medium">{formatAmount(selectedInvoice.total_amount || selectedInvoice.totalAmount)}</span></div>
                        <div><span className="text-gray-500">未払額:</span> <span className="font-medium text-red-600">{formatAmount(selectedInvoice.balance_due || selectedInvoice.balanceDue)}</span></div>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>入金日</Label>
                  <Input type="date" value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label>入金額</Label>
                  <Input type="number" value={paymentAmount} onChange={(e) => setPaymentAmount(e.target.value)} className="mt-1" placeholder="0" />
                </div>
              </div>
              <div>
                <Label>振込名義</Label>
                <Input value={payerName} onChange={(e) => setPayerName(e.target.value)} className="mt-1" placeholder="振込人の名義" />
              </div>
              <div>
                <Label>振込元銀行</Label>
                <Input value={bankName} onChange={(e) => setBankName(e.target.value)} className="mt-1" placeholder="○○銀行 ○○支店" />
              </div>
              <div>
                <Label>備考</Label>
                <Input value={paymentNotes} onChange={(e) => setPaymentNotes(e.target.value)} className="mt-1" placeholder="メモがあれば入力" />
              </div>
              {registerResult && (
                <div className={`p-3 rounded-lg flex items-center gap-2 ${registerResult.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                  {registerResult.success ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                  {registerResult.message}
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setManualPaymentDialogOpen(false)} disabled={registering}>キャンセル</Button>
              <Button onClick={handleRegisterPayment} disabled={registering || !paymentAmount}>
                {registering ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                入金を登録
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </ThreePaneLayout>
  );
}
