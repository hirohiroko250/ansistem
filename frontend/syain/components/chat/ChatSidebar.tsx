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
    <div className="h-full flex flex-col bg-[#1a1a2e]">
      {/* Chatwork風ヘッダー */}
      <div className="flex-shrink-0 bg-[#1a1a2e] px-3 py-3">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-[#07B53B]" />
            チャット
          </h1>
          <div className="flex items-center gap-1">
            {onOpenSearch && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onOpenSearch}
                className="text-gray-400 hover:text-white hover:bg-white/10 h-8 w-8"
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
                className="text-[#07B53B] hover:text-[#07B53B] hover:bg-white/10 h-8 w-8"
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
                className="text-[#07B53B] hover:text-[#07B53B] hover:bg-white/10 h-8 w-8"
                title="DMを作成"
              >
                <UserPlus className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Chatwork風タブ */}
        <div className="flex bg-[#2d2d44] rounded-lg p-0.5">
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
                    ? 'bg-[#07B53B] text-white'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Chatwork風検索バー */}
      <div className="flex-shrink-0 px-3 py-2 bg-[#2d2d44]">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-500" />
          <Input
            placeholder="チャットを検索..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="pl-9 bg-[#1a1a2e] border-0 rounded-md h-8 text-sm text-white placeholder:text-gray-500 focus-visible:ring-1 focus-visible:ring-[#07B53B]"
          />
        </div>
      </div>

      {/* 新規チャット作成（社員タブ）- Chatwork風 */}
      {activeTab === 'staff' && showNewChat && (
        <div className="flex-shrink-0 bg-[#2d2d44]">
          <div className="px-3 py-2 flex items-center justify-between border-b border-white/10">
            <p className="text-xs font-medium text-gray-400">メンバーを選択</p>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors ${
                showFilters || filterSchool || filterBrand
                  ? 'bg-[#07B53B] text-white'
                  : 'bg-white/10 text-gray-400 hover:bg-white/20'
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
            <div className="px-3 py-3 border-b border-white/10 space-y-2">
              <div className="flex gap-2">
                <Select value={filterSchool} onValueChange={onFilterSchoolChange}>
                  <SelectTrigger className="flex-1 h-8 text-xs bg-[#1a1a2e] border-0 text-white">
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
                  <SelectTrigger className="flex-1 h-8 text-xs bg-[#1a1a2e] border-0 text-white">
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
                  className="text-xs text-[#07B53B] hover:underline"
                >
                  フィルターをクリア
                </button>
              )}
            </div>
          )}

          <div className="max-h-64 overflow-y-auto bg-[#1a1a2e]">
            {staffList.map(staff => {
              const colorIndex = staff.fullName.charCodeAt(0) % avatarColors.length;

              return (
                <div
                  key={staff.id}
                  className="w-full px-3 py-2.5 flex items-center gap-3 hover:bg-white/5 transition-colors border-b border-white/5"
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
                    <p className="font-medium text-white text-sm truncate">{staff.fullName}</p>
                    {staff.positionName && (
                      <p className="text-xs text-gray-500 truncate">{staff.positionName}</p>
                    )}
                  </button>

                  <button
                    onClick={() => onCreateStaffDM(staff.id)}
                    className="p-1.5 text-[#07B53B] hover:bg-[#07B53B]/20 rounded transition-colors"
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

      {/* Chatwork風チャンネル一覧 */}
      <div className="flex-1 overflow-y-auto bg-[#1a1a2e]">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-[#07B53B]" />
          </div>
        ) : currentChannels.length === 0 && !showNewChat ? (
          <div className="text-center py-16 px-4">
            <div className="w-16 h-16 mx-auto mb-4 bg-[#2d2d44] rounded-full flex items-center justify-center">
              <MessageCircle className="w-8 h-8 text-gray-500" />
            </div>
            <p className="text-gray-500 text-sm">
              {searchQuery ? '検索結果がありません' : 'トークがありません'}
            </p>
            {activeTab === 'staff' && !searchQuery && (
              <Button
                size="sm"
                onClick={onToggleNewChat}
                className="mt-4 bg-[#07B53B] hover:bg-[#06a035]"
              >
                <UserPlus className="w-4 h-4 mr-2" />
                トークを開始
              </Button>
            )}
          </div>
        ) : (
          !showNewChat && (
            <>
              {/* ピン留めセクション - Chatwork風 */}
              {pinnedCount > 0 && (
                <div className="px-3 py-1.5 bg-[#2d2d44]">
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
                      <div className="px-3 py-1.5 bg-[#2d2d44]">
                        <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">すべて</p>
                      </div>
                    )}
                    <div
                      className={`w-full px-3 py-2.5 flex items-center gap-2.5 transition-colors group cursor-pointer ${
                        isSelected
                          ? 'bg-[#07B53B]/20 border-l-2 border-l-[#07B53B]'
                          : 'hover:bg-white/5 border-l-2 border-l-transparent'
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
                          {/* Chatwork風の未読バッジ */}
                          {unreadCount > 0 && (
                            <div className="absolute -top-1 -right-1 bg-[#E53935] text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1 shadow-lg">
                              {unreadCount > 99 ? '99+' : unreadCount}
                            </div>
                          )}
                        </div>

                        <div className="flex-1 min-w-0 text-left">
                          <div className="flex items-center gap-1">
                            <h3 className={`text-sm truncate ${
                              unreadCount > 0
                                ? 'font-semibold text-white'
                                : isSelected
                                  ? 'font-medium text-white'
                                  : 'font-medium text-gray-300'
                            }`}>
                              {displayName}
                            </h3>
                            {isPinned && (
                              <Pin className="w-3 h-3 text-[#07B53B] flex-shrink-0" />
                            )}
                            {isMuted && (
                              <BellOff className="w-3 h-3 text-gray-600 flex-shrink-0" />
                            )}
                          </div>
                          <div className="flex items-center justify-between mt-0.5">
                            {lastMessage ? (
                              <p className={`text-xs truncate flex-1 ${
                                unreadCount > 0 ? 'text-gray-300' : 'text-gray-500'
                              }`}>
                                {lastMessage.content}
                              </p>
                            ) : (
                              <p className="text-xs text-gray-600 truncate flex-1">メッセージなし</p>
                            )}
                            {lastMessage && (
                              <span className="text-[10px] text-gray-500 flex-shrink-0 ml-2">
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

                      {/* Chatwork風チャンネルメニュー */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 text-gray-400 hover:text-white hover:bg-white/10"
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-44 bg-[#2d2d44] border-white/10">
                          {onTogglePin && (
                            <DropdownMenuItem
                              onClick={() => onTogglePin(channel.id)}
                              className="text-gray-300 focus:text-white focus:bg-white/10"
                            >
                              <Pin className="w-4 h-4 mr-2" />
                              {isPinned ? 'ピン留め解除' : 'ピン留め'}
                            </DropdownMenuItem>
                          )}
                          {onToggleMute && (
                            <DropdownMenuItem
                              onClick={() => onToggleMute(channel.id)}
                              className="text-gray-300 focus:text-white focus:bg-white/10"
                            >
                              <BellOff className="w-4 h-4 mr-2" />
                              {isMuted ? 'ミュート解除' : 'ミュート'}
                            </DropdownMenuItem>
                          )}
                          {(onTogglePin || onToggleMute) && onArchive && (
                            <DropdownMenuSeparator className="bg-white/10" />
                          )}
                          {onArchive && (
                            <DropdownMenuItem
                              onClick={() => onArchive(channel.id)}
                              className="text-red-400 focus:text-red-300 focus:bg-red-500/10"
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
