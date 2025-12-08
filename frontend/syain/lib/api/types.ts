/**
 * API Types - Django バックエンドのモデルに対応する型定義
 * 社員・講師向けの型定義
 */

// ============================================
// ユーザー関連
// ============================================

export type UserType = 'staff' | 'instructor' | 'guardian' | 'student';
export type UserRole = 'admin' | 'manager' | 'staff' | 'user';

export interface User {
  id: string;
  email: string;
  user_type: UserType;
  role: UserRole;
  last_name: string;
  first_name: string;
  last_name_kana?: string;
  first_name_kana?: string;
  display_name?: string;
  phone_number?: string;
  phone_number_secondary?: string;
  profile_image_url?: string;
  birth_date?: string;
  gender?: 'male' | 'female' | 'other' | 'prefer_not_to_say';
  postal_code?: string;
  prefecture?: string;
  city?: string;
  address_line1?: string;
  address_line2?: string;
  is_active: boolean;
  last_login_at?: string;
  password_changed_at?: string;
  created_at: string;
  updated_at: string;
  tenant_id: string;
}

export interface UserSummary {
  id: string;
  email: string;
  user_type: UserType;
  role: UserRole;
  full_name: string;
  display_name?: string;
  is_active: boolean;
}

export interface Profile extends User {
  full_name: string;
  full_name_kana?: string;
}

// ============================================
// 認証関連
// ============================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: Profile;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
}

// ============================================
// 生徒関連
// ============================================

export type StudentStatus = 'inquiry' | 'trial' | 'enrolled' | 'suspended' | 'withdrawn';

export interface Student {
  id: string;
  user_id: string;
  user: UserSummary;
  student_number?: string;
  grade?: string;
  school_name?: string;
  enrollment_date?: string;
  withdrawal_date?: string;
  status: StudentStatus;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface StudentDetail extends Student {
  guardians: StudentGuardian[];
  tickets: TicketBalance;
}

export interface StudentGuardian {
  id: string;
  student_id: string;
  guardian_id: string;
  guardian: UserSummary;
  relationship: string;
  is_primary: boolean;
  is_emergency_contact: boolean;
  is_billing_target: boolean;
}

// ============================================
// 講師関連
// ============================================

export type InstructorStatus = 'active' | 'inactive' | 'on_leave' | 'terminated';

export interface Instructor {
  id: string;
  user_id: string;
  user: UserSummary;
  instructor_number?: string;
  specialties?: string[];
  bio?: string;
  hire_date?: string;
  status: InstructorStatus;
  hourly_rate?: string;
  is_featured: boolean;
  max_students_per_class?: number;
  created_at: string;
  updated_at: string;
}

// ============================================
// 教室・コース関連
// ============================================

export interface School {
  id: string;
  name: string;
  short_name?: string;
  school_code?: string;
  description?: string;
  postal_code?: string;
  prefecture?: string;
  city?: string;
  address_line1?: string;
  address_line2?: string;
  latitude?: number;
  longitude?: number;
  phone_number?: string;
  email?: string;
  capacity?: number;
  opening_time?: string;
  closing_time?: string;
  is_active: boolean;
}

export interface Course {
  id: string;
  school_id: string;
  school?: School;
  name: string;
  short_name?: string;
  course_code?: string;
  description?: string;
  category: string;
  target_age_min?: number;
  target_age_max?: number;
  capacity_per_class?: number;
  duration_minutes?: number;
  ticket_cost: number;
  monthly_fee?: string;
  is_active: boolean;
}

export type ClassStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

export interface ClassSession {
  id: string;
  course_id: string;
  course: Course;
  instructor_id?: string;
  instructor?: UserSummary;
  school_id: string;
  school: School;
  scheduled_date: string;
  start_time: string;
  end_time: string;
  capacity?: number;
  current_enrollment?: number;
  status: ClassStatus;
  notes?: string;
  created_at: string;
}

// ============================================
// 予約・出席関連
// ============================================

export type ReservationStatus = 'pending' | 'confirmed' | 'attended' | 'absent' | 'cancelled';

export interface Reservation {
  id: string;
  student_id: string;
  student: Student;
  class_session_id: string;
  class_session: ClassSession;
  booked_by_id: string;
  booked_by: UserSummary;
  status: ReservationStatus;
  ticket_used?: string;
  check_in_at?: string;
  check_out_at?: string;
  notes?: string;
  created_at: string;
}

export interface Attendance {
  id: string;
  class_session_id: string;
  student_id: string;
  student: Student;
  status: 'present' | 'absent' | 'late' | 'excused';
  check_in_time?: string;
  check_out_time?: string;
  instructor_notes?: string;
  performance_rating?: number;
}

// ============================================
// チケット関連
// ============================================

export interface TicketBalance {
  student_id: string;
  student_name: string;
  total_available: number;
  expiring_soon: number;
  expiring_date?: string;
}

// ============================================
// フィード関連
// ============================================

export type FeedVisibility = 'public' | 'school' | 'grade' | 'staff';

export interface FeedPost {
  id: string;
  author_id: string;
  author: UserSummary;
  school_id?: string;
  school?: School;
  title?: string;
  content: string;
  visibility: FeedVisibility;
  target_grades?: string[];
  is_pinned: boolean;
  likes_count: number;
  comments_count: number;
  is_liked: boolean;
  is_bookmarked: boolean;
  media: FeedMedia[];
  created_at: string;
  updated_at: string;
}

export interface FeedMedia {
  id: string;
  media_type: 'image' | 'video';
  file_url: string;
  thumbnail_url?: string;
  order: number;
}

export interface CreateFeedPostRequest {
  title?: string;
  content: string;
  visibility: FeedVisibility;
  school_id?: string;
  target_grades?: string[];
}

// ============================================
// チャット・メッセージ関連
// ============================================

export type ChannelType = 'direct' | 'group' | 'support' | 'announcement';

export interface Channel {
  id: string;
  channel_type: ChannelType;
  name?: string;
  description?: string;
  is_active: boolean;
  last_message_at?: string;
  unread_count: number;
  participants: ChannelParticipant[];
  last_message?: Message;
  created_at: string;
}

export interface ChannelParticipant {
  id: string;
  user_id: string;
  user: UserSummary;
  is_admin: boolean;
  joined_at: string;
  last_read_at?: string;
}

export interface Message {
  id: string;
  channel_id: string;
  sender_id: string;
  sender: UserSummary;
  message_type: 'text' | 'image' | 'file' | 'system';
  content?: string;
  file_url?: string;
  file_name?: string;
  is_read: boolean;
  read_at?: string;
  created_at: string;
}

// ============================================
// 通知関連
// ============================================

export interface Notification {
  id: string;
  notification_type: string;
  title: string;
  message: string;
  data?: Record<string, unknown>;
  is_read: boolean;
  read_at?: string;
  created_at: string;
}

// ============================================
// CRM関連
// ============================================

export interface ContactLog {
  id: string;
  contact_type: 'phone' | 'email' | 'chat' | 'visit' | 'other';
  direction: 'inbound' | 'outbound';
  guardian_id?: string;
  guardian?: UserSummary;
  student_id?: string;
  student?: Student;
  handled_by_id: string;
  handled_by: UserSummary;
  subject?: string;
  content: string;
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  contacted_at: string;
  resolved_at?: string;
  follow_up_date?: string;
  tags?: string[];
  created_at: string;
}

// ============================================
// 共通型
// ============================================

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiSuccessMessage {
  message: string;
}
