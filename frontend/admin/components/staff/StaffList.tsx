"use client";

import { StaffDetail, StaffGroup, PaginatedResult } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { User, Building2, Users } from "lucide-react";

interface StaffListProps {
  result: PaginatedResult<StaffDetail>;
  groups?: StaffGroup[];
  selectedStaffId?: string;
  onSelectStaff: (staffId: string) => void;
}

function getStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    active: "在籍中",
    inactive: "退職",
    suspended: "休職",
  };
  return statusMap[status] || status;
}

function getStatusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  if (status === "active") return "default";
  if (status === "suspended") return "secondary";
  if (status === "inactive") return "outline";
  return "secondary";
}

export function StaffList({ result, groups = [], selectedStaffId, onSelectStaff }: StaffListProps) {
  const { data: staffList } = result;

  // スタッフIDからグループを取得するマップを作成
  const staffGroupsMap = new Map<string, string[]>();
  groups.forEach(group => {
    (group.members || []).forEach(member => {
      const existingGroups = staffGroupsMap.get(member.id) || [];
      existingGroups.push(group.name);
      staffGroupsMap.set(member.id, existingGroups);
    });
  });

  if (staffList.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 py-12">
        <User className="w-16 h-16 mb-4 text-gray-300" />
        <p>社員が見つかりません</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {staffList.map((staff) => {
        const staffName = staff.fullName || staff.full_name || `${staff.lastName || staff.last_name || ''} ${staff.firstName || staff.first_name || ''}`.trim();
        const employeeNo = staff.employeeNo || staff.employee_no || "";
        const positionName = staff.positionName || staff.position_name || "";
        const brands = staff.brands || [];
        const staffGroups = staffGroupsMap.get(staff.id) || [];

        return (
          <div
            key={staff.id}
            className={cn(
              "px-2 py-1.5 cursor-pointer hover:bg-blue-50 transition-all border-b border-gray-100",
              selectedStaffId === staff.id && "bg-blue-50 border-l-4 border-l-blue-500"
            )}
            onClick={() => onSelectStaff(staff.id)}
          >
            <div className="flex items-start gap-1.5">
              <div className="flex-1 min-w-0">
                {/* 1行目: 名前、役職、ステータス */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="font-medium text-gray-900 text-xs">{staffName || "名前未設定"}</span>
                  {positionName && <span className="text-[10px] text-gray-500">{positionName}</span>}
                  <Badge
                    variant={getStatusVariant(staff.status)}
                    className="text-[9px] px-1 py-0 h-4"
                  >
                    {getStatusLabel(staff.status)}
                  </Badge>
                </div>

                {/* 2行目: 会社タグとグループタグ */}
                <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                  {/* 会社タグ */}
                  {brands.map(brand => (
                    <Badge
                      key={brand.id}
                      variant="outline"
                      className="text-[9px] px-1 py-0 h-4 bg-orange-50 text-orange-700 border-orange-200"
                    >
                      <Building2 className="w-2 h-2 mr-0.5" />
                      {brand.name}
                    </Badge>
                  ))}

                  {/* グループタグ */}
                  {staffGroups.map((groupName, index) => (
                    <Badge
                      key={index}
                      variant="outline"
                      className="text-[9px] px-1 py-0 h-4 bg-blue-50 text-blue-700 border-blue-200"
                    >
                      <Users className="w-2 h-2 mr-0.5" />
                      {groupName}
                    </Badge>
                  ))}

                  {/* 社員番号 */}
                  {employeeNo && (
                    <span className="text-[9px] text-gray-400">No.{employeeNo}</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
