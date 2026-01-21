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
import { Check, Trash2, RefreshCw } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import apiClient from "@/lib/api/client";

interface MessageMemo {
  id: string;
  student_id: string;
  student_name: string;
  student_no: string;
  guardian_no: string;
  content: string;
  priority: string;
  status: string;
  created_by_name: string;
  created_at: string;
  completed_at: string | null;
}

interface MessageMemoListModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const priorityLabels: Record<string, { label: string; color: string }> = {
  low: { label: "低", color: "bg-gray-100 text-gray-600" },
  normal: { label: "通常", color: "bg-blue-100 text-blue-600" },
  high: { label: "高", color: "bg-orange-100 text-orange-600" },
  urgent: { label: "緊急", color: "bg-red-100 text-red-600" },
};

export function MessageMemoListModal({ isOpen, onClose }: MessageMemoListModalProps) {
  const { toast } = useToast();
  const [memos, setMemos] = useState<MessageMemo[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadMemos = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get<{ results: MessageMemo[] }>("/communications/message-memos/");
      setMemos(response.results || []);
    } catch (error) {
      console.error("Load error:", error);
      toast({
        title: "読み込みエラー",
        description: "伝言メモの読み込みに失敗しました",
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

  const handleComplete = async (id: string) => {
    try {
      await apiClient.post(`/communications/message-memos/${id}/complete/`);
      toast({
        title: "完了",
        description: "伝言メモを完了にしました",
      });
      loadMemos();
    } catch (error) {
      console.error("Complete error:", error);
      toast({
        title: "エラー",
        description: "操作に失敗しました",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("このメモを削除しますか？")) return;

    try {
      await apiClient.delete(`/communications/message-memos/${id}/`);
      toast({
        title: "削除完了",
        description: "伝言メモを削除しました",
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
            <span>伝言メモ一覧</span>
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
                <TableHead className="w-28">優先度</TableHead>
                <TableHead>生徒名</TableHead>
                <TableHead>家族ID</TableHead>
                <TableHead>生徒ID</TableHead>
                <TableHead className="min-w-[200px]">内容</TableHead>
                <TableHead>作成者</TableHead>
                <TableHead>作成日時</TableHead>
                <TableHead>状態</TableHead>
                <TableHead className="w-24">アクション</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {memos.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center text-gray-500 py-8">
                    {isLoading ? "読み込み中..." : "伝言メモがありません"}
                  </TableCell>
                </TableRow>
              ) : (
                memos.map((memo) => (
                  <TableRow key={memo.id} className={memo.status === "completed" ? "bg-gray-50 opacity-60" : ""}>
                    <TableCell>
                      <Badge className={priorityLabels[memo.priority]?.color || "bg-gray-100"}>
                        {priorityLabels[memo.priority]?.label || memo.priority}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">{memo.student_name}</TableCell>
                    <TableCell>{memo.guardian_no || "-"}</TableCell>
                    <TableCell>{memo.student_no || "-"}</TableCell>
                    <TableCell className="max-w-[200px] truncate" title={memo.content}>
                      {memo.content}
                    </TableCell>
                    <TableCell>{memo.created_by_name || "-"}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {formatDate(memo.created_at)}
                    </TableCell>
                    <TableCell>
                      {memo.status === "completed" ? (
                        <Badge variant="outline" className="text-green-600 border-green-600">
                          完了
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-yellow-600 border-yellow-600">
                          未対応
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {memo.status !== "completed" && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 w-7 p-0 text-green-600 hover:text-green-700"
                            onClick={() => handleComplete(memo.id)}
                            title="完了にする"
                          >
                            <Check className="w-4 h-4" />
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 w-7 p-0 text-red-600 hover:text-red-700"
                          onClick={() => handleDelete(memo.id)}
                          title="削除"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
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
