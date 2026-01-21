"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { StudentList } from "@/components/students/StudentList";
import { StudentDetail } from "@/components/students/StudentDetail";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, Filter, ChevronLeft, ChevronRight } from "lucide-react";
import {
  getStudents,
  getStudentDetail,
  getStudentParents,
  getStudentContracts,
  getStudentInvoices,
  getStudentContactLogs,
  getGuardianChatLogs,
  getGuardianMessages,
  getSiblings,
  getBrandCategories,
  getBrands,
  getCampuses,
  updateContractDiscounts,
  type BrandCategory,
  type ContactLog,
  type ChatLog,
  type ChatMessage,
} from "@/lib/api/staff";
import { getChannels } from "@/lib/api/chat";
import apiClient from "@/lib/api/client";
import type { Student, Guardian, Contract, Invoice, Brand, School, PaginatedResult, StudentFilters } from "@/lib/api/types";

export default function StudentsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [result, setResult] = useState<PaginatedResult<Student>>({
    data: [],
    count: 0,
    page: 1,
    pageSize: 50,
    totalPages: 0,
  });
  const [brandCategories, setBrandCategories] = useState<BrandCategory[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [filters, setFilters] = useState<StudentFilters>({
    page: 1,
    page_size: 50,
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [idSearchQuery, setIdSearchQuery] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedStudentId, setSelectedStudentId] = useState<string>();
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [selectedStudentParents, setSelectedStudentParents] = useState<Guardian[]>([]);
  const [selectedStudentContracts, setSelectedStudentContracts] = useState<Contract[]>([]);
  const [selectedStudentInvoices, setSelectedStudentInvoices] = useState<Invoice[]>([]);
  const [selectedStudentContactLogs, setSelectedStudentContactLogs] = useState<ContactLog[]>([]);
  const [selectedStudentChatLogs, setSelectedStudentChatLogs] = useState<ChatLog[]>([]);
  const [selectedStudentMessages, setSelectedStudentMessages] = useState<ChatMessage[]>([]);
  const [selectedStudentSiblings, setSelectedStudentSiblings] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [unreadCounts, setUnreadCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    // 認証チェック
    const token = apiClient.getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    loadInitialData();
  }, [router]);

  // URLパラメータから生徒IDを取得して選択
  useEffect(() => {
    const studentIdFromUrl = searchParams.get("id");
    if (studentIdFromUrl && studentIdFromUrl !== selectedStudentId) {
      setSelectedStudentId(studentIdFromUrl);
    }
  }, [searchParams]);

  useEffect(() => {
    // 認証済みの場合のみデータ取得
    const token = apiClient.getToken();
    if (!token) return;
    // 検索が実行された場合のみ生徒を取得
    if (hasSearched) {
      loadStudents();
    }
  }, [filters, hasSearched]);

  useEffect(() => {
    if (selectedStudentId) {
      loadStudentDetail(selectedStudentId);
    }
  }, [selectedStudentId]);

  async function loadInitialData() {
    const [categoriesData, brandsData, schoolsData] = await Promise.all([
      getBrandCategories(),
      getBrands(),
      getCampuses(),
    ]);
    setBrandCategories(categoriesData);
    setBrands(brandsData);
    setSchools(schoolsData);
    setLoading(false);
  }

  async function loadStudents() {
    setLoading(true);
    const data = await getStudents(filters);
    setResult(data);
    setLoading(false);

    // 各生徒の未読件数を取得（バックグラウンドで）
    loadUnreadCounts(data.data);
  }

  async function loadUnreadCounts(students: Student[]) {
    const counts: Record<string, number> = {};

    // 保護者IDでグループ化（同じ保護者の生徒は同じチャンネルを共有）
    const guardianToStudents: Record<string, string[]> = {};
    students.forEach((student) => {
      const guardianId = student.guardianId || student.guardian_id || student.guardian?.id;
      if (guardianId) {
        if (!guardianToStudents[guardianId]) {
          guardianToStudents[guardianId] = [];
        }
        guardianToStudents[guardianId].push(student.id);
      }
    });

    // 保護者ごとにチャンネルを取得（並列で最大10件ずつ）
    const guardianIds = Object.keys(guardianToStudents);
    const batchSize = 10;
    for (let i = 0; i < guardianIds.length; i += batchSize) {
      const batch = guardianIds.slice(i, i + batchSize);
      await Promise.all(
        batch.map(async (guardianId) => {
          try {
            const channels = await getChannels({ guardianId });
            // 未読件数を合計
            const totalUnread = (channels || []).reduce(
              (sum, ch) => sum + (ch.unreadCount || 0),
              0
            );
            if (totalUnread > 0) {
              // この保護者に紐づく全生徒に未読件数を設定
              guardianToStudents[guardianId].forEach((studentId) => {
                counts[studentId] = totalUnread;
              });
            }
          } catch (err) {
            console.error(`Failed to get unread count for guardian ${guardianId}:`, err);
          }
        })
      );
    }

    setUnreadCounts(counts);
  }

  async function loadStudentDetail(studentId: string) {
    console.log("[loadStudentDetail] studentId:", studentId);
    const [student, parents, contracts, invoices, contactLogs, siblings] = await Promise.all([
      getStudentDetail(studentId),
      getStudentParents(studentId),
      getStudentContracts(studentId),
      getStudentInvoices(studentId),
      getStudentContactLogs(studentId),
      getSiblings(studentId),
    ]);

    console.log("[loadStudentDetail] student:", student);
    console.log("[loadStudentDetail] parents:", parents);
    console.log("[loadStudentDetail] contracts:", contracts);
    console.log("[loadStudentDetail] invoices:", invoices);
    console.log("[loadStudentDetail] contactLogs:", contactLogs);
    console.log("[loadStudentDetail] siblings:", siblings);

    setSelectedStudent(student);
    setSelectedStudentParents(parents);
    setSelectedStudentContracts(contracts);
    setSelectedStudentInvoices(invoices);
    setSelectedStudentContactLogs(contactLogs);
    setSelectedStudentSiblings(siblings);

    // チャットログとメッセージは保護者IDで取得
    const guardianId = student?.guardianId || student?.guardian_id || student?.guardian?.id;
    if (guardianId) {
      const [chatLogs, messages] = await Promise.all([
        getGuardianChatLogs(guardianId),
        getGuardianMessages(guardianId),
      ]);
      setSelectedStudentChatLogs(chatLogs);
      setSelectedStudentMessages(messages);
    } else {
      setSelectedStudentChatLogs([]);
      setSelectedStudentMessages([]);
    }
  }

  function handleSelectStudent(studentId: string) {
    setSelectedStudentId(studentId);
  }

  async function handleContractUpdate(contractId: string, updates: {
    item_discounts?: {
      id?: string;
      student_item_id?: string;
      discount_name: string;
      amount: number;
      discount_unit: "yen" | "percent";
      is_new?: boolean;
      is_deleted?: boolean;
    }[];
    notes?: string;
  }) {
    try {
      await updateContractDiscounts(contractId, updates);
      // Refresh contracts after update
      if (selectedStudentId) {
        const contracts = await getStudentContracts(selectedStudentId);
        setSelectedStudentContracts(contracts);
      }
    } catch (error) {
      console.error("Failed to update contract:", error);
      throw error;
    }
  }

  function handleCloseDetail() {
    setSelectedStudentId(undefined);
    setSelectedStudent(null);
    setSelectedStudentParents([]);
    setSelectedStudentContracts([]);
    setSelectedStudentInvoices([]);
    setSelectedStudentContactLogs([]);
    setSelectedStudentChatLogs([]);
    setSelectedStudentMessages([]);
    setSelectedStudentSiblings([]);
  }

  function handleSearch() {
    setHasSearched(true);
    setFilters((prev) => ({
      ...prev,
      search: searchQuery || undefined,
      student_no: idSearchQuery || undefined,
      page: 1,
    }));
  }

  function handleCategoryChange(categoryId: string) {
    if (categoryId !== "all") {
      setHasSearched(true);
    }
    setFilters((prev) => ({
      ...prev,
      brand_category_id: categoryId === "all" ? undefined : categoryId,
      page: 1,
    }));
  }

  function handleBrandChange(brandId: string) {
    if (brandId !== "all") {
      setHasSearched(true);
    }
    setFilters((prev) => ({
      ...prev,
      brand_id: brandId === "all" ? undefined : brandId,
      page: 1,
    }));
  }

  function handleSchoolChange(schoolId: string) {
    if (schoolId !== "all") {
      setHasSearched(true);
    }
    setFilters((prev) => ({
      ...prev,
      school_id: schoolId === "all" ? undefined : schoolId,
      page: 1,
    }));
  }

  function handleStatusChange(status: string) {
    if (status !== "all") {
      setHasSearched(true);
    }
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
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const startResult = (result.page - 1) * result.pageSize + 1;
  const endResult = Math.min(result.page * result.pageSize, result.count);

  return (
    <ThreePaneLayout
      isRightPanelOpen={!!selectedStudentId}
      onCloseRightPanel={handleCloseDetail}
      rightPanel={
        selectedStudent ? (
          <StudentDetail
            student={selectedStudent}
            parents={selectedStudentParents}
            contracts={selectedStudentContracts}
            invoices={selectedStudentInvoices}
            contactLogs={selectedStudentContactLogs}
            chatLogs={selectedStudentChatLogs}
            messages={selectedStudentMessages}
            siblings={selectedStudentSiblings}
            onSelectSibling={handleSelectStudent}
            onContractUpdate={handleContractUpdate}
            onRefresh={() => selectedStudentId && loadStudentDetail(selectedStudentId)}
          />
        ) : (
          <div className="text-center text-gray-500">読み込み中...</div>
        )
      }
    >
      <div className="p-6 h-full flex flex-col">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">生徒一覧</h1>
          <p className="text-gray-600">
            {hasSearched
              ? `${result.count.toLocaleString()}名の生徒が見つかりました`
              : "検索条件を入力して生徒を検索してください"}
          </p>
        </div>

        <div className="space-y-4 mb-6">
          <div className="flex gap-3">
            <div className="flex gap-2 items-center">
              <span className="text-sm text-gray-600 whitespace-nowrap">ID</span>
              <Input
                type="text"
                placeholder="生徒番号"
                value={idSearchQuery}
                onChange={(e) => setIdSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleSearch();
                  }
                }}
                className="w-32"
              />
            </div>
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <Input
                type="text"
                placeholder="名前・電話番号で検索..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleSearch();
                  }
                }}
                className="pl-10"
              />
            </div>
            <Button onClick={handleSearch}>検索</Button>
          </div>

          <div className="flex gap-3 flex-wrap items-center">
            <Filter className="w-4 h-4 text-gray-500" />

            <Select
              value={filters.brand_category_id || "all"}
              onValueChange={handleCategoryChange}
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="会社" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全会社</SelectItem>
                {brandCategories.map((category) => (
                  <SelectItem key={category.id} value={category.id}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={filters.brand_id || "all"}
              onValueChange={handleBrandChange}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="ブランド" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全ブランド</SelectItem>
                {brands.map((brand) => (
                  <SelectItem key={brand.id} value={brand.id}>
                    {brand.brandName || brand.brand_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={filters.school_id || "all"}
              onValueChange={handleSchoolChange}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="校舎" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全校舎</SelectItem>
                {schools.map((school) => (
                  <SelectItem key={school.id} value={school.id}>
                    {school.schoolNameShort || school.schoolName || school.school_name_short || school.school_name}
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
                <SelectItem value="enrolled">在籍中</SelectItem>
                <SelectItem value="suspended">休会</SelectItem>
                <SelectItem value="withdrawn">退会</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex-1 overflow-auto mb-4">
          {loading ? (
            <div className="text-center text-gray-500 py-8">読み込み中...</div>
          ) : !hasSearched ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-500">
              <Search className="w-16 h-16 text-gray-300 mb-4" />
              <p className="text-lg">検索条件を入力してください</p>
              <p className="text-sm mt-2">生徒名、生徒番号、または各種フィルターで検索できます</p>
            </div>
          ) : (
            <StudentList
              result={result}
              selectedStudentId={selectedStudentId}
              onSelectStudent={handleSelectStudent}
              unreadCounts={unreadCounts}
            />
          )}
        </div>

        {hasSearched && result.totalPages > 1 && (
          <div className="flex items-center justify-between pt-4 border-t">
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
      </div>
    </ThreePaneLayout>
  );
}
