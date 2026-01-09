'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import {
  Plus,
  Trash2,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Bold,
  Type
} from 'lucide-react';
import { TextOverlay, DEFAULT_TEXT_OVERLAY } from './types';

interface TextOverlayToolProps {
  overlays: TextOverlay[];
  selectedId: string | null;
  onAdd: () => void;
  onUpdate: (id: string, updates: Partial<TextOverlay>) => void;
  onRemove: (id: string) => void;
  onSelect: (id: string | null) => void;
}

export function TextOverlayTool({
  overlays,
  selectedId,
  onAdd,
  onUpdate,
  onRemove,
  onSelect,
}: TextOverlayToolProps) {
  const selectedOverlay = overlays.find(o => o.id === selectedId);

  return (
    <div className="space-y-4">
      {/* Add Text Button */}
      <Button
        variant="outline"
        size="sm"
        onClick={onAdd}
        className="w-full gap-2"
      >
        <Plus className="h-4 w-4" />
        テキストを追加
      </Button>

      {/* Text List */}
      {overlays.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-gray-500">テキスト一覧（クリックで選択）</p>
          <div className="space-y-1">
            {overlays.map((overlay) => (
              <div
                key={overlay.id}
                onClick={() => onSelect(overlay.id)}
                className={`
                  flex items-center justify-between p-2 rounded cursor-pointer
                  ${selectedId === overlay.id
                    ? 'bg-blue-50 border border-blue-200'
                    : 'bg-gray-50 hover:bg-gray-100'
                  }
                `}
              >
                <div className="flex items-center gap-2 truncate">
                  <Type className="h-4 w-4 text-gray-400 shrink-0" />
                  <span className="text-sm truncate">{overlay.text || '(空)'}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove(overlay.id);
                  }}
                  className="h-6 w-6 p-0 text-red-500 hover:text-red-700"
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Selected Text Editor */}
      {selectedOverlay && (
        <div className="space-y-4 pt-4 border-t">
          <p className="text-sm font-medium">テキスト編集</p>

          {/* Text Input */}
          <div>
            <Input
              value={selectedOverlay.text}
              onChange={(e) => onUpdate(selectedOverlay.id, { text: e.target.value })}
              placeholder="テキストを入力"
            />
          </div>

          {/* Font Size */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm">サイズ</span>
              <span className="text-sm text-gray-500">{selectedOverlay.fontSize}px</span>
            </div>
            <Slider
              value={[selectedOverlay.fontSize]}
              onValueChange={([value]) => onUpdate(selectedOverlay.id, { fontSize: value })}
              min={12}
              max={72}
              step={1}
            />
          </div>

          {/* Color */}
          <div className="flex items-center justify-between">
            <span className="text-sm">色</span>
            <input
              type="color"
              value={selectedOverlay.color}
              onChange={(e) => onUpdate(selectedOverlay.id, { color: e.target.value })}
              className="w-8 h-8 rounded cursor-pointer border"
            />
          </div>

          {/* Alignment */}
          <div className="flex items-center justify-between">
            <span className="text-sm">配置</span>
            <div className="flex gap-1">
              <Button
                variant={selectedOverlay.textAlign === 'left' ? 'default' : 'outline'}
                size="sm"
                onClick={() => onUpdate(selectedOverlay.id, { textAlign: 'left' })}
                className="h-8 w-8 p-0"
              >
                <AlignLeft className="h-4 w-4" />
              </Button>
              <Button
                variant={selectedOverlay.textAlign === 'center' ? 'default' : 'outline'}
                size="sm"
                onClick={() => onUpdate(selectedOverlay.id, { textAlign: 'center' })}
                className="h-8 w-8 p-0"
              >
                <AlignCenter className="h-4 w-4" />
              </Button>
              <Button
                variant={selectedOverlay.textAlign === 'right' ? 'default' : 'outline'}
                size="sm"
                onClick={() => onUpdate(selectedOverlay.id, { textAlign: 'right' })}
                className="h-8 w-8 p-0"
              >
                <AlignRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Bold */}
          <div className="flex items-center justify-between">
            <span className="text-sm">太字</span>
            <Button
              variant={selectedOverlay.fontWeight === 'bold' ? 'default' : 'outline'}
              size="sm"
              onClick={() => onUpdate(selectedOverlay.id, {
                fontWeight: selectedOverlay.fontWeight === 'bold' ? 'normal' : 'bold'
              })}
              className="h-8 w-8 p-0"
            >
              <Bold className="h-4 w-4" />
            </Button>
          </div>

          <p className="text-xs text-gray-400 text-center">
            プレビュー上でドラッグして位置を調整できます
          </p>
        </div>
      )}

      {overlays.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-4">
          テキストを追加するとここに表示されます
        </p>
      )}
    </div>
  );
}
