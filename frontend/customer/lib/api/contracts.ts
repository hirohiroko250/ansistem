/**
 * Contracts API
 * 契約管理関連のAPI関数（講師・スタッフ向け）
 */

import api from './client';
import type { PaginatedResponse } from './types';

// 契約ステータス型
export type ContractStatus = 'draft' | 'pending' | 'active' | 'suspended' | 'cancelled' | 'expired';

// 契約型
export interface Contract {
  id: string;
  contractNumber?: string;
  studentId: string;
  student?: {
    id: string;
    user: {
      id: string;
      fullName: string;
      email?: string;
    };
    grade?: string;
  };
  courseId: string;
  course?: {
    id: string;
    name: string;
    monthlyFee?: string;
    ticketCost: number;
  };
  startDate: string;
  endDate?: string;
  status: ContractStatus;
  monthlyFee?: string;
  discountRate?: number;
  discountAmount?: string;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

// 契約詳細型
export interface ContractDetail extends Contract {
  payments?: ContractPayment[];
  ticketHistory?: TicketTransaction[];
}

// 支払い型
export interface ContractPayment {
  id: string;
  contractId: string;
  amount: string;
  paymentDate: string;
  paymentMethod: 'bank_transfer' | 'credit_card' | 'cash' | 'other';
  status: 'pending' | 'completed' | 'failed' | 'refunded';
  notes?: string;
}

// チケット取引型
export interface TicketTransaction {
  id: string;
  studentId: string;
  transactionType: 'purchase' | 'use' | 'refund' | 'expire' | 'transfer';
  amount: number;
  balance: number;
  description?: string;
  createdAt: string;
}

// 検索パラメータ型
export interface ContractSearchParams {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  studentId?: string;
  courseId?: string;
  startDateFrom?: string;
  startDateTo?: string;
  ordering?: string;
}

/**
 * 契約一覧取得
 */
export async function getContracts(
  params?: ContractSearchParams
): Promise<PaginatedResponse<Contract>> {
  const queryParams = new URLSearchParams();

  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.pageSize) queryParams.append('page_size', params.pageSize.toString());
  if (params?.search) queryParams.append('search', params.search);
  if (params?.status) queryParams.append('status', params.status);
  if (params?.studentId) queryParams.append('student_id', params.studentId);
  if (params?.courseId) queryParams.append('course_id', params.courseId);
  if (params?.startDateFrom) queryParams.append('start_date_from', params.startDateFrom);
  if (params?.startDateTo) queryParams.append('start_date_to', params.startDateTo);
  if (params?.ordering) queryParams.append('ordering', params.ordering);

  const query = queryParams.toString();
  const endpoint = `/contracts/${query ? `?${query}` : ''}`;

  return api.get<PaginatedResponse<Contract>>(endpoint);
}

/**
 * 契約詳細取得
 */
export async function getContract(id: string): Promise<ContractDetail> {
  return api.get<ContractDetail>(`/contracts/${id}/`);
}

/**
 * 契約作成
 */
export interface CreateContractRequest {
  studentId: string;
  courseId: string;
  startDate: string;
  endDate?: string;
  monthlyFee?: string;
  discountRate?: number;
  discountAmount?: string;
  notes?: string;
}

export async function createContract(data: CreateContractRequest): Promise<Contract> {
  return api.post<Contract>('/contracts/', data);
}

/**
 * 契約更新
 */
export interface UpdateContractRequest {
  endDate?: string;
  monthlyFee?: string;
  discountRate?: number;
  discountAmount?: string;
  notes?: string;
  status?: ContractStatus;
}

export async function updateContract(
  id: string,
  data: UpdateContractRequest
): Promise<Contract> {
  return api.patch<Contract>(`/contracts/${id}/`, data);
}

/**
 * 契約休会
 */
export interface SuspendContractRequest {
  reason?: string;
  suspendFrom?: string;
  suspendUntil?: string;
}

export async function suspendContract(
  id: string,
  data?: SuspendContractRequest
): Promise<Contract> {
  return api.post<Contract>(`/contracts/${id}/suspend/`, data);
}

/**
 * 契約再開
 */
export async function resumeContract(id: string): Promise<Contract> {
  return api.post<Contract>(`/contracts/${id}/resume/`);
}

/**
 * 契約解約
 */
export interface CancelContractRequest {
  reason?: string;
  cancelDate?: string;
}

export async function cancelContract(
  id: string,
  data?: CancelContractRequest
): Promise<Contract> {
  return api.post<Contract>(`/contracts/${id}/cancel/`, data);
}

/**
 * 契約の支払い履歴取得
 */
export async function getContractPayments(
  contractId: string
): Promise<ContractPayment[]> {
  return api.get<ContractPayment[]>(`/contracts/${contractId}/payments/`);
}
