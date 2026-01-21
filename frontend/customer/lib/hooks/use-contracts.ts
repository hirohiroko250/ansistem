'use client';

/**
 * useContracts - 契約情報取得フック
 *
 * スタッフ向け契約管理のReact Queryフック
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getContracts,
  getContract,
  updateContract,
  suspendContract,
  resumeContract,
  cancelContract,
  getMyContracts,
  type Contract,
  type ContractDetail,
  type ContractSearchParams,
  type UpdateContractRequest,
  type SuspendContractRequest,
  type CancelContractRequest,
  type MyContractsResponse,
} from '@/lib/api/contracts';

// クエリキー
export const contractKeys = {
  all: ['contracts'] as const,
  lists: () => [...contractKeys.all, 'list'] as const,
  list: (filters?: ContractSearchParams) =>
    [...contractKeys.lists(), filters] as const,
  details: () => [...contractKeys.all, 'detail'] as const,
  detail: (id: string) => [...contractKeys.details(), id] as const,
  my: () => [...contractKeys.all, 'my'] as const,
};

/**
 * 契約一覧を取得（スタッフ向け）
 */
export function useContracts(params?: ContractSearchParams) {
  return useQuery({
    queryKey: contractKeys.list(params),
    queryFn: async () => {
      const response = await getContracts(params);
      return {
        contracts: response.results || [],
        count: response.count || 0,
        hasNext: !!response.next,
        hasPrev: !!response.previous,
      };
    },
    enabled: !!getAccessToken(),
    staleTime: 2 * 60 * 1000, // 2分
  });
}

/**
 * 契約詳細を取得
 */
export function useContract(contractId: string | undefined) {
  return useQuery({
    queryKey: contractKeys.detail(contractId || ''),
    queryFn: async () => {
      if (!contractId) throw new Error('Contract ID is required');
      return getContract(contractId);
    },
    enabled: !!contractId && !!getAccessToken(),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 自分の子どもの契約一覧を取得（保護者向け）
 */
export function useMyContracts() {
  return useQuery({
    queryKey: contractKeys.my(),
    queryFn: async () => {
      return getMyContracts();
    },
    enabled: !!getAccessToken(),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 契約を更新
 */
export function useUpdateContract() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateContractRequest }) => {
      return updateContract(id, data);
    },
    onSuccess: (data: Contract, variables: { id: string; data: UpdateContractRequest }) => {
      queryClient.setQueryData(contractKeys.detail(variables.id), data);
      queryClient.invalidateQueries({ queryKey: contractKeys.lists() });
    },
  });
}

/**
 * 契約を休会
 */
export function useSuspendContract() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data?: SuspendContractRequest }) => {
      return suspendContract(id, data);
    },
    onSuccess: (_data: Contract, variables: { id: string; data?: SuspendContractRequest }) => {
      queryClient.invalidateQueries({ queryKey: contractKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: contractKeys.lists() });
    },
  });
}

/**
 * 契約を再開
 */
export function useResumeContract() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return resumeContract(id);
    },
    onSuccess: (_data: Contract, id: string) => {
      queryClient.invalidateQueries({ queryKey: contractKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: contractKeys.lists() });
    },
  });
}

/**
 * 契約を解約
 */
export function useCancelContract() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data?: CancelContractRequest }) => {
      return cancelContract(id, data);
    },
    onSuccess: (_data: Contract, variables: { id: string; data?: CancelContractRequest }) => {
      queryClient.invalidateQueries({ queryKey: contractKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: contractKeys.lists() });
    },
  });
}

/**
 * 契約キャッシュを無効化
 */
export function useInvalidateContracts() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: contractKeys.all });
  };
}
