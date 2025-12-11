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
  const requestBody = {
    studentId: data.studentId,
    productIds: data.productIds,
    courseId: data.courseId,
    packId: data.packId,
    additionalTickets: data.additionalTickets,
    promoCode: data.promoCode,
    startDate: data.startDate,  // 入会時授業料計算用
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
  const requestBody = {
    previewId: data.previewId,
    paymentMethod: data.paymentMethod,
    useMile: data.useMile,
    studentId: data.studentId,
    courseId: data.courseId,
    // 購入時に選択した情報
    brandId: data.brandId,
    schoolId: data.schoolId,
    startDate: data.startDate,
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
