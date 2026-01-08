/**
 * Students API
 * 生徒（子ども）関連のAPI関数
 */

import api from './client';
import type { Child, ChildDetail, PaginatedResponse, TicketBalance, TicketLog } from './types';

/**
 * 子ども（生徒）一覧を取得
 * ログイン中の保護者に紐づく子ども一覧を返す
 */
export async function getChildren(): Promise<Child[]> {
  const response = await api.get<PaginatedResponse<Child> | Child[] | { data: Child[] }>('/students/');
  // APIがページネーション形式または配列形式で返す可能性に対応
  if (Array.isArray(response)) {
    return response;
  }
  // バックエンドが { data: [...] } 形式で返す場合
  if ('data' in response && Array.isArray(response.data)) {
    return response.data;
  }
  if ('results' in response && Array.isArray(response.results)) {
    return response.results;
  }
  return [];
}

/**
 * 子ども詳細を取得
 * @param id - 子どものID
 */
export async function getChildDetail(id: string): Promise<ChildDetail> {
  const response = await api.get<ChildDetail | { data: ChildDetail }>(`/students/${id}/`);
  // バックエンドが { data: {...} } 形式で返す場合
  if (response && typeof response === 'object' && 'data' in response && response.data && typeof response.data === 'object') {
    return response.data as ChildDetail;
  }
  return response as ChildDetail;
}

/**
 * 子どものチケット残高を取得
 * @param id - 子どものID
 */
export async function getChildTicketBalance(id: string): Promise<TicketBalance> {
  return api.get<TicketBalance>(`/students/${id}/tickets/`);
}

/**
 * 子どものチケット履歴を取得
 * @param id - 子どものID
 * @param params - ページネーションパラメータ
 */
export interface TicketHistoryParams {
  page?: number;
  pageSize?: number;
}

export async function getChildTicketHistory(
  id: string,
  params?: TicketHistoryParams
): Promise<PaginatedResponse<TicketLog>> {
  const query = new URLSearchParams();
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));

  const queryString = query.toString();
  const endpoint = queryString
    ? `/students/${id}/tickets/history/?${queryString}`
    : `/students/${id}/tickets/history/`;

  return api.get<PaginatedResponse<TicketLog>>(endpoint);
}

// ============================================
// 講師向け生徒管理API
// ============================================

/**
 * 講師向け生徒型（syain互換）
 */
export interface StaffStudent {
  id: string;
  user?: {
    id: string;
    full_name: string;
    first_name?: string;
    last_name?: string;
    email?: string;
    phone_number?: string;
  };
  student_number?: string;
  grade?: string;
  school_name?: string;
  enrollment_date?: string;
  status: string;
  notes?: string;
  created_at?: string;
}

/**
 * 講師向け生徒検索パラメータ
 */
export interface StudentSearchParams {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  grade?: string;
  schoolId?: string;
  ordering?: string;
}

/**
 * 講師向け生徒一覧取得
 */
export async function getStudents(
  params?: StudentSearchParams
): Promise<PaginatedResponse<StaffStudent>> {
  const queryParams = new URLSearchParams();

  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.pageSize) queryParams.append('page_size', params.pageSize.toString());
  if (params?.search) queryParams.append('search', params.search);
  if (params?.status) queryParams.append('status', params.status);
  if (params?.grade) queryParams.append('grade', params.grade);
  if (params?.schoolId) queryParams.append('school_id', params.schoolId);
  if (params?.ordering) queryParams.append('ordering', params.ordering);

  const query = queryParams.toString();
  const endpoint = `/students/${query ? `?${query}` : ''}`;

  return api.get<PaginatedResponse<StaffStudent>>(endpoint);
}

/**
 * 講師向け生徒詳細取得
 */
export async function getStudentDetail(id: string): Promise<StaffStudent> {
  return api.get<StaffStudent>(`/students/${id}/`);
}

/**
 * 生徒のチケット残高取得（講師向け）
 */
export async function getStudentTicketBalance(studentId: string): Promise<TicketBalance> {
  return api.get<TicketBalance>(`/students/${studentId}/tickets/`);
}

/**
 * 生徒の保護者一覧取得
 */
export interface Guardian {
  id: string;
  fullName: string;
  email?: string;
  phoneNumber?: string;
  relationship?: string;
}

export async function getStudentGuardians(studentId: string): Promise<Guardian[]> {
  return api.get<Guardian[]>(`/students/${studentId}/guardians/`);
}

// ============================================
// 生徒登録API（保護者向け）
// ============================================

/**
 * 生徒作成リクエスト型
 */
export interface CreateStudentRequest {
  last_name: string;
  first_name: string;
  last_name_kana?: string;
  first_name_kana?: string;
  birth_date?: string;
  gender?: 'male' | 'female' | 'other';
  school_name?: string;
  grade?: string;
  notes?: string;
}

/**
 * 生徒作成レスポンス型
 */
export interface CreateStudentResponse {
  id: string;
  student_no: string;
  last_name: string;
  first_name: string;
  last_name_kana?: string;
  first_name_kana?: string;
  full_name: string;
  birth_date?: string;
  gender?: string;
  school_name?: string;
  grade?: string;
  grade_name?: string;
  status: string;
  enrollment_date?: string;
  guardian?: string;
  guardian_id?: string;
  guardian_name?: string;
  created_at: string;
  updated_at: string;
}

/**
 * 新しい生徒（子ども）を作成
 * @param data - 生徒情報
 */
export async function createStudent(data: CreateStudentRequest): Promise<CreateStudentResponse> {
  return api.post<CreateStudentResponse>('/students/', data);
}

/**
 * 生徒情報を更新
 * @param id - 生徒ID
 * @param data - 更新する生徒情報
 */
export async function updateStudent(id: string, data: Partial<CreateStudentRequest>): Promise<CreateStudentResponse> {
  return api.patch<CreateStudentResponse>(`/students/${id}/`, data);
}

/**
 * 生徒を削除（論理削除）
 * @param id - 生徒ID
 */
export async function deleteStudent(id: string): Promise<void> {
  return api.delete<void>(`/students/${id}/`);
}

// ============================================
// 購入アイテム関連API（保護者向け）
// ============================================

/**
 * 購入アイテム型
 */
export interface PurchasedItem {
  id: string;
  studentId?: string;
  studentName?: string;
  productId?: string;
  productName: string;
  productType: string;  // tuition, textbook, etc.
  courseName?: string;
  brandName?: string;
  brandCode?: string;
  brandId?: string;
  schoolName?: string;
  schoolId?: string;
  billingMonth: string;
  quantity: number;
  unitPrice: number;
  discountAmount: number;
  finalPrice: number;
  notes?: string;
  createdAt?: string;
}

/**
 * 生徒の購入アイテム一覧を取得
 * @param studentId - 生徒ID
 * @param billingMonth - 請求月（例: 2025-01）
 */
export async function getStudentItems(
  studentId: string,
  billingMonth?: string
): Promise<PurchasedItem[]> {
  const params = billingMonth ? `?billing_month=${billingMonth}` : '';
  return api.get<PurchasedItem[]>(`/students/${studentId}/items/${params}`);
}

// マイル情報の型
export type MileInfo = {
  balance: number;
  potentialDiscount: number;
};

// FS割引の型
export type FSDiscount = {
  id: string;
  discountType: string;
  discountValue: number;
  validFrom: string | null;
  validUntil: string | null;
};

// 購入アイテム一覧レスポンスの型
export type AllStudentItemsResponse = {
  items: PurchasedItem[];
  mileInfo: MileInfo;
  fsDiscounts: FSDiscount[];
};

/**
 * 保護者の全子どもの購入アイテム一覧を取得
 * @param billingMonth - 請求月（例: 2025-01）
 */
export async function getAllStudentItems(
  billingMonth?: string
): Promise<AllStudentItemsResponse> {
  const params = billingMonth ? `?billing_month=${billingMonth}` : '';
  const response = await api.get<AllStudentItemsResponse | PurchasedItem[]>(`/students/all_items/${params}`);

  // 後方互換性: 古いAPIレスポンス形式の場合
  if (Array.isArray(response)) {
    return {
      items: response,
      mileInfo: { balance: 0, potentialDiscount: 0 },
      fsDiscounts: [],
    };
  }
  return response;
}

// ============================================
// 休会・退会申請API（保護者向け）
// ============================================

import type {
  SuspensionRequest,
  SuspensionRequestCreate,
  WithdrawalRequest,
  WithdrawalRequestCreate,
} from './types';

/**
 * 休会申請一覧を取得
 */
export async function getSuspensionRequests(): Promise<SuspensionRequest[]> {
  const response = await api.get<PaginatedResponse<SuspensionRequest> | SuspensionRequest[]>(
    '/students/suspension-requests/'
  );
  if (Array.isArray(response)) {
    return response;
  }
  if ('results' in response && Array.isArray(response.results)) {
    return response.results;
  }
  if ('data' in response && Array.isArray(response.data)) {
    return response.data;
  }
  return [];
}

/**
 * 休会申請詳細を取得
 * @param id - 申請ID
 */
export async function getSuspensionRequest(id: string): Promise<SuspensionRequest> {
  return api.get<SuspensionRequest>(`/students/suspension-requests/${id}/`);
}

/**
 * 休会申請を作成
 * @param data - 申請データ
 */
export async function createSuspensionRequest(
  data: SuspensionRequestCreate
): Promise<SuspensionRequest> {
  // snake_caseに変換
  const payload = {
    student: data.student,
    brand: data.brand,
    school: data.school,
    suspend_from: data.suspendFrom,
    suspend_until: data.suspendUntil,
    keep_seat: data.keepSeat ?? false,
    reason: data.reason,
    reason_detail: data.reasonDetail,
  };
  return api.post<SuspensionRequest>('/students/suspension-requests/', payload);
}

/**
 * 休会申請をキャンセル
 * @param id - 申請ID
 */
export async function cancelSuspensionRequest(id: string): Promise<SuspensionRequest> {
  return api.post<SuspensionRequest>(`/students/suspension-requests/${id}/cancel/`, {});
}

/**
 * 退会申請一覧を取得
 */
export async function getWithdrawalRequests(): Promise<WithdrawalRequest[]> {
  const response = await api.get<PaginatedResponse<WithdrawalRequest> | WithdrawalRequest[]>(
    '/students/withdrawal-requests/'
  );
  if (Array.isArray(response)) {
    return response;
  }
  if ('results' in response && Array.isArray(response.results)) {
    return response.results;
  }
  if ('data' in response && Array.isArray(response.data)) {
    return response.data;
  }
  return [];
}

/**
 * 退会申請詳細を取得
 * @param id - 申請ID
 */
export async function getWithdrawalRequest(id: string): Promise<WithdrawalRequest> {
  return api.get<WithdrawalRequest>(`/students/withdrawal-requests/${id}/`);
}

/**
 * 退会申請を作成
 * @param data - 申請データ
 */
export async function createWithdrawalRequest(
  data: WithdrawalRequestCreate
): Promise<WithdrawalRequest> {
  // snake_caseに変換
  const payload = {
    student: data.student,
    brand: data.brand,
    school: data.school,
    withdrawal_date: data.withdrawalDate,
    last_lesson_date: data.lastLessonDate,
    reason: data.reason,
    reason_detail: data.reasonDetail,
  };
  return api.post<WithdrawalRequest>('/students/withdrawal-requests/', payload);
}

/**
 * 退会申請をキャンセル
 * @param id - 申請ID
 */
export async function cancelWithdrawalRequest(id: string): Promise<WithdrawalRequest> {
  return api.post<WithdrawalRequest>(`/students/withdrawal-requests/${id}/cancel/`, {});
}

// 理由選択肢の定数
export const SUSPENSION_REASONS = [
  { value: 'travel', label: '旅行・帰省' },
  { value: 'illness', label: '病気・怪我' },
  { value: 'exam', label: '受験準備' },
  { value: 'schedule', label: 'スケジュール都合' },
  { value: 'financial', label: '経済的理由' },
  { value: 'other', label: 'その他' },
] as const;

export const WITHDRAWAL_REASONS = [
  { value: 'moving', label: '転居' },
  { value: 'school_change', label: '学校変更' },
  { value: 'graduation', label: '卒業' },
  { value: 'schedule', label: 'スケジュール都合' },
  { value: 'financial', label: '経済的理由' },
  { value: 'satisfaction', label: '満足度' },
  { value: 'other_school', label: '他塾への変更' },
  { value: 'other', label: 'その他' },
] as const;

export const REQUEST_STATUS_LABELS = {
  pending: '申請中',
  approved: '承認済',
  rejected: '却下',
  cancelled: '取消',
  resumed: '復会済',
} as const;

// ============================================
// 領収書ダウンロードAPI
// ============================================

/**
 * 領収書PDFをダウンロード
 * @param year - 請求年
 * @param month - 請求月
 * @returns PDFのBlob
 */
export async function downloadReceipt(year: number, month: number): Promise<Blob> {
  return api.getBlob(`/billing/confirmed/my-receipt/?year=${year}&month=${month}`);
}

/**
 * 領収書PDFをダウンロードしてブラウザで保存ダイアログを表示
 * @param year - 請求年
 * @param month - 請求月
 */
export async function downloadAndSaveReceipt(year: number, month: number): Promise<void> {
  const blob = await downloadReceipt(year, month);

  // ダウンロードリンクを作成
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `領収書_${year}年${month}月.pdf`;

  // クリックしてダウンロード
  document.body.appendChild(link);
  link.click();

  // クリーンアップ
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}
