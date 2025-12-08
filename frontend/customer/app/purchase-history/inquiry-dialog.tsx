'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { X } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

type InquiryDialogProps = {
  open: boolean;
  onClose: () => void;
  brandName: string;
  itemDescription: string;
  itemAmount: number;
};

export function InquiryDialog({ open, onClose, brandName, itemDescription, itemAmount }: InquiryDialogProps) {
  const router = useRouter();
  const [contactMethod, setContactMethod] = useState('chat');
  const [availableTime, setAvailableTime] = useState('');
  const [inquiry, setInquiry] = useState('');

  const handleSubmit = () => {
    const message = `【明細お問い合わせ】\n\n1. ${brandName}\n   ${itemDescription}\n   ¥${itemAmount.toLocaleString()}\n\n可能な連絡方法: ${contactMethod === 'chat' ? 'チャット' : contactMethod === 'phone' ? '電話' : 'チャット、電話'}${availableTime ? `\n\n電話可能時間: ${availableTime}` : ''}\n\n明細の疑問点:\n${inquiry}`;

    // 新規チャット（事務局問い合わせ）ページに遷移
    router.push(`/chat/new?message=${encodeURIComponent(message)}`);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-[380px] max-h-[90vh] overflow-y-auto p-0">
        <DialogHeader className="px-4 pt-4 pb-2">
          <DialogTitle className="text-lg font-bold">明細お問い合わせ</DialogTitle>
          <p className="text-xs text-amber-600 font-semibold mt-2">
            ブランドと、明細の内容＆金額が必要
          </p>
        </DialogHeader>

        <div className="px-4 pb-4 space-y-4">
          <div className="border-l-4 border-blue-600 bg-blue-50 p-3 rounded">
            <div className="text-xs font-bold text-blue-900 mb-2">1. {brandName}</div>
            <div className="text-xs text-gray-700 mb-1">{itemDescription}</div>
            <div className="text-sm font-bold text-blue-900">¥{itemAmount.toLocaleString()}</div>
          </div>

          <div>
            <Label className="text-xs font-medium text-gray-700 mb-2 block">
              可能な連絡方法
              <span className="text-amber-600 ml-1">→デフォルト「チャット」、電話</span>
            </Label>
            <select
              value={contactMethod}
              onChange={(e) => setContactMethod(e.target.value)}
              className="w-full h-9 px-2 rounded-md border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="chat">チャット</option>
              <option value="phone">電話</option>
              <option value="both">チャット、電話</option>
            </select>
          </div>

          {(contactMethod === 'phone' || contactMethod === 'both') && (
            <div>
              <Label className="text-xs font-medium text-gray-700 mb-2 block">
                電話可能時間
                <span className="text-amber-600 ml-1">→電話の場合のみ、表示</span>
              </Label>
              <select
                value={availableTime}
                onChange={(e) => setAvailableTime(e.target.value)}
                className="w-full h-9 px-2 rounded-md border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">選択してください</option>
                <option value="平日 9:00-12:00">平日 9:00-12:00</option>
                <option value="平日 12:00-15:00">平日 12:00-15:00</option>
                <option value="平日 15:00-18:00">平日 15:00-18:00</option>
                <option value="平日 18:00-21:00">平日 18:00-21:00</option>
                <option value="土日 9:00-12:00">土日 9:00-12:00</option>
                <option value="土日 12:00-15:00">土日 12:00-15:00</option>
                <option value="土日 15:00-18:00">土日 15:00-18:00</option>
                <option value="いつでも可">いつでも可</option>
              </select>
            </div>
          )}

          <div>
            <Label className="text-xs font-medium text-gray-700 mb-2 block">
              明細の疑問点を入力してください
            </Label>
            <Textarea
              value={inquiry}
              onChange={(e) => setInquiry(e.target.value)}
              placeholder="例: なぜ、先に２か月分なのですか？？？"
              className="min-h-[120px] text-sm"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              onClick={onClose}
              className="flex-1 h-10 text-sm"
            >
              閉じる
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!inquiry.trim()}
              className="flex-1 h-10 bg-blue-900 hover:bg-blue-800 text-white font-semibold text-sm"
            >
              保存
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
