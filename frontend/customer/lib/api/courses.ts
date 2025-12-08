/**
 * Public Courses & Packs API
 * コース・パック購入関連のAPI関数（顧客向け・認証不要）
 */

import api from './client';
import type { PublicBrand, PublicCourse, PublicPack } from './types';

/**
 * 公開ブランド一覧を取得
 * 認証不要
 */
export async function getPublicBrands(): Promise<PublicBrand[]> {
  return api.get<PublicBrand[]>('/contracts/public/brands/', { skipAuth: true });
}

/**
 * 公開コース一覧を取得
 * 認証不要
 * @param params - フィルタパラメータ
 */
export async function getPublicCourses(params?: {
  brandId?: string;
  schoolId?: string;
}): Promise<PublicCourse[]> {
  const searchParams = new URLSearchParams();
  if (params?.brandId) searchParams.append('brand_id', params.brandId);
  if (params?.schoolId) searchParams.append('school_id', params.schoolId);

  const query = searchParams.toString();
  return api.get<PublicCourse[]>(
    `/contracts/public/courses/${query ? `?${query}` : ''}`,
    { skipAuth: true }
  );
}

/**
 * 公開コース詳細を取得
 * 認証不要
 * @param courseId - コースID
 */
export async function getPublicCourse(courseId: string): Promise<PublicCourse> {
  return api.get<PublicCourse>(`/contracts/public/courses/${courseId}/`, { skipAuth: true });
}

/**
 * 公開パック一覧を取得
 * 認証不要
 * @param params - フィルタパラメータ
 */
export async function getPublicPacks(params?: {
  brandId?: string;
  schoolId?: string;
}): Promise<PublicPack[]> {
  const searchParams = new URLSearchParams();
  if (params?.brandId) searchParams.append('brand_id', params.brandId);
  if (params?.schoolId) searchParams.append('school_id', params.schoolId);

  const query = searchParams.toString();
  return api.get<PublicPack[]>(
    `/contracts/public/packs/${query ? `?${query}` : ''}`,
    { skipAuth: true }
  );
}

/**
 * 公開パック詳細を取得
 * 認証不要
 * @param packId - パックID
 */
export async function getPublicPack(packId: string): Promise<PublicPack> {
  return api.get<PublicPack>(`/contracts/public/packs/${packId}/`, { skipAuth: true });
}
