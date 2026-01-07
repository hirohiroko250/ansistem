/**
 * WebSocket Client for Real-time Chat
 * リアルタイムチャット用WebSocketクライアント
 */

export interface ChatMessage {
  id: string;
  content: string;
  senderId: string;
  senderName: string;
  senderType: 'staff' | 'guardian' | 'system' | 'bot';
  createdAt: string;
  replyTo?: string;
}

export interface TypingUser {
  userId: string;
  userName: string;
  isTyping: boolean;
}

export interface WebSocketMessage {
  type: string;
  [key: string]: unknown;
}

type MessageHandler = (message: ChatMessage) => void;
type TypingHandler = (typing: TypingUser) => void;
type ConnectionHandler = (status: 'connected' | 'disconnected' | 'reconnecting') => void;
type UserJoinLeaveHandler = (event: { userId: string; userName: string }) => void;
type MessageEditedHandler = (event: { messageId: string; content: string; editedAt?: string }) => void;
type MessageDeletedHandler = (event: { messageId: string }) => void;
type ThreadReplyHandler = (event: { parentMessageId: string; reply: ChatMessage; replyCount: number }) => void;
type ReactionAddedHandler = (event: { messageId: string; emoji: string; userId: string; userName: string }) => void;
type ReactionRemovedHandler = (event: { messageId: string; emoji: string; userId: string }) => void;

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private channelId: string;
  private token: string;
  private baseUrl: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: NodeJS.Timeout | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;

  // Event handlers
  private onMessageHandlers: MessageHandler[] = [];
  private onTypingHandlers: TypingHandler[] = [];
  private onConnectionHandlers: ConnectionHandler[] = [];
  private onUserJoinHandlers: UserJoinLeaveHandler[] = [];
  private onUserLeaveHandlers: UserJoinLeaveHandler[] = [];
  private onMessageEditedHandlers: MessageEditedHandler[] = [];
  private onMessageDeletedHandlers: MessageDeletedHandler[] = [];
  private onThreadReplyHandlers: ThreadReplyHandler[] = [];
  private onReactionAddedHandlers: ReactionAddedHandler[] = [];
  private onReactionRemovedHandlers: ReactionRemovedHandler[] = [];

  constructor(channelId: string, token: string) {
    this.channelId = channelId;
    this.token = token;

    // WebSocket URLを構築（環境変数から取得）
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const wsProtocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
    const host = apiUrl.replace(/^https?:\/\//, '').replace(/\/api\/v1\/?$/, '');
    this.baseUrl = `${wsProtocol}://${host}`;
  }

  /**
   * WebSocket接続を開始
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    const url = `${this.baseUrl}/ws/chat/${this.channelId}/?token=${this.token}`;

    try {
      this.ws = new WebSocket(url);
      this.setupEventHandlers();
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.handleReconnect();
    }
  }

  /**
   * WebSocket接続を切断
   */
  disconnect(): void {
    this.clearTimers();

    if (this.ws) {
      this.ws.close(1000, 'User disconnected');
      this.ws = null;
    }

    this.reconnectAttempts = 0;
  }

  /**
   * メッセージを送信
   */
  sendMessage(content: string, replyTo?: string): void {
    this.send({
      type: 'chat_message',
      content,
      reply_to: replyTo,
    });
  }

  /**
   * タイピング状態を送信
   */
  sendTyping(isTyping: boolean): void {
    this.send({
      type: 'typing',
      is_typing: isTyping,
    });
  }

  /**
   * メッセージを既読にする
   */
  markAsRead(messageId: string): void {
    this.send({
      type: 'mark_read',
      message_id: messageId,
    });
  }

  /**
   * メッセージ受信ハンドラを登録
   */
  onMessage(handler: MessageHandler): () => void {
    this.onMessageHandlers.push(handler);
    return () => {
      this.onMessageHandlers = this.onMessageHandlers.filter(h => h !== handler);
    };
  }

  /**
   * タイピングハンドラを登録
   */
  onTyping(handler: TypingHandler): () => void {
    this.onTypingHandlers.push(handler);
    return () => {
      this.onTypingHandlers = this.onTypingHandlers.filter(h => h !== handler);
    };
  }

  /**
   * 接続状態ハンドラを登録
   */
  onConnectionChange(handler: ConnectionHandler): () => void {
    this.onConnectionHandlers.push(handler);
    return () => {
      this.onConnectionHandlers = this.onConnectionHandlers.filter(h => h !== handler);
    };
  }

  /**
   * ユーザー参加ハンドラを登録
   */
  onUserJoin(handler: UserJoinLeaveHandler): () => void {
    this.onUserJoinHandlers.push(handler);
    return () => {
      this.onUserJoinHandlers = this.onUserJoinHandlers.filter(h => h !== handler);
    };
  }

  /**
   * ユーザー離脱ハンドラを登録
   */
  onUserLeave(handler: UserJoinLeaveHandler): () => void {
    this.onUserLeaveHandlers.push(handler);
    return () => {
      this.onUserLeaveHandlers = this.onUserLeaveHandlers.filter(h => h !== handler);
    };
  }

  /**
   * メッセージ編集ハンドラを登録
   */
  onMessageEdited(handler: MessageEditedHandler): () => void {
    this.onMessageEditedHandlers.push(handler);
    return () => {
      this.onMessageEditedHandlers = this.onMessageEditedHandlers.filter(h => h !== handler);
    };
  }

  /**
   * メッセージ削除ハンドラを登録
   */
  onMessageDeleted(handler: MessageDeletedHandler): () => void {
    this.onMessageDeletedHandlers.push(handler);
    return () => {
      this.onMessageDeletedHandlers = this.onMessageDeletedHandlers.filter(h => h !== handler);
    };
  }

  /**
   * スレッド返信ハンドラを登録
   */
  onThreadReply(handler: ThreadReplyHandler): () => void {
    this.onThreadReplyHandlers.push(handler);
    return () => {
      this.onThreadReplyHandlers = this.onThreadReplyHandlers.filter(h => h !== handler);
    };
  }

  /**
   * リアクション追加ハンドラを登録
   */
  onReactionAdded(handler: ReactionAddedHandler): () => void {
    this.onReactionAddedHandlers.push(handler);
    return () => {
      this.onReactionAddedHandlers = this.onReactionAddedHandlers.filter(h => h !== handler);
    };
  }

  /**
   * リアクション削除ハンドラを登録
   */
  onReactionRemoved(handler: ReactionRemovedHandler): () => void {
    this.onReactionRemovedHandlers.push(handler);
    return () => {
      this.onReactionRemovedHandlers = this.onReactionRemovedHandlers.filter(h => h !== handler);
    };
  }

  /**
   * 接続状態を取得
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // Private methods

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.notifyConnectionChange('connected');
      this.startPing();
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      this.clearTimers();
      this.notifyConnectionChange('disconnected');

      // 異常終了の場合は再接続を試みる
      if (event.code !== 1000) {
        this.handleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WebSocketMessage;
        this.handleMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
  }

  private handleMessage(data: WebSocketMessage): void {
    switch (data.type) {
      case 'chat_message':
        // バックエンドはsnake_caseで送信するのでcamelCaseに変換
        const rawMessage = data.message as Record<string, unknown>;
        const message: ChatMessage = {
          id: rawMessage.id as string,
          content: rawMessage.content as string,
          senderId: (rawMessage.sender_id || rawMessage.senderId) as string,
          senderName: (rawMessage.sender_name || rawMessage.senderName) as string,
          senderType: (rawMessage.sender_type || rawMessage.senderType) as 'staff' | 'guardian' | 'system' | 'bot',
          createdAt: (rawMessage.created_at || rawMessage.createdAt) as string,
          replyTo: (rawMessage.reply_to || rawMessage.replyTo) as string | undefined,
        };
        this.onMessageHandlers.forEach(handler => handler(message));
        break;

      case 'typing':
        const typing: TypingUser = {
          userId: data.user_id as string,
          userName: data.user_name as string,
          isTyping: data.is_typing as boolean,
        };
        this.onTypingHandlers.forEach(handler => handler(typing));
        break;

      case 'user_join':
        const joinEvent = {
          userId: data.user_id as string,
          userName: data.user_name as string,
        };
        this.onUserJoinHandlers.forEach(handler => handler(joinEvent));
        break;

      case 'user_leave':
        const leaveEvent = {
          userId: data.user_id as string,
          userName: data.user_name as string,
        };
        this.onUserLeaveHandlers.forEach(handler => handler(leaveEvent));
        break;

      case 'message_edited':
        const editedEvent = {
          messageId: data.message_id as string,
          content: data.content as string,
          editedAt: data.edited_at as string | undefined,
        };
        this.onMessageEditedHandlers.forEach(handler => handler(editedEvent));
        break;

      case 'message_deleted':
        const deletedEvent = {
          messageId: data.message_id as string,
        };
        this.onMessageDeletedHandlers.forEach(handler => handler(deletedEvent));
        break;

      case 'thread_reply':
        const threadReplyEvent = {
          parentMessageId: data.parent_message_id as string,
          reply: data.reply as ChatMessage,
          replyCount: data.reply_count as number,
        };
        this.onThreadReplyHandlers.forEach(handler => handler(threadReplyEvent));
        break;

      case 'reaction_added':
        const reactionAddedEvent = {
          messageId: data.message_id as string,
          emoji: data.emoji as string,
          userId: data.user_id as string,
          userName: data.user_name as string,
        };
        this.onReactionAddedHandlers.forEach(handler => handler(reactionAddedEvent));
        break;

      case 'reaction_removed':
        const reactionRemovedEvent = {
          messageId: data.message_id as string,
          emoji: data.emoji as string,
          userId: data.user_id as string,
        };
        this.onReactionRemovedHandlers.forEach(handler => handler(reactionRemovedEvent));
        break;

      case 'pong':
        // Heartbeat response
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  }

  private send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  private startPing(): void {
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 30000); // 30秒ごとにping
  }

  private clearTimers(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    this.notifyConnectionChange('reconnecting');

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private notifyConnectionChange(status: 'connected' | 'disconnected' | 'reconnecting'): void {
    this.onConnectionHandlers.forEach(handler => handler(status));
  }
}

/**
 * 通知用WebSocketクライアント
 */
export class NotificationWebSocket {
  private ws: WebSocket | null = null;
  private token: string;
  private baseUrl: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private pingInterval: NodeJS.Timeout | null = null;

  private onNewChatMessageHandlers: ((data: {
    channelId: string;
    channelName: string;
    message: ChatMessage;
  }) => void)[] = [];

  private onSystemNotificationHandlers: ((data: {
    title: string;
    message: string;
    level: 'info' | 'warning' | 'error';
  }) => void)[] = [];

  constructor(token: string) {
    this.token = token;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const wsProtocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
    const host = apiUrl.replace(/^https?:\/\//, '').replace(/\/api\/v1\/?$/, '');
    this.baseUrl = `${wsProtocol}://${host}`;
  }

  connect(): void {
    const url = `${this.baseUrl}/ws/notifications/?token=${this.token}`;

    try {
      this.ws = new WebSocket(url);
      this.setupEventHandlers();
    } catch (error) {
      console.error('Notification WebSocket connection error:', error);
    }
  }

  disconnect(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
    }
    if (this.ws) {
      this.ws.close(1000);
      this.ws = null;
    }
  }

  onNewChatMessage(handler: (data: {
    channelId: string;
    channelName: string;
    message: ChatMessage;
  }) => void): () => void {
    this.onNewChatMessageHandlers.push(handler);
    return () => {
      this.onNewChatMessageHandlers = this.onNewChatMessageHandlers.filter(h => h !== handler);
    };
  }

  onSystemNotification(handler: (data: {
    title: string;
    message: string;
    level: 'info' | 'warning' | 'error';
  }) => void): () => void {
    this.onSystemNotificationHandlers.push(handler);
    return () => {
      this.onSystemNotificationHandlers = this.onSystemNotificationHandlers.filter(h => h !== handler);
    };
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('Notification WebSocket connected');
      this.reconnectAttempts = 0;
      this.startPing();
    };

    this.ws.onclose = () => {
      if (this.pingInterval) {
        clearInterval(this.pingInterval);
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'new_chat_message':
            this.onNewChatMessageHandlers.forEach(handler => handler({
              channelId: data.channel_id,
              channelName: data.channel_name,
              message: data.message,
            }));
            break;

          case 'system_notification':
            this.onSystemNotificationHandlers.forEach(handler => handler({
              title: data.title,
              message: data.message,
              level: data.level,
            }));
            break;
        }
      } catch (error) {
        console.error('Failed to parse notification:', error);
      }
    };
  }

  private startPing(): void {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
  }
}
