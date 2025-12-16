/**
 * 支払い方法 API
 */
import api from './client';

export interface PaymentInfo {
  id: string;
  guardianNo: string;
  fullName: string;
  bankName: string;
  bankCode: string;
  branchName: string;
  branchCode: string;
  accountType: 'ordinary' | 'current' | 'savings';
  accountNumber: string;
  accountNumberMasked: string;
  accountHolder: string;
  accountHolderKana: string;
  withdrawalDay: number | null;
  paymentRegistered: boolean;
  paymentRegisteredAt: string | null;
}

export interface PaymentUpdateData {
  bank_name?: string;
  bank_code?: string;
  branch_name?: string;
  branch_code?: string;
  account_type?: 'ordinary' | 'current' | 'savings';
  account_number?: string;
  account_holder?: string;
  account_holder_kana?: string;
  withdrawal_day?: number;
}

/**
 * 支払い情報を取得
 */
export async function getMyPayment(): Promise<PaymentInfo | null> {
  try {
    return await api.get<PaymentInfo>('/students/guardians/my_payment/');
  } catch (error) {
    console.error('Failed to fetch payment info:', error);
    return null;
  }
}

/**
 * 支払い情報を更新
 */
export async function updateMyPayment(data: PaymentUpdateData): Promise<PaymentInfo | null> {
  try {
    return await api.patch<PaymentInfo>('/students/guardians/my_payment_update/', data);
  } catch (error) {
    console.error('Failed to update payment info:', error);
    throw error;
  }
}

/**
 * 口座種別の表示名を取得
 */
export function getAccountTypeLabel(type: string): string {
  switch (type) {
    case 'ordinary':
      return '普通';
    case 'current':
      return '当座';
    case 'savings':
      return '貯蓄';
    default:
      return type;
  }
}

/**
 * 次回引き落とし日を計算
 */
export function getNextWithdrawalDate(withdrawalDay: number | null): string {
  if (!withdrawalDay) return '-';

  const now = new Date();
  let nextDate = new Date(now.getFullYear(), now.getMonth(), withdrawalDay);

  // 今月の引き落とし日を過ぎていたら来月
  if (nextDate <= now) {
    nextDate = new Date(now.getFullYear(), now.getMonth() + 1, withdrawalDay);
  }

  return `${nextDate.getFullYear()}年${nextDate.getMonth() + 1}月${nextDate.getDate()}日`;
}

// =====================================
// 銀行口座変更申請API
// =====================================

export interface BankAccount {
  id: string;
  guardian_name: string;
  bank_name: string;
  bank_code: string;
  branch_name: string;
  branch_code: string;
  account_type: 'ordinary' | 'current' | 'savings';
  account_type_display: string;
  account_number: string;
  account_holder: string;
  account_holder_kana: string;
  is_primary: boolean;
  is_active: boolean;
  notes: string;
  created_at: string;
}

export interface BankAccountRequest {
  id: string;
  guardian_name: string;
  guardian_no: string;
  request_type: 'new' | 'update' | 'delete';
  request_type_display: string;
  bank_name: string;
  bank_code: string;
  branch_name: string;
  branch_code: string;
  account_type: string;
  account_type_display: string;
  account_number: string;
  account_holder: string;
  account_holder_kana: string;
  is_primary: boolean;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  status_display: string;
  requested_at: string;
  processed_at: string | null;
  request_notes: string;
  process_notes: string;
}

export interface BankAccountRequestData {
  request_type: 'new' | 'update' | 'delete';
  existing_account?: string;
  bank_name: string;
  bank_code?: string;
  branch_name: string;
  branch_code?: string;
  account_type: 'ordinary' | 'current' | 'savings';
  account_number: string;
  account_holder: string;
  account_holder_kana: string;
  is_primary?: boolean;
  request_notes?: string;
}

/**
 * 銀行口座一覧を取得
 */
export async function getMyBankAccounts(): Promise<BankAccount[]> {
  try {
    return await api.get<BankAccount[]>('/students/bank-accounts/my_accounts/');
  } catch (error) {
    console.error('Failed to fetch bank accounts:', error);
    return [];
  }
}

/**
 * 銀行口座変更申請一覧を取得
 */
export async function getMyBankAccountRequests(): Promise<BankAccountRequest[]> {
  try {
    return await api.get<BankAccountRequest[]>('/students/bank-account-requests/my_requests/');
  } catch (error) {
    console.error('Failed to fetch bank account requests:', error);
    return [];
  }
}

/**
 * 銀行口座変更申請を作成
 */
export async function createBankAccountRequest(data: BankAccountRequestData): Promise<BankAccountRequest> {
  return await api.post<BankAccountRequest>('/students/bank-account-requests/', data);
}

/**
 * 銀行口座変更申請をキャンセル
 */
export async function cancelBankAccountRequest(id: string): Promise<BankAccountRequest> {
  return await api.post<BankAccountRequest>(`/students/bank-account-requests/${id}/cancel/`, {});
}
