"use client";

import { useEffect, useState } from "react";
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
  getStudentLessons,
  getStudentParents,
  getBrands,
  getCampuses,
} from "@/lib/api/staff";
import type { Student, Guardian, LessonSchedule, Brand, School, PaginatedResult, StudentFilters } from "@/lib/api/types";

export default function StudentsPage() {
  const [result, setResult] = useState<PaginatedResult<Student>>({
    data: [],
    count: 0,
    page: 1,
    pageSize: 50,
    totalPages: 0,
  });
  const [brands, setBrands] = useState<Brand[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [filters, setFilters] = useState<StudentFilters>({
    page: 1,
    page_size: 50,
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStudentId, setSelectedStudentId] = useState<string>();
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [selectedStudentParents, setSelectedStudentParents] = useState<Guardian[]>([]);
  const [selectedStudentLessons, setSelectedStudentLessons] = useState<LessonSchedule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    loadStudents();
  }, [filters]);

  useEffect(() => {
    if (selectedStudentId) {
      loadStudentDetail(selectedStudentId);
    }
  }, [selectedStudentId]);

  async function loadInitialData() {
    const [brandsData, schoolsData] = await Promise.all([
      getBrands(),
      getCampuses(),
    ]);
    setBrands(brandsData);
    setSchools(schoolsData);
    await loadStudents();
  }

  async function loadStudents() {
    setLoading(true);
    const data = await getStudents(filters);
    setResult(data);
    setLoading(false);
  }

  async function loadStudentDetail(studentId: string) {
    const [student, parents, lessons] = await Promise.all([
      getStudentDetail(studentId),
      getStudentParents(studentId),
      getStudentLessons(studentId),
    ]);

    setSelectedStudent(student);
    setSelectedStudentParents(parents);
    setSelectedStudentLessons(lessons);
  }

  function handleSelectStudent(studentId: string) {
    setSelectedStudentId(studentId);
  }

  function handleCloseDetail() {
    setSelectedStudentId(undefined);
    setSelectedStudent(null);
    setSelectedStudentParents([]);
    setSelectedStudentLessons([]);
  }

  function handleSearch() {
    setFilters((prev) => ({
      ...prev,
      search: searchQuery || undefined,
      page: 1,
    }));
  }

  function handleBrandChange(brandId: string) {
    setFilters((prev) => ({
      ...prev,
      brand_id: brandId === "all" ? undefined : brandId,
      page: 1,
    }));
  }

  function handleSchoolChange(schoolId: string) {
    setFilters((prev) => ({
      ...prev,
      school_id: schoolId === "all" ? undefined : schoolId,
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
            lessons={selectedStudentLessons}
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
            {result.count.toLocaleString()}名の生徒が登録されています
          </p>
        </div>

        <div className="space-y-4 mb-6">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <Input
                type="text"
                placeholder="生徒名で検索..."
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
                    {brand.brand_name}
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
                    {school.school_name_short || school.school_name}
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
          ) : (
            <StudentList
              result={result}
              selectedStudentId={selectedStudentId}
              onSelectStudent={handleSelectStudent}
            />
          )}
        </div>

        {result.totalPages > 1 && (
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
