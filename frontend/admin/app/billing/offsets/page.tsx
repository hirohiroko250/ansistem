"use client";

import { useEffect, useState, useCallback } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
  DialogDescription,
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
  Loader2,
  RefreshCw,
  ArrowUpRight,
  ArrowDownLeft,
  Repeat,
  Settings,
  PlusCircle,
  CheckCircle,
  XCircle,
  Clock,
  Ban,
  Search,
  FileText,
  Undo2,
} from "lucide-react";
import Link from "next/link";
import {
  getOffsetLogs,
  getRefundRequests,
  createRefundRequest,
  approveRefundRequest,
  type OffsetLog,
  type RefundRequest,
} from "@/lib/api/staff";
import apiClient from "@/lib/api/client";

export default function OffsetsPage() {
  // タブ状態
  const [activeTab, setActiveTab] = useState<string>("offset-logs");

  // 相殺ログ
  const [offsetLogs, setOffsetLogs] = useState<OffsetLog[]>([]);
  const [offsetLogsCount, setOffsetLogsCount] = useState(0);
  const [loadingOffsetLogs, setLoadingOffsetLogs] = useState(true);
  const [offsetLogFilter, setOffsetLogFilter] = useState<string>("all");

  // 返金申請
  const [refundRequests, setRefundRequests] = useState<RefundRequest[]>([]);
  const [refundRequestsCount, setRefundRequestsCount] = useState(0);
  const [loadingRefundRequests, setLoadingRefundRequests] = useState(true);
  const [refundStatusFilter, setRefundStatusFilter] = useState<string>("all");

  // 返金申請作成ダイアログ
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [guardianSearch, setGuardianSearch] = useState("");
  const [searchingGuardians, setSearchingGuardians] = useState(false);
  const [guardianResults, setGuardianResults] = useState<Array<{
    id: string;
    guardianNo?: string;
    guardian_no?: string;
    fullName?: string;
    full_name?: string;
  }>>([]);
  const [selectedGuardian, setSelectedGuardian] = useState<{
    id: string;
    guardianNo?: string;
    guardian_no?: string;
    fullName?: string;
    full_name?: string;
  } | null>(null);
  const [refundAmount, setRefundAmount] = useState("");
  const [refundMethod, setRefundMethod] = useState<"bank_transfer" | "cash" | "offset_next">("bank_transfer");
  const [refundReason, setRefundReason] = useState("");
  const [creating, setCreating] = useState(false);

  // 承認/却下ダイアログ
  const [approveDialogOpen, setApproveDialogOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<RefundRequest | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [approving, setApproving] = useState(false);

  // 相殺ログを読み込み
  const loadOffsetLogs = useCallback(async () => {
    setLoadingOffsetLogs(true);
    try {
      const params: { transaction_type?: string; page_size: number } = { page_size: 100 };
      if (offsetLogFilter !== "all") {
        params.transaction_type = offsetLogFilter;
      }
      const data = await getOffsetLogs(params);
      setOffsetLogs(data.results || []);
      setOffsetLogsCount(data.count || 0);
    } catch (error) {
      console.error("Error loading offset logs:", error);
    } finally {
      setLoadingOffsetLogs(false);
    }
  }, [offsetLogFilter]);

  // 返金申請を読み込み
  const loadRefundRequests = useCallback(async () => {
    setLoadingRefundRequests(true);
    try {
      const params: { status?: string; page_size: number } = { page_size: 100 };
      if (refundStatusFilter !== "all") {
        params.status = refundStatusFilter;
      }
      const data = await getRefundRequests(params);
      setRefundRequests(data.results || []);
      setRefundRequestsCount(data.count || 0);
    } catch (error) {
      console.error("Error loading refund requests:", error);
    } finally {
      setLoadingRefundRequests(false);
    }
  }, [refundStatusFilter]);

  useEffect(() => {
    if (activeTab === "offset-logs") {
      loadOffsetLogs();
    } else if (activeTab === "refund-requests") {
      loadRefundRequests();
    }
  }, [activeTab, loadOffsetLogs, loadRefundRequests]);

  // 保護者検索
  const handleSearchGuardians = async () => {
    if (!guardianSearch.trim()) return;
    setSearchingGuardians(true);
    try {
      const res = await apiClient.get<{ results?: Array<{
        id: string;
        guardianNo?: string;
        guardian_no?: string;
        fullName?: string;
        full_name?: string;
      }> }>('/students/guardians/', {
        search: guardianSearch,
        page_size: 10,
      });
      setGuardianResults(res.results || []);
    } catch (error) {
      console.error("Error searching guardians:", error);
    } finally {
      setSearchingGuardians(false);
    }
  };

  // 返金申請作成
  const handleCreateRefundRequest = async () => {
    if (!selectedGuardian || !refundAmount || !refundReason) return;
    setCreating(true);
    try {
      await createRefundRequest({
        guardian_id: selectedGuardian.id,
        refund_amount: Number(refundAmount),
        refund_method: refundMethod,
        reason: refundReason,
      });
      setCreateDialogOpen(false);
      resetCreateForm();
      loadRefundRequests();
    } catch (error) {
      console.error("Error creating refund request:", error);
    } finally {
      setCreating(false);
    }
  };

  const resetCreateForm = () => {
    setGuardianSearch("");
    setGuardianResults([]);
    setSelectedGuardian(null);
    setRefundAmount("");
    setRefundMethod("bank_transfer");
    setRefundReason("");
  };

  // 承認/却下
  const handleApprove = async (approve: boolean) => {
    if (!selectedRequest) return;
    setApproving(true);
    try {
      await approveRefundRequest({
        request_id: selectedRequest.id,
        approve,
        reject_reason: approve ? undefined : rejectReason,
      });
      setApproveDialogOpen(false);
      setSelectedRequest(null);
      setRejectReason("");
      loadRefundRequests();
    } catch (error) {
      console.error("Error approving refund request:", error);
    } finally {
      setApproving(false);
    }
  };

  // ユーティリティ関数
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

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case "deposit":
        return <ArrowDownLeft className="w-4 h-4 text-green-600" />;
      case "offset":
        return <Repeat className="w-4 h-4 text-blue-600" />;
      case "refund":
        return <ArrowUpRight className="w-4 h-4 text-red-600" />;
      case "adjustment":
        return <Settings className="w-4 h-4 text-gray-600" />;
      default:
        return null;
    }
  };

  const getTransactionBadge = (type: string, display?: string) => {
    const config: Record<string, { color: string }> = {
      deposit: { color: "bg-green-100 text-green-700" },
      offset: { color: "bg-blue-100 text-blue-700" },
      refund: { color: "bg-red-100 text-red-700" },
      adjustment: { color: "bg-gray-100 text-gray-700" },
    };
    const conf = config[type] || { color: "bg-gray-100 text-gray-700" };
    return <Badge className={conf.color}>{display || type}</Badge>;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "pending":
        return <Clock className="w-4 h-4 text-yellow-600" />;
      case "approved":
        return <CheckCircle className="w-4 h-4 text-blue-600" />;
      case "processing":
        return <Loader2 className="w-4 h-4 text-purple-600 animate-spin" />;
      case "completed":
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case "rejected":
        return <XCircle className="w-4 h-4 text-red-600" />;
      case "cancelled":
        return <Ban className="w-4 h-4 text-gray-600" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string, display?: string) => {
    const config: Record<string, { color: string }> = {
      pending: { color: "bg-yellow-100 text-yellow-700" },
      approved: { color: "bg-blue-100 text-blue-700" },
      processing: { color: "bg-purple-100 text-purple-700" },
      completed: { color: "bg-green-100 text-green-700" },
      rejected: { color: "bg-red-100 text-red-700" },
      cancelled: { color: "bg-gray-100 text-gray-500" },
    };
    const conf = config[status] || { color: "bg-gray-100 text-gray-700" };
    return <Badge className={conf.color}>{display || status}</Badge>;
  };

  const getMethodDisplay = (method: string): string => {
    const map: Record<string, string> = {
      bank_transfer: "銀行振込",
      cash: "現金",
      offset_next: "次回相殺",
    };
    return map[method] || method;
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
          <h1 className="text-3xl font-bold text-gray-900 mb-2">返金・相殺管理</h1>
          <p className="text-gray-600">
            預り金の入出金履歴と返金申請を管理します
          </p>
        </div>

        {/* タブ切り替え */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="mb-4">
            <TabsTrigger value="offset-logs" className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              相殺ログ
              {offsetLogsCount > 0 && (
                <Badge variant="outline" className="ml-1">{offsetLogsCount}</Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="refund-requests" className="flex items-center gap-2">
              <Undo2 className="w-4 h-4" />
              返金申請
              {refundRequestsCount > 0 && (
                <Badge variant="outline" className="ml-1">{refundRequestsCount}</Badge>
              )}
            </TabsTrigger>
          </TabsList>

          {/* 相殺ログタブ */}
          <TabsContent value="offset-logs" className="flex-1 flex flex-col overflow-auto">
            <Card className="flex-1 flex flex-col overflow-hidden">
              <CardHeader className="pb-2">
                <div className="flex justify-between items-center">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    入出金履歴
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Select value={offsetLogFilter} onValueChange={setOffsetLogFilter}>
                      <SelectTrigger className="w-[140px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">すべて</SelectItem>
                        <SelectItem value="deposit">入金</SelectItem>
                        <SelectItem value="offset">相殺</SelectItem>
                        <SelectItem value="refund">返金</SelectItem>
                        <SelectItem value="adjustment">調整</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button variant="outline" size="sm" onClick={loadOffsetLogs}>
                      <RefreshCw className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex-1 overflow-auto p-0">
                {loadingOffsetLogs ? (
                  <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                  </div>
                ) : offsetLogs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                    <FileText className="w-12 h-12 text-gray-300 mb-4" />
                    <p>相殺ログがありません</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[100px]">日時</TableHead>
                        <TableHead className="w-[100px]">種別</TableHead>
                        <TableHead>保護者</TableHead>
                        <TableHead>関連情報</TableHead>
                        <TableHead className="w-[120px] text-right">金額</TableHead>
                        <TableHead className="w-[120px] text-right">残高</TableHead>
                        <TableHead>理由</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {offsetLogs.map((log) => {
                        const transactionType = log.transactionType || log.transaction_type || "";
                        const transactionTypeDisplay = log.transactionTypeDisplay || log.transaction_type_display || transactionType;
                        const guardianName = log.guardianName || log.guardian_name || "";
                        const invoiceLabel = log.invoiceBillingLabel || log.invoice_billing_label || "";
                        const paymentNo = log.paymentNo || log.payment_no || "";
                        const amount = Number(log.amount || 0);
                        const balanceAfter = Number(log.balanceAfter || log.balance_after || 0);
                        const createdAt = log.createdAt || log.created_at || "";

                        return (
                          <TableRow key={log.id}>
                            <TableCell className="text-sm">{formatDate(createdAt)}</TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                {getTransactionIcon(transactionType)}
                                {getTransactionBadge(transactionType, transactionTypeDisplay)}
                              </div>
                            </TableCell>
                            <TableCell className="font-medium">{guardianName}</TableCell>
                            <TableCell className="text-sm text-gray-600">
                              {invoiceLabel && <span className="mr-2">{invoiceLabel}</span>}
                              {paymentNo && <span className="text-xs text-gray-400">入金#{paymentNo}</span>}
                            </TableCell>
                            <TableCell className={`text-right font-medium ${amount >= 0 ? "text-green-600" : "text-red-600"}`}>
                              {amount >= 0 ? "+" : ""}{formatAmount(amount)}
                            </TableCell>
                            <TableCell className="text-right">{formatAmount(balanceAfter)}</TableCell>
                            <TableCell className="text-sm text-gray-600 max-w-[200px] truncate">
                              {log.reason || "-"}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* 返金申請タブ */}
          <TabsContent value="refund-requests" className="flex-1 flex flex-col overflow-auto">
            <Card className="flex-1 flex flex-col overflow-hidden">
              <CardHeader className="pb-2">
                <div className="flex justify-between items-center">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Undo2 className="w-5 h-5" />
                    返金申請一覧
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Select value={refundStatusFilter} onValueChange={setRefundStatusFilter}>
                      <SelectTrigger className="w-[140px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">すべて</SelectItem>
                        <SelectItem value="pending">申請中</SelectItem>
                        <SelectItem value="approved">承認済</SelectItem>
                        <SelectItem value="processing">処理中</SelectItem>
                        <SelectItem value="completed">完了</SelectItem>
                        <SelectItem value="rejected">却下</SelectItem>
                        <SelectItem value="cancelled">取消</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button variant="outline" size="sm" onClick={loadRefundRequests}>
                      <RefreshCw className="w-4 h-4" />
                    </Button>
                    <Button size="sm" onClick={() => { resetCreateForm(); setCreateDialogOpen(true); }}>
                      <PlusCircle className="w-4 h-4 mr-1" />
                      新規申請
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex-1 overflow-auto p-0">
                {loadingRefundRequests ? (
                  <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                  </div>
                ) : refundRequests.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                    <Undo2 className="w-12 h-12 text-gray-300 mb-4" />
                    <p>返金申請がありません</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[140px]">申請番号</TableHead>
                        <TableHead className="w-[100px]">申請日</TableHead>
                        <TableHead>保護者</TableHead>
                        <TableHead className="w-[120px] text-right">返金額</TableHead>
                        <TableHead className="w-[100px]">返金方法</TableHead>
                        <TableHead className="w-[100px]">ステータス</TableHead>
                        <TableHead>理由</TableHead>
                        <TableHead className="w-[100px]">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {refundRequests.map((request) => {
                        const requestNo = request.requestNo || request.request_no || "";
                        const guardianName = request.guardianName || request.guardian_name || "";
                        const refundAmt = Number(request.refundAmount || request.refund_amount || 0);
                        const method = request.refundMethod || request.refund_method || "";
                        const methodDisplay = request.refundMethodDisplay || request.refund_method_display || getMethodDisplay(method);
                        const status = request.status || "";
                        const statusDisplay = request.statusDisplay || request.status_display || status;
                        const requestedAt = request.requestedAt || request.requested_at || "";

                        return (
                          <TableRow key={request.id}>
                            <TableCell className="font-mono text-sm">{requestNo}</TableCell>
                            <TableCell className="text-sm">{formatDate(requestedAt)}</TableCell>
                            <TableCell className="font-medium">{guardianName}</TableCell>
                            <TableCell className="text-right font-medium text-red-600">
                              {formatAmount(refundAmt)}
                            </TableCell>
                            <TableCell className="text-sm">{methodDisplay}</TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                {getStatusIcon(status)}
                                {getStatusBadge(status, statusDisplay)}
                              </div>
                            </TableCell>
                            <TableCell className="text-sm text-gray-600 max-w-[200px] truncate">
                              {request.reason || "-"}
                            </TableCell>
                            <TableCell>
                              {status === "pending" && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    setSelectedRequest(request);
                                    setRejectReason("");
                                    setApproveDialogOpen(true);
                                  }}
                                >
                                  審査
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* 返金申請作成ダイアログ */}
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <PlusCircle className="w-5 h-5" />
                返金申請作成
              </DialogTitle>
              <DialogDescription>
                返金申請を作成します
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {/* 保護者検索 */}
              <div>
                <Label>保護者</Label>
                {selectedGuardian ? (
                  <div className="mt-2 p-3 bg-blue-50 rounded-lg flex justify-between items-center">
                    <div>
                      <p className="font-medium">{selectedGuardian.fullName || selectedGuardian.full_name}</p>
                      <p className="text-sm text-gray-500">ID: {selectedGuardian.guardianNo || selectedGuardian.guardian_no}</p>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => setSelectedGuardian(null)}>
                      変更
                    </Button>
                  </div>
                ) : (
                  <div className="mt-2 space-y-2">
                    <div className="flex gap-2">
                      <Input
                        placeholder="名前で検索..."
                        value={guardianSearch}
                        onChange={(e) => setGuardianSearch(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") handleSearchGuardians(); }}
                      />
                      <Button onClick={handleSearchGuardians} disabled={searchingGuardians}>
                        {searchingGuardians ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                      </Button>
                    </div>
                    {guardianResults.length > 0 && (
                      <div className="border rounded-lg max-h-40 overflow-auto divide-y">
                        {guardianResults.map((guardian) => (
                          <div
                            key={guardian.id}
                            className="p-2 hover:bg-gray-50 cursor-pointer"
                            onClick={() => {
                              setSelectedGuardian(guardian);
                              setGuardianResults([]);
                            }}
                          >
                            <p className="font-medium">{guardian.fullName || guardian.full_name}</p>
                            <p className="text-xs text-gray-500">ID: {guardian.guardianNo || guardian.guardian_no}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* 返金額 */}
              <div>
                <Label>返金額</Label>
                <Input
                  type="number"
                  value={refundAmount}
                  onChange={(e) => setRefundAmount(e.target.value)}
                  placeholder="0"
                  className="mt-2"
                />
              </div>

              {/* 返金方法 */}
              <div>
                <Label>返金方法</Label>
                <Select value={refundMethod} onValueChange={(v) => setRefundMethod(v as typeof refundMethod)}>
                  <SelectTrigger className="mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bank_transfer">銀行振込</SelectItem>
                    <SelectItem value="cash">現金</SelectItem>
                    <SelectItem value="offset_next">次回相殺</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* 理由 */}
              <div>
                <Label>返金理由</Label>
                <Textarea
                  value={refundReason}
                  onChange={(e) => setRefundReason(e.target.value)}
                  placeholder="返金の理由を入力..."
                  className="mt-2"
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreateDialogOpen(false)} disabled={creating}>
                キャンセル
              </Button>
              <Button
                onClick={handleCreateRefundRequest}
                disabled={creating || !selectedGuardian || !refundAmount || !refundReason}
              >
                {creating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <PlusCircle className="w-4 h-4 mr-2" />}
                申請作成
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 承認/却下ダイアログ */}
        <Dialog open={approveDialogOpen} onOpenChange={setApproveDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5" />
                返金申請の審査
              </DialogTitle>
              <DialogDescription>
                返金申請を承認または却下します
              </DialogDescription>
            </DialogHeader>
            {selectedRequest && (
              <div className="space-y-4 py-4">
                <Card className="bg-gray-50">
                  <CardContent className="p-3">
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-gray-500">申請番号:</span>{" "}
                        <span className="font-medium">{selectedRequest.requestNo || selectedRequest.request_no}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">保護者:</span>{" "}
                        <span className="font-medium">{selectedRequest.guardianName || selectedRequest.guardian_name}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">返金額:</span>{" "}
                        <span className="font-medium text-red-600">
                          {formatAmount(selectedRequest.refundAmount || selectedRequest.refund_amount)}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">返金方法:</span>{" "}
                        <span className="font-medium">
                          {selectedRequest.refundMethodDisplay || selectedRequest.refund_method_display ||
                           getMethodDisplay(selectedRequest.refundMethod || selectedRequest.refund_method || "")}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t text-sm">
                      <span className="text-gray-500">理由:</span>{" "}
                      <span>{selectedRequest.reason}</span>
                    </div>
                  </CardContent>
                </Card>

                <div>
                  <Label>却下理由（却下する場合）</Label>
                  <Textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="却下する場合は理由を入力..."
                    className="mt-2"
                    rows={2}
                  />
                </div>
              </div>
            )}
            <DialogFooter className="flex gap-2">
              <Button variant="outline" onClick={() => setApproveDialogOpen(false)} disabled={approving}>
                キャンセル
              </Button>
              <Button
                variant="destructive"
                onClick={() => handleApprove(false)}
                disabled={approving || !rejectReason}
              >
                {approving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <XCircle className="w-4 h-4 mr-2" />}
                却下
              </Button>
              <Button onClick={() => handleApprove(true)} disabled={approving}>
                {approving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                承認
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </ThreePaneLayout>
  );
}
