"use client";

import { useEffect, useState, useRef } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
  DialogDescription,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Search,
  Printer,
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  ChevronLeft,
  Edit,
  Eye,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import {
  getBankAccountRequests,
  approveBankAccountRequest,
  rejectBankAccountRequest,
  updateBankAccountRequest,
  type BankAccountRequest,
  type BankAccountRequestFilters,
} from "@/lib/api/bank-requests";

const statusConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  pending: { label: "申請中", color: "bg-yellow-100 text-yellow-700", icon: <Clock className="w-3 h-3" /> },
  approved: { label: "承認済", color: "bg-green-100 text-green-700", icon: <CheckCircle className="w-3 h-3" /> },
  rejected: { label: "却下", color: "bg-red-100 text-red-700", icon: <XCircle className="w-3 h-3" /> },
  cancelled: { label: "取消", color: "bg-gray-100 text-gray-500", icon: <FileText className="w-3 h-3" /> },
};

const requestTypeConfig: Record<string, { label: string; color: string }> = {
  new: { label: "新規登録", color: "bg-blue-100 text-blue-700" },
  update: { label: "変更", color: "bg-purple-100 text-purple-700" },
  delete: { label: "削除", color: "bg-red-100 text-red-700" },
};

export default function BankRequestsPage() {
  const [requests, setRequests] = useState<BankAccountRequest[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<BankAccountRequestFilters>({
    status: "pending",
    page: 1,
    page_size: 50,
  });
  const [searchQuery, setSearchQuery] = useState("");

  // 選択中の申請
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedRequest, setSelectedRequest] = useState<BankAccountRequest | null>(null);

  // ダイアログ
  const [detailOpen, setDetailOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [printDialogOpen, setPrintDialogOpen] = useState(false);

  // 編集フォーム
  const [editForm, setEditForm] = useState<Partial<BankAccountRequest>>({});

  // 印刷用iframe
  const printFrameRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    loadRequests();
  }, [filters]);

  async function loadRequests() {
    setLoading(true);
    try {
      const data = await getBankAccountRequests(filters);
      setRequests(data.results || []);
      setTotalCount(data.count || 0);
    } catch (error) {
      console.error("Failed to load requests:", error);
    } finally {
      setLoading(false);
    }
  }

  function handleSearch() {
    setFilters((prev) => ({
      ...prev,
      search: searchQuery || undefined,
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

  function handleRequestTypeChange(type: string) {
    setFilters((prev) => ({
      ...prev,
      request_type: type === "all" ? undefined : type,
      page: 1,
    }));
  }

  function openDetail(request: BankAccountRequest) {
    setSelectedRequest(request);
    setEditForm({
      bankName: request.bankName,
      bankCode: request.bankCode,
      branchName: request.branchName,
      branchCode: request.branchCode,
      accountType: request.accountType,
      accountNumber: request.accountNumber,
      accountHolder: request.accountHolder,
      accountHolderKana: request.accountHolderKana,
      requestNotes: request.requestNotes,
    });
    setEditMode(false);
    setDetailOpen(true);
  }

  async function handleApprove() {
    if (!selectedRequest) return;
    try {
      await approveBankAccountRequest(selectedRequest.id);
      setDetailOpen(false);
      loadRequests();
    } catch (error) {
      console.error("Failed to approve:", error);
      alert("承認に失敗しました");
    }
  }

  async function handleReject() {
    if (!selectedRequest) return;
    try {
      await rejectBankAccountRequest(selectedRequest.id, rejectReason);
      setRejectDialogOpen(false);
      setDetailOpen(false);
      setRejectReason("");
      loadRequests();
    } catch (error) {
      console.error("Failed to reject:", error);
      alert("却下に失敗しました");
    }
  }

  async function handleSaveEdit() {
    if (!selectedRequest) return;
    try {
      const updated = await updateBankAccountRequest(selectedRequest.id, editForm);
      setSelectedRequest(updated);
      setEditMode(false);
      loadRequests();
    } catch (error) {
      console.error("Failed to update:", error);
      alert("更新に失敗しました");
    }
  }

  function toggleSelectAll() {
    if (selectedIds.size === requests.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(requests.map((r) => r.id)));
    }
  }

  function toggleSelect(id: string) {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  }

  function handlePrint() {
    const targetRequests = selectedIds.size > 0
      ? requests.filter((r) => selectedIds.has(r.id))
      : selectedRequest
        ? [selectedRequest]
        : [];

    if (targetRequests.length === 0) {
      alert("印刷する申請を選択してください");
      return;
    }

    // 口座振替依頼書のHTMLを生成
    const printContent = generatePrintContent(targetRequests);

    const printWindow = window.open("", "_blank");
    if (printWindow) {
      printWindow.document.write(printContent);
      printWindow.document.close();
      printWindow.print();
    }
  }

  function generatePrintContent(targetRequests: BankAccountRequest[]): string {
    const forms = targetRequests.map((req) => `
      <div class="form-page">
        <h1>口座振替依頼書</h1>
        <div class="form-section">
          <h2>お届け日</h2>
          <p>${format(new Date(), "yyyy年MM月dd日", { locale: ja })}</p>
        </div>
        <div class="form-section">
          <h2>ご依頼人</h2>
          <table>
            <tr><th>お名前</th><td>${req.guardianName || ""}</td></tr>
            <tr><th>ご住所</th><td>${req.guardianAddress || ""}</td></tr>
            <tr><th>お電話番号</th><td>${req.guardianPhone || ""}</td></tr>
          </table>
        </div>
        <div class="form-section">
          <h2>預金口座</h2>
          <table>
            <tr><th>金融機関名</th><td>${req.bankName} (${req.bankCode})</td></tr>
            <tr><th>支店名</th><td>${req.branchName} (${req.branchCode})</td></tr>
            <tr><th>口座種別</th><td>${req.accountTypeDisplay || req.accountType}</td></tr>
            <tr><th>口座番号</th><td>${req.accountNumber}</td></tr>
            <tr><th>口座名義（カナ）</th><td>${req.accountHolderKana}</td></tr>
          </table>
        </div>
        <div class="form-section">
          <h2>申請情報</h2>
          <table>
            <tr><th>申請種別</th><td>${req.requestTypeDisplay || req.requestType}</td></tr>
            <tr><th>申請日</th><td>${format(new Date(req.requestedAt), "yyyy年MM月dd日", { locale: ja })}</td></tr>
            <tr><th>備考</th><td>${req.requestNotes || "-"}</td></tr>
          </table>
        </div>
        <div class="signature-area">
          <p>上記の通り、口座振替を依頼します。</p>
          <div class="signature-line">
            <span>届出印</span>
            <div class="stamp-box"></div>
          </div>
        </div>
      </div>
    `).join('<div class="page-break"></div>');

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>口座振替依頼書</title>
        <style>
          @media print {
            .page-break { page-break-after: always; }
          }
          body { font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif; padding: 20px; }
          .form-page { max-width: 800px; margin: 0 auto; }
          h1 { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; }
          h2 { font-size: 14px; background: #f0f0f0; padding: 5px 10px; margin-top: 20px; }
          table { width: 100%; border-collapse: collapse; }
          th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
          th { background: #f9f9f9; width: 30%; }
          .signature-area { margin-top: 40px; padding: 20px; border: 1px solid #333; }
          .signature-line { display: flex; justify-content: flex-end; align-items: center; margin-top: 20px; }
          .stamp-box { width: 60px; height: 60px; border: 1px solid #333; margin-left: 20px; }
        </style>
      </head>
      <body>
        ${forms}
      </body>
      </html>
    `;
  }

  const leftPane = (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Link href="/billing">
          <Button variant="ghost" size="sm">
            <ChevronLeft className="w-4 h-4 mr-1" />
            請求管理
          </Button>
        </Link>
      </div>

      <h2 className="text-lg font-semibold">口座申請管理</h2>

      <div className="space-y-2">
        <Label>ステータス</Label>
        <Select value={filters.status || "all"} onValueChange={handleStatusChange}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">すべて</SelectItem>
            <SelectItem value="pending">申請中</SelectItem>
            <SelectItem value="approved">承認済</SelectItem>
            <SelectItem value="rejected">却下</SelectItem>
            <SelectItem value="cancelled">取消</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>申請種別</Label>
        <Select value={filters.request_type || "all"} onValueChange={handleRequestTypeChange}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">すべて</SelectItem>
            <SelectItem value="new">新規登録</SelectItem>
            <SelectItem value="update">変更</SelectItem>
            <SelectItem value="delete">削除</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="pt-4 border-t">
        <p className="text-sm text-gray-500">
          申請中: {requests.filter((r) => r.status === "pending").length}件
        </p>
        <p className="text-sm text-gray-500">
          選択中: {selectedIds.size}件
        </p>
      </div>

      {selectedIds.size > 0 && (
        <div className="space-y-2">
          <Button
            className="w-full"
            variant="outline"
            onClick={handlePrint}
          >
            <Printer className="w-4 h-4 mr-2" />
            選択分を印刷
          </Button>
        </div>
      )}
    </div>
  );

  const mainPane = (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            placeholder="保護者名、保護者番号で検索..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="pl-10"
          />
        </div>
        <Button variant="outline" onClick={handleSearch}>
          検索
        </Button>
        <Button variant="ghost" onClick={loadRequests}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={selectedIds.size === requests.length && requests.length > 0}
                  onCheckedChange={toggleSelectAll}
                />
              </TableHead>
              <TableHead>保護者</TableHead>
              <TableHead>種別</TableHead>
              <TableHead>金融機関</TableHead>
              <TableHead>口座番号</TableHead>
              <TableHead>申請日</TableHead>
              <TableHead>ステータス</TableHead>
              <TableHead className="w-20">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8">
                  読み込み中...
                </TableCell>
              </TableRow>
            ) : requests.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-gray-500">
                  申請がありません
                </TableCell>
              </TableRow>
            ) : (
              requests.map((req) => {
                const statusCfg = statusConfig[req.status] || statusConfig.pending;
                const typeCfg = requestTypeConfig[req.requestType] || requestTypeConfig.new;
                return (
                  <TableRow key={req.id} className="cursor-pointer hover:bg-gray-50">
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={selectedIds.has(req.id)}
                        onCheckedChange={() => toggleSelect(req.id)}
                      />
                    </TableCell>
                    <TableCell onClick={() => openDetail(req)}>
                      <div className="font-medium">{req.guardianName}</div>
                      <div className="text-xs text-gray-500">{req.guardianNo}</div>
                    </TableCell>
                    <TableCell onClick={() => openDetail(req)}>
                      <Badge className={typeCfg.color}>{typeCfg.label}</Badge>
                    </TableCell>
                    <TableCell onClick={() => openDetail(req)}>
                      <div>{req.bankName}</div>
                      <div className="text-xs text-gray-500">{req.branchName}</div>
                    </TableCell>
                    <TableCell onClick={() => openDetail(req)}>
                      {req.accountNumber}
                    </TableCell>
                    <TableCell onClick={() => openDetail(req)}>
                      {format(new Date(req.requestedAt), "MM/dd HH:mm")}
                    </TableCell>
                    <TableCell onClick={() => openDetail(req)}>
                      <Badge className={statusCfg.color}>
                        {statusCfg.icon}
                        <span className="ml-1">{statusCfg.label}</span>
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" onClick={() => openDetail(req)}>
                        <Eye className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </Card>

      <div className="flex justify-between items-center text-sm text-gray-500">
        <span>全{totalCount}件</span>
      </div>
    </div>
  );

  return (
    <ThreePaneLayout>
      <div className="flex h-full">
        {/* 左パネル - フィルター */}
        {leftPane}

        {/* メインパネル */}
        <div className="flex-1">
          {mainPane}
        </div>
      </div>

      {/* 詳細ダイアログ */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>口座申請詳細</DialogTitle>
          </DialogHeader>

          {selectedRequest && (
            <div className="space-y-4">
              {/* 保護者情報 */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="font-medium mb-2">保護者情報</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">氏名:</span> {selectedRequest.guardianName}
                  </div>
                  <div>
                    <span className="text-gray-500">番号:</span> {selectedRequest.guardianNo}
                  </div>
                  <div>
                    <span className="text-gray-500">メール:</span> {selectedRequest.guardianEmail || "-"}
                  </div>
                  <div>
                    <span className="text-gray-500">電話:</span> {selectedRequest.guardianPhone || "-"}
                  </div>
                </div>
              </div>

              {/* 口座情報 */}
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <h3 className="font-medium">口座情報</h3>
                  {selectedRequest.status === "pending" && !editMode && (
                    <Button variant="outline" size="sm" onClick={() => setEditMode(true)}>
                      <Edit className="w-4 h-4 mr-1" />
                      編集
                    </Button>
                  )}
                </div>

                {editMode ? (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>金融機関名</Label>
                      <Input
                        value={editForm.bankName || ""}
                        onChange={(e) => setEditForm({ ...editForm, bankName: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>金融機関コード</Label>
                      <Input
                        value={editForm.bankCode || ""}
                        onChange={(e) => setEditForm({ ...editForm, bankCode: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>支店名</Label>
                      <Input
                        value={editForm.branchName || ""}
                        onChange={(e) => setEditForm({ ...editForm, branchName: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>支店コード</Label>
                      <Input
                        value={editForm.branchCode || ""}
                        onChange={(e) => setEditForm({ ...editForm, branchCode: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>口座番号</Label>
                      <Input
                        value={editForm.accountNumber || ""}
                        onChange={(e) => setEditForm({ ...editForm, accountNumber: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>口座種別</Label>
                      <Select
                        value={editForm.accountType || "ordinary"}
                        onValueChange={(v) => setEditForm({ ...editForm, accountType: v })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ordinary">普通</SelectItem>
                          <SelectItem value="current">当座</SelectItem>
                          <SelectItem value="savings">貯蓄</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>口座名義</Label>
                      <Input
                        value={editForm.accountHolder || ""}
                        onChange={(e) => setEditForm({ ...editForm, accountHolder: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>口座名義（カナ）</Label>
                      <Input
                        value={editForm.accountHolderKana || ""}
                        onChange={(e) => setEditForm({ ...editForm, accountHolderKana: e.target.value })}
                      />
                    </div>
                    <div className="col-span-2">
                      <Label>備考</Label>
                      <Textarea
                        value={editForm.requestNotes || ""}
                        onChange={(e) => setEditForm({ ...editForm, requestNotes: e.target.value })}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-500">金融機関:</span> {selectedRequest.bankName} ({selectedRequest.bankCode})
                    </div>
                    <div>
                      <span className="text-gray-500">支店:</span> {selectedRequest.branchName} ({selectedRequest.branchCode})
                    </div>
                    <div>
                      <span className="text-gray-500">口座種別:</span> {selectedRequest.accountTypeDisplay || selectedRequest.accountType}
                    </div>
                    <div>
                      <span className="text-gray-500">口座番号:</span> {selectedRequest.accountNumber}
                    </div>
                    <div>
                      <span className="text-gray-500">口座名義:</span> {selectedRequest.accountHolder}
                    </div>
                    <div>
                      <span className="text-gray-500">口座名義（カナ）:</span> {selectedRequest.accountHolderKana}
                    </div>
                    {selectedRequest.requestNotes && (
                      <div className="col-span-2">
                        <span className="text-gray-500">備考:</span> {selectedRequest.requestNotes}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* 申請ステータス */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="font-medium mb-2">申請状況</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">種別:</span>{" "}
                    <Badge className={requestTypeConfig[selectedRequest.requestType]?.color}>
                      {selectedRequest.requestTypeDisplay || selectedRequest.requestType}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-gray-500">ステータス:</span>{" "}
                    <Badge className={statusConfig[selectedRequest.status]?.color}>
                      {selectedRequest.statusDisplay || selectedRequest.status}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-gray-500">申請日時:</span>{" "}
                    {format(new Date(selectedRequest.requestedAt), "yyyy/MM/dd HH:mm")}
                  </div>
                  {selectedRequest.processedAt && (
                    <div>
                      <span className="text-gray-500">処理日時:</span>{" "}
                      {format(new Date(selectedRequest.processedAt), "yyyy/MM/dd HH:mm")}
                    </div>
                  )}
                  {selectedRequest.processNotes && (
                    <div className="col-span-2">
                      <span className="text-gray-500">処理メモ:</span> {selectedRequest.processNotes}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            {editMode ? (
              <>
                <Button variant="outline" onClick={() => setEditMode(false)}>
                  キャンセル
                </Button>
                <Button onClick={handleSaveEdit}>保存</Button>
              </>
            ) : selectedRequest?.status === "pending" ? (
              <>
                <Button variant="outline" onClick={() => handlePrint()}>
                  <Printer className="w-4 h-4 mr-1" />
                  印刷
                </Button>
                <Button
                  variant="outline"
                  className="text-red-600"
                  onClick={() => setRejectDialogOpen(true)}
                >
                  <XCircle className="w-4 h-4 mr-1" />
                  却下
                </Button>
                <Button onClick={handleApprove}>
                  <CheckCircle className="w-4 h-4 mr-1" />
                  承認
                </Button>
              </>
            ) : (
              <Button variant="outline" onClick={() => setDetailOpen(false)}>
                閉じる
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 却下理由ダイアログ */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>申請を却下</DialogTitle>
            <DialogDescription>却下理由を入力してください（任意）</DialogDescription>
          </DialogHeader>
          <Textarea
            placeholder="却下理由..."
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialogOpen(false)}>
              キャンセル
            </Button>
            <Button variant="destructive" onClick={handleReject}>
              却下する
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </ThreePaneLayout>
  );
}
