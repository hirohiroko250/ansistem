/**
 * Feed API
 * フィード投稿関連のAPI関数（保護者・顧客向け）
 */

import api from './client';
import type { PaginatedResponse } from './types';

// ============================================
// 型定義
// ============================================

export interface FeedPost {
  id: string;
  postType: string;
  content: string;
  visibility: string;
  hashtags: string[];
  isPinned: boolean;
  isPublished: boolean;
  allowComments: boolean;
  allowLikes: boolean;
  viewCount: number;
  likeCount: number;
  commentCount: number;
  publishedAt: string | null;
  publishEndAt: string | null;
  createdAt: string;
  updatedAt: string;
  author: {
    id: string;
    fullName: string;
    email: string;
  } | null;
  authorName: string;
  school: {
    id: string;
    schoolName: string;
  } | null;
  media: FeedMedia[];
  targetSchools: { id: string; schoolName: string }[];
  targetGrades: { id: string; gradeName: string }[];
  targetBrands: { id: string; brandName: string }[];
  isLiked?: boolean;
  isBookmarked?: boolean;
}

export interface FeedMedia {
  id: string;
  mediaType: 'IMAGE' | 'VIDEO';
  fileUrl: string;
  thumbnailUrl?: string;
  caption?: string;
  displayOrder: number;
}

export interface FeedComment {
  id: string;
  postId: string;
  content: string;
  author: {
    id: string;
    fullName: string;
  } | null;
  authorName: string;
  likeCount: number;
  isLiked?: boolean;
  createdAt: string;
}

// ============================================
// フィード投稿関連
// ============================================

export interface GetFeedPostsParams {
  page?: number;
  pageSize?: number;
  visibility?: string;
  schoolId?: string;
  hashtag?: string;
  authorId?: string;
}

/**
 * フィード投稿一覧を取得
 */
export async function getFeedPosts(params?: GetFeedPostsParams): Promise<PaginatedResponse<FeedPost>> {
  const query = new URLSearchParams();
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));
  if (params?.visibility) query.set('visibility', params.visibility);
  if (params?.schoolId) query.set('school_id', params.schoolId);
  if (params?.hashtag) query.set('hashtag', params.hashtag);
  if (params?.authorId) query.set('author_id', params.authorId);

  const queryString = query.toString();
  const endpoint = queryString
    ? `/communications/feed/posts/?${queryString}`
    : '/communications/feed/posts/';

  return api.get<PaginatedResponse<FeedPost>>(endpoint);
}

/**
 * フィード投稿詳細を取得
 */
export async function getFeedPost(id: string): Promise<FeedPost> {
  return api.get<FeedPost>(`/communications/feed/posts/${id}/`);
}

// ============================================
// いいね関連
// ============================================

/**
 * 投稿にいいねする
 */
export async function likeFeedPost(postId: string): Promise<{ liked: boolean; likeCount: number }> {
  return api.post<{ liked: boolean; likeCount: number }>(`/communications/feed/posts/${postId}/like/`);
}

/**
 * 投稿のいいねを解除する
 */
export async function unlikeFeedPost(postId: string): Promise<{ liked: boolean; likeCount: number }> {
  return api.delete<{ liked: boolean; likeCount: number }>(`/communications/feed/posts/${postId}/like/`);
}

// ============================================
// コメント関連
// ============================================

/**
 * 投稿のコメント一覧を取得
 */
export async function getFeedComments(postId: string): Promise<FeedComment[]> {
  const response = await api.get<PaginatedResponse<FeedComment>>(`/communications/feed/posts/${postId}/comments/`);
  return response.results || response.data || [];
}

/**
 * コメントを投稿する
 */
export async function createFeedComment(postId: string, content: string): Promise<FeedComment> {
  return api.post<FeedComment>(`/communications/feed/posts/${postId}/comments/`, { content });
}

// ============================================
// ブックマーク関連
// ============================================

/**
 * 投稿をブックマークする
 */
export async function bookmarkFeedPost(postId: string): Promise<{ bookmarked: boolean }> {
  return api.post<{ bookmarked: boolean }>(`/communications/feed/posts/${postId}/bookmark/`);
}

/**
 * ブックマークを解除する
 */
export async function unbookmarkFeedPost(postId: string): Promise<{ bookmarked: boolean }> {
  return api.delete<{ bookmarked: boolean }>(`/communications/feed/posts/${postId}/bookmark/`);
}

/**
 * ブックマークした投稿一覧を取得
 */
export async function getBookmarkedPosts(): Promise<FeedPost[]> {
  const response = await api.get<PaginatedResponse<FeedPost>>('/communications/feed/bookmarks/');
  return response.results || response.data || [];
}
