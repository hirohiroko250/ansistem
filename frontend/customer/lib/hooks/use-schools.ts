'use client';

/**
 * useSchools - 校舎情報取得フック
 *
 * 校舎一覧を取得するReact Queryフック
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { School, PublicSchool } from '@/lib/api/types';

// クエリキー
export const schoolKeys = {
  all: ['schools'] as const,
  lists: () => [...schoolKeys.all, 'list'] as const,
  list: (filters?: Record<string, unknown>) =>
    [...schoolKeys.lists(), filters] as const,
  detail: (id: string) => [...schoolKeys.all, 'detail', id] as const,
  public: () => [...schoolKeys.all, 'public'] as const,
};

interface SchoolsResponse {
  schools: School[];
  count?: number;
}

interface PublicSchoolsResponse {
  schools: PublicSchool[];
}

/**
 * 校舎一覧を取得（認証必要）
 */
export function useSchools(filters?: { brandId?: string; prefectureId?: string }) {
  return useQuery({
    queryKey: schoolKeys.list(filters),
    queryFn: async () => {
      let endpoint = '/schools/';
      const params = new URLSearchParams();
      if (filters?.brandId) params.append('brand_id', filters.brandId);
      if (filters?.prefectureId) params.append('prefecture_id', filters.prefectureId);
      if (params.toString()) endpoint += `?${params.toString()}`;

      const response = await api.get<SchoolsResponse>(endpoint);
      return response.schools || [];
    },
    staleTime: 30 * 60 * 1000, // 30分（校舎情報は頻繁に変わらない）
    gcTime: 60 * 60 * 1000, // 1時間
  });
}

/**
 * 公開校舎一覧を取得（認証不要）
 */
export function usePublicSchools() {
  return useQuery({
    queryKey: schoolKeys.public(),
    queryFn: async () => {
      const response = await api.get<PublicSchoolsResponse>(
        '/schools/public/',
        { skipAuth: true }
      );
      return response.schools || [];
    },
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });
}

/**
 * 特定の校舎を取得
 */
export function useSchool(schoolId: string | undefined) {
  return useQuery({
    queryKey: schoolKeys.detail(schoolId || ''),
    queryFn: async () => {
      if (!schoolId) throw new Error('School ID is required');
      const response = await api.get<School>(`/schools/${schoolId}/`);
      return response;
    },
    enabled: !!schoolId,
    staleTime: 30 * 60 * 1000,
  });
}
