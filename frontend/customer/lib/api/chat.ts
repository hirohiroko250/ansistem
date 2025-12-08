/**
 * Chat API
 * チャット・通知関連のAPI関数（保護者・顧客向け）
 */

import api from './client';
import type {
  Channel,
  Message,
  SendMessageRequest,
  Notification,
  PaginatedResponse,
  ApiSuccessMessage,
} from './types';

// ============================================
// チャンネル関連
// ============================================

/**
 * チャンネル一覧を取得
 *
 * @returns チャンネル一覧
 */
export async function getChannels(): Promise<Channel[]> {
  const response = await api.get<PaginatedResponse<Channel>>('/communications/channels/');
  // バックエンドは data フィールドを使用、標準DRFは results を使用
  return response?.data || response?.results || [];
}

/**
 * チャンネル詳細を取得
 *
 * @param id - チャンネルID
 * @returns チャンネル詳細
 */
export async function getChannel(id: string): Promise<Channel> {
  return api.get<Channel>(`/communications/channels/${id}/`);
}

// ============================================
// メッセージ関連
// ============================================

export interface GetMessagesParams {
  page?: number;
  pageSize?: number;
  before?: string; // ISO日時（この日時より前のメッセージを取得）
  after?: string;  // ISO日時（この日時より後のメッセージを取得）
}

/**
 * メッセージ一覧を取得
 *
 * @param channelId - チャンネルID
 * @param params - ページネーション・フィルタパラメータ
 * @returns メッセージ一覧（ページネーション付き）
 */
export async function getMessages(
  channelId: string,
  params?: GetMessagesParams
): Promise<PaginatedResponse<Message>> {
  const query = new URLSearchParams();
  query.set('channel_id', channelId);
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));
  if (params?.before) query.set('before', params.before);
  if (params?.after) query.set('after', params.after);

  return api.get<PaginatedResponse<Message>>(`/communications/messages/?${query.toString()}`);
}

/**
 * メッセージを送信
 *
 * @param data - 送信データ（チャンネルID、内容、タイプ）
 * @returns 送信されたメッセージ
 */
export async function sendMessage(data: SendMessageRequest): Promise<Message> {
  // message_typeはバックエンドが大文字を期待（TEXT, IMAGE, FILE, SYSTEM, BOT）
  const messageType = (data.messageType || 'text').toUpperCase();
  return api.post<Message>('/communications/messages/', {
    channel: data.channelId,  // バックエンドは'channel'フィールドを期待
    content: data.content,
    message_type: messageType,
  });
}

/**
 * メッセージを既読にする
 *
 * @param messageId - メッセージID
 * @returns 成功メッセージ
 */
export async function markAsRead(messageId: string): Promise<ApiSuccessMessage> {
  return api.patch<ApiSuccessMessage>(`/communications/messages/${messageId}/read/`);
}

/**
 * メッセージを削除（論理削除）
 *
 * @param messageId - メッセージID
 * @returns 成功メッセージ
 */
export async function deleteMessage(messageId: string): Promise<ApiSuccessMessage> {
  return api.post<ApiSuccessMessage>(`/communications/messages/${messageId}/delete_message/`);
}

/**
 * チャンネル内の全メッセージを既読にする
 *
 * @param channelId - チャンネルID
 * @returns 成功メッセージ
 */
export async function markChannelAsRead(channelId: string): Promise<ApiSuccessMessage> {
  return api.patch<ApiSuccessMessage>(`/communications/channels/${channelId}/read/`);
}

// ============================================
// 通知関連
// ============================================

export interface GetNotificationsParams {
  page?: number;
  pageSize?: number;
  unreadOnly?: boolean;
}

/**
 * 通知一覧を取得
 *
 * @param params - ページネーション・フィルタパラメータ
 * @returns 通知一覧（ページネーション付き）
 */
export async function getNotifications(
  params?: GetNotificationsParams
): Promise<PaginatedResponse<Notification>> {
  const query = new URLSearchParams();
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));
  if (params?.unreadOnly) query.set('unread_only', 'true');

  const queryString = query.toString();
  const endpoint = queryString
    ? `/communications/notifications/?${queryString}`
    : '/communications/notifications/';

  return api.get<PaginatedResponse<Notification>>(endpoint);
}

/**
 * 通知を既読にする
 *
 * @param id - 通知ID
 * @returns 成功メッセージ
 */
export async function markNotificationAsRead(id: string): Promise<ApiSuccessMessage> {
  return api.patch<ApiSuccessMessage>(`/communications/notifications/${id}/read/`);
}

/**
 * 全通知を既読にする
 *
 * @returns 成功メッセージ
 */
export async function markAllNotificationsAsRead(): Promise<ApiSuccessMessage> {
  return api.patch<ApiSuccessMessage>('/communications/notifications/read-all/');
}

/**
 * 未読通知数を取得
 *
 * @returns 未読通知数
 */
export interface UnreadCountResponse {
  count: number;
}

export async function getUnreadNotificationCount(): Promise<UnreadCountResponse> {
  return api.get<UnreadCountResponse>('/communications/notifications/unread-count/');
}

// ============================================
// ボット関連
// ============================================

export interface BotConfig {
  id: string;
  name: string;
  welcomeMessage: string;
  botType: string;
  aiEnabled: boolean;
}

/**
 * アクティブなボット設定を取得
 *
 * @returns ボット設定
 */
export async function getActiveBotConfig(): Promise<BotConfig> {
  return api.get<BotConfig>('/communications/bot/configs/active/');
}

/**
 * ボットとチャット
 *
 * @param message - 送信メッセージ
 * @param channelId - チャンネルID（オプション）
 * @returns ボットの応答
 */
export interface BotChatResponse {
  response: string;
  conversationId?: string;
  matchedFaq?: boolean;
}

export async function chatWithBot(message: string, channelId?: string): Promise<BotChatResponse> {
  return api.post<BotChatResponse>('/communications/bot-chat/chat/', {
    message,
    channel_id: channelId,
  });
}
