'use client';

import { useState, useEffect } from 'react';
import { Search, Bot, MessageCircle, Pin, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import Link from 'next/link';
import { getChannels, getActiveBotConfig, type BotConfig } from '@/lib/api/chat';
import type { Channel } from '@/lib/api/types';

// デフォルトのAIチャットボット設定
const DEFAULT_BOT: BotConfig = {
  id: 'ai-assistant',
  name: 'AIアシスタント',
  welcomeMessage: 'いつでもご質問ください！',
  botType: 'GENERAL',
  aiEnabled: false,
};

// タイムスタンプをフォーマット
function formatTimestamp(dateString?: string): string {
  if (!dateString) return '';

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffHours < 1) {
    return '今';
  } else if (diffHours < 24) {
    return `${diffHours}時間前`;
  } else if (diffDays === 1) {
    return '昨日';
  } else if (diffDays < 7) {
    return `${diffDays}日前`;
  } else {
    return date.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' });
  }
}

// チャンネル名からアバターテキストを生成
function getAvatarText(name?: string): string {
  if (!name) return '??';
  return name.substring(0, 2);
}

export default function ChatListPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [channels, setChannels] = useState<Channel[]>([]);
  const [botConfig, setBotConfig] = useState<BotConfig>(DEFAULT_BOT);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // チャンネル一覧とボット設定を取得
  useEffect(() => {
    async function fetchData() {
      try {
        setIsLoading(true);
        setError(null);

        // チャンネルとボット設定を並行取得
        const [channelsData, botData] = await Promise.all([
          getChannels().catch(() => []),
          getActiveBotConfig().catch(() => DEFAULT_BOT),
        ]);

        setChannels(Array.isArray(channelsData) ? channelsData : []);
        setBotConfig(botData || DEFAULT_BOT);
      } catch (err) {
        console.error('Failed to fetch data:', err);
        setError('データの取得に失敗しました');
        setChannels([]);
      } finally {
        setIsLoading(false);
      }
    }

    fetchData();
  }, []);

  // 検索フィルタリング（通常のチャンネルのみ）
  const filteredChats = (channels || []).filter((channel) => {
    const name = channel.name || '';
    const lastMessage = channel.lastMessage?.content || '';
    return (
      name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lastMessage.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  // AIチャットボットが検索に一致するか
  const showAiBot = !searchQuery ||
    botConfig.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    botConfig.welcomeMessage.toLowerCase().includes(searchQuery.toLowerCase());

  // ローディング表示
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 py-3">
            <h1 className="text-2xl font-bold text-blue-600 mb-3">チャット</h1>
          </div>
        </header>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
        <BottomTabBar />
      </div>
    );
  }

  // エラー表示
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <header className="sticky top-0 z-40 bg-white shadow-sm">
          <div className="max-w-[390px] mx-auto px-4 py-3">
            <h1 className="text-2xl font-bold text-blue-600 mb-3">チャット</h1>
          </div>
        </header>
        <div className="flex flex-col items-center justify-center h-64 px-4">
          <p className="text-red-600 text-center">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg"
          >
            再読み込み
          </button>
        </div>
        <BottomTabBar />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 py-3">
          <h1 className="text-2xl font-bold text-blue-600 mb-3">チャット</h1>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <Input
              placeholder="チャットを検索"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 rounded-full"
            />
          </div>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto pb-24">
        {/* ピン留め - AIチャットボット（常に表示） */}
        {showAiBot && (
          <div className="mb-2">
            <div className="px-4 py-2 flex items-center gap-2">
              <Pin className="h-4 w-4 text-gray-600" />
              <h2 className="text-sm font-semibold text-gray-600">ピン留め</h2>
            </div>
            <Link href={`/chat/${botConfig.id}`}>
              <Card className="rounded-none border-x-0 border-t-0 shadow-none hover:bg-gray-50 transition-colors cursor-pointer">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <Avatar className="bg-gradient-to-br from-blue-500 to-purple-600">
                        <AvatarFallback className="text-white">
                          <Bot className="h-5 w-5" />
                        </AvatarFallback>
                      </Avatar>
                      <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <h3 className="font-semibold text-gray-800 truncate flex items-center gap-2">
                          {botConfig.name}
                          <Badge className="bg-gradient-to-r from-blue-500 to-purple-600 text-white text-xs">
                            AI
                          </Badge>
                        </h3>
                      </div>
                      <div className="flex items-center justify-between">
                        <p className="text-sm text-gray-600 truncate">
                          {botConfig.welcomeMessage}
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          </div>
        )}

        {/* 通常チャンネル */}
        {filteredChats.length > 0 && (
          <div>
            <div className="px-4 py-2">
              <h2 className="text-sm font-semibold text-gray-600">すべてのチャット</h2>
            </div>
            {filteredChats.map((channel) => (
              <Link key={channel.id} href={`/chat/${channel.id}`}>
                <Card className="rounded-none border-x-0 border-t-0 shadow-none hover:bg-gray-50 transition-colors cursor-pointer">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <Avatar className="bg-blue-100">
                          <AvatarFallback className="text-blue-600 font-semibold">
                            {getAvatarText(channel.name)}
                          </AvatarFallback>
                        </Avatar>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <h3 className="font-semibold text-gray-800 truncate">
                            {channel.name || 'チャット'}
                          </h3>
                          <span className="text-xs text-gray-500 shrink-0 ml-2">
                            {formatTimestamp(channel.lastMessage?.createdAt || channel.updatedAt)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <p className="text-sm text-gray-600 truncate">
                            {channel.lastMessage?.content || 'メッセージはありません'}
                          </p>
                          {channel.unreadCount > 0 && (
                            <Badge className="bg-blue-600 text-white shrink-0 ml-2">
                              {channel.unreadCount}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}

        {/* チャンネルがない場合 */}
        {!showAiBot && filteredChats.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 px-4">
            <MessageCircle className="h-12 w-12 text-gray-300 mb-4" />
            <p className="text-gray-500 text-center">検索結果がありません</p>
          </div>
        )}
      </main>

      <BottomTabBar />
    </div>
  );
}
