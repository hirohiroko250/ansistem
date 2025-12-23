"use client";

import { useState, useMemo, useEffect } from "react";
import { Student, Guardian, Contract, Invoice, StudentDiscount } from "@/lib/api/types";
import { ContactLog, ChatLog, ChatMessage } from "@/lib/api/staff";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Phone,
  Edit,
  MessageCircle,
  FileText,
  CreditCard,
  PauseCircle,
  XCircle,
  User,
  Mail,
  MapPin,
  History,
  Users,
  Calendar,
  Pencil,
  ExternalLink,
} from "lucide-react";
import { ContractEditDialog } from "./ContractEditDialog";
import { NewContractDialog } from "./NewContractDialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import apiClient from "@/lib/api/client";

interface ContractUpdate {
  discounts?: {
    id?: string;
    discount_name: string;
    amount: number;
    discount_unit: "yen" | "percent";
    is_new?: boolean;
    is_deleted?: boolean;
  }[];
  notes?: string;
}

interface StudentDetailProps {
  student: Student;
  parents: Guardian[];
  contracts: Contract[];
  invoices: Invoice[];
  contactLogs?: ContactLog[];
  chatLogs?: ChatLog[];
  messages?: ChatMessage[];
  siblings?: Student[];
  onSelectSibling?: (studentId: string) => void;
  onContractUpdate?: (contractId: string, updates: ContractUpdate) => Promise<void>;
}

function getStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    registered: "登録済",
    enrolled: "在籍中",
    suspended: "休会中",
    withdrawn: "退会",
    graduated: "卒業",
  };
  return statusMap[status] || status;
}

function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    registered: "bg-yellow-100 text-yellow-800",
    enrolled: "bg-green-100 text-green-800",
    suspended: "bg-orange-100 text-orange-800",
    withdrawn: "bg-gray-100 text-gray-800",
    graduated: "bg-blue-100 text-blue-800",
  };
  return colorMap[status] || "bg-gray-100 text-gray-800";
}

function getContractStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    active: "有効",
    pending: "保留",
    cancelled: "解約",
    expired: "期限切れ",
  };
  return statusMap[status] || status;
}

function getInvoiceStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    draft: "下書き",
    pending: "未払い",
    partial: "一部入金",
    paid: "支払済",
    overdue: "延滞",
    cancelled: "キャンセル",
  };
  return statusMap[status] || status;
}

function getContactTypeLabel(type: string): string {
  const typeMap: Record<string, string> = {
    PHONE_IN: "電話（受信）",
    PHONE_OUT: "電話（発信）",
    EMAIL_IN: "メール（受信）",
    EMAIL_OUT: "メール（送信）",
    VISIT: "来校",
    MEETING: "面談",
    ONLINE_MEETING: "オンライン面談",
    CHAT: "チャット",
    OTHER: "その他",
  };
  return typeMap[type] || type;
}

function getContactStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    OPEN: "対応中",
    PENDING: "保留",
    RESOLVED: "解決",
    CLOSED: "クローズ",
  };
  return statusMap[status] || status;
}

function getContactStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    OPEN: "bg-blue-100 text-blue-800",
    PENDING: "bg-yellow-100 text-yellow-800",
    RESOLVED: "bg-green-100 text-green-800",
    CLOSED: "bg-gray-100 text-gray-800",
  };
  return colorMap[status] || "bg-gray-100 text-gray-800";
}

function getSenderTypeLabel(type: string): string {
  const typeMap: Record<string, string> = {
    GUARDIAN: "保護者",
    STAFF: "スタッフ",
    BOT: "ボット",
  };
  return typeMap[type] || type;
}

export function StudentDetail({ student, parents, contracts, invoices, contactLogs = [], chatLogs = [], messages = [], siblings = [], onSelectSibling, onContractUpdate }: StudentDetailProps) {
  const [activeTab, setActiveTab] = useState("basic");
  const [editingContract, setEditingContract] = useState<Contract | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);

  // 新規契約登録ダイアログ
  const [newContractDialogOpen, setNewContractDialogOpen] = useState(false);

  // 保護者編集ダイアログ
  const [guardianEditDialogOpen, setGuardianEditDialogOpen] = useState(false);
  const [editingGuardian, setEditingGuardian] = useState<Guardian | null>(null);
  const [guardianForm, setGuardianForm] = useState({
    last_name: '',
    first_name: '',
    last_name_kana: '',
    first_name_kana: '',
    phone: '',
    phone_mobile: '',
    email: '',
    postal_code: '',
    prefecture: '',
    city: '',
    address1: '',
    address2: '',
  });

  // 休会・退会ダイアログ
  const [suspensionDialogOpen, setSuspensionDialogOpen] = useState(false);
  const [withdrawalDialogOpen, setWithdrawalDialogOpen] = useState(false);
  const [suspensionForm, setSuspensionForm] = useState({
    suspend_from: new Date().toISOString().split('T')[0],
    suspend_until: '',
    keep_seat: true,
    reason: 'other',
    reason_detail: '',
  });
  const [withdrawalForm, setWithdrawalForm] = useState({
    withdrawal_date: new Date().toISOString().split('T')[0],
    last_lesson_date: '',
    reason: 'other',
    reason_detail: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 休会・退会申請履歴
  const [suspensionRequests, setSuspensionRequests] = useState<any[]>([]);
  const [withdrawalRequests, setWithdrawalRequests] = useState<any[]>([]);

  // 締め済み月の情報
  const [closedMonths, setClosedMonths] = useState<Set<string>>(new Set());

  // 保護者の預り金残高
  const [guardianBalance, setGuardianBalance] = useState<{
    balance: number;
    lastUpdated: string | null;
  } | null>(null);

  // 保護者の預り金残高を取得
  useEffect(() => {
    const fetchGuardianBalance = async () => {
      // 最初の保護者のIDを取得
      const guardian = parents[0];
      if (!guardian?.id) return;

      try {
        const data = await apiClient.get<{
          guardian_id: string;
          balance: number;
          last_updated: string | null;
        }>(`/billing/balances/by-guardian/${guardian.id}/`);
        setGuardianBalance({
          balance: data.balance || 0,
          lastUpdated: data.last_updated,
        });
      } catch (error) {
        // 残高レコードがない場合は0として扱う
        setGuardianBalance({ balance: 0, lastUpdated: null });
      }
    };
    if (parents.length > 0) {
      fetchGuardianBalance();
    }
  }, [parents]);

  // 締め済み月の情報を取得
  useEffect(() => {
    const fetchBillingDeadlines = async () => {
      try {
        const data = await apiClient.get<{
          months: { year: number; month: number; is_closed: boolean }[];
        }>('/billing/deadlines/status_list/');
        const closed = new Set<string>();
        if (data.months) {
          data.months.forEach((m) => {
            if (m.is_closed) {
              closed.add(`${m.year}-${String(m.month).padStart(2, '0')}`);
            }
          });
        }
        setClosedMonths(closed);
      } catch (error) {
        console.error('Failed to fetch billing deadlines:', error);
      }
    };
    fetchBillingDeadlines();
  }, []);

  // 契約の請求月が締め済みかどうかをチェック
  // 過去月は全て締め済みとして扱う
  const isContractPeriodClosed = (contract: Contract): boolean => {
    const startDateStr = contract.start_date || (contract as any).startDate;
    if (!startDateStr) return false;

    const startDate = new Date(startDateStr);
    if (isNaN(startDate.getTime())) return false;

    const now = new Date();
    const currentYearMonth = now.getFullYear() * 12 + now.getMonth();
    const contractYearMonth = startDate.getFullYear() * 12 + startDate.getMonth();

    // 過去月は締め済み
    if (contractYearMonth < currentYearMonth) {
      return true;
    }

    // または、closedMonthsに含まれている場合も締め済み
    const yearMonth = `${startDate.getFullYear()}-${String(startDate.getMonth() + 1).padStart(2, '0')}`;
    return closedMonths.has(yearMonth);
  };

  // 休会・退会申請を取得
  useEffect(() => {
    const fetchRequests = async () => {
      try {
        const [suspensions, withdrawals] = await Promise.all([
          apiClient.get<{ results?: any[]; data?: any[] } | any[]>(`/students/suspension-requests/?student_id=${student.id}`),
          apiClient.get<{ results?: any[]; data?: any[] } | any[]>(`/students/withdrawal-requests/?student_id=${student.id}`),
        ]);
        const suspensionData = Array.isArray(suspensions) ? suspensions : (suspensions.results || suspensions.data || []);
        const withdrawalData = Array.isArray(withdrawals) ? withdrawals : (withdrawals.results || withdrawals.data || []);
        setSuspensionRequests(suspensionData);
        setWithdrawalRequests(withdrawalData);
      } catch (error) {
        console.error('Failed to fetch requests:', error);
      }
    };
    if (student.id) {
      fetchRequests();
    }
  }, [student.id]);

  // 契約フィルター用の年月選択
  const [contractYear, setContractYear] = useState<string>("all");
  const [contractMonth, setContractMonth] = useState<string>("all");

  // 請求フィルター用の年月選択
  const [invoiceYear, setInvoiceYear] = useState<string>("all");
  const [invoiceMonth, setInvoiceMonth] = useState<string>("all");

  // やりとりタブのサブタブと日付フィルター
  const [commTab, setCommTab] = useState<"logs" | "chat" | "requests">("logs");
  const [commDateFrom, setCommDateFrom] = useState<string>("");
  const [commDateTo, setCommDateTo] = useState<string>("");

  // 日付フィルタリングされた対応ログ
  const filteredContactLogs = useMemo(() => {
    return contactLogs.filter((log) => {
      const logDate = new Date(log.created_at);
      if (commDateFrom && logDate < new Date(commDateFrom)) return false;
      if (commDateTo && logDate > new Date(commDateTo + "T23:59:59")) return false;
      return true;
    });
  }, [contactLogs, commDateFrom, commDateTo]);

  // 日付フィルタリングされたメッセージ
  const filteredMessages = useMemo(() => {
    const allMessages = messages.length > 0 ? messages : chatLogs;
    return allMessages.filter((msg: any) => {
      const msgDate = new Date(msg.created_at || msg.timestamp);
      if (commDateFrom && msgDate < new Date(commDateFrom)) return false;
      if (commDateTo && msgDate > new Date(commDateTo + "T23:59:59")) return false;
      return true;
    });
  }, [messages, chatLogs, commDateFrom, commDateTo]);

  // 日付フィルターをクリア
  const clearCommDateFilter = () => {
    setCommDateFrom("");
    setCommDateTo("");
  };

  // 年の選択肢を生成（過去3年〜今年まで）
  const currentYear = new Date().getFullYear();
  const yearOptions = useMemo(() => {
    const years = [];
    for (let y = currentYear - 3; y <= currentYear + 1; y++) {
      years.push(y);
    }
    return years;
  }, [currentYear]);

  // 月の選択肢
  const monthOptions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

  // 日付文字列をDateに変換（複数フォーマット対応）
  const parseDate = (dateStr: string | null | undefined): Date | null => {
    if (!dateStr) return null;
    // ISO形式 (2025-10-01)
    let date = new Date(dateStr);
    if (!isNaN(date.getTime())) return date;
    // スラッシュ形式 (2025/10/1)
    const slashMatch = dateStr.match(/(\d{4})\/(\d{1,2})\/(\d{1,2})/);
    if (slashMatch) {
      return new Date(parseInt(slashMatch[1]), parseInt(slashMatch[2]) - 1, parseInt(slashMatch[3]));
    }
    // 日本語形式 (2025年10月1日)
    const jpMatch = dateStr.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
    if (jpMatch) {
      return new Date(parseInt(jpMatch[1]), parseInt(jpMatch[2]) - 1, parseInt(jpMatch[3]));
    }
    return null;
  };

  // 契約フィルター処理
  const filteredContracts = useMemo(() => {
    if (contractYear === "all" && contractMonth === "all") {
      return contracts;
    }

    const filterYear = contractYear !== "all" ? parseInt(contractYear) : null;
    const filterMonth = contractMonth !== "all" ? parseInt(contractMonth) : null;

    const filtered = contracts.filter((contract) => {
      const startDateStr = contract.start_date || contract.startDate;
      const endDateStr = contract.end_date || contract.endDate;

      if (!startDateStr) return false; // 開始日なしは非表示

      const startDate = parseDate(startDateStr);
      const endDate = parseDate(endDateStr);

      if (!startDate) return false; // パース失敗は非表示

      // フィルター期間の設定
      if (filterYear && filterMonth) {
        // 年と月両方指定: その年月に請求対象となる契約のみ
        const filterMonthStart = new Date(filterYear, filterMonth - 1, 1);
        const filterMonthEnd = new Date(filterYear, filterMonth, 0, 23, 59, 59);

        // 契約開始日がフィルター月の末日以前 AND
        // 契約終了日がフィルター月の初日以降（または終了日なし）
        const startBeforeOrInMonth = startDate <= filterMonthEnd;
        const endAfterOrInMonth = !endDate || endDate >= filterMonthStart;

        return startBeforeOrInMonth && endAfterOrInMonth;
      } else if (filterYear) {
        // 年のみ指定: その年に請求対象となる契約
        const yearStart = new Date(filterYear, 0, 1);
        const yearEnd = new Date(filterYear, 11, 31, 23, 59, 59);

        const startBeforeOrInYear = startDate <= yearEnd;
        const endAfterOrInYear = !endDate || endDate >= yearStart;

        return startBeforeOrInYear && endAfterOrInYear;
      } else if (filterMonth) {
        // 月のみ指定: 現在の年のその月に有効な契約
        const thisYear = new Date().getFullYear();
        const filterMonthStart = new Date(thisYear, filterMonth - 1, 1);
        const filterMonthEnd = new Date(thisYear, filterMonth, 0, 23, 59, 59);

        const startBeforeOrInMonth = startDate <= filterMonthEnd;
        const endAfterOrInMonth = !endDate || endDate >= filterMonthStart;

        return startBeforeOrInMonth && endAfterOrInMonth;
      }
      return true;
    });

    // 開始日でソート（新しいものが先）
    return filtered.sort((a, b) => {
      const aDateStr = a.start_date || a.startDate;
      const bDateStr = b.start_date || b.startDate;
      const aDate = aDateStr ? parseDate(aDateStr) : null;
      const bDate = bDateStr ? parseDate(bDateStr) : null;
      if (!aDate && !bDate) return 0;
      if (!aDate) return 1;
      if (!bDate) return -1;
      return bDate.getTime() - aDate.getTime(); // 降順
    });
  }, [contracts, contractYear, contractMonth]);

  // 請求フィルター処理
  const filteredInvoices = useMemo(() => {
    if (invoiceYear === "all" && invoiceMonth === "all") {
      return invoices;
    }
    return invoices.filter((invoice) => {
      const billingMonth = String(invoice.billingMonth || invoice.billing_month || "");
      // billing_monthは "2024年1月" のような形式を想定
      if (!billingMonth || billingMonth === "未設定") return true;

      const match = billingMonth.match(/(\d{4})年(\d{1,2})月/);
      if (!match) return true;

      const invYear = parseInt(match[1]);
      const invMonth = parseInt(match[2]);

      const filterYear = invoiceYear !== "all" ? parseInt(invoiceYear) : null;
      const filterMonth = invoiceMonth !== "all" ? parseInt(invoiceMonth) : null;

      if (filterYear && filterMonth) {
        return invYear === filterYear && invMonth === filterMonth;
      } else if (filterYear) {
        return invYear === filterYear;
      } else if (filterMonth) {
        return invMonth === filterMonth;
      }
      return true;
    });
  }, [invoices, invoiceYear, invoiceMonth]);

  // フィールド名の両対応 (eslint-disable-next-line @typescript-eslint/no-explicit-any)
  const s = student as any;
  const lastName = s.lastName || s.last_name || "";
  const firstName = s.firstName || s.first_name || "";
  const lastNameKana = s.lastNameKana || s.last_name_kana || "";
  const firstNameKana = s.firstNameKana || s.first_name_kana || "";
  const studentNo = s.studentNo || s.student_no || "";
  const gradeText = s.gradeText || s.grade_text || s.gradeName || "";
  const schoolName = s.schoolName || s.school_name || "";
  const primarySchoolName = s.primarySchoolName || s.primary_school_name || "";
  const primaryBrandName = s.primaryBrandName || s.primary_brand_name || "";
  const brandNames = s.brandNames || s.brand_names || [];
  const email = s.email || "";
  const phone = s.phone || "";
  const gender = s.gender || "";
  // 日付情報
  const birthDate = s.birthDate || s.birth_date || "";
  const enrollmentDate = s.enrollmentDate || s.enrollment_date || "";
  const registeredDate = s.registeredDate || s.registered_date || "";
  const trialDate = s.trialDate || s.trial_date || "";

  // 日付フォーマット
  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "-";
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
  };

  // 保護者編集ダイアログを開く
  const openGuardianEditDialog = (g: Guardian) => {
    setEditingGuardian(g);
    setGuardianForm({
      last_name: g.lastName || g.last_name || '',
      first_name: g.firstName || g.first_name || '',
      last_name_kana: g.lastNameKana || g.last_name_kana || '',
      first_name_kana: g.firstNameKana || g.first_name_kana || '',
      phone: g.phone || '',
      phone_mobile: g.phoneMobile || g.phone_mobile || '',
      email: g.email || '',
      postal_code: g.postalCode || g.postal_code || '',
      prefecture: g.prefecture || '',
      city: g.city || '',
      address1: g.address1 || '',
      address2: g.address2 || '',
    });
    setGuardianEditDialogOpen(true);
  };

  // 保護者情報を更新
  const handleGuardianUpdate = async () => {
    if (!editingGuardian) return;
    setIsSubmitting(true);
    try {
      await apiClient.patch(`/students/guardians/${editingGuardian.id}/`, guardianForm);
      alert('保護者情報を更新しました');
      setGuardianEditDialogOpen(false);
      window.location.reload();
    } catch (error: any) {
      console.error('Guardian update error:', error);
      alert(error.message || '保護者情報の更新に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 休会申請を送信
  const handleSuspensionSubmit = async () => {
    setIsSubmitting(true);
    try {
      const response = await apiClient.post<{ id: string }>('/students/suspension-requests/', {
        student: student.id,
        school: student.primary_school?.id || student.primary_school_id,
        ...suspensionForm,
      });

      // 承認処理も同時に実行（管理者なので）
      await apiClient.post(`/students/suspension-requests/${response.id}/approve/`, {});

      alert('休会登録が完了しました');
      setSuspensionDialogOpen(false);
      window.location.reload(); // リロードして最新状態を取得
    } catch (error: any) {
      console.error('Suspension error:', error);
      alert(error.message || '休会登録に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 退会申請を送信
  const handleWithdrawalSubmit = async () => {
    setIsSubmitting(true);
    try {
      const response = await apiClient.post<{ id: string }>('/students/withdrawal-requests/', {
        student: student.id,
        school: student.primary_school?.id || student.primary_school_id,
        ...withdrawalForm,
      });

      // 承認処理も同時に実行（管理者なので）
      await apiClient.post(`/students/withdrawal-requests/${response.id}/approve/`, {});

      alert('退会登録が完了しました');
      setWithdrawalDialogOpen(false);
      window.location.reload(); // リロードして最新状態を取得
    } catch (error: any) {
      console.error('Withdrawal error:', error);
      alert(error.message || '退会登録に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 保護者情報
  const guardian = parents[0] || student.guardian;
  const guardianNo = guardian?.guardianNo || guardian?.guardian_no || "";
  const guardianLastName = guardian?.lastName || guardian?.last_name || "";
  const guardianFirstName = guardian?.firstName || guardian?.first_name || "";
  const guardianName = `${guardianLastName} ${guardianFirstName}`.trim();
  const guardianPhone = guardian?.phone || guardian?.phoneMobile || guardian?.phone_mobile || "";
  const guardianEmail = guardian?.email || "";

  return (
    <div className="h-full flex flex-col bg-white">
      {/* ヘッダー */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold">{lastName} {firstName}</h2>
            <p className="text-blue-100 text-sm">{lastNameKana} {firstNameKana}</p>
            <p className="text-blue-200 text-xs mt-1">No. {studentNo}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={getStatusColor(student.status)}>
              {getStatusLabel(student.status)}
            </Badge>
{/* 保護者画面ボタン - ユーザーアカウント作成後に有効化予定 */}
          </div>
        </div>
      </div>

      {/* タブ */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="w-full justify-start rounded-none border-b bg-gray-50 p-0">
          <TabsTrigger
            value="basic"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-white px-4 py-2"
          >
            基本情報
          </TabsTrigger>
          <TabsTrigger
            value="guardian"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-white px-4 py-2"
          >
            保護者
          </TabsTrigger>
          <TabsTrigger
            value="contracts"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-white px-4 py-2"
          >
            契約
          </TabsTrigger>
          <TabsTrigger
            value="billing"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-white px-4 py-2"
          >
            請求
          </TabsTrigger>
          <TabsTrigger
            value="communications"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-white px-4 py-2"
          >
            やりとり
          </TabsTrigger>
        </TabsList>

        {/* 基本情報タブ */}
        <TabsContent value="basic" className="flex-1 overflow-auto p-0 m-0">
          <div className="p-4 space-y-4">
            {/* 生徒基本情報 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">生徒情報</h3>
              <table className="w-full text-sm border">
                <tbody>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium w-28 border-r">生徒ID</th>
                    <td className="px-3 py-2 font-mono">{studentNo}</td>
                  </tr>
                  <tr className="border-b">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">学年</th>
                    <td className="px-3 py-2">{gradeText || "-"}</td>
                  </tr>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">生年月日</th>
                    <td className="px-3 py-2">{formatDate(birthDate)}</td>
                  </tr>
                  <tr className="border-b">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">性別</th>
                    <td className="px-3 py-2">{gender === "male" ? "男" : gender === "female" ? "女" : "-"}</td>
                  </tr>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">学校名</th>
                    <td className="px-3 py-2">{schoolName || "-"}</td>
                  </tr>
                  <tr className="border-b">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">電話番号</th>
                    <td className="px-3 py-2">{phone || "-"}</td>
                  </tr>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">メール</th>
                    <td className="px-3 py-2 break-all">{email || "-"}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* 在籍情報 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">在籍情報</h3>
              <table className="w-full text-sm border">
                <tbody>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium w-28 border-r">校舎</th>
                    <td className="px-3 py-2">{primarySchoolName || "-"}</td>
                  </tr>
                  <tr className="border-b">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">ブランド</th>
                    <td className="px-3 py-2">
                      {primaryBrandName || (brandNames.length > 0 ? brandNames.join(", ") : "-")}
                    </td>
                  </tr>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium w-28 border-r">体験日</th>
                    <td className="px-3 py-2">{formatDate(trialDate)}</td>
                  </tr>
                  <tr className="border-b">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">入会日</th>
                    <td className="px-3 py-2">{formatDate(enrollmentDate)}</td>
                  </tr>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">登録日</th>
                    <td className="px-3 py-2">{formatDate(registeredDate)}</td>
                  </tr>
                  <tr className="border-b">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">契約ブランド</th>
                    <td className="px-3 py-2">
                      {contracts.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {Array.from(new Set(contracts.map(c => (c as any).brand_name || (c as any).brandName).filter(Boolean))).map((brandName, i) => (
                            <Badge key={i} variant="outline" className="text-xs">{brandName as string}</Badge>
                          ))}
                        </div>
                      ) : "-"}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* 保護者情報（概要） */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">保護者情報</h3>
              <table className="w-full text-sm border">
                <tbody>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium w-28 border-r">保護者名</th>
                    <td className="px-3 py-2">{guardianName || "-"}</td>
                  </tr>
                  <tr className="border-b">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">保護者ID</th>
                    <td className="px-3 py-2 font-mono">{guardianNo || "-"}</td>
                  </tr>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">電話番号</th>
                    <td className="px-3 py-2">{guardianPhone || "-"}</td>
                  </tr>
                  <tr className="border-b">
                    <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">メール</th>
                    <td className="px-3 py-2 break-all">{guardianEmail || "-"}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* 兄弟情報 */}
            {siblings.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                  <Users className="w-4 h-4 mr-1" />
                  兄弟姉妹
                </h3>
                <div className="flex flex-wrap gap-2">
                  {siblings.map((sibling) => {
                    const siblingName = `${sibling.lastName || sibling.last_name || ""} ${sibling.firstName || sibling.first_name || ""}`.trim();
                    const siblingGrade = sibling.gradeText || sibling.grade_text || sibling.gradeName || "";
                    const siblingStatus = sibling.status;
                    return (
                      <button
                        key={sibling.id}
                        onClick={() => onSelectSibling?.(sibling.id)}
                        className="flex items-center gap-2 p-2 border rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors cursor-pointer text-left"
                      >
                        <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                          <User className="w-4 h-4 text-gray-500" />
                        </div>
                        <div>
                          <div className="font-medium text-sm">{siblingName}</div>
                          <div className="text-xs text-gray-500">
                            {siblingGrade && <span>{siblingGrade}</span>}
                            {siblingGrade && siblingStatus && <span> / </span>}
                            {siblingStatus && (
                              <Badge className={`text-xs ${getStatusColor(siblingStatus)}`}>
                                {getStatusLabel(siblingStatus)}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 銀行口座情報 */}
            {guardian && (guardian.bank_name || guardian.bankName) && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">引落口座</h3>
                <table className="w-full text-sm border">
                  <tbody>
                    <tr className="border-b bg-gray-50">
                      <th className="px-3 py-2 text-left text-gray-600 font-medium w-28 border-r">金融機関</th>
                      <td className="px-3 py-2">{guardian.bank_name || guardian.bankName || "-"}</td>
                    </tr>
                    <tr className="border-b">
                      <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">支店</th>
                      <td className="px-3 py-2">{guardian.branch_name || guardian.branchName || "-"}</td>
                    </tr>
                    <tr className="border-b bg-gray-50">
                      <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">口座番号</th>
                      <td className="px-3 py-2 font-mono">
                        {(guardian.account_type || guardian.accountType) === "ordinary" ? "普通" : "当座"}{" "}
                        {guardian.account_number || guardian.accountNumber || "-"}
                      </td>
                    </tr>
                    <tr className="border-b">
                      <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">名義</th>
                      <td className="px-3 py-2">{guardian.account_holder_kana || guardian.accountHolderKana || "-"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}

            {/* 特記事項 */}
            {(s.notes || s.tags) && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">特記事項</h3>
                <div className="border rounded p-3 bg-yellow-50 text-sm">
                  {s.tags && Array.isArray(s.tags) && s.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {s.tags.map((tag: string, i: number) => (
                        <Badge key={i} className="bg-yellow-200 text-yellow-800 text-xs">{tag}</Badge>
                      ))}
                    </div>
                  )}
                  <p className="whitespace-pre-wrap text-gray-700">{s.notes || "特記事項なし"}</p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <Button size="sm" className="w-full">
                <MessageCircle className="w-4 h-4 mr-1" />
                チャット
              </Button>
              <Button size="sm" variant="outline" className="w-full">
                <Edit className="w-4 h-4 mr-1" />
                編集
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* 保護者タブ */}
        <TabsContent value="guardian" className="flex-1 overflow-auto p-0 m-0">
          <div className="p-4">
            {parents.length > 0 || guardian ? (
              <div className="space-y-4">
                {(parents.length > 0 ? parents : [guardian]).filter(Boolean).map((g, idx) => {
                  const gNo = g?.guardianNo || g?.guardian_no || "";
                  const gLastName = g?.lastName || g?.last_name || "";
                  const gFirstName = g?.firstName || g?.first_name || "";
                  const gLastNameKana = g?.lastNameKana || g?.last_name_kana || "";
                  const gFirstNameKana = g?.firstNameKana || g?.first_name_kana || "";
                  const gPhone = g?.phone || "";
                  const gPhoneMobile = g?.phoneMobile || g?.phone_mobile || "";
                  const gEmail = g?.email || "";
                  const gPostalCode = g?.postalCode || g?.postal_code || "";
                  const gPrefecture = g?.prefecture || "";
                  const gCity = g?.city || "";
                  const gAddress1 = g?.address1 || "";
                  const gAddress2 = g?.address2 || "";

                  return (
                    <div key={g?.id || idx} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-start gap-3">
                          <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
                            <User className="w-6 h-6 text-gray-500" />
                          </div>
                          <div>
                            <h3 className="font-bold text-lg">{gLastName} {gFirstName}</h3>
                            <p className="text-sm text-gray-500">{gLastNameKana} {gFirstNameKana}</p>
                            <p className="text-xs text-gray-400">No. {gNo}</p>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => g && openGuardianEditDialog(g)}
                        >
                          <Pencil className="w-4 h-4 mr-1" />
                          編集
                        </Button>
                      </div>

                      <table className="w-full text-sm border">
                        <tbody>
                          <tr className="border-b bg-gray-50">
                            <th className="px-3 py-2 text-left text-gray-600 font-medium w-28 border-r">
                              <Phone className="w-4 h-4 inline mr-1" />電話
                            </th>
                            <td className="px-3 py-2">{gPhone || "-"}</td>
                          </tr>
                          <tr className="border-b">
                            <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">
                              <Phone className="w-4 h-4 inline mr-1" />携帯
                            </th>
                            <td className="px-3 py-2">{gPhoneMobile || "-"}</td>
                          </tr>
                          <tr className="border-b bg-gray-50">
                            <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">
                              <Mail className="w-4 h-4 inline mr-1" />メール
                            </th>
                            <td className="px-3 py-2 break-all">{gEmail || "-"}</td>
                          </tr>
                          <tr className="border-b">
                            <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">
                              <MapPin className="w-4 h-4 inline mr-1" />住所
                            </th>
                            <td className="px-3 py-2">
                              {gPostalCode && <span className="text-gray-500">〒{gPostalCode}<br /></span>}
                              {gPrefecture}{gCity}{gAddress1}{gAddress2 || "-"}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                保護者情報が登録されていません
              </div>
            )}
          </div>
        </TabsContent>

        {/* 契約タブ */}
        <TabsContent value="contracts" className="flex-1 overflow-auto p-0 m-0">
          <div className="p-4">
            {/* 年月フィルター */}
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-4 h-4 text-gray-500" />
              <Select value={contractYear} onValueChange={setContractYear}>
                <SelectTrigger className="w-24 h-8">
                  <SelectValue placeholder="年" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全て</SelectItem>
                  {yearOptions.map((y) => (
                    <SelectItem key={y} value={String(y)}>{y}年</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={contractMonth} onValueChange={setContractMonth}>
                <SelectTrigger className="w-20 h-8">
                  <SelectValue placeholder="月" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全て</SelectItem>
                  {monthOptions.map((m) => (
                    <SelectItem key={m} value={String(m)}>{m}月</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-xs text-gray-500 ml-2">
                {filteredContracts.length}件
              </span>
            </div>

            {filteredContracts.length > 0 ? (
              <div className="space-y-3">
                {filteredContracts.map((contract) => {
                  // 各種フィールド取得
                  const courseName = contract.course_name || contract.courseName || "";
                  const brandName = contract.brand_name || contract.brandName || "";
                  const schoolName = contract.school_name || contract.schoolName || "";
                  const contractNo = contract.contract_no || contract.contractNo || "";
                  const contractName = courseName || brandName || contractNo || "-";
                  // monthlyTotalは後でフィルタ後のアイテムから計算
                  const originalMonthlyTotal = contract.monthly_total || contract.monthlyTotal || 0;
                  const discountApplied = contract.discount_applied || contract.discountApplied || 0;
                  const discountType = contract.discount_type || contract.discountType || "";
                  const dayOfWeek = contract.day_of_week || contract.dayOfWeek;
                  const startTime = contract.start_time || contract.startTime || "";

                  // 生徒商品（明細）を取得
                  const allStudentItems = contract.student_items || contract.studentItems || [];

                  // 契約の開始月を取得（この契約の請求月）
                  const contractStartDate = contract.start_date || contract.startDate || "";
                  const contractBillingMonth = contractStartDate ? contractStartDate.substring(0, 7) : ""; // "YYYY-MM"

                  // billing_monthを正規化する関数（"202503" → "2025-03", "2025-03" → "2025-03"）
                  const normalizeBillingMonth = (bm: string): string => {
                    if (!bm) return "";
                    // 既に "YYYY-MM" 形式の場合
                    if (bm.includes("-")) return bm;
                    // "YYYYMM" 形式の場合
                    if (bm.length === 6) return `${bm.substring(0, 4)}-${bm.substring(4, 6)}`;
                    return bm;
                  };

                  // 契約の請求月でフィルタリング（各契約はその月のアイテムのみ表示）
                  const studentItems = allStudentItems.filter((item: { billing_month?: string; billingMonth?: string }) => {
                    const itemBillingMonth = item.billing_month || item.billingMonth || "";
                    if (!itemBillingMonth) return true;

                    // billing_monthを正規化して比較
                    const normalizedItemMonth = normalizeBillingMonth(itemBillingMonth);

                    // 契約の請求月と一致するアイテムのみ表示
                    if (contractBillingMonth) {
                      return normalizedItemMonth === contractBillingMonth;
                    }

                    // 契約の請求月がない場合は、フィルターで絞り込み
                    if (contractYear !== "all" || contractMonth !== "all") {
                      const [itemYear, itemMonth] = normalizedItemMonth.split("-");
                      if (contractYear !== "all" && itemYear !== contractYear) return false;
                      if (contractMonth !== "all" && parseInt(itemMonth) !== parseInt(contractMonth)) return false;
                    }
                    return true;
                  });

                  // 割引情報を取得
                  const discounts = contract.discounts || [];
                  const discountTotal = contract.discount_total || contract.discountTotal || 0;

                  // 請求月を取得（フィルタ後のStudentItemから）
                  const billingMonths = Array.from(new Set(studentItems.map((item: { billing_month?: string; billingMonth?: string }) =>
                    item.billing_month || item.billingMonth
                  ).filter(Boolean)));
                  const billingMonthLabel = billingMonths.length > 0 ? billingMonths.join(", ") : "";

                  // フィルタ後のアイテムから月額合計を計算
                  const monthlyTotal = studentItems.length > 0
                    ? studentItems.reduce((sum: number, item: { final_price?: number | string; finalPrice?: number | string; unit_price?: number | string; unitPrice?: number | string }) => {
                        const price = Number(item.final_price || item.finalPrice || item.unit_price || item.unitPrice || 0);
                        return sum + price;
                      }, 0)
                    : originalMonthlyTotal;

                  // 曜日表示
                  const dayOfWeekLabel = dayOfWeek ? ["", "月", "火", "水", "木", "金", "土", "日"][dayOfWeek] || "" : "";

                  // 日付フォーマット（YYYY-MM形式）
                  const startDateStr = contract.start_date || contract.startDate;
                  const endDateStr = contract.end_date || contract.endDate;
                  const formatYearMonth = (dateStr: string | null | undefined) => {
                    if (!dateStr) return "-";
                    const date = new Date(dateStr);
                    if (isNaN(date.getTime())) return "-";
                    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
                  };
                  const startYearMonth = formatYearMonth(startDateStr);
                  const endYearMonth = formatYearMonth(endDateStr);
                  const status = contract.status || "";

                  // ステータスカラー
                  const statusColor = status === "active" ? "bg-green-100 text-green-700 border-green-300"
                    : status === "cancelled" ? "bg-red-100 text-red-700 border-red-300"
                    : "bg-gray-100 text-gray-700 border-gray-300";

                  return (
                    <div key={contract.id} className="border rounded-lg overflow-hidden hover:shadow-md transition-shadow">
                      {/* ヘッダー */}
                      <div className="bg-gray-50 px-4 py-2 flex items-center justify-between border-b">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm">{contractName}</span>
                          <Badge className={`text-xs ${statusColor}`}>
                            {getContractStatusLabel(status)}
                          </Badge>
                          {startYearMonth !== "-" && (
                            <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                              {startYearMonth}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">No. {contractNo}</span>
                          {isContractPeriodClosed(contract) ? (
                            <span
                              className="h-6 px-2 flex items-center text-xs text-gray-400 bg-gray-100 rounded"
                              title="締め済みのため編集不可"
                            >
                              締め済み
                            </span>
                          ) : (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 w-6 p-0 text-gray-500 hover:text-blue-600"
                              onClick={() => {
                                setEditingContract(contract);
                                setEditDialogOpen(true);
                              }}
                            >
                              <Pencil className="w-3 h-3" />
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* 基本情報 */}
                      <div className="px-4 py-2 border-b bg-white">
                        <div className="grid grid-cols-4 gap-2 text-xs">
                          <div>
                            <span className="text-gray-500">ブランド:</span>
                            <span className="font-medium ml-1">{brandName || "-"}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">校舎:</span>
                            <span className="font-medium ml-1">{schoolName || "-"}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">曜日:</span>
                            <span className="font-medium ml-1">
                              {dayOfWeekLabel ? `${dayOfWeekLabel}曜 ${startTime || ""}` : "-"}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">期間:</span>
                            <span className="font-medium ml-1">{startYearMonth} 〜 {endYearMonth}</span>
                          </div>
                        </div>
                      </div>

                      {/* 教材費選択 */}
                      {(() => {
                        const textbookOptions = contract.textbook_options || contract.textbookOptions || [];
                        const selectedIds = new Set(contract.selected_textbook_ids || contract.selectedTextbookIds || []);

                        if (textbookOptions.length > 0) {
                          return (
                            <div className="px-4 py-2 border-b bg-amber-50">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-xs font-medium text-amber-700">教材費選択:</span>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {textbookOptions.map((option: { id: string; product_name?: string; productName?: string; price: number }) => {
                                  const isSelected = selectedIds.has(option.id);
                                  const optionName = option.product_name || option.productName || "教材費";

                                  return (
                                    <label
                                      key={option.id}
                                      className={`flex items-center gap-1 px-2 py-1 rounded border cursor-pointer text-xs transition-colors ${
                                        isSelected
                                          ? 'bg-amber-200 border-amber-400 text-amber-800'
                                          : 'bg-white border-gray-200 text-gray-600 hover:border-amber-300'
                                      }`}
                                    >
                                      <input
                                        type="checkbox"
                                        checked={isSelected}
                                        onChange={async (e) => {
                                          const newSelectedIds = new Set(selectedIds);
                                          if (e.target.checked) {
                                            newSelectedIds.add(option.id);
                                          } else {
                                            newSelectedIds.delete(option.id);
                                          }

                                          try {
                                            await apiClient.post(`/contracts/${contract.id}/update-textbooks/`, {
                                              selected_textbook_ids: Array.from(newSelectedIds)
                                            });
                                            // ページをリロードして更新を反映
                                            window.location.reload();
                                          } catch (err) {
                                            console.error('Failed to update textbooks:', err);
                                            alert('教材費の更新に失敗しました');
                                          }
                                        }}
                                        className="w-3 h-3"
                                        disabled={isContractPeriodClosed(contract)}
                                      />
                                      <span>{optionName}</span>
                                      <span className="text-gray-500">¥{option.price.toLocaleString()}</span>
                                    </label>
                                  );
                                })}
                              </div>
                              {selectedIds.size === 0 && (
                                <p className="text-xs text-amber-600 mt-1">※ 教材費が選択されていません</p>
                              )}
                            </div>
                          );
                        }
                        return null;
                      })()}

                      {/* 料金内訳 */}
                      <div className="p-3">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b">
                              <th className="text-left py-1 text-gray-500 font-normal">項目</th>
                              <th className="text-right py-1 text-gray-500 font-normal w-20">数量</th>
                              <th className="text-right py-1 text-gray-500 font-normal w-24">単価</th>
                              <th className="text-right py-1 text-gray-500 font-normal w-24">金額</th>
                            </tr>
                          </thead>
                          <tbody>
                            {studentItems.length > 0 ? (
                              studentItems.map((item: {
                                id: string;
                                product_name?: string;
                                productName?: string;
                                notes?: string;
                                quantity?: number;
                                unit_price?: number | string;
                                unitPrice?: number | string;
                                final_price?: number | string;
                                finalPrice?: number | string;
                              }, idx: number) => {
                                const itemName = item.product_name || item.productName || item.notes || "-";
                                const qty = item.quantity || 1;
                                const unitPrice = item.unit_price || item.unitPrice || 0;
                                const finalPrice = item.final_price || item.finalPrice || 0;
                                return (
                                  <tr key={item.id || idx} className="border-b border-gray-100">
                                    <td className="py-1">{itemName}</td>
                                    <td className="py-1 text-right">{qty}</td>
                                    <td className="py-1 text-right">¥{Number(unitPrice).toLocaleString()}</td>
                                    <td className="py-1 text-right">¥{Number(finalPrice).toLocaleString()}</td>
                                  </tr>
                                );
                              })
                            ) : (
                              <tr className="border-b border-gray-100">
                                <td className="py-1">{courseName || "月額料金"}</td>
                                <td className="py-1 text-right">1</td>
                                <td className="py-1 text-right">¥{Number(monthlyTotal).toLocaleString()}</td>
                                <td className="py-1 text-right">¥{Number(monthlyTotal).toLocaleString()}</td>
                              </tr>
                            )}
                            {/* 割引情報（詳細） */}
                            {discounts.length > 0 ? (
                              discounts.map((discount: StudentDiscount, idx: number) => {
                                const discountName = discount.discount_name || discount.discountName || "割引";
                                const discountAmt = Math.abs(Number(discount.amount) || 0);
                                const discountUnit = discount.discount_unit || discount.discountUnit || "yen";
                                const brandName = discount.brand_name || discount.brandName || "";

                                return (
                                  <tr key={discount.id || idx} className="border-b border-gray-100 text-orange-600">
                                    <td className="py-1" colSpan={3}>
                                      {discountName}
                                      {brandName && <span className="text-orange-400 ml-1">({brandName})</span>}
                                    </td>
                                    <td className="py-1 text-right">
                                      {discountUnit === "percent"
                                        ? `-${discountAmt}%`
                                        : `-¥${discountAmt.toLocaleString()}`
                                      }
                                    </td>
                                  </tr>
                                );
                              })
                            ) : Number(discountApplied) > 0 && (
                              <tr className="border-b border-gray-100 text-orange-600">
                                <td className="py-1" colSpan={3}>
                                  割引{discountType && `（${discountType}）`}
                                </td>
                                <td className="py-1 text-right">-¥{Number(discountApplied).toLocaleString()}</td>
                              </tr>
                            )}
                          </tbody>
                          <tfoot>
                            <tr className="font-bold">
                              <td className="pt-2" colSpan={3}>月額合計</td>
                              <td className="pt-2 text-right text-blue-600">
                                ¥{(Number(monthlyTotal) - Number(discounts.length > 0 ? discountTotal : discountApplied)).toLocaleString()}
                              </td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                {contracts.length > 0 ? "該当期間の契約がありません" : "契約情報がありません"}
              </div>
            )}
            <div className="mt-4">
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={() => setNewContractDialogOpen(true)}
              >
                <FileText className="w-4 h-4 mr-1" />
                新規契約登録
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* 請求タブ */}
        <TabsContent value="billing" className="flex-1 overflow-auto p-0 m-0">
          <div className="p-4">
            {/* 預り金残高表示 */}
            {guardianBalance !== null && (
              <div className={`mb-4 p-3 rounded-lg border ${
                guardianBalance.balance > 0
                  ? 'bg-green-50 border-green-200'
                  : guardianBalance.balance < 0
                    ? 'bg-red-50 border-red-200'
                    : 'bg-gray-50 border-gray-200'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CreditCard className="w-4 h-4 text-gray-500" />
                    <span className="text-sm font-medium text-gray-700">預り金残高</span>
                  </div>
                  <div className="text-right">
                    <span className={`text-lg font-bold ${
                      guardianBalance.balance > 0
                        ? 'text-green-600'
                        : guardianBalance.balance < 0
                          ? 'text-red-600'
                          : 'text-gray-600'
                    }`}>
                      {guardianBalance.balance >= 0 ? '' : '-'}¥{Math.abs(guardianBalance.balance).toLocaleString()}
                    </span>
                    {guardianBalance.balance > 0 && (
                      <div className="text-xs text-green-600">次回請求で相殺可能</div>
                    )}
                    {guardianBalance.balance < 0 && (
                      <div className="text-xs text-red-600">未払い残高あり</div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 年月フィルター */}
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-4 h-4 text-gray-500" />
              <Select value={invoiceYear} onValueChange={setInvoiceYear}>
                <SelectTrigger className="w-24 h-8">
                  <SelectValue placeholder="年" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全て</SelectItem>
                  {yearOptions.map((y) => (
                    <SelectItem key={y} value={String(y)}>{y}年</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={invoiceMonth} onValueChange={setInvoiceMonth}>
                <SelectTrigger className="w-20 h-8">
                  <SelectValue placeholder="月" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全て</SelectItem>
                  {monthOptions.map((m) => (
                    <SelectItem key={m} value={String(m)}>{m}月</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-xs text-gray-500 ml-2">
                {filteredInvoices.length}件
              </span>
            </div>

            {filteredInvoices.length > 0 ? (
              <div className="space-y-4">
                {/* 請求月ごとにグループ化（バケツ形式） */}
                {(() => {
                  // 請求月でグループ化
                  const groupedInvoices: Record<string, typeof invoices> = {};
                  filteredInvoices.forEach((invoice) => {
                    const billingMonth = invoice.billingMonth || invoice.billing_month || "未設定";
                    if (!groupedInvoices[billingMonth]) {
                      groupedInvoices[billingMonth] = [];
                    }
                    groupedInvoices[billingMonth].push(invoice);
                  });

                  return Object.entries(groupedInvoices).map(([month, monthInvoices]) => {
                    // 月の請求合計
                    const monthTotal = monthInvoices.reduce((sum, inv) => {
                      const amount = inv.totalAmount || inv.total_amount || 0;
                      return sum + Number(amount);
                    }, 0);

                    // 入金済み金額
                    const paidAmount = monthInvoices.reduce((sum, inv) => {
                      const paid = inv.paidAmount || inv.paid_amount || 0;
                      return sum + Number(paid);
                    }, 0);

                    // 前月繰越（マイナス=過払い、プラス=未払い）
                    const carryOver = monthInvoices.reduce((sum, inv) => {
                      const carry = inv.carryOverAmount || inv.carry_over_amount || 0;
                      return sum + Number(carry);
                    }, 0);

                    // 今月請求額（繰越含む）
                    const totalDue = monthTotal + carryOver;

                    // 残高（プラス=未払い、マイナス=過払い）
                    const balance = totalDue - paidAmount;

                    // 次月繰越が必要か
                    const needsCarryForward = balance !== 0;

                    // 残高の色
                    const balanceColor = balance > 0 ? "text-red-600" : balance < 0 ? "text-blue-600" : "text-green-600";
                    const balanceLabel = balance > 0 ? "不足" : balance < 0 ? "過払い" : "精算済";

                    return (
                      <div key={month} className="border rounded-lg overflow-hidden">
                        {/* 月ヘッダー（バケツサマリー） */}
                        <div className="bg-gradient-to-r from-gray-100 to-gray-50 px-4 py-3 border-b">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-bold text-lg">{month}</span>
                            <Badge className={`${balance === 0 ? 'bg-green-100 text-green-700' : balance > 0 ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                              {balanceLabel}
                            </Badge>
                          </div>

                          {/* 金額サマリー */}
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="space-y-1">
                              {carryOver !== 0 && (
                                <div className="flex justify-between">
                                  <span className="text-gray-500">前月繰越:</span>
                                  <span className={carryOver > 0 ? "text-red-600" : "text-blue-600"}>
                                    {carryOver > 0 ? "+" : ""}¥{carryOver.toLocaleString()}
                                  </span>
                                </div>
                              )}
                              <div className="flex justify-between">
                                <span className="text-gray-500">今月請求:</span>
                                <span className="font-medium">¥{monthTotal.toLocaleString()}</span>
                              </div>
                              <div className="flex justify-between border-t pt-1">
                                <span className="text-gray-600 font-medium">請求合計:</span>
                                <span className="font-bold">¥{totalDue.toLocaleString()}</span>
                              </div>
                            </div>
                            <div className="space-y-1 border-l pl-3">
                              <div className="flex justify-between">
                                <span className="text-gray-500">入金済み:</span>
                                <span className="font-medium text-green-600">¥{paidAmount.toLocaleString()}</span>
                              </div>
                              <div className="flex justify-between border-t pt-1">
                                <span className="text-gray-600 font-medium">残高:</span>
                                <span className={`font-bold ${balanceColor}`}>
                                  {balance > 0 ? "+" : ""}¥{Math.abs(balance).toLocaleString()}
                                </span>
                              </div>
                              {needsCarryForward && (
                                <div className="flex justify-between text-orange-600">
                                  <span className="text-xs">→ 翌月繰越</span>
                                  <span className="text-xs font-medium">
                                    {balance > 0 ? `+¥${balance.toLocaleString()}` : `-¥${Math.abs(balance).toLocaleString()}`}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* 明細 */}
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-3 py-2 text-left border-r">内容</th>
                              <th className="px-3 py-2 text-right border-r w-20">請求額</th>
                              <th className="px-3 py-2 text-right border-r w-20">入金額</th>
                              <th className="px-3 py-2 text-left border-r w-16">方法</th>
                              <th className="px-3 py-2 text-left w-16">状態</th>
                            </tr>
                          </thead>
                          <tbody>
                            {monthInvoices.map((invoice) => {
                              const totalAmount = invoice.totalAmount || invoice.total_amount || 0;
                              const paidAmt = invoice.paidAmount || invoice.paid_amount || 0;
                              const status = invoice.status || "";
                              const paymentMethod = invoice.paymentMethod || invoice.payment_method || "direct_debit";
                              const description = invoice.description || invoice.invoiceNo || invoice.invoice_no || "-";
                              const courseName = invoice.courseName || invoice.course_name || "";
                              const brandName = invoice.brandName || invoice.brand_name || "";

                              // 支払方法の表示
                              const paymentMethodLabel = paymentMethod === "direct_debit" ? "引落"
                                : paymentMethod === "bank_transfer" ? "振込"
                                : paymentMethod === "credit_card" ? "カード"
                                : paymentMethod === "cash" ? "現金"
                                : paymentMethod;

                              return (
                                <tr key={invoice.id} className="border-b hover:bg-gray-50">
                                  <td className="px-3 py-2 border-r">
                                    <div className="text-xs">
                                      <span className="font-medium">{courseName || description}</span>
                                      {brandName && <span className="text-gray-400 ml-1">({brandName})</span>}
                                    </div>
                                  </td>
                                  <td className="px-3 py-2 border-r text-right text-xs">¥{Number(totalAmount).toLocaleString()}</td>
                                  <td className="px-3 py-2 border-r text-right text-xs">
                                    {Number(paidAmt) > 0 ? (
                                      <span className="text-green-600">¥{Number(paidAmt).toLocaleString()}</span>
                                    ) : (
                                      <span className="text-gray-400">-</span>
                                    )}
                                  </td>
                                  <td className="px-3 py-2 border-r">
                                    <Badge variant="secondary" className="text-xs px-1">
                                      {paymentMethodLabel}
                                    </Badge>
                                  </td>
                                  <td className="px-3 py-2">
                                    <Badge
                                      variant="outline"
                                      className={`text-xs px-1 ${status === 'paid' ? 'bg-green-50 text-green-700' : status === 'overdue' ? 'bg-red-50 text-red-700' : status === 'partial' ? 'bg-yellow-50 text-yellow-700' : ''}`}
                                    >
                                      {getInvoiceStatusLabel(status)}
                                    </Badge>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    );
                  });
                })()}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                {invoices.length > 0 ? "該当期間の請求がありません" : "請求情報がありません"}
              </div>
            )}
            <div className="mt-4">
              <Button size="sm" variant="outline" className="w-full">
                <CreditCard className="w-4 h-4 mr-1" />
                請求書発行
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* やりとりタブ */}
        <TabsContent value="communications" className="flex-1 overflow-auto p-0 m-0">
          <div className="p-4 space-y-4">
            {/* 日付範囲フィルター */}
            <div className="flex items-center gap-2 flex-wrap bg-gray-50 p-2 rounded-lg">
              <Calendar className="w-4 h-4 text-gray-500" />
              <Input
                type="date"
                value={commDateFrom}
                onChange={(e) => setCommDateFrom(e.target.value)}
                className="w-36 h-8 text-sm"
              />
              <span className="text-gray-400">〜</span>
              <Input
                type="date"
                value={commDateTo}
                onChange={(e) => setCommDateTo(e.target.value)}
                className="w-36 h-8 text-sm"
              />
              {(commDateFrom || commDateTo) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearCommDateFilter}
                  className="h-8 text-xs"
                >
                  クリア
                </Button>
              )}
            </div>

            {/* サブタブ切り替え */}
            <div className="flex gap-1 border-b">
              <button
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  commTab === "logs"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
                onClick={() => setCommTab("logs")}
              >
                対応履歴 ({filteredContactLogs.length})
              </button>
              <button
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  commTab === "chat"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
                onClick={() => setCommTab("chat")}
              >
                チャット ({filteredMessages.length})
              </button>
              <button
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  commTab === "requests"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
                onClick={() => setCommTab("requests")}
              >
                申請履歴 ({suspensionRequests.length + withdrawalRequests.length})
              </button>
            </div>

            {/* 対応履歴 */}
            {commTab === "logs" && (
              <div className="space-y-3">
                {filteredContactLogs.length > 0 ? (
                  filteredContactLogs.map((log) => (
                    <div key={log.id} className="border rounded-lg p-3 hover:bg-gray-50">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {getContactTypeLabel(log.contact_type)}
                          </Badge>
                          <Badge className={`text-xs ${getContactStatusColor(log.status)}`}>
                            {getContactStatusLabel(log.status)}
                          </Badge>
                        </div>
                        <span className="text-xs text-gray-400">
                          {new Date(log.created_at).toLocaleDateString("ja-JP")}
                        </span>
                      </div>
                      <h4 className="font-medium text-sm mb-1">{log.subject}</h4>
                      <p className="text-xs text-gray-600 whitespace-pre-wrap">{log.content}</p>
                      {log.handled_by_name && (
                        <p className="text-xs text-gray-400 mt-2">対応者: {log.handled_by_name}</p>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="text-center text-gray-500 py-8 text-sm">
                    {contactLogs.length === 0
                      ? "対応履歴がありません"
                      : "該当する期間の対応履歴がありません"}
                  </div>
                )}
              </div>
            )}

            {/* チャット履歴 */}
            {commTab === "chat" && (
              <div className="space-y-2 max-h-[60vh] overflow-y-auto border rounded-lg p-2 bg-gray-50">
                {filteredMessages.length > 0 ? (
                  filteredMessages.map((msg: any) => {
                    const isGuardian = !!msg.sender_guardian_id || !!msg.sender_guardian_name || msg.sender_type === "GUARDIAN";
                    const isBot = msg.is_bot_message || msg.sender_type === "BOT";
                    const senderLabel = isBot
                      ? "ボット"
                      : isGuardian
                      ? (msg.sender_guardian_name || msg.guardian_name || "保護者")
                      : (msg.sender_name || "スタッフ");

                    return (
                      <div
                        key={msg.id}
                        className={`p-3 rounded-lg text-sm ${
                          isGuardian
                            ? "bg-blue-100 ml-0 mr-12"
                            : isBot
                            ? "bg-gray-200 ml-12 mr-0"
                            : "bg-green-100 ml-12 mr-0"
                        }`}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-xs font-medium text-gray-600">
                            {senderLabel}
                          </span>
                          <span className="text-xs text-gray-400">
                            {new Date(msg.created_at || msg.timestamp).toLocaleString("ja-JP", {
                              month: "numeric",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                        <p className="text-gray-800 whitespace-pre-wrap">{msg.content}</p>
                        {msg.attachment_name && (
                          <div className="mt-1 text-xs text-blue-600">
                            添付: {msg.attachment_name}
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center text-gray-500 py-8 text-sm">
                    {messages.length === 0 && chatLogs.length === 0
                      ? "チャット履歴がありません"
                      : "該当する期間のチャットがありません"}
                  </div>
                )}
              </div>
            )}

            {/* 休会・退会申請履歴 */}
            {commTab === "requests" && (
              <div className="space-y-3">
                {(suspensionRequests.length > 0 || withdrawalRequests.length > 0) ? (
                  <>
                    {/* 休会申請 */}
                    {suspensionRequests.map((req) => (
                      <div key={req.id} className="border rounded-lg p-3 hover:bg-orange-50 border-orange-200">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge className="bg-orange-100 text-orange-800 text-xs">
                              休会申請
                            </Badge>
                            <Badge className={`text-xs ${
                              req.status === 'approved' ? 'bg-green-100 text-green-800' :
                              req.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                              req.status === 'rejected' ? 'bg-red-100 text-red-800' :
                              req.status === 'resumed' ? 'bg-blue-100 text-blue-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {req.status === 'approved' ? '承認済' :
                               req.status === 'pending' ? '申請中' :
                               req.status === 'rejected' ? '却下' :
                               req.status === 'resumed' ? '復会済' :
                               req.status === 'cancelled' ? '取消' : req.status}
                            </Badge>
                          </div>
                          <span className="text-xs text-gray-400">
                            {req.requested_at && new Date(req.requested_at).toLocaleDateString("ja-JP")}
                          </span>
                        </div>
                        <div className="text-sm text-gray-700">
                          <p>休会期間: {req.suspend_from} 〜 {req.suspend_until || '未定'}</p>
                          {req.keep_seat && <p className="text-xs text-orange-600">座席保持あり（休会費800円/月）</p>}
                          {req.reason_detail && <p className="text-xs text-gray-500 mt-1">{req.reason_detail}</p>}
                        </div>
                      </div>
                    ))}
                    {/* 退会申請 */}
                    {withdrawalRequests.map((req) => (
                      <div key={req.id} className="border rounded-lg p-3 hover:bg-red-50 border-red-200">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge className="bg-red-100 text-red-800 text-xs">
                              退会申請
                            </Badge>
                            <Badge className={`text-xs ${
                              req.status === 'approved' ? 'bg-green-100 text-green-800' :
                              req.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                              req.status === 'rejected' ? 'bg-red-100 text-red-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {req.status === 'approved' ? '承認済' :
                               req.status === 'pending' ? '申請中' :
                               req.status === 'rejected' ? '却下' :
                               req.status === 'cancelled' ? '取消' : req.status}
                            </Badge>
                          </div>
                          <span className="text-xs text-gray-400">
                            {req.requested_at && new Date(req.requested_at).toLocaleDateString("ja-JP")}
                          </span>
                        </div>
                        <div className="text-sm text-gray-700">
                          <p>退会日: {req.withdrawal_date}</p>
                          {req.last_lesson_date && <p className="text-xs">最終授業日: {req.last_lesson_date}</p>}
                          {req.reason_detail && <p className="text-xs text-gray-500 mt-1">{req.reason_detail}</p>}
                        </div>
                      </div>
                    ))}
                  </>
                ) : (
                  <div className="text-center text-gray-500 py-8 text-sm">
                    休会・退会申請履歴がありません
                  </div>
                )}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* フッターボタン */}
      <div className="border-t p-3 bg-gray-50">
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-orange-600 border-orange-300 hover:bg-orange-50"
            onClick={() => setSuspensionDialogOpen(true)}
            disabled={student.status === 'suspended' || student.status === 'withdrawn'}
          >
            <PauseCircle className="w-4 h-4 mr-1" />
            休会登録
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-red-600 border-red-300 hover:bg-red-50"
            onClick={() => setWithdrawalDialogOpen(true)}
            disabled={student.status === 'withdrawn'}
          >
            <XCircle className="w-4 h-4 mr-1" />
            退会登録
          </Button>
        </div>
      </div>

      {/* 保護者編集ダイアログ */}
      <Dialog open={guardianEditDialogOpen} onOpenChange={setGuardianEditDialogOpen}>
        <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>保護者情報の編集</DialogTitle>
            <DialogDescription>
              保護者の連絡先・住所情報を編集します。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {/* 氏名 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right">氏名</Label>
              <div className="col-span-3 flex gap-2">
                <Input
                  placeholder="姓"
                  value={guardianForm.last_name}
                  onChange={(e) => setGuardianForm({ ...guardianForm, last_name: e.target.value })}
                  className="flex-1"
                />
                <Input
                  placeholder="名"
                  value={guardianForm.first_name}
                  onChange={(e) => setGuardianForm({ ...guardianForm, first_name: e.target.value })}
                  className="flex-1"
                />
              </div>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right">氏名（カナ）</Label>
              <div className="col-span-3 flex gap-2">
                <Input
                  placeholder="セイ"
                  value={guardianForm.last_name_kana}
                  onChange={(e) => setGuardianForm({ ...guardianForm, last_name_kana: e.target.value })}
                  className="flex-1"
                />
                <Input
                  placeholder="メイ"
                  value={guardianForm.first_name_kana}
                  onChange={(e) => setGuardianForm({ ...guardianForm, first_name_kana: e.target.value })}
                  className="flex-1"
                />
              </div>
            </div>
            {/* 連絡先 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_phone" className="text-right">
                電話番号
              </Label>
              <Input
                id="guardian_phone"
                value={guardianForm.phone}
                onChange={(e) => setGuardianForm({ ...guardianForm, phone: e.target.value })}
                className="col-span-3"
                placeholder="0561-12-3456"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_mobile" className="text-right">
                携帯電話
              </Label>
              <Input
                id="guardian_mobile"
                value={guardianForm.phone_mobile}
                onChange={(e) => setGuardianForm({ ...guardianForm, phone_mobile: e.target.value })}
                className="col-span-3"
                placeholder="090-1234-5678"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_email" className="text-right">
                メールアドレス
              </Label>
              <Input
                id="guardian_email"
                type="email"
                value={guardianForm.email}
                onChange={(e) => setGuardianForm({ ...guardianForm, email: e.target.value })}
                className="col-span-3"
                placeholder="example@email.com"
              />
            </div>
            {/* 住所 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_postal" className="text-right">
                郵便番号
              </Label>
              <Input
                id="guardian_postal"
                value={guardianForm.postal_code}
                onChange={(e) => setGuardianForm({ ...guardianForm, postal_code: e.target.value })}
                className="col-span-3"
                placeholder="488-0001"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_prefecture" className="text-right">
                都道府県
              </Label>
              <Input
                id="guardian_prefecture"
                value={guardianForm.prefecture}
                onChange={(e) => setGuardianForm({ ...guardianForm, prefecture: e.target.value })}
                className="col-span-3"
                placeholder="愛知県"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_city" className="text-right">
                市区町村
              </Label>
              <Input
                id="guardian_city"
                value={guardianForm.city}
                onChange={(e) => setGuardianForm({ ...guardianForm, city: e.target.value })}
                className="col-span-3"
                placeholder="尾張旭市"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_address1" className="text-right">
                住所1
              </Label>
              <Input
                id="guardian_address1"
                value={guardianForm.address1}
                onChange={(e) => setGuardianForm({ ...guardianForm, address1: e.target.value })}
                className="col-span-3"
                placeholder="東印場町3-9-31"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_address2" className="text-right">
                住所2
              </Label>
              <Input
                id="guardian_address2"
                value={guardianForm.address2}
                onChange={(e) => setGuardianForm({ ...guardianForm, address2: e.target.value })}
                className="col-span-3"
                placeholder="建物名・部屋番号"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setGuardianEditDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleGuardianUpdate} disabled={isSubmitting}>
              {isSubmitting ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 契約編集ダイアログ */}
      <ContractEditDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        contract={editingContract}
        onSave={async (contractId, updates) => {
          if (onContractUpdate) {
            await onContractUpdate(contractId, updates);
          }
        }}
      />

      {/* 休会登録ダイアログ */}
      <Dialog open={suspensionDialogOpen} onOpenChange={setSuspensionDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>休会登録</DialogTitle>
            <DialogDescription>
              {lastName} {firstName}さんの休会を登録します。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="suspend_from" className="text-right">
                休会開始日
              </Label>
              <Input
                id="suspend_from"
                type="date"
                value={suspensionForm.suspend_from}
                onChange={(e) => setSuspensionForm({ ...suspensionForm, suspend_from: e.target.value })}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="suspend_until" className="text-right">
                休会終了日
              </Label>
              <Input
                id="suspend_until"
                type="date"
                value={suspensionForm.suspend_until}
                onChange={(e) => setSuspensionForm({ ...suspensionForm, suspend_until: e.target.value })}
                className="col-span-3"
                placeholder="未定の場合は空欄"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right">座席保持</Label>
              <div className="col-span-3 flex items-center space-x-2">
                <Checkbox
                  id="keep_seat"
                  checked={suspensionForm.keep_seat}
                  onCheckedChange={(checked) => setSuspensionForm({ ...suspensionForm, keep_seat: !!checked })}
                />
                <label htmlFor="keep_seat" className="text-sm text-gray-600">
                  座席を保持する（休会費800円/月が発生）
                </label>
              </div>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="reason" className="text-right">
                理由
              </Label>
              <select
                id="reason"
                value={suspensionForm.reason}
                onChange={(e) => setSuspensionForm({ ...suspensionForm, reason: e.target.value })}
                className="col-span-3 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="travel">旅行・帰省</option>
                <option value="illness">病気・怪我</option>
                <option value="exam">受験準備</option>
                <option value="schedule">スケジュール都合</option>
                <option value="other">その他</option>
              </select>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="reason_detail" className="text-right">
                詳細
              </Label>
              <Textarea
                id="reason_detail"
                value={suspensionForm.reason_detail}
                onChange={(e) => setSuspensionForm({ ...suspensionForm, reason_detail: e.target.value })}
                className="col-span-3"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSuspensionDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleSuspensionSubmit} disabled={isSubmitting}>
              {isSubmitting ? '処理中...' : '休会登録'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 退会登録ダイアログ */}
      <Dialog open={withdrawalDialogOpen} onOpenChange={setWithdrawalDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>退会登録</DialogTitle>
            <DialogDescription>
              {lastName} {firstName}さんの退会を登録します。この操作は取り消せません。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="withdrawal_date" className="text-right">
                退会日
              </Label>
              <Input
                id="withdrawal_date"
                type="date"
                value={withdrawalForm.withdrawal_date}
                onChange={(e) => setWithdrawalForm({ ...withdrawalForm, withdrawal_date: e.target.value })}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="last_lesson_date" className="text-right">
                最終授業日
              </Label>
              <Input
                id="last_lesson_date"
                type="date"
                value={withdrawalForm.last_lesson_date}
                onChange={(e) => setWithdrawalForm({ ...withdrawalForm, last_lesson_date: e.target.value })}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="withdrawal_reason" className="text-right">
                理由
              </Label>
              <select
                id="withdrawal_reason"
                value={withdrawalForm.reason}
                onChange={(e) => setWithdrawalForm({ ...withdrawalForm, reason: e.target.value })}
                className="col-span-3 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="moving">転居</option>
                <option value="school_change">学校変更</option>
                <option value="graduation">卒業</option>
                <option value="schedule">スケジュール都合</option>
                <option value="financial">経済的理由</option>
                <option value="satisfaction">満足度</option>
                <option value="other_school">他塾への変更</option>
                <option value="other">その他</option>
              </select>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="withdrawal_reason_detail" className="text-right">
                詳細
              </Label>
              <Textarea
                id="withdrawal_reason_detail"
                value={withdrawalForm.reason_detail}
                onChange={(e) => setWithdrawalForm({ ...withdrawalForm, reason_detail: e.target.value })}
                className="col-span-3"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setWithdrawalDialogOpen(false)}>
              キャンセル
            </Button>
            <Button variant="destructive" onClick={handleWithdrawalSubmit} disabled={isSubmitting}>
              {isSubmitting ? '処理中...' : '退会登録'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 新規契約登録ダイアログ */}
      <NewContractDialog
        open={newContractDialogOpen}
        onOpenChange={setNewContractDialogOpen}
        student={student}
        guardian={parents[0]}
        onSuccess={() => {
          // 契約一覧を再読み込み（親コンポーネントで処理）
          window.location.reload();
        }}
      />
    </div>
  );
}
