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
  student_name?: string;
  guardian?: string;
  guardian_name?: string;
  assigned_to_id?: string;
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

export async function getStudentInvoices(studentId: string): Promise<Invoice[]> {
  try {
    // まず生徒情報から保護者IDを取得
    const student = await getStudentDetail(studentId);
    const guardianId = student?.guardianId || student?.guardian_id || student?.guardian?.id;

    if (!guardianId) {
      return [];
    }

    // 保護者IDで請求を検索
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const response = await apiClient.get<any>("/billing/invoices/", {
      guardian_id: guardianId,
      page_size: 100,
    });
    return response.data || response.results || [];
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
 * 引落データCSVエクスポート
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
      queryParams.billing_year = params.billing_year;
      queryParams.billing_month = params.billing_month;
    }

    if (params.provider) {
      queryParams.provider = params.provider;
    }
    const blob = await apiClient.getBlob("/billing/invoices/export-debit/", queryParams);
    return blob;
  } catch (error) {
    console.error("Error exporting direct debit CSV:", error);
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
