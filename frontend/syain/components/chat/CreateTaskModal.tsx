'use client';

import { useState } from 'react';
import { X, ClipboardList, Calendar, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { createTaskFromMessage, type Message } from '@/lib/api/chat';

interface CreateTaskModalProps {
  message: Message;
  channelId: string;
  onClose: () => void;
  onSuccess?: (task: { id: string; title: string }) => void;
}

const PRIORITY_OPTIONS = [
  { value: 'low', label: '低', color: 'bg-gray-100 text-gray-700' },
  { value: 'normal', label: '通常', color: 'bg-blue-100 text-blue-700' },
  { value: 'high', label: '高', color: 'bg-orange-100 text-orange-700' },
  { value: 'urgent', label: '緊急', color: 'bg-red-100 text-red-700' },
] as const;

export function CreateTaskModal({
  message,
  channelId,
  onClose,
  onSuccess,
}: CreateTaskModalProps) {
  const [title, setTitle] = useState(message.content.slice(0, 100));
  const [description, setDescription] = useState(message.content);
  const [priority, setPriority] = useState<'low' | 'normal' | 'high' | 'urgent'>('normal');
  const [dueDate, setDueDate] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!title.trim()) {
      setError('タイトルを入力してください');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const task = await createTaskFromMessage({
        messageId: message.id,
        channelId,
        title: title.trim(),
        description,
        priority,
        dueDate: dueDate || undefined,
      });
      onSuccess?.(task);
      onClose();
    } catch (err) {
      console.error('Failed to create task:', err);
      setError('タスクの作成に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
          <div className="flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-blue-600" />
            <h2 className="font-bold text-gray-900">タスクを作成</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-200 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 space-y-4 overflow-y-auto">
          {/* エラー表示 */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          {/* タイトル */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              タイトル <span className="text-red-500">*</span>
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="タスクのタイトル"
              className="w-full"
            />
          </div>

          {/* 説明 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              説明
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="タスクの詳細説明"
              className="w-full p-2 border rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={4}
            />
          </div>

          {/* 優先度 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              優先度
            </label>
            <div className="flex gap-2">
              {PRIORITY_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setPriority(option.value)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                    priority === option.value
                      ? `${option.color} ring-2 ring-offset-1 ring-blue-400`
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* 期限 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <Calendar className="w-4 h-4 inline mr-1" />
              期限日
            </label>
            <Input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="w-full"
            />
          </div>

          {/* 元メッセージ */}
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">元メッセージ:</p>
            <p className="text-sm text-gray-700 line-clamp-3">{message.content}</p>
            <p className="text-xs text-gray-400 mt-1">
              {message.senderName} - {new Date(message.createdAt).toLocaleString('ja-JP')}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-4 py-3 border-t bg-gray-50">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isSubmitting}
          >
            キャンセル
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !title.trim()}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isSubmitting ? '作成中...' : 'タスクを作成'}
          </Button>
        </div>
      </div>
    </div>
  );
}
