/**
 * Pricing API
 * 料金計算関連のAPI関数（保護者・顧客向け）
 */

import api from './client';
import type {
  PricingPreviewRequest,
  PricingPreviewResponse,
  PricingCalculateRequest,
  PricingCalculateResponse,
  PricingConfirmRequest,
  PricingConfirmResponse,
} from './types';

/**
 * 料金プレビュー（認証必要）
 * コース、パック、追加チケットなどの料金を計算し、詳細な内訳を返す
 *
 * @param data - プレビューリクエスト
 * @returns 料金計算結果（内訳、割引、マイル、合計など）
 */
export async function previewPricing(data: PricingPreviewRequest): Promise<PricingPreviewResponse> {
  // バックエンドはsnake_caseを期待するので、全てsnake_caseで送信
  const requestBody = {
    student_id: data.studentId,
    product_ids: data.productIds,
    course_id: data.courseId,
    pack_id: data.packId,
    additional_tickets: data.additionalTickets,
    promo_code: data.promoCode,
    start_date: data.startDate,  // 入会時授業料計算用
    day_of_week: data.dayOfWeek,  // 当月分回数割計算用（単一曜日）
    days_of_week: data.daysOfWeek,  // 複数曜日対応
  };
  console.log('[previewPricing] Sending request with body:', requestBody);
  return api.post<PricingPreviewResponse>('/pricing/preview/', requestBody);
}

/**
 * シンプル料金計算（認証不要）
 * コースの基本料金とオプションの計算を行う
 * 未ログインユーザーでも利用可能
 *
 * @param data - 計算リクエスト
 * @returns 基本料金計算結果
 */
export async function calculatePricing(data: PricingCalculateRequest): Promise<PricingCalculateResponse> {
  return api.post<PricingCalculateResponse>('/pricing/calculate/', {
    course_id: data.courseId,
    additional_tickets: data.additionalTickets,
    promo_code: data.promoCode,
  }, {
    skipAuth: true,
  });
}

/**
 * 料金確定・購入
 * プレビューIDを指定して購入を確定する
 *
 * @param data - 確定リクエスト（プレビューID、支払い方法、マイル使用量）
 * @returns 注文情報
 */
export async function confirmPricing(data: PricingConfirmRequest): Promise<PricingConfirmResponse> {
  // バックエンドはsnake_caseを期待するので、全てsnake_caseで送信
  const requestBody = {
    preview_id: data.previewId,
    payment_method: data.paymentMethod,
    use_mile: data.useMile,
    miles_to_use: data.milesToUse,  // マイル使用数
    student_id: data.studentId,
    course_id: data.courseId,
    // 購入時に選択した情報
    brand_id: data.brandId,
    school_id: data.schoolId,
    start_date: data.startDate,
    // スケジュール情報（曜日・時間帯）
    schedules: data.schedules,
    ticket_id: data.ticketId,
    // 教材費選択
    selected_textbook_ids: data.selectedTextbookIds,
  };
  console.log('[confirmPricing] Sending request with body:', requestBody);
  return api.post<PricingConfirmResponse>('/pricing/confirm/', requestBody);
}

/**
 * プロモーションコード検証
 *
 * @param code - プロモーションコード
 * @returns 有効性と割引情報
 */
export interface PromoCodeValidationResponse {
  valid: boolean;
  discountType?: 'percentage' | 'fixed';
  discountValue?: number;
  description?: string;
  expiresAt?: string;
  message?: string;
}

export async function validatePromoCode(code: string): Promise<PromoCodeValidationResponse> {
  return api.post<PromoCodeValidationResponse>('/pricing/promo/validate/', {
    code,
  }, {
    skipAuth: true,
  });
}

/**
 * 利用可能なマイル残高を取得
 *
 * @returns マイル残高情報
 */
export interface MileBalanceResponse {
  balance: number;
  expiringAmount: number;
  expiringDate?: string;
}

export async function getMileBalance(): Promise<MileBalanceResponse> {
  return api.get<MileBalanceResponse>('/pricing/mile/balance/');
}

/**
 * マイル履歴を取得
 *
 * @param params - ページネーションパラメータ
 * @returns マイル履歴リスト
 */
export interface MileHistory {
  id: string;
  operation: 'grant' | 'use' | 'expire';
  amount: number;
  reason?: string;
  createdAt: string;
}

export interface MileHistoryParams {
  page?: number;
  pageSize?: number;
}

export interface MileHistoryResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: MileHistory[];
}

export async function getMileHistory(params?: MileHistoryParams): Promise<MileHistoryResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));

  const queryString = query.toString();
  const endpoint = queryString ? `/pricing/mile/history/?${queryString}` : '/pricing/mile/history/';

  return api.get<MileHistoryResponse>(endpoint);
}

// =============================================================================
// 締日情報（請求月判定）
// =============================================================================

/**
 * 締日情報（請求月判定）レスポンス
 */
export interface BillingMonthInfo {
  purchase_date: string;
  billing_year: number;
  billing_month: number;
  closing_day: number | null;
  closing_date: string | null;
  is_after_closing: boolean;
  message: string;
}

/**
 * 入会時の請求情報レスポンス
 */
export interface EnrollmentBillingInfo {
  enrollment_date: string;
  closing_day: number;
  is_after_closing: boolean;
  current_month: {
    year: number;
    month: number;
    editable: boolean;
    note: string;
  } | null;
  next_month: {
    year: number;
    month: number;
    editable: boolean;
    note: string;
  } | null;
  following_month: {
    year: number;
    month: number;
    editable: boolean;
    note: string;
  } | null;
  first_billable_month: {
    year: number;
    month: number;
  } | null;
  message: string;
}

/**
 * チケット購入時の請求月を取得
 * 締日を考慮して、どの月の請求になるかを返す
 *
 * @param purchaseDate - 購入日（YYYY-MM-DD形式、省略時は今日）
 * @returns 請求月情報
 */
export async function getTicketBillingMonth(purchaseDate?: string): Promise<BillingMonthInfo> {
  const params = purchaseDate ? `?purchase_date=${purchaseDate}` : '';
  return api.get<BillingMonthInfo>(`/billing/periods/ticket_billing_info/${params}`);
}

/**
 * 入会時の請求情報を取得
 * 締日を考慮して、どの月から請求できるかを返す
 *
 * @param enrollmentDate - 入会日（YYYY-MM-DD形式、省略時は今日）
 * @returns 請求情報
 */
export async function getEnrollmentBillingInfo(enrollmentDate?: string): Promise<EnrollmentBillingInfo> {
  const params = enrollmentDate ? `?enrollment_date=${enrollmentDate}` : '';
  return api.get<EnrollmentBillingInfo>(`/billing/periods/enrollment_billing_info/${params}`);
}
