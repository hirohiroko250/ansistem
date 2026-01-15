/**
 * Schools API
 * 校舎・地域関連のAPI関数（保護者・顧客向け）
 */

import api from './client';
import type { Area, PublicSchool } from './types';

/**
 * 公開地域（市区町村）一覧を取得
 * 認証不要
 * @param prefecture - 都道府県でフィルタリング（オプション）
 */
export async function getAreas(prefecture?: string): Promise<Area[]> {
  const params = prefecture ? `?prefecture=${encodeURIComponent(prefecture)}` : '';
  return api.get<Area[]>(`/schools/public/areas/${params}`, { skipAuth: true });
}

/**
 * 地域別校舎一覧を取得
 * 認証不要
 * @param city - 市区町村名
 */
export async function getSchoolsByArea(city: string): Promise<PublicSchool[]> {
  return api.get<PublicSchool[]>(
    `/schools/public/schools-by-area/?city=${encodeURIComponent(city)}`,
    { skipAuth: true }
  );
}

/**
 * 都道府県一覧を取得
 * 愛知県・岐阜県のみ（固定値）
 */
export async function getPrefectures(): Promise<string[]> {
  // 愛知県・岐阜県のみ対象
  return Promise.resolve(['愛知県', '岐阜県']);
}

/**
 * 公開校舎一覧を取得
 * 認証不要
 * @param params - フィルタパラメータ
 */
export async function getPublicSchools(params?: {
  prefecture?: string;
  city?: string;
}): Promise<PublicSchool[]> {
  const searchParams = new URLSearchParams();
  if (params?.prefecture) searchParams.append('prefecture', params.prefecture);
  if (params?.city) searchParams.append('city', params.city);

  const query = searchParams.toString();
  return api.get<PublicSchool[]>(
    `/schools/public/schools/${query ? `?${query}` : ''}`,
    { skipAuth: true }
  );
}

/**
 * ブランドカテゴリ内のブランド
 */
export interface CategoryBrand {
  id: string;
  brandCode: string;
  brandName: string;
  brandNameShort: string;
  brandType: string;
  logoUrl: string;
  colorPrimary: string;
}

/**
 * ブランドカテゴリ
 */
export interface BrandCategory {
  id: string;
  categoryCode: string;
  categoryName: string;
  categoryNameShort: string;
  logoUrl: string;
  colorPrimary: string;
  sortOrder: number;
  brands: CategoryBrand[];
}

/**
 * ブランドカテゴリ一覧を取得
 * 認証不要
 */
export async function getBrandCategories(): Promise<BrandCategory[]> {
  const response = await api.get<{ data: BrandCategory[]; count: number }>(
    `/schools/public/brand-categories/`,
    { skipAuth: true }
  );
  return response.data || [];
}

/**
 * ブランドの開講校舎一覧（緯度・経度付き）
 */
export interface BrandSchool {
  id: string;
  name: string;
  code: string;
  address: string;
  phone: string;
  latitude: number | null;
  longitude: number | null;
  isMain: boolean;
  sortOrder: number;
}

/**
 * ブランドの開講校舎一覧を取得
 * 認証不要
 * @param brandId - ブランドIDまたはブランドコード
 */
export async function getBrandSchools(brandId: string): Promise<BrandSchool[]> {
  const response = await api.get<{ data: BrandSchool[]; count: number }>(
    `/schools/public/brands/${brandId}/schools/`,
    { skipAuth: true }
  );
  return response.data || [];
}

/**
 * 開講カレンダー（日別情報）
 */
export interface LessonCalendarDay {
  date: string;
  dayOfWeek: string;
  isOpen: boolean;
  lessonType: 'A' | 'B' | 'closed';
  displayLabel: string;
  ticketType: string;
  ticketSequence: number | null;
  noticeMessage: string;
  holidayName: string;
  isNativeDay: boolean;  // 外国人講師あり
  isJapaneseOnly: boolean;  // 日本人講師のみ
}

export interface LessonCalendarResponse {
  brandId: string;
  schoolId: string;
  year: number;
  month: number;
  calendarCode?: string;
  calendar: LessonCalendarDay[];
}

/**
 * 開講カレンダーを取得
 * 認証不要
 * @param brandId - ブランドID
 * @param schoolId - 校舎ID
 * @param year - 年
 * @param month - 月
 */
export async function getLessonCalendar(
  brandId: string,
  schoolId: string,
  year: number,
  month: number
): Promise<LessonCalendarResponse> {
  return api.get<LessonCalendarResponse>(
    `/schools/public/lesson-calendar/?brand_id=${brandId}&school_id=${schoolId}&year=${year}&month=${month}`,
    { skipAuth: true }
  );
}

/**
 * 開講時間割のスケジュール詳細
 */
export interface ClassScheduleItem {
  id: string;
  scheduleCode: string;
  className: string;
  classType: string;
  displayCourseName: string;
  displayPairName: string;
  displayDescription: string;
  period: number;
  startTime: string;
  endTime: string;
  durationMinutes: number;
  capacity: number;
  trialCapacity: number;
  reservedSeats: number;
  availableSeats: number;
  transferGroup: string;
  calendarPattern: string;
  approvalType: number;
  roomName: string;
  brandId: string | null;
  brandName: string | null;
  brandCategoryId: string | null;
  brandCategoryName: string | null;
  ticketName: string;
  ticketId: string;
  gradeCode?: string;
  gradeName?: string;
  sortOrder?: number;
}

/**
 * 曜日ごとの開講状況
 */
export interface DayAvailability {
  status: 'none' | 'available' | 'few' | 'full';
  totalCapacity?: number;
  totalReserved?: number;
  availableSeats?: number;
  schedules: ClassScheduleItem[];
}

/**
 * 時間帯ごとの開講情報
 */
export interface TimeSlotSchedule {
  time: string;
  days: {
    [key: string]: DayAvailability;  // '月', '火', '水', '木', '金', '土', '日'
  };
}

/**
 * 開講時間割レスポンス
 */
export interface ClassScheduleResponse {
  schoolId: string;
  brandId: string | null;
  brandCategoryId: string | null;
  timeSlots: TimeSlotSchedule[];
  dayLabels: string[];
}

/**
 * 開講時間割を取得
 * 認証不要
 * @param schoolId - 校舎ID
 * @param brandId - ブランドID（オプション）
 * @param brandCategoryId - ブランドカテゴリID（オプション）
 */
export async function getClassSchedules(
  schoolId: string,
  brandId?: string,
  brandCategoryId?: string,
  ticketId?: string
): Promise<ClassScheduleResponse> {
  const params = new URLSearchParams({ school_id: schoolId });
  if (brandId) params.append('brand_id', brandId);
  if (brandCategoryId) params.append('brand_category_id', brandCategoryId);
  if (ticketId) params.append('ticket_id', ticketId);

  return api.get<ClassScheduleResponse>(
    `/schools/public/class-schedules/?${params.toString()}`,
    { skipAuth: true }
  );
}

/**
 * チケットが開講している校舎一覧を取得
 * @param ticketId - チケットID（例: Ti10000063）
 * @param brandId - ブランドID（オプション）
 */
export async function getSchoolsByTicket(
  ticketId: string,
  brandId?: string
): Promise<BrandSchool[]> {
  const params = new URLSearchParams({ ticket_id: ticketId });
  if (brandId) params.append('brand_id', brandId);

  return api.get<BrandSchool[]>(
    `/schools/public/schools-by-ticket/?${params.toString()}`,
    { skipAuth: true }
  );
}

/**
 * 校舎で開講しているチケット一覧を取得
 * @param schoolId - 校舎ID
 */
export async function getTicketsBySchool(
  schoolId: string
): Promise<{ schoolId: string; ticketIds: string[] }> {
  const params = new URLSearchParams({ school_id: schoolId });

  return api.get<{ schoolId: string; ticketIds: string[] }>(
    `/schools/public/tickets-by-school/?${params.toString()}`,
    { skipAuth: true }
  );
}

/**
 * 日ごとの座席状況
 */
export interface DailySeatInfo {
  date: string;
  dayOfWeek: number;
  isOpen: boolean;
  totalCapacity: number;
  enrolledCount: number;
  availableSeats: number;
  lessonType: string | null;
  ticketType: string | null;
  holidayName: string | null;
}

/**
 * 月間座席状況レスポンス
 */
export interface CalendarSeatsResponse {
  year: number;
  month: number;
  schoolId: string;
  brandId: string;
  days: DailySeatInfo[];
}

/**
 * 月間座席状況を取得
 * 認証不要
 * @param brandId - ブランドID
 * @param schoolId - 校舎ID
 * @param year - 年
 * @param month - 月
 */
export async function getCalendarSeats(
  brandId: string,
  schoolId: string,
  year: number,
  month: number
): Promise<CalendarSeatsResponse> {
  return api.get<CalendarSeatsResponse>(
    `/schools/public/calendar-seats/?brand_id=${brandId}&school_id=${schoolId}&year=${year}&month=${month}`,
    { skipAuth: true }
  );
}

// ============================================
// 認証済みユーザー向け校舎API
// ============================================

/**
 * 校舎情報型（認証済みユーザー向け）
 */
export interface School {
  id: string;
  school_code: string;
  school_name: string;
  school_name_short?: string;
  prefecture?: string;
  city?: string;
  address1?: string;
  phone?: string;
}

/**
 * 校舎一覧を取得（認証済みユーザー向け）
 * スタッフ/講師がアクセス可能な校舎一覧を返す
 */
export async function getSchools(): Promise<School[]> {
  const response = await api.get<{ results?: School[] } | School[]>('/schools/');
  if (Array.isArray(response)) {
    return response;
  }
  return response.results || [];
}
