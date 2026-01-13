"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Send, MessageSquare, Lock } from "lucide-react";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { cn } from "@/lib/utils";
import { getTaskComments, createTaskComment, TaskComment } from "@/lib/api/staff";

interface TaskCommentsProps {
  taskId: string;
  className?: string;
}

export function TaskComments({ taskId, className }: TaskCommentsProps) {
  const [comments, setComments] = useState<TaskComment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newComment, setNewComment] = useState("");
  const [isInternal, setIsInternal] = useState(false);

  // コメント一覧を取得
  const fetchComments = async () => {
    setIsLoading(true);
    try {
      const data = await getTaskComments(taskId);
      setComments(data);
    } catch (error) {
      console.error("Failed to fetch comments:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (taskId) {
      fetchComments();
    }
  }, [taskId]);

  // コメント投稿
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const result = await createTaskComment({
        task: taskId,
        comment: newComment.trim(),
        is_internal: isInternal,
      });
      if (result) {
        setComments((prev) => [...prev, result]);
        setNewComment("");
        setIsInternal(false);
      }
    } catch (error) {
      console.error("Failed to create comment:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // 名前からイニシャルを取得
  const getInitials = (name?: string) => {
    if (!name) return "?";
    return name.charAt(0);
  };

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* ヘッダー */}
      <div className="flex items-center gap-2 px-4 py-3 border-b">
        <MessageSquare className="h-5 w-5 text-gray-500" />
        <h3 className="font-semibold">コメント</h3>
        <span className="text-sm text-gray-500">({comments.length})</span>
      </div>

      {/* コメント一覧 */}
      <ScrollArea className="flex-1 p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : comments.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">コメントはありません</p>
          </div>
        ) : (
          <div className="space-y-4">
            {comments.map((comment) => (
              <div
                key={comment.id}
                className={cn(
                  "flex gap-3",
                  comment.is_internal && "bg-yellow-50 rounded-lg p-2 -m-2"
                )}
              >
                <Avatar className="h-8 w-8 flex-shrink-0">
                  <AvatarFallback className="text-xs bg-blue-100 text-blue-600">
                    {getInitials(comment.commented_by_name)}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-sm">
                      {comment.commented_by_name || "不明"}
                    </span>
                    <span className="text-xs text-gray-400">
                      {comment.created_at && !isNaN(new Date(comment.created_at).getTime())
                        ? format(new Date(comment.created_at), "M/d HH:mm", { locale: ja })
                        : "-"}
                    </span>
                    {comment.is_internal && (
                      <span className="inline-flex items-center gap-1 text-xs text-yellow-600 bg-yellow-100 px-1.5 py-0.5 rounded">
                        <Lock className="h-3 w-3" />
                        内部メモ
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap break-words">
                    {comment.comment}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* 入力フォーム */}
      <form onSubmit={handleSubmit} className="p-4 border-t space-y-3">
        <Textarea
          placeholder="コメントを入力..."
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          className="resize-none"
          rows={2}
        />
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="internal"
              checked={isInternal}
              onCheckedChange={(checked) => setIsInternal(checked === true)}
            />
            <Label
              htmlFor="internal"
              className="text-sm text-gray-600 cursor-pointer"
            >
              内部メモとして投稿
            </Label>
          </div>
          <Button
            type="submit"
            size="sm"
            disabled={!newComment.trim() || isSubmitting}
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <Send className="h-4 w-4 mr-1" />
                送信
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
