"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Task } from "@/lib/api/staff";
import {
  getOrCreateChannelForGuardian,
  getMessages,
  sendMessage,
  Channel,
  Message,
} from "@/lib/api/chat";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Loader2, Send, MessageCircle, AlertCircle } from "lucide-react";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { cn } from "@/lib/utils";

interface TaskChatTabProps {
  task: Task;
}

export function TaskChatTab({ task }: TaskChatTabProps) {
  const [channel, setChannel] = useState<Channel | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [newMessage, setNewMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // 保護者IDを取得（フォールバック付き）
  const guardianId =
    task.guardian ||
    task.guardian_detail?.id ||
    task.student_detail?.guardian_id ||
    null;

  // チャンネル初期化
  const initChannel = useCallback(async () => {
    if (!guardianId) {
      setIsLoading(false);
      setError("このタスクに保護者が紐付けられていないため、チャットを利用できません。");
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const ch = await getOrCreateChannelForGuardian(guardianId);
      setChannel(ch);

      // メッセージ取得
      const res = await getMessages(ch.id, { pageSize: 50 });
      const msgs = res?.data || res?.results || [];
      setMessages(msgs);
    } catch (err) {
      console.error("チャンネル初期化エラー:", err);
      setError("チャットの読み込みに失敗しました。");
    } finally {
      setIsLoading(false);
    }
  }, [guardianId]);

  useEffect(() => {
    initChannel();
  }, [initChannel]);

  // ポーリング（5秒間隔）
  useEffect(() => {
    if (!channel) return;

    const poll = async () => {
      try {
        const res = await getMessages(channel.id, { pageSize: 50 });
        const msgs = res?.data || res?.results || [];
        setMessages(msgs);
      } catch {
        // ポーリングエラーは静かに無視
      }
    };

    pollingRef.current = setInterval(poll, 5000);
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [channel]);

  // スクロールを最下部に
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // メッセージ送信
  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !channel || isSending) return;

    setIsSending(true);
    try {
      const sent = await sendMessage({
        channelId: channel.id,
        content: newMessage.trim(),
      });
      setMessages((prev) => [...prev, sent]);
      setNewMessage("");
    } catch (err) {
      console.error("送信エラー:", err);
    } finally {
      setIsSending(false);
    }
  };

  // キーボードショートカット
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSend(e as unknown as React.FormEvent);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-12">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400 mr-2" />
        <span className="text-sm text-gray-500">チャットを読み込み中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-12 px-4">
        <AlertCircle className="h-10 w-10 text-gray-300 mb-3" />
        <p className="text-sm text-gray-500 text-center">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* チャンネル情報 */}
      <div className="px-4 py-2 border-b bg-gray-50">
        <p className="text-xs text-gray-500">
          保護者: {task.guardian_detail?.full_name || task.guardian_name || "不明"}
        </p>
      </div>

      {/* メッセージ一覧 */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <MessageCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">メッセージはありません</p>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((msg) => {
              const isGuardian = !!msg.senderGuardian || !!msg.senderGuardianName;
              const senderName =
                msg.senderGuardianName || msg.senderName || "不明";
              const createdAt = msg.createdAt || msg.updatedAt;
              const isValidDate =
                createdAt && !isNaN(new Date(createdAt).getTime());

              return (
                <div
                  key={msg.id}
                  className={cn(
                    "flex gap-2",
                    !isGuardian && "flex-row-reverse"
                  )}
                >
                  <Avatar className="h-7 w-7 flex-shrink-0">
                    <AvatarFallback
                      className={cn(
                        "text-xs",
                        isGuardian
                          ? "bg-green-100 text-green-600"
                          : "bg-blue-100 text-blue-600"
                      )}
                    >
                      {senderName.charAt(0)}
                    </AvatarFallback>
                  </Avatar>
                  <div
                    className={cn(
                      "max-w-[75%]",
                      !isGuardian && "text-right"
                    )}
                  >
                    <p className="text-xs text-gray-400 mb-0.5">
                      {senderName}
                      {isValidDate && (
                        <span className="ml-2">
                          {format(new Date(createdAt), "M/d HH:mm", {
                            locale: ja,
                          })}
                        </span>
                      )}
                    </p>
                    <div
                      className={cn(
                        "inline-block px-3 py-2 rounded-lg text-sm whitespace-pre-wrap break-words",
                        isGuardian
                          ? "bg-gray-100 text-gray-800"
                          : "bg-blue-500 text-white"
                      )}
                    >
                      {msg.content}
                    </div>
                    {msg.attachmentUrl || msg.attachment_url ? (
                      <a
                        href={msg.attachmentUrl || msg.attachment_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-xs text-blue-500 underline mt-1"
                      >
                        {msg.attachmentName || msg.attachment_name || "添付ファイル"}
                      </a>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </ScrollArea>

      {/* 入力フォーム */}
      <form onSubmit={handleSend} className="p-3 border-t space-y-2">
        <Textarea
          placeholder="メッセージを入力... (Ctrl+Enter で送信)"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          className="resize-none text-sm"
          rows={2}
        />
        <div className="flex justify-end">
          <Button
            type="submit"
            size="sm"
            disabled={!newMessage.trim() || isSending}
          >
            {isSending ? (
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
