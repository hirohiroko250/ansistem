'use client';

import { useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { getMediaUrl } from '@/lib/api/client';
import { Heart, MessageCircle, ArrowLeft, Send, Loader2 } from 'lucide-react';
import { AuthGuard } from '@/components/auth';
import { useFeedPost, useFeedComments, useCreateComment, useToggleLike, type FeedComment } from '@/lib/hooks/use-feed';

function FeedDetailContent() {
  const router = useRouter();
  const params = useParams();
  const postId = params.id as string;

  // React Queryフックを使用
  const { data: post, isLoading: postLoading, error: postError } = useFeedPost(postId);
  const { data: comments = [] } = useFeedComments(postId);
  const createCommentMutation = useCreateComment(postId);
  const toggleLikeMutation = useToggleLike(postId);

  const [newComment, setNewComment] = useState('');

  const loading = postLoading;
  const error = postError ? '投稿の読み込みに失敗しました' : null;

  // いいね状態とカウント（postデータから取得）
  const isLiked = post?.isLiked || false;
  const likeCount = post?.likeCount || 0;

  const handleLike = async () => {
    if (!post) return;
    toggleLikeMutation.mutate(isLiked);
  };

  const handleSubmitComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim() || createCommentMutation.isPending) return;

    try {
      await createCommentMutation.mutateAsync(newComment.trim());
      setNewComment('');
    } catch {
      alert('コメントの投稿に失敗しました');
    }
  };

  const submitting = createCommentMutation.isPending;

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

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <span className="ml-2 font-semibold">投稿詳細</span>
          </div>
        </header>
        <main className="max-w-[390px] mx-auto pb-24 flex items-center justify-center min-h-[50vh]">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <p className="text-gray-600">読み込み中...</p>
          </div>
        </main>
        <BottomTabBar />
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <span className="ml-2 font-semibold">投稿詳細</span>
          </div>
        </header>
        <main className="max-w-[390px] mx-auto pb-24 px-4 py-8">
          <Card className="rounded-xl bg-red-50 border-red-200">
            <CardContent className="p-4 text-center">
              <p className="text-red-600 mb-2">{error || '投稿が見つかりません'}</p>
              <Button variant="outline" size="sm" onClick={() => router.push('/feed')}>
                フィードに戻る
              </Button>
            </CardContent>
          </Card>
        </main>
        <BottomTabBar />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <span className="ml-2 font-semibold">投稿詳細</span>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto pb-24">
        {/* Post */}
        <Card className="rounded-none border-x-0 shadow-none">
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
              {post.isPinned && (
                <Badge className="bg-red-500 text-white">重要</Badge>
              )}
            </div>

            {/* Media */}
            {post.media && post.media.length > 0 && (
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
                    alt="投稿画像"
                    className="w-full aspect-square object-cover"
                  />
                )}
                {post.media.length > 1 && (
                  <Badge className="absolute top-2 right-2 bg-black/60">
                    +{post.media.length - 1}
                  </Badge>
                )}
              </div>
            )}

            <div className="px-4 py-3">
              <div className="flex items-center gap-4 mb-3">
                <button
                  onClick={handleLike}
                  className="hover:opacity-70 transition-opacity"
                >
                  <Heart
                    className={`h-6 w-6 ${isLiked ? 'fill-red-500 text-red-500' : 'text-gray-700'}`}
                  />
                </button>
                <MessageCircle className="h-6 w-6 text-gray-700" />
              </div>

              {likeCount > 0 && (
                <p className="font-semibold text-sm text-gray-800 mb-1">
                  {likeCount}件のいいね
                </p>
              )}

              {post.title && (
                <h2 className="font-semibold text-gray-900 mb-2">{post.title}</h2>
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
            </div>
          </CardContent>
        </Card>

        {/* Comments Section */}
        <div className="px-4 py-3 border-t">
          <h3 className="font-semibold text-gray-800 mb-3">
            コメント ({comments.length})
          </h3>

          {comments.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">
              コメントはまだありません
            </p>
          ) : (
            <div className="space-y-4">
              {comments.map((comment) => (
                <div key={comment.id} className="flex gap-3">
                  <Avatar className="w-8 h-8">
                    <AvatarFallback className="bg-gray-100 text-gray-600 text-xs">
                      {comment.authorName?.charAt(0) || 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <p className="text-sm">
                      <span className="font-semibold mr-2">{comment.authorName || '匿名'}</span>
                      {comment.content}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatDate(comment.createdAt)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Comment Input */}
        {post.allowComments && (
          <form
            onSubmit={handleSubmitComment}
            className="fixed bottom-16 left-0 right-0 bg-white border-t px-4 py-3"
          >
            <div className="max-w-[390px] mx-auto flex gap-2">
              <Input
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="コメントを入力..."
                className="flex-1"
                disabled={submitting}
              />
              <Button type="submit" size="sm" disabled={!newComment.trim() || submitting}>
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </form>
        )}
      </main>

      <BottomTabBar />
    </div>
  );
}

export default function FeedDetailPage() {
  return (
    <AuthGuard>
      <FeedDetailContent />
    </AuthGuard>
  );
}
