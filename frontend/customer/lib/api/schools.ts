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
