'use client';

/**
 * useBrands - ブランド情報取得フック
 *
 * ブランド一覧を取得するReact Queryフック
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { PublicBrand, PublicBrandCategory } from '@/lib/api/types';

// クエリキー
export const brandKeys = {
  all: ['brands'] as const,
  lists: () => [...brandKeys.all, 'list'] as const,
  list: (filters?: Record<string, unknown>) =>
    [...brandKeys.lists(), filters] as const,
  detail: (id: string) => [...brandKeys.all, 'detail', id] as const,
  categories: () => [...brandKeys.all, 'categories'] as const,
  public: () => [...brandKeys.all, 'public'] as const,
};

interface BrandsResponse {
  brands: PublicBrand[];
  categories?: PublicBrandCategory[];
}

/**
 * ブランド一覧を取得（公開API）
 */
export function useBrands() {
  return useQuery({
    queryKey: brandKeys.public(),
    queryFn: async () => {
      const response = await api.get<BrandsResponse>(
        '/contracts/public/brands/',
        { skipAuth: true }
      );
      return response.brands || [];
    },
    staleTime: 30 * 60 * 1000, // 30分
    gcTime: 60 * 60 * 1000, // 1時間
  });
}

/**
 * ブランドカテゴリ一覧を取得
 */
export function useBrandCategories() {
  return useQuery({
    queryKey: brandKeys.categories(),
    queryFn: async () => {
      const response = await api.get<{ categories: PublicBrandCategory[] }>(
        '/contracts/public/brand-categories/',
        { skipAuth: true }
      );
      return response.categories || [];
    },
    staleTime: 60 * 60 * 1000, // 1時間
    gcTime: 24 * 60 * 60 * 1000, // 24時間
  });
}

/**
 * 特定のブランドを取得
 */
export function useBrand(brandId: string | undefined) {
  const { data: brands } = useBrands();

  return useQuery({
    queryKey: brandKeys.detail(brandId || ''),
    queryFn: async () => {
      // キャッシュされたブランド一覧から検索
      if (brands) {
        const brand = brands.find((b: PublicBrand) => b.id === brandId);
        if (brand) return brand;
      }
      // 見つからない場合は個別取得
      const response = await api.get<PublicBrand>(
        `/contracts/public/brands/${brandId}/`,
        { skipAuth: true }
      );
      return response;
    },
    enabled: !!brandId,
    staleTime: 30 * 60 * 1000,
  });
}
