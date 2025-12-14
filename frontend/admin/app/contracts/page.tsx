"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  PauseCircle,
  Package,
  Percent,
  History,
  Calendar,
} from "lucide-react";
import {
  getContracts,
  getBrands,
  getCampuses,
  getAllStudentItems,
  getAllStudentDiscounts,
  getOperationHistory,
  type Contract,
  type Brand,
  type School,
  type StudentItem,
  type StudentDiscount,
  type OperationHistoryItem,
} from "@/lib/api/staff";
import ContractAgent from "@/components/contract-agent";

// 操作種別の設定
const operationTypeConfig: Record<string, { label: string; color: string }> = {
  discount_add: { label: "割引追加", color: "bg-green-100 text-green-700" },
  discount_update: { label: "割引変更", color: "bg-blue-100 text-blue-700" },
  discount_delete: { label: "割引削除", color: "bg-red-100 text-red-700" },
  contract_created: { label: "契約登録", color: "bg-green-100 text-green-700" },
  contract_cancelled: { label: "契約解約", color: "bg-red-100 text-red-700" },
  contract_paused: { label: "休会", color: "bg-orange-100 text-orange-700" },
  contract_resumed: { label: "再開", color: "bg-green-100 text-green-700" },
  school_changed: { label: "校舎変更", color: "bg-blue-100 text-blue-700" },
  course_changed: { label: "クラス変更", color: "bg-blue-100 text-blue-700" },
  debit_success: { label: "引落成功", color: "bg-green-100 text-green-700" },
  debit_failed: { label: "引落失敗", color: "bg-red-100 text-red-700" },
  transfer_confirmed: { label: "振込確認", color: "bg-green-100 text-green-700" },
  transfer_pending: { label: "振込未着", color: "bg-yellow-100 text-yellow-700" },
};

// ステータス設定
const statusConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  active: { label: "有効", color: "bg-green-100 text-green-700", icon: <CheckCircle className="w-3 h-3" /> },
  enrolled: { label: "在籍", color: "bg-green-100 text-green-700", icon: <CheckCircle className="w-3 h-3" /> },
  pending: { label: "申請中", color: "bg-yellow-100 text-yellow-700", icon: <Clock className="w-3 h-3" /> },
  suspended: { label: "休会", color: "bg-orange-100 text-orange-700", icon: <PauseCircle className="w-3 h-3" /> },
  cancelled: { label: "解約", color: "bg-red-100 text-red-700", icon: <XCircle className="w-3 h-3" /> },
  expired: { label: "終了", color: "bg-gray-100 text-gray-500", icon: <FileText className="w-3 h-3" /> },
};

// Helper to get student display name
function getStudentName(student: Contract["student"]): string {
  if (!student) return "-";
  return student.name || student.full_name || `${student.last_name || ""}${student.first_name || ""}` || "-";
}

// Helper to format date
function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "-";
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
  } catch {
    return "-";
  }
}

// Helper to format datetime
function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "-";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "-";
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
  } catch {
    return "-";
  }
}

export default function ContractsPage() {
  const [activeTab, setActiveTab] = useState("items");  // 最初は生徒商品タブ（高速）
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [studentItems, setStudentItems] = useState<StudentItem[]>([]);
  const [studentDiscounts, setStudentDiscounts] = useState<StudentDiscount[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [brandFilter, setBrandFilter] = useState<string>("all");
  const [schoolFilter, setSchoolFilter] = useState<string>("all");

  // Year/Month filter
  const currentDate = new Date();
  const [filterYear, setFilterYear] = useState<string>(currentDate.getFullYear().toString());
  const [filterMonth, setFilterMonth] = useState<string>("all");

  // Operation history
  const [operationHistory, setOperationHistory] = useState<OperationHistoryItem[]>([]);

  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // タブごとのデータロード状態
  const [tabLoading, setTabLoading] = useState(false);

  // 初期ロード
  useEffect(() => {
    loadBasicData();
  }, []);

  // フィルタ変更時にデータ再読み込み（年月・ブランド・校舎）
  useEffect(() => {
    // 初期ロード完了後のみ再読み込み
    if (!loading) {
      loadTabData(activeTab, true);
    }
  }, [filterYear, filterMonth, brandFilter, schoolFilter]);

  async function loadBasicData() {
    setLoading(true);
    try {
      console.log("[ContractsPage] Loading basic data...");

      // 基本データ（ブランド、校舎）は常にロード
      const loadBrands = getBrands().then(data => {
        console.log("[ContractsPage] Brands loaded:", data.length);
        setBrands(data);
        return data;
      }).catch(err => {
        console.error("[ContractsPage] Failed to load brands:", err);
        return [];
      });

      const loadSchools = getCampuses().then(data => {
        console.log("[ContractsPage] Schools loaded:", data.length);
        setSchools(data);
        return data;
      }).catch(err => {
        console.error("[ContractsPage] Failed to load schools:", err);
        return [];
      });

      await Promise.all([loadBrands, loadSchools]);

      // 最初のタブのデータをロード
      await loadTabData(activeTab, true);

      console.log("[ContractsPage] Initial data loading complete");
    } catch (error) {
      console.error("[ContractsPage] Error loading data:", error);
    } finally {
      setLoading(false);
    }
  }

  // タブごとのデータをロード（フィルタ付き）
  async function loadTabData(tab: string, forceReload = false) {
    setTabLoading(true);
    console.log(`[ContractsPage] Loading data for tab: ${tab}, filters:`, {
      year: filterYear, month: filterMonth, brand: brandFilter, school: schoolFilter
    });

    const filters = {
      year: filterYear,
      month: filterMonth,
      brand_id: brandFilter !== "all" ? brandFilter : undefined,
      school_id: schoolFilter !== "all" ? schoolFilter : undefined,
    };

    try {
      switch (tab) {
        case "contracts":
          const contractsData = await getContracts(filters).catch(err => {
            console.error("[ContractsPage] Failed to load contracts:", err);
            return [];
          });
          setContracts(contractsData);
          break;

        case "items":
          const itemsData = await getAllStudentItems(filters).catch(err => {
            console.error("[ContractsPage] Failed to load student items:", err);
            return [];
          });
          setStudentItems(itemsData);
          break;

        case "discounts":
          const discountsData = await getAllStudentDiscounts(filters).catch(err => {
            console.error("[ContractsPage] Failed to load discounts:", err);
            return [];
          });
          setStudentDiscounts(discountsData);
          break;

        case "history":
          const historyData = await getOperationHistory(filters).catch(err => {
            console.error("[ContractsPage] Failed to load operation history:", err);
            return [];
          });
          setOperationHistory(historyData);
          break;
      }
    } finally {
      setTabLoading(false);
    }
  }

  // 年月フィルターヘルパー関数
  const filterByYearMonth = (dateStr: string | null | undefined): boolean => {
    if (!dateStr) return filterMonth === "all";
    try {
      const date = new Date(dateStr);
      const year = date.getFullYear().toString();
      const month = (date.getMonth() + 1).toString();
      if (filterYear !== "all" && year !== filterYear) return false;
      if (filterMonth !== "all" && month !== filterMonth) return false;
      return true;
    } catch {
      return false;
    }
  };

  // フィルタリング - 契約（年月・ブランド・校舎はバックエンドでフィルタ済み）
  const filteredContracts = useMemo(() => {
    let result = [...contracts];

    // ステータスフィルタ（フロントエンドのみ）
    if (statusFilter !== "all") {
      result = result.filter((c) => c.status === statusFilter);
    }

    // 検索フィルタ
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter((c) => {
        const studentName = getStudentName(c.student).toLowerCase();
        const contractNo = (c.contract_no || "").toLowerCase();
        const brandName = (c.brand?.brand_name || c.brand?.name || "").toLowerCase();
        return studentName.includes(query) || contractNo.includes(query) || brandName.includes(query);
      });
    }

    result.sort((a, b) => {
      const aDate = a.start_date ? new Date(a.start_date).getTime() : 0;
      const bDate = b.start_date ? new Date(b.start_date).getTime() : 0;
      return bDate - aDate;
    });

    return result;
  }, [contracts, statusFilter, searchQuery]);

  // フィルタリング - 生徒商品（年月・ブランド・校舎はバックエンドでフィルタ済み）
  const filteredStudentItems = useMemo(() => {
    let result = [...studentItems];

    // 検索フィルタ
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter((item) => {
        const studentName = (item.student_name || "").toLowerCase();
        const productName = (item.product_name || "").toLowerCase();
        return studentName.includes(query) || productName.includes(query);
      });
    }

    result.sort((a, b) => {
      const aDate = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bDate = b.created_at ? new Date(b.created_at).getTime() : 0;
      return bDate - aDate;
    });

    return result;
  }, [studentItems, searchQuery]);

  // フィルタリング - 生徒割引（年月・ブランドはバックエンドでフィルタ済み）
  const filteredStudentDiscounts = useMemo(() => {
    let result = [...studentDiscounts];

    // ステータスフィルタ（active/inactive）
    if (statusFilter !== "all" && statusFilter === "active") {
      result = result.filter((d) => d.is_active);
    } else if (statusFilter === "inactive") {
      result = result.filter((d) => !d.is_active);
    }

    // 検索フィルタ
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter((d) => {
        const studentName = (d.student_name || "").toLowerCase();
        const discountName = (d.discount_name || "").toLowerCase();
        return studentName.includes(query) || discountName.includes(query);
      });
    }

    result.sort((a, b) => {
      const aDate = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bDate = b.created_at ? new Date(b.created_at).getTime() : 0;
      return bDate - aDate;
    });

    return result;
  }, [studentDiscounts, statusFilter, searchQuery]);

  // フィルタリング - 操作履歴（年月はバックエンドでフィルタ済み）
  const filteredOperationHistory = useMemo(() => {
    let result = [...operationHistory];

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter((h) => {
        const studentName = (h.student_name || "").toLowerCase();
        const content = (h.content || "").toLowerCase();
        return studentName.includes(query) || content.includes(query);
      });
    }

    result.sort((a, b) => {
      const aDate = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bDate = b.created_at ? new Date(b.created_at).getTime() : 0;
      return bDate - aDate;
    });

    return result;
  }, [operationHistory, searchQuery]);

  // ページネーション
  const getCurrentData = () => {
    switch (activeTab) {
      case "contracts":
        return filteredContracts;
      case "items":
        return filteredStudentItems;
      case "discounts":
        return filteredStudentDiscounts;
      case "history":
        return filteredOperationHistory;
      default:
        return [];
    }
  };

  // 年の選択肢を生成
  const yearOptions = useMemo(() => {
    const years: string[] = [];
    const currentYear = new Date().getFullYear();
    for (let y = currentYear; y >= currentYear - 5; y--) {
      years.push(y.toString());
    }
    return years;
  }, []);

  const currentData = getCurrentData();
  const totalPages = Math.ceil(currentData.length / pageSize);
  const paginatedData = currentData.slice((page - 1) * pageSize, page * pageSize);
  const startResult = currentData.length > 0 ? (page - 1) * pageSize + 1 : 0;
  const endResult = Math.min(page * pageSize, currentData.length);

  function handleSearch() {
    setPage(1);
  }

  function handleFilterChange() {
    setPage(1);
  }

  function handleTabChange(tab: string) {
    setActiveTab(tab);
    setPage(1);
    // タブのデータをロード（年月フィルタ付きで常に再読み込み）
    loadTabData(tab, true);
  }

  return (
    <ThreePaneLayout>
      <div className="p-6 h-full flex flex-col">
        {/* ヘッダー */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">契約管理</h1>
          <p className="text-gray-600">
            最新100件を表示中（フィルタで絞り込み可能）
          </p>
        </div>

        {/* タブ */}
        <Tabs value={activeTab} onValueChange={handleTabChange} className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-4 mb-4">
            <TabsTrigger value="contracts" className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              契約 ({filteredContracts.length})
            </TabsTrigger>
            <TabsTrigger value="items" className="flex items-center gap-2">
              <Package className="w-4 h-4" />
              生徒商品 ({filteredStudentItems.length})
            </TabsTrigger>
            <TabsTrigger value="discounts" className="flex items-center gap-2">
              <Percent className="w-4 h-4" />
              割引 ({filteredStudentDiscounts.length})
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center gap-2">
              <History className="w-4 h-4" />
              操作履歴 ({filteredOperationHistory.length})
            </TabsTrigger>
          </TabsList>

          {/* フィルター */}
          <div className="space-y-4 mb-6">
            {/* 年月フィルター */}
            <div className="flex gap-3 items-center">
              <Calendar className="w-5 h-5 text-gray-400" />
              <Select value={filterYear} onValueChange={(value) => { setFilterYear(value); setPage(1); }}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="年" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全期間</SelectItem>
                  {yearOptions.map((year) => (
                    <SelectItem key={year} value={year}>{year}年</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filterMonth} onValueChange={(value) => { setFilterMonth(value); setPage(1); }}>
                <SelectTrigger className="w-28">
                  <SelectValue placeholder="月" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全月</SelectItem>
                  {[1,2,3,4,5,6,7,8,9,10,11,12].map((month) => (
                    <SelectItem key={month} value={month.toString()}>{month}月</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <Input
                  type="text"
                  placeholder="生徒名、商品名、割引名で検索..."
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

            <div className="flex gap-3 items-center">
              {activeTab === "contracts" && (
                <Select
                  value={statusFilter}
                  onValueChange={(v) => {
                    setStatusFilter(v);
                    handleFilterChange();
                  }}
                >
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="ステータス" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全ステータス</SelectItem>
                    <SelectItem value="active">有効</SelectItem>
                    <SelectItem value="enrolled">在籍</SelectItem>
                    <SelectItem value="pending">申請中</SelectItem>
                    <SelectItem value="suspended">休会</SelectItem>
                    <SelectItem value="cancelled">解約</SelectItem>
                    <SelectItem value="expired">終了</SelectItem>
                  </SelectContent>
                </Select>
              )}

              {activeTab === "discounts" && (
                <Select
                  value={statusFilter}
                  onValueChange={(v) => {
                    setStatusFilter(v);
                    handleFilterChange();
                  }}
                >
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="状態" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全て</SelectItem>
                    <SelectItem value="active">有効</SelectItem>
                    <SelectItem value="inactive">無効</SelectItem>
                  </SelectContent>
                </Select>
              )}

              <Select
                value={brandFilter}
                onValueChange={(v) => {
                  setBrandFilter(v);
                  handleFilterChange();
                }}
              >
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="ブランド" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全ブランド</SelectItem>
                  {brands.map((brand) => (
                    <SelectItem key={brand.id} value={brand.id}>
                      {brand.brand_name || brand.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select
                value={schoolFilter}
                onValueChange={(v) => {
                  setSchoolFilter(v);
                  handleFilterChange();
                }}
              >
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="校舎" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全校舎</SelectItem>
                  {schools.map((school) => (
                    <SelectItem key={school.id} value={school.id}>
                      {school.school_name || school.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* テーブル */}
          <Card className="flex-1 overflow-hidden">
            {(loading || tabLoading) ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-gray-500">読み込み中...</div>
              </div>
            ) : (
              <>
                {/* 契約タブ */}
                <TabsContent value="contracts" className="h-full m-0">
                  {paginatedData.length > 0 ? (
                    <div className="overflow-auto h-full">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[160px]">更新日時</TableHead>
                            <TableHead className="w-[120px]">契約番号</TableHead>
                            <TableHead>生徒名</TableHead>
                            <TableHead>ブランド</TableHead>
                            <TableHead>校舎</TableHead>
                            <TableHead className="w-[100px]">開始</TableHead>
                            <TableHead className="w-[100px]">終了</TableHead>
                            <TableHead className="w-[100px]">ステータス</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(paginatedData as Contract[]).map((contract) => {
                            const status = statusConfig[contract.status || ""] || {
                              label: contract.status || "-",
                              color: "bg-gray-100 text-gray-700",
                              icon: <FileText className="w-3 h-3" />,
                            };
                            // camelCase/snake_case両対応
                            const studentId = typeof contract.student === 'string' ? contract.student : contract.student?.id;
                            const studentName = (contract as any).studentName || (contract as any).student_name || getStudentName(contract.student);
                            const brandName = (contract as any).brandName || (contract as any).brand_name || contract.brand?.brand_name || "-";
                            const schoolName = (contract as any).schoolName || (contract as any).school_name || contract.school?.school_name || "-";
                            const contractNo = (contract as any).contractNo || (contract as any).contract_no || "-";
                            const startDate = (contract as any).startDate || (contract as any).start_date;
                            const endDate = (contract as any).endDate || (contract as any).end_date;
                            const updatedAt = (contract as any).updatedAt || (contract as any).updated_at;
                            const createdAt = (contract as any).createdAt || (contract as any).created_at;

                            return (
                              <TableRow key={contract.id} className="cursor-pointer hover:bg-gray-50">
                                <TableCell className="text-sm text-gray-500">
                                  {formatDateTime(updatedAt || createdAt)}
                                </TableCell>
                                <TableCell className="font-mono text-sm">
                                  {contractNo}
                                </TableCell>
                                <TableCell className="font-medium">
                                  {studentId ? (
                                    <Link
                                      href={`/students?id=${studentId}`}
                                      className="text-blue-600 hover:text-blue-800 hover:underline"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {studentName || "-"}
                                    </Link>
                                  ) : (
                                    studentName || "-"
                                  )}
                                </TableCell>
                                <TableCell>{brandName}</TableCell>
                                <TableCell>{schoolName}</TableCell>
                                <TableCell>{formatDate(startDate)}</TableCell>
                                <TableCell>{formatDate(endDate)}</TableCell>
                                <TableCell>
                                  <Badge className={`${status.color} flex items-center gap-1 w-fit`}>
                                    {status.icon}
                                    {status.label}
                                  </Badge>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-gray-500">契約が見つかりませんでした</div>
                    </div>
                  )}
                </TabsContent>

                {/* 生徒商品タブ */}
                <TabsContent value="items" className="h-full m-0">
                  {paginatedData.length > 0 ? (
                    <div className="overflow-auto h-full">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[160px]">作成日時</TableHead>
                            <TableHead>生徒名</TableHead>
                            <TableHead>商品</TableHead>
                            <TableHead>ブランド</TableHead>
                            <TableHead>校舎</TableHead>
                            <TableHead className="w-[100px]">請求月</TableHead>
                            <TableHead className="w-[80px] text-right">数量</TableHead>
                            <TableHead className="w-[120px] text-right">確定金額</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(paginatedData as StudentItem[]).map((item) => {
                            // camelCase/snake_case両対応
                            const studentId = typeof item.student === 'string' ? item.student : (item as any).student_id || (item.student as any)?.id;
                            const createdAt = (item as any).createdAt || item.created_at;
                            const studentName = (item as any).studentName || item.student_name || "-";
                            const productName = (item as any).productName || item.product_name || "-";
                            const brandName = (item as any).brandName || item.brand_name || "-";
                            const schoolName = (item as any).schoolName || item.school_name || "-";
                            const billingMonth = (item as any).billingMonth || item.billing_month || "-";
                            const finalPrice = (item as any).finalPrice || item.final_price;

                            return (
                              <TableRow key={item.id} className="cursor-pointer hover:bg-gray-50">
                                <TableCell className="text-sm text-gray-500">
                                  {formatDateTime(createdAt)}
                                </TableCell>
                                <TableCell className="font-medium">
                                  {studentId ? (
                                    <Link
                                      href={`/students?id=${studentId}`}
                                      className="text-blue-600 hover:text-blue-800 hover:underline"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {studentName}
                                    </Link>
                                  ) : (
                                    studentName
                                  )}
                                </TableCell>
                                <TableCell>{productName}</TableCell>
                                <TableCell>{brandName}</TableCell>
                                <TableCell>{schoolName}</TableCell>
                                <TableCell>{billingMonth}</TableCell>
                                <TableCell className="text-right">{item.quantity}</TableCell>
                                <TableCell className="text-right">
                                  {finalPrice != null ? `¥${Number(finalPrice).toLocaleString()}` : "-"}
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-gray-500">生徒商品が見つかりませんでした</div>
                    </div>
                  )}
                </TabsContent>

                {/* 割引タブ */}
                <TabsContent value="discounts" className="h-full m-0">
                  {paginatedData.length > 0 ? (
                    <div className="overflow-auto h-full">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[160px]">作成日時</TableHead>
                            <TableHead>生徒名</TableHead>
                            <TableHead>割引名</TableHead>
                            <TableHead className="w-[120px] text-right">金額</TableHead>
                            <TableHead>ブランド</TableHead>
                            <TableHead className="w-[100px]">開始日</TableHead>
                            <TableHead className="w-[100px]">終了日</TableHead>
                            <TableHead className="w-[80px]">状態</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(paginatedData as StudentDiscount[]).map((discount) => {
                            // camelCase/snake_case両対応
                            const studentId = typeof discount.student === 'string' ? discount.student : (discount as any).student_id || (discount.student as any)?.id;
                            const createdAt = (discount as any).createdAt || discount.created_at;
                            const studentName = (discount as any).studentName || discount.student_name || "-";
                            const discountName = (discount as any).discountName || discount.discount_name || "-";
                            const brandName = (discount as any).brandName || discount.brand_name || "-";
                            const startDate = (discount as any).startDate || discount.start_date;
                            const endDate = (discount as any).endDate || discount.end_date;
                            const discountUnit = (discount as any).discountUnit || discount.discount_unit;
                            const isActive = (discount as any).isActive ?? discount.is_active;

                            return (
                              <TableRow key={discount.id} className="cursor-pointer hover:bg-gray-50">
                                <TableCell className="text-sm text-gray-500">
                                  {formatDateTime(createdAt)}
                                </TableCell>
                                <TableCell className="font-medium">
                                  {studentId ? (
                                    <Link
                                      href={`/students?id=${studentId}`}
                                      className="text-blue-600 hover:text-blue-800 hover:underline"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {studentName}
                                    </Link>
                                  ) : (
                                    studentName
                                  )}
                                </TableCell>
                                <TableCell>{discountName}</TableCell>
                                <TableCell className="text-right">
                                  {discount.amount != null
                                    ? `${discountUnit === "percent" ? "" : "¥"}${Number(discount.amount).toLocaleString()}${discountUnit === "percent" ? "%" : ""}`
                                    : "-"}
                                </TableCell>
                                <TableCell>{brandName}</TableCell>
                                <TableCell>{formatDate(startDate)}</TableCell>
                                <TableCell>{formatDate(endDate)}</TableCell>
                                <TableCell>
                                  <Badge className={isActive ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}>
                                    {isActive ? "有効" : "無効"}
                                  </Badge>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-gray-500">割引が見つかりませんでした</div>
                    </div>
                  )}
                </TabsContent>

                {/* 操作履歴タブ */}
                <TabsContent value="history" className="h-full m-0">
                  {paginatedData.length > 0 ? (
                    <div className="overflow-auto h-full">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[160px]">日時</TableHead>
                            <TableHead className="w-[120px]">種別</TableHead>
                            <TableHead>生徒/保護者</TableHead>
                            <TableHead>内容</TableHead>
                            <TableHead className="w-[120px] text-right">金額</TableHead>
                            <TableHead className="w-[100px]">ステータス</TableHead>
                            <TableHead className="w-[100px]">担当者</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(paginatedData as OperationHistoryItem[]).map((item) => {
                            const typeConfig = operationTypeConfig[item.type] || { label: item.type_display || item.type, color: "bg-gray-100 text-gray-700" };
                            return (
                              <TableRow key={item.id} className="cursor-pointer hover:bg-gray-50">
                                <TableCell className="text-sm text-gray-500">
                                  {formatDateTime(item.created_at)}
                                </TableCell>
                                <TableCell>
                                  <Badge className={typeConfig.color}>
                                    {typeConfig.label}
                                  </Badge>
                                </TableCell>
                                <TableCell className="font-medium">
                                  {item.student_id && item.student_name ? (
                                    <Link
                                      href={`/students?id=${item.student_id}`}
                                      className="text-blue-600 hover:text-blue-800 hover:underline"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {item.student_name}
                                    </Link>
                                  ) : item.guardian_id && item.guardian_name ? (
                                    <Link
                                      href={`/parents?id=${item.guardian_id}`}
                                      className="text-blue-600 hover:text-blue-800 hover:underline"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {item.guardian_name}
                                    </Link>
                                  ) : (
                                    item.student_name || item.guardian_name || "-"
                                  )}
                                </TableCell>
                                <TableCell>{item.content}</TableCell>
                                <TableCell className="text-right">
                                  {item.amount != null ? `¥${Number(item.amount).toLocaleString()}` : "-"}
                                </TableCell>
                                <TableCell>
                                  {item.status_display && (
                                    <Badge className={
                                      item.status === "success" ? "bg-green-100 text-green-700" :
                                      item.status === "failed" ? "bg-red-100 text-red-700" :
                                      item.status === "pending" ? "bg-yellow-100 text-yellow-700" :
                                      "bg-gray-100 text-gray-700"
                                    }>
                                      {item.status_display}
                                    </Badge>
                                  )}
                                </TableCell>
                                <TableCell className="text-sm text-gray-500">
                                  {item.operator || "-"}
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-gray-500">操作履歴が見つかりませんでした</div>
                    </div>
                  )}
                </TabsContent>
              </>
            )}
          </Card>

          {/* ページネーション */}
          {totalPages > 1 && (
            <div className="flex flex-col items-center gap-2 pt-4 border-t mt-4">
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                >
                  <ChevronLeft className="w-4 h-4" />
                  前へ
                </Button>
                <span className="text-sm text-gray-600">
                  {page} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
                  disabled={page === totalPages}
                >
                  次へ
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
              <p className="text-sm text-gray-500">
                {startResult}〜{endResult}件 / 全{currentData.length.toLocaleString()}件
              </p>
            </div>
          )}
        </Tabs>

        {/* 契約管理エージェント */}
        <ContractAgent
          activeTab={activeTab}
          onRefreshData={loadBasicData}
          onExportCSV={async (type) => {
            // CSVエクスポート - 現在のフィルタ済みデータをCSV化
            let data: any[] = [];
            let filename = "";

            if (type === "contracts") {
              data = filteredContracts;
              filename = "contracts";
            } else if (type === "items") {
              data = filteredStudentItems;
              filename = "student_items";
            } else if (type === "discounts") {
              data = filteredStudentDiscounts;
              filename = "student_discounts";
            }

            if (data.length === 0) return null;

            // CSVヘッダーと行を生成
            const headers = Object.keys(data[0]);
            const csvContent = [
              headers.join(","),
              ...data.map(row =>
                headers.map(h => {
                  const val = (row as any)[h];
                  if (val === null || val === undefined) return "";
                  if (typeof val === "object") return JSON.stringify(val).replace(/"/g, '""');
                  return String(val).replace(/"/g, '""');
                }).map(v => `"${v}"`).join(",")
              )
            ].join("\n");

            // BlobとURLを作成
            const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
            const url = URL.createObjectURL(blob);
            return url;
          }}
          onImportCSV={async (type, file) => {
            // TODO: CSV インポート実装
            console.log("Import CSV:", type, file.name);
            return { success: false, imported: 0, errors: ["CSVインポート機能は準備中です"] };
          }}
        />
      </div>
    </ThreePaneLayout>
  );
}
