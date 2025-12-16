/**
 * Chat API
 * チャット・通知関連のAPI関数（管理者向け）
 */

import apiClient from './client';

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
  memberCount?: number;
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
  senderGuardianName?: string;
  messageType: string;
  content: string;
  isRead: boolean;
  isEdited: boolean;
  isBotMessage: boolean;
  replyTo?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChatLog {
  id: string;
  timestamp: string;
  senderType: string;
  content: string;
  guardianId?: string;
  guardianName?: string;
  schoolId?: string;
  schoolName?: string;
  brandId?: string;
  brandName?: string;
}

export interface PaginatedResponse<T> {
  data?: T[];
  results?: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

// ============================================
// チャンネル関連（管理者向け - 全チャンネル閲覧可能）
// ============================================

/**
 * チャンネル一覧を取得
 */
export async function getChannels(params?: {
  channelType?: string;
  guardianId?: string;
  studentId?: string;
  schoolId?: string;
  isArchived?: boolean;
  includeArchived?: boolean;
  search?: string;
}): Promise<Channel[]> {
  const query = new URLSearchParams();
  if (params?.channelType) query.set('channel_type', params.channelType);
  if (params?.guardianId) query.set('guardian_id', params.guardianId);
  if (params?.studentId) query.set('student_id', params.studentId);
  if (params?.schoolId) query.set('school_id', params.schoolId);
  if (params?.isArchived !== undefined) query.set('is_archived', String(params.isArchived));
  if (params?.includeArchived) query.set('include_archived', 'true');
  if (params?.search) query.set('search', params.search);

  const queryString = query.toString();
  const endpoint = queryString
    ? `/communications/channels/?${queryString}`
    : '/communications/channels/';

  const response = await apiClient.get<PaginatedResponse<Channel>>(endpoint);
  return response?.data || response?.results || [];
}

/**
 * チャンネル詳細を取得
 */
export async function getChannel(id: string): Promise<Channel> {
  return apiClient.get<Channel>(`/communications/channels/${id}/`);
}

/**
 * 保護者用チャンネルを取得または作成
 */
export async function getOrCreateChannelForGuardian(guardianId: string): Promise<Channel> {
  return apiClient.post<Channel>('/communications/channels/get-or-create-for-guardian/', {
    guardian_id: guardianId
  });
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

  return apiClient.get<PaginatedResponse<Message>>(`/communications/messages/?${query.toString()}`);
}

/**
 * 保護者のメッセージ履歴を取得
 */
export async function getGuardianMessages(
  guardianId: string,
  params?: { page?: number; pageSize?: number }
): Promise<PaginatedResponse<Message>> {
  const query = new URLSearchParams();
  query.set('guardian_id', guardianId);
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));

  return apiClient.get<PaginatedResponse<Message>>(`/communications/messages/?${query.toString()}`);
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
  return apiClient.post<Message>('/communications/messages/', {
    channel: data.channelId,
    content: data.content,
    message_type: (data.messageType || 'text').toUpperCase(),
    reply_to: data.replyTo,
  });
}

// ============================================
// チャットログ関連（管理者向け）
// ============================================

/**
 * チャットログ一覧を取得
 */
export async function getChatLogs(params?: {
  guardianId?: string;
  schoolId?: string;
  brandId?: string;
  senderType?: string;
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
  if (params?.senderType) query.set('sender_type', params.senderType);
  if (params?.dateFrom) query.set('date_from', params.dateFrom);
  if (params?.dateTo) query.set('date_to', params.dateTo);
  if (params?.search) query.set('search', params.search);
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));

  const queryString = query.toString();
  const endpoint = queryString
    ? `/communications/chat-logs/?${queryString}`
    : '/communications/chat-logs/';

  return apiClient.get<PaginatedResponse<ChatLog>>(endpoint);
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
  return apiClient.get('/communications/chat-logs/statistics/');
}

// ============================================
// 対応履歴関連
// ============================================

export interface ContactLog {
  id: string;
  contactType: string;
  subject: string;
  content: string;
  student?: { id: string; fullName: string };
  guardian?: { id: string; fullName: string };
  school?: { id: string; schoolName: string };
  handledBy?: { id: string; email: string; fullName: string };
  status: string;
  priority: string;
  followUpDate?: string;
  resolvedAt?: string;
  createdAt: string;
}

/**
 * 対応履歴一覧を取得
 */
export async function getContactLogs(params?: {
  status?: string;
  contactType?: string;
  priority?: string;
  studentId?: string;
  guardianId?: string;
  handledBy?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}): Promise<PaginatedResponse<ContactLog>> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.contactType) query.set('contact_type', params.contactType);
  if (params?.priority) query.set('priority', params.priority);
  if (params?.studentId) query.set('student_id', params.studentId);
  if (params?.guardianId) query.set('guardian_id', params.guardianId);
  if (params?.handledBy) query.set('handled_by', params.handledBy);
  if (params?.search) query.set('search', params.search);
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));

  const queryString = query.toString();
  const endpoint = queryString
    ? `/communications/contact-logs/?${queryString}`
    : '/communications/contact-logs/';

  return apiClient.get<PaginatedResponse<ContactLog>>(endpoint);
}

/**
 * 対応履歴を作成
 */
export async function createContactLog(data: {
  contactType: string;
  subject: string;
  content: string;
  studentId?: string;
  guardianId?: string;
  schoolId?: string;
  priority?: string;
  followUpDate?: string;
}): Promise<ContactLog> {
  return apiClient.post<ContactLog>('/communications/contact-logs/', {
    contact_type: data.contactType,
    subject: data.subject,
    content: data.content,
    student: data.studentId,
    guardian: data.guardianId,
    school: data.schoolId,
    priority: data.priority || 'normal',
    follow_up_date: data.followUpDate,
  });
}

/**
 * 対応履歴を解決済みにする
 */
export async function resolveContactLog(id: string): Promise<ContactLog> {
  return apiClient.post<ContactLog>(`/communications/contact-logs/${id}/resolve/`);
}
