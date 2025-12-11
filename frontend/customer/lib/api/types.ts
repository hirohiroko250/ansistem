/**
 * API Types - Django バックエンドのモデルに対応する型定義
 * 保護者・顧客向けの型定義
 */

// ============================================
// ユーザー関連
// ============================================

export type UserType = 'guardian' | 'student' | 'staff' | 'teacher';
export type UserRole = 'user' | 'staff' | 'admin';

export interface User {
  id: string;
  email: string;
  userType: UserType;
  role: UserRole;
  lastName: string;
  firstName: string;
  lastNameKana?: string;
  firstNameKana?: string;
  displayName?: string;
  phoneNumber?: string;
  phoneNumberSecondary?: string;
  profileImageUrl?: string;
  birthDate?: string;
  gender?: 'male' | 'female' | 'other' | 'prefer_not_to_say';
  postalCode?: string;
  prefecture?: string;
  city?: string;
  addressLine1?: string;
  addressLine2?: string;
  isActive: boolean;
  lastLoginAt?: string;
  createdAt: string;
  updatedAt: string;
  tenantId: string;
}

export interface UserSummary {
  id: string;
  email: string;
  fullName: string;
  displayName?: string;
}

export interface Profile extends User {
  fullName: string;
  fullNameKana?: string;
  // Guardian specific fields (from API)
  address1?: string;
  address2?: string;
  nearestSchoolId?: string | null;
  nearestSchoolName?: string | null;
  interestedBrands?: string[];
  referralSource?: string;
  expectations?: string;
}

// ============================================
// 認証関連
// ============================================

export interface LoginRequest {
  email?: string;
  phone?: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  fullName: string;
  fullNameKana?: string;
  phone?: string;
  // 住所
  postalCode?: string;
  prefecture?: string;
  city?: string;
  address1?: string;
  address2?: string;
  // その他
  nearestSchoolId?: string;
  interestedBrands?: string[];
  referralSource?: string;
  expectations?: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: Profile;
}

export interface RegisterResponse {
  tokens: {
    access: string;
    refresh: string;
  };
  user: Profile;
}

export interface RefreshRequest {
  refresh: string;
}

export interface RefreshResponse {
  access: string;
}

export interface LogoutRequest {
  refresh: string;
}

// ============================================
// 子ども（生徒）関連
// ============================================

export type StudentStatus = 'inquiry' | 'trial' | 'enrolled' | 'suspended' | 'withdrawn';

export interface Child {
  id: string;
  userId: string;
  studentNumber?: string;
  lastName: string;
  firstName: string;
  lastNameKana?: string;
  firstNameKana?: string;
  fullName: string;
  grade?: string;
  schoolName?: string;
  enrollmentDate?: string;
  status: StudentStatus;
  profileImageUrl?: string;
  birthDate?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChildDetail extends Child {
  tickets: TicketBalance;
  courses: CourseEnrollment[];
}

// ============================================
// チケット関連
// ============================================

export interface TicketBalance {
  studentId: string;
  studentName: string;
  totalAvailable: number;
  expiringSoon: number;
  expiringDate?: string;
}

export interface TicketLog {
  id: string;
  ticketType: 'normal' | 'makeup' | 'seminar';
  operation: 'grant' | 'consume' | 'expire' | 'cancel';
  quantity: number;
  reason?: string;
  createdAt: string;
}

// ============================================
// 料金計算関連
// ============================================

export interface PricingPreviewRequest {
  studentId: string;
  productIds: string[];
  courseId?: string;
  packId?: string;
  additionalTickets?: number;
  promoCode?: string;
}

export interface PricingItem {
  productId: string;
  productName: string;
  productType: 'tuition' | 'material' | 'misc';
  unitPrice: number;
  quantity: number;
  subtotal: number;
  taxRate: number;
  taxAmount: number;
  discountAmount: number;
  total: number;
}

export interface PricingDiscount {
  discountId: string;
  discountName: string;
  discountType: 'percentage' | 'fixed';
  discountValue: number;
  appliedAmount: number;
}

export interface PricingMile {
  mileUsed: number;
  mileDiscount: number;
  remainingMile: number;
}

export interface PricingPreviewResponse {
  items: PricingItem[];
  subtotal: number;
  taxTotal: number;
  discounts: PricingDiscount[];
  discountTotal: number;
  mile?: PricingMile;
  companyContribution: number;
  schoolContribution: number;
  grandTotal: number;
  monthlyBreakdown?: {
    firstMonth: number;
    subsequentMonths: number;
  };
}

export interface PricingCalculateRequest {
  courseId: string;
  additionalTickets?: number;
  promoCode?: string;
}

export interface PricingCalculateResponse {
  basePrice: number;
  additionalTicketPrice: number;
  discount: number;
  tax: number;
  total: number;
}

export interface PricingConfirmRequest {
  previewId: string;
  paymentMethod: 'credit_card' | 'bank_transfer' | 'convenience_store';
  useMile?: number;
  studentId?: string;
  courseId?: string;
  // 購入時に選択した情報
  brandId?: string;
  schoolId?: string;
  startDate?: string;  // YYYY-MM-DD形式
}

export interface PricingConfirmResponse {
  orderId: string;
  status: 'pending' | 'completed' | 'failed';
  paymentUrl?: string;
  message: string;
}

// ============================================
// コース・教室関連
// ============================================

export interface School {
  id: string;
  name: string;
  shortName?: string;
  description?: string;
  prefecture?: string;
  city?: string;
  addressLine1?: string;
  phoneNumber?: string;
  openingTime?: string;
  closingTime?: string;
  latitude?: number;
  longitude?: number;
}

export interface Area {
  id: string;
  name: string;
  schoolCount: number;
}

export interface PublicSchool {
  id: string;
  name: string;
  code: string;
  address: string;
  phone?: string;
  brands: string[];
}

export interface Course {
  id: string;
  schoolId: string;
  school?: School;
  name: string;
  shortName?: string;
  description?: string;
  category: string;
  targetAgeMin?: number;
  targetAgeMax?: number;
  durationMinutes?: number;
  ticketCost: number;
  monthlyFee?: number;
  isActive: boolean;
}

export interface CourseEnrollment {
  id: string;
  courseId: string;
  course: Course;
  studentId: string;
  enrolledAt: string;
  status: 'active' | 'paused' | 'cancelled';
}

// ============================================
// 予約・授業関連
// ============================================

export type ClassStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
export type ReservationStatus = 'pending' | 'confirmed' | 'attended' | 'absent' | 'cancelled';

export interface ClassSession {
  id: string;
  courseId: string;
  course: Course;
  instructorName?: string;
  schoolId: string;
  school: School;
  scheduledDate: string;
  startTime: string;
  endTime: string;
  capacity?: number;
  currentEnrollment?: number;
  status: ClassStatus;
  notes?: string;
}

export interface Reservation {
  id: string;
  studentId: string;
  childName: string;
  classSessionId: string;
  classSession: ClassSession;
  status: ReservationStatus;
  ticketUsed?: string;
  checkInAt?: string;
  checkOutAt?: string;
  notes?: string;
  createdAt: string;
}

// ============================================
// チャット関連
// ============================================

export type ChannelType = 'direct' | 'group' | 'support';

export interface Channel {
  id: string;
  channelType: ChannelType;
  name?: string;
  description?: string;
  student?: string;
  guardian?: string;
  school?: string;
  isArchived?: boolean;
  isActive?: boolean;
  memberCount?: number;
  lastMessageAt?: string;
  unreadCount: number;
  lastMessage?: {
    id: string;
    content: string;
    senderName: string;
    createdAt: string;
  };
  createdAt: string;
  updatedAt?: string;
}

export interface Message {
  id: string;
  channel: string;           // バックエンド: channel
  channelId?: string;        // 互換性用
  sender?: string;           // バックエンド: sender (UUID)
  senderId?: string;         // 互換性用
  senderName: string;        // バックエンド: sender_name -> senderName
  senderGuardian?: string;   // バックエンド: sender_guardian
  messageType: 'text' | 'image' | 'file' | 'system' | 'TEXT' | 'IMAGE' | 'FILE' | 'SYSTEM';
  content?: string;
  attachmentUrl?: string;    // バックエンド: attachment_url
  attachmentName?: string;   // バックエンド: attachment_name
  fileUrl?: string;          // 互換性用
  fileName?: string;         // 互換性用
  isRead?: boolean;
  readAt?: string;
  isEdited?: boolean;
  editedAt?: string;
  isDeleted?: boolean;
  createdAt: string;
  isBotMessage?: boolean;    // バックエンド: is_bot_message
}

export interface SendMessageRequest {
  channelId: string;
  content: string;
  messageType?: 'text' | 'image' | 'file';
}

// ============================================
// 通知関連
// ============================================

export interface Notification {
  id: string;
  notificationType: string;
  title: string;
  message: string;
  data?: Record<string, unknown>;
  isRead: boolean;
  readAt?: string;
  createdAt: string;
}

// ============================================
// 共通型
// ============================================

export interface PaginatedResponse<T> {
  // 標準DRFフォーマット
  count?: number;
  next?: string | null;
  previous?: string | null;
  results?: T[];
  // カスタムページネーションフォーマット（バックエンド標準）
  data?: T[];
  meta?: {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
  };
  links?: {
    next: string | null;
    previous: string | null;
  };
}

export interface ApiSuccessMessage {
  message: string;
}

export interface ApiError {
  message: string;
  status: number;
  errors?: Record<string, string[]>;
}

// ============================================
// 授業・スケジュール関連（Lessons）
// ============================================

export type LessonType = 'individual' | 'group' | 'online' | 'self_study';
export type LessonStatus = 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled';
export type AttendanceStatus = 'present' | 'absent' | 'late' | 'early_leave' | 'absent_notice' | 'makeup';
export type MakeupStatus = 'requested' | 'approved' | 'scheduled' | 'completed' | 'rejected' | 'cancelled' | 'expired';

export interface TimeSlot {
  id: string;
  slotCode: string;
  slotName: string;
  startTime: string;
  endTime: string;
  durationMinutes: number;
  schoolId?: string;
  dayOfWeek?: number;
  sortOrder: number;
  isActive: boolean;
}

export interface LessonSchedule {
  id: string;
  schoolId: string;
  schoolName?: string;
  classroomId?: string;
  classroomName?: string;
  subjectId: string;
  subjectName?: string;
  lessonType: LessonType;
  date: string;
  timeSlotId?: string;
  timeSlotName?: string;
  startTime: string;
  endTime: string;
  teacherId?: string;
  teacherName?: string;
  studentId?: string;
  studentName?: string;
  className?: string;
  capacity?: number;
  status: LessonStatus;
  notes?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface LessonRecord {
  id: string;
  scheduleId: string;
  scheduleInfo?: {
    date: string;
    subject?: string;
    student?: string;
    teacher?: string;
  };
  actualStartTime?: string;
  actualEndTime?: string;
  actualDurationMinutes?: number;
  content?: string;
  homework?: string;
  nextLessonPlan?: string;
  understandingLevel?: 'excellent' | 'good' | 'average' | 'below_average' | 'poor';
  attitudeEvaluation?: 'excellent' | 'good' | 'average' | 'below_average' | 'poor';
  homeworkStatus?: 'excellent' | 'good' | 'average' | 'below_average' | 'poor';
  teacherComment?: string;
  recordedAt?: string;
}

export interface Attendance {
  id: string;
  scheduleId: string;
  studentId: string;
  studentName?: string;
  status: AttendanceStatus;
  checkInTime?: string;
  checkOutTime?: string;
  absenceReason?: string;
  absenceNotifiedAt?: string;
  notes?: string;
}

export interface MakeupRequest {
  originalScheduleId: string;
  studentId: string;
  preferredDate?: string;
  preferredTimeSlotId?: string;
  reason?: string;
}

export interface MakeupResponse {
  id: string;
  originalScheduleId: string;
  originalScheduleInfo?: {
    date: string;
    startTime: string;
    endTime: string;
    subject?: string;
  };
  studentId: string;
  studentName?: string;
  makeupScheduleId?: string;
  makeupScheduleInfo?: {
    date: string;
    startTime: string;
    endTime: string;
    subject?: string;
  };
  preferredDate?: string;
  preferredTimeSlotId?: string;
  status: MakeupStatus;
  validUntil?: string;
  requestedAt: string;
  requestedBy?: string;
  processedAt?: string;
  processedBy?: string;
  reason?: string;
  notes?: string;
}

export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  type: string;
  status: string;
  color?: string;
  resourceId?: string;
  classScheduleId?: string;
  brandName?: string;
  className?: string;
  isNativeDay?: boolean;
  holidayName?: string;
  noticeMessage?: string;
}

// スケジュール取得パラメータ
export interface ScheduleParams {
  studentId?: string;
  schoolId?: string;
  teacherId?: string;
  dateFrom?: string;
  dateTo?: string;
  status?: LessonStatus;
  lessonType?: LessonType;
  page?: number;
  pageSize?: number;
}

// 出欠取得パラメータ
export interface AttendanceParams {
  studentId?: string;
  scheduleId?: string;
  status?: AttendanceStatus;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
}

// 振替可能日
export interface MakeupAvailableDate {
  date: string;
  dayOfWeek: string;
  timeSlots: TimeSlot[];
  availableCapacity: number;
}

// 欠席登録リクエスト
export interface MarkAbsentRequest {
  absenceReason?: string;
  requestMakeup?: boolean;
}

// ============================================
// 公開API用（コース・パック購入）
// ============================================

export interface PublicBrandCategory {
  id: string;
  categoryCode: string;
  categoryName: string;
  categoryNameShort?: string;
  colorPrimary?: string;
  sortOrder: number;
}

export interface PublicBrand {
  id: string;
  brandCode: string;
  brandName: string;
  brandNameShort?: string;
  brandType?: string;
  description?: string;
  logoUrl?: string;
  colorPrimary?: string;
  colorSecondary?: string;
  category?: PublicBrandCategory;
}

export interface PublicCourseItem {
  productId: string;
  productName: string;
  productType: string;
  quantity: number;
  price: number;
}

export interface PublicCourse {
  id: string;
  courseCode: string;
  courseName: string;
  description?: string;
  price: number;
  isMonthly: boolean;
  brandId?: string;
  brandName?: string;
  brandCode?: string;
  schoolId?: string;
  schoolName?: string;
  gradeName?: string;
  items?: PublicCourseItem[];
  ticketId?: string;
  ticketCode?: string;
  ticketName?: string;
}

export interface PublicPackCourse {
  courseId: string;
  courseName: string;
  courseCode: string;
  coursePrice: number;
}

export interface PublicPackTicket {
  ticketId: string;
  ticketName: string;
  ticketCode: string;
  quantity: number;
  perWeek: number;
}

export interface PublicPack {
  id: string;
  packCode: string;
  packName: string;
  description?: string;
  price: number;
  discountType: string;
  discountValue: number;
  brandId?: string;
  brandName?: string;
  brandCode?: string;
  schoolId?: string;
  schoolName?: string;
  gradeName?: string;
  courses?: PublicPackCourse[];
  tickets?: PublicPackTicket[];
}
