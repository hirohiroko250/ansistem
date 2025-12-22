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
  // snake_case fields (from Django)
  student_no?: string;
  old_id?: string;
  last_name?: string;
  first_name?: string;
  last_name_kana?: string;
  first_name_kana?: string;
  last_name_roman?: string;
  first_name_roman?: string;
  birth_date?: string | null;
  postal_code?: string;
  school_name?: string;
  grade_text?: string;
  contract_status?: string;
  primary_school?: School | null;
  primary_school_id?: string | null;
  guardian_id?: string | null;
  registered_date?: string | null;
  created_at?: string;
  updated_at?: string;
  full_name?: string;
  full_name_kana?: string;
  // camelCase fields (from Django REST framework with camelCase renderer)
  studentNo?: string;
  oldId?: string;
  lastName?: string;
  firstName?: string;
  lastNameKana?: string;
  firstNameKana?: string;
  lastNameRoman?: string;
  firstNameRoman?: string;
  birthDate?: string | null;
  postalCode?: string;
  schoolName?: string;
  gradeText?: string;
  gradeName?: string;
  contractStatus?: string;
  primarySchool?: School | null;
  primarySchoolId?: string | null;
  guardianId?: string | null;
  registeredDate?: string | null;
  createdAt?: string;
  updatedAt?: string;
  fullName?: string;
  fullNameKana?: string;
  // Common fields (both cases)
  nickname?: string;
  gender?: string;
  email?: string;
  phone?: string;
  phone2?: string;
  prefecture?: string;
  city?: string;
  address1?: string;
  address2?: string;
  status: string;
  guardian?: Guardian | null;
  // Computed/convenience fields for UI
  name?: string;
  grade?: string;
  brand?: string;
  campus?: string;
  brand_id?: string;
  campus_id?: string;
}

export interface Guardian {
  id: string;
  // snake_case fields
  guardian_no?: string;
  old_id?: string;
  last_name?: string;
  first_name?: string;
  last_name_kana?: string;
  first_name_kana?: string;
  last_name_roman?: string;
  first_name_roman?: string;
  phone_mobile?: string;
  postal_code?: string;
  nearest_school?: School | null;
  nearest_school_id?: string | null;
  bank_name?: string;
  bank_code?: string;
  branch_name?: string;
  branch_code?: string;
  account_type?: string;
  account_number?: string;
  account_holder?: string;
  account_holder_kana?: string;
  created_at?: string;
  updated_at?: string;
  full_name?: string;
  full_name_kana?: string;
  student_count?: number;
  student_names?: string[];
  // camelCase fields
  guardianNo?: string;
  oldId?: string;
  lastName?: string;
  firstName?: string;
  lastNameKana?: string;
  firstNameKana?: string;
  lastNameRoman?: string;
  firstNameRoman?: string;
  phoneMobile?: string;
  postalCode?: string;
  nearestSchool?: School | null;
  nearestSchoolId?: string | null;
  bankName?: string;
  bankCode?: string;
  branchName?: string;
  branchCode?: string;
  accountType?: string;
  accountNumber?: string;
  accountHolder?: string;
  accountHolderKana?: string;
  createdAt?: string;
  updatedAt?: string;
  fullName?: string;
  fullNameKana?: string;
  studentCount?: number;
  studentNames?: string[];
  // Common fields
  email?: string;
  phone?: string;
  prefecture?: string;
  city?: string;
  address1?: string;
  address2?: string;
  workplace?: string;
  workplace2?: string;
  workplace_phone?: string;
  workplace_phone2?: string;
  // Account status
  has_account?: boolean;
  hasAccount?: boolean;
  // Payment registration
  payment_registered?: boolean;
  paymentRegistered?: boolean;
  payment_registered_at?: string | null;
  paymentRegisteredAt?: string | null;
  // Computed/convenience fields for UI
  name?: string;
  relationship?: string;
  students?: Student[];
}

// ============================================================================
// 契約
// ============================================================================

export interface Contract {
  id: string;
  contract_no: string;
  contractNo?: string;  // camelCase alias
  old_id: string;
  student: Student | null;
  student_id: string | null;
  guardian: Guardian | null;
  guardian_id: string | null;
  school: School | null;
  school_id: string | null;
  school_name?: string;
  schoolName?: string;
  brand: Brand | null;
  brand_id: string | null;
  brand_name?: string;
  brandName?: string;
  course?: { id: string; course_name?: string; courseName?: string } | null;
  course_id?: string | null;
  course_name?: string;
  courseName?: string;
  contract_date: string | null;
  start_date: string | null;
  startDate?: string | null;
  end_date: string | null;
  endDate?: string | null;
  status: string;
  notes: string;
  created_at: string;
  updated_at: string;
  // 金額・割引
  monthly_total?: number | string;
  monthlyTotal?: number | string;
  discount_applied?: number | string;
  discountApplied?: number | string;
  discount_type?: string;
  discountType?: string;
  // スケジュール
  day_of_week?: number;
  dayOfWeek?: number;
  start_time?: string;
  startTime?: string;
  // 料金内訳（StudentItem）
  student_items?: StudentItem[];
  studentItems?: StudentItem[];
  // 割引情報
  discounts?: StudentDiscount[];
  discount_total?: number | string;
  discountTotal?: number | string;
  discount_max?: number | string;
  discountMax?: number | string;
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
  old_id?: string;
  student?: Student | null;
  student_id?: string;
  student_name?: string;
  student_no?: string;
  studentName?: string;
  contract?: Contract | null;
  contract_id?: string | null;
  product?: Product | null;
  product_id?: string;
  product_name?: string;
  product_code?: string;
  productName?: string;
  brand?: Brand | null;
  brand_id?: string | null;
  brand_name?: string;
  school?: School | null;
  school_id?: string | null;
  school_name?: string;
  course?: Course | null;
  course_id?: string | null;
  course_name?: string;
  start_date?: string;
  day_of_week?: number;
  start_time?: string;
  end_time?: string;
  billing_month?: string;
  billingMonth?: string;
  quantity?: number;
  unit_price?: string | number;
  unitPrice?: string | number;
  discount_amount?: string | number;
  discountAmount?: string | number;
  final_price?: string | number;
  finalPrice?: string | number;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface StudentDiscount {
  id: string;
  old_id?: string;
  // 対象
  student?: string | Student | null;
  student_id?: string | null;
  student_name?: string;
  student_no?: string;
  guardian?: string | Guardian | null;
  guardian_id?: string | null;
  guardian_name?: string;
  contract?: string | Contract | null;
  contract_id?: string | null;
  // Item-level discount support
  student_item?: string | null;
  student_item_id?: string | null;
  studentItemId?: string | null;
  product_name?: string;
  productName?: string;
  // Brand
  brand?: string | Brand | null;
  brand_id?: string | null;
  brand_name?: string;
  brandName?: string;
  // 割引情報
  discount_name?: string;
  discountName?: string;
  amount?: number | string;
  discount_unit?: string;
  discount_unit_display?: string;
  discountUnit?: string;
  // 適用期間
  start_date?: string;
  startDate?: string;
  end_date?: string;
  endDate?: string;
  // 繰り返し・自動適用
  is_recurring?: boolean;
  isRecurring?: boolean;
  is_auto?: boolean;
  isAuto?: boolean;
  end_condition?: string;
  end_condition_display?: string;
  endCondition?: string;
  is_active?: boolean;
  isActive?: boolean;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

// ============================================================================
// 請求
// ============================================================================

export interface Invoice {
  id: string;
  invoiceNo?: string;
  invoice_no?: string;
  guardian?: Guardian | null;
  guardianId?: string;
  guardian_id?: string;
  student?: Student | null;
  studentId?: string;
  student_id?: string;
  // 請求年月
  billingYear?: number;
  billing_year?: number;
  billingMonth?: number | string;
  billing_month?: number | string;
  // 金額
  totalAmount?: string | number;
  total_amount?: string | number;
  paidAmount?: string | number;
  paid_amount?: string | number;
  balanceDue?: string | number;
  balance_due?: string | number;
  balance?: string | number;
  carryOverAmount?: string | number;
  carry_over_amount?: string | number;
  status?: string;
  confirmed_at?: string;
  paid_at?: string;
  dueDate?: string;
  due_date?: string;
  paidDate?: string;
  paid_date?: string;
  // 支払方法
  paymentMethod?: string;
  payment_method?: string;
  // 預り金残高
  guardianBalance?: number;
  guardian_balance?: number;
  // 詳細情報
  description?: string;
  courseName?: string;
  course_name?: string;
  brandName?: string;
  brand_name?: string;
  // メモ
  notes?: string;
  createdAt?: string;
  created_at?: string;
  updatedAt?: string;
  updated_at?: string;
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

// ============================================================================
// 請求確定
// ============================================================================

export interface ConfirmedBilling {
  id: string;
  student: string;
  student_name: string;
  student_no?: string;
  guardian: string;
  guardian_name: string;
  guardian_no?: string;
  year: number;
  month: number;
  billing_deadline?: string;
  subtotal: number;
  discount_total: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  balance: number;
  items_snapshot: ConfirmedBillingItem[];
  discounts_snapshot: ConfirmedBillingDiscount[];
  status: 'confirmed' | 'unpaid' | 'partial' | 'paid' | 'cancelled';
  status_display: string;
  payment_method: 'direct_debit' | 'bank_transfer' | 'cash' | 'other';
  payment_method_display: string;
  confirmed_at: string;
  confirmed_by?: string;
  confirmed_by_name?: string;
  paid_at?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ConfirmedBillingItem {
  id: string;
  product_name?: string;
  course_name?: string;
  brand_name?: string;
  quantity: number;
  unit_price: string;
  discount_amount: string;
  final_price: string;
  notes?: string;
}

export interface ConfirmedBillingDiscount {
  id: string;
  discount_name: string;
  amount: string;
  discount_unit: string;
}

export interface ConfirmedBillingSummary {
  year: number;
  month: number;
  total_count: number;
  total_amount: number;
  total_paid: number;
  total_balance: number;
  collection_rate: number;
  status_counts: {
    [key: string]: {
      label: string;
      count: number;
    };
  };
  payment_method_counts: {
    [key: string]: {
      label: string;
      count: number;
      amount: number;
    };
  };
}

export interface ConfirmedBillingFilters {
  year?: number;
  month?: number;
  status?: string;
  guardian_id?: string;
  student_id?: string;
  page?: number;
  page_size?: number;
}
