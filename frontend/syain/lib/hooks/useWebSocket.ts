/**
 * WebSocket Hook for Chat
 * チャット用WebSocket Reactフック
 */
'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { ChatWebSocket, ChatMessage, TypingUser } from '../websocket';

interface ThreadReplyEvent {
  parentMessageId: string;
  reply: ChatMessage;
  replyCount: number;
}

interface ReactionAddedEvent {
  messageId: string;
  emoji: string;
  userId: string;
  userName: string;
}

interface ReactionRemovedEvent {
  messageId: string;
  emoji: string;
  userId: string;
}

interface UseWebSocketOptions {
  onMessage?: (message: ChatMessage) => void;
  onTyping?: (typing: TypingUser) => void;
  onUserJoin?: (event: { userId: string; userName: string }) => void;
  onUserLeave?: (event: { userId: string; userName: string }) => void;
  onThreadReply?: (event: ThreadReplyEvent) => void;
  onReactionAdded?: (event: ReactionAddedEvent) => void;
  onReactionRemoved?: (event: ReactionRemovedEvent) => void;
  autoConnect?: boolean;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  connectionStatus: 'connected' | 'disconnected' | 'reconnecting';
  sendMessage: (content: string, replyTo?: string) => void;
  sendTyping: (isTyping: boolean) => void;
  markAsRead: (messageId: string) => void;
  connect: () => void;
  disconnect: () => void;
}

/**
 * チャット用WebSocket フック
 */
export function useChatWebSocket(
  channelId: string | null,
  token: string | null,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const wsRef = useRef<ChatWebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'reconnecting'>('disconnected');

  const { onMessage, onTyping, onUserJoin, onUserLeave, onThreadReply, onReactionAdded, onReactionRemoved, autoConnect = true } = options;

  // WebSocket接続
  const connect = useCallback(() => {
    if (!channelId || !token) return;

    // 既存の接続があれば切断
    if (wsRef.current) {
      wsRef.current.disconnect();
    }

    // 新しい接続を作成
    const ws = new ChatWebSocket(channelId, token);

    // イベントハンドラを設定
    ws.onConnectionChange((status) => {
      setConnectionStatus(status);
      setIsConnected(status === 'connected');
    });

    if (onMessage) {
      ws.onMessage(onMessage);
    }

    if (onTyping) {
      ws.onTyping(onTyping);
    }

    if (onUserJoin) {
      ws.onUserJoin(onUserJoin);
    }

    if (onUserLeave) {
      ws.onUserLeave(onUserLeave);
    }

    if (onThreadReply) {
      ws.onThreadReply(onThreadReply);
    }

    if (onReactionAdded) {
      ws.onReactionAdded(onReactionAdded);
    }

    if (onReactionRemoved) {
      ws.onReactionRemoved(onReactionRemoved);
    }

    ws.connect();
    wsRef.current = ws;
  }, [channelId, token, onMessage, onTyping, onUserJoin, onUserLeave, onThreadReply, onReactionAdded, onReactionRemoved]);

  // WebSocket切断
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
    }
    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, []);

  // メッセージ送信
  const sendMessage = useCallback((content: string, replyTo?: string) => {
    wsRef.current?.sendMessage(content, replyTo);
  }, []);

  // タイピング状態送信
  const sendTyping = useCallback((isTyping: boolean) => {
    wsRef.current?.sendTyping(isTyping);
  }, []);

  // 既読処理
  const markAsRead = useCallback((messageId: string) => {
    wsRef.current?.markAsRead(messageId);
  }, []);

  // 自動接続（channelIdとtokenが変わった時のみ再接続）
  useEffect(() => {
    if (autoConnect && channelId && token) {
      // 既存の接続があれば切断
      if (wsRef.current) {
        wsRef.current.disconnect();
      }

      // 新しい接続を作成
      const ws = new ChatWebSocket(channelId, token);

      // イベントハンドラを設定
      ws.onConnectionChange((status) => {
        setConnectionStatus(status);
        setIsConnected(status === 'connected');
      });

      if (onMessage) ws.onMessage(onMessage);
      if (onTyping) ws.onTyping(onTyping);
      if (onUserJoin) ws.onUserJoin(onUserJoin);
      if (onUserLeave) ws.onUserLeave(onUserLeave);
      if (onThreadReply) ws.onThreadReply(onThreadReply);
      if (onReactionAdded) ws.onReactionAdded(onReactionAdded);
      if (onReactionRemoved) ws.onReactionRemoved(onReactionRemoved);

      ws.connect();
      wsRef.current = ws;
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }
      setIsConnected(false);
      setConnectionStatus('disconnected');
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channelId, token, autoConnect]);

  return {
    isConnected,
    connectionStatus,
    sendMessage,
    sendTyping,
    markAsRead,
    connect,
    disconnect,
  };
}

/**
 * タイピングインジケータ用フック
 */
export function useTypingIndicator(
  sendTyping: (isTyping: boolean) => void,
  delay: number = 2000
) {
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isTypingRef = useRef(false);

  const handleTyping = useCallback(() => {
    // まだタイピング中でなければ開始を通知
    if (!isTypingRef.current) {
      isTypingRef.current = true;
      sendTyping(true);
    }

    // 既存のタイマーをクリア
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // 一定時間後にタイピング終了を通知
    typingTimeoutRef.current = setTimeout(() => {
      isTypingRef.current = false;
      sendTyping(false);
    }, delay);
  }, [sendTyping, delay]);

  const stopTyping = useCallback(() => {
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    if (isTypingRef.current) {
      isTypingRef.current = false;
      sendTyping(false);
    }
  }, [sendTyping]);

  // クリーンアップ
  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  return { handleTyping, stopTyping };
}

/**
 * 複数ユーザーのタイピング状態を管理するフック
 */
export function useTypingUsers(timeout: number = 3000) {
  const [typingUsers, setTypingUsers] = useState<Map<string, { userName: string; timestamp: number }>>(new Map());

  const handleTypingEvent = useCallback((event: TypingUser) => {
    setTypingUsers(prev => {
      const next = new Map(prev);

      if (event.isTyping) {
        next.set(event.userId, {
          userName: event.userName,
          timestamp: Date.now(),
        });
      } else {
        next.delete(event.userId);
      }

      return next;
    });
  }, []);

  // タイムアウトしたユーザーを削除
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      setTypingUsers(prev => {
        const next = new Map(prev);
        let changed = false;

        prev.forEach((value, key) => {
          if (now - value.timestamp > timeout) {
            next.delete(key);
            changed = true;
          }
        });

        return changed ? next : prev;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [timeout]);

  const typingUserNames = Array.from(typingUsers.values()).map(u => u.userName);

  return { typingUsers: typingUserNames, handleTypingEvent };
}
