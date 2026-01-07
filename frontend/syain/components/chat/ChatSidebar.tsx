'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  MessageCircle,
  Users,
  Search,
  Loader2,
  UserPlus,
  User,
  Filter,
  UsersRound,
  Pin,
  BellOff,
  MoreVertical,
  Archive,
} from 'lucide-react';
import { format, isToday, isYesterday } from 'date-fns';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { Channel, StaffChannel } from '@/lib/api/chat';

export type TabType = 'guardian' | 'group' | 'staff';

interface StaffDetail {
  id: string;
  employeeNo: string;
  fullName: string;
  lastName: string;
  firstName: string;
  email: string;
  phone: string;
  department: string;
  positionName: string | null;
  profileImageUrl?: string | null;
  schoolsList: { id: string; name: string }[];
  brandsList: { id: string; name: string }[];
}

interface SchoolOption {
  id: string;
  schoolName: string;
}

interface BrandOption {
  id: string;
  brandName: string;
}

interface ChatSidebarProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  channels: Channel[];
  staffChannels: StaffChannel[];
  selectedChannelId: string | null;
  onSelectChannel: (channel: Channel | StaffChannel) => void;
  isLoading: boolean;
  currentUserId: string;
  // Staff-specific props
  showNewChat: boolean;
  onToggleNewChat: () => void;
  staffList: StaffDetail[];
  onCreateStaffDM: (staffId: string) => void;
  onShowStaffDetail: (staff: StaffDetail) => void;
  onCreateGroup?: () => void;
  // Filter props
  schools: SchoolOption[];
  brands: BrandOption[];
  filterSchool: string;
  filterBrand: string;
  onFilterSchoolChange: (value: string) => void;
  onFilterBrandChange: (value: string) => void;
  // Search props
  onOpenSearch?: () => void;
  // Channel action props
  onTogglePin?: (channelId: string) => void;
  onToggleMute?: (channelId: string) => void;
  onArchive?: (channelId: string) => void;
}

const avatarColors = [
  'from-pink-400 to-rose-500',
  'from-blue-400 to-indigo-500',
  'from-green-400 to-emerald-500',
  'from-purple-400 to-violet-500',
  'from-orange-400 to-amber-500',
  'from-cyan-400 to-teal-500',
];

export function ChatSidebar({
  activeTab,
  onTabChange,
  channels,
  staffChannels,
  selectedChannelId,
  onSelectChannel,
  isLoading,
  currentUserId,
  showNewChat,
  onToggleNewChat,
  staffList,
  onCreateStaffDM,
  onShowStaffDetail,
  onCreateGroup,
  schools,
  brands,
  filterSchool,
  filterBrand,
  onFilterSchoolChange,
  onFilterBrandChange,
  onOpenSearch,
  onTogglePin,
  onToggleMute,
  onArchive,
}: ChatSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const getChannelDisplayName = (channel: Channel | StaffChannel) => {
    if ('guardian' in channel && channel.guardian?.fullName) {
      return channel.guardian.fullName;
    }
    if ('members' in channel && channel.members?.length === 2) {
      const other = channel.members.find((m: any) => m.user?.id !== currentUserId);
      return other?.user?.fullName || other?.user?.email || channel.name;
    }
    return channel.name || '不明';
  };

  const getChannelAvatar = (channel: Channel | StaffChannel) => {
    const name = getChannelDisplayName(channel);
    return name.substring(0, 2);
  };

  // 検索フィルター
  const filteredChannels = channels.filter(channel => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      channel.name?.toLowerCase().includes(query) ||
      channel.guardian?.fullName?.toLowerCase().includes(query) ||
      channel.student?.fullName?.toLowerCase().includes(query)
    );
  });

  const filteredStaffChannels = staffChannels.filter(channel => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    const displayName = getChannelDisplayName(channel);
    return displayName.toLowerCase().includes(query);
  });

  // ピン留めされたチャンネルを先頭にソート
  const sortByPinned = <T extends Channel | StaffChannel>(channels: T[]): T[] => {
    return [...channels].sort((a, b) => {
      const aPinned = 'isPinned' in a ? a.isPinned : false;
      const bPinned = 'isPinned' in b ? b.isPinned : false;
      if (aPinned && !bPinned) return -1;
      if (!aPinned && bPinned) return 1;
      return 0;
    });
  };

  const currentChannels = sortByPinned(activeTab === 'staff' ? filteredStaffChannels : filteredChannels);
  const pinnedCount = currentChannels.filter(c => 'isPinned' in c && c.isPinned).length;

  return (
    <div className="h-full flex flex-col bg-white">
      {/* ヘッダー */}
      <div className="flex-shrink-0 bg-white px-3 py-3 border-b">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-lg font-bold text-gray-800 flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-blue-500" />
            チャット
          </h1>
          <div className="flex items-center gap-1">
            {onOpenSearch && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onOpenSearch}
                className="text-gray-500 hover:text-gray-700 hover:bg-gray-100 h-8 w-8"
                title="メッセージを検索"
              >
                <Search className="w-4 h-4" />
              </Button>
            )}
            {activeTab === 'staff' && onCreateGroup && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onCreateGroup}
                className="text-blue-500 hover:text-blue-600 hover:bg-blue-50 h-8 w-8"
                title="グループを作成"
              >
                <UsersRound className="w-4 h-4" />
              </Button>
            )}
            {activeTab === 'staff' && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onToggleNewChat}
                className="text-blue-500 hover:text-blue-600 hover:bg-blue-50 h-8 w-8"
                title="DMを作成"
              >
                <UserPlus className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>

        {/* タブ */}
        <div className="flex bg-gray-100 rounded-lg p-0.5">
          {[
            { key: 'guardian', label: '保護者', icon: User },
            { key: 'group', label: 'グループ', icon: Users },
            { key: 'staff', label: '社内', icon: UsersRound },
          ].map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => onTabChange(tab.key as TabType)}
                className={`flex-1 py-2 text-xs font-medium rounded-md transition-all flex items-center justify-center gap-1 ${
                  activeTab === tab.key
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 検索バー */}
      <div className="flex-shrink-0 px-3 py-2 bg-gray-50 border-b">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="チャットを検索..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="pl-9 bg-white border border-gray-200 rounded-md h-8 text-sm text-gray-800 placeholder:text-gray-400 focus-visible:ring-1 focus-visible:ring-blue-500"
          />
        </div>
      </div>

      {/* 新規チャット作成（社員タブ） */}
      {activeTab === 'staff' && showNewChat && (
        <div className="flex-shrink-0 bg-gray-50">
          <div className="px-3 py-2 flex items-center justify-between border-b border-gray-200">
            <p className="text-xs font-medium text-gray-600">メンバーを選択</p>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors ${
                showFilters || filterSchool || filterBrand
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
              }`}
            >
              <Filter className="w-3 h-3" />
              絞り込み
              {(filterSchool || filterBrand) && (
                <span className="ml-1 bg-white/20 rounded-full w-4 h-4 flex items-center justify-center text-[10px]">
                  {(filterSchool ? 1 : 0) + (filterBrand ? 1 : 0)}
                </span>
              )}
            </button>
          </div>

          {/* フィルター */}
          {showFilters && (
            <div className="px-3 py-3 border-b border-gray-200 space-y-2 bg-white">
              <div className="flex gap-2">
                <Select value={filterSchool} onValueChange={onFilterSchoolChange}>
                  <SelectTrigger className="flex-1 h-8 text-xs bg-white border-gray-200 text-gray-800">
                    <SelectValue placeholder="教室" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">すべて</SelectItem>
                    {schools.map(school => (
                      <SelectItem key={school.id} value={school.id}>
                        {school.schoolName}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={filterBrand} onValueChange={onFilterBrandChange}>
                  <SelectTrigger className="flex-1 h-8 text-xs bg-white border-gray-200 text-gray-800">
                    <SelectValue placeholder="ブランド" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">すべて</SelectItem>
                    {brands.map(brand => (
                      <SelectItem key={brand.id} value={brand.id}>
                        {brand.brandName}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {(filterSchool || filterBrand) && (
                <button
                  onClick={() => {
                    onFilterSchoolChange('');
                    onFilterBrandChange('');
                  }}
                  className="text-xs text-blue-500 hover:underline"
                >
                  フィルターをクリア
                </button>
              )}
            </div>
          )}

          <div className="max-h-64 overflow-y-auto bg-white">
            {staffList.map(staff => {
              const colorIndex = staff.fullName.charCodeAt(0) % avatarColors.length;

              return (
                <div
                  key={staff.id}
                  className="w-full px-3 py-2.5 flex items-center gap-3 hover:bg-gray-50 transition-colors border-b border-gray-100"
                >
                  <button
                    onClick={() => onShowStaffDetail(staff)}
                    className="relative"
                  >
                    <Avatar className="w-9 h-9">
                      {staff.profileImageUrl && (
                        <AvatarImage src={staff.profileImageUrl} alt={staff.fullName} />
                      )}
                      <AvatarFallback className={`bg-gradient-to-br ${avatarColors[colorIndex]} text-white text-xs font-medium`}>
                        {staff.fullName.substring(0, 2)}
                      </AvatarFallback>
                    </Avatar>
                  </button>

                  <button
                    onClick={() => onCreateStaffDM(staff.id)}
                    className="flex-1 text-left min-w-0"
                  >
                    <p className="font-medium text-gray-800 text-sm truncate">{staff.fullName}</p>
                    {staff.positionName && (
                      <p className="text-xs text-gray-500 truncate">{staff.positionName}</p>
                    )}
                  </button>

                  <button
                    onClick={() => onCreateStaffDM(staff.id)}
                    className="p-1.5 text-blue-500 hover:bg-blue-50 rounded transition-colors"
                  >
                    <MessageCircle className="w-4 h-4" />
                  </button>
                </div>
              );
            })}
            {staffList.length === 0 && (
              <p className="text-center text-gray-500 py-8 text-sm">
                {filterSchool || filterBrand ? '該当するメンバーがいません' : 'メンバーがいません'}
              </p>
            )}
          </div>
        </div>
      )}

      {/* チャンネル一覧 */}
      <div className="flex-1 overflow-y-auto bg-white">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
          </div>
        ) : currentChannels.length === 0 && !showNewChat ? (
          <div className="text-center py-16 px-4">
            <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <MessageCircle className="w-8 h-8 text-gray-400" />
            </div>
            <p className="text-gray-500 text-sm">
              {searchQuery ? '検索結果がありません' : 'トークがありません'}
            </p>
            {activeTab === 'staff' && !searchQuery && (
              <Button
                size="sm"
                onClick={onToggleNewChat}
                className="mt-4 bg-blue-500 hover:bg-blue-600"
              >
                <UserPlus className="w-4 h-4 mr-2" />
                トークを開始
              </Button>
            )}
          </div>
        ) : (
          !showNewChat && (
            <>
              {/* ピン留めセクション */}
              {pinnedCount > 0 && (
                <div className="px-3 py-1.5 bg-gray-50 border-b">
                  <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wider flex items-center gap-1">
                    <Pin className="w-2.5 h-2.5" />
                    ピン留め
                  </p>
                </div>
              )}

              {currentChannels.map((channel, index) => {
                const lastMessage = 'lastMessage' in channel ? channel.lastMessage : null;
                const unreadCount = channel.unreadCount || 0;
                const displayName = getChannelDisplayName(channel);
                const colorIndex = displayName.charCodeAt(0) % avatarColors.length;
                const isSelected = channel.id === selectedChannelId;
                const isPinned = 'isPinned' in channel ? channel.isPinned : false;
                const isMuted = 'isMuted' in channel ? channel.isMuted : false;

                // ピン留めセクションと通常セクションの境界
                const showDivider = pinnedCount > 0 && index === pinnedCount;

                return (
                  <div key={channel.id}>
                    {showDivider && (
                      <div className="px-3 py-1.5 bg-gray-50 border-b">
                        <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">すべて</p>
                      </div>
                    )}
                    <div
                      className={`w-full px-3 py-2.5 flex items-center gap-2.5 transition-colors group cursor-pointer ${
                        isSelected
                          ? 'bg-blue-50 border-l-2 border-l-blue-500'
                          : 'hover:bg-gray-50 border-l-2 border-l-transparent'
                      }`}
                    >
                      <button
                        onClick={() => onSelectChannel(channel)}
                        className="flex items-center gap-2.5 flex-1 min-w-0"
                      >
                        <div className="relative flex-shrink-0">
                          <Avatar className="w-10 h-10">
                            <AvatarFallback className={`bg-gradient-to-br ${avatarColors[colorIndex]} text-white text-sm font-medium`}>
                              {activeTab === 'group' ? (
                                <Users className="w-4 h-4" />
                              ) : (
                                getChannelAvatar(channel)
                              )}
                            </AvatarFallback>
                          </Avatar>
                          {/* 未読バッジ */}
                          {unreadCount > 0 && (
                            <div className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1 shadow-lg">
                              {unreadCount > 99 ? '99+' : unreadCount}
                            </div>
                          )}
                        </div>

                        <div className="flex-1 min-w-0 text-left">
                          <div className="flex items-center gap-1">
                            <h3 className={`text-sm truncate ${
                              unreadCount > 0
                                ? 'font-semibold text-gray-900'
                                : isSelected
                                  ? 'font-medium text-gray-900'
                                  : 'font-medium text-gray-700'
                            }`}>
                              {displayName}
                            </h3>
                            {isPinned && (
                              <Pin className="w-3 h-3 text-blue-500 flex-shrink-0" />
                            )}
                            {isMuted && (
                              <BellOff className="w-3 h-3 text-gray-400 flex-shrink-0" />
                            )}
                          </div>
                          <div className="flex items-center justify-between mt-0.5">
                            {lastMessage ? (
                              <p className={`text-xs truncate flex-1 ${
                                unreadCount > 0 ? 'text-gray-600' : 'text-gray-500'
                              }`}>
                                {lastMessage.content}
                              </p>
                            ) : (
                              <p className="text-xs text-gray-400 truncate flex-1">メッセージなし</p>
                            )}
                            {lastMessage && (
                              <span className="text-[10px] text-gray-400 flex-shrink-0 ml-2">
                                {isToday(new Date(lastMessage.createdAt))
                                  ? format(new Date(lastMessage.createdAt), 'HH:mm')
                                  : isYesterday(new Date(lastMessage.createdAt))
                                  ? '昨日'
                                  : format(new Date(lastMessage.createdAt), 'M/d')}
                              </span>
                            )}
                          </div>
                        </div>
                      </button>

                      {/* チャンネルメニュー */}
                      <DropdownMenu modal={false}>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-44">
                          {onTogglePin && (
                            <DropdownMenuItem onClick={() => onTogglePin(channel.id)}>
                              <Pin className="w-4 h-4 mr-2" />
                              {isPinned ? 'ピン留め解除' : 'ピン留め'}
                            </DropdownMenuItem>
                          )}
                          {onToggleMute && (
                            <DropdownMenuItem onClick={() => onToggleMute(channel.id)}>
                              <BellOff className="w-4 h-4 mr-2" />
                              {isMuted ? 'ミュート解除' : 'ミュート'}
                            </DropdownMenuItem>
                          )}
                          {(onTogglePin || onToggleMute) && onArchive && (
                            <DropdownMenuSeparator />
                          )}
                          {onArchive && (
                            <DropdownMenuItem
                              onClick={() => onArchive(channel.id)}
                              className="text-red-600"
                            >
                              <Archive className="w-4 h-4 mr-2" />
                              アーカイブ
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                );
              })}
            </>
          )
        )}
      </div>
    </div>
  );
}
