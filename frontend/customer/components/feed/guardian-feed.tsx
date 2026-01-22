'use client';

import { useEffect, useState, useCallback } from 'react';
import { Heart, MessageCircle, AlertCircle, Filter, RefreshCw, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getFeedPosts, likeFeedPost, unlikeFeedPost, type FeedPost } from '@/lib/api/feed';
import { getMediaUrl } from '@/lib/api/client';
import { useRouter } from 'next/navigation';
import Image from 'next/image';

type AnnouncementType = {
  id: number;
  title: string;
  message: string;
  type: 'info' | 'warning' | 'important';
  date: string;
};

// お知らせは別APIから取得するか、フィードの固定投稿として表示
const announcements: AnnouncementType[] = [];

export function GuardianFeed() {
  const router = useRouter();
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAllBrands, setShowAllBrands] = useState(false);
  const [likedPosts, setLikedPosts] = useState<Set<string>>(new Set());

  const loadPosts = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const response = await getFeedPosts({ pageSize: 50 });
      const postsData = response.results || response.data || [];

      // デバッグ: メディアデータの構造を確認
      if (postsData.length > 0 && postsData[0].media) {
        if (postsData[0].media[0]) {
        }
      }

      setPosts(postsData);

      // いいね済みの投稿を設定
      const liked = new Set<string>();
      postsData.forEach((post) => {
        if (post.isLiked) {
          liked.add(post.id);
        }
      });
      setLikedPosts(liked);
    } catch (err) {
      console.error('Failed to load posts:', err);
      setError('投稿の読み込みに失敗しました');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  const handleRefresh = () => {
    loadPosts(true);
  };

  const getAnnouncementColor = (type: string) => {
    switch (type) {
      case 'important':
        return 'bg-red-50 border-red-200';
      case 'warning':
        return 'bg-amber-50 border-amber-200';
      case 'info':
        return 'bg-blue-50 border-blue-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getAnnouncementIconColor = (type: string) => {
    switch (type) {
      case 'important':
        return 'text-red-600';
      case 'warning':
        return 'text-amber-600';
      case 'info':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  const handleLike = async (postId: string) => {
    const isLiked = likedPosts.has(postId);

    // 楽観的更新
    const newLikedPosts = new Set(likedPosts);
    if (isLiked) {
      newLikedPosts.delete(postId);
    } else {
      newLikedPosts.add(postId);
    }
    setLikedPosts(newLikedPosts);

    // 投稿のいいね数を更新
    setPosts((prev) =>
      prev.map((post) =>
        post.id === postId
          ? { ...post, likeCount: post.likeCount + (isLiked ? -1 : 1) }
          : post
      )
    );

    try {
      if (isLiked) {
        await unlikeFeedPost(postId);
      } else {
        await likeFeedPost(postId);
      }
    } catch (err) {
      // エラー時は元に戻す
      console.error('Failed to toggle like:', err);
      setLikedPosts(likedPosts);
      setPosts((prev) =>
        prev.map((post) =>
          post.id === postId
            ? { ...post, likeCount: post.likeCount + (isLiked ? 1 : -1) }
            : post
        )
      );
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);

    if (hours < 1) return '今';
    if (hours < 24) return `${hours}時間前`;
    if (days < 7) return `${days}日前`;
    return date.toLocaleDateString('ja-JP');
  };

  const getPostTypeLabel = (post: FeedPost) => {
    if (post.isPinned) return '重要';
    if (post.postType === 'EVENT') return 'イベント';
    if (post.postType === 'ANNOUNCEMENT') return 'お知らせ';
    return null;
  };

  const getPostTypeBadgeClass = (post: FeedPost) => {
    if (post.isPinned) return 'bg-red-500 text-white';
    if (post.postType === 'EVENT') return 'bg-purple-500 text-white';
    if (post.postType === 'ANNOUNCEMENT') return 'bg-amber-500 text-white';
    return 'bg-blue-500 text-white';
  };

  if (loading) {
    return (
      <>
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center justify-between">
            <Image
              src="/oza-logo-header.svg"
              alt="OZA"
              width={100}
              height={36}
              className="h-9 w-auto"
              priority
            />
          </div>
        </header>
        <main className="max-w-[390px] mx-auto pb-24 flex items-center justify-center min-h-[50vh]">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <p className="text-gray-600">読み込み中...</p>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center justify-between">
          <Image
            src="/oza-logo-header.svg"
            alt="OZA"
            width={100}
            height={36}
            className="h-9 w-auto"
            priority
          />
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing}
              className="rounded-full"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
            <Button
              variant={showAllBrands ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowAllBrands(!showAllBrands)}
              className="rounded-full"
            >
              <Filter className="h-4 w-4 mr-1" />
              {showAllBrands ? '全て表示中' : '契約ブランドのみ'}
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto pb-24">
        {announcements.length > 0 && (
          <div className="px-4 py-4 space-y-3">
            {announcements.map((announcement) => (
              <Card
                key={announcement.id}
                className={`rounded-xl shadow-md ${getAnnouncementColor(announcement.type)}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className={`h-5 w-5 mt-0.5 ${getAnnouncementIconColor(announcement.type)}`} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-gray-800">{announcement.title}</h3>
                        <Badge variant="outline" className="text-xs">
                          {announcement.date}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-700">{announcement.message}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {error && (
          <div className="px-4 py-4">
            <Card className="rounded-xl bg-red-50 border-red-200">
              <CardContent className="p-4 text-center">
                <p className="text-red-600 mb-2">{error}</p>
                <Button variant="outline" size="sm" onClick={() => loadPosts()}>
                  再読み込み
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        {!error && posts.length === 0 && (
          <div className="px-4 py-8 text-center">
            <p className="text-gray-500">投稿がありません</p>
          </div>
        )}

        <div className="space-y-4 py-4">
          {posts.map((post) => (
            <Card key={post.id} className="rounded-none border-x-0 shadow-none">
              <CardContent className="p-0">
                <div className="px-4 py-3 flex items-center gap-3">
                  <Avatar>
                    <AvatarFallback className="bg-blue-100 text-blue-600 font-semibold">
                      {post.authorName?.charAt(0) || 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-800">{post.authorName || '運営'}</p>
                    <p className="text-xs text-gray-500">{formatDate(post.createdAt)}</p>
                  </div>
                  {getPostTypeLabel(post) && (
                    <Badge className={getPostTypeBadgeClass(post)}>
                      {getPostTypeLabel(post)}
                    </Badge>
                  )}
                </div>

                {/* メディア表示 */}
                {post.media && post.media.length > 0 ? (
                  <div className="relative">
                    {post.media[0].mediaType === 'VIDEO' ? (
                      <video
                        src={getMediaUrl(post.media[0].fileUrl)}
                        className="w-full aspect-square object-cover"
                        controls
                      />
                    ) : (
                      <img
                        src={getMediaUrl(post.media[0].fileUrl)}
                        alt={post.media[0].caption || '投稿画像'}
                        className="w-full aspect-square object-cover"
                        onError={(e) => console.error('Image load error:', post.media[0].fileUrl, e)}
                      />
                    )}
                    {post.media.length > 1 && (
                      <Badge className="absolute top-2 right-2 bg-black/60">
                        +{post.media.length - 1}
                      </Badge>
                    )}
                  </div>
                ) : (
                  <div className="w-full aspect-video bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center">
                    <p className="text-blue-600 text-sm">テキスト投稿</p>
                  </div>
                )}

                <div className="px-4 py-3">
                  <div className="flex items-center gap-4 mb-3">
                    <button
                      onClick={() => handleLike(post.id)}
                      className="hover:opacity-70 transition-opacity"
                    >
                      <Heart
                        className={`h-6 w-6 ${likedPosts.has(post.id)
                          ? 'fill-red-500 text-red-500'
                          : 'text-gray-700'
                        }`}
                      />
                    </button>
                    {post.allowComments && (
                      <button
                        onClick={() => router.push(`/feed/${post.id}`)}
                        className="hover:opacity-70 transition-opacity"
                      >
                        <MessageCircle className="h-6 w-6 text-gray-700" />
                      </button>
                    )}
                  </div>

                  {post.likeCount > 0 && (
                    <p className="font-semibold text-sm text-gray-800 mb-1">
                      {post.likeCount}件のいいね
                    </p>
                  )}

                  {post.title && (
                    <h4 className="font-semibold text-gray-900 mb-1">{post.title}</h4>
                  )}

                  <p className="text-sm text-gray-800">
                    <span className="font-semibold mr-2">{post.authorName || '運営'}</span>
                    {post.content}
                  </p>

                  {post.hashtags && post.hashtags.length > 0 && (
                    <p className="text-sm text-blue-600 mt-1">
                      {post.hashtags.map((tag) => `#${tag}`).join(' ')}
                    </p>
                  )}

                  {post.commentCount > 0 && (
                    <button
                      onClick={() => router.push(`/feed/${post.id}`)}
                      className="text-sm text-gray-500 mt-2"
                    >
                      {post.commentCount}件のコメントを見る
                    </button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </>
  );
}
