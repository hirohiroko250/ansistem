"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, X, Filter, ChevronDown, ChevronUp } from "lucide-react";
import { getStaffList, StaffDetail } from "@/lib/api/staff";

export interface TaskFilterValues {
  search: string;
  status: string;
  priority: string;
  task_type: string;
  assigned_to_id: string;
}

interface TaskFiltersProps {
  filters: TaskFilterValues;
  onFilterChange: (filters: TaskFilterValues) => void;
  onClearFilters: () => void;
}

const statusOptions = [
  { value: "all", label: "すべて" },
  { value: "new", label: "新規" },
  { value: "in_progress", label: "対応中" },
  { value: "waiting", label: "保留" },
  { value: "completed", label: "完了" },
];

const priorityOptions = [
  { value: "all", label: "すべて" },
  { value: "urgent", label: "緊急" },
  { value: "high", label: "高" },
  { value: "normal", label: "通常" },
  { value: "medium", label: "中" },
  { value: "low", label: "低" },
];

const taskTypeOptions = [
  { value: "all", label: "すべて" },
  { value: "customer_inquiry", label: "顧客問い合わせ" },
  { value: "inquiry", label: "問い合わせ" },
  { value: "chat", label: "チャット" },
  { value: "trial_registration", label: "体験登録" },
  { value: "enrollment", label: "入会申請" },
  { value: "withdrawal", label: "退会" },
  { value: "suspension", label: "休会" },
  { value: "contract_change", label: "契約変更" },
  { value: "tuition_operation", label: "授業料操作" },
  { value: "debit_failure", label: "引落失敗" },
  { value: "refund_request", label: "返金申請" },
  { value: "bank_account_request", label: "口座申請" },
  { value: "event_registration", label: "イベント" },
  { value: "referral", label: "友人紹介" },
  { value: "guardian_registration", label: "保護者登録" },
  { value: "student_registration", label: "生徒登録" },
  { value: "staff_registration", label: "社員登録" },
  { value: "request", label: "依頼" },
  { value: "trouble", label: "トラブル" },
  { value: "follow_up", label: "フォローアップ" },
  { value: "other", label: "その他" },
];

export function TaskFilters({
  filters,
  onFilterChange,
  onClearFilters,
}: TaskFiltersProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [staffList, setStaffList] = useState<StaffDetail[]>([]);
  const [searchInput, setSearchInput] = useState(filters.search);

  // スタッフ一覧を取得
  useEffect(() => {
    const fetchStaff = async () => {
      try {
        const result = await getStaffList({ page_size: 100 });
        setStaffList(result.data);
      } catch (error) {
        console.error("Failed to fetch staff list:", error);
      }
    };
    fetchStaff();
  }, []);

  // 検索入力の変更（デバウンス）
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchInput !== filters.search) {
        onFilterChange({ ...filters, search: searchInput });
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput, filters, onFilterChange]);

  const handleFilterChange = (key: keyof TaskFilterValues, value: string) => {
    onFilterChange({ ...filters, [key]: value });
  };

  const hasActiveFilters =
    filters.status !== "all" ||
    filters.priority !== "all" ||
    filters.task_type !== "all" ||
    filters.assigned_to_id !== "all" ||
    filters.search !== "";

  const activeFilterCount = [
    filters.status !== "all",
    filters.priority !== "all",
    filters.task_type !== "all",
    filters.assigned_to_id !== "all",
    filters.search !== "",
  ].filter(Boolean).length;

  return (
    <div className="space-y-3">
      {/* メイン検索バー */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="タスクを検索..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-10"
          />
          {searchInput && (
            <button
              onClick={() => setSearchInput("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        <Button
          variant={showAdvanced ? "secondary" : "outline"}
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="gap-2"
        >
          <Filter className="h-4 w-4" />
          フィルター
          {activeFilterCount > 0 && (
            <span className="bg-blue-500 text-white text-xs px-1.5 py-0.5 rounded-full">
              {activeFilterCount}
            </span>
          )}
          {showAdvanced ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </Button>

        {hasActiveFilters && (
          <Button
            variant="ghost"
            onClick={onClearFilters}
            className="text-gray-500 hover:text-gray-700"
          >
            <X className="h-4 w-4 mr-1" />
            クリア
          </Button>
        )}
      </div>

      {/* 詳細フィルター */}
      {showAdvanced && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 bg-gray-50 rounded-lg border">
          {/* ステータス */}
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">
              ステータス
            </label>
            <Select
              value={filters.status}
              onValueChange={(value) => handleFilterChange("status", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="ステータス" />
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 優先度 */}
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">
              優先度
            </label>
            <Select
              value={filters.priority}
              onValueChange={(value) => handleFilterChange("priority", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="優先度" />
              </SelectTrigger>
              <SelectContent>
                {priorityOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* タスク種別 */}
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">
              種別
            </label>
            <Select
              value={filters.task_type}
              onValueChange={(value) => handleFilterChange("task_type", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="種別" />
              </SelectTrigger>
              <SelectContent>
                {taskTypeOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 担当者 */}
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">
              担当者
            </label>
            <Select
              value={filters.assigned_to_id}
              onValueChange={(value) =>
                handleFilterChange("assigned_to_id", value)
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="担当者" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">すべて</SelectItem>
                <SelectItem value="unassigned">未割当</SelectItem>
                {staffList.map((staff) => (
                  <SelectItem key={staff.id} value={staff.id}>
                    {staff.fullName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}
    </div>
  );
}

export const defaultFilterValues: TaskFilterValues = {
  search: "",
  status: "all",
  priority: "all",
  task_type: "all",
  assigned_to_id: "all",
};
