"use client";

import { useState, useMemo } from "react";
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
} from "lucide-react";
import { ContractEditDialog } from "./ContractEditDialog";

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

  // 契約フィルター用の年月選択
  const [contractYear, setContractYear] = useState<string>("all");
  const [contractMonth, setContractMonth] = useState<string>("all");

  // 請求フィルター用の年月選択
  const [invoiceYear, setInvoiceYear] = useState<string>("all");
  const [invoiceMonth, setInvoiceMonth] = useState<string>("all");

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
      const billingMonth = invoice.billingMonth || invoice.billing_month || "";
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
          <Badge className={getStatusColor(student.status)}>
            {getStatusLabel(student.status)}
          </Badge>
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
                      <div className="flex items-start gap-3 mb-4">
                        <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
                          <User className="w-6 h-6 text-gray-500" />
                        </div>
                        <div>
                          <h3 className="font-bold text-lg">{gLastName} {gFirstName}</h3>
                          <p className="text-sm text-gray-500">{gLastNameKana} {gFirstNameKana}</p>
                          <p className="text-xs text-gray-400">No. {gNo}</p>
                        </div>
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
                  const monthlyTotal = contract.monthly_total || contract.monthlyTotal || 0;
                  const discountApplied = contract.discount_applied || contract.discountApplied || 0;
                  const discountType = contract.discount_type || contract.discountType || "";
                  const dayOfWeek = contract.day_of_week || contract.dayOfWeek;
                  const startTime = contract.start_time || contract.startTime || "";

                  // 生徒商品（明細）を取得
                  const studentItems = contract.student_items || contract.studentItems || [];

                  // 割引情報を取得
                  const discounts = contract.discounts || [];
                  const discountTotal = contract.discount_total || contract.discountTotal || 0;

                  // 請求月を取得（StudentItemから）
                  const billingMonths = Array.from(new Set(studentItems.map((item: { billing_month?: string; billingMonth?: string }) =>
                    item.billing_month || item.billingMonth
                  ).filter(Boolean)));
                  const billingMonthLabel = billingMonths.length > 0 ? billingMonths.join(", ") : "";

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
                                quantity?: number;
                                unit_price?: number | string;
                                unitPrice?: number | string;
                                final_price?: number | string;
                                finalPrice?: number | string;
                              }, idx: number) => {
                                const itemName = item.product_name || item.productName || "-";
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
              <Button size="sm" variant="outline" className="w-full">
                <FileText className="w-4 h-4 mr-1" />
                新規契約登録
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* 請求タブ */}
        <TabsContent value="billing" className="flex-1 overflow-auto p-0 m-0">
          <div className="p-4">
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
          <div className="p-4">
            {/* 対応履歴 */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                <History className="w-4 h-4 mr-1" />
                対応履歴
              </h3>
              {contactLogs.length > 0 ? (
                <div className="space-y-3">
                  {contactLogs.map((log) => (
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
                      <p className="text-xs text-gray-600 line-clamp-2">{log.content}</p>
                      {log.handled_by_name && (
                        <p className="text-xs text-gray-400 mt-2">対応者: {log.handled_by_name}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-gray-500 py-4 text-sm">
                  対応履歴がありません
                </div>
              )}
            </div>

            {/* チャット履歴 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                <MessageCircle className="w-4 h-4 mr-1" />
                チャット履歴
              </h3>
              {messages.length > 0 ? (
                <div className="space-y-2 max-h-96 overflow-y-auto border rounded-lg p-2 bg-gray-50">
                  {messages.map((msg) => {
                    const isGuardian = !!msg.sender_guardian_id || !!msg.sender_guardian_name;
                    const isBot = msg.is_bot_message;
                    const senderLabel = isBot
                      ? "ボット"
                      : isGuardian
                      ? (msg.sender_guardian_name || "保護者")
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
                            {new Date(msg.created_at).toLocaleString("ja-JP", {
                              year: "numeric",
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
                        {msg.is_edited && (
                          <span className="text-xs text-gray-400 ml-2">(編集済み)</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : chatLogs.length > 0 ? (
                <div className="space-y-2 max-h-96 overflow-y-auto border rounded-lg p-2 bg-gray-50">
                  {chatLogs.map((chat) => (
                    <div
                      key={chat.id}
                      className={`p-3 rounded-lg text-sm ${
                        chat.sender_type === "GUARDIAN"
                          ? "bg-blue-100 ml-0 mr-12"
                          : chat.sender_type === "BOT"
                          ? "bg-gray-200 ml-12 mr-0"
                          : "bg-green-100 ml-12 mr-0"
                      }`}
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-medium text-gray-600">
                          {getSenderTypeLabel(chat.sender_type)}
                          {chat.guardian_name && ` - ${chat.guardian_name}`}
                        </span>
                        <span className="text-xs text-gray-400">
                          {new Date(chat.timestamp).toLocaleString("ja-JP", {
                            year: "numeric",
                            month: "numeric",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                      <p className="text-gray-800 whitespace-pre-wrap">{chat.content}</p>
                      {(chat.brand_name || chat.school_name) && (
                        <div className="mt-1 text-xs text-gray-500">
                          {chat.brand_name && <span className="mr-2">{chat.brand_name}</span>}
                          {chat.school_name && <span>{chat.school_name}</span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-gray-500 py-4 text-sm">
                  チャット履歴がありません
                </div>
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* フッターボタン */}
      <div className="border-t p-3 bg-gray-50">
        <div className="flex gap-2">
          <Button size="sm" variant="outline" className="flex-1 text-orange-600 border-orange-300 hover:bg-orange-50">
            <PauseCircle className="w-4 h-4 mr-1" />
            休会登録
          </Button>
          <Button size="sm" variant="outline" className="flex-1 text-red-600 border-red-300 hover:bg-red-50">
            <XCircle className="w-4 h-4 mr-1" />
            退会登録
          </Button>
        </div>
      </div>

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
    </div>
  );
}
