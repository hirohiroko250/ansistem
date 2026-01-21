"use client";

import { useState } from "react";
import { StaffDetail as StaffDetailType, StaffGroup } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Phone,
  Mail,
  User,
  Building2,
  Briefcase,
  Calendar,
  Edit,
  Users,
  Clock,
  FileUser,
} from "lucide-react";
import { StaffProfileTab } from "./StaffProfileTab";
import { StaffScheduleTab } from "./StaffScheduleTab";
import { StaffAttendanceTab } from "./StaffAttendanceTab";

interface StaffDetailProps {
  staff: StaffDetailType;
  groups?: StaffGroup[];
  onEdit?: (staff: StaffDetailType) => void;
}

function getStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    active: "在籍中",
    inactive: "退職",
    suspended: "休職",
  };
  return statusMap[status] || status;
}

function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    active: "bg-green-100 text-green-800",
    inactive: "bg-gray-100 text-gray-800",
    suspended: "bg-orange-100 text-orange-800",
  };
  return colorMap[status] || "bg-gray-100 text-gray-800";
}

export function StaffDetail({ staff, groups = [], onEdit }: StaffDetailProps) {
  const [activeTab, setActiveTab] = useState("basic");

  const staffName = staff.fullName || staff.full_name || `${staff.lastName || staff.last_name || ''} ${staff.firstName || staff.first_name || ''}`.trim();
  const employeeNo = staff.employeeNo || staff.employee_no || "";
  const positionName = staff.positionName || staff.position_name || "";
  const hireDate = staff.hireDate || staff.hire_date || "";
  const brands = staff.brands || [];
  const schools = staff.schools || [];
  const roles = staff.roles || [];

  // スタッフが所属しているグループをフィルタ
  const memberGroups = groups.filter(g =>
    g.members?.some(m => m.id === staff.id)
  );

  return (
    <div className="h-full flex flex-col">
      {/* ヘッダー */}
      <div className="p-4 border-b bg-gray-50">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h2 className="text-xl font-bold text-gray-900">{staffName || "名前未設定"}</h2>
              <Badge className={getStatusColor(staff.status)}>
                {getStatusLabel(staff.status)}
              </Badge>
            </div>
            <div className="text-sm text-gray-500 space-y-0.5">
              {employeeNo && <p>社員番号: {employeeNo}</p>}
              {positionName && <p>{positionName}</p>}
            </div>
          </div>
          {onEdit && (
            <Button variant="outline" size="sm" onClick={() => onEdit(staff)}>
              <Edit className="w-4 h-4 mr-1" />
              編集
            </Button>
          )}
        </div>
      </div>

      {/* タブ */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="px-4 pt-2 justify-start flex-wrap">
          <TabsTrigger value="basic">基本情報</TabsTrigger>
          <TabsTrigger value="assignment">所属情報</TabsTrigger>
          <TabsTrigger value="groups">グループ ({memberGroups.length})</TabsTrigger>
          <TabsTrigger value="profile" className="flex items-center gap-1">
            <FileUser className="w-3.5 h-3.5" />
            プロフィール
          </TabsTrigger>
          <TabsTrigger value="schedule" className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            スケジュール
          </TabsTrigger>
          <TabsTrigger value="attendance" className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            勤怠
          </TabsTrigger>
        </TabsList>

        <div className="flex-1 overflow-auto">
          <TabsContent value="basic" className="p-4 m-0 space-y-6">
            {/* 連絡先 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <User className="w-4 h-4" />
                連絡先情報
              </h3>
              <div className="bg-white rounded-lg border p-4 space-y-3">
                <div className="flex items-center gap-3">
                  <Mail className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-xs text-gray-500">メールアドレス</p>
                    <p className="text-sm">{staff.email || "未設定"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-xs text-gray-500">電話番号</p>
                    <p className="text-sm">{staff.phone || "未設定"}</p>
                  </div>
                </div>
                {hireDate && (
                  <div className="flex items-center gap-3">
                    <Calendar className="w-4 h-4 text-gray-400" />
                    <div>
                      <p className="text-xs text-gray-500">入社日</p>
                      <p className="text-sm">{hireDate}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 役割 */}
            {roles.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <Briefcase className="w-4 h-4" />
                  役割
                </h3>
                <div className="flex flex-wrap gap-2">
                  {roles.map((role, index) => (
                    <Badge key={index} variant="secondary">
                      {role}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="assignment" className="p-4 m-0 space-y-6">
            {/* ブランド */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                所属ブランド
              </h3>
              {brands.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {brands.map((brand) => (
                    <Badge key={brand.id} variant="outline">
                      {brand.name}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">ブランド未設定</p>
              )}
            </div>

            {/* 校舎 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                所属校舎
              </h3>
              {schools.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {schools.map((school) => (
                    <Badge key={school.id} variant="outline">
                      {school.name}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">校舎未設定</p>
              )}
            </div>

            {/* 部署 */}
            {staff.department && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">部署</h3>
                <Badge variant="secondary">{staff.department}</Badge>
              </div>
            )}
          </TabsContent>

          <TabsContent value="groups" className="p-4 m-0">
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Users className="w-4 h-4" />
                所属グループ
              </h3>
              {memberGroups.length > 0 ? (
                <div className="space-y-2">
                  {memberGroups.map((group) => (
                    <div
                      key={group.id}
                      className="bg-white rounded-lg border p-3"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">{group.name}</p>
                          {group.description && (
                            <p className="text-xs text-gray-500">{group.description}</p>
                          )}
                        </div>
                        <Badge variant="secondary" className="text-xs">
                          {group.memberCount || group.member_count || group.members?.length || 0}人
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">グループに所属していません</p>
              )}
            </div>
          </TabsContent>

          <TabsContent value="profile" className="p-4 m-0">
            <StaffProfileTab staffId={staff.id} />
          </TabsContent>

          <TabsContent value="schedule" className="p-4 m-0">
            <StaffScheduleTab staffId={staff.id} />
          </TabsContent>

          <TabsContent value="attendance" className="p-4 m-0">
            <StaffAttendanceTab staffId={staff.id} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
