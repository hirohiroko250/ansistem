'use client';

/**
 * useFeed - フィード関連フック
 *
 * フィード投稿、コメント、いいねなどを管理するReact Queryフック
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getFeedPost,
  getFeedComments,
  createFeedComment,
  likeFeedPost,
  unlikeFeedPost,
  type FeedPost,
  type FeedComment,
} from '@/lib/api/feed';

// クエリキー
export const feedKeys = {
  all: ['feed'] as const,
  lists: () => [...feedKeys.all, 'list'] as const,
  details: () => [...feedKeys.all, 'detail'] as const,
  detail: (id: string) => [...feedKeys.details(), id] as const,
  comments: (postId: string) => [...feedKeys.all, 'comments', postId] as const,
};

/**
 * フィード投稿詳細を取得
 */
export function useFeedPost(postId: string | undefined) {
  return useQuery({
    queryKey: feedKeys.detail(postId || ''),
    queryFn: async () => {
      if (!postId) throw new Error('Post ID is required');
      return getFeedPost(postId);
    },
    enabled: !!postId && !!getAccessToken(),
    staleTime: 2 * 60 * 1000, // 2分
  });
}

/**
 * フィード投稿のコメントを取得
 */
export function useFeedComments(postId: string | undefined) {
  return useQuery({
    queryKey: feedKeys.comments(postId || ''),
    queryFn: async () => {
      if (!postId) throw new Error('Post ID is required');
      return getFeedComments(postId);
    },
    enabled: !!postId && !!getAccessToken(),
    staleTime: 1 * 60 * 1000, // 1分
  });
}

/**
 * コメントを投稿
 */
export function useCreateComment(postId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (content: string) => createFeedComment(postId, content),
    onSuccess: (newComment) => {
      // コメント一覧のキャッシュを更新
      queryClient.setQueryData<FeedComment[]>(feedKeys.comments(postId), (old) =>
        old ? [...old, newComment] : [newComment]
      );
    },
  });
}

/**
 * いいねを切り替え
 */
export function useToggleLike(postId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (isCurrentlyLiked: boolean) => {
      if (isCurrentlyLiked) {
        await unlikeFeedPost(postId);
        return false;
      } else {
        await likeFeedPost(postId);
        return true;
      }
    },
    onMutate: async (isCurrentlyLiked) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: feedKeys.detail(postId) });
      const previousPost = queryClient.getQueryData<FeedPost>(feedKeys.detail(postId));

      if (previousPost) {
        queryClient.setQueryData<FeedPost>(feedKeys.detail(postId), {
          ...previousPost,
          isLiked: !isCurrentlyLiked,
          likeCount: previousPost.likeCount + (isCurrentlyLiked ? -1 : 1),
        });
      }

      return { previousPost };
    },
    onError: (err, isCurrentlyLiked, context) => {
      // Rollback on error
      if (context?.previousPost) {
        queryClient.setQueryData(feedKeys.detail(postId), context.previousPost);
      }
    },
  });
}

/**
 * フィードキャッシュを無効化
 */
export function useInvalidateFeed() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: feedKeys.all });
  };
}

// 型を再エクスポート
export type { FeedPost, FeedComment } from '@/lib/api/feed';
