/**
 * 支払い方法 API
 */
import api from './client';

export interface PaymentInfo {
  id: string;
  guardian_no: string;
  full_name: string;
  bank_name: string;
  bank_code: string;
  branch_name: string;
  branch_code: string;
  account_type: 'ordinary' | 'current' | 'savings';
  account_number: string;
  account_number_masked: string;
  account_holder: string;
  account_holder_kana: string;
  withdrawal_day: number | null;
  payment_registered: boolean;
  payment_registered_at: string | null;
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
