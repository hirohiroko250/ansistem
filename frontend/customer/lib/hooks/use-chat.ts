'use client';

/**
 * useChat - チャット関連フック
 *
 * チャンネル一覧、ボット設定を取得するReact Queryフック
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getChannels,
  getActiveBotConfig,
  archiveChannel,
  createChannel,
  sendMessage,
  getMessages,
  type BotConfig,
  type CreateChannelRequest,
} from '@/lib/api/chat';
import type { Channel, Message, SendMessageRequest } from '@/lib/api/types';

// クエリキー
export const chatKeys = {
  all: ['chat'] as const,
  channels: () => [...chatKeys.all, 'channels'] as const,
  messages: (channelId: string) => [...chatKeys.all, 'messages', channelId] as const,
  botConfig: () => [...chatKeys.all, 'botConfig'] as const,
};

// デフォルトのAIチャットボット設定
const DEFAULT_BOT: BotConfig = {
  id: 'ai-assistant',
  name: 'AIアシスタント',
  welcomeMessage: '体験申込・振替・料金など、何でもお気軽に！',
  botType: 'GENERAL',
  aiEnabled: false,
};

/**
 * チャンネル一覧を取得
 */
export function useChannels() {
  return useQuery({
    queryKey: chatKeys.channels(),
    queryFn: async () => {
      const channels = await getChannels().catch(() => [] as Channel[]);
      return Array.isArray(channels) ? channels : [];
    },
    enabled: !!getAccessToken(),
    staleTime: 30 * 1000, // 30秒（チャットは頻繁に更新される）
    refetchOnWindowFocus: true, // 画面に戻った時に再取得
  });
}

/**
 * ボット設定を取得
 */
export function useBotConfig() {
  return useQuery({
    queryKey: chatKeys.botConfig(),
    queryFn: async () => {
      const config = await getActiveBotConfig().catch(() => DEFAULT_BOT);
      return config || DEFAULT_BOT;
    },
    enabled: !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分（ボット設定は頻繁に変わらない）
  });
}

/**
 * チャンネルをアーカイブ（削除）
 */
export function useArchiveChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (channelId: string) => archiveChannel(channelId),
    onSuccess: (_, channelId) => {
      // キャッシュから該当チャンネルを削除
      queryClient.setQueryData<Channel[]>(chatKeys.channels(), (old) =>
        old ? old.filter((ch) => ch.id !== channelId) : []
      );
    },
    onError: (error) => {
      console.error('Failed to archive channel:', error);
    },
  });
}

/**
 * チャンネルを作成
 */
export function useCreateChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateChannelRequest) => createChannel(data),
    onSuccess: (newChannel) => {
      // チャンネル一覧にキャッシュを追加
      queryClient.setQueryData<Channel[]>(chatKeys.channels(), (old) =>
        old ? [newChannel, ...old] : [newChannel]
      );
    },
  });
}

/**
 * メッセージを送信
 */
export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SendMessageRequest) => sendMessage(data),
    onSuccess: (newMessage, variables) => {
      // メッセージ一覧キャッシュを更新（楽観的更新の置き換え用）
      queryClient.invalidateQueries({ queryKey: chatKeys.messages(variables.channelId) });
    },
  });
}

/**
 * チャンネルのメッセージを取得
 */
export function useChannelMessages(channelId: string | undefined) {
  return useQuery({
    queryKey: chatKeys.messages(channelId || ''),
    queryFn: async () => {
      if (!channelId) throw new Error('Channel ID is required');
      const response = await getMessages(channelId);
      return response.results || [];
    },
    enabled: !!channelId && !!getAccessToken(),
    staleTime: 10 * 1000, // 10秒（チャットは頻繁に更新される）
  });
}

/**
 * チャンネルキャッシュを無効化
 */
export function useInvalidateChannels() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: chatKeys.channels() });
  };
}

/**
 * デフォルトボット設定を取得
 */
export function getDefaultBotConfig(): BotConfig {
  return DEFAULT_BOT;
}

// 型を再エクスポート
export type { BotConfig, CreateChannelRequest } from '@/lib/api/chat';
export type { Channel, Message, SendMessageRequest } from '@/lib/api/types';
