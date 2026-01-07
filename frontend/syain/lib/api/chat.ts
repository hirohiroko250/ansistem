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
  isPinned: boolean;
  isMuted: boolean;
  unreadCount: number;
  lastMessage?: {
    content: string;
    createdAt: string;
    senderName: string;
  };
  createdAt: string;
  updatedAt: string;
}

export interface MessageReaction {
  emoji: string;
  count: number;
  users: Array<{
    user_id: string;
    user_name: string;
  }>;
}

export interface MessageMention {
  user_id: string;
  user_name: string;
  start_index: number;
  end_index: number;
}

export interface MentionableUser {
  id: string;
  name: string;
  email: string;
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
  attachmentUrl?: string;
  attachmentName?: string;
  isRead: boolean;
  readCount?: number;  // 既読人数
  isEdited: boolean;
  editedAt?: string;   // 編集日時
  isBotMessage: boolean;
  replyTo?: string;
  replyToContent?: string;
  replyToSenderName?: string;  // 返信先の送信者名
  replyCount?: number;
  reactions?: MessageReaction[];
  mentions?: MessageMention[];
  createdAt: string;
  updatedAt: string;
}

export interface FileUploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface ThreadResponse {
  parent: Message;
  replies: Message[];
  totalCount: number;
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

/**
 * メンション可能なユーザー一覧を取得
 */
export async function getMentionableUsers(channelId: string): Promise<MentionableUser[]> {
  return api.get<MentionableUser[]>(`/communications/channels/${channelId}/mentionable-users/`);
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
 * メッセージを編集
 */
export async function editMessage(messageId: string, content: string): Promise<Message> {
  return api.post<Message>(`/communications/messages/${messageId}/edit/`, { content });
}

/**
 * ファイルをアップロードしてメッセージを作成
 */
export async function uploadFile(
  data: {
    channelId: string;
    file: File;
    content?: string;
    replyTo?: string;
  },
  onProgress?: (progress: FileUploadProgress) => void
): Promise<Message> {
  const formData = new FormData();
  formData.append('file', data.file);
  formData.append('channel_id', data.channelId);
  if (data.content) formData.append('content', data.content);
  if (data.replyTo) formData.append('reply_to', data.replyTo);

  // XMLHttpRequestでプログレスを監視
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress({
          loaded: event.loaded,
          total: event.total,
          percentage: Math.round((event.loaded / event.total) * 100),
        });
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response);
        } catch {
          reject(new Error('Invalid JSON response'));
        }
      } else {
        try {
          const error = JSON.parse(xhr.responseText);
          reject(new Error(error.error || 'Upload failed'));
        } catch {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Network error'));
    });

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload aborted'));
    });

    // Get token from localStorage
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

    xhr.open('POST', `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/communications/messages/upload/`);
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }
    xhr.send(formData);
  });
}

/**
 * 許可されているファイル拡張子
 */
export const ALLOWED_FILE_EXTENSIONS = {
  images: ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
  documents: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv'],
};

/**
 * 最大ファイルサイズ（10MB）
 */
export const MAX_FILE_SIZE = 10 * 1024 * 1024;

/**
 * ファイルが画像かどうかを判定
 */
export function isImageFile(filename: string): boolean {
  const ext = filename.toLowerCase().slice(filename.lastIndexOf('.'));
  return ALLOWED_FILE_EXTENSIONS.images.includes(ext);
}

/**
 * ファイルが許可されている形式かどうかを判定
 */
export function isAllowedFile(filename: string): boolean {
  const ext = filename.toLowerCase().slice(filename.lastIndexOf('.'));
  return [...ALLOWED_FILE_EXTENSIONS.images, ...ALLOWED_FILE_EXTENSIONS.documents].includes(ext);
}

/**
 * ファイルサイズをフォーマット
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * スレッド（返信）メッセージを取得
 */
export async function getThread(messageId: string): Promise<ThreadResponse> {
  return api.get<ThreadResponse>(`/communications/messages/${messageId}/thread/`);
}

/**
 * スレッドに返信
 */
export async function sendThreadReply(data: {
  channelId: string;
  parentMessageId: string;
  content: string;
}): Promise<Message> {
  return api.post<Message>('/communications/messages/', {
    channel: data.channelId,
    content: data.content,
    message_type: 'TEXT',
    reply_to: data.parentMessageId,
  });
}

/**
 * リアクション（絵文字）を追加
 */
export async function addReaction(messageId: string, emoji: string): Promise<{ id: string; emoji: string; message_id: string }> {
  return api.post(`/communications/messages/${messageId}/reactions/`, { emoji });
}

/**
 * リアクション（絵文字）を削除
 */
export async function removeReaction(messageId: string, emoji: string): Promise<void> {
  const encodedEmoji = encodeURIComponent(emoji);
  return api.delete(`/communications/messages/${messageId}/reactions/${encodedEmoji}/`);
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

// ============================================
// スタッフ間チャット関連
// ============================================

export interface StaffChannel {
  id: string;
  name: string;
  channelType: string;
  description?: string;
  updatedAt: string;
  members?: Array<{
    id: string;
    user?: { id: string; fullName?: string; email: string };
  }>;
  unreadCount?: number;
  isPinned?: boolean;
  isMuted?: boolean;
}

export interface Staff {
  id: string;
  name: string;
  email?: string;
  position?: string;
}

/**
 * 自分が参加している内部チャンネル一覧を取得
 */
export async function getStaffChannels(): Promise<StaffChannel[]> {
  const response = await api.get<PaginatedResponse<StaffChannel>>(
    '/communications/channels/my-channels/?channel_type=INTERNAL'
  );
  return response?.data || response?.results || (response as unknown as StaffChannel[]) || [];
}

/**
 * スタッフ一覧を取得
 */
export async function getStaffList(): Promise<Staff[]> {
  const response = await api.get<PaginatedResponse<any>>('/tenants/employees/');
  const data = response?.data || response?.results || (response as unknown as any[]) || [];
  return data.map((e: any) => ({
    id: e.id,
    name: e.fullName || e.full_name || e.email,
    email: e.email,
    position: e.positionName || e.position_name,
  }));
}

/**
 * スタッフとのDMを作成または取得
 */
export async function createStaffDM(targetUserId: string): Promise<StaffChannel> {
  return api.post<StaffChannel>('/communications/channels/create-dm/', {
    target_user_id: targetUserId,
  });
}

/**
 * スタッフグループチャットを作成
 */
export async function createStaffGroup(name: string, memberIds: string[]): Promise<StaffChannel> {
  return api.post<StaffChannel>('/communications/channels/create-group/', {
    name,
    member_ids: memberIds,
  });
}

/**
 * チャンネルのメッセージを送信
 */
export async function sendStaffMessage(channelId: string, content: string): Promise<Message> {
  return api.post<Message>(`/communications/channels/${channelId}/send_message/`, {
    content,
    message_type: 'TEXT',
  });
}

/**
 * チャンネルのメッセージを取得
 */
export async function getStaffMessages(channelId: string): Promise<Message[]> {
  const response = await api.get<PaginatedResponse<Message>>(
    `/communications/channels/${channelId}/messages/`
  );
  return response?.data || response?.results || (response as unknown as Message[]) || [];
}

// ============================================
// チャンネル管理関連（Phase 7）
// ============================================

export type MemberRole = 'ADMIN' | 'MEMBER' | 'READONLY';

export interface ChannelMember {
  id: string;
  user: {
    id: string;
    fullName?: string;
    full_name?: string;
    email: string;
  };
  role: MemberRole;
  joinedAt: string;
}

export interface ChannelSettings {
  name?: string;
  description?: string;
}

/**
 * チャンネル設定を更新（名前・説明）
 */
export async function updateChannelSettings(
  channelId: string,
  settings: ChannelSettings
): Promise<Channel> {
  return api.put<Channel>(`/communications/channels/${channelId}/settings/`, settings);
}

/**
 * チャンネルメンバー一覧を取得
 */
export async function getChannelMembers(channelId: string): Promise<ChannelMember[]> {
  const response = await api.get<{ members: ChannelMember[] } | ChannelMember[]>(
    `/communications/channels/${channelId}/members/`
  );
  // レスポンス形式に対応
  if (Array.isArray(response)) {
    return response;
  }
  return response?.members || [];
}

/**
 * チャンネルにメンバーを追加
 */
export async function addChannelMember(
  channelId: string,
  userId: string,
  role: MemberRole = 'MEMBER'
): Promise<ChannelMember> {
  return api.post<ChannelMember>(`/communications/channels/${channelId}/members/`, {
    user_id: userId,
    role,
  });
}

/**
 * チャンネルからメンバーを削除
 */
export async function removeChannelMember(
  channelId: string,
  userId: string
): Promise<void> {
  return api.delete(`/communications/channels/${channelId}/members/${userId}/`);
}

/**
 * メンバーのロールを更新
 */
export async function updateMemberRole(
  channelId: string,
  userId: string,
  role: MemberRole
): Promise<ChannelMember> {
  return api.put<ChannelMember>(
    `/communications/channels/${channelId}/members/${userId}/role/`,
    { role }
  );
}

// ============================================
// メッセージ検索関連（Phase 8）
// ============================================

export interface SearchParams {
  query: string;
  channelId?: string;
  senderId?: string;
  dateFrom?: string;  // YYYY-MM-DD
  dateTo?: string;    // YYYY-MM-DD
  page?: number;
  pageSize?: number;
}

export interface SearchResult extends Message {
  highlight?: string;
}

export interface SearchResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: SearchResult[];
}

/**
 * メッセージを検索
 */
export async function searchMessages(params: SearchParams): Promise<SearchResponse> {
  const query = new URLSearchParams();
  query.set('q', params.query);
  if (params.channelId) query.set('channel_id', params.channelId);
  if (params.senderId) query.set('sender_id', params.senderId);
  if (params.dateFrom) query.set('date_from', params.dateFrom);
  if (params.dateTo) query.set('date_to', params.dateTo);
  if (params.page) query.set('page', String(params.page));
  if (params.pageSize) query.set('page_size', String(params.pageSize));

  return api.get<SearchResponse>(`/communications/messages/search/?${query.toString()}`);
}

/**
 * ハイライトマーカーをHTMLタグに変換
 */
export function parseHighlight(text: string): string {
  if (!text) return '';
  return text
    .replace(/\[\[HIGHLIGHT\]\]/g, '<mark class="bg-yellow-200">')
    .replace(/\[\[\/HIGHLIGHT\]\]/g, '</mark>');
}

// ============================================
// タスク連携（メッセージからタスク作成）
// ============================================

export interface CreateTaskFromMessageParams {
  messageId: string;
  channelId: string;
  title: string;
  description?: string;
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  dueDate?: string;
}

/**
 * メッセージからタスクを作成
 */
export async function createTaskFromMessage(params: CreateTaskFromMessageParams): Promise<{
  id: string;
  title: string;
  status: string;
}> {
  return api.post('/tasks/tasks/', {
    task_type: 'chat',
    title: params.title,
    description: params.description || '',
    priority: params.priority || 'normal',
    due_date: params.dueDate || null,
    source_type: 'message',
    source_id: params.messageId,
  });
}

// ============================================
// チャンネル設定（ピン留め・ミュート）
// ============================================

/**
 * チャンネルのピン留めを切り替え
 */
export async function toggleChannelPin(channelId: string): Promise<{ status: string; is_pinned: boolean }> {
  return api.post(`/communications/channels/${channelId}/toggle-pin/`);
}

/**
 * チャンネルのミュートを切り替え
 */
export async function toggleChannelMute(channelId: string): Promise<{ status: string; is_muted: boolean }> {
  return api.post(`/communications/channels/${channelId}/toggle-mute/`);
}

/**
 * チャンネルのアーカイブを解除
 */
export async function unarchiveChannel(channelId: string): Promise<Channel> {
  return api.post(`/communications/channels/${channelId}/unarchive/`);
}
