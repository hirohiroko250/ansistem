'use client';

import { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { ChevronLeft, Send, Headphones, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCreateChannel, useSendMessage, useChannelMessages } from '@/lib/hooks/use-chat';
import type { Channel, Message } from '@/lib/api/types';

// タイムスタンプをフォーマット
function formatMessageTime(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
}

// バックエンドのsnake_caseをフロントエンドのcamelCaseに変換
// eslint-disable @typescript-eslint/no-explicit-any -- API response mapping
function mapApiMessage(apiMessage: any): Message {
  return {
    id: apiMessage.id,
    channel: apiMessage.channel || apiMessage.channelId,
    channelId: apiMessage.channel || apiMessage.channelId,
    senderId: apiMessage.sender || apiMessage.senderId || '',
    senderName: apiMessage.sender_name || apiMessage.senderName || '',
    messageType: apiMessage.message_type || apiMessage.messageType || 'text',
    content: apiMessage.content || '',
    fileUrl: apiMessage.attachment_url || apiMessage.fileUrl,
    fileName: apiMessage.attachment_name || apiMessage.fileName,
    isRead: apiMessage.is_read ?? apiMessage.isRead ?? false,
    readAt: apiMessage.read_at || apiMessage.readAt,
    createdAt: apiMessage.created_at || apiMessage.createdAt,
    isBotMessage: apiMessage.is_bot_message ?? apiMessage.isBotMessage ?? false,
  };
}

function NewChatContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialMessage = searchParams.get('message') || '';

  const [channel, setChannel] = useState<Channel | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState(initialMessage);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasAutoSent, setHasAutoSent] = useState(false);
  const isAutoSending = useRef(false); // 重複防止用フラグ

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // React Query mutations
  const createChannelMutation = useCreateChannel();
  const sendMessageMutation = useSendMessage();
  const { data: channelMessages } = useChannelMessages(channel?.id);

  const isSending = createChannelMutation.isPending || sendMessageMutation.isPending;

  // チャンネル作成後にメッセージを取得して表示
  useEffect(() => {
    if (channelMessages && channelMessages.length > 0) {
      setMessages(channelMessages.map(mapApiMessage));
    }
  }, [channelMessages]);

  // スクロールを最下部へ
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // メッセージ更新時にスクロール
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // 初期メッセージがある場合は自動送信（1回のみ）
  useEffect(() => {
    if (initialMessage && !channel && !isLoading && !isSending && !hasAutoSent && !isAutoSending.current) {
      isAutoSending.current = true;
      setHasAutoSent(true);
      handleSendMessage();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialMessage, hasAutoSent]);

  // メッセージ送信（チャンネル作成含む）
  const handleSendMessage = async () => {
    if (!inputValue.trim() || isSending) return;

    const messageContent = inputValue.trim();
    const tempMessageId = `temp-${Date.now()}`;
    setInputValue('');
    setError(null);

    try {
      let currentChannel = channel;

      // チャンネルがない場合は新規作成
      if (!currentChannel) {
        setIsLoading(true);
        const newChannel = await createChannelMutation.mutateAsync({
          channel_type: 'SUPPORT',
          name: '明細お問い合わせ',
        });
        currentChannel = newChannel;
        setChannel(newChannel);
        setIsLoading(false);
      }

      // 楽観的更新: 送信中のメッセージを仮表示
      const tempMessage: Message = {
        id: tempMessageId,
        channel: currentChannel.id,
        channelId: currentChannel.id,
        senderId: 'me',
        senderName: 'あなた',
        messageType: 'text',
        content: messageContent,
        isRead: false,
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, tempMessage]);

      // メッセージを送信
      const sentMessageRaw = await sendMessageMutation.mutateAsync({
        channelId: currentChannel.id,
        content: messageContent,
        messageType: 'text',
      });
      const sentMessage = mapApiMessage(sentMessageRaw);

      // 仮メッセージを実際のメッセージに置き換え
      setMessages((prev) =>
        prev.map((msg) => (msg.id === tempMessageId ? sentMessage : msg))
      );

      // チャンネル作成後、詳細ページに遷移
      if (!channel) {
        router.replace(`/chat/${currentChannel.id}`);
      }

    } catch (err) {
      console.error('Failed to send message:', err);
      setError('メッセージの送信に失敗しました');
      // 仮メッセージを削除
      setMessages((prev) => prev.filter((msg) => msg.id !== tempMessageId));
      // 入力値を復元
      setInputValue(messageContent);
    }
  };

  // Enterキーで送信
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // ローディング表示（チャンネル作成中）
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex flex-col">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
            <Link href="/chat" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <div className="h-10 w-10 bg-gray-200 rounded-full animate-pulse mr-3" />
            <div className="h-5 w-32 bg-gray-200 rounded animate-pulse" />
          </div>
        </header>
        <div className="flex-1 flex flex-col items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-2" />
          <p className="text-gray-600 text-sm">チャットを開始しています...</p>
        </div>
        <BottomTabBar />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex flex-col">
      {/* ヘッダー */}
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/chat" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <Avatar className="bg-gradient-to-br from-green-500 to-teal-600 mr-3">
            <AvatarFallback className="text-white">
              <Headphones className="h-5 w-5" />
            </AvatarFallback>
          </Avatar>
          <div>
            <h1 className="text-lg font-bold text-gray-800">新規チャット</h1>
            <p className="text-xs text-gray-500">事務局へのお問い合わせ</p>
          </div>
        </div>
      </header>

      {/* メッセージ一覧 */}
      <main className="flex-1 max-w-[390px] mx-auto w-full px-4 py-4 overflow-y-auto pb-32">
        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">
            {error}
          </div>
        )}

        <div className="space-y-4">
          {messages.length === 0 && !initialMessage && (
            <div className="text-center text-gray-500 py-8">
              <Headphones className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p className="text-sm">事務局へのお問い合わせチャットです</p>
              <p className="text-xs text-gray-400 mt-1">メッセージを送信してください</p>
            </div>
          )}

          {messages.map((message) => {
            // ボットメッセージは左側（相手側）に表示
            const isOwnMessage = !message.isBotMessage && (message.senderId === 'me' || message.senderName === 'あなた');

            return (
              <div key={message.id}>
                <div
                  className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[75%] ${isOwnMessage
                        ? 'bg-blue-500 text-white'
                        : 'bg-gradient-to-br from-green-100 to-teal-100 text-gray-800'
                      } rounded-2xl px-4 py-3`}
                  >
                    {/* 送信者名（自分以外） */}
                    {!isOwnMessage && (
                      <p className="text-xs font-medium text-gray-600 mb-1">
                        {message.isBotMessage ? '事務局（自動応答）' : message.senderName || '事務局'}
                      </p>
                    )}
                    <p className="text-sm break-words whitespace-pre-wrap">
                      {message.content}
                    </p>
                    <p
                      className={`text-xs mt-1 ${isOwnMessage ? 'text-blue-100' : 'text-gray-500'
                        }`}
                    >
                      {formatMessageTime(message.createdAt)}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* 入力エリア */}
      <div className="fixed bottom-16 left-0 right-0 bg-white border-t px-4 py-3 z-30">
        <div className="max-w-[390px] mx-auto flex items-center gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="メッセージを入力..."
            className="flex-1 rounded-full border-2 px-4"
            disabled={isSending}
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isSending}
            className="h-10 w-10 rounded-full bg-green-600 hover:bg-green-700 p-0 flex items-center justify-center"
          >
            {isSending ? (
              <Loader2 className="h-5 w-5 text-white animate-spin" />
            ) : (
              <Send className="h-5 w-5 text-white" />
            )}
          </Button>
        </div>
      </div>

      <BottomTabBar />
    </div>
  );
}

export default function NewChatPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    }>
      <NewChatContent />
    </Suspense>
  );
}
