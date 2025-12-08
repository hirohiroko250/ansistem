'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { ChevronLeft, Send, Bot, Loader2, Check, CheckCheck, Trash2, X, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import { getChannel, getMessages, sendMessage, markChannelAsRead, chatWithBot, deleteMessage } from '@/lib/api/chat';
import type { Channel, Message } from '@/lib/api/types';

// AIアシスタントのID
const AI_ASSISTANT_ID = 'ai-assistant';

// タイムスタンプをフォーマット
function formatMessageTime(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
}

// 現在のユーザーID（実際にはAuthコンテキストから取得）
function getCurrentUserId(): string {
  // TODO: 実際のユーザーIDをAuthコンテキストから取得
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.user_id || '';
      } catch {
        return '';
      }
    }
  }
  return '';
}

export default function ChatConversationPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const channelId = params.id as string;
  const isAiAssistant = channelId === AI_ASSISTANT_ID;
  const initialMessage = searchParams.get('message') || '';

  const [channel, setChannel] = useState<Channel | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState(initialMessage);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const longPressTimerRef = useRef<NodeJS.Timeout | null>(null);
  const currentUserId = getCurrentUserId();

  // スクロールを最下部へ
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // チャンネル情報とメッセージを取得
  useEffect(() => {
    async function fetchData() {
      try {
        setIsLoading(true);
        setError(null);

        // AIアシスタントの場合は特別な処理
        if (isAiAssistant) {
          // 仮想的なAIチャンネルを設定
          setChannel({
            id: AI_ASSISTANT_ID,
            channelType: 'support',
            name: 'AIアシスタント',
            isActive: true,
            unreadCount: 0,
            createdAt: new Date().toISOString(),
          });
          // ウェルカムメッセージを設定
          setMessages([
            {
              id: 'welcome-message',
              channelId: AI_ASSISTANT_ID,
              senderId: 'ai',
              senderName: 'AIアシスタント',
              messageType: 'text',
              content: 'こんにちは！何かお手伝いできることはありますか？\n\n授業のこと、予約のこと、料金のことなど、何でもお気軽にお聞きください。',
              isRead: true,
              createdAt: new Date().toISOString(),
            },
          ]);
          setIsLoading(false);
          return;
        }

        // チャンネル情報とメッセージを並列取得
        const [channelData, messagesData] = await Promise.all([
          getChannel(channelId),
          getMessages(channelId, { pageSize: 50 }),
        ]);

        setChannel(channelData);
        // バックエンドは data フィールドを使用、標準DRFは results を使用
        // APIは古い順（created_at昇順）で返すため、そのまま使用
        const messageList = messagesData?.data || messagesData?.results || [];
        setMessages(Array.isArray(messageList) ? messageList : []);

        // 既読処理
        if (channelData.unreadCount > 0) {
          try {
            await markChannelAsRead(channelId);
          } catch (err) {
            console.error('Failed to mark as read:', err);
          }
        }
      } catch (err) {
        console.error('Failed to fetch chat data:', err);
        setError('チャットの取得に失敗しました');
      } finally {
        setIsLoading(false);
      }
    }

    fetchData();
  }, [channelId, isAiAssistant]);

  // メッセージ更新時にスクロール
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // メッセージ送信
  const handleSendMessage = async () => {
    if (!inputValue.trim() || isSending) return;

    const messageContent = inputValue.trim();
    setInputValue('');
    setIsSending(true);

    // 楽観的更新: 送信中のメッセージを仮表示
    const tempMessage: Message = {
      id: `temp-${Date.now()}`,
      channelId,
      senderId: currentUserId,
      senderName: 'あなた',
      messageType: 'text',
      content: messageContent,
      isRead: false,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempMessage]);

    try {
      // AIアシスタントの場合はボットAPIを使用
      if (isAiAssistant) {
        const botResponse = await chatWithBot(messageContent);
        // ユーザーメッセージを確定
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === tempMessage.id
              ? { ...tempMessage, id: `user-${Date.now()}`, isRead: true }
              : msg
          )
        );
        // ボットの応答を追加
        const aiMessage: Message = {
          id: `ai-${Date.now()}`,
          channelId: AI_ASSISTANT_ID,
          senderId: 'ai',
          senderName: 'AIアシスタント',
          messageType: 'text',
          content: botResponse.response,
          isRead: true,
          createdAt: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMessage]);
      } else {
        const sentMessage = await sendMessage({
          channelId,
          content: messageContent,
          messageType: 'text',
        });

        // 仮メッセージを実際のメッセージに置き換え
        setMessages((prev) =>
          prev.map((msg) => (msg.id === tempMessage.id ? sentMessage : msg))
        );
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      // 送信失敗時は仮メッセージを削除
      setMessages((prev) => prev.filter((msg) => msg.id !== tempMessage.id));
      // 入力値を復元
      setInputValue(messageContent);
      alert('メッセージの送信に失敗しました');
    } finally {
      setIsSending(false);
    }
  };

  // Enterキーで送信
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 長押し開始（モバイル）
  const handleTouchStart = (messageId: string, isOwnMessage: boolean) => {
    if (!isOwnMessage) return;
    longPressTimerRef.current = setTimeout(() => {
      setSelectedMessageId(messageId);
    }, 500);
  };

  // 長押し終了（モバイル）
  const handleTouchEnd = () => {
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }
  };

  // 右クリック（PC）
  const handleContextMenu = (e: React.MouseEvent, messageId: string, isOwnMessage: boolean) => {
    if (!isOwnMessage) return;
    e.preventDefault();
    setSelectedMessageId(messageId);
  };

  // メッセージ削除
  const handleDeleteMessage = async () => {
    if (!selectedMessageId || isDeleting) return;

    setIsDeleting(true);
    try {
      await deleteMessage(selectedMessageId);
      // UIから削除
      setMessages((prev) => prev.filter((m) => m.id !== selectedMessageId));
      setSelectedMessageId(null);
    } catch (err) {
      console.error('Failed to delete message:', err);
      alert('メッセージの削除に失敗しました');
    } finally {
      setIsDeleting(false);
    }
  };

  // コピー
  const handleCopyMessage = () => {
    const message = messages.find((m) => m.id === selectedMessageId);
    if (message?.content) {
      navigator.clipboard.writeText(message.content);
      setSelectedMessageId(null);
    }
  };

  // チャンネルタイプ判定
  const isBot = isAiAssistant || channel?.channelType === 'support';
  const channelName = channel?.name || 'チャット';

  // ローディング表示
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
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
        <BottomTabBar />
      </div>
    );
  }

  // エラー表示
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex flex-col">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
            <Link href="/chat" className="mr-3">
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </Link>
            <h1 className="text-lg font-bold text-gray-800">エラー</h1>
          </div>
        </header>
        <div className="flex-1 flex flex-col items-center justify-center px-4">
          <p className="text-red-600 text-center mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg"
          >
            再読み込み
          </button>
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
          <Avatar className={isBot ? 'bg-gradient-to-br from-blue-500 to-purple-600 mr-3' : 'bg-blue-100 mr-3'}>
            <AvatarFallback className={isBot ? 'text-white' : 'text-blue-600 font-semibold'}>
              {isBot ? <Bot className="h-5 w-5" /> : channelName.substring(0, 2)}
            </AvatarFallback>
          </Avatar>
          <div>
            <h1 className="text-lg font-bold text-gray-800">{channelName}</h1>
            <p className="text-xs text-green-600">オンライン</p>
          </div>
        </div>
      </header>

      {/* メッセージ一覧 */}
      <main className="flex-1 max-w-[390px] mx-auto w-full px-4 py-4 overflow-y-auto pb-32">
        <div className="space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              メッセージはありません
            </div>
          )}

          {messages.map((message) => {
            // 自分のメッセージかどうか判定（sender または senderId で比較、または senderGuardian が存在する = 保護者）
            const senderId = message.sender || message.senderId;
            const isOwnMessage = senderId === currentUserId ||
                                (message.senderGuardian && senderId === currentUserId);
            // 本部/アシスタント/ボットからのメッセージ = 左側（自分以外でかつsenderGuardianが無い、またはisBotMessage）
            const isFromHQ = message.isBotMessage || (!message.senderGuardian && senderId !== currentUserId);

            return (
              <div key={message.id} className="relative">
                <div
                  className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[75%] ${
                      isOwnMessage
                        ? 'bg-blue-500 text-white rounded-2xl rounded-br-md'
                        : isFromHQ
                        ? 'bg-gray-100 text-gray-800 rounded-2xl rounded-bl-md'
                        : 'bg-white text-gray-800 shadow-md rounded-2xl rounded-bl-md'
                    } px-4 py-3 ${isOwnMessage ? 'cursor-pointer select-none' : ''}`}
                    onTouchStart={() => handleTouchStart(message.id, isOwnMessage)}
                    onTouchEnd={handleTouchEnd}
                    onTouchMove={handleTouchEnd}
                    onContextMenu={(e) => handleContextMenu(e, message.id, isOwnMessage)}
                  >
                    {/* 送信者名（自分以外） */}
                    {!isOwnMessage && (
                      <p className={`text-xs font-medium mb-1 ${isFromHQ ? 'text-blue-600' : 'text-gray-600'}`}>
                        {message.isBotMessage ? 'アシスタント' : message.senderName}
                      </p>
                    )}
                    <p className="text-sm break-words whitespace-pre-wrap">
                      {message.content}
                    </p>
                    <div
                      className={`flex items-center gap-1 mt-1 ${
                        isOwnMessage ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <span className={`text-xs ${isOwnMessage ? 'text-blue-100' : 'text-gray-500'}`}>
                        {formatMessageTime(message.createdAt)}
                      </span>
                      {/* 自分のメッセージの場合に既読マークを表示 */}
                      {isOwnMessage && (
                        message.isRead ? (
                          <CheckCheck className="h-3.5 w-3.5 text-blue-200" />
                        ) : (
                          <Check className="h-3.5 w-3.5 text-blue-200" />
                        )
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* メッセージアクションモーダル */}
      {selectedMessageId && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-end justify-center"
          onClick={() => setSelectedMessageId(null)}
        >
          <div
            className="bg-white w-full max-w-[390px] rounded-t-2xl p-4 pb-8 animate-in slide-in-from-bottom duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-12 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <div className="space-y-2">
              <button
                onClick={handleCopyMessage}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <Copy className="h-5 w-5 text-gray-600" />
                <span className="text-gray-800">コピー</span>
              </button>
              <button
                onClick={handleDeleteMessage}
                disabled={isDeleting}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-red-50 transition-colors text-red-600"
              >
                {isDeleting ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Trash2 className="h-5 w-5" />
                )}
                <span>削除</span>
              </button>
              <button
                onClick={() => setSelectedMessageId(null)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors mt-2"
              >
                <X className="h-5 w-5 text-gray-600" />
                <span className="text-gray-600">キャンセル</span>
              </button>
            </div>
          </div>
        </div>
      )}

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
            className="h-10 w-10 rounded-full bg-blue-600 hover:bg-blue-700 p-0 flex items-center justify-center"
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
