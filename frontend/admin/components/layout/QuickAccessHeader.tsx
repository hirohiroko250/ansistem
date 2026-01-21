"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ClipboardList,
  MessageSquareText,
  Phone,
  FileQuestion,
  Plus,
} from "lucide-react";
import { MessageMemoModal } from "@/components/memos/MessageMemoModal";
import { MessageMemoListModal } from "@/components/memos/MessageMemoListModal";
import { TelMemoModal } from "@/components/memos/TelMemoModal";
import { TelMemoListModal } from "@/components/memos/TelMemoListModal";

interface QuickAccessHeaderProps {
  taskCount?: number;
  memoCount?: number;
  telMemoCount?: number;
}

export function QuickAccessHeader({
  taskCount = 0,
  memoCount = 0,
  telMemoCount = 0,
}: QuickAccessHeaderProps) {
  const [isMessageMemoOpen, setIsMessageMemoOpen] = useState(false);
  const [isMessageMemoListOpen, setIsMessageMemoListOpen] = useState(false);
  const [isTelMemoOpen, setIsTelMemoOpen] = useState(false);
  const [isTelMemoListOpen, setIsTelMemoListOpen] = useState(false);

  return (
    <>
      <div className="bg-blue-600 text-white px-4 py-2 flex items-center gap-2 overflow-x-auto">
        {/* 作業一覧 */}
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:bg-blue-700 flex items-center gap-1.5 whitespace-nowrap"
          onClick={() => window.location.href = '/admin/tasks'}
        >
          <ClipboardList className="w-4 h-4" />
          <span>作業一覧</span>
          {taskCount > 0 && (
            <Badge variant="destructive" className="ml-1 text-xs px-1.5 py-0">
              {taskCount}
            </Badge>
          )}
        </Button>

        {/* 伝言メモ一覧 */}
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:bg-blue-700 flex items-center gap-1.5 whitespace-nowrap"
          onClick={() => setIsMessageMemoListOpen(true)}
        >
          <MessageSquareText className="w-4 h-4" />
          <span>伝言メモ一覧</span>
          {memoCount > 0 && (
            <Badge variant="destructive" className="ml-1 text-xs px-1.5 py-0">
              {memoCount}
            </Badge>
          )}
        </Button>

        {/* TEL登録メモ一覧 */}
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:bg-blue-700 flex items-center gap-1.5 whitespace-nowrap"
          onClick={() => setIsTelMemoListOpen(true)}
        >
          <Phone className="w-4 h-4" />
          <span>TEL登録メモ</span>
          {telMemoCount > 0 && (
            <Badge variant="destructive" className="ml-1 text-xs px-1.5 py-0">
              {telMemoCount}
            </Badge>
          )}
        </Button>

        {/* スペーサー */}
        <div className="flex-1" />

        {/* 伝言メモ作成ボタン */}
        <Button
          size="sm"
          className="bg-pink-500 hover:bg-pink-600 text-white flex items-center gap-1.5 whitespace-nowrap"
          onClick={() => setIsMessageMemoOpen(true)}
        >
          <Plus className="w-4 h-4" />
          <span>伝言メモ</span>
        </Button>
      </div>

      {/* モーダル */}
      <MessageMemoModal
        isOpen={isMessageMemoOpen}
        onClose={() => setIsMessageMemoOpen(false)}
      />
      <MessageMemoListModal
        isOpen={isMessageMemoListOpen}
        onClose={() => setIsMessageMemoListOpen(false)}
      />
      <TelMemoModal
        isOpen={isTelMemoOpen}
        onClose={() => setIsTelMemoOpen(false)}
      />
      <TelMemoListModal
        isOpen={isTelMemoListOpen}
        onClose={() => setIsTelMemoListOpen(false)}
      />
    </>
  );
}
