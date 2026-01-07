'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { BottomNav } from '@/components/bottom-nav';
import { Heart, MessageCircle, Bookmark, Plus, Loader2, RefreshCw, Pin } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';
import Image from 'next/image';
import api, { getMediaUrl } from '@/lib/api/client';

interface FeedAuthor {
  id: string;
  fullName: string;
  displayName: string;
  profileImageUrl: string | null;
}

interface FeedMedia {
  id: string;
  mediaType: 'IMAGE' | 'VIDEO';
  fileUrl: string;
  thumbnailUrl: string | null;
}

interface FeedPost {
  id: string;
  title?: string;
  content: string;
  postType: string;
  visibility: string;
  hashtags: string[];
  isPinned: boolean;
  isPublished: boolean;
  allowComments: boolean;
  allowLikes: boolean;
  likesCount: number;
  commentsCount: number;
  viewsCount: number;
  media: FeedMedia[];
  author: FeedAuthor;
  authorDetail?: FeedAuthor;
  schoolName: string | null;
  createdAt: string;
  updatedAt: string;
}

interface FeedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: FeedPost[];
}

export default function FeedPage() {
  const router = useRouter();
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPosts();
  }, []);

  const loadPosts = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get<FeedResponse>('/communications/feed/posts/');
      setPosts(response.results || []);
    } catch (err: any) {
      console.error('Failed to load posts:', err);
      setError(err?.message || 'フィードの読み込みに失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const getAuthorName = (post: FeedPost) => {
    const author = post.authorDetail || post.author;
    return author?.displayName || author?.fullName || '匿名';
  };

  const getAuthorInitial = (post: FeedPost) => {
    const name = getAuthorName(post);
    return name.charAt(0);
  };

  const getAuthorImage = (post: FeedPost) => {
    const author = post.authorDetail || post.author;
    return author?.profileImageUrl || null;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white pb-20">
      <div className="max-w-[420px] mx-auto">
        {/* ヘッダー */}
        <div className="bg-white/90 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4 flex items-center justify-between">
            <Image
              src="/oza-logo-header.svg"
              alt="OZA"
              width={100}
              height={36}
              className="h-9 w-auto"
              priority
            />
            <Button
              size="sm"
              variant="ghost"
              onClick={loadPosts}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* エラー表示 */}
        {error && (
          <div className="p-4">
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">
              {error}
              <Button
                variant="link"
                size="sm"
                className="ml-2 text-red-700 underline"
                onClick={loadPosts}
              >
                再試行
              </Button>
            </div>
          </div>
        )}

        {/* 投稿一覧 */}
        <div className="p-4 space-y-4">
          {posts.map((post) => (
            <Card
              key={post.id}
              className="shadow-md border-0 rounded-2xl overflow-hidden hover:shadow-lg transition-shadow"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                  <Avatar className="w-12 h-12">
                    <AvatarImage src={getAuthorImage(post) || undefined} />
                    <AvatarFallback className="bg-blue-500 text-white">
                      {getAuthorInitial(post)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-gray-900">
                        {getAuthorName(post)}
                      </h3>
                      {post.isPinned && (
                        <Badge variant="secondary" className="text-xs bg-yellow-100 text-yellow-800">
                          <Pin className="w-3 h-3 mr-1" />
                          固定
                        </Badge>
                      )}
                      {post.schoolName && (
                        <Badge variant="secondary" className="text-xs">
                          {post.schoolName}
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      {formatDistanceToNow(new Date(post.createdAt), {
                        addSuffix: true,
                        locale: ja,
                      })}
                    </p>
                  </div>
                </div>
              </CardHeader>

              {/* メディア表示 */}
              {post.media && post.media.length > 0 && (
                <div className="w-full">
                  {post.media[0].mediaType === 'VIDEO' ? (
                    <video
                      src={getMediaUrl(post.media[0].fileUrl)}
                      controls
                      className="w-full h-auto max-h-[400px] object-cover"
                    />
                  ) : (
                    <img
                      src={getMediaUrl(post.media[0].fileUrl)}
                      alt="Post image"
                      className="w-full h-auto max-h-[400px] object-cover"
                    />
                  )}
                </div>
              )}

              <CardContent className="pt-4">
                {post.title && (
                  <h4 className="font-semibold text-gray-900 mb-2">{post.title}</h4>
                )}
                <p className="text-gray-800 whitespace-pre-wrap mb-3">{post.content}</p>

                {/* ハッシュタグ */}
                {post.hashtags && post.hashtags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {post.hashtags.map((tag, index) => (
                      <span
                        key={index}
                        className="text-blue-500 text-sm hover:underline cursor-pointer"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}

                {/* アクション */}
                <div className="flex items-center gap-4 pt-2 border-t">
                  {post.allowLikes && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="gap-2 text-gray-600"
                    >
                      <Heart className="w-5 h-5" />
                      <span className="text-sm">{post.likesCount}</span>
                    </Button>
                  )}

                  {post.allowComments && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="gap-2 text-gray-600"
                    >
                      <MessageCircle className="w-5 h-5" />
                      <span className="text-sm">{post.commentsCount}</span>
                    </Button>
                  )}

                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-2 text-gray-600 ml-auto"
                  >
                    <Bookmark className="w-5 h-5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}

          {/* 投稿がない場合 */}
          {!loading && posts.length === 0 && !error && (
            <div className="text-center py-12">
              <p className="text-gray-500 mb-4">まだ投稿がありません</p>
              <Button onClick={loadPosts}>
                <RefreshCw className="w-4 h-4 mr-2" />
                更新する
              </Button>
            </div>
          )}
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
