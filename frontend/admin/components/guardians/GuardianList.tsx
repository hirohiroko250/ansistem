"use client";

import { Guardian } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { Users } from "lucide-react";

interface GuardianListProps {
  guardians: Guardian[];
  selectedGuardianId?: string;
  onSelectGuardian: (guardianId: string) => void;
}

// Helper to get guardian display name
function getGuardianName(guardian: Guardian): string {
  if (guardian.full_name) return guardian.full_name;
  if (guardian.fullName) return guardian.fullName;
  const lastName = guardian.last_name || guardian.lastName || "";
  const firstName = guardian.first_name || guardian.firstName || "";
  if (lastName || firstName) {
    return `${lastName}${firstName}`;
  }
  return guardian.guardian_no || guardian.guardianNo || "(名前未設定)";
}

// Helper to get children's names
function getStudentNames(guardian: Guardian): string[] {
  return guardian.student_names || guardian.studentNames || [];
}

export function GuardianList({ guardians, selectedGuardianId, onSelectGuardian }: GuardianListProps) {
  if (guardians.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 py-12">
        <Users className="w-16 h-16 mb-4 text-gray-300" />
        <p>保護者が見つかりません</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {guardians.map((guardian) => {
        const name = getGuardianName(guardian);
        const studentNames = getStudentNames(guardian);
        const guardianNo = guardian.guardian_no || guardian.guardianNo || "";

        return (
          <div
            key={guardian.id}
            className={cn(
              "px-3 py-2 cursor-pointer hover:bg-blue-50 transition-all border-b border-gray-100",
              selectedGuardianId === guardian.id && "bg-blue-50 border-l-4 border-l-blue-500"
            )}
            onClick={() => onSelectGuardian(guardian.id)}
          >
            <div className="flex items-center gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900 text-sm truncate">{name}</span>
                </div>
                <div className="text-xs text-gray-400 flex items-center gap-2">
                  {guardianNo && <span>No.{guardianNo}</span>}
                  {studentNames.length > 0 && (
                    <span className="text-blue-500">
                      {studentNames.slice(0, 2).join("、")}
                      {studentNames.length > 2 && `他${studentNames.length - 2}名`}
                    </span>
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
