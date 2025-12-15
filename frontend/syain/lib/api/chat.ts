/**
 * Chat API
 * チャット・通知関連のAPI関数（社員向け）
 */

import api from './client';

// ============================================
// Types
// ============================================

export interface Channel {
  id: string;
  channelType: string;
  name: string;
  description?: string;
  student?: {
    id: string;
    studentNo: string;
    fullName: string;
  };
  guardian?: {
    id: string;
    guardianNo: string;
    fullName: string;
  };
  school?: {
    id: string;
    schoolCode: string;
    schoolName: string;
  };
  isArchived: boolean;
  unreadCount: number;
  lastMessage?: {
    content: string;
    createdAt: string;
    senderName: string;
  };
  createdAt: string;
  updatedAt: string;
}

export interface Message {
  id: string;
  channel: string;
  channelId: string;
  sender?: string;
  senderId?: string;
  senderName: string;
  senderGuardian?: string;
  messageType: string;
  content: string;
  isRead: boolean;
  isEdited: boolean;
  isBotMessage: boolean;
  replyTo?: string;
  createdAt: string;
  updatedAt: string;
}

export interface PaginatedResponse<T> {
  data?: T[];
  results?: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

// ============================================
// チャンネル関連
// ============================================

/**
 * チャンネル一覧を取得（社員用 - 全チャンネル取得可能）
 */
export async function getChannels(params?: {
  channelType?: string;
  guardianId?: string;
  studentId?: string;
  schoolId?: string;
  isArchived?: boolean;
}): Promise<Channel[]> {
  const query = new URLSearchParams();
  if (params?.channelType) query.set('channel_type', params.channelType);
  if (params?.guardianId) query.set('guardian_id', params.guardianId);
  if (params?.studentId) query.set('student_id', params.studentId);
  if (params?.schoolId) query.set('school_id', params.schoolId);
  if (params?.isArchived !== undefined) query.set('is_archived', String(params.isArchived));

  const queryString = query.toString();
  const endpoint = queryString
    ? `/communications/channels/?${queryString}`
    : '/communications/channels/';

  const response = await api.get<PaginatedResponse<Channel>>(endpoint);
  return response?.data || response?.results || [];
}

/**
 * 保護者とのチャンネル一覧を取得
 */
export async function getGuardianChannels(): Promise<Channel[]> {
  return getChannels({ channelType: 'direct' });
}

/**
 * サポートチャンネル一覧を取得
 */
export async function getSupportChannels(): Promise<Channel[]> {
  return getChannels({ channelType: 'support' });
}

/**
 * チャンネル詳細を取得
 */
export async function getChannel(id: string): Promise<Channel> {
  return api.get<Channel>(`/communications/channels/${id}/`);
}

/**
 * チャンネルを作成
 */
export async function createChannel(data: {
  channelType: string;
  name: string;
  guardianId?: string;
  studentId?: string;
  schoolId?: string;
}): Promise<Channel> {
  return api.post<Channel>('/communications/channels/', {
    channel_type: data.channelType,
    name: data.name,
    guardian: data.guardianId,
    student: data.studentId,
    school: data.schoolId,
  });
}

/**
 * チャンネルをアーカイブ
 */
export async function archiveChannel(id: string): Promise<Channel> {
  return api.post<Channel>(`/communications/channels/${id}/archive/`);
}

// ============================================
// メッセージ関連
// ============================================

/**
 * メッセージ一覧を取得
 */
export async function getMessages(
  channelId: string,
  params?: { page?: number; pageSize?: number }
): Promise<PaginatedResponse<Message>> {
  const query = new URLSearchParams();
  query.set('channel_id', channelId);
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));

  return api.get<PaginatedResponse<Message>>(`/communications/messages/?${query.toString()}`);
}

/**
 * メッセージを送信
 */
export async function sendMessage(data: {
  channelId: string;
  content: string;
  messageType?: string;
  replyTo?: string;
}): Promise<Message> {
  return api.post<Message>('/communications/messages/', {
    channel: data.channelId,
    content: data.content,
    message_type: (data.messageType || 'text').toUpperCase(),
    reply_to: data.replyTo,
  });
}

/**
 * メッセージを削除
 */
export async function deleteMessage(messageId: string): Promise<void> {
  return api.post<void>(`/communications/messages/${messageId}/delete_message/`);
}

/**
 * チャンネルを既読にする
 */
export async function markChannelAsRead(channelId: string): Promise<void> {
  return api.post<void>(`/communications/channels/${channelId}/mark_read/`);
}

// ============================================
// 通知関連
// ============================================

export interface Notification {
  id: string;
  notificationType: string;
  title: string;
  content: string;
  isRead: boolean;
  readAt?: string;
  actionUrl?: string;
  createdAt: string;
}

/**
 * 通知一覧を取得
 */
export async function getNotifications(params?: {
  page?: number;
  pageSize?: number;
  unreadOnly?: boolean;
}): Promise<PaginatedResponse<Notification>> {
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
 */
export async function markNotificationAsRead(id: string): Promise<void> {
  return api.post<void>(`/communications/notifications/${id}/mark_read/`);
}

/**
 * 全通知を既読にする
 */
export async function markAllNotificationsAsRead(): Promise<void> {
  return api.post<void>('/communications/notifications/mark_all_read/');
}

/**
 * 未読通知数を取得
 */
export async function getUnreadNotificationCount(): Promise<{ unread_count: number }> {
  return api.get<{ unread_count: number }>('/communications/notifications/unread_count/');
}

// ============================================
// チャットログ関連（管理者向け）
// ============================================

export interface ChatLog {
  id: string;
  timestamp: string;
  senderType: string;
  content: string;
  guardianName?: string;
  schoolName?: string;
  brandName?: string;
}

/**
 * チャットログ一覧を取得
 */
export async function getChatLogs(params?: {
  guardianId?: string;
  schoolId?: string;
  brandId?: string;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}): Promise<PaginatedResponse<ChatLog>> {
  const query = new URLSearchParams();
  if (params?.guardianId) query.set('guardian_id', params.guardianId);
  if (params?.schoolId) query.set('school_id', params.schoolId);
  if (params?.brandId) query.set('brand_id', params.brandId);
  if (params?.dateFrom) query.set('date_from', params.dateFrom);
  if (params?.dateTo) query.set('date_to', params.dateTo);
  if (params?.search) query.set('search', params.search);
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));

  const queryString = query.toString();
  const endpoint = queryString
    ? `/communications/chat-logs/?${queryString}`
    : '/communications/chat-logs/';

  return api.get<PaginatedResponse<ChatLog>>(endpoint);
}

/**
 * チャットログ統計を取得
 */
export async function getChatLogStatistics(): Promise<{
  total_messages: number;
  by_sender_type: Record<string, number>;
  by_brand: Record<string, number>;
  by_school: Record<string, number>;
}> {
  return api.get('/communications/chat-logs/statistics/');
}
