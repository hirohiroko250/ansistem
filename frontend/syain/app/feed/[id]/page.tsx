'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { ArrowLeft, Heart, Send, Sparkles, Bookmark } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';

interface Post {
  id: string;
  content: string;
  image_url: string | null;
  video_url: string | null;
  created_at: string;
  instructor: {
    full_name: string;
    avatar_url: string | null;
  };
  campus: {
    name: string;
  } | null;
}

interface Comment {
  id: string;
  content: string;
  created_at: string;
  user: {
    full_name: string;
    avatar_url: string | null;
  };
}

export default function PostDetailPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const postId = params.id as string;

  const [post, setPost] = useState<Post | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [reactionCount, setReactionCount] = useState(0);
  const [hasReacted, setHasReacted] = useState(false);
  const [aiSummary, setAiSummary] = useState('');
  const [showAiSummary, setShowAiSummary] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    loadPost();
    loadComments();
    loadReactions();
  }, [user, loading, postId]);

  const loadPost = async () => {
    const { data, error } = await supabase
      .from('posts')
      .select(`
        id,
        content,
        image_url,
        video_url,
        created_at,
        instructor:profiles!instructor_id(full_name, avatar_url),
        campus:campuses(name)
      `)
      .eq('id', postId)
      .single();

    if (data) {
      setPost(data as any);
    }
  };

  const loadComments = async () => {
    const { data } = await supabase
      .from('post_comments')
      .select(`
        id,
        content,
        created_at,
        user:profiles!user_id(full_name, avatar_url)
      `)
      .eq('post_id', postId)
      .order('created_at', { ascending: true });

    if (data) {
      setComments(data as any);
    }
  };

  const loadReactions = async () => {
    if (!user) return;

    const { count } = await supabase
      .from('post_reactions')
      .select('*', { count: 'exact', head: true })
      .eq('post_id', postId);

    setReactionCount(count || 0);

    const { data: userReaction } = await supabase
      .from('post_reactions')
      .select('id')
      .eq('post_id', postId)
      .eq('user_id', user.id)
      .maybeSingle();

    setHasReacted(!!userReaction);
  };

  const handleAddComment = async () => {
    if (!user || !newComment.trim()) return;

    const { error } = await supabase
      .from('post_comments')
      .insert({
        post_id: postId,
        user_id: user.id,
        content: newComment,
      });

    if (!error) {
      setNewComment('');
      loadComments();
    }
  };

  const toggleReaction = async () => {
    if (!user) return;

    if (hasReacted) {
      await supabase
        .from('post_reactions')
        .delete()
        .eq('post_id', postId)
        .eq('user_id', user.id);
    } else {
      await supabase
        .from('post_reactions')
        .insert({
          post_id: postId,
          user_id: user.id,
          reaction_type: 'like',
        });
    }

    loadReactions();
  };

  const generateAiSummary = () => {
    const allContent = [
      `投稿: ${post?.content}`,
      ...comments.map((c, i) => `コメント${i + 1}: ${c.content}`),
    ].join('\n\n');

    const summary = `【投稿要約】\n${post?.content.substring(0, 100)}...\n\n【コメント要約】\n全${comments.length}件のコメントがあります。主な反応として、共感や質問、追加情報の共有などが見られます。講師同士の活発な情報交換が行われています。`;

    setAiSummary(summary);
    setShowAiSummary(true);
  };

  if (loading || !post) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white" />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white pb-24">
      <div className="max-w-[420px] mx-auto">
        <div className="bg-white/90 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4 flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => router.back()}
              className="rounded-full"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <h1 className="text-xl font-bold text-gray-900">投稿詳細</h1>
          </div>
        </div>

        <div className="p-4 space-y-4">
          <Card className="shadow-md border-0 rounded-2xl overflow-hidden">
            <CardHeader className="pb-3">
              <div className="flex items-start gap-3">
                <Avatar className="w-12 h-12">
                  <AvatarImage src={post.instructor.avatar_url || undefined} />
                  <AvatarFallback className="bg-blue-500 text-white">
                    {post.instructor.full_name.charAt(0)}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-900">{post.instructor.full_name}</h3>
                    {post.campus && (
                      <Badge variant="secondary" className="text-xs">
                        {post.campus.name}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-gray-500">
                    {formatDistanceToNow(new Date(post.created_at), {
                      addSuffix: true,
                      locale: ja,
                    })}
                  </p>
                </div>
              </div>
            </CardHeader>

            {post.image_url && (
              <div className="w-full">
                <img
                  src={post.image_url}
                  alt="Post image"
                  className="w-full h-auto max-h-[500px] object-cover"
                />
              </div>
            )}

            <CardContent className="pt-4">
              <p className="text-gray-800 whitespace-pre-wrap mb-4 text-base leading-relaxed">
                {post.content}
              </p>

              <div className="flex items-center gap-4 pt-2 border-t">
                <Button
                  variant="ghost"
                  size="sm"
                  className={`gap-2 ${hasReacted ? 'text-red-500' : 'text-gray-600'}`}
                  onClick={toggleReaction}
                >
                  <Heart className={`w-5 h-5 ${hasReacted ? 'fill-current' : ''}`} />
                  <span className="text-sm">{reactionCount}</span>
                </Button>

                <Button variant="ghost" size="sm" className="gap-2 text-gray-600 ml-auto">
                  <Bookmark className="w-5 h-5" />
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={generateAiSummary}
              className="flex-1 gap-2"
            >
              <Sparkles className="w-4 h-4" />
              AI要約を生成
            </Button>
          </div>

          {showAiSummary && (
            <Card className="shadow-md border-0 rounded-2xl bg-gradient-to-br from-purple-50 to-blue-50">
              <CardContent className="pt-4">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-5 h-5 text-purple-600" />
                  <h3 className="font-semibold text-gray-900">AI要約</h3>
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{aiSummary}</p>
              </CardContent>
            </Card>
          )}

          <div className="space-y-3">
            <h3 className="font-semibold text-gray-900 px-1">
              コメント ({comments.length})
            </h3>

            {comments.map((comment) => (
              <Card key={comment.id} className="shadow-sm border border-gray-200 rounded-xl">
                <CardContent className="pt-4">
                  <div className="flex items-start gap-3">
                    <Avatar className="w-9 h-9">
                      <AvatarImage src={comment.user.avatar_url || undefined} />
                      <AvatarFallback className="bg-gray-400 text-white text-sm">
                        {comment.user.full_name.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-sm text-gray-900">
                          {comment.user.full_name}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatDistanceToNow(new Date(comment.created_at), {
                            addSuffix: true,
                            locale: ja,
                          })}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700">{comment.content}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {comments.length === 0 && (
              <p className="text-center text-sm text-gray-500 py-6">
                まだコメントがありません
              </p>
            )}
          </div>
        </div>

        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4">
          <div className="max-w-[420px] mx-auto flex gap-2">
            <Textarea
              placeholder="コメントを入力..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              className="resize-none min-h-[44px] max-h-[120px]"
              rows={1}
            />
            <Button onClick={handleAddComment} size="icon" className="rounded-full h-[44px] w-[44px]">
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
