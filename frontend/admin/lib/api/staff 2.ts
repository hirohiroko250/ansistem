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
  Course,
  LessonSchedule,
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
  School as Campus,
  Student,
  Guardian as Parent,
  Contract,
  LessonSchedule as Lesson,
  PaginatedResult,
  StudentFilters,
};

// Legacy type aliases
export type Staff = {
  id: string;
  name: string;
  email: string;
  role: string;
  created_at: string;
};

export type Task = {
  id: string;
  title: string;
  description: string;
  task_type: string;
  status: string;
  priority: string;
  assigned_staff_id: string;
  related_student_id: string | null;
  due_date: string;
  created_at: string;
  student?: Student;
  staff?: Staff;
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
// ブランド・校舎
// ============================================================================

export async function getBrands(): Promise<Brand[]> {
  try {
    const response = await apiClient.get<PaginatedResponse<Brand> | Brand[]>("/schools/brands/");
    // Handle both paginated and non-paginated responses
    if (Array.isArray(response)) {
      return response;
    }
    return response.results || [];
  } catch (error) {
    console.error("Error fetching brands:", error);
    return [];
  }
}

export async function getCampuses(brandId?: string): Promise<School[]> {
  try {
    const params: Record<string, string | undefined> = {};
    if (brandId) {
      params.brand_id = brandId;
    }
    const response = await apiClient.get<PaginatedResponse<School> | School[]>("/schools/schools/", params);
    if (Array.isArray(response)) {
      return response;
    }
    return response.results || [];
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
    if (filters?.brand_id) {
      params.brand_id = filters.brand_id;
    }
    if (filters?.school_id) {
      params.primary_school_id = filters.school_id;
    }
    if (filters?.status) {
      params.status = filters.status;
    }

    const response = await apiClient.get<PaginatedResponse<Student>>("/students/", params);

    return {
      data: response.results || [],
      count: response.count || 0,
      page,
      pageSize,
      totalPages: Math.ceil((response.count || 0) / pageSize),
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
    // Get student detail which includes guardian
    const student = await getStudentDetail(studentId);
    if (student?.guardian) {
      return [student.guardian];
    }
    // Or query guardians directly if needed
    const response = await apiClient.get<PaginatedResponse<Guardian>>("/students/guardians/", {
      student_id: studentId,
    });
    return response.results || [];
  } catch (error) {
    console.error("Error fetching student parents:", error);
    return [];
  }
}

// ============================================================================
// 保護者
// ============================================================================

export async function getParents(): Promise<Guardian[]> {
  try {
    const response = await apiClient.get<PaginatedResponse<Guardian>>("/students/guardians/", {
      page_size: 100,
    });
    return response.results || [];
  } catch (error) {
    console.error("Error fetching parents:", error);
    return [];
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

export async function getContracts(): Promise<Contract[]> {
  try {
    const response = await apiClient.get<PaginatedResponse<Contract>>("/contracts/", {
      page_size: 100,
    });
    return response.results || [];
  } catch (error) {
    console.error("Error fetching contracts:", error);
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
// タスク（仮実装 - 必要に応じてDjango側にエンドポイント追加）
// ============================================================================

export async function getTasks(): Promise<Task[]> {
  // TODO: Implement when Django task endpoint is available
  console.warn("getTasks: Not implemented yet");
  return [];
}

export async function getTaskDetail(id: string): Promise<Task | null> {
  // TODO: Implement when Django task endpoint is available
  console.warn("getTaskDetail: Not implemented yet");
  return null;
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
      brandName: brand.brand_name,
      studentCount: 0, // Would need aggregation endpoint
      color: brand.brand_color || "#3B82F6",
    }));

    const campusStats = schoolsData.slice(0, 10).map((school) => ({
      campusId: school.id,
      campusName: school.school_name,
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
