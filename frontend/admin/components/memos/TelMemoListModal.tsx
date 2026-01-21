"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Trash2, RefreshCw, PhoneIncoming, PhoneOutgoing } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import apiClient from "@/lib/api/client";

interface TelMemo {
  id: string;
  student_id: string;
  student_name: string;
  student_no: string;
  guardian_no: string;
  phone_number: string;
  call_direction: string;
  call_result: string;
  content: string;
  created_by_name: string;
  created_at: string;
}

interface TelMemoListModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const callResultLabels: Record<string, { label: string; color: string }> = {
  connected: { label: "通話", color: "bg-green-100 text-green-600" },
  no_answer: { label: "不在", color: "bg-yellow-100 text-yellow-600" },
  busy: { label: "話し中", color: "bg-orange-100 text-orange-600" },
  voicemail: { label: "留守電", color: "bg-blue-100 text-blue-600" },
};

export function TelMemoListModal({ isOpen, onClose }: TelMemoListModalProps) {
  const { toast } = useToast();
  const [memos, setMemos] = useState<TelMemo[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadMemos = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get<{ results: TelMemo[] }>("/communications/tel-memos/");
      setMemos(response.results || []);
    } catch (error) {
      console.error("Load error:", error);
      toast({
        title: "読み込みエラー",
        description: "TEL登録メモの読み込みに失敗しました",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadMemos();
    }
  }, [isOpen]);

  const handleDelete = async (id: string) => {
    if (!confirm("このメモを削除しますか？")) return;

    try {
      await apiClient.delete(`/communications/tel-memos/${id}/`);
      toast({
        title: "削除完了",
        description: "TEL登録メモを削除しました",
      });
      loadMemos();
    } catch (error) {
      console.error("Delete error:", error);
      toast({
        title: "削除エラー",
        description: "削除に失敗しました",
        variant: "destructive",
      });
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>TEL登録メモ一覧</span>
            <Button
              variant="outline"
              size="sm"
              onClick={loadMemos}
              disabled={isLoading}
            >
              <RefreshCw className={`w-4 h-4 mr-1 ${isLoading ? "animate-spin" : ""}`} />
              更新
            </Button>
          </DialogTitle>
        </DialogHeader>

        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-gray-50">
                <TableHead className="w-16">種別</TableHead>
                <TableHead>生徒名</TableHead>
                <TableHead>家族ID</TableHead>
                <TableHead>電話番号</TableHead>
                <TableHead>結果</TableHead>
                <TableHead className="min-w-[200px]">内容</TableHead>
                <TableHead>担当</TableHead>
                <TableHead>日時</TableHead>
                <TableHead className="w-16">削除</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {memos.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center text-gray-500 py-8">
                    {isLoading ? "読み込み中..." : "TEL登録メモがありません"}
                  </TableCell>
                </TableRow>
              ) : (
                memos.map((memo) => (
                  <TableRow key={memo.id}>
                    <TableCell>
                      {memo.call_direction === "incoming" ? (
                        <div className="flex items-center gap-1 text-blue-600">
                          <PhoneIncoming className="w-4 h-4" />
                          <span className="text-xs">着信</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-green-600">
                          <PhoneOutgoing className="w-4 h-4" />
                          <span className="text-xs">発信</span>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="font-medium">{memo.student_name}</TableCell>
                    <TableCell>{memo.guardian_no || "-"}</TableCell>
                    <TableCell>{memo.phone_number || "-"}</TableCell>
                    <TableCell>
                      <Badge className={callResultLabels[memo.call_result]?.color || "bg-gray-100"}>
                        {callResultLabels[memo.call_result]?.label || memo.call_result}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate" title={memo.content}>
                      {memo.content || "-"}
                    </TableCell>
                    <TableCell>{memo.created_by_name || "-"}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {formatDate(memo.created_at)}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 w-7 p-0 text-red-600 hover:text-red-700"
                        onClick={() => handleDelete(memo.id)}
                        title="削除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </DialogContent>
    </Dialog>
  );
}
