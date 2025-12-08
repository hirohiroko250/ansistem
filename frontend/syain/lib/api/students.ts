/**
 * Students API
 * 生徒管理関連のAPI関数
 */

import api from './client';
import type {
  Student,
  StudentDetail,
  PaginatedResponse,
} from './types';

// 検索パラメータ型
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
 * 生徒一覧取得
 */
export async function getStudents(
  params?: StudentSearchParams
): Promise<PaginatedResponse<Student>> {
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

  return api.get<PaginatedResponse<Student>>(endpoint);
}

/**
 * 生徒詳細取得
 */
export async function getStudent(id: string): Promise<StudentDetail> {
  return api.get<StudentDetail>(`/students/${id}/`);
}

/**
 * 生徒作成
 */
export interface CreateStudentRequest {
  userId: string;
  studentNumber?: string;
  grade?: string;
  schoolName?: string;
  enrollmentDate?: string;
  status?: string;
  notes?: string;
}

export async function createStudent(data: CreateStudentRequest): Promise<Student> {
  return api.post<Student>('/students/', data);
}

/**
 * 生徒更新
 */
export interface UpdateStudentRequest {
  studentNumber?: string;
  grade?: string;
  schoolName?: string;
  enrollmentDate?: string;
  withdrawalDate?: string;
  status?: string;
  notes?: string;
}

export async function updateStudent(
  id: string,
  data: UpdateStudentRequest
): Promise<Student> {
  return api.patch<Student>(`/students/${id}/`, data);
}

/**
 * 生徒削除
 */
export async function deleteStudent(id: string): Promise<void> {
  return api.delete<void>(`/students/${id}/`);
}

/**
 * 生徒のチケット残高取得
 */
export async function getStudentTicketBalance(studentId: string) {
  return api.get(`/students/${studentId}/tickets/`);
}

/**
 * 生徒の保護者一覧取得
 */
export async function getStudentGuardians(studentId: string) {
  return api.get(`/students/${studentId}/guardians/`);
}

/**
 * 生徒の予約履歴取得
 */
export async function getStudentReservations(
  studentId: string,
  params?: { status?: string; startDate?: string; endDate?: string }
) {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.append('status', params.status);
  if (params?.startDate) queryParams.append('start_date', params.startDate);
  if (params?.endDate) queryParams.append('end_date', params.endDate);

  const query = queryParams.toString();
  return api.get(`/students/${studentId}/reservations/${query ? `?${query}` : ''}`);
}
