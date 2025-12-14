'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { BottomNav } from '@/components/bottom-nav';
import { useRequireAuth } from '@/lib/auth';
import { getStudents, StudentSearchParams } from '@/lib/api/students';
import { getBrandCategories, getBrands, getSchools, type BrandCategory, type Brand, type School } from '@/lib/api/schools';
import { getContracts, type Contract } from '@/lib/api/contracts';
import type { Student, PaginatedResponse } from '@/lib/api/types';
import { Search, ChevronDown, ChevronRight, ChevronLeft, MessageCircle, User, FileText, Wallet, Settings, Loader2 } from 'lucide-react';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  inquiry: { label: '問い合わせ', color: 'bg-yellow-100 text-yellow-800' },
  trial: { label: '体験', color: 'bg-blue-100 text-blue-800' },
  enrolled: { label: '在籍', color: 'bg-green-100 text-green-800' },
  suspended: { label: '休会', color: 'bg-orange-100 text-orange-800' },
  withdrawn: { label: '退会', color: 'bg-gray-100 text-gray-800' },
};

const STATUS_OPTIONS = [
  { value: '', label: '全ステータス' },
  { value: 'enrolled', label: '在籍' },
  { value: 'trial', label: '体験' },
  { value: 'inquiry', label: '問い合わせ' },
  { value: 'suspended', label: '休会' },
  { value: 'withdrawn', label: '退会' },
];

export default function StudentsPage() {
  const { loading: authLoading } = useRequireAuth();
  const router = useRouter();

  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [contracts, setContracts] = useState<Record<string, Contract[]>>({});
  const [contractsLoading, setContractsLoading] = useState<Record<string, boolean>>({});
  const [searchParams, setSearchParams] = useState<StudentSearchParams>({
    page: 1,
    pageSize: 50,
    search: '',
    status: '',
    brandCategoryId: '',
    brandId: '',
    schoolId: '',
  });
  const [pagination, setPagination] = useState({
    count: 0,
    hasNext: false,
    hasPrev: false,
  });

  // フィルタ用データ
  const [brandCategories, setBrandCategories] = useState<BrandCategory[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [schools, setSchools] = useState<School[]>([]);

  // フィルタ用データの取得（認証後に実行）
  useEffect(() => {
    if (authLoading) return;

    const fetchFilterData = async () => {
      try {
        const [categories, allBrands, allSchools] = await Promise.all([
          getBrandCategories(),
          getBrands(),
          getSchools(),
        ]);
        setBrandCategories(categories);
        setBrands(allBrands);
        setSchools(allSchools);
      } catch (err) {
        console.error('Failed to fetch filter data:', err);
      }
    };
    fetchFilterData();
  }, [authLoading]);

  // 検索条件があるかどうかをチェック
  const hasSearchCriteria = !!(
    searchParams.search?.trim() ||
    searchParams.brandCategoryId ||
    searchParams.brandId ||
    searchParams.schoolId ||
    searchParams.status
  );

  const fetchStudents = useCallback(async () => {
    if (!hasSearchCriteria) {
      setStudents([]);
      setPagination({ count: 0, hasNext: false, hasPrev: false });
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response: PaginatedResponse<Student> = await getStudents(searchParams);
      setStudents(response.results);
      setPagination({
        count: response.count,
        hasNext: !!response.next,
        hasPrev: !!response.previous,
      });
    } catch (err) {
      console.error('Failed to fetch students:', err);
      setError('生徒情報の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  }, [searchParams, hasSearchCriteria]);

  useEffect(() => {
    if (!authLoading) {
      fetchStudents();
    }
  }, [authLoading, fetchStudents]);

  const handleSearchChange = (value: string) => {
    setSearchParams((prev) => ({ ...prev, search: value, page: 1 }));
  };

  const handleStatusChange = (value: string) => {
    setSearchParams((prev) => ({ ...prev, status: value, page: 1 }));
  };

  const handleBrandCategoryChange = (value: string) => {
    setSearchParams((prev) => ({ ...prev, brandCategoryId: value, brandId: '', schoolId: '', page: 1 }));
  };

  const handleBrandChange = (value: string) => {
    setSearchParams((prev) => ({ ...prev, brandId: value, schoolId: '', page: 1 }));
  };

  const handleSchoolChange = (value: string) => {
    setSearchParams((prev) => ({ ...prev, schoolId: value, page: 1 }));
  };

  const handlePageChange = (newPage: number) => {
    setSearchParams((prev) => ({ ...prev, page: newPage }));
  };

  const toggleExpand = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }

    setExpandedId(id);

    // 契約データがまだ取得されていない場合は取得
    if (!contracts[id] && !contractsLoading[id]) {
      setContractsLoading(prev => ({ ...prev, [id]: true }));
      try {
        const response = await getContracts({ studentId: id });
        setContracts(prev => ({ ...prev, [id]: response.results }));
      } catch (err) {
        console.error('Failed to fetch contracts:', err);
        setContracts(prev => ({ ...prev, [id]: [] }));
      } finally {
        setContractsLoading(prev => ({ ...prev, [id]: false }));
      }
    }
  };

  // フィルタされたブランドと校舎
  const filteredBrands = searchParams.brandCategoryId
    ? brands.filter((b) => b.brandCategoryId === searchParams.brandCategoryId)
    : brands;

  const filteredSchools = searchParams.brandId
    ? schools.filter((s) => s.brandId === searchParams.brandId)
    : schools;

  if (authLoading) {
    return <div className="min-h-screen bg-gray-100" />;
  }

  return (
    <div className="min-h-screen bg-gray-100 pb-20">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white border-b border-gray-300 sticky top-0 z-10">
          <div className="p-3">
            <h1 className="text-lg font-bold text-gray-800">生徒検索結果</h1>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="bg-white border-b border-gray-300 p-3">
          <div className="flex flex-wrap gap-2 items-center">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                type="text"
                placeholder="名前・電話番号・IDで検索..."
                value={searchParams.search}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="pl-8 h-8 text-sm"
              />
            </div>

            <Select value={searchParams.brandCategoryId} onValueChange={handleBrandCategoryChange}>
              <SelectTrigger className="w-[100px] h-8 text-xs">
                <SelectValue placeholder="全会社" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">全会社</SelectItem>
                {brandCategories.map((cat) => (
                  <SelectItem key={cat.id} value={cat.id}>{cat.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={searchParams.brandId} onValueChange={handleBrandChange}>
              <SelectTrigger className="w-[100px] h-8 text-xs">
                <SelectValue placeholder="全ブランド" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">全ブランド</SelectItem>
                {filteredBrands.map((brand) => (
                  <SelectItem key={brand.id} value={brand.id}>{brand.brandName}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={searchParams.schoolId} onValueChange={handleSchoolChange}>
              <SelectTrigger className="w-[100px] h-8 text-xs">
                <SelectValue placeholder="全校舎" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">全校舎</SelectItem>
                {filteredSchools.map((school) => (
                  <SelectItem key={school.id} value={school.id}>{school.schoolName}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={searchParams.status} onValueChange={handleStatusChange}>
              <SelectTrigger className="w-[100px] h-8 text-xs">
                <SelectValue placeholder="全て" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button size="sm" onClick={fetchStudents} className="h-8 px-4 bg-blue-600 hover:bg-blue-700">
              検索
            </Button>
          </div>
        </div>

        {/* Results Table */}
        <div className="bg-white">
          {loading ? (
            <div className="p-8 text-center text-gray-500">読み込み中...</div>
          ) : error ? (
            <div className="p-4 bg-red-50 text-red-600">{error}</div>
          ) : !hasSearchCriteria ? (
            <div className="p-8 text-center text-gray-500">
              <Search className="w-12 h-12 text-gray-300 mx-auto mb-2" />
              <p>検索条件を入力してください</p>
            </div>
          ) : students.length === 0 ? (
            <div className="p-8 text-center text-gray-500">生徒が見つかりません</div>
          ) : (
            <>
              {/* Table Header */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="bg-blue-100 border-b-2 border-blue-300">
                      <th className="p-2 text-left font-semibold w-10">No.</th>
                      <th className="p-2 text-left font-semibold">保護者ID</th>
                      <th className="p-2 text-left font-semibold">個人ID</th>
                      <th className="p-2 text-left font-semibold">現在の学年</th>
                      <th className="p-2 text-left font-semibold">苗字</th>
                      <th className="p-2 text-left font-semibold">お名前</th>
                      <th className="p-2 text-left font-semibold">性別</th>
                      <th className="p-2 text-center font-semibold">アクション</th>
                    </tr>
                  </thead>
                  <tbody>
                    {students.map((student, index) => (
                      <>
                        {/* Main Row */}
                        <tr
                          key={student.id}
                          className={`border-b border-gray-200 hover:bg-blue-50 cursor-pointer ${expandedId === student.id ? 'bg-blue-50' : ''}`}
                          onClick={() => toggleExpand(student.id)}
                        >
                          <td className="p-2">
                            <div className="flex items-center gap-1">
                              {expandedId === student.id ? (
                                <ChevronDown className="w-4 h-4 text-blue-600" />
                              ) : (
                                <ChevronRight className="w-4 h-4 text-gray-400" />
                              )}
                              {((searchParams.page || 1) - 1) * (searchParams.pageSize || 50) + index + 1}
                            </div>
                          </td>
                          <td className="p-2 font-mono text-xs">{student.guardian_no || '-'}</td>
                          <td className="p-2 font-mono text-xs">{student.student_no || student.id.slice(0, 8)}</td>
                          <td className="p-2">{student.grade_name || student.grade_text || '-'}</td>
                          <td className="p-2 font-semibold">{student.last_name || '-'}</td>
                          <td className="p-2">{student.first_name || '-'}</td>
                          <td className="p-2">{student.gender === 'male' ? '男' : student.gender === 'female' ? '女' : '-'}</td>
                          <td className="p-2">
                            <div className="flex gap-1 justify-center" onClick={(e) => e.stopPropagation()}>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-6 px-2 text-xs bg-yellow-100 hover:bg-yellow-200 border-yellow-300"
                                onClick={() => router.push(`/billing?student_id=${student.id}`)}
                              >
                                請求一覧
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-6 px-2 text-xs bg-purple-100 hover:bg-purple-200 border-purple-300"
                                onClick={() => router.push(`/contracts?student_id=${student.id}`)}
                              >
                                契約情報
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-6 px-2 text-xs"
                                onClick={() => router.push(`/students/${student.id}`)}
                              >
                                詳細
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-6 px-2 text-xs"
                                onClick={() => router.push(`/students/${student.id}/passbook`)}
                              >
                                通帳
                              </Button>
                            </div>
                          </td>
                        </tr>

                        {/* Expanded Detail Row */}
                        {expandedId === student.id && (
                          <tr className="bg-gray-50">
                            <td colSpan={8} className="p-0">
                              <div className="p-4 border-l-4 border-blue-400">
                                {/* Student Detail Grid */}
                                <div className="grid grid-cols-2 gap-4 mb-4">
                                  {/* Left Side - Student Info */}
                                  <div className="bg-white border rounded p-3">
                                    <table className="w-full text-xs">
                                      <tbody>
                                        <tr className="border-b">
                                          <th className="p-1 text-left bg-gray-50 w-24">生徒ID</th>
                                          <td className="p-1">{student.student_no || student.id.slice(0, 8)}</td>
                                          <th className="p-1 text-left bg-gray-50 w-24">家族ID</th>
                                          <td className="p-1">{student.guardian_no || '-'}</td>
                                        </tr>
                                        <tr className="border-b">
                                          <th className="p-1 text-left bg-gray-50">学年</th>
                                          <td className="p-1">{student.grade_name || student.grade_text || '-'}</td>
                                          <th className="p-1 text-left bg-gray-50">生徒氏名</th>
                                          <td className="p-1">
                                            {student.last_name_kana} {student.first_name_kana}<br />
                                            {student.last_name} {student.first_name}
                                          </td>
                                        </tr>
                                        <tr className="border-b">
                                          <th className="p-1 text-left bg-gray-50">保護者名</th>
                                          <td className="p-1">{student.guardian_name || '-'}</td>
                                          <th className="p-1 text-left bg-gray-50">TEL①②</th>
                                          <td className="p-1">{student.guardian_phone || student.phone || '-'}</td>
                                        </tr>
                                        <tr>
                                          <th className="p-1 text-left bg-gray-50">校舎</th>
                                          <td className="p-1">{student.primary_school_name || student.school_name || '-'}</td>
                                          <th className="p-1 text-left bg-gray-50">ブランド</th>
                                          <td className="p-1">{student.primary_brand_name || '-'}</td>
                                        </tr>
                                      </tbody>
                                    </table>

                                    <div className="flex gap-2 mt-3">
                                      <span
                                        className="bg-orange-100 text-orange-800 px-2 py-1 text-xs rounded cursor-pointer hover:bg-orange-200"
                                        onClick={() => router.push(`/contracts?student_id=${student.id}`)}
                                      >
                                        契約情報
                                      </span>
                                      <a href="#" className="text-blue-600 underline text-xs">追加請求又は割引</a>
                                      <div className="ml-auto flex gap-1">
                                        <Button
                                          size="sm"
                                          variant="outline"
                                          className="h-6 px-2 text-xs"
                                          onClick={() => router.push(`/students/${student.id}`)}
                                        >
                                          詳細
                                        </Button>
                                        <Button
                                          size="sm"
                                          variant="outline"
                                          className="h-6 px-2 text-xs"
                                          onClick={() => router.push(`/students/${student.id}/passbook`)}
                                        >
                                          通帳
                                        </Button>
                                      </div>
                                    </div>

                                    <Button
                                      size="sm"
                                      className="mt-2 h-7 bg-blue-600 hover:bg-blue-700 text-xs"
                                      onClick={() => router.push(`/chat?student_id=${student.id}`)}
                                    >
                                      <MessageCircle className="w-3 h-3 mr-1" />
                                      チャット開始
                                    </Button>
                                  </div>

                                  {/* Right Side - Guardian Info */}
                                  <div className="bg-white border rounded p-3">
                                    <table className="w-full text-xs">
                                      <tbody>
                                        <tr className="border-b">
                                          <th className="p-1 text-left bg-gray-50 w-24">保護者1</th>
                                          <td className="p-1">{student.guardian_name || '-'}</td>
                                        </tr>
                                        <tr className="border-b">
                                          <th className="p-1 text-left bg-gray-50">生徒</th>
                                          <td className="p-1">{student.email || '-'}</td>
                                        </tr>
                                        <tr className="border-b">
                                          <th className="p-1 text-left bg-gray-50">会員種別</th>
                                          <td className="p-1">
                                            <span className={`px-2 py-0.5 rounded text-xs ${STATUS_LABELS[student.status]?.color || 'bg-gray-100'}`}>
                                              {STATUS_LABELS[student.status]?.label || student.status}
                                            </span>
                                          </td>
                                        </tr>
                                        <tr className="border-b">
                                          <th className="p-1 text-left bg-gray-50">入塾日</th>
                                          <td className="p-1">{student.enrollment_date || '-'}</td>
                                        </tr>
                                        <tr>
                                          <th className="p-1 text-left bg-gray-50">備考</th>
                                          <td className="p-1">{student.notes || '-'}</td>
                                        </tr>
                                      </tbody>
                                    </table>
                                  </div>
                                </div>

                                {/* Contract List */}
                                <div className="bg-white border rounded">
                                  <div className="flex items-center gap-2 p-2 bg-gray-100 border-b">
                                    <span className="font-semibold text-sm">契約一覧</span>
                                    <Select defaultValue="current">
                                      <SelectTrigger className="w-[100px] h-6 text-xs">
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem value="current">会計年度</SelectItem>
                                        <SelectItem value="2024">2024年度</SelectItem>
                                        <SelectItem value="2025">2025年度</SelectItem>
                                      </SelectContent>
                                    </Select>
                                    <Button size="sm" variant="outline" className="h-6 px-2 text-xs ml-auto">
                                      新規登録
                                    </Button>
                                  </div>
                                  <table className="w-full text-xs">
                                    <thead>
                                      <tr className="bg-yellow-100 border-b">
                                        <th className="p-1 text-left">No.</th>
                                        <th className="p-1 text-left">契約名</th>
                                        <th className="p-1 text-left">開始日</th>
                                        <th className="p-1 text-left">終了日</th>
                                        <th className="p-1 text-left">休会開始</th>
                                        <th className="p-1 text-left">復会日</th>
                                        <th className="p-1 text-left">ブランド</th>
                                        <th className="p-1 text-center">アクション</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {contractsLoading[student.id] ? (
                                        <tr>
                                          <td colSpan={8} className="p-4 text-center text-gray-500">
                                            <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                                            読み込み中...
                                          </td>
                                        </tr>
                                      ) : contracts[student.id]?.length === 0 ? (
                                        <tr>
                                          <td colSpan={8} className="p-4 text-center text-gray-500">
                                            契約データがありません
                                          </td>
                                        </tr>
                                      ) : (
                                        contracts[student.id]?.map((contract, cIndex) => (
                                          <tr key={contract.id} className="border-b hover:bg-gray-50">
                                            <td className="p-1">{cIndex + 1}</td>
                                            <td className="p-1">{contract.course_name || contract.contract_no || '-'}</td>
                                            <td className="p-1">{contract.start_date || '-'}</td>
                                            <td className="p-1">{contract.end_date || '-'}</td>
                                            <td className="p-1">{contract.suspend_from || '-'}</td>
                                            <td className="p-1">{contract.suspend_until || '-'}</td>
                                            <td className="p-1">{contract.brand_name || '-'}</td>
                                            <td className="p-1">
                                              <div className="flex gap-1 justify-center">
                                                <Button size="sm" variant="outline" className="h-5 px-1 text-xs">変更</Button>
                                                {contract.status !== 'cancelled' && (
                                                  <Button size="sm" variant="outline" className="h-5 px-1 text-xs bg-gray-200">退会</Button>
                                                )}
                                                {contract.status === 'cancelled' && (
                                                  <Button size="sm" variant="outline" className="h-5 px-1 text-xs text-red-600">退会取消</Button>
                                                )}
                                                {contract.status !== 'suspended' && (
                                                  <Button size="sm" variant="outline" className="h-5 px-1 text-xs bg-blue-100">休会</Button>
                                                )}
                                                {contract.status === 'suspended' && (
                                                  <Button size="sm" variant="outline" className="h-5 px-1 text-xs text-red-600">休会取消</Button>
                                                )}
                                              </div>
                                            </td>
                                          </tr>
                                        ))
                                      )}
                                    </tbody>
                                  </table>
                                </div>

                                {/* Bottom Actions */}
                                <div className="flex gap-2 mt-4">
                                  <Button size="sm" variant="outline" className="h-7 px-3 text-xs bg-blue-600 text-white hover:bg-blue-700">
                                    キャンセル
                                  </Button>
                                  <Button size="sm" variant="outline" className="h-7 px-3 text-xs text-orange-600 border-orange-300">
                                    担当者として新規登録
                                  </Button>
                                  <Button size="sm" variant="outline" className="h-7 px-3 text-xs bg-gray-500 text-white">
                                    退会登録
                                  </Button>
                                  <Button size="sm" variant="outline" className="h-7 px-3 text-xs bg-gray-400 text-white">
                                    休会登録
                                  </Button>
                                  <Button size="sm" variant="outline" className="h-7 px-3 text-xs bg-red-600 text-white hover:bg-red-700 ml-auto">
                                    新規登録
                                  </Button>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex justify-between items-center p-3 border-t bg-gray-50">
                <span className="text-sm text-gray-600">
                  {((searchParams.page || 1) - 1) * (searchParams.pageSize || 50) + 1} - {Math.min((searchParams.page || 1) * (searchParams.pageSize || 50), pagination.count)} / {pagination.count}件
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!pagination.hasPrev}
                    onClick={() => handlePageChange((searchParams.page || 1) - 1)}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!pagination.hasNext}
                    onClick={() => handlePageChange((searchParams.page || 1) + 1)}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
