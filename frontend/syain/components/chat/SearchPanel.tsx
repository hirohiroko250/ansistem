'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { X, Search, Calendar, Loader2, MessageCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import {
  searchMessages,
  parseHighlight,
  type SearchResult,
  type SearchParams,
  type Channel,
  type StaffChannel,
} from '@/lib/api/chat';

interface SearchPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onResultClick?: (result: SearchResult, channelId: string) => void;
  channels?: (Channel | StaffChannel)[];
  currentChannelId?: string | null;
}

export function SearchPanel({
  isOpen,
  onClose,
  onResultClick,
  channels = [],
  currentChannelId,
}: SearchPanelProps) {
  const [query, setQuery] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [searchInCurrentChannel, setSearchInCurrentChannel] = useState(false);

  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // モーダルが開いたときに入力欄にフォーカス
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // 検索実行
  const handleSearch = useCallback(async (newPage: number = 1) => {
    if (!query.trim() || query.trim().length < 2) {
      setError('2文字以上入力してください');
      return;
    }

    setError(null);
    setIsSearching(true);

    try {
      const params: SearchParams = {
        query: query.trim(),
        page: newPage,
        pageSize: 20,
      };

      if (searchInCurrentChannel && currentChannelId) {
        params.channelId = currentChannelId;
      }

      if (dateFrom) params.dateFrom = dateFrom;
      if (dateTo) params.dateTo = dateTo;

      const response = await searchMessages(params);

      if (newPage === 1) {
        setResults(response.results);
      } else {
        setResults(prev => [...prev, ...response.results]);
      }

      setTotalCount(response.count);
      setHasMore(!!response.next);
      setPage(newPage);
    } catch (err: any) {
      console.error('Search failed:', err);
      setError(err.message || '検索に失敗しました');
    } finally {
      setIsSearching(false);
    }
  }, [query, dateFrom, dateTo, searchInCurrentChannel, currentChannelId]);

  // Enterキーで検索
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSearch(1);
    }
  };

  // 検索結果をクリック
  const handleResultClick = (result: SearchResult) => {
    onResultClick?.(result, result.channelId || result.channel);
    onClose();
  };

  // さらに読み込む
  const handleLoadMore = () => {
    if (hasMore && !isSearching) {
      handleSearch(page + 1);
    }
  };

  // フィルターをリセット
  const handleReset = () => {
    setQuery('');
    setDateFrom('');
    setDateTo('');
    setSearchInCurrentChannel(false);
    setResults([]);
    setTotalCount(0);
    setError(null);
  };

  // チャンネル名を取得
  const getChannelName = (channelId: string) => {
    const channel = channels.find(ch => ch.id === channelId);
    if (channel) {
      if ('guardian' in channel && channel.guardian?.fullName) {
        return channel.guardian.fullName;
      }
      return channel.name;
    }
    return 'Unknown';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col mx-4">
        {/* ヘッダー */}
        <div className="flex items-center gap-3 px-4 py-3 border-b">
          <Search className="w-5 h-5 text-gray-400" />
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="メッセージを検索..."
            className="flex-1 border-0 focus-visible:ring-0 text-lg"
          />
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* フィルター */}
        <div className="px-4 py-2 border-b bg-gray-50">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
          >
            <Calendar className="w-4 h-4" />
            フィルター
            {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showFilters && (
            <div className="mt-3 space-y-3">
              {/* 日付範囲 */}
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600 w-16">期間:</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="px-2 py-1 border rounded text-sm"
                />
                <span className="text-gray-400">〜</span>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="px-2 py-1 border rounded text-sm"
                />
              </div>

              {/* 現在のチャンネルのみ */}
              {currentChannelId && (
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={searchInCurrentChannel}
                    onChange={(e) => setSearchInCurrentChannel(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-gray-600">現在のチャンネルのみ検索</span>
                </label>
              )}

              {/* リセットボタン */}
              <div className="flex justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleReset}
                >
                  リセット
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* 検索ボタン */}
        <div className="px-4 py-2 border-b">
          <Button
            onClick={() => handleSearch(1)}
            disabled={isSearching || query.trim().length < 2}
            className="w-full bg-blue-600 hover:bg-blue-700"
          >
            {isSearching ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                検索中...
              </>
            ) : (
              <>
                <Search className="w-4 h-4 mr-2" />
                検索
              </>
            )}
          </Button>
        </div>

        {/* エラー */}
        {error && (
          <div className="px-4 py-2 bg-red-50 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* 検索結果 */}
        <div ref={resultsRef} className="flex-1 overflow-y-auto">
          {results.length === 0 && !isSearching && query && (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <MessageCircle className="w-12 h-12 text-gray-300 mb-3" />
              <p>検索結果がありません</p>
            </div>
          )}

          {results.length > 0 && (
            <>
              <div className="px-4 py-2 text-sm text-gray-500 bg-gray-50 border-b">
                {totalCount}件の結果
              </div>

              <div className="divide-y">
                {results.map((result) => (
                  <button
                    key={result.id}
                    onClick={() => handleResultClick(result)}
                    className="w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                  >
                    {/* チャンネル名と日時 */}
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-blue-600 font-medium">
                        #{getChannelName(result.channelId || result.channel)}
                      </span>
                      <span className="text-xs text-gray-400">
                        {format(new Date(result.createdAt), 'yyyy/MM/dd HH:mm', { locale: ja })}
                      </span>
                    </div>

                    {/* 送信者名 */}
                    <div className="text-sm text-gray-600 mb-1">
                      {result.senderName}
                    </div>

                    {/* ハイライト付きメッセージ */}
                    <div
                      className="text-sm text-gray-800"
                      dangerouslySetInnerHTML={{
                        __html: parseHighlight(result.highlight || result.content)
                      }}
                    />
                  </button>
                ))}
              </div>

              {/* さらに読み込む */}
              {hasMore && (
                <div className="p-4 text-center">
                  <Button
                    variant="outline"
                    onClick={handleLoadMore}
                    disabled={isSearching}
                  >
                    {isSearching ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        読み込み中...
                      </>
                    ) : (
                      'さらに表示'
                    )}
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
