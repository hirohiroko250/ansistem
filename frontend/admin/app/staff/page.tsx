"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { StaffList } from "@/components/staff/StaffList";
import { StaffDetail } from "@/components/staff/StaffDetail";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Plus,
  Users,
  User,
  Edit,
  Trash2,
  Loader2,
  Briefcase,
  Building2,
} from "lucide-react";
import {
  getStaffList,
  getStaffDetail,
  getStaffGroups,
  getStaffGroupDetail,
  createStaffGroup,
  updateStaffGroup,
  deleteStaffGroup,
  getBrands,
  getCampuses,
  getRoles,
  getDepartments,
} from "@/lib/api/staff";
import apiClient from "@/lib/api/client";
import type { StaffDetail as StaffDetailType, StaffFilters, StaffGroup, Brand, School, PaginatedResult } from "@/lib/api/types";

const avatarColors = [
  'from-pink-400 to-rose-500',
  'from-blue-400 to-indigo-500',
  'from-green-400 to-emerald-500',
  'from-purple-400 to-violet-500',
  'from-orange-400 to-amber-500',
  'from-cyan-400 to-teal-500',
];

type GroupByType = 'none' | 'role' | 'company';
type TabType = 'list' | 'groups';

export default function StaffPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<TabType>('list');
  const [result, setResult] = useState<PaginatedResult<StaffDetailType>>({
    data: [],
    count: 0,
    page: 1,
    pageSize: 50,
    totalPages: 0,
  });
  const [brands, setBrands] = useState<Brand[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [groups, setGroups] = useState<StaffGroup[]>([]);
  const [allStaff, setAllStaff] = useState<StaffDetailType[]>([]);
  const [filters, setFilters] = useState<StaffFilters>({
    page: 1,
    page_size: 50,
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStaffId, setSelectedStaffId] = useState<string>();
  const [selectedStaff, setSelectedStaff] = useState<StaffDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // グループ関連の状態
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<StaffGroup | null>(null);
  const [groupName, setGroupName] = useState("");
  const [groupDescription, setGroupDescription] = useState("");
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [groupSearchQuery, setGroupSearchQuery] = useState("");
  const [groupBy, setGroupBy] = useState<GroupByType>('role');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['all']));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = apiClient.getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    loadInitialData();
  }, [router]);

  useEffect(() => {
    const staffIdFromUrl = searchParams.get("id");
    if (staffIdFromUrl && staffIdFromUrl !== selectedStaffId) {
      setSelectedStaffId(staffIdFromUrl);
    }
  }, [searchParams]);

  useEffect(() => {
    const token = apiClient.getToken();
    if (!token) return;
    loadStaffList();
  }, [filters]);

  useEffect(() => {
    if (selectedStaffId) {
      loadStaffDetail(selectedStaffId);
    }
  }, [selectedStaffId]);

  async function loadInitialData() {
    const [brandsData, schoolsData, rolesData, departmentsData, groupsData, allStaffData] = await Promise.all([
      getBrands(),
      getCampuses(),
      getRoles(),
      getDepartments(),
      getStaffGroups(),
      getStaffList({ page_size: 500 }),
    ]);
    setBrands(brandsData);
    setSchools(schoolsData);
    setRoles(rolesData);
    setDepartments(departmentsData);
    setGroups(groupsData);
    setAllStaff(allStaffData.data);
    await loadStaffList();
  }

  async function loadStaffList() {
    setLoading(true);
    const data = await getStaffList(filters);
    setResult(data);
    setLoading(false);
  }

  async function loadGroups() {
    const groupsData = await getStaffGroups();
    setGroups(groupsData);
  }

  async function loadStaffDetail(staffId: string) {
    const staff = await getStaffDetail(staffId);
    setSelectedStaff(staff);
  }

  function handleSelectStaff(staffId: string) {
    setSelectedStaffId(staffId);
  }

  function handleCloseDetail() {
    setSelectedStaffId(undefined);
    setSelectedStaff(null);
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

  function handleRoleChange(role: string) {
    setFilters((prev) => ({
      ...prev,
      role: role === "all" ? undefined : role,
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

  // グループ関連の機能
  const filteredStaff = useMemo(() => {
    return allStaff.filter(staff => {
      if (!groupSearchQuery) return true;
      const query = groupSearchQuery.toLowerCase();
      const name = staff.fullName || staff.full_name || `${staff.lastName || ''} ${staff.firstName || ''}`.trim();
      return (
        name.toLowerCase().includes(query) ||
        (staff.email?.toLowerCase().includes(query) ?? false) ||
        (staff.positionName?.toLowerCase().includes(query) ?? false) ||
        (staff.position_name?.toLowerCase().includes(query) ?? false)
      );
    });
  }, [allStaff, groupSearchQuery]);

  const groupedStaff = useMemo(() => {
    if (groupBy === 'none') {
      return [{ key: 'all', label: '全メンバー', members: filteredStaff }];
    }

    if (groupBy === 'role') {
      const staffGroups = new Map<string, StaffDetailType[]>();
      filteredStaff.forEach(staff => {
        const role = staff.positionName || staff.position_name || '未設定';
        if (!staffGroups.has(role)) {
          staffGroups.set(role, []);
        }
        staffGroups.get(role)!.push(staff);
      });
      return Array.from(staffGroups.entries())
        .sort((a, b) => a[0].localeCompare(b[0], 'ja'))
        .map(([role, members]) => ({
          key: role,
          label: role,
          members,
        }));
    }

    if (groupBy === 'company') {
      const staffGroups = new Map<string, StaffDetailType[]>();
      filteredStaff.forEach(staff => {
        const staffBrands = staff.brands || [];
        if (staffBrands.length === 0) {
          const key = '未所属';
          if (!staffGroups.has(key)) {
            staffGroups.set(key, []);
          }
          staffGroups.get(key)!.push(staff);
        } else {
          staffBrands.forEach(brand => {
            if (!staffGroups.has(brand.name)) {
              staffGroups.set(brand.name, []);
            }
            staffGroups.get(brand.name)!.push(staff);
          });
        }
      });
      return Array.from(staffGroups.entries())
        .sort((a, b) => a[0].localeCompare(b[0], 'ja'))
        .map(([company, members]) => ({
          key: company,
          label: company,
          members,
        }));
    }

    return [];
  }, [filteredStaff, groupBy]);

  function handleToggleMember(staffId: string) {
    setSelectedMembers(prev =>
      prev.includes(staffId)
        ? prev.filter(id => id !== staffId)
        : [...prev, staffId]
    );
  }

  function handleToggleGroup(groupKey: string) {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupKey)) {
        next.delete(groupKey);
      } else {
        next.add(groupKey);
      }
      return next;
    });
  }

  function handleSelectAllInGroup(members: StaffDetailType[]) {
    const memberIds = members.map(m => m.id);
    const allSelected = memberIds.every(id => selectedMembers.includes(id));

    if (allSelected) {
      setSelectedMembers(prev => prev.filter(id => !memberIds.includes(id)));
    } else {
      setSelectedMembers(prev => {
        const newSet = new Set([...prev, ...memberIds]);
        return Array.from(newSet);
      });
    }
  }

  function openCreateDialog() {
    setGroupName("");
    setGroupDescription("");
    setSelectedMembers([]);
    setGroupSearchQuery("");
    setError(null);
    setCreateDialogOpen(true);
  }

  async function openEditDialog(group: StaffGroup) {
    const detail = await getStaffGroupDetail(group.id);
    if (detail) {
      setSelectedGroup(detail);
      setGroupName(detail.name);
      setGroupDescription(detail.description || "");
      setSelectedMembers(detail.members?.map(m => m.id) || []);
      setGroupSearchQuery("");
      setError(null);
      setEditDialogOpen(true);
    }
  }

  function openDeleteDialog(group: StaffGroup) {
    setSelectedGroup(group);
    setDeleteDialogOpen(true);
  }

  async function handleCreate() {
    if (!groupName.trim()) {
      setError("グループ名を入力してください");
      return;
    }
    if (selectedMembers.length === 0) {
      setError("メンバーを1人以上選択してください");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await createStaffGroup({
        name: groupName.trim(),
        description: groupDescription.trim(),
        memberIds: selectedMembers,
      });
      setCreateDialogOpen(false);
      await loadGroups();
    } catch (err) {
      console.error("Failed to create group:", err);
      setError("グループの作成に失敗しました");
    }
    setSaving(false);
  }

  async function handleUpdate() {
    if (!selectedGroup) return;
    if (!groupName.trim()) {
      setError("グループ名を入力してください");
      return;
    }
    if (selectedMembers.length === 0) {
      setError("メンバーを1人以上選択してください");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await updateStaffGroup(selectedGroup.id, {
        name: groupName.trim(),
        description: groupDescription.trim(),
        memberIds: selectedMembers,
      });
      setEditDialogOpen(false);
      setSelectedGroup(null);
      await loadGroups();
    } catch (err) {
      console.error("Failed to update group:", err);
      setError("グループの更新に失敗しました");
    }
    setSaving(false);
  }

  async function handleDelete() {
    if (!selectedGroup) return;

    setSaving(true);
    try {
      await deleteStaffGroup(selectedGroup.id);
      setDeleteDialogOpen(false);
      setSelectedGroup(null);
      await loadGroups();
    } catch (err) {
      console.error("Failed to delete group:", err);
    }
    setSaving(false);
  }

  const renderMemberSelector = () => (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>メンバー選択 * ({selectedMembers.length}人選択中)</Label>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
        <button
          type="button"
          onClick={() => setGroupBy('role')}
          className={`flex-1 py-1.5 px-2 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
            groupBy === 'role'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          <Briefcase className="w-3.5 h-3.5" />
          役割別
        </button>
        <button
          type="button"
          onClick={() => setGroupBy('company')}
          className={`flex-1 py-1.5 px-2 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
            groupBy === 'company'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          <Building2 className="w-3.5 h-3.5" />
          会社別
        </button>
        <button
          type="button"
          onClick={() => setGroupBy('none')}
          className={`flex-1 py-1.5 px-2 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
            groupBy === 'none'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          一覧
        </button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          value={groupSearchQuery}
          onChange={(e) => setGroupSearchQuery(e.target.value)}
          placeholder="名前で検索..."
          className="pl-10"
        />
      </div>

      <div className="max-h-[300px] overflow-y-auto border rounded-lg">
        {filteredStaff.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            {groupSearchQuery ? '該当するメンバーがいません' : 'メンバーがいません'}
          </div>
        ) : (
          groupedStaff.map(group => {
            const isExpanded = expandedGroups.has(group.key) || groupBy === 'none';
            const selectedInGroup = group.members.filter(m => selectedMembers.includes(m.id)).length;
            const allSelectedInGroup = selectedInGroup === group.members.length;

            return (
              <div key={group.key} className="border-b last:border-b-0">
                {groupBy !== 'none' && (
                  <div
                    className="flex items-center gap-2 px-3 py-2 bg-gray-50 cursor-pointer hover:bg-gray-100 sticky top-0"
                    onClick={() => handleToggleGroup(group.key)}
                  >
                    <button type="button" className="p-0.5">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-gray-500" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-500" />
                      )}
                    </button>
                    <span className="flex-1 text-sm font-medium text-gray-700">
                      {group.label}
                    </span>
                    <span className="text-xs text-gray-500">
                      {selectedInGroup > 0 && (
                        <span className="text-blue-600 font-medium mr-1">
                          {selectedInGroup}選択
                        </span>
                      )}
                      ({group.members.length}人)
                    </span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectAllInGroup(group.members);
                      }}
                      className={`text-xs px-2 py-0.5 rounded transition-colors ${
                        allSelectedInGroup
                          ? 'bg-blue-100 text-blue-600'
                          : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                      }`}
                    >
                      {allSelectedInGroup ? '解除' : '全選択'}
                    </button>
                  </div>
                )}

                {isExpanded && (
                  <div>
                    {group.members.map(staff => {
                      const name = staff.fullName || staff.full_name || `${staff.lastName || ''} ${staff.firstName || ''}`.trim();
                      const colorIndex = name.charCodeAt(0) % avatarColors.length;
                      const isSelected = selectedMembers.includes(staff.id);

                      return (
                        <label
                          key={staff.id}
                          className={`flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 border-b last:border-b-0 ${
                            isSelected ? 'bg-blue-50' : ''
                          }`}
                        >
                          <Checkbox
                            checked={isSelected}
                            onCheckedChange={() => handleToggleMember(staff.id)}
                          />
                          <Avatar className="w-9 h-9">
                            <AvatarFallback className={`bg-gradient-to-br ${avatarColors[colorIndex]} text-white text-sm`}>
                              {name.substring(0, 2)}
                            </AvatarFallback>
                          </Avatar>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm text-gray-900 truncate">
                              {name}
                            </p>
                            <div className="flex items-center gap-2 text-xs text-gray-500">
                              {(staff.positionName || staff.position_name) && (
                                <span className="truncate">{staff.positionName || staff.position_name}</span>
                              )}
                              {staff.brands && staff.brands.length > 0 && groupBy !== 'company' && (
                                <span className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">
                                  {staff.brands[0].name}
                                </span>
                              )}
                            </div>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );

  const startResult = (result.page - 1) * result.pageSize + 1;
  const endResult = Math.min(result.page * result.pageSize, result.count);

  return (
    <ThreePaneLayout
      isRightPanelOpen={!!selectedStaffId && activeTab === 'list'}
      onCloseRightPanel={handleCloseDetail}
      rightPanel={
        selectedStaff ? (
          <StaffDetail
            staff={selectedStaff}
            groups={groups}
          />
        ) : (
          <div className="text-center text-gray-500">...</div>
        )
      }
    >
      <div className="p-6 h-full flex flex-col">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">社員管理</h1>
          <p className="text-gray-600">
            {activeTab === 'list'
              ? `${result.count.toLocaleString()}名の社員が登録されています`
              : `${groups.length}件のグループが登録されています`
            }
          </p>
        </div>

        {/* タブ切り替え */}
        <div className="mb-6 border-b">
          <div className="flex gap-1">
            <button
              onClick={() => setActiveTab('list')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'list'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <span className="flex items-center gap-2">
                <User className="w-4 h-4" />
                社員一覧 ({result.count})
              </span>
            </button>
            <button
              onClick={() => setActiveTab('groups')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'groups'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <span className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                グループ ({groups.length})
              </span>
            </button>
          </div>
        </div>

        {activeTab === 'list' ? (
          <>
            {/* 社員一覧タブの内容 */}
            <div className="space-y-4 mb-6">
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <Input
                    type="text"
                    placeholder="社員名・社員番号で検索..."
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

                {roles.length > 0 && (
                  <Select
                    value={filters.role || "all"}
                    onValueChange={handleRoleChange}
                  >
                    <SelectTrigger className="w-[140px]">
                      <SelectValue placeholder="役割" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全役割</SelectItem>
                      {roles.map((role) => (
                        <SelectItem key={role} value={role}>
                          {role}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}

                <Select
                  value={filters.status || "all"}
                  onValueChange={handleStatusChange}
                >
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="状態" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全て</SelectItem>
                    <SelectItem value="active">在籍中</SelectItem>
                    <SelectItem value="suspended">休職</SelectItem>
                    <SelectItem value="inactive">退職</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex-1 overflow-auto mb-4">
              {loading ? (
                <div className="text-center text-gray-500 py-8">...</div>
              ) : (
                <StaffList
                  result={result}
                  groups={groups}
                  selectedStaffId={selectedStaffId}
                  onSelectStaff={handleSelectStaff}
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
          </>
        ) : (
          <>
            {/* グループタブの内容 */}
            <div className="flex justify-end mb-4">
              <Button onClick={openCreateDialog}>
                <Plus className="w-4 h-4 mr-2" />
                新規グループ
              </Button>
            </div>

            <div className="flex-1 overflow-auto">
              {groups.length === 0 ? (
                <div className="bg-white rounded-lg border p-12 text-center">
                  <Users className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                  <p className="text-gray-500 mb-4">グループがありません</p>
                  <Button onClick={openCreateDialog}>
                    <Plus className="w-4 h-4 mr-2" />
                    グループを作成
                  </Button>
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {groups.map((group) => (
                    <div
                      key={group.id}
                      className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="font-semibold text-gray-900">{group.name}</h3>
                          {group.description && (
                            <p className="text-sm text-gray-500 mt-1">{group.description}</p>
                          )}
                        </div>
                        <Badge variant="secondary">
                          {group.memberCount || group.member_count || 0}人
                        </Badge>
                      </div>

                      <div className="flex -space-x-2 mb-4">
                        {(group.members || []).slice(0, 5).map((member) => {
                          const name = member.fullName || member.full_name || `${member.lastName || ''} ${member.firstName || ''}`.trim();
                          const colorIndex = name.charCodeAt(0) % avatarColors.length;
                          return (
                            <Avatar key={member.id} className="w-8 h-8 border-2 border-white">
                              <AvatarFallback className={`bg-gradient-to-br ${avatarColors[colorIndex]} text-white text-xs`}>
                                {name.substring(0, 2)}
                              </AvatarFallback>
                            </Avatar>
                          );
                        })}
                        {(group.memberCount || group.member_count || 0) > 5 && (
                          <div className="w-8 h-8 rounded-full bg-gray-200 border-2 border-white flex items-center justify-center text-xs text-gray-600">
                            +{(group.memberCount || group.member_count || 0) - 5}
                          </div>
                        )}
                      </div>

                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() => openEditDialog(group)}
                        >
                          <Edit className="w-4 h-4 mr-1" />
                          編集
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() => openDeleteDialog(group)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* 新規作成ダイアログ */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>新規グループ作成</DialogTitle>
            <DialogDescription>
              グループ名とメンバーを設定してください
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="group-name">グループ名 *</Label>
              <Input
                id="group-name"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="例: 営業チーム"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="group-description">説明</Label>
              <Textarea
                id="group-description"
                value={groupDescription}
                onChange={(e) => setGroupDescription(e.target.value)}
                placeholder="グループの説明（任意）"
                rows={2}
              />
            </div>

            {renderMemberSelector()}

            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateDialogOpen(false)}
              disabled={saving}
            >
              キャンセル
            </Button>
            <Button onClick={handleCreate} disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  作成中...
                </>
              ) : (
                '作成'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 編集ダイアログ */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>グループ編集</DialogTitle>
            <DialogDescription>
              グループ名とメンバーを編集してください
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-group-name">グループ名 *</Label>
              <Input
                id="edit-group-name"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="例: 営業チーム"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-group-description">説明</Label>
              <Textarea
                id="edit-group-description"
                value={groupDescription}
                onChange={(e) => setGroupDescription(e.target.value)}
                placeholder="グループの説明（任意）"
                rows={2}
              />
            </div>

            {renderMemberSelector()}

            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditDialogOpen(false)}
              disabled={saving}
            >
              キャンセル
            </Button>
            <Button onClick={handleUpdate} disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  更新中...
                </>
              ) : (
                '更新'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 削除確認ダイアログ */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>グループを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              「{selectedGroup?.name}」を削除します。この操作は取り消せません。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={saving}>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={saving}
              className="bg-red-600 hover:bg-red-700"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  削除中...
                </>
              ) : (
                '削除'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </ThreePaneLayout>
  );
}
