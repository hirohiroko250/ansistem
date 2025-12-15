/**
 * Bank Account Requests API
 * 口座変更申請管理用API
 */

import apiClient from './client';

export interface BankAccountRequest {
  id: string;
  guardian: string;
  guardianName: string;
  guardianNo: string;
  guardianEmail?: string;
  guardianPhone?: string;
  guardianAddress?: string;
  guardianNameKana?: string;
  existingAccount?: string;
  requestType: 'new' | 'update' | 'delete';
  requestTypeDisplay: string;
  bankName: string;
  bankCode: string;
  branchName: string;
  branchCode: string;
  accountType: string;
  accountTypeDisplay: string;
  accountNumber: string;
  accountHolder: string;
  accountHolderKana: string;
  isPrimary: boolean;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  statusDisplay: string;
  requestedAt: string;
  requestedBy?: string;
  requestedByName?: string;
  requestNotes: string;
  processedAt?: string;
  processedBy?: string;
  processedByName?: string;
  processNotes: string;
  createdAt: string;
  updatedAt: string;
}

export interface BankAccountRequestFilters {
  status?: string;
  request_type?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  results: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

/**
 * 口座変更申請一覧を取得
 */
export async function getBankAccountRequests(
  filters?: BankAccountRequestFilters
): Promise<PaginatedResponse<BankAccountRequest>> {
  const params = new URLSearchParams();
  if (filters?.status) params.set('status', filters.status);
  if (filters?.request_type) params.set('request_type', filters.request_type);
  if (filters?.search) params.set('search', filters.search);
  if (filters?.page) params.set('page', String(filters.page));
  if (filters?.page_size) params.set('page_size', String(filters.page_size));

  const query = params.toString();
  const endpoint = query ? `/students/bank-account-requests/?${query}` : '/students/bank-account-requests/';

  const response = await apiClient.get<any>(endpoint);

  // レスポンス形式を統一（data/results両方に対応）
  return {
    results: response.data || response.results || [],
    count: response.meta?.total || response.count || 0,
    next: response.links?.next || response.next || null,
    previous: response.links?.previous || response.previous || null,
  };
}

/**
 * 口座変更申請詳細を取得
 */
export async function getBankAccountRequest(id: string): Promise<BankAccountRequest> {
  return apiClient.get<BankAccountRequest>(`/students/bank-account-requests/${id}/`);
}

/**
 * 口座変更申請を承認
 */
export async function approveBankAccountRequest(id: string): Promise<BankAccountRequest> {
  return apiClient.post<BankAccountRequest>(`/students/bank-account-requests/${id}/approve/`);
}

/**
 * 口座変更申請を却下
 */
export async function rejectBankAccountRequest(id: string, reason?: string): Promise<BankAccountRequest> {
  return apiClient.post<BankAccountRequest>(`/students/bank-account-requests/${id}/reject/`, {
    reason,
  });
}

/**
 * 口座変更申請を更新
 */
export async function updateBankAccountRequest(
  id: string,
  data: Partial<BankAccountRequest>
): Promise<BankAccountRequest> {
  return apiClient.patch<BankAccountRequest>(`/students/bank-account-requests/${id}/`, {
    bank_name: data.bankName,
    bank_code: data.bankCode,
    branch_name: data.branchName,
    branch_code: data.branchCode,
    account_type: data.accountType,
    account_number: data.accountNumber,
    account_holder: data.accountHolder,
    account_holder_kana: data.accountHolderKana,
    request_notes: data.requestNotes,
  });
}

/**
 * 口座振替依頼書データを取得（差し込み印刷用）
 */
export async function getDirectDebitFormData(ids: string[]): Promise<{
  requests: BankAccountRequest[];
  formData: Array<{
    guardianName: string;
    guardianNameKana: string;
    postalCode: string;
    address: string;
    phone: string;
    bankName: string;
    bankCode: string;
    branchName: string;
    branchCode: string;
    accountType: string;
    accountNumber: string;
    accountHolder: string;
    accountHolderKana: string;
    requestDate: string;
  }>;
}> {
  return apiClient.post('/students/bank-account-requests/form_data/', {
    ids,
  });
}
