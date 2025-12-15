'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BottomNav } from '@/components/bottom-nav';
import {
  MessageCircle,
  Users,
  Send,
  Loader2,
  Search,
  ChevronLeft,
  Check,
  CheckCheck,
  Archive,
} from 'lucide-react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  getChannels,
  getChannel,
  getMessages,
  sendMessage,
  markChannelAsRead,
  archiveChannel,
  type Channel,
  type Message,
} from '@/lib/api/chat';
import { getAccessToken } from '@/lib/api/client';

export default function ChatPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'guardian' | 'group'>('guardian');
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 認証チェック
  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  // チャンネル一覧を取得
  useEffect(() => {
    loadChannels();
  }, [activeTab]);

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
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const loadChannels = async () => {
    try {
      setIsLoading(true);
      const channelType = activeTab === 'guardian' ? 'direct' : 'group';
      const data = await getChannels({ channelType, isArchived: false });
      setChannels(data);
    } catch (error) {
      console.error('Failed to load channels:', error);
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

      // 既読処理
      if (selectedChannel.unreadCount > 0) {
        await markChannelAsRead(selectedChannel.id);
        // ローカルの未読数を更新
        setChannels(prev =>
          prev.map(ch =>
            ch.id === selectedChannel.id ? { ...ch, unreadCount: 0 } : ch
          )
        );
      }
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!selectedChannel || !newMessage.trim() || isSending) return;

    const content = newMessage.trim();
    setNewMessage('');
    setIsSending(true);

    // 楽観的更新
    const tempMessage: Message = {
      id: `temp-${Date.now()}`,
      channel: selectedChannel.id,
      channelId: selectedChannel.id,
      senderName: 'あなた',
      messageType: 'text',
      content,
      isRead: false,
      isEdited: false,
      isBotMessage: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempMessage]);

    try {
      const sentMessage = await sendMessage({
        channelId: selectedChannel.id,
        content,
        messageType: 'text',
      });
      // 仮メッセージを実際のメッセージに置き換え
      setMessages(prev =>
        prev.map(msg => (msg.id === tempMessage.id ? sentMessage : msg))
      );
    } catch (error) {
      console.error('Failed to send message:', error);
      // 送信失敗時は仮メッセージを削除
      setMessages(prev => prev.filter(msg => msg.id !== tempMessage.id));
      setNewMessage(content);
      alert('メッセージの送信に失敗しました');
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleArchive = async (channelId: string) => {
    if (!confirm('このチャットをアーカイブしますか？')) return;

    try {
      await archiveChannel(channelId);
      setChannels(prev => prev.filter(ch => ch.id !== channelId));
      if (selectedChannel?.id === channelId) {
        setSelectedChannel(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to archive channel:', error);
      alert('アーカイブに失敗しました');
    }
  };

  // 検索フィルター
  const filteredChannels = channels.filter(channel => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      channel.name?.toLowerCase().includes(query) ||
      channel.guardian?.fullName?.toLowerCase().includes(query) ||
      channel.student?.fullName?.toLowerCase().includes(query)
    );
  });

  // 現在のユーザーIDを取得（JWTから）
  const getCurrentUserId = (): string => {
    if (typeof window === 'undefined') return '';
    const token = getAccessToken();
    if (!token) return '';
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.user_id || '';
    } catch {
      return '';
    }
  };

  const currentUserId = getCurrentUserId();

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-[390px] mx-auto">
        {/* ヘッダー */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <h1 className="text-2xl font-bold text-gray-900">チャット</h1>
            <p className="text-sm text-gray-600">保護者との連絡</p>
          </div>
        </div>

        <div className="p-4">
          {/* 検索 */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="チャットを検索..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="pl-10 rounded-full"
            />
          </div>

          {/* タブ */}
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'guardian' | 'group')} className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-4">
              <TabsTrigger value="guardian" className="text-xs">
                <MessageCircle className="w-4 h-4 mr-1" />
                保護者
              </TabsTrigger>
              <TabsTrigger value="group" className="text-xs">
                <Users className="w-4 h-4 mr-1" />
                グループ
              </TabsTrigger>
            </TabsList>

            <TabsContent value={activeTab} className="space-y-4">
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                </div>
              ) : filteredChannels.length === 0 ? (
                <Card className="p-8 text-center text-gray-500">
                  {searchQuery ? '検索結果がありません' : 'チャットがありません'}
                </Card>
              ) : (
                <div className="space-y-2">
                  {filteredChannels.map(channel => (
                    <Card
                      key={channel.id}
                      className={`p-3 cursor-pointer transition-all ${
                        selectedChannel?.id === channel.id
                          ? 'ring-2 ring-blue-500 bg-blue-50'
                          : 'hover:bg-gray-50'
                      }`}
                      onClick={() => setSelectedChannel(channel)}
                    >
                      <div className="flex items-center gap-3">
                        <Avatar className="bg-blue-100">
                          <AvatarFallback className="text-blue-600 text-sm font-semibold">
                            {(channel.guardian?.fullName || channel.name || '??').substring(0, 2)}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <h3 className="font-semibold text-gray-900 truncate">
                              {channel.guardian?.fullName || channel.name}
                            </h3>
                            {channel.unreadCount > 0 && (
                              <Badge className="bg-red-500 text-white">{channel.unreadCount}</Badge>
                            )}
                          </div>
                          {channel.lastMessage && (
                            <p className="text-xs text-gray-500 truncate">
                              {channel.lastMessage.content}
                            </p>
                          )}
                          {channel.student && (
                            <p className="text-xs text-gray-400">
                              生徒: {channel.student.fullName}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleArchive(channel.id);
                          }}
                          className="p-1 text-gray-400 hover:text-gray-600"
                          title="アーカイブ"
                        >
                          <Archive className="w-4 h-4" />
                        </button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}

              {/* チャット詳細 */}
              {selectedChannel && (
                <Card className="shadow-lg border-0 mt-4">
                  {/* チャットヘッダー */}
                  <div className="p-3 border-b flex items-center gap-3">
                    <button
                      onClick={() => {
                        setSelectedChannel(null);
                        setMessages([]);
                      }}
                      className="p-1"
                    >
                      <ChevronLeft className="w-5 h-5 text-gray-600" />
                    </button>
                    <Avatar className="bg-blue-100">
                      <AvatarFallback className="text-blue-600 text-sm font-semibold">
                        {(selectedChannel.guardian?.fullName || selectedChannel.name || '??').substring(0, 2)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900">
                        {selectedChannel.guardian?.fullName || selectedChannel.name}
                      </h3>
                      {selectedChannel.student && (
                        <p className="text-xs text-gray-500">
                          生徒: {selectedChannel.student.fullName}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* メッセージ一覧 */}
                  <ScrollArea className="h-80 p-3">
                    <div className="space-y-3">
                      {messages.length === 0 ? (
                        <p className="text-center text-gray-500 py-8">
                          メッセージがありません
                        </p>
                      ) : (
                        messages.map(message => {
                          const senderId = message.sender || message.senderId;
                          const isOwnMessage = senderId === currentUserId;
                          const isFromGuardian = !!message.senderGuardian;

                          return (
                            <div
                              key={message.id}
                              className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}
                            >
                              <div
                                className={`max-w-[75%] ${
                                  isOwnMessage
                                    ? 'bg-blue-500 text-white rounded-2xl rounded-br-md'
                                    : 'bg-gray-100 text-gray-900 rounded-2xl rounded-bl-md'
                                } p-3 shadow-sm`}
                              >
                                {!isOwnMessage && (
                                  <p className={`text-xs font-semibold mb-1 ${isFromGuardian ? 'text-blue-600' : 'text-gray-600'}`}>
                                    {message.senderName || (isFromGuardian ? '保護者' : 'スタッフ')}
                                  </p>
                                )}
                                <p className="text-sm break-words whitespace-pre-wrap">{message.content}</p>
                                <div className={`flex items-center gap-1 mt-1 ${isOwnMessage ? 'justify-end' : 'justify-start'}`}>
                                  <p className={`text-xs ${isOwnMessage ? 'text-blue-200' : 'text-gray-500'}`}>
                                    {format(new Date(message.createdAt), 'HH:mm', { locale: ja })}
                                  </p>
                                  {isOwnMessage && (
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
                  </ScrollArea>

                  {/* 入力エリア */}
                  <div className="p-3 border-t bg-white">
                    <div className="flex gap-2">
                      <Input
                        placeholder="メッセージを入力..."
                        value={newMessage}
                        onChange={e => setNewMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        disabled={isSending}
                        className="flex-1"
                      />
                      <Button
                        onClick={handleSendMessage}
                        disabled={!newMessage.trim() || isSending}
                        size="icon"
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
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
