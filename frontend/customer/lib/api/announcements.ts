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
    const response = await api.get<AnnouncementResponse>('/communications/announcements/', {
      params: {
        status: 'SENT',
        page_size: limit,
      },
    });
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
    const response = await api.get<FeedPostResponse>('/communications/feed/posts/', {
      params: {
        page_size: limit,
      },
    });
    return response?.results || [];
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
    const [announcements, feedPosts] = await Promise.all([
      getAnnouncements(limit),
      getFeedPosts(limit),
    ]);

    const news: NewsItem[] = [];

    // お知らせをNewsItemに変換
    announcements.forEach((a) => {
      news.push({
        id: a.id,
        type: 'お知らせ',
        caption: a.title,
        date: formatDate(a.sentAt || a.createdAt),
        source: 'announcement',
      });
    });

    // フィード投稿をNewsItemに変換
    feedPosts.forEach((f) => {
      let type: '新着' | 'お知らせ' | 'イベント' = '新着';
      if (f.hashtags.includes('イベント') || f.hashtags.includes('event')) {
        type = 'イベント';
      } else if (f.hashtags.includes('お知らせ') || f.hashtags.includes('notice')) {
        type = 'お知らせ';
      }

      news.push({
        id: f.id,
        type,
        caption: f.content.slice(0, 100),
        date: formatDate(f.publishedAt || f.createdAt),
        source: 'feed',
      });
    });

    // 日付でソート（新しい順）
    news.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

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
