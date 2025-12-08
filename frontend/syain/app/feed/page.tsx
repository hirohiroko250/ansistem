'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAuth } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { BottomNav } from '@/components/bottom-nav';
import { Heart, MessageCircle, Bookmark, Plus, Image as ImageIcon, Sparkles } from 'lucide-react';
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
  reactions: { count: number }[];
  comments: { count: number }[];
  user_reaction: any[];
}

interface Campus {
  id: string;
  name: string;
}

export default function FeedPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [posts, setPosts] = useState<Post[]>([]);
  const [campuses, setCampuses] = useState<Campus[]>([]);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newPost, setNewPost] = useState({
    content: '',
    campus_id: '',
    image_url: '',
  });

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    loadPosts();
    loadCampuses();
  }, [user, loading]);

  const loadPosts = async () => {
    if (!user) return;

    const { data, error } = await supabase
      .from('posts')
      .select(`
        id,
        content,
        image_url,
        video_url,
        created_at,
        instructor:profiles!instructor_id(full_name, avatar_url),
        campus:campuses(name),
        reactions:post_reactions(count),
        comments:post_comments(count),
        user_reaction:post_reactions!post_reactions_post_id_fkey(id, reaction_type)
      `)
      .order('created_at', { ascending: false });

    if (data) {
      setPosts(data as any);
    }
  };

  const loadCampuses = async () => {
    const { data } = await supabase
      .from('campuses')
      .select('id, name')
      .order('name');

    if (data) {
      setCampuses(data);
    }
  };

  const handleCreatePost = async () => {
    if (!user || !newPost.content.trim()) return;

    const { error } = await supabase
      .from('posts')
      .insert({
        instructor_id: user.id,
        campus_id: newPost.campus_id || null,
        content: newPost.content,
        image_url: newPost.image_url || null,
      });

    if (!error) {
      setNewPost({ content: '', campus_id: '', image_url: '' });
      setIsCreateOpen(false);
      loadPosts();
    }
  };

  const toggleReaction = async (postId: string, hasReacted: boolean) => {
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

    loadPosts();
  };

  if (loading) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white" />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white pb-20">
      <div className="max-w-[420px] mx-auto">
        <div className="bg-white/90 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4 flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">フィード</h1>
            <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
              <DialogTrigger asChild>
                <Button size="sm" className="rounded-full">
                  <Plus className="w-4 h-4 mr-1" />
                  投稿
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-[380px] rounded-2xl">
                <DialogHeader>
                  <DialogTitle>新しい投稿</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label>本文</Label>
                    <Textarea
                      placeholder="今日の授業の様子や、役立つ情報を共有しましょう..."
                      value={newPost.content}
                      onChange={(e) => setNewPost({ ...newPost, content: e.target.value })}
                      className="min-h-[120px] resize-none"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>校舎</Label>
                    <Select
                      value={newPost.campus_id}
                      onValueChange={(value) => setNewPost({ ...newPost, campus_id: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="校舎を選択（任意）" />
                      </SelectTrigger>
                      <SelectContent>
                        {campuses.map((campus) => (
                          <SelectItem key={campus.id} value={campus.id}>
                            {campus.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>画像URL（任意）</Label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="https://..."
                        value={newPost.image_url}
                        onChange={(e) => setNewPost({ ...newPost, image_url: e.target.value })}
                        className="flex-1 px-3 py-2 border rounded-lg text-sm"
                      />
                      <Button size="icon" variant="outline">
                        <ImageIcon className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                  <Button onClick={handleCreatePost} className="w-full" size="lg">
                    投稿する
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {posts.map((post) => {
            const reactionCount = post.reactions?.[0]?.count || 0;
            const commentCount = post.comments?.[0]?.count || 0;
            const hasReacted = post.user_reaction && post.user_reaction.length > 0;

            return (
              <Card
                key={post.id}
                className="shadow-md border-0 rounded-2xl overflow-hidden hover:shadow-lg transition-shadow"
              >
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
                      className="w-full h-auto max-h-[400px] object-cover"
                    />
                  </div>
                )}

                <CardContent className="pt-4">
                  <p className="text-gray-800 whitespace-pre-wrap mb-4">{post.content}</p>

                  <div className="flex items-center gap-4 pt-2 border-t">
                    <Button
                      variant="ghost"
                      size="sm"
                      className={`gap-2 ${hasReacted ? 'text-red-500' : 'text-gray-600'}`}
                      onClick={() => toggleReaction(post.id, hasReacted)}
                    >
                      <Heart className={`w-5 h-5 ${hasReacted ? 'fill-current' : ''}`} />
                      <span className="text-sm">{reactionCount}</span>
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      className="gap-2 text-gray-600"
                      onClick={() => router.push(`/feed/${post.id}`)}
                    >
                      <MessageCircle className="w-5 h-5" />
                      <span className="text-sm">{commentCount}</span>
                    </Button>

                    <Button variant="ghost" size="sm" className="gap-2 text-gray-600 ml-auto">
                      <Bookmark className="w-5 h-5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}

          {posts.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500 mb-4">まだ投稿がありません</p>
              <Button onClick={() => setIsCreateOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                最初の投稿をする
              </Button>
            </div>
          )}
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
