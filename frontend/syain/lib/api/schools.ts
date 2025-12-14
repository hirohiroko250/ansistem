/**
 * Schools API
 * 校舎・ブランド関連のAPI関数
 */

import api from './client';

export interface BrandCategory {
  id: string;
  name: string;
  code: string;
}

export interface Brand {
  id: string;
  brandName: string;
  brandCode: string;
  brandCategoryId?: string;
  brandCategoryName?: string;
}

export interface School {
  id: string;
  schoolName: string;
  schoolCode: string;
  brandId?: string;
  brandName?: string;
}

/**
 * ブランドカテゴリ（会社）一覧取得
 */
export async function getBrandCategories(): Promise<BrandCategory[]> {
  const response = await api.get<{ results: BrandCategory[] } | BrandCategory[]>('/schools/brand-categories/');
  return Array.isArray(response) ? response : response.results;
}

/**
 * ブランド一覧取得
 */
export async function getBrands(categoryId?: string): Promise<Brand[]> {
  const query = categoryId ? `?brand_category_id=${categoryId}` : '';
  const response = await api.get<{ results: Brand[] } | Brand[]>(`/schools/brands/${query}`);
  return Array.isArray(response) ? response : response.results;
}

/**
 * 校舎一覧取得
 */
export async function getSchools(brandId?: string): Promise<School[]> {
  const query = brandId ? `?brand_id=${brandId}` : '';
  const response = await api.get<{ results: School[] } | School[]>(`/schools/${query}`);
  return Array.isArray(response) ? response : response.results;
}
