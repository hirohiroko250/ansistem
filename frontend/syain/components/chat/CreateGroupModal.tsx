'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Checkbox } from '@/components/ui/checkbox';
import { Search, Users, Loader2, ChevronLeft } from 'lucide-react';
import { createStaffGroup, type StaffChannel } from '@/lib/api/chat';

interface StaffMember {
  id: string;
  fullName: string;
  positionName: string | null;
  email: string;
}

interface CreateGroupScreenProps {
  onClose: () => void;
  onGroupCreated: (channel: StaffChannel) => void;
  staffList: StaffMember[];
  currentUserId: string;
}

const avatarColors = [
  'from-pink-400 to-rose-500',
  'from-blue-400 to-indigo-500',
  'from-green-400 to-emerald-500',
  'from-purple-400 to-violet-500',
  'from-orange-400 to-amber-500',
  'from-cyan-400 to-teal-500',
];

export function CreateGroupScreen({
  onClose,
  onGroupCreated,
  staffList,
  currentUserId,
}: CreateGroupScreenProps) {
  const [groupName, setGroupName] = useState('');
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 自分以外のスタッフをフィルター
  const filteredStaff = staffList.filter(staff => {
    if (staff.id === currentUserId) return false;
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      staff.fullName.toLowerCase().includes(query) ||
      staff.email.toLowerCase().includes(query) ||
      (staff.positionName?.toLowerCase().includes(query) ?? false)
    );
  });

  const handleToggleMember = (staffId: string) => {
    setSelectedMembers(prev =>
      prev.includes(staffId)
        ? prev.filter(id => id !== staffId)
        : [...prev, staffId]
    );
  };

  const handleCreate = async () => {
    if (!groupName.trim()) {
      setError('グループ名を入力してください');
      return;
    }

    if (selectedMembers.length === 0) {
      setError('メンバーを1人以上選択してください');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const channel = await createStaffGroup(groupName.trim(), selectedMembers);
      onGroupCreated(channel);
      onClose();
    } catch (err) {
      console.error('Failed to create group:', err);
      setError('グループの作成に失敗しました');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* ヘッダー */}
      <div className="flex-shrink-0 bg-blue-600 text-white px-4 py-3 flex items-center gap-3">
        <button
          onClick={onClose}
          className="p-1 hover:bg-white/10 rounded-full transition-colors"
        >
          <ChevronLeft className="w-6 h-6" />
        </button>
        <Users className="w-5 h-5" />
        <h1 className="text-lg font-semibold">グループを作成</h1>
      </div>

      {/* コンテンツ */}
      <div className="flex-1 overflow-hidden flex flex-col p-4 gap-4">
        {/* グループ名 */}
        <div className="space-y-2 flex-shrink-0">
          <Label htmlFor="group-name">グループ名 *</Label>
          <Input
            id="group-name"
            value={groupName}
            onChange={(e) => setGroupName(e.target.value)}
            placeholder="例: プロジェクトチーム"
            maxLength={50}
          />
        </div>

        {/* メンバー選択 */}
        <div className="flex-1 space-y-2 overflow-hidden flex flex-col min-h-0">
          <Label>メンバー選択 * ({selectedMembers.length}人選択中)</Label>

          {/* 検索 */}
          <div className="relative flex-shrink-0">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="名前で検索..."
              className="pl-10"
            />
          </div>

          {/* メンバー一覧 */}
          <div className="flex-1 overflow-y-auto border rounded-lg min-h-0">
            {filteredStaff.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">
                {searchQuery ? '該当するメンバーがいません' : 'メンバーがいません'}
              </div>
            ) : (
              filteredStaff.map(staff => {
                const colorIndex = staff.fullName.charCodeAt(0) % avatarColors.length;
                const isSelected = selectedMembers.includes(staff.id);

                return (
                  <label
                    key={staff.id}
                    className={`flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 border-b last:border-b-0 ${
                      isSelected ? 'bg-blue-50' : ''
                    }`}
                  >
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={() => handleToggleMember(staff.id)}
                    />
                    <Avatar className="w-9 h-9">
                      <AvatarFallback className={`bg-gradient-to-br ${avatarColors[colorIndex]} text-white text-sm`}>
                        {staff.fullName.substring(0, 2)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm text-gray-900 truncate">
                        {staff.fullName}
                      </p>
                      {staff.positionName && (
                        <p className="text-xs text-gray-500 truncate">
                          {staff.positionName}
                        </p>
                      )}
                    </div>
                  </label>
                );
              })
            )}
          </div>
        </div>

        {/* エラー表示 */}
        {error && (
          <p className="text-sm text-red-500 flex-shrink-0">{error}</p>
        )}

        {/* アクション */}
        <div className="flex gap-2 flex-shrink-0">
          <Button
            variant="outline"
            onClick={onClose}
            className="flex-1"
            disabled={isCreating}
          >
            キャンセル
          </Button>
          <Button
            onClick={handleCreate}
            className="flex-1 bg-blue-600 hover:bg-blue-700"
            disabled={isCreating || !groupName.trim() || selectedMembers.length === 0}
          >
            {isCreating ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                作成中...
              </>
            ) : (
              '作成'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

// 後方互換性のためのエイリアス
export const CreateGroupModal = CreateGroupScreen;
