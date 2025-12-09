'use client';

import { Heart, MessageCircle, Ticket, AlertCircle, Filter, Star } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { posts } from '@/lib/feed-data';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';

type AnnouncementType = {
  id: number;
  title: string;
  message: string;
  type: 'info' | 'warning' | 'important';
  date: string;
};

const announcements: AnnouncementType[] = [
  {
    id: 1,
    title: '重要なお知らせ',
    message: 'システムメンテナンスのため、1月30日（火）23:00〜翌2:00までサービスを一時停止いたします。',
    type: 'important',
    date: '2025-01-25',
  },
];

export function GuardianFeed() {
  const router = useRouter();
  const [likedPosts, setLikedPosts] = useState<number[]>([]);
  const [showAllBrands, setShowAllBrands] = useState(false);
  const [ratings, setRatings] = useState<{ [key: number]: number }>({});

  const contractedBrands = ['イングリッシュスクール○○', 'OZA運営'];

  const filteredPosts = posts;

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

  const handleLike = (postId: number) => {
    if (likedPosts.includes(postId)) {
      setLikedPosts(likedPosts.filter((id) => id !== postId));
    } else {
      setLikedPosts([...likedPosts, postId]);
    }
  };

  const handleTicketPurchase = (postId: number) => {
    router.push('/ticket-purchase');
  };

  const handleRating = (postId: number, rating: number) => {
    setRatings(prev => ({ ...prev, [postId]: rating }));
  };

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

        <div className="space-y-4 py-4">
          {filteredPosts.map((post) => (
            <Card key={post.id} className="rounded-none border-x-0 shadow-none">
              <CardContent className="p-0">
                <div className="px-4 py-3 flex items-center gap-3">
                  <Avatar>
                    <AvatarFallback className="bg-blue-100 text-blue-600 font-semibold">
                      {post.avatar}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-800">{post.user}</p>
                    <p className="text-xs text-gray-500">{post.timestamp}</p>
                  </div>
                  {post.type && (
                    <Badge
                      className={
                        post.type === 'イベント'
                          ? 'bg-purple-500 text-white'
                          : post.type === 'お知らせ'
                            ? 'bg-amber-500 text-white'
                            : 'bg-blue-500 text-white'
                      }
                    >
                      {post.type}
                    </Badge>
                  )}
                </div>

                <img
                  src={post.image}
                  alt="Post"
                  className="w-full aspect-square object-cover"
                />

                <div className="px-4 py-3">
                  <div className="flex items-center gap-4 mb-3">
                    <button
                      onClick={() => handleLike(post.id)}
                      className="hover:opacity-70 transition-opacity"
                    >
                      <Heart
                        className={`h-6 w-6 ${likedPosts.includes(post.id)
                            ? 'fill-red-500 text-red-500'
                            : 'text-gray-700'
                          }`}
                      />
                    </button>
                    <button
                      onClick={() => router.push(`/chat/saved-${post.id}`)}
                      className="hover:opacity-70 transition-opacity"
                    >
                      <MessageCircle className="h-6 w-6 text-gray-700" />
                    </button>
                    {post.type === 'イベント' && (
                      <button
                        onClick={() => handleTicketPurchase(post.id)}
                        className="hover:opacity-70 transition-opacity ml-auto"
                      >
                        <Ticket className="h-6 w-6 text-purple-600" />
                      </button>
                    )}
                  </div>

                  <p className="font-semibold text-sm text-gray-800 mb-1">
                    {post.likes + (likedPosts.includes(post.id) ? 1 : 0)}件のいいね
                  </p>
                  <p className="text-sm text-gray-800 mb-3">
                    <span className="font-semibold mr-2">{post.user}</span>
                    {post.caption}
                  </p>

                  <div className="flex items-center gap-1 pt-2 border-t">
                    <span className="text-xs text-gray-600 mr-2">評価:</span>
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        onClick={() => handleRating(post.id, star)}
                        className="hover:scale-110 transition-transform"
                      >
                        <Star
                          className={`h-5 w-5 ${ratings[post.id] >= star
                              ? 'fill-yellow-400 text-yellow-400'
                              : 'text-gray-300'
                            }`}
                        />
                      </button>
                    ))}
                    {ratings[post.id] && (
                      <span className="text-xs text-gray-600 ml-2">
                        {ratings[post.id]}.0
                      </span>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </>
  );
}
