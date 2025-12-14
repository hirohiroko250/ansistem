"use client";

import { useEffect, useState } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Search, Mail, MailOpen } from "lucide-react";
import { getMessages, Message } from "@/lib/api/staff";
import { format } from "date-fns";
import { ja } from "date-fns/locale";

export default function MessagesPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [filteredMessages, setFilteredMessages] = useState<Message[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMessages();
  }, []);

  useEffect(() => {
    if (searchQuery) {
      const filtered = messages.filter(
        (message) =>
          message.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
          message.content.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredMessages(filtered);
    } else {
      setFilteredMessages(messages);
    }
  }, [searchQuery, messages]);

  async function loadMessages() {
    setLoading(true);
    const data = await getMessages();
    setMessages(data);
    setFilteredMessages(data);
    setLoading(false);
  }

  const unreadMessages = messages.filter((m) => !m.read_at);

  return (
    <ThreePaneLayout>
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">メッセージ</h1>
          <p className="text-gray-600">
            {unreadMessages.length}件の未読メッセージがあります
          </p>
        </div>

        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <Input
              type="text"
              placeholder="件名、内容で検索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {loading ? (
          <div className="text-center text-gray-500 py-8">読み込み中...</div>
        ) : filteredMessages.length > 0 ? (
          <div className="space-y-2">
            {filteredMessages.map((message) => (
              <Card
                key={message.id}
                className="p-4 hover:shadow-md transition-all cursor-pointer"
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`p-3 rounded-lg ${
                      message.read_at ? "bg-gray-100" : "bg-blue-100"
                    }`}
                  >
                    {message.read_at ? (
                      <MailOpen className="w-5 h-5 text-gray-600" />
                    ) : (
                      <Mail className="w-5 h-5 text-blue-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3
                        className={`font-semibold text-gray-900 ${
                          !message.read_at && "font-bold"
                        }`}
                      >
                        {message.subject}
                      </h3>
                      {!message.read_at && (
                        <Badge variant="default" className="text-xs">
                          未読
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                      {message.content}
                    </p>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>
                        {message.sender_type === "staff" ? "社員" : "保護者"}
                      </span>
                      <span>→</span>
                      <span>
                        {message.receiver_type === "staff" ? "社員" : "保護者"}
                      </span>
                      <span>•</span>
                      <span>
                        {format(new Date(message.created_at), "yyyy年M月d日 HH:mm", {
                          locale: ja,
                        })}
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center text-gray-500 py-8">
            メッセージが見つかりませんでした
          </div>
        )}
      </div>
    </ThreePaneLayout>
  );
}
