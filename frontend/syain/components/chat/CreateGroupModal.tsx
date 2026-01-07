'use client';

import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Checkbox } from '@/components/ui/checkbox';
import { Search, Users, Loader2, ChevronLeft, ChevronDown, ChevronRight, Building2, Briefcase } from 'lucide-react';
import { createStaffGroup, type StaffChannel } from '@/lib/api/chat';

interface StaffMember {
  id: string;
  fullName: string;
  positionName: string | null;
  email: string;
  department?: string;
  brandsList?: { id: string; name: string }[];
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

type GroupByType = 'none' | 'role' | 'company';

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
  const [groupBy, setGroupBy] = useState<GroupByType>('role');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['all']));

  // 自分以外のスタッフをフィルター
  const filteredStaff = useMemo(() => {
    return staffList.filter(staff => {
      if (staff.id === currentUserId) return false;
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        staff.fullName.toLowerCase().includes(query) ||
        staff.email.toLowerCase().includes(query) ||
        (staff.positionName?.toLowerCase().includes(query) ?? false)
      );
    });
  }, [staffList, currentUserId, searchQuery]);

  // グループ化されたスタッフ
  const groupedStaff = useMemo(() => {
    if (groupBy === 'none') {
      return [{ key: 'all', label: 'すべてのメンバー', members: filteredStaff }];
    }

    if (groupBy === 'role') {
      const groups = new Map<string, StaffMember[]>();
      filteredStaff.forEach(staff => {
        const role = staff.positionName || '未設定';
        if (!groups.has(role)) {
          groups.set(role, []);
        }
        groups.get(role)!.push(staff);
      });
      return Array.from(groups.entries())
        .sort((a, b) => a[0].localeCompare(b[0], 'ja'))
        .map(([role, members]) => ({
          key: role,
          label: role,
          members,
        }));
    }

    if (groupBy === 'company') {
      const groups = new Map<string, StaffMember[]>();
      filteredStaff.forEach(staff => {
        const brands = staff.brandsList || [];
        if (brands.length === 0) {
          const key = '未所属';
          if (!groups.has(key)) {
            groups.set(key, []);
          }
          groups.get(key)!.push(staff);
        } else {
          brands.forEach(brand => {
            if (!groups.has(brand.name)) {
              groups.set(brand.name, []);
            }
            groups.get(brand.name)!.push(staff);
          });
        }
      });
      return Array.from(groups.entries())
        .sort((a, b) => a[0].localeCompare(b[0], 'ja'))
        .map(([company, members]) => ({
          key: company,
          label: company,
          members,
        }));
    }

    return [];
  }, [filteredStaff, groupBy]);

  const handleToggleMember = (staffId: string) => {
    setSelectedMembers(prev =>
      prev.includes(staffId)
        ? prev.filter(id => id !== staffId)
        : [...prev, staffId]
    );
  };

  const handleToggleGroup = (groupKey: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupKey)) {
        next.delete(groupKey);
      } else {
        next.add(groupKey);
      }
      return next;
    });
  };

  const handleSelectAllInGroup = (members: StaffMember[]) => {
    const memberIds = members.map(m => m.id);
    const allSelected = memberIds.every(id => selectedMembers.includes(id));

    if (allSelected) {
      // すべて選択解除
      setSelectedMembers(prev => prev.filter(id => !memberIds.includes(id)));
    } else {
      // すべて選択
      setSelectedMembers(prev => {
        const newSet = new Set([...prev, ...memberIds]);
        return Array.from(newSet);
      });
    }
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
          <div className="flex items-center justify-between flex-shrink-0">
            <Label>メンバー選択 * ({selectedMembers.length}人選択中)</Label>
          </div>

          {/* グルーピング切り替え */}
          <div className="flex gap-1 flex-shrink-0 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setGroupBy('role')}
              className={`flex-1 py-1.5 px-2 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
                groupBy === 'role'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Briefcase className="w-3.5 h-3.5" />
              役割別
            </button>
            <button
              onClick={() => setGroupBy('company')}
              className={`flex-1 py-1.5 px-2 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
                groupBy === 'company'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Building2 className="w-3.5 h-3.5" />
              会社別
            </button>
            <button
              onClick={() => setGroupBy('none')}
              className={`flex-1 py-1.5 px-2 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
                groupBy === 'none'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              一覧
            </button>
          </div>

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
              groupedStaff.map(group => {
                const isExpanded = expandedGroups.has(group.key) || groupBy === 'none';
                const selectedInGroup = group.members.filter(m => selectedMembers.includes(m.id)).length;
                const allSelectedInGroup = selectedInGroup === group.members.length;

                return (
                  <div key={group.key} className="border-b last:border-b-0">
                    {/* グループヘッダー */}
                    {groupBy !== 'none' && (
                      <div
                        className="flex items-center gap-2 px-3 py-2 bg-gray-50 cursor-pointer hover:bg-gray-100 sticky top-0"
                        onClick={() => handleToggleGroup(group.key)}
                      >
                        <button className="p-0.5">
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-gray-500" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-500" />
                          )}
                        </button>
                        <span className="flex-1 text-sm font-medium text-gray-700">
                          {group.label}
                        </span>
                        <span className="text-xs text-gray-500">
                          {selectedInGroup > 0 && (
                            <span className="text-blue-600 font-medium mr-1">
                              {selectedInGroup}選択
                            </span>
                          )}
                          ({group.members.length}人)
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectAllInGroup(group.members);
                          }}
                          className={`text-xs px-2 py-0.5 rounded transition-colors ${
                            allSelectedInGroup
                              ? 'bg-blue-100 text-blue-600'
                              : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                          }`}
                        >
                          {allSelectedInGroup ? '解除' : '全選択'}
                        </button>
                      </div>
                    )}

                    {/* メンバーリスト */}
                    {isExpanded && (
                      <div>
                        {group.members.map(staff => {
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
                                <div className="flex items-center gap-2 text-xs text-gray-500">
                                  {staff.positionName && (
                                    <span className="truncate">{staff.positionName}</span>
                                  )}
                                  {staff.brandsList && staff.brandsList.length > 0 && groupBy !== 'company' && (
                                    <span className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">
                                      {staff.brandsList[0].name}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </div>
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
