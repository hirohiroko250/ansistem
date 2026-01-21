/**
 * Staff API - Django Backend Connection
 */

import apiClient from "./client";
import type {
  Brand,
  School,
  Student,
  Guardian,
  Contract,
  StudentItem,
  Invoice,
  Course,
  LessonSchedule,
  Staff,
  PaginatedResponse,
  PaginatedResult,
  StudentFilters,
  DashboardData,
  DashboardStats,
  BrandStats,
  SchoolStats,
  DiscountMaster,
} from "./types";

// Re-export types for backward compatibility
export type {
  Brand,
  School,
  School as Campus,
  Student,
  Guardian as Parent,
  Contract,
  StudentItem,
  Invoice,
  LessonSchedule as Lesson,
  Staff,
  PaginatedResult,
  StudentFilters,
};

export type Task = {
  id: string;
  title: string;
  description: string;
  task_type: string;
  task_type_display?: string;
  status: string;
  status_display?: string;
  priority: string;
  priority_display?: string;
  category?: string;
  category_name?: string;
  school?: string;
  school_name?: string;
  brand?: string;
  brand_name?: string;
  student?: string;
  student_no?: string;
  student_name?: string;
  guardian?: string;
  guardian_no?: string;
  guardian_name?: string;
  assigned_to_id?: string;
  assigned_to_name?: string;
  created_by_id?: string;
  due_date?: string;
  completed_at?: string;
  source_type?: string;
  source_id?: string;
  source_url?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at?: string;
};

export type Message = {
  id: string;
  sender_type: string;
  sender_id: string;
  receiver_type: string;
  receiver_id: string;
  subject: string;
  content: string;
  read_at: string | null;
  created_at: string;
};

// ============================================================================
// 会社（ブランドカテゴリ）・ブランド・校舎
// ============================================================================

export type BrandCategory = {
  id: string;
  name: string;
  code: string;
};

export type Tenant = {
  id: string;
  tenant_code?: string;
  tenantCode?: string;
  tenant_name?: string;
  tenantName?: string;
  plan_type?: string;
  planType?: string;
  is_active?: boolean;
  isActive?: boolean;
};

export async function getTenants(): Promise<Tenant[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/tenants/");
    if (Array.isArray(response)) {
      return response;
    }
    if (response.data && Array.isArray(response.data)) {
      return response.data;
    }
    if (response.results && Array.isArray(response.results)) {
      return response.results;
    }
    return [];
  } catch (error) {
    console.error("Error fetching tenants:", error);
    return [];
  }
}

export async function getBrandCategories(): Promise<BrandCategory[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/schools/public/brand-categories/");
    if (Array.isArray(response)) {
      return response;
    }
    if (response.data && Array.isArray(response.data)) {
      return response.data;
    }
    if (response.results && Array.isArray(response.results)) {
      return response.results;
    }
    return [];
  } catch (error) {
    console.error("Error fetching brand categories:", error);
    return [];
  }
}

export async function getBrands(categoryId?: string): Promise<Brand[]> {
  try {
    const params: Record<string, string | number | undefined> = { page_size: 100 };
    if (categoryId) {
      params.brand_category_id = categoryId;
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/schools/brands/", params);
    console.log("[getBrands] response:", response);
    // Handle both paginated and non-paginated responses
    if (Array.isArray(response)) {
      console.log("[getBrands] returning array directly:", response.length);
      return response;
    }
    // Handle { data: [...] } format (DRF with custom renderer)
    if (response.data && Array.isArray(response.data)) {
      console.log("[getBrands] returning response.data:", response.data.length);
      return response.data;
    }
    // Handle { results: [...] } format (standard DRF pagination)
    if (response.results && Array.isArray(response.results)) {
      console.log("[getBrands] returning response.results:", response.results.length);
      return response.results;
    }
    console.log("[getBrands] returning empty array");
    return [];
  } catch (error) {
    console.error("Error fetching brands:", error);
    return [];
  }
}

export async function getCampuses(brandId?: string): Promise<School[]> {
  try {
    const params: Record<string, string | number | undefined> = { page_size: 100 };
    if (brandId) {
      params.brand_id = brandId;
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/schools/schools/", params);
    if (Array.isArray(response)) {
      return response;
    }
    // Handle { data: [...] } format (DRF with custom renderer)
    if (response.data && Array.isArray(response.data)) {
      return response.data;
    }
    // Handle { results: [...] } format (standard DRF pagination)
    if (response.results && Array.isArray(response.results)) {
      return response.results;
    }
    return [];
  } catch (error) {
    console.error("Error fetching schools:", error);
    return [];
  }
}

// ============================================================================
// 生徒
// ============================================================================

export async function getStudents(filters?: StudentFilters): Promise<PaginatedResult<Student>> {
  const page = filters?.page || 1;
  const pageSize = filters?.page_size || 50;

  try {
    const params: Record<string, string | number | undefined> = {
      page,
      page_size: pageSize,
    };

    if (filters?.search) {
      params.search = filters.search;
    }
    if (filters?.student_no) {
      params.student_no = filters.student_no;
    }
    if (filters?.brand_category_id) {
      params.brand_category_id = filters.brand_category_id;
    }
    if (filters?.brand_id) {
      params.brand_id = filters.brand_id;
    }
    if (filters?.school_id) {
      params.primary_school_id = filters.school_id;
    }
    if (filters?.status) {
      params.status = filters.status;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/students/", params);

    // Handle different API response formats
    // Format 1: { data: [...], meta: { total, page, limit, totalPages } }
    // Format 2: { results: [...], count: number }
    const students = response.data || response.results || [];
    const total = response.meta?.total || response.count || 0;

    return {
      data: students,
      count: total,
      page,
      pageSize,
      totalPages: Math.ceil(total / pageSize),
    };
  } catch (error) {
    console.error("Error fetching students:", error);
    return {
      data: [],
      count: 0,
      page,
      pageSize,
      totalPages: 0,
    };
  }
}

export async function getStudentDetail(id: string): Promise<Student | null> {
  try {
    return await apiClient.get<Student>(`/students/${id}/`);
  } catch (error) {
    console.error("Error fetching student detail:", error);
    return null;
  }
}

export async function getStudentLessons(studentId: string): Promise<LessonSchedule[]> {
  try {
    const response = await apiClient.get<PaginatedResponse<LessonSchedule> | LessonSchedule[]>(
      "/lessons/schedules/",
      { student_id: studentId, page_size: 10 }
    );
    if (Array.isArray(response)) {
      return response;
    }
    return response.results || [];
  } catch (error) {
    console.error("Error fetching student lessons:", error);
    return [];
  }
}

export async function getStudentParents(studentId: string): Promise<Guardian[]> {
  try {
    // Get student detail which includes guardian info
    const student = await getStudentDetail(studentId);
    if (student?.guardian) {
      return [student.guardian];
    }
    // guardianId/guardian_idがある場合は個別に取得
    const guardianId = student?.guardianId || student?.guardian_id;
    if (guardianId) {
      try {
        const guardian = await apiClient.get<Guardian>(`/students/guardians/${guardianId}/`);
        return guardian ? [guardian] : [];
      } catch {
        // Guardian fetch failed, return empty
      }
    }
    return [];
  } catch (error) {
    console.error("Error fetching student parents:", error);
    return [];
  }
}

/**
 * 兄弟（同じ保護者の生徒）を取得
 */
export async function getSiblings(studentId: string): Promise<Student[]> {
  try {
    // まず生徒詳細から保護者IDを取得
    const student = await getStudentDetail(studentId);
    const guardianId = student?.guardianId || student?.guardian_id || student?.guardian?.id;

    if (!guardianId) {
      return [];
    }

    // 保護者IDで生徒を検索
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/students/", {
      guardian_id: guardianId,
      page_size: 20,
    });

    const students = response.data || response.results || [];
    // 自分自身を除外
    return students.filter((s: Student) => s.id !== studentId);
  } catch (error) {
    console.error("Error fetching siblings:", error);
    return [];
  }
}

export async function getStudentContracts(
  studentId: string,
  options?: { year?: number; month?: number }
): Promise<Contract[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const params: any = {
      student_id: studentId,
      page_size: 100,
    };

    // 請求月フィルタが指定されている場合
    if (options?.year && options?.month) {
      params.year = options.year;
      params.month = options.month;
    }

    const response = await apiClient.get<any>("/contracts/", params);
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching student contracts:", error);
    return [];
  }
}

export async function getStudentItems(studentId: string): Promise<StudentItem[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/contracts/student-items/", {
      student_id: studentId,
      page_size: 100,
    });
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching student items:", error);
    return [];
  }
}

// 生徒商品一覧（全件取得）
export type StudentItemFilters = {
  student_id?: string;
  billing_month?: string;
  brand_id?: string;
  school_id?: string;
  year?: string;
  month?: string;
};

export async function getAllStudentItems(filters?: StudentItemFilters): Promise<StudentItem[]> {
  try {
    console.log("[getAllStudentItems] Starting API call with filters:", filters);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const params: Record<string, string | number | undefined> = {
      limit: 200,
    };
    if (filters?.student_id) params.student_id = filters.student_id;
    if (filters?.billing_month) params.billing_month = filters.billing_month;
    if (filters?.brand_id) params.brand_id = filters.brand_id;
    if (filters?.school_id) params.school_id = filters.school_id;
    // 年月フィルタ
    if (filters?.year && filters.year !== "all") params.year = filters.year;
    if (filters?.month && filters.month !== "all") params.month = filters.month;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/contracts/student-items/", params as any);
    console.log("[getAllStudentItems] response:", response);
    const data = response.data || response.results || [];
    console.log("[getAllStudentItems] returning", data.length, "items");
    return data;
  } catch (error) {
    console.error("[getAllStudentItems] Error:", error);
    return [];
  }
}

// 生徒割引
export type StudentDiscount = {
  id: string;
  old_id?: string;
  student?: string;
  student_name?: string;
  student_no?: string;
  guardian?: string;
  guardian_name?: string;
  contract?: string;
  student_item?: string;
  brand?: string;
  brand_name?: string;
  discount_name: string;
  amount: number;
  discount_unit: string;
  discount_unit_display?: string;
  start_date?: string;
  end_date?: string;
  is_recurring: boolean;
  is_auto: boolean;
  end_condition: string;
  end_condition_display?: string;
  is_active: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
};

export type StudentDiscountFilters = {
  student_id?: string;
  guardian_id?: string;
  contract_id?: string;
  is_active?: boolean;
  year?: string;
  month?: string;
  brand_id?: string;
};

export async function getAllStudentDiscounts(filters?: StudentDiscountFilters): Promise<StudentDiscount[]> {
  try {
    console.log("[getAllStudentDiscounts] Starting API call with filters:", filters);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const params: Record<string, string | number | boolean | undefined> = {
      limit: 200,
    };
    if (filters?.student_id) params.student_id = filters.student_id;
    if (filters?.guardian_id) params.guardian_id = filters.guardian_id;
    if (filters?.contract_id) params.contract_id = filters.contract_id;
    if (filters?.is_active !== undefined) params.is_active = filters.is_active;
    if (filters?.brand_id) params.brand_id = filters.brand_id;
    // 年月フィルタ
    if (filters?.year && filters.year !== "all") params.year = filters.year;
    if (filters?.month && filters.month !== "all") params.month = filters.month;

    const response = await apiClient.get<any>("/contracts/student-discounts/", params);
    console.log("[getAllStudentDiscounts] response:", response);
    const data = response.data || response.results || [];
    console.log("[getAllStudentDiscounts] returning", data.length, "discounts");
    return data;
  } catch (error) {
    console.error("[getAllStudentDiscounts] Error:", error);
    return [];
  }
}

export interface StudentDiscountUpdateData {
  amount?: number;
  discount_unit?: 'fixed' | 'percent';
  start_date?: string;
  end_date?: string | null;
  is_active?: boolean;
  notes?: string;
}

export async function updateStudentDiscount(id: string, data: StudentDiscountUpdateData): Promise<StudentDiscount> {
  const response = await apiClient.patch<StudentDiscount>(`/contracts/student-discounts/${id}/`, data);
  return response;
}

export async function deleteStudentDiscount(id: string): Promise<void> {
  await apiClient.delete(`/contracts/student-discounts/${id}/`);
}

export async function getStudentInvoices(studentId: string): Promise<Invoice[]> {
  try {
    // ConfirmedBillingから生徒の請求データを取得
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/billing/confirmed/", {
      student_id: studentId,
      page_size: 100,
    });
    // DRFのページネーションレスポンス形式に対応
    const results = response.results || response.data || (Array.isArray(response) ? response : []);

    // ConfirmedBillingのデータをInvoice形式に変換
    // items_snapshotの各項目を個別のInvoiceレコードとして展開
    const invoices: Invoice[] = [];

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    results.forEach((cb: any) => {
      const billingMonth = `${cb.year}年${cb.month}月`;
      const items = cb.itemsSnapshot || cb.items_snapshot || [];
      const status = cb.status;
      const paymentMethod = cb.paymentMethod || cb.payment_method;
      const paidAmount = Number(cb.paidAmount || cb.paid_amount || 0);
      const totalAmount = Number(cb.totalAmount || cb.total_amount || 0);
      // 繰越額（前月からの繰越）
      const carryOverAmount = Number(cb.carryOverAmount || cb.carry_over_amount || 0);

      if (items.length > 0) {
        // items_snapshotの各項目を個別のInvoiceとして追加
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        items.forEach((item: any, index: number) => {
          const itemTotal = Number(item.final_price || item.finalPrice || 0);
          // 入金を按分（全体に対する各項目の割合で）
          const itemPaid = totalAmount > 0 ? Math.round(paidAmount * (itemTotal / totalAmount)) : 0;

          invoices.push({
            id: `${cb.id}-${index}`,
            billingMonth,
            billing_month: billingMonth,
            billing_year: cb.year,
            totalAmount: itemTotal,
            total_amount: itemTotal,
            paidAmount: itemPaid,
            paid_amount: itemPaid,
            balance: itemTotal - itemPaid,
            // 繰越額は最初の項目にのみ設定
            carryOverAmount: index === 0 ? carryOverAmount : 0,
            carry_over_amount: index === 0 ? carryOverAmount : 0,
            status,
            paymentMethod,
            payment_method: paymentMethod,
            courseName: item.product_name || item.productName || item.notes || '',
            course_name: item.product_name || item.productName || item.notes || '',
            brandName: item.brand_name || item.brandName || '',
            brand_name: item.brand_name || item.brandName || '',
            description: item.notes || '',
            confirmed_at: cb.confirmedAt || cb.confirmed_at,
            paid_at: cb.paidAt || cb.paid_at,
          } as Invoice);
        });
      } else {
        // items_snapshotが空の場合は月のサマリーを追加
        invoices.push({
          id: cb.id,
          billingMonth,
          billing_month: billingMonth,
          billing_year: cb.year,
          totalAmount: totalAmount,
          total_amount: totalAmount,
          paidAmount: paidAmount,
          paid_amount: paidAmount,
          balance: cb.balance,
          carryOverAmount: carryOverAmount,
          carry_over_amount: carryOverAmount,
          status,
          paymentMethod,
          payment_method: paymentMethod,
          description: '月額請求',
          confirmed_at: cb.confirmedAt || cb.confirmed_at,
          paid_at: cb.paidAt || cb.paid_at,
        } as Invoice);
      }
    });

    return invoices;
  } catch (error) {
    console.error("Error fetching student invoices:", error);
    return [];
  }
}

// ============================================================================
// 保護者
// ============================================================================

export async function getParents(): Promise<Guardian[]> {
  try {
    const response = await apiClient.get<any>("/students/guardians/", {
      page_size: 100,
    });
    // Handle both response formats: { data } or { results }
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching parents:", error);
    return [];
  }
}

export async function searchParents(
  search?: string
): Promise<{ results: Guardian[]; count: number }> {
  try {
    const params: Record<string, string | number | boolean | undefined> = {
      page_size: 100,
    };
    if (search) {
      params.search = search;
    }
    const response = await apiClient.get<any>("/students/guardians/", params);
    // Handle both response formats: { data, meta } or { results, count }
    const results = response.data || response.results || [];
    const count = response.meta?.total || response.count || 0;
    return {
      results,
      count,
    };
  } catch (error) {
    console.error("Error fetching parents:", error);
    return { results: [], count: 0 };
  }
}

export async function getParentDetail(id: string): Promise<Guardian | null> {
  try {
    return await apiClient.get<Guardian>(`/students/guardians/${id}/`);
  } catch (error) {
    console.error("Error fetching parent detail:", error);
    return null;
  }
}

// ============================================================================
// 契約
// ============================================================================

export type ContractFilters = {
  year?: string;
  month?: string;
  status?: string;
  brand_id?: string;
  school_id?: string;
};

export async function getContracts(filters?: ContractFilters): Promise<Contract[]> {
  try {
    console.log("[getContracts] Starting API call with filters:", filters);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const params: Record<string, string | number | boolean | undefined> = {
      limit: 200,
    };
    // 年月フィルタ
    if (filters?.year && filters.year !== "all") params.year = filters.year;
    if (filters?.month && filters.month !== "all") params.month = filters.month;
    if (filters?.status && filters.status !== "all") params.status = filters.status;
    if (filters?.brand_id && filters.brand_id !== "all") params.brand_id = filters.brand_id;
    if (filters?.school_id && filters.school_id !== "all") params.school_id = filters.school_id;

    const response = await apiClient.get<any>("/contracts/", params);
    console.log("[getContracts] response:", response);
    const data = response.data || response.results || [];
    console.log("[getContracts] returning", data.length, "contracts");
    return data;
  } catch (error) {
    console.error("[getContracts] Error:", error);
    return [];
  }
}

export async function getContractDetail(id: string): Promise<Contract | null> {
  try {
    return await apiClient.get<Contract>(`/contracts/${id}/`);
  } catch (error) {
    console.error("Error fetching contract detail:", error);
    return null;
  }
}

// 操作履歴
export interface OperationHistoryItem {
  id: string;
  date: string;
  type: string;
  type_display: string;
  student_id?: string;
  student_name?: string;
  guardian_id?: string;
  guardian_name?: string;
  content: string;
  status?: string;
  status_display?: string;
  amount?: number;
  operator?: string;
  created_at: string;
}

export async function getOperationHistory(params?: {
  year?: string;
  month?: string;
  limit?: number;
}): Promise<OperationHistoryItem[]> {
  try {
    console.log("[getOperationHistory] Starting API call...");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/contracts/operation-history/", {
      ...params,
      limit: params?.limit || 100,  // Small limit for fast initial load
    });
    console.log("[getOperationHistory] response:", response);
    const data = response.data || response.results || [];
    console.log("[getOperationHistory] returning", data.length, "items");
    return data;
  } catch (error) {
    console.error("[getOperationHistory] Error:", error);
    return [];
  }
}

interface DiscountUpdate {
  id?: string;
  student_item_id?: string;  // 明細ID（optional）
  product_name?: string;
  discount_name: string;
  amount: number;
  discount_unit: "yen" | "percent";
  is_new?: boolean;
  is_deleted?: boolean;
}

interface ContractDiscountUpdateRequest {
  item_discounts?: DiscountUpdate[];  // 明細単位の割引
  discounts?: DiscountUpdate[];       // 後方互換性
  notes?: string;
}

interface ContractDiscountUpdateResponse {
  success: boolean;
  created: number;
  updated: number;
  deleted: number;
  contract: Contract;
}

export async function updateContractDiscounts(
  contractId: string,
  updates: ContractDiscountUpdateRequest
): Promise<ContractDiscountUpdateResponse> {
  try {
    return await apiClient.post<ContractDiscountUpdateResponse>(
      `/contracts/${contractId}/update-discounts/`,
      updates
    );
  } catch (error) {
    console.error("Error updating contract discounts:", error);
    throw error;
  }
}

// ============================================================================
// 授業
// ============================================================================

export async function getLessons(): Promise<LessonSchedule[]> {
  try {
    const response = await apiClient.get<PaginatedResponse<LessonSchedule>>("/lessons/schedules/", {
      page_size: 100,
    });
    return response.results || [];
  } catch (error) {
    console.error("Error fetching lessons:", error);
    return [];
  }
}

// ============================================================================
// タスク
// ============================================================================

export async function getTasks(filters?: {
  status?: string;
  priority?: string;
  task_type?: string;
}): Promise<Task[]> {
  try {
    const params: Record<string, string | undefined> = {};
    if (filters?.status) params.status = filters.status;
    if (filters?.priority) params.priority = filters.priority;
    if (filters?.task_type) params.task_type = filters.task_type;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/tasks/", params);
    if (Array.isArray(response)) {
      return response;
    }
    // Handle both { data: [...] } and { results: [...] } formats
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching tasks:", error);
    return [];
  }
}

export async function getPendingTasks(): Promise<Task[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/tasks/pending/");
    if (Array.isArray(response)) {
      return response;
    }
    // Handle both { data: [...] } and { results: [...] } formats
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching pending tasks:", error);
    return [];
  }
}

export async function getTaskDetail(id: string): Promise<Task | null> {
  try {
    return await apiClient.get<Task>(`/tasks/${id}/`);
  } catch (error) {
    console.error("Error fetching task detail:", error);
    return null;
  }
}

export async function createTask(data: Partial<Task>): Promise<Task | null> {
  try {
    return await apiClient.post<Task>("/tasks/", data);
  } catch (error) {
    console.error("Error creating task:", error);
    return null;
  }
}

export async function updateTask(id: string, data: Partial<Task>): Promise<Task | null> {
  try {
    return await apiClient.patch<Task>(`/tasks/${id}/`, data);
  } catch (error) {
    console.error("Error updating task:", error);
    return null;
  }
}

export async function completeTask(id: string): Promise<Task | null> {
  try {
    return await apiClient.post<Task>(`/tasks/${id}/complete/`);
  } catch (error) {
    console.error("Error completing task:", error);
    return null;
  }
}

export async function reopenTask(id: string): Promise<Task | null> {
  try {
    return await apiClient.post<Task>(`/tasks/${id}/reopen/`);
  } catch (error) {
    console.error("Error reopening task:", error);
    return null;
  }
}

/**
 * 社員登録タスクを承認する
 */
export async function approveEmployeeTask(taskId: string): Promise<{
  success: boolean;
  message: string;
  task?: Task;
  employee_id?: string;
} | null> {
  try {
    return await apiClient.post(`/tasks/${taskId}/approve_employee/`);
  } catch (error) {
    console.error("Error approving employee task:", error);
    throw error;
  }
}

/**
 * 社員登録タスクを却下する
 */
export async function rejectEmployeeTask(taskId: string): Promise<{
  success: boolean;
  message: string;
  task?: Task;
} | null> {
  try {
    return await apiClient.post(`/tasks/${taskId}/reject_employee/`);
  } catch (error) {
    console.error("Error rejecting employee task:", error);
    throw error;
  }
}

export async function getMyTasks(filters?: {
  status?: string;
}): Promise<Task[]> {
  try {
    const params: Record<string, string | undefined> = {};
    if (filters?.status) params.status = filters.status;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/tasks/my_tasks/", params);
    if (Array.isArray(response)) {
      return response;
    }
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching my tasks:", error);
    return [];
  }
}

export async function getTasksByAssignee(assigneeId: string, filters?: {
  status?: string;
}): Promise<Task[]> {
  try {
    const params: Record<string, string | undefined> = {
      assignee_id: assigneeId,
    };
    if (filters?.status) params.status = filters.status;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/tasks/by_assignee/", params);
    if (Array.isArray(response)) {
      return response;
    }
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching tasks by assignee:", error);
    return [];
  }
}

// ============================================================================
// タスクコメント
// ============================================================================

export type TaskComment = {
  id: string;
  task: string;
  comment: string;
  commented_by_id?: string;
  commented_by_name?: string;
  is_internal: boolean;
  created_at: string;
  updated_at?: string;
};

export async function getTaskComments(taskId: string): Promise<TaskComment[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/tasks/comments/", { task: taskId });
    if (Array.isArray(response)) {
      return response;
    }
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching task comments:", error);
    return [];
  }
}

export async function createTaskComment(data: {
  task: string;
  comment: string;
  commented_by_id?: string;
  is_internal?: boolean;
}): Promise<TaskComment | null> {
  try {
    console.log('[createTaskComment] Sending request:', data);
    const result = await apiClient.post<TaskComment>("/tasks/comments/", data);
    console.log('[createTaskComment] Response:', result);
    return result;
  } catch (error: unknown) {
    console.error("[createTaskComment] Error:", error);
    // Extract more details from the error
    if (error && typeof error === 'object') {
      const err = error as { response?: { data?: unknown; status?: number }; message?: string };
      if (err.response) {
        console.error("[createTaskComment] Response data:", err.response.data);
        console.error("[createTaskComment] Response status:", err.response.status);
      }
      if (err.message) {
        console.error("[createTaskComment] Error message:", err.message);
      }
    }
    return null;
  }
}

// ============================================================================
// メッセージ（仮実装 - 必要に応じてDjango側にエンドポイント追加）
// ============================================================================

export async function getMessages(): Promise<Message[]> {
  // TODO: Implement when Django message endpoint is available
  console.warn("getMessages: Not implemented yet");
  return [];
}

// ============================================================================
// ダッシュボード
// ============================================================================

export interface DashboardDataLegacy {
  totalStudents: number;
  todayLessons: number;
  pendingTasks: number;
  unreadMessages: number;
  recentTasks: Task[];
  upcomingLessons: LessonSchedule[];
  brandStats: { brandId: string; brandName: string; studentCount: number; color: string }[];
  campusStats: { campusId: string; campusName: string; studentCount: number }[];
  activeStudents: number;
  inactiveStudents: number;
}

export async function getDashboard(): Promise<DashboardDataLegacy> {
  try {
    // Fetch data from multiple endpoints
    const [studentsResponse, brandsData, schoolsData] = await Promise.all([
      apiClient.get<PaginatedResponse<Student>>("/students/", { page_size: 1 }),
      getBrands(),
      getCampuses(),
    ]);

    const totalStudents = studentsResponse.count || 0;

    // Get active/inactive counts
    const [activeResponse, inactiveResponse] = await Promise.all([
      apiClient.get<PaginatedResponse<Student>>("/students/", { status: "enrolled", page_size: 1 }),
      apiClient.get<PaginatedResponse<Student>>("/students/", { status: "suspended", page_size: 1 }),
    ]);

    // Calculate brand stats (simplified - would need aggregation endpoint for accuracy)
    const brandStats = brandsData.map((brand) => ({
      brandId: brand.id,
      brandName: brand.brandName || brand.brand_name || "",
      studentCount: 0, // Would need aggregation endpoint
      color: brand.colorPrimary || brand.brand_color || "#3B82F6",
    }));

    const campusStats = schoolsData.slice(0, 10).map((school) => ({
      campusId: school.id,
      campusName: school.schoolName || school.school_name || "",
      studentCount: 0, // Would need aggregation endpoint
    }));

    return {
      totalStudents,
      todayLessons: 0, // Would need lessons endpoint with date filter
      pendingTasks: 0,
      unreadMessages: 0,
      recentTasks: [],
      upcomingLessons: [],
      brandStats,
      campusStats,
      activeStudents: activeResponse.count || 0,
      inactiveStudents: inactiveResponse.count || 0,
    };
  } catch (error) {
    console.error("Error fetching dashboard:", error);
    return {
      totalStudents: 0,
      todayLessons: 0,
      pendingTasks: 0,
      unreadMessages: 0,
      recentTasks: [],
      upcomingLessons: [],
      brandStats: [],
      campusStats: [],
      activeStudents: 0,
      inactiveStudents: 0,
    };
  }
}

// ============================================================================
// 認証
// ============================================================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: {
    id: string;
    email: string;
    username: string;
  };
}

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>("/auth/login/", credentials);
  apiClient.setToken(response.access);
  return response;
}

export async function logout(): Promise<void> {
  apiClient.setToken(null);
}

export async function refreshToken(refresh: string): Promise<{ access: string }> {
  return apiClient.post<{ access: string }>("/auth/token/refresh/", { refresh });
}

// ============================================================================
// カレンダー
// ============================================================================

export type CalendarEvent = {
  id: string;
  scheduleCode: string;
  className: string;
  displayCourseName: string;
  startTime: string;
  endTime: string;
  period: number;
  brandId: string | null;
  brandName: string | null;
  brandColor: string | null;
  lessonType: string;
  lessonTypeLabel: string;
  capacity: number;
  enrolledCount: number;
  availableSeats: number;
  roomName: string | null;
  calendarPattern: string | null;
  ticketName: string | null;
  presentCount: number;
  absentCount: number;
};

export type CalendarDay = {
  date: string;
  day: number;
  dayOfWeek: number;
  dayName: string;
  isWeekend: boolean;
  isClosed: boolean;
  closureReason: string | null;
  events: CalendarEvent[];
};

export type CalendarResponse = {
  year: number;
  month: number;
  schoolId: string;
  brandId: string | null;
  days: CalendarDay[];
};

export type CalendarEventDetailStudent = {
  id: string;
  studentNo: string;
  name: string;
  nameKana: string;
  grade: string;
  guardianName: string | null;
  guardianPhone: string | null;
  enrollmentType: string;
  attendanceStatus: string;
};

export type CalendarEventDetail = {
  scheduleId: string;
  date: string;
  schedule: {
    className: string;
    displayCourseName: string;
    startTime: string;
    endTime: string;
    brandName: string | null;
    schoolName: string | null;
    roomName: string | null;
    capacity: number;
    lessonType: string;
    lessonTypeLabel: string;
    calendarPattern: string | null;
  };
  summary: {
    totalEnrolled: number;
    presentCount: number;
    absentCount: number;
    unknownCount: number;
  };
  students: CalendarEventDetailStudent[];
};

export async function getCalendar(params: {
  schoolId: string;
  year: number;
  month: number;
  brandId?: string;
}): Promise<CalendarResponse | null> {
  try {
    const queryParams: Record<string, string> = {
      school_id: params.schoolId,
      year: String(params.year),
      month: String(params.month),
    };
    if (params.brandId) {
      queryParams.brand_id = params.brandId;
    }
    return await apiClient.get<CalendarResponse>("/schools/admin/calendar/", queryParams);
  } catch (error) {
    console.error("Error fetching calendar:", error);
    return null;
  }
}

export async function getCalendarEventDetail(params: {
  scheduleId: string;
  date: string;
}): Promise<CalendarEventDetail | null> {
  try {
    return await apiClient.get<CalendarEventDetail>("/schools/admin/calendar/event/", {
      schedule_id: params.scheduleId,
      date: params.date,
    });
  } catch (error) {
    console.error("Error fetching calendar event detail:", error);
    return null;
  }
}

// ============================================================================
// 出欠管理
// ============================================================================

export type MarkAttendanceResponse = {
  success: boolean;
  message: string;
  absence_ticket_id?: string;
  consumption_symbol?: string;
  valid_until?: string;
};

export async function markAttendance(params: {
  studentId: string;
  scheduleId: string;
  date: string;
  status: 'present' | 'absent';
  reason?: string;
}): Promise<MarkAttendanceResponse | null> {
  try {
    return await apiClient.post<MarkAttendanceResponse>("/schools/admin/calendar/attendance/", {
      student_id: params.studentId,
      schedule_id: params.scheduleId,
      date: params.date,
      status: params.status,
      reason: params.reason || '',
    });
  } catch (error) {
    console.error("Error marking attendance:", error);
    return null;
  }
}

// ============================================================================
// ABスワップ
// ============================================================================

export type ABSwapResponse = {
  success: boolean;
  calendarPattern: string;
  date: string;
  oldType: string;
  newType: string;
  message: string;
};

/**
 * ABスワップを実行
 * @param calendarPattern カレンダーパターン (例: 1001_SKAEC_A)
 * @param date 日付 (YYYY-MM-DD)
 * @param newType 新しいタイプ (A, B, P, Y) - オプション、指定しない場合は自動切り替え
 */
export async function performABSwap(params: {
  calendarPattern: string;
  date: string;
  newType?: "A" | "B" | "P" | "Y";
}): Promise<ABSwapResponse | null> {
  try {
    return await apiClient.post<ABSwapResponse>("/schools/admin/calendar/ab-swap/", {
      calendar_pattern: params.calendarPattern,
      date: params.date,
      new_type: params.newType,
    });
  } catch (error) {
    console.error("Error performing AB swap:", error);
    return null;
  }
}

// ============================================================================
// 休校設定
// ============================================================================

export type ClosureType =
  | "school_closed"
  | "brand_closed"
  | "schedule_closed"
  | "holiday"
  | "maintenance"
  | "weather"
  | "other";

export type SchoolClosure = {
  id: string;
  schoolId: string | null;
  schoolName: string | null;
  brandId: string | null;
  brandName: string | null;
  scheduleId: string | null;
  closureDate: string;
  closureType: ClosureType;
  closureTypeDisplay: string;
  reason: string | null;
  isAllDay: boolean;
};

export type CreateClosureParams = {
  schoolId?: string;
  brandId?: string;
  scheduleId?: string;
  closureDate: string;
  closureType: ClosureType;
  reason?: string;
};

/**
 * 休校一覧を取得
 */
export async function getClosures(params?: {
  schoolId?: string;
  brandId?: string;
  startDate?: string;
  endDate?: string;
}): Promise<SchoolClosure[]> {
  try {
    const queryParams: Record<string, string | undefined> = {};
    if (params?.schoolId) queryParams.school_id = params.schoolId;
    if (params?.brandId) queryParams.brand_id = params.brandId;
    if (params?.startDate) queryParams.start_date = params.startDate;
    if (params?.endDate) queryParams.end_date = params.endDate;

    const response = await apiClient.get<PaginatedResponse<SchoolClosure> | SchoolClosure[]>(
      "/schools/closures/",
      { ...queryParams, page_size: 100 }
    );

    if (Array.isArray(response)) {
      return response;
    }
    return response.results || [];
  } catch (error) {
    console.error("Error fetching closures:", error);
    return [];
  }
}

/**
 * 休校を作成
 */
export async function createClosure(params: CreateClosureParams): Promise<SchoolClosure | null> {
  try {
    return await apiClient.post<SchoolClosure>("/schools/closures/", {
      school: params.schoolId,
      brand: params.brandId,
      schedule: params.scheduleId,
      closure_date: params.closureDate,
      closure_type: params.closureType,
      reason: params.reason,
    });
  } catch (error) {
    console.error("Error creating closure:", error);
    return null;
  }
}

/**
 * 休校を削除
 */
export async function deleteClosure(id: string): Promise<boolean> {
  try {
    await apiClient.delete(`/schools/closures/${id}/`);
    return true;
  } catch (error) {
    console.error("Error deleting closure:", error);
    return false;
  }
}

// ============================================================================
// カレンダーCSVエクスポート/インポート
// ============================================================================

/**
 * カレンダーCSVエクスポート
 */
export async function exportCalendarCSV(params: {
  schoolId: string;
  year: number;
  month: number;
  brandId?: string;
}): Promise<string | null> {
  try {
    const queryParams: Record<string, string | number> = {
      school_id: params.schoolId,
      year: params.year,
      month: params.month,
    };
    if (params.brandId) {
      queryParams.brand_id = params.brandId;
    }

    // Get CSV data as blob
    const blob = await apiClient.getBlob("/schools/closures/export/", queryParams);

    // Create download URL
    const url = URL.createObjectURL(blob);
    return url;
  } catch (error) {
    console.error("Error exporting calendar CSV:", error);
    return null;
  }
}

/**
 * カレンダーCSVインポート
 */
export async function importCalendarCSV(file: File): Promise<{ success: boolean; message: string }> {
  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await apiClient.postFormData<{ success: boolean; message: string }>(
      "/schools/closures/import/",
      formData
    );

    return response;
  } catch (error) {
    console.error("Error importing calendar CSV:", error);
    return { success: false, message: "インポートに失敗しました" };
  }
}

// ============================================================================
// コミュニケーション（対応履歴）
// ============================================================================

export type ContactLog = {
  id: string;
  student_id?: string;
  student_name?: string;
  guardian_id?: string;
  guardian_name?: string;
  school_id?: string;
  school_name?: string;
  contact_type: string;
  contact_type_display?: string;
  subject: string;
  content: string;
  handled_by_id?: string;
  handled_by_name?: string;
  priority: string;
  priority_display?: string;
  status: string;
  status_display?: string;
  follow_up_date?: string;
  follow_up_notes?: string;
  resolved_at?: string;
  resolved_by_name?: string;
  tags?: string[];
  created_at: string;
  updated_at?: string;
};

export type ChatLog = {
  id: string;
  school_id?: string;
  school_name?: string;
  guardian_id?: string;
  guardian_name?: string;
  brand_id?: string;
  brand_name?: string;
  content: string;
  sender_type: string;
  timestamp: string;
};

export type ChatMessage = {
  id: string;
  channel_id?: string;
  message_type: string;
  sender_id?: string;
  sender_name?: string;
  sender_guardian_id?: string;
  sender_guardian_name?: string;
  is_bot_message: boolean;
  content: string;
  attachment_url?: string;
  attachment_name?: string;
  is_edited: boolean;
  created_at: string;
  // チャンネル情報
  channel_name?: string;
  channel_guardian_name?: string;
  channel_school_name?: string;
};

/**
 * 保護者の対応履歴を取得
 */
export async function getGuardianContactLogs(guardianId: string): Promise<ContactLog[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/communications/contact-logs/", {
      guardian_id: guardianId,
      page_size: 100,
    });
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching guardian contact logs:", error);
    return [];
  }
}

/**
 * 生徒の対応履歴を取得
 */
export async function getStudentContactLogs(studentId: string): Promise<ContactLog[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/communications/contact-logs/", {
      student_id: studentId,
      page_size: 100,
    });
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching student contact logs:", error);
    return [];
  }
}

/**
 * 対応履歴を作成
 */
export type ContactLogCreateData = {
  contact_type: 'PHONE_IN' | 'PHONE_OUT' | 'EMAIL_IN' | 'EMAIL_OUT' | 'VISIT' | 'MEETING' | 'ONLINE_MEETING' | 'CHAT' | 'OTHER';
  subject: string;
  content: string;
  student_id?: string;
  guardian_id?: string;
  school_id?: string;
  priority?: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
  status?: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';
  follow_up_date?: string;
  follow_up_notes?: string;
  tags?: string[];
};

export async function createContactLog(data: ContactLogCreateData): Promise<ContactLog | null> {
  try {
    const response = await apiClient.post<ContactLog>("/communications/contact-logs/", data);
    return response;
  } catch (error) {
    console.error("Error creating contact log:", error);
    throw error;
  }
}

/**
 * 保護者のチャットログを取得
 */
export async function getGuardianChatLogs(guardianId: string): Promise<ChatLog[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/communications/chat-logs/", {
      guardian_id: guardianId,
      page_size: 100,
    });
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching guardian chat logs:", error);
    return [];
  }
}

/**
 * 保護者のチャットメッセージを取得
 */
export async function getGuardianMessages(guardianId: string): Promise<ChatMessage[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/communications/messages/", {
      guardian_id: guardianId,
      page_size: 100,
    });
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching guardian messages:", error);
    return [];
  }
}

// =============================================================================
// Billing API - 請求管理
// =============================================================================

export interface InvoiceFilters {
  billing_year?: number;
  billing_month?: number;
  status?: string;
  guardian_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface InvoiceLine {
  id: string;
  student_id?: string;
  student_name?: string;
  studentName?: string;
  description?: string;
  quantity?: number;
  unit_price?: number | string;
  unitPrice?: number | string;
  line_total?: number | string;
  lineTotal?: number | string;
}

export interface InvoiceDetail extends Invoice {
  lines?: InvoiceLine[];
  guardian_name?: string;
  guardianName?: string;
  guardian_phone?: string;
  guardianPhone?: string;
  guardian_email?: string;
  guardianEmail?: string;
}

export interface DirectDebitExportRequest {
  // 新形式（日付範囲）
  start_date?: string;  // YYYY-MM-DD
  end_date?: string;    // YYYY-MM-DD
  // 旧形式（互換性のため）
  billing_year?: number;
  billing_month?: number;
  provider?: string; // jaccs, ufj_factor, chukyo_finance
}

export interface DirectDebitResult {
  id: string;
  guardian_id?: string;
  guardianId?: string;
  guardian_name?: string;
  guardianName?: string;
  invoice_id?: string;
  invoiceId?: string;
  debit_date?: string;
  debitDate?: string;
  amount?: number | string;
  result_status?: string;
  resultStatus?: string;
  failure_reason?: string;
  failureReason?: string;
}

/**
 * 請求書一覧を取得
 */
export async function getInvoices(filters?: InvoiceFilters): Promise<PaginatedResult<Invoice>> {
  try {
    const params: Record<string, string | number | boolean | undefined> = {
      page: filters?.page || 1,
      page_size: filters?.page_size || 50,
    };
    if (filters?.billing_year) params.billing_year = filters.billing_year;
    if (filters?.billing_month) params.billing_month = filters.billing_month;
    if (filters?.status) params.status = filters.status;
    if (filters?.guardian_id) params.guardian_id = filters.guardian_id;
    if (filters?.search) params.search = filters.search;

    const response = await apiClient.get<PaginatedResponse<Invoice>>("/billing/invoices/", params);
    return {
      data: response.results || [],
      count: response.count || 0,
      page: filters?.page || 1,
      pageSize: filters?.page_size || 50,
      totalPages: Math.ceil((response.count || 0) / (filters?.page_size || 50)),
    };
  } catch (error) {
    console.error("Error fetching invoices:", error);
    return { data: [], count: 0, page: 1, pageSize: 50, totalPages: 0 };
  }
}

/**
 * 請求書詳細を取得
 */
export async function getInvoiceDetail(invoiceId: string): Promise<InvoiceDetail | null> {
  try {
    return await apiClient.get<InvoiceDetail>(`/billing/invoices/${invoiceId}/`);
  } catch (error) {
    console.error("Error fetching invoice detail:", error);
    return null;
  }
}

/**
 * 引落データCSVエクスポート（ConfirmedBillingから）
 */
export async function exportDirectDebitCSV(params: DirectDebitExportRequest): Promise<Blob | null> {
  try {
    const queryParams: Record<string, string | number> = {};

    // 新形式（日付範囲）を優先
    if (params.start_date && params.end_date) {
      queryParams.start_date = params.start_date;
      queryParams.end_date = params.end_date;
    } else if (params.billing_year && params.billing_month) {
      // 旧形式（互換性のため）
      queryParams.year = params.billing_year;
      queryParams.month = params.billing_month;
    }

    if (params.provider) {
      queryParams.provider = params.provider;
    }

    // ConfirmedBillingからエクスポート（確定データ）
    const blob = await apiClient.getBlob("/billing/confirmed/export-debit/", queryParams);
    return blob;
  } catch (error) {
    console.error("Error exporting direct debit CSV:", error);
    return null;
  }
}

/**
 * 引落データCSVエクスポート（Invoiceから、互換性のため残す）
 */
export async function exportDirectDebitCSVFromInvoice(params: DirectDebitExportRequest): Promise<Blob | null> {
  try {
    const queryParams: Record<string, string | number> = {};

    if (params.start_date && params.end_date) {
      queryParams.start_date = params.start_date;
      queryParams.end_date = params.end_date;
    } else if (params.billing_year && params.billing_month) {
      queryParams.billing_year = params.billing_year;
      queryParams.billing_month = params.billing_month;
    }

    if (params.provider) {
      queryParams.provider = params.provider;
    }
    const blob = await apiClient.getBlob("/billing/invoices/export-debit/", queryParams);
    return blob;
  } catch (error) {
    console.error("Error exporting direct debit CSV from invoice:", error);
    return null;
  }
}

/**
 * 引落データエクスポートプレビュー
 */
export interface DirectDebitExportPreview {
  // API returns camelCase
  totalBillings: number;
  totalGuardians: number;
  guardiansWithBank: number;
  guardiansWithoutBank: number;
  totalAmount: number;
  exportableCount: number;
  missingBankGuardians: Array<{
    guardianNo: string;
    name: string;
    bankCode: string;
    accountNumber: string;
  }>;
}

export async function getDirectDebitExportPreview(params: DirectDebitExportRequest): Promise<DirectDebitExportPreview | null> {
  try {
    const queryParams: Record<string, string | number> = {};

    if (params.start_date && params.end_date) {
      queryParams.start_date = params.start_date;
      queryParams.end_date = params.end_date;
    } else if (params.billing_year && params.billing_month) {
      queryParams.year = params.billing_year;
      queryParams.month = params.billing_month;
    }

    // 決済代行会社でフィルタ
    if (params.provider) {
      queryParams.provider = params.provider;
    }

    const response = await apiClient.get<DirectDebitExportPreview>("/billing/confirmed/export-debit-preview/", queryParams);
    return response;
  } catch (error) {
    console.error("Error getting export preview:", error);
    return null;
  }
}

/**
 * 引落結果CSVインポート
 */
export async function importDirectDebitResult(file: File): Promise<{ success: boolean; imported: number; errors: string[] }> {
  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await apiClient.postFormData<{ success: boolean; imported: number; errors: string[] }>(
      "/billing/invoices/import-debit-result/",
      formData
    );
    return response;
  } catch (error) {
    console.error("Error importing direct debit result:", error);
    return { success: false, imported: 0, errors: ["インポートに失敗しました"] };
  }
}

/**
 * 引落結果一覧を取得
 */
export async function getDirectDebitResults(filters?: {
  billing_year?: number;
  billing_month?: number;
  result_status?: string;
}): Promise<DirectDebitResult[]> {
  try {
    const response = await apiClient.get<PaginatedResponse<DirectDebitResult>>("/billing/debit-results/", filters);
    return response.results || [];
  } catch (error) {
    console.error("Error fetching direct debit results:", error);
    return [];
  }
}

// =============================================================================
// 通帳機能（入出金履歴）
// =============================================================================

/**
 * 通帳取引タイプ
 */
export type PassbookTransactionType = 'deposit' | 'offset' | 'refund' | 'adjustment';

/**
 * 通帳取引
 */
export interface PassbookTransaction {
  id: string;
  guardian: string;
  guardian_name?: string;
  guardianName?: string;
  invoice?: string | null;
  invoice_no?: string | null;
  invoiceNo?: string | null;
  invoice_billing_label?: string | null;
  invoiceBillingLabel?: string | null;
  payment?: string | null;
  payment_no?: string | null;
  paymentNo?: string | null;
  payment_method_display?: string | null;
  paymentMethodDisplay?: string | null;
  transaction_type: PassbookTransactionType;
  transactionType?: PassbookTransactionType;
  transaction_type_display?: string;
  transactionTypeDisplay?: string;
  amount: number;
  balance_after: number;
  balanceAfter?: number;
  reason?: string;
  created_at: string;
  createdAt?: string;
}

/**
 * 通帳データ（保護者の入出金履歴）
 */
export interface PassbookData {
  guardian_id: string;
  guardianId?: string;
  guardian_name: string;
  guardianName?: string;
  current_balance: number;
  currentBalance?: number;
  transactions: PassbookTransaction[];
}

/**
 * 保護者の通帳（入出金履歴）を取得
 */
export async function getGuardianPassbook(guardianId: string): Promise<PassbookData | null> {
  try {
    const response = await apiClient.get<PassbookTransaction[]>(`/billing/offset-logs/by-guardian/${guardianId}/`);

    // 残高を別途取得
    const balanceResponse = await apiClient.get<{ balance: number }>(`/billing/balances/by-guardian/${guardianId}/`).catch(() => null);
    const currentBalance = balanceResponse?.balance || 0;

    return {
      guardian_id: guardianId,
      guardian_name: response[0]?.guardian_name || '',
      current_balance: currentBalance,
      transactions: response || [],
    };
  } catch (error) {
    console.error("Error fetching guardian passbook:", error);
    return null;
  }
}

// =============================================================================
// 入金消込（Payment Matching）
// =============================================================================

/**
 * 入金データ
 */
export interface PaymentData {
  id: string;
  payment_no: string;
  guardian?: {
    id: string;
    full_name?: string;
  };
  guardian_name?: string;
  invoice?: {
    id: string;
    invoice_no?: string;
  } | null;
  invoice_no?: string | null;
  payment_date: string;
  amount: number | string;
  method: string;
  method_display?: string;
  status: string;
  status_display?: string;
  payer_name?: string;
  bank_name?: string;
  notes?: string;
  created_at: string;
}

/**
 * 消込候補
 */
export interface MatchCandidate {
  invoice: Invoice;
  match_type: 'amount' | 'name';
  match_score: number;
  match_reason: string;
}

/**
 * 未消込入金一覧を取得
 */
export async function getUnmatchedPayments(): Promise<{ count: number; payments: PaymentData[] }> {
  try {
    const response = await apiClient.get<{ count: number; payments: PaymentData[] }>('/billing/payments/unmatched/');
    return response;
  } catch (error) {
    console.error("Error fetching unmatched payments:", error);
    return { count: 0, payments: [] };
  }
}

/**
 * 入金の消込候補を取得
 */
export async function getMatchCandidates(paymentId: string): Promise<{ payment: PaymentData; candidates: MatchCandidate[] }> {
  try {
    const response = await apiClient.get<{ payment: PaymentData; candidates: MatchCandidate[] }>(`/billing/payments/${paymentId}/match_candidates/`);
    return response;
  } catch (error) {
    console.error("Error fetching match candidates:", error);
    throw error;
  }
}

/**
 * 入金を請求書に消込
 */
export async function matchPaymentToInvoice(paymentId: string, invoiceId: string): Promise<{ success: boolean; payment: PaymentData; invoice: Invoice }> {
  const response = await apiClient.post<{ success: boolean; payment: PaymentData; invoice: Invoice }>(`/billing/payments/${paymentId}/match_invoice/`, {
    invoice_id: invoiceId,
  });
  return response;
}

// =============================================================================
// 相殺ログ・返金申請
// =============================================================================

/**
 * 相殺ログ
 */
export interface OffsetLog {
  id: string;
  guardian: string;
  guardianName?: string;
  guardian_name?: string;
  invoice?: string | null;
  invoiceNo?: string | null;
  invoice_no?: string | null;
  invoiceBillingLabel?: string | null;
  invoice_billing_label?: string | null;
  payment?: string | null;
  paymentNo?: string | null;
  payment_no?: string | null;
  paymentMethodDisplay?: string | null;
  payment_method_display?: string | null;
  transactionType: 'deposit' | 'offset' | 'refund' | 'adjustment';
  transaction_type?: 'deposit' | 'offset' | 'refund' | 'adjustment';
  transactionTypeDisplay?: string;
  transaction_type_display?: string;
  amount: number;
  balanceAfter: number;
  balance_after?: number;
  reason?: string;
  createdAt: string;
  created_at?: string;
}

/**
 * 返金申請
 */
export interface RefundRequest {
  id: string;
  requestNo: string;
  request_no?: string;
  guardian: string;
  guardianName?: string;
  guardian_name?: string;
  invoice?: string | null;
  refundAmount: number;
  refund_amount?: number;
  refundMethod: 'bank_transfer' | 'cash' | 'offset_next';
  refund_method?: 'bank_transfer' | 'cash' | 'offset_next';
  refundMethodDisplay?: string;
  refund_method_display?: string;
  reason: string;
  status: 'pending' | 'approved' | 'processing' | 'completed' | 'rejected' | 'cancelled';
  statusDisplay?: string;
  status_display?: string;
  requestedBy?: string;
  requested_by?: string;
  requestedAt: string;
  requested_at?: string;
  approvedBy?: string | null;
  approved_by?: string | null;
  approvedAt?: string | null;
  approved_at?: string | null;
  processedAt?: string | null;
  processed_at?: string | null;
  processNotes?: string;
  process_notes?: string;
}

/**
 * 相殺ログ一覧を取得
 */
export async function getOffsetLogs(params?: {
  guardian_id?: string;
  transaction_type?: string;
  page?: number;
  page_size?: number;
}): Promise<{ results: OffsetLog[]; count: number }> {
  try {
    const response = await apiClient.get<{ results: OffsetLog[]; count: number }>('/billing/offset-logs/', params);
    return response;
  } catch (error) {
    console.error("Error fetching offset logs:", error);
    return { results: [], count: 0 };
  }
}

/**
 * 返金申請一覧を取得
 */
export async function getRefundRequests(params?: {
  guardian_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<{ results: RefundRequest[]; count: number }> {
  try {
    const response = await apiClient.get<{ results: RefundRequest[]; count: number }>('/billing/refund-requests/', params);
    return response;
  } catch (error) {
    console.error("Error fetching refund requests:", error);
    return { results: [], count: 0 };
  }
}

/**
 * 返金申請を作成
 */
export async function createRefundRequest(data: {
  guardian_id: string;
  invoice_id?: string;
  refund_amount: number;
  refund_method: 'bank_transfer' | 'cash' | 'offset_next';
  reason: string;
}): Promise<RefundRequest> {
  const response = await apiClient.post<RefundRequest>('/billing/refund-requests/create_request/', data);
  return response;
}

/**
 * 返金申請を承認/却下
 */
export async function approveRefundRequest(data: {
  request_id: string;
  approve: boolean;
  reject_reason?: string;
}): Promise<RefundRequest> {
  const response = await apiClient.post<RefundRequest>('/billing/refund-requests/approve/', data);
  return response;
}

// =============================================================================
// 割引マスタ（Discount Master）
// =============================================================================

export interface DiscountMasterFilters {
  is_active?: boolean;
  discount_type?: string;
  applicable_brand?: string;
  is_employee_discount?: boolean;
  search?: string;
}

/**
 * 割引マスタ一覧を取得
 */
export async function getDiscountMasters(filters?: DiscountMasterFilters): Promise<DiscountMaster[]> {
  try {
    const params: Record<string, string | number | boolean | undefined> = {
      limit: 200,
    };
    if (filters?.is_active !== undefined) params.is_active = filters.is_active;
    if (filters?.discount_type) params.discount_type = filters.discount_type;
    if (filters?.applicable_brand) params.applicable_brand = filters.applicable_brand;
    if (filters?.is_employee_discount !== undefined) params.is_employee_discount = filters.is_employee_discount;
    if (filters?.search) params.search = filters.search;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/contracts/discounts/", params);
    return response.data || response.results || [];
  } catch (error) {
    console.error("Error fetching discount masters:", error);
    return [];
  }
}

/**
 * 割引マスタ詳細を取得
 */
export async function getDiscountMasterDetail(id: string): Promise<DiscountMaster | null> {
  try {
    return await apiClient.get<DiscountMaster>(`/contracts/discounts/${id}/`);
  } catch (error) {
    console.error("Error fetching discount master detail:", error);
    return null;
  }
}

/**
 * 有効な割引マスタ一覧を取得（選択肢用）
 */
export async function getActiveDiscountMasters(): Promise<DiscountMaster[]> {
  return getDiscountMasters({ is_active: true });
}

/**
 * 社割以外の割引マスタを取得（手動割引選択用）
 */
export async function getManualDiscountMasters(): Promise<DiscountMaster[]> {
  return getDiscountMasters({ is_active: true, is_employee_discount: false });
}

// ============================================================================
// 社員（スタッフ）管理
// ============================================================================

import type { StaffDetail, StaffFilters, StaffGroup } from "./types";

export type { StaffDetail, StaffFilters, StaffGroup };

/**
 * 社員一覧を取得
 */
export async function getStaffList(filters?: StaffFilters): Promise<PaginatedResult<StaffDetail>> {
  try {
    const params: Record<string, string | number | boolean | undefined> = {
      page: filters?.page || 1,
      page_size: filters?.page_size || 50,
    };
    if (filters?.search) params.search = filters.search;
    if (filters?.status) params.status = filters.status;
    if (filters?.brand_id) params.brand_id = filters.brand_id;
    if (filters?.school_id) params.school_id = filters.school_id;
    if (filters?.role) params.role = filters.role;
    if (filters?.department) params.department = filters.department;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/tenants/employees/", params);

    const results = response.data || response.results || [];
    const normalizedResults: StaffDetail[] = results.map((e: Record<string, unknown>) => ({
      id: e.id as string,
      employeeNo: (e.employeeNo || e.employee_no || '') as string,
      fullName: (e.fullName || e.full_name || `${e.last_name || ''} ${e.first_name || ''}`.trim()) as string,
      lastName: (e.lastName || e.last_name || '') as string,
      firstName: (e.firstName || e.first_name || '') as string,
      email: (e.email || '') as string,
      phone: (e.phone || e.phone_mobile || '') as string,
      department: (e.department || '') as string,
      positionName: (e.positionName || e.position_name || null) as string | null,
      profileImageUrl: (e.profileImageUrl || e.profile_image_url || null) as string | null,
      status: (e.status || 'active') as 'active' | 'inactive' | 'suspended',
      hireDate: (e.hireDate || e.hire_date || '') as string,
      schools: ((e.schools || e.schools_list || []) as { id: string; name: string; school_name?: string }[]).map(s => ({
        id: s.id,
        name: s.name || s.school_name || '',
      })),
      brands: ((e.brands || e.brands_list || []) as { id: string; name: string; brand_name?: string }[]).map(b => ({
        id: b.id,
        name: b.name || b.brand_name || '',
      })),
      roles: (e.roles || []) as string[],
      createdAt: (e.createdAt || e.created_at || '') as string,
      updatedAt: (e.updatedAt || e.updated_at || '') as string,
    }));

    return {
      data: normalizedResults,
      count: response.count || normalizedResults.length,
      page: Number(params.page),
      pageSize: Number(params.page_size),
      totalPages: Math.ceil((response.count || normalizedResults.length) / Number(params.page_size)),
    };
  } catch (error) {
    console.error("Error fetching staff list:", error);
    return { data: [], count: 0, page: 1, pageSize: 50, totalPages: 0 };
  }
}

/**
 * 社員詳細を取得
 */
export async function getStaffDetail(id: string): Promise<StaffDetail | null> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const e = await apiClient.get<any>(`/tenants/employees/${id}/`);
    return {
      id: e.id as string,
      employeeNo: (e.employeeNo || e.employee_no || '') as string,
      fullName: (e.fullName || e.full_name || `${e.last_name || ''} ${e.first_name || ''}`.trim()) as string,
      lastName: (e.lastName || e.last_name || '') as string,
      firstName: (e.firstName || e.first_name || '') as string,
      email: (e.email || '') as string,
      phone: (e.phone || e.phone_mobile || '') as string,
      department: (e.department || '') as string,
      positionName: (e.positionName || e.position_name || null) as string | null,
      profileImageUrl: (e.profileImageUrl || e.profile_image_url || null) as string | null,
      status: (e.status || 'active') as 'active' | 'inactive' | 'suspended',
      hireDate: (e.hireDate || e.hire_date || '') as string,
      schools: ((e.schools || e.schools_list || []) as { id: string; name: string; school_name?: string }[]).map(s => ({
        id: s.id,
        name: s.name || s.school_name || '',
      })),
      brands: ((e.brands || e.brands_list || []) as { id: string; name: string; brand_name?: string }[]).map(b => ({
        id: b.id,
        name: b.name || b.brand_name || '',
      })),
      roles: (e.roles || []) as string[],
      createdAt: (e.createdAt || e.created_at || '') as string,
      updatedAt: (e.updatedAt || e.updated_at || '') as string,
    };
  } catch (error) {
    console.error("Error fetching staff detail:", error);
    return null;
  }
}

/**
 * 社員を作成
 */
export async function createStaff(data: Partial<StaffDetail>): Promise<StaffDetail | null> {
  try {
    const payload = {
      employee_no: data.employeeNo,
      last_name: data.lastName,
      first_name: data.firstName,
      email: data.email,
      phone: data.phone,
      department: data.department,
      position_name: data.positionName,
      status: data.status || 'active',
      hire_date: data.hireDate,
      school_ids: data.schools?.map(s => s.id) || [],
      brand_ids: data.brands?.map(b => b.id) || [],
      roles: data.roles || [],
    };
    return await apiClient.post<StaffDetail>("/tenants/employees/", payload);
  } catch (error) {
    console.error("Error creating staff:", error);
    throw error;
  }
}

/**
 * 社員を更新
 */
export async function updateStaff(id: string, data: Partial<StaffDetail>): Promise<StaffDetail | null> {
  try {
    const payload: Record<string, unknown> = {};
    if (data.employeeNo !== undefined) payload.employee_no = data.employeeNo;
    if (data.lastName !== undefined) payload.last_name = data.lastName;
    if (data.firstName !== undefined) payload.first_name = data.firstName;
    if (data.email !== undefined) payload.email = data.email;
    if (data.phone !== undefined) payload.phone = data.phone;
    if (data.department !== undefined) payload.department = data.department;
    if (data.positionName !== undefined) payload.position_name = data.positionName;
    if (data.status !== undefined) payload.status = data.status;
    if (data.hireDate !== undefined) payload.hire_date = data.hireDate;
    if (data.schools !== undefined) payload.school_ids = data.schools.map(s => s.id);
    if (data.brands !== undefined) payload.brand_ids = data.brands.map(b => b.id);
    if (data.roles !== undefined) payload.roles = data.roles;

    return await apiClient.patch<StaffDetail>(`/tenants/employees/${id}/`, payload);
  } catch (error) {
    console.error("Error updating staff:", error);
    throw error;
  }
}

/**
 * 社員を削除
 */
export async function deleteStaff(id: string): Promise<boolean> {
  try {
    await apiClient.delete(`/tenants/employees/${id}/`);
    return true;
  } catch (error) {
    console.error("Error deleting staff:", error);
    return false;
  }
}

/**
 * スタッフグループ一覧を取得
 */
export async function getStaffGroups(): Promise<StaffGroup[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/tenants/employee-groups/");
    const results = response.data || response.results || response || [];
    return results.map((g: Record<string, unknown>) => ({
      id: g.id as string,
      name: (g.name || '') as string,
      description: (g.description || '') as string,
      memberCount: (g.memberCount || g.member_count || 0) as number,
      members: ((g.members || []) as StaffDetail[]),
      createdAt: (g.createdAt || g.created_at || '') as string,
    }));
  } catch {
    // API endpoint may not exist yet
    return [];
  }
}

/**
 * スタッフグループ詳細を取得
 */
export async function getStaffGroupDetail(id: string): Promise<StaffGroup | null> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const g = await apiClient.get<any>(`/tenants/employee-groups/${id}/`);
    return {
      id: g.id as string,
      name: (g.name || '') as string,
      description: (g.description || '') as string,
      memberCount: (g.memberCount || g.member_count || 0) as number,
      members: ((g.members || []) as StaffDetail[]),
      createdAt: (g.createdAt || g.created_at || '') as string,
    };
  } catch {
    // API endpoint may not exist yet
    return null;
  }
}

/**
 * スタッフグループを作成
 */
export async function createStaffGroup(data: { name: string; description?: string; memberIds: string[] }): Promise<StaffGroup | null> {
  try {
    const payload = {
      name: data.name,
      description: data.description || '',
      member_ids: data.memberIds,
    };
    return await apiClient.post<StaffGroup>("/tenants/employee-groups/", payload);
  } catch (error) {
    console.error("Error creating staff group:", error);
    throw error;
  }
}

/**
 * スタッフグループを更新
 */
export async function updateStaffGroup(id: string, data: { name?: string; description?: string; memberIds?: string[] }): Promise<StaffGroup | null> {
  try {
    const payload: Record<string, unknown> = {};
    if (data.name !== undefined) payload.name = data.name;
    if (data.description !== undefined) payload.description = data.description;
    if (data.memberIds !== undefined) payload.member_ids = data.memberIds;
    return await apiClient.patch<StaffGroup>(`/tenants/employee-groups/${id}/`, payload);
  } catch (error) {
    console.error("Error updating staff group:", error);
    throw error;
  }
}

/**
 * スタッフグループを削除
 */
export async function deleteStaffGroup(id: string): Promise<boolean> {
  try {
    await apiClient.delete(`/tenants/employee-groups/${id}/`);
    return true;
  } catch (error) {
    console.error("Error deleting staff group:", error);
    return false;
  }
}

/**
 * 役割一覧を取得
 */
export async function getRoles(): Promise<string[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/tenants/roles/");
    return (response.data || response.results || response || []).map((r: { name?: string } | string) =>
      typeof r === 'string' ? r : r.name || ''
    );
  } catch {
    // API endpoint may not exist yet
    return [];
  }
}

/**
 * 部署一覧を取得
 */
export async function getDepartments(): Promise<string[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/tenants/departments/");
    return (response.data || response.results || response || []).map((d: { name?: string } | string) =>
      typeof d === 'string' ? d : d.name || ''
    );
  } catch {
    // API endpoint may not exist yet
    return [];
  }
}

// ============================================================================
// QRコード関連
// ============================================================================

/**
 * QRコード情報型
 */
export type QRCodeInfo = {
  qr_code: string;
  student_no: string;
  student_name: string;
};

/**
 * 生徒のQRコード情報を取得
 * @param studentId - 生徒ID
 */
export async function getStudentQRCode(studentId: string): Promise<QRCodeInfo | null> {
  try {
    return await apiClient.get<QRCodeInfo>(`/students/${studentId}/qr-code/`);
  } catch {
    return null;
  }
}

/**
 * 生徒のQRコードを再発行
 * @param studentId - 生徒ID
 */
export async function regenerateStudentQRCode(studentId: string): Promise<QRCodeInfo & { message: string }> {
  return apiClient.post<QRCodeInfo & { message: string }>(`/students/${studentId}/regenerate-qr/`, {});
}

// ============================================================================
// 承認待ち社員管理
// ============================================================================

/**
 * 承認待ち社員の型定義
 */
export type PendingEmployee = {
  id: string;
  employee_no: string | null;
  last_name: string;
  first_name: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  department: string | null;
  position_name: string | null;
  hire_date: string | null;
  schools: { id: string; name: string }[];
  brands: { id: string; name: string }[];
  user_id: string | null;
  user_email: string | null;
  created_at: string | null;
};

/**
 * 承認待ち社員一覧を取得
 */
export async function getPendingEmployees(): Promise<PendingEmployee[]> {
  try {
    const response = await apiClient.get<PendingEmployee[]>("/tenants/employees/pending/");
    return response || [];
  } catch (error) {
    console.error("Error fetching pending employees:", error);
    return [];
  }
}

/**
 * 社員を承認（有効化）
 */
export async function approveEmployee(employeeId: string): Promise<{
  success: boolean;
  message: string;
  employee_id?: string;
  user_id?: string | null;
}> {
  return apiClient.post(`/tenants/employees/${employeeId}/approve/`, {});
}

/**
 * 社員登録を却下
 */
export async function rejectEmployee(employeeId: string, reason?: string): Promise<{
  success: boolean;
  message: string;
}> {
  return apiClient.post(`/tenants/employees/${employeeId}/reject/`, { reason: reason || '' });
}
