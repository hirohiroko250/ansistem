"use client";

import { useState, useEffect } from "react";
import { Task, updateTask, getStaffList, StaffDetail } from "@/lib/api/staff";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Loader2, UserPlus, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface TaskAssignmentProps {
  task: Task;
  onTaskUpdated?: () => void;
}

export function TaskAssignment({ task, onTaskUpdated }: TaskAssignmentProps) {
  const [staffList, setStaffList] = useState<StaffDetail[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    const fetchStaff = async () => {
      setIsLoading(true);
      try {
        const result = await getStaffList({ page_size: 100 });
        setStaffList(result.data);
      } catch (error) {
        console.error("スタッフ取得エラー:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchStaff();
  }, []);

  const handleAssign = async (staffId: string | null) => {
    setIsUpdating(true);
    try {
      await updateTask(task.id, { assigned_to_id: staffId || undefined } as Partial<Task>);
      onTaskUpdated?.();
    } catch (error) {
      console.error("担当者変更エラー:", error);
    } finally {
      setIsUpdating(false);
    }
  };

  const filteredStaff = staffList.filter((s) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      s.fullName.toLowerCase().includes(q) ||
      s.email.toLowerCase().includes(q) ||
      (s.department || "").toLowerCase().includes(q)
    );
  });

  const currentAssignee = staffList.find((s) => s.id === task.assigned_to_id);

  return (
    <div className="flex flex-col h-full">
      {/* 現在の担当者 */}
      <div className="px-4 py-3 border-b bg-gray-50">
        <p className="text-xs text-gray-500 mb-2">現在の担当者</p>
        {task.assigned_to_id ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-xs bg-blue-100 text-blue-600">
                  {(currentAssignee?.fullName || task.assigned_to_name || "?").charAt(0)}
                </AvatarFallback>
              </Avatar>
              <div>
                <p className="text-sm font-medium">
                  {currentAssignee?.fullName || task.assigned_to_name || "不明"}
                </p>
                {currentAssignee?.department && (
                  <p className="text-xs text-gray-400">{currentAssignee.department}</p>
                )}
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleAssign(null)}
              disabled={isUpdating}
              className="text-gray-400 hover:text-red-500"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-gray-400">
            <UserPlus className="h-5 w-5" />
            <span className="text-sm">未割り当て</span>
          </div>
        )}
      </div>

      {/* 検索 */}
      <div className="px-4 py-2 border-b">
        <input
          type="text"
          placeholder="スタッフを検索..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-3 py-1.5 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* スタッフ一覧 */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : filteredStaff.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <p className="text-sm">スタッフが見つかりません</p>
          </div>
        ) : (
          <div className="divide-y">
            {filteredStaff.map((staff) => {
              const isAssigned = staff.id === task.assigned_to_id;
              return (
                <button
                  key={staff.id}
                  onClick={() => !isAssigned && handleAssign(staff.id)}
                  disabled={isUpdating || isAssigned}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-3 text-left transition-colors",
                    isAssigned
                      ? "bg-blue-50"
                      : "hover:bg-gray-50",
                    isUpdating && "opacity-50"
                  )}
                >
                  <Avatar className="h-8 w-8 flex-shrink-0">
                    <AvatarFallback
                      className={cn(
                        "text-xs",
                        isAssigned
                          ? "bg-blue-200 text-blue-700"
                          : "bg-gray-100 text-gray-600"
                      )}
                    >
                      {staff.fullName.charAt(0)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{staff.fullName}</p>
                    <div className="flex items-center gap-1 mt-0.5">
                      {staff.department && (
                        <span className="text-xs text-gray-400">{staff.department}</span>
                      )}
                      {staff.positionName && (
                        <Badge variant="outline" className="text-xs px-1 py-0">
                          {staff.positionName}
                        </Badge>
                      )}
                    </div>
                  </div>
                  {isAssigned && (
                    <Check className="h-4 w-4 text-blue-600 flex-shrink-0" />
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
