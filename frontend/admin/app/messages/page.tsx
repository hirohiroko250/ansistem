"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Search,
  MessageCircle,
  Users,
  Send,
  Loader2,
  User,
  Building,
  Check,
  CheckCheck,
  RefreshCw,
  Archive,
  BarChart3,
  Maximize2,
  Minimize2,
  X,
} from "lucide-react";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import {
  getChannels,
  getChannel,
  getMessages,
  sendMessage,
  getChatLogs,
  getChatLogStatistics,
  type Channel,
  type Message,
  type ChatLog,
} from "@/lib/api/chat";

export default function MessagesPage() {
  const searchParams = useSearchParams();
  const channelIdParam = searchParams.get('channel');
  const guardianIdParam = searchParams.get('guardian');
  const [activeTab, setActiveTab] = useState<"channels" | "logs" | "stats">("channels");
  const [channels, setChannels] = useState<Channel[]>([]);
  const [chatLogs, setChatLogs] = useState<ChatLog[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [channelTypeFilter, setChannelTypeFilter] = useState<string>("all");
  const [statistics, setStatistics] = useState<{
    total_messages: number;
    by_sender_type: Record<string, number>;
    by_brand: Record<string, number>;
    by_school: Record<string, number>;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // フォーカスモード（URLパラメータで開いた場合）
  const isFocusMode = !!channelIdParam;
  const [windowSize, setWindowSize] = useState<"compact" | "normal" | "fullscreen">("normal");

  // チャンネル一覧を取得
  useEffect(() => {
    if (activeTab === "channels") {
      loadChannels();
    } else if (activeTab === "logs") {
      loadChatLogs();
    } else if (activeTab === "stats") {
      loadStatistics();
    }
  }, [activeTab, channelTypeFilter]);

  // URLパラメータからチャンネルを自動選択
  useEffect(() => {
    const loadChannelFromParam = async () => {
      if (channelIdParam && !selectedChannel) {
        try {
          const channel = await getChannel(channelIdParam);
          setSelectedChannel(channel);
        } catch (error) {
          console.error("Failed to load channel from param:", error);
        }
      }
    };
    loadChannelFromParam();
  }, [channelIdParam]);

  // 選択したチャンネルのメッセージを取得
  useEffect(() => {
    if (selectedChannel) {
      loadMessages();
    }
  }, [selectedChannel?.id]);

  // メッセージ更新時に自動スクロール
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const loadChannels = async () => {
    try {
      setIsLoading(true);
      const params: { channelType?: string; includeArchived?: boolean } = { includeArchived: true };
      if (channelTypeFilter !== "all") {
        params.channelType = channelTypeFilter;
      }
      const data = await getChannels(params);
      setChannels(data);
    } catch (error) {
      console.error("Failed to load channels:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadChatLogs = async () => {
    try {
      setIsLoading(true);
      const response = await getChatLogs({ pageSize: 100 });
      setChatLogs(response?.data || response?.results || []);
    } catch (error) {
      console.error("Failed to load chat logs:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      setIsLoading(true);
      const stats = await getChatLogStatistics();
      setStatistics(stats);
    } catch (error) {
      console.error("Failed to load statistics:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadMessages = async () => {
    if (!selectedChannel) return;

    try {
      const response = await getMessages(selectedChannel.id, { pageSize: 100 });
      const messageList = response?.data || response?.results || [];
      setMessages(messageList);
    } catch (error) {
      console.error("Failed to load messages:", error);
    }
  };

  const handleSendMessage = async () => {
    if (!selectedChannel || !newMessage.trim() || isSending) return;

    const content = newMessage.trim();
    setNewMessage("");
    setIsSending(true);

    // 楽観的更新
    const tempMessage: Message = {
      id: `temp-${Date.now()}`,
      channel: selectedChannel.id,
      channelId: selectedChannel.id,
      senderName: "管理者",
      messageType: "text",
      content,
      isRead: false,
      isEdited: false,
      isBotMessage: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempMessage]);

    try {
      const sentMessage = await sendMessage({
        channelId: selectedChannel.id,
        content,
        messageType: "text",
      });
      setMessages((prev) =>
        prev.map((msg) => (msg.id === tempMessage.id ? sentMessage : msg))
      );
    } catch (error) {
      console.error("Failed to send message:", error);
      setMessages((prev) => prev.filter((msg) => msg.id !== tempMessage.id));
      setNewMessage(content);
      alert("メッセージの送信に失敗しました");
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 検索フィルター
  const filteredChannels = channels.filter((channel) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      channel.name?.toLowerCase().includes(query) ||
      channel.guardian?.fullName?.toLowerCase().includes(query) ||
      channel.student?.fullName?.toLowerCase().includes(query) ||
      channel.school?.schoolName?.toLowerCase().includes(query)
    );
  });

  const filteredChatLogs = chatLogs.filter((log) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      log.content?.toLowerCase().includes(query) ||
      log.guardianName?.toLowerCase().includes(query) ||
      log.schoolName?.toLowerCase().includes(query)
    );
  });

  // フォーカスモード（特定のチャンネルだけを表示）- シンプルUI
  if (isFocusMode) {
    // チャンネル読み込み中
    if (!selectedChannel) {
      return (
        <div className="flex items-center justify-center h-screen bg-gray-50">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        </div>
      );
    }

    return (
      <div className="flex flex-col h-screen bg-gray-50">
        {/* シンプルヘッダー */}
        <div className="flex items-center gap-3 p-3 bg-white border-b">
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
            <User className="w-4 h-4 text-blue-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm truncate">
              {selectedChannel.guardian?.fullName || selectedChannel.name}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => window.close()}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* メッセージエリア */}
        <div className="flex-1 overflow-auto p-3">
          {messages.length === 0 ? (
            <p className="text-center text-gray-400 text-sm py-8">メッセージがありません</p>
          ) : (
            <div className="space-y-2">
              {messages.map((message) => {
                const isFromGuardian = !!message.senderGuardian;
                return (
                  <div key={message.id} className={`flex ${isFromGuardian ? "justify-start" : "justify-end"}`}>
                    <div className={`max-w-[75%] px-3 py-2 rounded-lg text-sm ${
                      isFromGuardian ? "bg-white shadow-sm" : "bg-blue-500 text-white"
                    }`}>
                      <p className="whitespace-pre-wrap">{message.content}</p>
                      <p className={`text-xs mt-1 ${isFromGuardian ? "text-gray-400" : "text-blue-200"}`}>
                        {format(new Date(message.createdAt), "HH:mm", { locale: ja })}
                      </p>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 入力エリア */}
        <div className="p-3 bg-white border-t">
          <div className="flex gap-2">
            <Input
              placeholder="メッセージ..."
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isSending}
              className="flex-1 h-9 text-sm"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!newMessage.trim() || isSending}
              size="sm"
              className="bg-blue-600 hover:bg-blue-700 h-9"
            >
              {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ThreePaneLayout>
      <div className="p-6 h-full flex flex-col">
        {/* ヘッダー */}
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-gray-900">チャット管理</h1>
          <p className="text-sm text-gray-600">保護者とのチャット履歴を管理</p>
        </div>

        {/* タブ */}
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)} className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-3 mb-4">
            <TabsTrigger value="channels">
              <MessageCircle className="w-4 h-4 mr-2" />
              チャンネル
            </TabsTrigger>
            <TabsTrigger value="logs">
              <Archive className="w-4 h-4 mr-2" />
              チャットログ
            </TabsTrigger>
            <TabsTrigger value="stats">
              <BarChart3 className="w-4 h-4 mr-2" />
              統計
            </TabsTrigger>
          </TabsList>

          {/* チャンネル一覧タブ */}
          <TabsContent value="channels" className="flex-1 flex flex-col gap-4">
            {/* フィルター */}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="チャンネルを検索..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Select value={channelTypeFilter} onValueChange={setChannelTypeFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="種別" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">すべて</SelectItem>
                  <SelectItem value="direct">個人</SelectItem>
                  <SelectItem value="group">グループ</SelectItem>
                  <SelectItem value="support">サポート</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon" onClick={loadChannels}>
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>

            <div className="flex-1 flex gap-4 min-h-0">
              {/* チャンネルリスト */}
              <Card className="w-1/3 flex flex-col">
                <CardHeader className="py-3 px-4">
                  <CardTitle className="text-sm">チャンネル ({filteredChannels.length})</CardTitle>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-2">
                  {isLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                    </div>
                  ) : filteredChannels.length === 0 ? (
                    <p className="text-center text-gray-500 py-4">
                      チャンネルがありません
                    </p>
                  ) : (
                    <div className="space-y-1">
                      {filteredChannels.map((channel) => (
                        <div
                          key={channel.id}
                          className={`p-2 rounded cursor-pointer transition-colors ${
                            selectedChannel?.id === channel.id
                              ? "bg-blue-100 border-blue-300"
                              : channel.isArchived
                              ? "bg-gray-50 opacity-60"
                              : "hover:bg-gray-50"
                          }`}
                          onClick={() => setSelectedChannel(channel)}
                        >
                          <div className="flex items-center gap-2">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                              channel.isArchived ? "bg-gray-200" : "bg-blue-100"
                            }`}>
                              {channel.channelType === "group" ? (
                                <Users className={`w-4 h-4 ${channel.isArchived ? "text-gray-400" : "text-blue-600"}`} />
                              ) : (
                                <User className={`w-4 h-4 ${channel.isArchived ? "text-gray-400" : "text-blue-600"}`} />
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-1">
                                <p className={`text-sm font-medium truncate ${channel.isArchived ? "text-gray-500" : ""}`}>
                                  {channel.guardian?.fullName || channel.name}
                                </p>
                                <div className="flex items-center gap-1 shrink-0">
                                  {channel.isArchived && (
                                    <Badge variant="outline" className="text-xs border-gray-400 text-gray-500">
                                      削除済み
                                    </Badge>
                                  )}
                                  {channel.unreadCount > 0 && !channel.isArchived && (
                                    <Badge className="bg-red-500 text-white text-xs">
                                      {channel.unreadCount}
                                    </Badge>
                                  )}
                                </div>
                              </div>
                              {channel.lastMessage && (
                                <p className="text-xs text-gray-500 truncate">
                                  {channel.lastMessage.content}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* メッセージ表示 */}
              <Card className="flex-1 flex flex-col">
                {selectedChannel ? (
                  <>
                    <CardHeader className="py-3 px-4 border-b">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          selectedChannel.isArchived ? "bg-gray-200" : "bg-blue-100"
                        }`}>
                          <User className={`w-5 h-5 ${selectedChannel.isArchived ? "text-gray-400" : "text-blue-600"}`} />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <CardTitle className="text-base">
                              {selectedChannel.guardian?.fullName || selectedChannel.name}
                            </CardTitle>
                            {selectedChannel.isArchived && (
                              <Badge variant="outline" className="text-xs border-gray-400 text-gray-500">
                                削除済み
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-gray-500">
                            {selectedChannel.student && (
                              <span className="flex items-center gap-1">
                                <User className="w-3 h-3" />
                                {selectedChannel.student.fullName}
                              </span>
                            )}
                            {selectedChannel.school && (
                              <span className="flex items-center gap-1">
                                <Building className="w-3 h-3" />
                                {selectedChannel.school.schoolName}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="flex-1 overflow-auto p-4">
                      <div className="space-y-3">
                        {messages.length === 0 ? (
                          <p className="text-center text-gray-500 py-8">
                            メッセージがありません
                          </p>
                        ) : (
                          messages.map((message) => {
                            const isFromGuardian = !!message.senderGuardian;
                            return (
                              <div
                                key={message.id}
                                className={`flex ${isFromGuardian ? "justify-start" : "justify-end"}`}
                              >
                                <div
                                  className={`max-w-[70%] ${
                                    isFromGuardian
                                      ? "bg-gray-100 text-gray-900 rounded-2xl rounded-bl-md"
                                      : "bg-blue-500 text-white rounded-2xl rounded-br-md"
                                  } p-3 shadow-sm`}
                                >
                                  {isFromGuardian && (
                                    <p className="text-xs font-semibold mb-1 text-blue-600">
                                      {message.senderName || "保護者"}
                                    </p>
                                  )}
                                  <p className="text-sm break-words whitespace-pre-wrap">
                                    {message.content}
                                  </p>
                                  <div className={`flex items-center gap-1 mt-1 ${isFromGuardian ? "justify-start" : "justify-end"}`}>
                                    <p className={`text-xs ${isFromGuardian ? "text-gray-500" : "text-blue-200"}`}>
                                      {format(new Date(message.createdAt), "M/d HH:mm", { locale: ja })}
                                    </p>
                                    {!isFromGuardian && (
                                      message.isRead ? (
                                        <CheckCheck className="h-3 w-3 text-blue-200" />
                                      ) : (
                                        <Check className="h-3 w-3 text-blue-200" />
                                      )
                                    )}
                                  </div>
                                </div>
                              </div>
                            );
                          })
                        )}
                        <div ref={messagesEndRef} />
                      </div>
                    </CardContent>
                    <div className="p-4 border-t">
                      <div className="flex gap-2">
                        <Input
                          placeholder="メッセージを入力..."
                          value={newMessage}
                          onChange={(e) => setNewMessage(e.target.value)}
                          onKeyPress={handleKeyPress}
                          disabled={isSending}
                          className="flex-1"
                        />
                        <Button
                          onClick={handleSendMessage}
                          disabled={!newMessage.trim() || isSending}
                          className="bg-blue-600 hover:bg-blue-700"
                        >
                          {isSending ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Send className="w-4 h-4" />
                          )}
                        </Button>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-gray-500">
                    <div className="text-center">
                      <MessageCircle className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                      <p>チャンネルを選択してください</p>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          </TabsContent>

          {/* チャットログタブ */}
          <TabsContent value="logs" className="flex-1 flex flex-col">
            <div className="mb-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="ログを検索..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Card className="flex-1 overflow-auto">
              <CardContent className="p-4">
                {isLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                  </div>
                ) : filteredChatLogs.length === 0 ? (
                  <p className="text-center text-gray-500 py-8">
                    チャットログがありません
                  </p>
                ) : (
                  <div className="space-y-2">
                    {filteredChatLogs.map((log) => (
                      <div key={log.id} className="p-3 border rounded-lg hover:bg-gray-50">
                        <div className="flex items-start justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <Badge
                              variant={log.senderType === "GUARDIAN" ? "default" : "secondary"}
                            >
                              {log.senderType === "GUARDIAN" ? "保護者" : log.senderType === "STAFF" ? "スタッフ" : "ボット"}
                            </Badge>
                            {log.guardianName && (
                              <span className="text-sm font-medium">{log.guardianName}</span>
                            )}
                          </div>
                          <span className="text-xs text-gray-500">
                            {format(new Date(log.timestamp), "yyyy/MM/dd HH:mm", { locale: ja })}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700">{log.content}</p>
                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                          {log.schoolName && (
                            <span className="flex items-center gap-1">
                              <Building className="w-3 h-3" />
                              {log.schoolName}
                            </span>
                          )}
                          {log.brandName && <span>{log.brandName}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* 統計タブ */}
          <TabsContent value="stats" className="flex-1">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
              </div>
            ) : statistics ? (
              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">総メッセージ数</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-3xl font-bold text-blue-600">
                      {statistics.total_messages.toLocaleString()}
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">送信者別</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {Object.entries(statistics.by_sender_type).map(([type, count]) => (
                        <div key={type} className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">
                            {type === "GUARDIAN" ? "保護者" : type === "STAFF" ? "スタッフ" : "ボット"}
                          </span>
                          <span className="font-medium">{count.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">ブランド別</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {Object.entries(statistics.by_brand).slice(0, 5).map(([brand, count]) => (
                        <div key={brand} className="flex items-center justify-between">
                          <span className="text-sm text-gray-600 truncate">{brand}</span>
                          <span className="font-medium">{count.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">校舎別</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {Object.entries(statistics.by_school).slice(0, 5).map(([school, count]) => (
                        <div key={school} className="flex items-center justify-between">
                          <span className="text-sm text-gray-600 truncate">{school}</span>
                          <span className="font-medium">{count.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            ) : (
              <p className="text-center text-gray-500 py-8">統計データがありません</p>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </ThreePaneLayout>
  );
}
