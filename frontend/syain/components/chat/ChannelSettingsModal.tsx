'use client';

import { useState, useEffect, useCallback } from 'react';
import { X, Settings, Users, UserPlus, Trash2, Shield, ShieldCheck, Eye, Loader2, Check, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  StaffChannel,
  Staff,
  ChannelMember,
  MemberRole,
  getChannelMembers,
  updateChannelSettings,
  addChannelMember,
  removeChannelMember,
  updateMemberRole,
  getStaffList,
} from '@/lib/api/chat';

interface ChannelSettingsModalProps {
  channel: StaffChannel;
  isOpen: boolean;
  onClose: () => void;
  onChannelUpdate?: (channel: StaffChannel) => void;
  currentUserId?: string;
}

type TabType = 'settings' | 'members';

export function ChannelSettingsModal({
  channel,
  isOpen,
  onClose,
  onChannelUpdate,
  currentUserId,
}: ChannelSettingsModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>('settings');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // チャンネル設定
  const [name, setName] = useState(channel.name);
  const [description, setDescription] = useState(channel.description || '');
  const [isSaving, setIsSaving] = useState(false);

  // メンバー管理
  const [members, setMembers] = useState<ChannelMember[]>([]);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [showAddMember, setShowAddMember] = useState(false);
  const [availableStaff, setAvailableStaff] = useState<Staff[]>([]);
  const [staffSearch, setStaffSearch] = useState('');
  const [isAddingMember, setIsAddingMember] = useState(false);

  // 権限チェック（グループチャンネルのみ設定可能）
  const isGroupChannel = channel.channelType === 'GROUP' || channel.channelType === 'INTERNAL';
  const isAdmin = members.some(
    (m) => m.user.id === currentUserId && m.role === 'ADMIN'
  );

  // メンバー一覧を取得
  const loadMembers = useCallback(async () => {
    if (!isGroupChannel) return;
    setIsLoadingMembers(true);
    try {
      const data = await getChannelMembers(channel.id);
      setMembers(data);
    } catch (err) {
      console.error('Failed to load members:', err);
      setError('メンバーの取得に失敗しました');
    } finally {
      setIsLoadingMembers(false);
    }
  }, [channel.id, isGroupChannel]);

  // スタッフ一覧を取得
  const loadStaff = useCallback(async () => {
    try {
      const data = await getStaffList();
      setAvailableStaff(data);
    } catch (err) {
      console.error('Failed to load staff:', err);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      setName(channel.name);
      setDescription(channel.description || '');
      setError(null);
      setSuccessMessage(null);
      loadMembers();
      loadStaff();
    }
  }, [isOpen, channel, loadMembers, loadStaff]);

  // 設定を保存
  const handleSaveSettings = async () => {
    if (!name.trim()) {
      setError('チャンネル名は必須です');
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      const updated = await updateChannelSettings(channel.id, {
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setSuccessMessage('設定を保存しました');
      onChannelUpdate?.(updated as unknown as StaffChannel);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      console.error('Failed to save settings:', err);
      setError(err.message || '設定の保存に失敗しました');
    } finally {
      setIsSaving(false);
    }
  };

  // メンバーを追加
  const handleAddMember = async (userId: string) => {
    setIsAddingMember(true);
    setError(null);
    try {
      await addChannelMember(channel.id, userId);
      await loadMembers();
      setShowAddMember(false);
      setStaffSearch('');
      setSuccessMessage('メンバーを追加しました');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      console.error('Failed to add member:', err);
      setError(err.message || 'メンバーの追加に失敗しました');
    } finally {
      setIsAddingMember(false);
    }
  };

  // メンバーを削除
  const handleRemoveMember = async (userId: string) => {
    if (!confirm('このメンバーを削除しますか？')) return;

    setIsLoading(true);
    setError(null);
    try {
      await removeChannelMember(channel.id, userId);
      await loadMembers();
      setSuccessMessage('メンバーを削除しました');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      console.error('Failed to remove member:', err);
      setError(err.message || 'メンバーの削除に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  // ロールを更新
  const handleUpdateRole = async (userId: string, newRole: MemberRole) => {
    setIsLoading(true);
    setError(null);
    try {
      await updateMemberRole(channel.id, userId, newRole);
      await loadMembers();
      setSuccessMessage('ロールを更新しました');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      console.error('Failed to update role:', err);
      setError(err.message || 'ロールの更新に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  // 追加可能なスタッフ（既存メンバー以外）
  const filteredStaff = availableStaff.filter((staff) => {
    const isAlreadyMember = members.some((m) => m.user.id === staff.id);
    const matchesSearch = staff.name.toLowerCase().includes(staffSearch.toLowerCase()) ||
      (staff.email?.toLowerCase().includes(staffSearch.toLowerCase()));
    return !isAlreadyMember && matchesSearch;
  });

  // ロールアイコン
  const getRoleIcon = (role: MemberRole) => {
    switch (role) {
      case 'ADMIN':
        return <ShieldCheck className="w-4 h-4 text-blue-600" />;
      case 'MEMBER':
        return <Shield className="w-4 h-4 text-gray-500" />;
      case 'READONLY':
        return <Eye className="w-4 h-4 text-gray-400" />;
    }
  };

  // ロール名
  const getRoleName = (role: MemberRole) => {
    switch (role) {
      case 'ADMIN':
        return '管理者';
      case 'MEMBER':
        return 'メンバー';
      case 'READONLY':
        return '閲覧のみ';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col mx-4">
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h2 className="text-lg font-semibold">チャンネル設定</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* タブ */}
        {isGroupChannel && (
          <div className="flex border-b">
            <button
              onClick={() => setActiveTab('settings')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'settings'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Settings className="w-4 h-4" />
              設定
            </button>
            <button
              onClick={() => setActiveTab('members')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'members'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Users className="w-4 h-4" />
              メンバー ({members.length})
            </button>
          </div>
        )}

        {/* コンテンツ */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* エラー・成功メッセージ */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
              {error}
            </div>
          )}
          {successMessage && (
            <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg text-sm flex items-center gap-2">
              <Check className="w-4 h-4" />
              {successMessage}
            </div>
          )}

          {/* 設定タブ */}
          {activeTab === 'settings' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  チャンネル名
                </label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="チャンネル名"
                  disabled={!isAdmin && isGroupChannel}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  説明（任意）
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="チャンネルの説明"
                  rows={3}
                  disabled={!isAdmin && isGroupChannel}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                />
              </div>

              {(!isGroupChannel || isAdmin) && (
                <Button
                  onClick={handleSaveSettings}
                  disabled={isSaving}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      保存中...
                    </>
                  ) : (
                    '設定を保存'
                  )}
                </Button>
              )}

              {isGroupChannel && !isAdmin && (
                <p className="text-sm text-gray-500 text-center">
                  設定を変更するには管理者権限が必要です
                </p>
              )}
            </div>
          )}

          {/* メンバータブ */}
          {activeTab === 'members' && (
            <div className="space-y-4">
              {/* メンバー追加ボタン */}
              {isAdmin && !showAddMember && (
                <Button
                  onClick={() => setShowAddMember(true)}
                  variant="outline"
                  className="w-full"
                >
                  <UserPlus className="w-4 h-4 mr-2" />
                  メンバーを追加
                </Button>
              )}

              {/* メンバー追加フォーム */}
              {showAddMember && (
                <div className="border rounded-lg p-3 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">メンバーを追加</span>
                    <button
                      onClick={() => {
                        setShowAddMember(false);
                        setStaffSearch('');
                      }}
                      className="p-1 hover:bg-gray-100 rounded"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      value={staffSearch}
                      onChange={(e) => setStaffSearch(e.target.value)}
                      placeholder="名前またはメールで検索"
                      className="pl-10"
                    />
                  </div>
                  <div className="max-h-40 overflow-y-auto space-y-1">
                    {filteredStaff.length === 0 ? (
                      <p className="text-sm text-gray-500 text-center py-2">
                        {staffSearch ? '該当するスタッフが見つかりません' : '追加可能なスタッフがいません'}
                      </p>
                    ) : (
                      filteredStaff.map((staff) => (
                        <button
                          key={staff.id}
                          onClick={() => handleAddMember(staff.id)}
                          disabled={isAddingMember}
                          className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                        >
                          <div className="text-left">
                            <p className="text-sm font-medium">{staff.name}</p>
                            {staff.email && (
                              <p className="text-xs text-gray-500">{staff.email}</p>
                            )}
                          </div>
                          <UserPlus className="w-4 h-4 text-blue-600" />
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* メンバー一覧 */}
              {isLoadingMembers ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                </div>
              ) : (
                <div className="space-y-2">
                  {members.map((member) => (
                    <div
                      key={member.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center text-sm font-medium text-white">
                          {(member.user.fullName || member.user.full_name || member.user.email)?.[0]?.toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-medium">
                            {member.user.fullName || member.user.full_name || member.user.email}
                            {member.user.id === currentUserId && (
                              <span className="text-xs text-gray-500 ml-1">(自分)</span>
                            )}
                          </p>
                          <div className="flex items-center gap-1 text-xs text-gray-500">
                            {getRoleIcon(member.role)}
                            <span>{getRoleName(member.role)}</span>
                          </div>
                        </div>
                      </div>

                      {/* 管理者のアクション */}
                      {isAdmin && member.user.id !== currentUserId && (
                        <div className="flex items-center gap-1">
                          {/* ロール変更 */}
                          <select
                            value={member.role}
                            onChange={(e) => handleUpdateRole(member.user.id, e.target.value as MemberRole)}
                            disabled={isLoading}
                            className="text-xs border rounded px-2 py-1 bg-white"
                          >
                            <option value="ADMIN">管理者</option>
                            <option value="MEMBER">メンバー</option>
                            <option value="READONLY">閲覧のみ</option>
                          </select>
                          {/* 削除 */}
                          <button
                            onClick={() => handleRemoveMember(member.user.id)}
                            disabled={isLoading}
                            className="p-1 text-red-500 hover:bg-red-50 rounded disabled:opacity-50"
                            title="メンバーを削除"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* フッター */}
        <div className="px-4 py-3 border-t flex justify-end">
          <Button variant="outline" onClick={onClose}>
            閉じる
          </Button>
        </div>
      </div>
    </div>
  );
}
