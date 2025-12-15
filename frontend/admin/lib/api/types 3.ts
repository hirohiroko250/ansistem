/**
 * Django API Type Definitions
 * Djangoのモデルに対応する型定義
 */

// ============================================================================
// 基本型
// ============================================================================

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface PaginatedResult<T> {
  data: T[];
  count: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// ============================================================================
// 校舎・ブランド
// ============================================================================

export interface Brand {
  id: string;
  // API returns camelCase
  brandCode?: string;
  brandName?: string;
  brandNameShort?: string;
  brandType?: string;
  colorPrimary?: string;
  sortOrder?: number;
  isActive?: boolean;
  schoolCount?: number;
  brandCategoryId?: string;
  // Legacy snake_case (for backwards compatibility)
  brand_code?: string;
  brand_name?: string;
  brand_name_short?: string;
  brand_color?: string;
  brand_category_id?: string;
  sort_order?: number;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
  // Computed/convenience field for UI
  name?: string;
}

export interface School {
  id: string;
  // API returns camelCase
  schoolCode?: string;
  schoolName?: string;
  schoolNameShort?: string;
  schoolType?: string;
  sortOrder?: number;
  isActive?: boolean;
  brandId?: string;
  // Legacy snake_case (for backwards compatibility)
  school_code?: string;
  school_name?: string;
  school_name_short?: string;
  prefecture?: string;
  city?: string;
  area?: string;
  address?: string;
  phone?: string;
  email?: string;
  sort_order?: number;
  is_active?: boolean;
  brand_id?: string;
  created_at?: string;
  updated_at?: string;
  // Computed/convenience field for UI
  name?: string;
}

export interface Grade {
  id: string;
  grade_code: string;
  grade_name: string;
  grade_order: number;
  is_active: boolean;
}

// ============================================================================
// 生徒・保護者
// ============================================================================

export interface Student {
  id: string;
  student_no: string;
  old_id: string;
  last_name: string;
  first_name: string;
  last_name_kana: string;
  first_name_kana: string;
  last_name_roman: string;
  first_name_roman: string;
  nickname: string;
  birth_date: string | null;
  gender: string;
  email: string;
  phone: string;
  phone2: string;
  postal_code: string;
  prefecture: string;
  city: string;
  address1: string;
  address2: string;
  school_name: string;
  grade_text: string;
  status: string;
  contract_status: string;
  primary_school: School | null;
  primary_school_id: string | null;
  guardian: Guardian | null;
  guardian_id: string | null;
  registered_date: string | null;
  created_at: string;
  updated_at: string;
  // Computed/convenience fields for UI
  full_name?: string;
  full_name_kana?: string;
  name?: string;          // Alias for full_name
  grade?: string;         // Alias for grade_text
  brand?: string;         // Brand name (from primary_school.brand)
  campus?: string;        // Campus name (from primary_school.school_name)
  brand_id?: string;      // Brand ID for filtering
  campus_id?: string;     // Alias for primary_school_id
}

export interface Guardian {
  id: string;
  guardian_no: string;
  old_id: string;
  last_name: string;
  first_name: string;
  last_name_kana: string;
  first_name_kana: string;
  last_name_roman: string;
  first_name_roman: string;
  email: string;
  phone: string;
  phone_mobile: string;
  postal_code: string;
  prefecture: string;
  city: string;
  address1: string;
  address2: string;
  workplace: string;
  workplace2: string;
  workplace_phone: string;
  workplace_phone2: string;
  nearest_school: School | null;
  nearest_school_id: string | null;
  // 口座情報
  bank_name: string;
  bank_code: string;
  branch_name: string;
  branch_code: string;
  account_type: string;
  account_number: string;
  account_holder: string;
  account_holder_kana: string;
  created_at: string;
  updated_at: string;
  // Computed/convenience fields for UI
  full_name?: string;
  full_name_kana?: string;
  name?: string;           // Alias for full_name
  relationship?: string;   // 続柄（将来的に追加予定）
  students?: Student[];
}

// ============================================================================
// 契約
// ============================================================================

export interface Contract {
  id: string;
  contract_no: string;
  old_id: string;
  student: Student | null;
  student_id: string | null;
  guardian: Guardian | null;
  guardian_id: string | null;
  school: School | null;
  school_id: string | null;
  brand: Brand | null;
  brand_id: string | null;
  contract_date: string | null;
  start_date: string | null;
  end_date: string | null;
  status: string;
  notes: string;
  created_at: string;
  updated_at: string;
  // Computed/convenience fields for UI
  contract_type?: string;  // 契約種別（将来的に追加予定）
  monthly_fee?: number;    // 月額（StudentItemから計算）
}

export interface Product {
  id: string;
  product_code: string;
  product_name: string;
  product_name_short: string;
  item_type: string;
  base_price: string;
  is_one_time: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StudentItem {
  id: string;
  old_id: string;
  student: Student | null;
  student_id: string;
  contract: Contract | null;
  contract_id: string | null;
  product: Product | null;
  product_id: string;
  brand: Brand | null;
  brand_id: string | null;
  school: School | null;
  school_id: string | null;
  billing_month: string;
  quantity: number;
  unit_price: string;
  discount_amount: string;
  final_price: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// 授業・スケジュール
// ============================================================================

export interface TimeSlot {
  id: string;
  slot_no: number;
  start_time: string;
  end_time: string;
  brand: Brand | null;
  brand_id: string | null;
  is_active: boolean;
}

export interface Staff {
  id: string;
  name: string;
  email?: string;
  role?: string;
}

export interface LessonSchedule {
  id: string;
  student: Student | null;
  student_id: string;
  school: School | null;
  school_id: string;
  date: string;
  time_slot: TimeSlot | null;
  time_slot_id: string | null;
  status: string;
  notes: string;
  created_at: string;
  updated_at: string;
  // Computed/convenience fields for UI
  scheduled_at?: string;      // Alias for date + time_slot.start_time
  subject?: string;           // 科目名（将来的に追加予定）
  duration_minutes?: number;  // 授業時間（分）
  staff?: Staff;              // 担当講師
}

export interface Attendance {
  id: string;
  schedule: LessonSchedule | null;
  schedule_id: string;
  status: string;
  check_in_time: string | null;
  check_out_time: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// コース・パック
// ============================================================================

export interface Course {
  id: string;
  course_code: string;
  course_name: string;
  brand: Brand | null;
  brand_id: string | null;
  school: School | null;
  school_id: string | null;
  grade: Grade | null;
  grade_id: string | null;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Pack {
  id: string;
  pack_code: string;
  pack_name: string;
  description: string;
  is_active: boolean;
  courses?: Course[];
  created_at: string;
  updated_at: string;
}

// ============================================================================
// ダッシュボード
// ============================================================================

export interface DashboardStats {
  total_students: number;
  active_students: number;
  inactive_students: number;
  total_guardians: number;
  total_contracts: number;
  today_lessons: number;
  pending_tasks: number;
  unread_messages: number;
}

export interface BrandStats {
  brand_id: string;
  brand_name: string;
  brand_color: string;
  student_count: number;
}

export interface SchoolStats {
  school_id: string;
  school_name: string;
  student_count: number;
}

export interface DashboardData {
  stats: DashboardStats;
  brand_stats: BrandStats[];
  school_stats: SchoolStats[];
  recent_students: Student[];
  recent_contracts: Contract[];
}

// ============================================================================
// フィルター
// ============================================================================

export interface StudentFilters {
  search?: string;
  brand_category_id?: string;
  brand_id?: string;
  school_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface ContractFilters {
  search?: string;
  student_id?: string;
  brand_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface LessonFilters {
  student_id?: string;
  school_id?: string;
  date_from?: string;
  date_to?: string;
  status?: string;
  page?: number;
  page_size?: number;
}
