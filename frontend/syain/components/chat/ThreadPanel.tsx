'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  X,
  Send,
  Loader2,
  MessageSquare,
} from 'lucide-react';
import { format, isToday, isYesterday } from 'date-fns';
import { ja } from 'date-fns/locale';
import { getThread, sendThreadReply, type Message, type ThreadResponse } from '@/lib/api/chat';

interface ThreadPanelProps {
  parentMessage: Message;
  channelId: string;
  currentUserId: string;
  onClose: () => void;
  onReplyCountUpdate?: (messageId: string, count: number) => void;
}

export function ThreadPanel({
  parentMessage,
  channelId,
  currentUserId,
  onClose,
  onReplyCountUpdate,
}: ThreadPanelProps) {
  const [replies, setReplies] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [newReply, setNewReply] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const fetchReplies = useCallback(async () => {
    try {
      setIsLoading(true);
      const response: ThreadResponse = await getThread(parentMessage.id);
      setReplies(response.replies || []);
    } catch (error) {
      console.error('Failed to fetch thread:', error);
    } finally {
      setIsLoading(false);
    }
  }, [parentMessage.id]);

  useEffect(() => {
    fetchReplies();
  }, [fetchReplies]);

  useEffect(() => {
    scrollToBottom();
  }, [replies, scrollToBottom]);

  const handleSendReply = async () => {
    if (!newReply.trim() || isSending) return;

    try {
      setIsSending(true);
      const reply = await sendThreadReply({
        channelId,
        parentMessageId: parentMessage.id,
        content: newReply.trim(),
      });
      setReplies(prev => [...prev, reply]);
      setNewReply('');
      inputRef.current?.focus();

      // 親コンポーネントに返信数更新を通知
      if (onReplyCountUpdate) {
        onReplyCountUpdate(parentMessage.id, replies.length + 1);
      }
    } catch (error) {
      console.error('Failed to send reply:', error);
    } finally {
      setIsSending(false);
    }
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    if (isToday(date)) {
      return format(date, 'HH:mm');
    }
    if (isYesterday(date)) {
      return `昨日 ${format(date, 'HH:mm')}`;
    }
    return format(date, 'M/d HH:mm', { locale: ja });
  };

  const renderMessage = (message: Message, isParent: boolean = false) => {
    const senderId = message.sender || message.senderId;
    const isOwnMessage = senderId === currentUserId;

    return (
      <div
        key={message.id}
        className={`flex items-start gap-2 ${isOwnMessage ? 'flex-row-reverse' : ''}`}
      >
        <Avatar className="w-8 h-8 flex-shrink-0">
          <AvatarFallback className={`text-xs ${isOwnMessage ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
            {(message.senderName || '?').substring(0, 2)}
          </AvatarFallback>
        </Avatar>

        <div className={`flex flex-col ${isOwnMessage ? 'items-end' : 'items-start'} max-w-[75%]`}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-gray-700">
              {message.senderName || '不明'}
            </span>
            <span className="text-xs text-gray-400">
              {formatTime(message.createdAt)}
            </span>
          </div>

          <div
            className={`px-3 py-2 rounded-lg ${
              isOwnMessage
                ? 'bg-[#A8D86D] text-gray-800'
                : 'bg-white text-gray-800 border border-gray-200'
            } ${isParent ? 'border-l-4 border-l-blue-400' : ''}`}
          >
            <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-gray-50 border-l border-gray-200">
      {/* ヘッダー */}
      <div className="flex-shrink-0 bg-white px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-gray-600" />
          <h2 className="font-semibold text-gray-900">スレッド</h2>
          <span className="text-sm text-gray-500">
            {replies.length}件の返信
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded-full transition-colors"
        >
          <X className="w-5 h-5 text-gray-500" />
        </button>
      </div>

      {/* メッセージエリア */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 親メッセージ */}
        <div className="pb-4 border-b border-gray-200">
          {renderMessage(parentMessage, true)}
        </div>

        {/* ローディング */}
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
          </div>
        ) : replies.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500 text-sm">まだ返信がありません</p>
            <p className="text-gray-400 text-xs mt-1">最初の返信を送ってください</p>
          </div>
        ) : (
          /* 返信一覧 */
          <div className="space-y-3">
            {replies.map(reply => renderMessage(reply))}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 入力エリア */}
      <div className="flex-shrink-0 bg-white px-3 py-3 border-t border-gray-200">
        <div className="flex items-center gap-2">
          <Input
            ref={inputRef}
            placeholder="返信を入力..."
            value={newReply}
            onChange={e => setNewReply(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                handleSendReply();
              }
            }}
            disabled={isSending}
            className="flex-1 rounded-full bg-gray-100 border-0"
          />
          <Button
            onClick={handleSendReply}
            disabled={!newReply.trim() || isSending}
            size="icon"
            className="rounded-full bg-blue-600 hover:bg-blue-700 w-9 h-9"
          >
            {isSending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
