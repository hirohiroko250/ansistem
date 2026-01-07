'use client';

import { useState, useRef, useEffect } from 'react';
import { Smile } from 'lucide-react';

// よく使う絵文字リスト
const EMOJI_LIST = [
  // リアクション
  { emoji: '👍', label: 'いいね' },
  { emoji: '❤️', label: 'ハート' },
  { emoji: '😊', label: '笑顔' },
  { emoji: '😂', label: '笑い' },
  { emoji: '🎉', label: '祝' },
  { emoji: '👏', label: '拍手' },
  { emoji: '🙏', label: 'お願い' },
  { emoji: '✨', label: 'キラキラ' },
  // 感情
  { emoji: '😀', label: 'にっこり' },
  { emoji: '😍', label: '目がハート' },
  { emoji: '🤔', label: '考え中' },
  { emoji: '😢', label: '泣き' },
  { emoji: '😮', label: '驚き' },
  { emoji: '😅', label: '汗' },
  { emoji: '🤗', label: 'ハグ' },
  { emoji: '💪', label: '筋肉' },
  // ビジネス
  { emoji: '✅', label: '完了' },
  { emoji: '📝', label: 'メモ' },
  { emoji: '💡', label: 'アイデア' },
  { emoji: '🔥', label: '炎' },
  { emoji: '⭐', label: '星' },
  { emoji: '💯', label: '100点' },
  { emoji: '🚀', label: 'ロケット' },
  { emoji: '👀', label: '見てる' },
];

interface EmojiPickerProps {
  onSelect: (emoji: string) => void;
  onClose: () => void;
}

export function EmojiPicker({ onSelect, onClose }: EmojiPickerProps) {
  const ref = useRef<HTMLDivElement>(null);

  // 外側クリックで閉じる
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="absolute bottom-full mb-2 left-0 bg-white rounded-lg shadow-lg border border-gray-200 p-2 z-50"
    >
      <div className="grid grid-cols-8 gap-1">
        {EMOJI_LIST.map(({ emoji, label }) => (
          <button
            key={emoji}
            onClick={() => {
              onSelect(emoji);
              onClose();
            }}
            title={label}
            className="w-8 h-8 flex items-center justify-center text-xl hover:bg-gray-100 rounded transition-colors"
          >
            {emoji}
          </button>
        ))}
      </div>
    </div>
  );
}

interface EmojiButtonProps {
  onSelect: (emoji: string) => void;
}

export function EmojiButton({ onSelect }: EmojiButtonProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-1 bg-white/80 hover:bg-white rounded-full shadow-sm transition-colors"
        title="リアクション"
      >
        <Smile className="w-4 h-4 text-gray-600" />
      </button>

      {isOpen && (
        <EmojiPicker
          onSelect={onSelect}
          onClose={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}
