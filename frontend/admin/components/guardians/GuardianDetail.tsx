"use client";

import { useState, useMemo, useEffect } from "react";
import { Guardian, Student, Invoice } from "@/lib/api/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import {
  User, Mail, Phone, MapPin, Building, CreditCard, Banknote,
  GraduationCap, Receipt, MessageSquare, Edit, ChevronDown, ChevronUp, Gift,
  AlertTriangle, CheckCircle, Wallet, Calendar, Filter, ExternalLink, MessageCircle,
  BookOpen, ArrowUpCircle, ArrowDownCircle
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { getOrCreateChannelForGuardian } from "@/lib/api/chat";
import type { ContactLog, ChatMessage, PassbookTransaction, PassbookData } from "@/lib/api/staff";
import { getGuardianPassbook } from "@/lib/api/staff";

// Enrollment info type
interface EnrollmentInfo {
  key: string;
  brandName: string;
  brandCode: string;
  dayOfWeek: number;
  dayDisplay: string;
  startTime: string;
  className: string;
  schoolName: string;
}

// Invoice history type
interface InvoiceHistory {
  id: string;
  invoiceNo: string;
  billingYear: number;
  billingMonth: number;
  billingLabel: string;
  totalAmount: number;
  paidAmount: number;
  balanceDue: number;
  status: string;
  statusDisplay: string;
  paymentMethod: string;
  paidAt: string | null;
  dueDate: string | null;
  issuedAt: string | null;
}

// Payment history type
interface PaymentHistory {
  id: string;
  paymentDate: string | null;
  amount: number;
  paymentMethod: string;
  paymentMethodDisplay: string;
  status: string;
  notes: string;
}

// Billing summary type
interface BillingSummary {
  guardianId: string;
  guardianName: string;
  children: {
    studentId: string;
    studentName: string;
    studentNo: string;
    status: string;
    gradeText: string;
    items: {
      id: string;
      productName: string;
      brandName: string;
      schoolName: string;
      billingMonth: string;
      unitPrice: number;
      discountAmount: number;
      finalPrice: number;
    }[];
    discounts: {
      id: string;
      discountName: string;
      amount: number;
      discountUnit: string;
      brandName: string;
      startDate: string | null;
      endDate: string | null;
    }[];
    enrollments?: EnrollmentInfo[];
    subtotal: number;
  }[];
  // 残高情報
  accountBalance?: number;
  accountBalanceLabel?: string;
  // 請求・入金履歴
  invoiceHistory?: InvoiceHistory[];
  paymentHistory?: PaymentHistory[];
  guardianDiscounts: {
    id: string;
    discountName: string;
    amount: number;
    discountUnit: string;
    brandName: string;
    startDate: string | null;
    endDate: string | null;
  }[];
  fsDiscounts: {
    id: string;
    discountType: string;
    discountTypeDisplay: string;
    discountValue: number;
    status: string;
    validFrom: string | null;
    validUntil: string | null;
  }[];
  totalAmount: number;
  totalDiscount: number;
  netAmount: number;
  // Payment info
  paymentMethod?: string;
  paymentMethodDisplay?: string;
  isOverdue?: boolean;
  overdueCount?: number;
  unpaidAmount?: number;
  // Bank account
  bankAccount?: {
    bankName: string;
    bankCode: string;
    branchName: string;
    branchCode: string;
    accountType: string;
    accountTypeDisplay: string;
    accountNumber: string;
    accountHolder: string;
    accountHolderKana: string;
    isRegistered: boolean;
    withdrawalDay: number | null;
  };
}

interface GuardianDetailProps {
  guardian: Guardian;
  children: Student[];
  invoices: Invoice[];
  contactLogs: ContactLog[];
  messages: ChatMessage[];
  billingSummary?: BillingSummary | null;
  onSelectChild?: (studentId: string) => void;
  onEditChild?: (studentId: string) => void;
}

// Helper to get guardian display name
function getGuardianName(guardian: Guardian): string {
  if (guardian.full_name) return guardian.full_name;
  if (guardian.fullName) return guardian.fullName;
  const lastName = guardian.last_name || guardian.lastName || "";
  const firstName = guardian.first_name || guardian.firstName || "";
  if (lastName || firstName) {
    return `${lastName}${firstName}`;
  }
  return "(名前未設定)";
}

// Helper to get guardian kana name
function getGuardianNameKana(guardian: Guardian): string {
  const lastNameKana = guardian.last_name_kana || guardian.lastNameKana || "";
  const firstNameKana = guardian.first_name_kana || guardian.firstNameKana || "";
  if (lastNameKana || firstNameKana) {
    return `${lastNameKana}${firstNameKana}`;
  }
  return "";
}

// ステータスの日本語変換
function getStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    registered: "登録済",
    enrolled: "在籍",
    suspended: "休会",
    withdrawn: "退会",
    graduated: "卒業",
  };
  return statusMap[status] || status;
}

function getStatusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  if (status === "enrolled") return "default";
  if (status === "suspended") return "secondary";
  if (status === "withdrawn" || status === "graduated") return "outline";
  return "secondary";
}

export function GuardianDetail({
  guardian,
  children,
  invoices,
  contactLogs,
  messages,
  billingSummary,
  onSelectChild,
  onEditChild
}: GuardianDetailProps) {
  const name = getGuardianName(guardian);
  const nameKana = getGuardianNameKana(guardian);
  const guardianNo = guardian.guardian_no || guardian.guardianNo || "";

  // Expanded state for each child in billing
  const [expandedChildren, setExpandedChildren] = useState<Record<string, boolean>>({});

  // History tab state
  const [historyTab, setHistoryTab] = useState<"logs" | "chat">("logs");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  // 通帳モーダル state
  const [isPassbookOpen, setIsPassbookOpen] = useState(false);
  const [passbookData, setPassbookData] = useState<PassbookData | null>(null);
  const [isLoadingPassbook, setIsLoadingPassbook] = useState(false);

  // 通帳を開く
  const openPassbook = async () => {
    setIsPassbookOpen(true);
    if (!passbookData) {
      setIsLoadingPassbook(true);
      try {
        const data = await getGuardianPassbook(guardian.id);
        setPassbookData(data);
      } catch (error) {
        console.error("Failed to load passbook:", error);
      } finally {
        setIsLoadingPassbook(false);
      }
    }
  };

  const toggleChildExpand = (studentId: string) => {
    setExpandedChildren(prev => ({
      ...prev,
      [studentId]: !prev[studentId]
    }));
  };

  // 日付でフィルタリングされた対応ログ
  const filteredContactLogs = useMemo(() => {
    return contactLogs.filter((log) => {
      const logDate = new Date(log.created_at);
      if (dateFrom && logDate < new Date(dateFrom)) return false;
      if (dateTo && logDate > new Date(dateTo + "T23:59:59")) return false;
      return true;
    });
  }, [contactLogs, dateFrom, dateTo]);

  // 日付でフィルタリングされたメッセージ
  const filteredMessages = useMemo(() => {
    return messages.filter((msg) => {
      const msgDate = new Date(msg.created_at);
      if (dateFrom && msgDate < new Date(dateFrom)) return false;
      if (dateTo && msgDate > new Date(dateTo + "T23:59:59")) return false;
      return true;
    });
  }, [messages, dateFrom, dateTo]);

  // 日付フィルターをクリア
  const clearDateFilter = () => {
    setDateFrom("");
    setDateTo("");
  };

  // チャット開始中フラグ
  const [isStartingChat, setIsStartingChat] = useState(false);

  // アカウント作成中フラグ
  const [isCreatingAccount, setIsCreatingAccount] = useState(false);
  const [accountCreated, setAccountCreated] = useState(false);

  // アカウント作成してすぐに保護者画面を開く
  const setupAccountAndOpen = async () => {
    if (!guardian.email) {
      alert('メールアドレスが設定されていません。先にメールアドレスを登録してください。');
      return;
    }

    setIsCreatingAccount(true);
    try {
      // アカウント作成
      await apiClient.post(`/students/guardians/${guardian.id}/setup_account/`);
      setAccountCreated(true);

      // 作成後すぐに保護者画面を開く
      const response = await apiClient.post<{ access: string; refresh: string }>('/auth/impersonate-guardian/', {
        guardian_id: guardian.id
      });
      const customerUrl = process.env.NEXT_PUBLIC_CUSTOMER_URL || 'http://localhost:3000';
      const url = `${customerUrl}/auth/callback?access=${response.access}&refresh=${response.refresh}`;
      window.open(url, '_blank');

    } catch (error: any) {
      const errorMessage = error.data?.error || error.message || '';
      alert(errorMessage || 'アカウント作成に失敗しました。');
    } finally {
      setIsCreatingAccount(false);
    }
  };

  // 保護者画面を開く（アカウントがなければ自動作成）
  const openGuardianView = async () => {
    // アカウント未設定の場合は自動作成
    if (!guardian.has_account && !guardian.hasAccount && !accountCreated) {
      // 電話番号またはメールが必要
      const hasContactInfo = guardian.email || guardian.phone || guardian.phone_mobile || guardian.phoneMobile;
      if (!hasContactInfo) {
        alert('電話番号またはメールアドレスが設定されていません。');
        return;
      }

      try {
        // アカウントを自動作成
        await apiClient.post(`/students/guardians/${guardian.id}/setup_account/`);
        setAccountCreated(true);
      } catch (error: any) {
        const errorMessage = error.data?.error || error.message || '';
        alert(errorMessage || 'アカウント作成に失敗しました。');
        return;
      }
    }

    try {
      const response = await apiClient.post<{ access: string; refresh: string }>('/auth/impersonate-guardian/', {
        guardian_id: guardian.id
      });
      // 保護者画面を新しいタブで開く
      const customerUrl = process.env.NEXT_PUBLIC_CUSTOMER_URL || 'http://localhost:3000';
      const url = `${customerUrl}/auth/callback?access=${response.access}&refresh=${response.refresh}`;
      window.open(url, '_blank');
    } catch (error: any) {
      console.error('Failed to impersonate guardian:', error);
      const errorMessage = error.data?.error || error.message || '';
      alert(errorMessage || '保護者画面を開けませんでした。');
    }
  };

  // チャットを開始
  const startChat = async () => {
    setIsStartingChat(true);
    try {
      const channel = await getOrCreateChannelForGuardian(guardian.id);
      // チャットページを新しいタブで開く
      window.open(`/messages?channel=${channel.id}&guardian=${guardian.id}`, '_blank');
    } catch (error: any) {
      console.error('Failed to start chat:', error);
      alert(error.message || 'チャットを開始できませんでした');
    } finally {
      setIsStartingChat(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="p-4 bg-purple-100 rounded-xl">
            <User className="w-8 h-8 text-purple-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{name}</h2>
            {nameKana && <p className="text-sm text-gray-500">{nameKana}</p>}
            {guardianNo && <p className="text-xs text-gray-400">保護者番号: {guardianNo}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* チャットを開始ボタン */}
          <Button
            variant="default"
            size="sm"
            onClick={startChat}
            disabled={isStartingChat}
            className="flex items-center gap-1 bg-blue-600 hover:bg-blue-700"
          >
            <MessageCircle className="w-4 h-4" />
            {isStartingChat ? '開始中...' : 'チャット'}
          </Button>

          {/* アカウント作成ボタン（アカウント未設定の場合のみ表示） */}
          {!guardian.has_account && !guardian.hasAccount && !accountCreated && (
            <Button
              variant="outline"
              size="sm"
              onClick={setupAccountAndOpen}
              disabled={isCreatingAccount}
              className="flex items-center gap-1 border-green-500 text-green-600 hover:bg-green-50"
            >
              <User className="w-4 h-4" />
              {isCreatingAccount ? '作成中...' : 'アカウント作成'}
            </Button>
          )}

          {/* 保護者画面を開くボタン */}
          <Button
            variant="outline"
            size="sm"
            onClick={openGuardianView}
            className="flex items-center gap-1"
          >
            <ExternalLink className="w-4 h-4" />
            保護者画面を開く
          </Button>
        </div>
      </div>

      <Tabs defaultValue="children" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="children">お子様 ({children.length})</TabsTrigger>
          <TabsTrigger value="billing">請求</TabsTrigger>
          <TabsTrigger value="info">基本情報</TabsTrigger>
          <TabsTrigger value="history">対応履歴</TabsTrigger>
        </TabsList>

        {/* Children Tab */}
        <TabsContent value="children" className="space-y-2">
          {children.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <GraduationCap className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>お子様の情報がありません</p>
            </div>
          ) : (
            children.map((child) => {
              const lastName = child.lastName || child.last_name || "";
              const firstName = child.firstName || child.first_name || "";
              const childName = child.fullName || child.full_name || `${lastName}${firstName}`;
              const gradeText = child.gradeText || child.grade_text || child.gradeName || "";
              const studentNo = child.studentNo || child.student_no || "";

              // 在籍情報をbillingSummaryから取得
              const childBilling = billingSummary?.children.find(c => c.studentId === child.id);
              const enrollments = childBilling?.enrollments || [];

              return (
                <Card key={child.id} className="overflow-hidden">
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div
                        className={cn("flex-1 cursor-pointer", onSelectChild && "hover:text-blue-600")}
                        onClick={() => onSelectChild?.(child.id)}
                      >
                        <p className="font-medium">{childName || "名前未設定"}</p>
                        <p className="text-xs text-gray-500">
                          {studentNo && `No.${studentNo}`}
                          {gradeText && ` / ${gradeText}`}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={getStatusVariant(child.status)}>
                          {getStatusLabel(child.status)}
                        </Badge>
                        {onEditChild && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onEditChild(child.id);
                            }}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                    {/* 在籍情報（ブランド・曜日・時間） */}
                    {enrollments.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <p className="text-xs text-gray-400 mb-1">在籍クラス</p>
                        <div className="flex flex-wrap gap-1">
                          {enrollments.map((enrollment) => (
                            <Badge
                              key={enrollment.key}
                              variant="outline"
                              className="text-xs font-normal"
                            >
                              {enrollment.brandName}
                              {enrollment.dayDisplay && ` ${enrollment.dayDisplay}曜`}
                              {enrollment.startTime && ` ${enrollment.startTime}`}
                              {enrollment.className && ` (${enrollment.className})`}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })
          )}
        </TabsContent>

        {/* Billing Tab */}
        <TabsContent value="billing" className="space-y-4">
          {billingSummary ? (
            <>
              {/* Account Balance Card - 残高表示 */}
              {billingSummary.accountBalance !== undefined && billingSummary.accountBalance !== 0 && (
                <Card className={cn(
                  billingSummary.accountBalance < 0
                    ? "bg-gradient-to-r from-blue-100 to-blue-50 border-blue-300"
                    : "bg-gradient-to-r from-red-100 to-orange-50 border-red-300"
                )}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Receipt className="w-5 h-5" />
                        <span className="font-medium">口座残高</span>
                      </div>
                      <div className="text-right">
                        <Badge className={cn(
                          "text-sm",
                          billingSummary.accountBalance < 0 ? "bg-blue-600" : "bg-red-600"
                        )}>
                          {billingSummary.accountBalanceLabel}
                        </Badge>
                        <p className={cn(
                          "text-2xl font-bold mt-1",
                          billingSummary.accountBalance < 0 ? "text-blue-700" : "text-red-700"
                        )}>
                          {billingSummary.accountBalance < 0 ? "+" : "-"}¥{Math.abs(billingSummary.accountBalance).toLocaleString()}
                        </p>
                        <p className="text-xs text-gray-500">
                          {billingSummary.accountBalance < 0
                            ? "次回請求から差し引かれます"
                            : "未払い残高があります"}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Payment Status Card */}
              <Card className={cn(
                billingSummary.isOverdue
                  ? "bg-gradient-to-r from-red-50 to-orange-50 border-red-200"
                  : "bg-gradient-to-r from-green-50 to-blue-50"
              )}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Wallet className="w-5 h-5" />
                      <span className="font-medium">支払い方法: {billingSummary.paymentMethodDisplay || "口座引落"}</span>
                    </div>
                    {billingSummary.isOverdue ? (
                      <Badge variant="destructive" className="flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        滞納あり ({billingSummary.overdueCount}件)
                      </Badge>
                    ) : (
                      <Badge variant="default" className="flex items-center gap-1 bg-green-600">
                        <CheckCircle className="w-3 h-3" />
                        正常
                      </Badge>
                    )}
                  </div>
                  {billingSummary.unpaidAmount && billingSummary.unpaidAmount > 0 && (
                    <p className="text-sm text-orange-600 mb-2">
                      未入金額: ¥{billingSummary.unpaidAmount.toLocaleString()}
                    </p>
                  )}
                  <div className="grid grid-cols-3 gap-4 text-center pt-2 border-t">
                    <div>
                      <p className="text-xs text-gray-500">月額合計</p>
                      <p className="text-lg font-bold">¥{billingSummary.totalAmount.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">割引合計</p>
                      <p className="text-lg font-bold text-red-600">-¥{billingSummary.totalDiscount.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">請求額</p>
                      <p className="text-xl font-bold text-blue-600">¥{billingSummary.netAmount.toLocaleString()}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Bank Account Card */}
              {billingSummary.bankAccount && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Banknote className="w-4 h-4" />
                      引落口座
                      {billingSummary.bankAccount.isRegistered ? (
                        <Badge variant="outline" className="text-xs text-green-600 border-green-300">登録済</Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs text-orange-600 border-orange-300">未登録</Badge>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm space-y-1">
                    {billingSummary.bankAccount.bankName ? (
                      <>
                        <p className="font-medium">
                          {billingSummary.bankAccount.bankName}
                          {billingSummary.bankAccount.bankCode && ` (${billingSummary.bankAccount.bankCode})`}
                        </p>
                        <p>
                          {billingSummary.bankAccount.branchName}支店
                          {billingSummary.bankAccount.branchCode && ` (${billingSummary.bankAccount.branchCode})`}
                        </p>
                        <p className="text-gray-600">
                          {billingSummary.bankAccount.accountTypeDisplay}
                          {billingSummary.bankAccount.accountNumber}
                        </p>
                        <p className="text-gray-600">
                          名義: {billingSummary.bankAccount.accountHolder}
                          {billingSummary.bankAccount.accountHolderKana && ` (${billingSummary.bankAccount.accountHolderKana})`}
                        </p>
                        {billingSummary.bankAccount.withdrawalDay && (
                          <p className="text-gray-500 text-xs">
                            引落日: 毎月{billingSummary.bankAccount.withdrawalDay}日
                          </p>
                        )}
                      </>
                    ) : (
                      <p className="text-gray-400">口座情報未登録</p>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Passbook Button */}
              <Card className="bg-gradient-to-r from-indigo-50 to-purple-50 border-indigo-200 hover:shadow-md transition-shadow cursor-pointer" onClick={openPassbook}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-indigo-100 rounded-lg">
                        <BookOpen className="w-5 h-5 text-indigo-600" />
                      </div>
                      <div>
                        <p className="font-medium text-indigo-900">入出金履歴（通帳）</p>
                        <p className="text-xs text-indigo-600">預り金残高・取引履歴を確認</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {billingSummary.accountBalance !== undefined && (
                        <Badge className={cn(
                          "text-sm",
                          billingSummary.accountBalance < 0 ? "bg-blue-600" : billingSummary.accountBalance > 0 ? "bg-orange-600" : "bg-gray-400"
                        )}>
                          残高: {billingSummary.accountBalance < 0 ? '+' : ''}{Math.abs(billingSummary.accountBalance || 0).toLocaleString()}円
                        </Badge>
                      )}
                      <ChevronDown className="w-5 h-5 text-indigo-400" />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Children billing breakdown */}
              {billingSummary.children.map((child) => (
                <Card key={child.studentId}>
                  <CardHeader
                    className="pb-2 cursor-pointer"
                    onClick={() => toggleChildExpand(child.studentId)}
                  >
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <GraduationCap className="w-4 h-4" />
                        {child.studentName}
                        <Badge variant="outline" className="text-xs">{child.gradeText}</Badge>
                      </CardTitle>
                      <div className="flex items-center gap-2">
                        <span className="font-bold">¥{child.subtotal.toLocaleString()}</span>
                        {expandedChildren[child.studentId] ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  {expandedChildren[child.studentId] && (
                    <CardContent className="pt-0 space-y-2">
                      {/* Items */}
                      {child.items.length > 0 && (
                        <div className="space-y-1">
                          {child.items.map((item) => (
                            <div key={item.id} className="flex justify-between text-sm py-1 border-b border-gray-100">
                              <div>
                                <span>{item.productName}</span>
                                {item.brandName && (
                                  <span className="text-xs text-gray-400 ml-1">({item.brandName})</span>
                                )}
                              </div>
                              <div className="text-right">
                                {item.discountAmount > 0 ? (
                                  <>
                                    <span className="line-through text-gray-400 text-xs mr-1">
                                      ¥{item.unitPrice.toLocaleString()}
                                    </span>
                                    <span className="font-medium">¥{item.finalPrice.toLocaleString()}</span>
                                  </>
                                ) : (
                                  <span className="font-medium">¥{item.finalPrice.toLocaleString()}</span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      {/* Child discounts */}
                      {child.discounts.length > 0 && (
                        <div className="pt-2 space-y-1">
                          <p className="text-xs text-gray-500 font-medium">適用中の割引</p>
                          {child.discounts.map((disc) => (
                            <div key={disc.id} className="flex justify-between text-sm text-green-600">
                              <span>{disc.discountName}</span>
                              <span>
                                {disc.discountUnit === "percent" ? `${disc.amount}%OFF` : `-¥${Math.abs(disc.amount).toLocaleString()}`}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                      {child.items.length === 0 && child.discounts.length === 0 && (
                        <p className="text-sm text-gray-400">料金情報がありません</p>
                      )}
                    </CardContent>
                  )}
                </Card>
              ))}

              {/* Guardian-level discounts */}
              {(billingSummary.guardianDiscounts.length > 0 || billingSummary.fsDiscounts.length > 0) && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Gift className="w-4 h-4" />
                      家族割引・特典
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {/* Guardian discounts (sibling discount etc) */}
                    {billingSummary.guardianDiscounts.map((disc) => (
                      <div key={disc.id} className="flex justify-between text-sm">
                        <span>{disc.discountName}</span>
                        <span className="text-green-600">
                          {disc.discountUnit === "percent" ? `${disc.amount}%OFF` : `-¥${Math.abs(disc.amount).toLocaleString()}`}
                        </span>
                      </div>
                    ))}
                    {/* FS discounts (friendship) */}
                    {billingSummary.fsDiscounts.map((fs) => (
                      <div key={fs.id} className="flex justify-between text-sm">
                        <span>フレンドシップ割引 ({fs.discountTypeDisplay})</span>
                        <span className="text-green-600">
                          {fs.discountType === "percentage" ? `${fs.discountValue}%OFF` :
                           fs.discountType === "months_free" ? `${fs.discountValue}ヶ月無料` :
                           `-¥${fs.discountValue.toLocaleString()}`}
                        </span>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {/* Invoice History - 請求履歴 */}
              {billingSummary.invoiceHistory && billingSummary.invoiceHistory.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Receipt className="w-4 h-4" />
                      請求・入金履歴
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-3 py-2 text-left">請求月</th>
                            <th className="px-3 py-2 text-right">請求額</th>
                            <th className="px-3 py-2 text-right">入金額</th>
                            <th className="px-3 py-2 text-right">残高</th>
                            <th className="px-3 py-2 text-center">状態</th>
                          </tr>
                        </thead>
                        <tbody>
                          {billingSummary.invoiceHistory.map((inv) => {
                            const balanceColor = inv.balanceDue === 0
                              ? "text-green-600"
                              : inv.balanceDue < 0
                              ? "text-blue-600"
                              : "text-red-600";
                            const statusColor = inv.status === "paid"
                              ? "bg-green-100 text-green-700"
                              : inv.status === "overdue"
                              ? "bg-red-100 text-red-700"
                              : inv.status === "partial"
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-gray-100 text-gray-700";

                            return (
                              <tr key={inv.id} className="border-t hover:bg-gray-50">
                                <td className="px-3 py-2 font-medium">{inv.billingLabel}</td>
                                <td className="px-3 py-2 text-right">¥{inv.totalAmount.toLocaleString()}</td>
                                <td className="px-3 py-2 text-right">
                                  {inv.paidAmount > 0 ? (
                                    <span className="text-green-600">¥{inv.paidAmount.toLocaleString()}</span>
                                  ) : (
                                    <span className="text-gray-400">-</span>
                                  )}
                                </td>
                                <td className={cn("px-3 py-2 text-right font-medium", balanceColor)}>
                                  {inv.balanceDue === 0
                                    ? "精算済"
                                    : inv.balanceDue < 0
                                    ? `+¥${Math.abs(inv.balanceDue).toLocaleString()}`
                                    : `¥${inv.balanceDue.toLocaleString()}`}
                                </td>
                                <td className="px-3 py-2 text-center">
                                  <Badge className={cn("text-xs", statusColor)}>
                                    {inv.statusDisplay}
                                  </Badge>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <div className="text-center text-gray-500 py-8">
              <Receipt className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>請求情報を読み込み中...</p>
            </div>
          )}
        </TabsContent>

        {/* Basic Info Tab */}
        <TabsContent value="info" className="space-y-4">
          {/* Contact Info */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Phone className="w-4 h-4" />
                連絡先
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {guardian.email && (
                <div className="flex items-center gap-2">
                  <Mail className="w-4 h-4 text-gray-400" />
                  <a href={`mailto:${guardian.email}`} className="text-blue-600 hover:underline">
                    {guardian.email}
                  </a>
                </div>
              )}
              {guardian.phone && (
                <div className="flex items-center gap-2">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <span>{guardian.phone}</span>
                </div>
              )}
              {(guardian.phone_mobile || guardian.phoneMobile) && (
                <div className="flex items-center gap-2">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <span>{guardian.phone_mobile || guardian.phoneMobile} (携帯)</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Address */}
          {(guardian.postal_code || guardian.postalCode || guardian.prefecture || guardian.city || guardian.address1) && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  住所
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                {(guardian.postal_code || guardian.postalCode) && (
                  <p className="text-gray-500">〒{guardian.postal_code || guardian.postalCode}</p>
                )}
                <p>
                  {guardian.prefecture}
                  {guardian.city}
                  {guardian.address1}
                  {guardian.address2 && ` ${guardian.address2}`}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Workplace */}
          {(guardian.workplace || guardian.workplace_phone) && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Building className="w-4 h-4" />
                  勤務先
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                {guardian.workplace && <p>{guardian.workplace}</p>}
                {guardian.workplace_phone && (
                  <p className="text-gray-500">TEL: {guardian.workplace_phone}</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Bank Info */}
          {(guardian.bank_name || guardian.bankName) && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <CreditCard className="w-4 h-4" />
                  引落口座
                  {(guardian.payment_registered || guardian.paymentRegistered) ? (
                    <Badge variant="outline" className="text-xs text-green-600 border-green-300">登録済</Badge>
                  ) : (
                    <Badge variant="outline" className="text-xs text-orange-600 border-orange-300">未登録</Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-3">
                {/* 金融機関 */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-xs text-gray-400">金融機関</p>
                    <p className="font-medium">{guardian.bank_name || guardian.bankName}</p>
                    {(guardian.bank_code || guardian.bankCode) && (
                      <p className="text-xs text-gray-500">コード: {guardian.bank_code || guardian.bankCode}</p>
                    )}
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">支店</p>
                    <p className="font-medium">{guardian.branch_name || guardian.branchName}</p>
                    {(guardian.branch_code || guardian.branchCode) && (
                      <p className="text-xs text-gray-500">コード: {guardian.branch_code || guardian.branchCode}</p>
                    )}
                  </div>
                </div>
                {/* 口座情報 */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-xs text-gray-400">口座種別</p>
                    <p className="font-medium">
                      {(() => {
                        const accountType = guardian.account_type || guardian.accountType;
                        if (accountType === 'ordinary') return '普通';
                        if (accountType === 'current') return '当座';
                        if (accountType === 'savings') return '貯蓄';
                        return accountType || '-';
                      })()}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">口座番号</p>
                    <p className="font-medium">
                      {(() => {
                        const accNum = guardian.account_number || guardian.accountNumber;
                        if (!accNum) return '-';
                        // マスク処理: 下4桁以外を*に
                        if (accNum.length > 4) {
                          return '*'.repeat(accNum.length - 4) + accNum.slice(-4);
                        }
                        return accNum;
                      })()}
                    </p>
                  </div>
                </div>
                {/* 名義 */}
                <div>
                  <p className="text-xs text-gray-400">口座名義</p>
                  <p className="font-medium">{guardian.account_holder || guardian.accountHolder || '-'}</p>
                  {(guardian.account_holder_kana || guardian.accountHolderKana) && (
                    <p className="text-xs text-gray-500">
                      {guardian.account_holder_kana || guardian.accountHolderKana}
                    </p>
                  )}
                </div>
                {/* 登録日時 */}
                {(guardian.payment_registered_at || guardian.paymentRegisteredAt) && (
                  <div className="pt-2 border-t border-gray-100">
                    <p className="text-xs text-gray-400">
                      登録日時: {(() => {
                        const dateStr = guardian.payment_registered_at || guardian.paymentRegisteredAt;
                        return dateStr ? new Date(dateStr).toLocaleString('ja-JP') : '-';
                      })()}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-4">
          {/* 日付範囲フィルター */}
          <Card className="bg-gray-50">
            <CardContent className="p-3">
              <div className="flex items-center gap-2 flex-wrap">
                <Calendar className="w-4 h-4 text-gray-500" />
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-36 h-8 text-sm"
                  placeholder="開始日"
                />
                <span className="text-gray-400">〜</span>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-36 h-8 text-sm"
                  placeholder="終了日"
                />
                {(dateFrom || dateTo) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearDateFilter}
                    className="h-8 text-xs"
                  >
                    クリア
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* サブタブ切り替え */}
          <div className="flex gap-1 border-b">
            <button
              className={cn(
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                historyTab === "logs"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              )}
              onClick={() => setHistoryTab("logs")}
            >
              対応ログ ({filteredContactLogs.length})
            </button>
            <button
              className={cn(
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                historyTab === "chat"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              )}
              onClick={() => setHistoryTab("chat")}
            >
              チャット ({filteredMessages.length})
            </button>
          </div>

          {/* 対応ログ一覧 */}
          {historyTab === "logs" && (
            <div className="space-y-2">
              {filteredContactLogs.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                  <p>
                    {contactLogs.length === 0
                      ? "対応ログがありません"
                      : "該当する期間の対応ログがありません"}
                  </p>
                </div>
              ) : (
                filteredContactLogs.map((log) => (
                  <Card key={log.id}>
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between mb-1">
                        <Badge variant="outline" className="text-xs">
                          {log.contact_type_display || log.contact_type}
                        </Badge>
                        <span className="text-xs text-gray-400">
                          {log.created_at ? new Date(log.created_at).toLocaleDateString("ja-JP") : "-"}
                        </span>
                      </div>
                      <p className="text-sm font-medium">{log.subject}</p>
                      <p className="text-xs text-gray-500 whitespace-pre-wrap">{log.content}</p>
                      {log.handled_by_name && (
                        <p className="text-xs text-gray-400 mt-1">担当: {log.handled_by_name}</p>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* チャット一覧 */}
          {historyTab === "chat" && (
            <div className="space-y-2">
              {filteredMessages.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                  <p>
                    {messages.length === 0
                      ? "チャット履歴がありません"
                      : "該当する期間のチャットがありません"}
                  </p>
                </div>
              ) : (
                filteredMessages.map((msg) => {
                  const isStaffMessage = !!msg.sender_id && !msg.sender_guardian_id;
                  return (
                  <Card key={msg.id} className={cn(
                    isStaffMessage ? "border-l-4 border-l-blue-400" : "border-l-4 border-l-green-400"
                  )}>
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-xs",
                              isStaffMessage ? "bg-blue-50" : "bg-green-50"
                            )}
                          >
                            {isStaffMessage ? "スタッフ" : "保護者"}
                          </Badge>
                          <span className="text-xs text-gray-500">
                            {msg.sender_name || msg.sender_guardian_name || "不明"}
                          </span>
                        </div>
                        <span className="text-xs text-gray-400">
                          {msg.created_at ? new Date(msg.created_at).toLocaleString("ja-JP", {
                            month: "numeric",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit"
                          }) : "-"}
                        </span>
                      </div>
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    </CardContent>
                  </Card>
                  );
                })
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* 通帳モーダル */}
      <Dialog open={isPassbookOpen} onOpenChange={setIsPassbookOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-indigo-600" />
              入出金履歴（通帳）
            </DialogTitle>
          </DialogHeader>

          {isLoadingPassbook ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : passbookData ? (
            <div className="space-y-4">
              {/* 残高サマリ */}
              <div className={cn(
                "p-4 rounded-lg",
                passbookData.current_balance < 0
                  ? "bg-blue-50 border border-blue-200"
                  : passbookData.current_balance > 0
                  ? "bg-orange-50 border border-orange-200"
                  : "bg-gray-50 border border-gray-200"
              )}>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">現在の預り金残高</span>
                  <span className={cn(
                    "text-2xl font-bold",
                    passbookData.current_balance < 0
                      ? "text-blue-600"
                      : passbookData.current_balance > 0
                      ? "text-orange-600"
                      : "text-gray-600"
                  )}>
                    {passbookData.current_balance < 0 ? '+' : ''}
                    ¥{Math.abs(passbookData.current_balance).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {passbookData.current_balance < 0
                    ? "※ 次回請求から差し引かれます"
                    : passbookData.current_balance > 0
                    ? "※ 未払い残高があります"
                    : "※ 残高はありません"}
                </p>
              </div>

              {/* 取引履歴 */}
              <div className="space-y-2">
                <h4 className="font-medium text-sm text-gray-700">取引履歴</h4>
                {passbookData.transactions.length === 0 ? (
                  <p className="text-center text-gray-400 py-8">取引履歴がありません</p>
                ) : (
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-3 py-2 text-left">日時</th>
                          <th className="px-3 py-2 text-left">内容</th>
                          <th className="px-3 py-2 text-right">金額</th>
                          <th className="px-3 py-2 text-right">残高</th>
                        </tr>
                      </thead>
                      <tbody>
                        {passbookData.transactions.map((tx) => {
                          const isDeposit = tx.amount > 0;
                          const dateStr = tx.created_at || tx.createdAt;
                          const description = tx.transaction_type_display || tx.transactionTypeDisplay || tx.transaction_type;
                          const invoiceLabel = tx.invoice_billing_label || tx.invoiceBillingLabel;

                          return (
                            <tr key={tx.id} className="border-t hover:bg-gray-50">
                              <td className="px-3 py-2 text-gray-500">
                                {dateStr ? new Date(dateStr).toLocaleDateString('ja-JP', {
                                  year: 'numeric',
                                  month: 'numeric',
                                  day: 'numeric'
                                }) : "-"}
                              </td>
                              <td className="px-3 py-2">
                                <div className="flex items-center gap-2">
                                  {isDeposit ? (
                                    <ArrowDownCircle className="w-4 h-4 text-blue-500" />
                                  ) : (
                                    <ArrowUpCircle className="w-4 h-4 text-orange-500" />
                                  )}
                                  <span>{description}</span>
                                  {invoiceLabel && (
                                    <span className="text-xs text-gray-400">({invoiceLabel})</span>
                                  )}
                                </div>
                                {tx.reason && (
                                  <p className="text-xs text-gray-400 mt-0.5 ml-6">{tx.reason}</p>
                                )}
                              </td>
                              <td className={cn(
                                "px-3 py-2 text-right font-medium",
                                isDeposit ? "text-blue-600" : "text-orange-600"
                              )}>
                                {isDeposit ? '+' : ''}¥{Math.abs(tx.amount).toLocaleString()}
                              </td>
                              <td className="px-3 py-2 text-right">
                                ¥{(tx.balance_after || tx.balanceAfter || 0).toLocaleString()}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <p className="text-center text-gray-400 py-8">データを取得できませんでした</p>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
