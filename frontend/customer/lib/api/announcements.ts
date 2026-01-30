/**
 * お知らせ・フィード API
 */
import api from './client';

export interface Announcement {
  id: string;
  title: string;
  content: string;
  targetType: string;
  status: string;
  sentAt: string | null;
  createdAt: string;
}

export interface FeedPost {
  id: string;
  postType: string;
  authorName: string;
  schoolName: string | null;
  title?: string;
  content: string;
  visibility: string;
  hashtags: string[];
  isPinned: boolean;
  likeCount: number;
  commentCount: number;
  viewCount: number;
  isLiked: boolean;
  isBookmarked: boolean;
  isPublished: boolean;
  publishedAt: string | null;
  createdAt: string;
}

interface AnnouncementResponse {
  results: Announcement[];
  count: number;
}

interface FeedPostResponse {
  results: FeedPost[];
  count: number;
}

/**
 * お知らせ一覧を取得（送信済みのみ）
 */
export async function getAnnouncements(limit: number = 10): Promise<Announcement[]> {
  try {
    const response = await api.get<AnnouncementResponse>(`/communications/announcements/?status=SENT&page_size=${limit}`);
    return response?.results || [];
  } catch (error) {
    console.error('Failed to fetch announcements:', error);
    return [];
  }
}

/**
 * フィード投稿一覧を取得
 */
export async function getFeedPosts(limit: number = 10): Promise<FeedPost[]> {
  try {
    const response = await api.get<any>(`/communications/feed/posts/?page_size=${limit}`);
    // ページネーション形式 { results: [...] } と配列の両方に対応
    const data = response?.results || response?.data || response || [];
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Failed to fetch feed posts:', error);
    return [];
  }
}

/**
 * フィード投稿詳細を取得
 */
export async function getFeedPost(id: string): Promise<FeedPost | null> {
  try {
    return await api.get<FeedPost>(`/communications/feed/posts/${id}/`);
  } catch (error) {
    console.error('Failed to fetch feed post:', error);
    return null;
  }
}

/**
 * お知らせとフィードを統合して取得（ホーム用）
 */
export interface NewsItem {
  id: string;
  type: '新着' | 'お知らせ' | 'イベント';
  caption: string;
  date: string;
  source: 'announcement' | 'feed';
}

export async function getLatestNews(limit: number = 5): Promise<NewsItem[]> {
  try {
    const feedPosts = await getFeedPosts(limit);

    const news: NewsItem[] = [];

    // フィード投稿をNewsItemに変換
    feedPosts.forEach((f) => {
      let type: '新着' | 'お知らせ' | 'イベント' = '新着';
      if (f.hashtags.includes('イベント') || f.hashtags.includes('event')) {
        type = 'イベント';
      } else if (f.hashtags.includes('お知らせ') || f.hashtags.includes('notice')) {
        type = 'お知らせ';
      }

      const rawDate = f.publishedAt || f.createdAt;
      const caption = f.title || f.content.replace(/<[^>]*>/g, '').slice(0, 100);

      news.push({
        id: f.id,
        type,
        caption,
        date: formatDate(rawDate),
        source: 'feed',
      });
    });

    return news.slice(0, limit);
  } catch (error) {
    console.error('Failed to fetch latest news:', error);
    return [];
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
}
