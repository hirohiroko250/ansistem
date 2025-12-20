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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  ChevronLeft,
  Search,
  CheckCircle,
  AlertCircle,
  Loader2,
  CreditCard,
  User,
  Building2,
  Receipt,
  Upload,
  FileSpreadsheet,
  Check,
  X,
  Link as LinkIcon,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import apiClient from "@/lib/api/client";
import type { Invoice, Guardian, Student } from "@/lib/api/types";

// 検索結果の型
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

export default function BankTransfersPage() {
  const searchParams = useSearchParams();

  // タブ状態 - URLパラメータから初期値を取得
  const [activeTab, setActiveTab] = useState<string>(() => {
    const tab = searchParams.get("tab");
    return tab === "import" ? "import" : "search";
  });

  // 検索
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  // 選択された対象
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);

  // 入金登録ダイアログ
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [paymentDate, setPaymentDate] = useState(() => {
    const now = new Date();
    return now.toISOString().split('T')[0];
  });
  const [paymentAmount, setPaymentAmount] = useState<string>("");
  const [payerName, setPayerName] = useState("");
  const [bankName, setBankName] = useState("");
  const [paymentNotes, setPaymentNotes] = useState("");
  const [registering, setRegistering] = useState(false);
  const [registerResult, setRegisterResult] = useState<{ success: boolean; message: string } | null>(null);

  // インポート関連
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

  // 照合ダイアログ
  const [matchDialogOpen, setMatchDialogOpen] = useState(false);
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
    if (activeTab === "import") {
      loadImportBatches();
    }
  }, [activeTab, loadImportBatches]);

  // 検索実行
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;

    setSearching(true);
    setSearchResults([]);
    setSelectedResult(null);
    setSelectedInvoice(null);

    try {
      // 保護者と生徒を並列で検索
      const [guardiansRes, studentsRes] = await Promise.all([
        apiClient.get<{ results?: Guardian[]; data?: Guardian[] }>('/students/guardians/', {
          search: searchQuery,
          page_size: 20,
        }),
        apiClient.get<{ results?: Student[]; data?: Student[] }>('/students/', {
          search: searchQuery,
          page_size: 20,
        }),
      ]);

      const guardians = guardiansRes.results || guardiansRes.data || [];
      const students = studentsRes.results || studentsRes.data || [];

      // 保護者IDをリストアップ（請求書を取得するため）
      const guardianIds = new Set<string>();
      const results: SearchResult[] = [];

      // 保護者の結果
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

      // 生徒の結果
      for (const student of students) {
        const guardianId = student.guardianId || student.guardian_id || student.guardian?.id;
        if (guardianId) {
          guardianIds.add(guardianId);
        }
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

      // 保護者ごとの請求書を取得
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

        // 結果に請求書を紐付け
        for (const result of results) {
          const gId = result.type === 'guardian' ? result.id : result.guardianId;
          if (gId) {
            result.invoices = invoiceMap.get(gId) || [];
          }
        }
      }

      setSearchResults(results);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setSearching(false);
    }
  }, [searchQuery]);

  // 検索結果を選択
  const handleSelectResult = (result: SearchResult) => {
    setSelectedResult(result);
    setSelectedInvoice(null);
  };

  // 請求書を選択して入金登録を開く
  const openPaymentDialog = (invoice: Invoice) => {
    setSelectedInvoice(invoice);
    const balanceDue = Number(invoice.balance_due || invoice.balanceDue || invoice.total_amount || invoice.totalAmount || 0);
    setPaymentAmount(String(balanceDue));
    setPayerName(selectedResult?.name || '');
    setBankName('');
    setPaymentNotes('');
    setRegisterResult(null);
    setPaymentDialogOpen(true);
  };

  // 入金登録
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
      if (selectedResult) {
        const gId = selectedResult.type === 'guardian' ? selectedResult.id : selectedResult.guardianId;
        if (gId) {
          const res = await apiClient.get<{ results?: Invoice[]; data?: Invoice[] }>('/billing/invoices/', {
            guardian_id: gId,
            page_size: 50,
          });
          setSelectedResult({
            ...selectedResult,
            invoices: res.results || res.data || [],
          });
        }
      }

      // ダイアログを閉じる（成功の場合）
      setTimeout(() => {
        setPaymentDialogOpen(false);
        setRegisterResult(null);
      }, 1500);
    } catch (error) {
      console.error('Payment registration error:', error);
      setRegisterResult({ success: false, message: '入金登録に失敗しました' });
    } finally {
      setRegistering(false);
    }
  };

  // ファイルインポート
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

      // バッチ一覧を更新
      loadImportBatches();

      // バッチ詳細を読み込み
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
  const openMatchDialog = (transfer: BankTransfer) => {
    setMatchingTransfer(transfer);
    setGuardianSearchQuery(transfer.payerName || '');
    setGuardianSearchResults(transfer.candidateGuardians || []);
    setSelectedGuardian(null);
    setSelectedMatchInvoice(null);
    setMatchDialogOpen(true);
  };

  // 照合エラー状態
  const [matchError, setMatchError] = useState<string | null>(null);

  // 照合実行
  const handleMatch = async () => {
    if (!matchingTransfer || !selectedGuardian) return;

    setMatching(true);
    setMatchError(null);
    try {
      console.log('Matching transfer:', matchingTransfer.id, 'to guardian:', selectedGuardian.guardianId);

      // まず照合
      const matchResult = await apiClient.post<{ success: boolean; message: string }>(`/billing/transfers/${matchingTransfer.id}/match/`, {
        guardian_id: selectedGuardian.guardianId,
      });
      console.log('Match result:', matchResult);

      // 入金処理を実行（請求書の有無に関わらず）
      const applyResult = await apiClient.post<{ success: boolean; message: string }>(`/billing/transfers/${matchingTransfer.id}/apply/`, {
        invoice_id: selectedMatchInvoice || undefined,
      });
      console.log('Apply result:', applyResult);

      setMatchDialogOpen(false);

      // バッチ詳細を更新
      if (selectedBatch) {
        loadBatchDetail(selectedBatch.id);
      }
    } catch (error) {
      console.error('Match error:', error);
      const errorMessage = error instanceof Error ? error.message : '照合に失敗しました';
      setMatchError(errorMessage);
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

  // 金額フォーマット
  const formatAmount = (amount: number | string | undefined): string => {
    const num = Number(amount || 0);
    return `¥${num.toLocaleString()}`;
  };

  // ステータスバッジ
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
          <h1 className="text-3xl font-bold text-gray-900 mb-2">振込入金確認</h1>
          <p className="text-gray-600">
            振込データのインポートと照合、手動での入金登録を行います
          </p>
        </div>

        {/* タブ切り替え */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="mb-4">
            <TabsTrigger value="search" className="flex items-center gap-2">
              <Search className="w-4 h-4" />
              手動検索
            </TabsTrigger>
            <TabsTrigger value="import" className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              データ取込
            </TabsTrigger>
          </TabsList>

          {/* 手動検索タブ */}
          <TabsContent value="search" className="flex-1 flex flex-col">
            {/* 検索 */}
            <Card className="mb-6">
              <CardContent className="p-4">
                <div className="flex gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <Input
                      type="text"
                      placeholder="生徒名・保護者名・電話番号で検索..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSearch();
                      }}
                      className="pl-10"
                    />
                  </div>
                  <Button onClick={handleSearch} disabled={searching}>
                    {searching ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <Search className="w-4 h-4 mr-2" />
                    )}
                    検索
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* メインコンテンツ */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-hidden">
              {/* 検索結果 */}
              <Card className="flex flex-col overflow-hidden">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <User className="w-5 h-5" />
                    検索結果
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-0">
                  {searching ? (
                    <div className="flex items-center justify-center h-32">
                      <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                    </div>
                  ) : searchResults.length > 0 ? (
                    <div className="divide-y">
                      {searchResults.map((result) => (
                        <div
                          key={`${result.type}-${result.id}`}
                          className={`p-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                            selectedResult?.id === result.id && selectedResult?.type === result.type
                              ? 'bg-blue-50 border-l-4 border-blue-500'
                              : ''
                          }`}
                          onClick={() => handleSelectResult(result)}
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-2">
                                {result.type === 'guardian' ? (
                                  <Badge variant="outline" className="text-xs">保護者</Badge>
                                ) : (
                                  <Badge variant="outline" className="text-xs bg-blue-50">生徒</Badge>
                                )}
                                <span className="font-medium">{result.name}</span>
                              </div>
                              {result.kana && (
                                <p className="text-xs text-gray-500 mt-0.5">{result.kana}</p>
                              )}
                              {result.type === 'student' && result.guardianName && (
                                <p className="text-xs text-gray-600 mt-1">
                                  保護者: {result.guardianName}
                                </p>
                              )}
                              {result.phone && (
                                <p className="text-xs text-gray-500 mt-0.5">{result.phone}</p>
                              )}
                            </div>
                            <div className="text-right">
                              <p className="text-xs text-gray-500">請求書</p>
                              <p className="font-medium">{result.invoices.length}件</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : searchQuery && !searching ? (
                    <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                      <AlertCircle className="w-8 h-8 mb-2 text-gray-400" />
                      <p>検索結果がありません</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                      <Search className="w-8 h-8 mb-2 text-gray-300" />
                      <p>生徒名・保護者名で検索してください</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* 請求書一覧 */}
              <Card className="flex flex-col overflow-hidden">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Receipt className="w-5 h-5" />
                    請求書一覧
                    {selectedResult && (
                      <span className="text-sm font-normal text-gray-500">
                        - {selectedResult.name}
                      </span>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-0">
                  {selectedResult ? (
                    selectedResult.invoices.length > 0 ? (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[100px]">請求月</TableHead>
                            <TableHead className="w-[80px]">状態</TableHead>
                            <TableHead className="text-right">請求額</TableHead>
                            <TableHead className="text-right">未払額</TableHead>
                            <TableHead className="w-[80px]">操作</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectedResult.invoices.map((invoice) => {
                            const totalAmount = Number(invoice.total_amount || invoice.totalAmount || 0);
                            const balanceDue = Number(invoice.balance_due || invoice.balanceDue || 0);
                            const status = invoice.status || 'draft';

                            return (
                              <TableRow key={invoice.id}>
                                <TableCell>
                                  {invoice.billing_year || invoice.billingYear}/{(invoice.billing_month || invoice.billingMonth || 0).toString().padStart(2, '0')}
                                </TableCell>
                                <TableCell>{getStatusBadge(status)}</TableCell>
                                <TableCell className="text-right">
                                  {formatAmount(totalAmount)}
                                </TableCell>
                                <TableCell className={`text-right ${balanceDue > 0 ? 'text-red-600 font-medium' : ''}`}>
                                  {formatAmount(balanceDue)}
                                </TableCell>
                                <TableCell>
                                  <Button
                                    size="sm"
                                    variant={balanceDue > 0 ? 'default' : 'outline'}
                                    onClick={() => openPaymentDialog(invoice)}
                                  >
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
                        <p>請求書がありません</p>
                      </div>
                    )
                  ) : (
                    <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                      <Receipt className="w-8 h-8 mb-2 text-gray-300" />
                      <p>左側から対象を選択してください</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* データ取込タブ */}
          <TabsContent value="import" className="flex-1 flex flex-col overflow-hidden">
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 overflow-hidden">
              {/* インポートバッチ一覧 */}
              <Card className="flex flex-col overflow-hidden">
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <FileSpreadsheet className="w-5 h-5" />
                      インポート履歴
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
                          onClick={() => loadBatchDetail(batch.id)}
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-medium text-sm">{batch.fileName}</p>
                              <p className="text-xs text-gray-500 mt-1">
                                {new Date(batch.importedAt).toLocaleString()}
                              </p>
                            </div>
                            {getStatusBadge(batch.status)}
                          </div>
                          <div className="flex gap-4 mt-2 text-xs text-gray-600">
                            <span>総件数: {batch.totalCount}</span>
                            <span className="text-green-600">照合済: {batch.matchedCount}</span>
                            <span className="text-red-600">未照合: {batch.unmatchedCount}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                      <FileSpreadsheet className="w-8 h-8 mb-2 text-gray-300" />
                      <p>インポート履歴がありません</p>
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
                      <Receipt className="w-5 h-5" />
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
                                {new Date(transfer.transferDate).toLocaleDateString()}
                              </TableCell>
                              <TableCell>
                                {transfer.guardianNoHint ? (
                                  <button
                                    className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                    onClick={() => window.open(`/parents?search=${transfer.guardianNoHint}`, '_blank')}
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
                                  {transfer.payerNameKana && (
                                    <p className="text-xs text-gray-500">{transfer.payerNameKana}</p>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell className="text-right font-medium">
                                {formatAmount(transfer.amount)}
                              </TableCell>
                              <TableCell>
                                {getStatusBadge(transfer.status)}
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
                                    onClick={() => openMatchDialog(transfer)}
                                  >
                                    <LinkIcon className="w-3 h-3 mr-1" />
                                    照合
                                  </Button>
                                )}
                                {transfer.status === 'matched' && (
                                  <Button
                                    size="sm"
                                    variant="default"
                                    onClick={() => openMatchDialog(transfer)}
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
                        <Receipt className="w-8 h-8 mb-2 text-gray-300" />
                        <p>振込データがありません</p>
                      </div>
                    )
                  ) : (
                    <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                      <Receipt className="w-8 h-8 mb-2 text-gray-300" />
                      <p>左側からインポートバッチを選択してください</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* 入金登録ダイアログ */}
        <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CreditCard className="w-5 h-5" />
                振込入金登録
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {/* 対象情報 */}
              <Card className="bg-gray-50">
                <CardContent className="p-3">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-500">対象:</span>
                      <span className="font-medium ml-2">{selectedResult?.name}</span>
                    </div>
                    {selectedInvoice && (
                      <>
                        <div>
                          <span className="text-gray-500">請求月:</span>
                          <span className="font-medium ml-2">
                            {selectedInvoice.billing_year || selectedInvoice.billingYear}/
                            {(selectedInvoice.billing_month || selectedInvoice.billingMonth || 0).toString().padStart(2, '0')}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500">請求額:</span>
                          <span className="font-medium ml-2">
                            {formatAmount(selectedInvoice.total_amount || selectedInvoice.totalAmount)}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500">未払額:</span>
                          <span className="font-medium ml-2 text-red-600">
                            {formatAmount(selectedInvoice.balance_due || selectedInvoice.balanceDue)}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* 入金情報 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="paymentDate">入金日</Label>
                  <Input
                    id="paymentDate"
                    type="date"
                    value={paymentDate}
                    onChange={(e) => setPaymentDate(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="paymentAmount">入金額</Label>
                  <Input
                    id="paymentAmount"
                    type="number"
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(e.target.value)}
                    className="mt-1"
                    placeholder="0"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="payerName">振込名義</Label>
                <Input
                  id="payerName"
                  value={payerName}
                  onChange={(e) => setPayerName(e.target.value)}
                  className="mt-1"
                  placeholder="振込人の名義"
                />
              </div>

              <div>
                <Label htmlFor="bankName">振込元銀行</Label>
                <Input
                  id="bankName"
                  value={bankName}
                  onChange={(e) => setBankName(e.target.value)}
                  className="mt-1"
                  placeholder="○○銀行 ○○支店"
                />
              </div>

              <div>
                <Label htmlFor="paymentNotes">備考</Label>
                <Input
                  id="paymentNotes"
                  value={paymentNotes}
                  onChange={(e) => setPaymentNotes(e.target.value)}
                  className="mt-1"
                  placeholder="メモがあれば入力"
                />
              </div>

              {/* 登録結果 */}
              {registerResult && (
                <div className={`p-3 rounded-lg flex items-center gap-2 ${
                  registerResult.success
                    ? 'bg-green-50 text-green-800'
                    : 'bg-red-50 text-red-800'
                }`}>
                  {registerResult.success ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : (
                    <AlertCircle className="w-5 h-5" />
                  )}
                  {registerResult.message}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setPaymentDialogOpen(false)}
                disabled={registering}
              >
                キャンセル
              </Button>
              <Button
                onClick={handleRegisterPayment}
                disabled={registering || !paymentAmount}
              >
                {registering ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <CheckCircle className="w-4 h-4 mr-2" />
                )}
                入金を登録
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
                      CSV, Excel (.xlsx, .xls) に対応
                    </p>
                  </label>
                </div>
              </div>

              <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                <p className="font-medium mb-2">必要なカラム:</p>
                <ul className="list-disc list-inside text-xs space-y-1">
                  <li>振込日 (YYYY-MM-DD形式)</li>
                  <li>金額</li>
                  <li>振込人名義</li>
                  <li>振込人名義カナ (任意)</li>
                  <li>銀行名 (任意)</li>
                  <li>支店名 (任意)</li>
                </ul>
              </div>

              {/* インポート結果 */}
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
                        インポート完了
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
                      インポートに失敗しました
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

        {/* 照合ダイアログ */}
        <Dialog open={matchDialogOpen} onOpenChange={setMatchDialogOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <LinkIcon className="w-5 h-5" />
                振込データの照合
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {/* 振込データ情報 */}
              {matchingTransfer && (
                <Card className="bg-gray-50">
                  <CardContent className="p-3">
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div>
                        <span className="text-gray-500">振込日:</span>
                        <span className="font-medium ml-2">
                          {new Date(matchingTransfer.transferDate).toLocaleDateString()}
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

              {/* 保護者検索 */}
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

              {/* 検索結果/候補一覧 */}
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
                        {/* 請求書一覧 */}
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

              {/* エラー表示 */}
              {matchError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    {matchError}
                  </div>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setMatchDialogOpen(false)}
                disabled={matching}
              >
                キャンセル
              </Button>
              <Button
                onClick={handleMatch}
                disabled={matching || !selectedGuardian}
              >
                {matching ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                確定して入金処理
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </ThreePaneLayout>
  );
}
