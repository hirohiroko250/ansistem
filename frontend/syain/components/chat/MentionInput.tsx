'use client';

import { useState, useRef, useEffect, useCallback, KeyboardEvent, ChangeEvent } from 'react';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import type { MentionableUser } from '@/lib/api/chat';

interface MentionInputProps {
  value: string;
  onChange: (value: string) => void;
  onKeyDown?: (e: KeyboardEvent<HTMLInputElement>) => void;
  mentionableUsers: MentionableUser[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function MentionInput({
  value,
  onChange,
  onKeyDown,
  mentionableUsers,
  placeholder = 'メッセージを入力',
  disabled = false,
  className = '',
}: MentionInputProps) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [filteredUsers, setFilteredUsers] = useState<MentionableUser[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [mentionStartIndex, setMentionStartIndex] = useState(-1);
  const [searchText, setSearchText] = useState('');

  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // @入力を検出してサジェストを表示
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    const cursorPosition = e.target.selectionStart || 0;

    onChange(newValue);

    // @を検出
    const textBeforeCursor = newValue.substring(0, cursorPosition);
    const atIndex = textBeforeCursor.lastIndexOf('@');

    if (atIndex !== -1) {
      // @の前が空白か文字列の先頭かをチェック
      const charBefore = atIndex > 0 ? textBeforeCursor[atIndex - 1] : ' ';
      if (charBefore === ' ' || charBefore === '\n' || atIndex === 0) {
        const searchStr = textBeforeCursor.substring(atIndex + 1);

        // スペースや改行が含まれていないことを確認
        if (!searchStr.includes(' ') && !searchStr.includes('\n')) {
          setMentionStartIndex(atIndex);
          setSearchText(searchStr);

          // ユーザーをフィルタリング
          const filtered = mentionableUsers.filter(user =>
            user.name.toLowerCase().includes(searchStr.toLowerCase()) ||
            user.email.toLowerCase().includes(searchStr.toLowerCase())
          );

          setFilteredUsers(filtered);
          setShowSuggestions(filtered.length > 0);
          setSelectedIndex(0);
          return;
        }
      }
    }

    // サジェストを閉じる
    setShowSuggestions(false);
    setMentionStartIndex(-1);
    setSearchText('');
  };

  // ユーザーを選択してメンションを挿入
  const insertMention = useCallback((user: MentionableUser) => {
    if (mentionStartIndex === -1) return;

    const beforeMention = value.substring(0, mentionStartIndex);
    const afterMention = value.substring(mentionStartIndex + 1 + searchText.length);

    // @[user_id] 形式で挿入（表示用に名前も追加）
    const mentionText = `@[${user.id}]`;
    const newValue = beforeMention + mentionText + ' ' + afterMention;

    onChange(newValue);
    setShowSuggestions(false);
    setMentionStartIndex(-1);
    setSearchText('');

    // フォーカスを維持
    inputRef.current?.focus();
  }, [value, mentionStartIndex, searchText, onChange]);

  // キーボード操作
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (showSuggestions && filteredUsers.length > 0) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev =>
            prev < filteredUsers.length - 1 ? prev + 1 : 0
          );
          return;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev =>
            prev > 0 ? prev - 1 : filteredUsers.length - 1
          );
          return;
        case 'Enter':
          e.preventDefault();
          insertMention(filteredUsers[selectedIndex]);
          return;
        case 'Escape':
          e.preventDefault();
          setShowSuggestions(false);
          return;
        case 'Tab':
          e.preventDefault();
          insertMention(filteredUsers[selectedIndex]);
          return;
      }
    }

    // 親コンポーネントのonKeyDownを呼び出す
    onKeyDown?.(e);
  };

  // 外側クリックでサジェストを閉じる
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 選択されたアイテムをビューに表示
  useEffect(() => {
    if (showSuggestions && suggestionsRef.current) {
      const selectedElement = suggestionsRef.current.children[selectedIndex] as HTMLElement;
      selectedElement?.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex, showSuggestions]);

  return (
    <div className="relative flex-1">
      <Input
        ref={inputRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className={className}
      />

      {/* メンションサジェスト */}
      {showSuggestions && filteredUsers.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute bottom-full mb-1 left-0 right-0 bg-white rounded-lg shadow-lg border border-gray-200 max-h-48 overflow-y-auto z-50"
        >
          {filteredUsers.map((user, index) => (
            <button
              key={user.id}
              onClick={() => insertMention(user)}
              className={`w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-gray-100 transition-colors ${
                index === selectedIndex ? 'bg-blue-50' : ''
              }`}
            >
              <Avatar className="w-8 h-8">
                <AvatarFallback className="bg-blue-100 text-blue-600 text-xs">
                  {user.name.substring(0, 2)}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{user.name}</p>
                <p className="text-xs text-gray-500 truncate">{user.email}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * メンションをハイライト表示するユーティリティ
 * @[user_id] 形式のメンションを @ユーザー名 形式に変換してハイライト
 */
export function formatMessageWithMentions(
  content: string,
  mentions: Array<{ user_id: string; user_name: string }> = []
): React.ReactNode[] {
  if (!mentions || mentions.length === 0) {
    return [content];
  }

  // user_idからuser_nameへのマッピング
  const userMap = new Map(mentions.map(m => [m.user_id, m.user_name]));

  // @[uuid] パターンを検索
  const mentionPattern = /@\[([0-9a-f-]{36})\]/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;

  while ((match = mentionPattern.exec(content)) !== null) {
    // マッチ前のテキスト
    if (match.index > lastIndex) {
      parts.push(content.substring(lastIndex, match.index));
    }

    const userId = match[1];
    const userName = userMap.get(userId);

    if (userName) {
      // メンションをハイライト
      parts.push(
        <span
          key={`mention-${match.index}`}
          className="text-blue-600 font-medium bg-blue-50 px-1 rounded"
        >
          @{userName}
        </span>
      );
    } else {
      // ユーザーが見つからない場合はそのまま表示
      parts.push(match[0]);
    }

    lastIndex = match.index + match[0].length;
  }

  // 残りのテキスト
  if (lastIndex < content.length) {
    parts.push(content.substring(lastIndex));
  }

  return parts.length > 0 ? parts : [content];
}
