'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BottomNav } from '@/components/bottom-nav';
import {
  MessageCircle,
  Users,
  Send,
  Loader2,
  Search,
  ChevronLeft,
  Check,
  CheckCheck,
  User,
  UserPlus,
  Plus,
  Image as ImageIcon,
  MoreVertical,
  Phone,
  Video,
} from 'lucide-react';
import { format, isToday, isYesterday, isSameDay } from 'date-fns';
import { ja } from 'date-fns/locale';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  getChannels,
  getMessages,
  sendMessage,
  markChannelAsRead,
  getStaffChannels,
  getStaffMessages,
  sendStaffMessage,
  createStaffDM,
  createStaffGroup,
  getStaffList,
  type Channel,
  type Message,
  type StaffChannel,
  type Staff,
} from '@/lib/api/chat';
import { getAccessToken } from '@/lib/api/client';
import api from '@/lib/api/client';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Building, MapPin, Briefcase, X, Filter } from 'lucide-react';

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

type TabType = 'guardian' | 'group' | 'staff';

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = searchParams.get('tab') as TabType | null;

  const [activeTab, setActiveTab] = useState<TabType>(initialTab || 'guardian');
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Staff chat state
  const [staffChannels, setStaffChannels] = useState<StaffChannel[]>([]);
  const [selectedStaffChannel, setSelectedStaffChannel] = useState<StaffChannel | null>(null);
  const [staffMessages, setStaffMessages] = useState<Message[]>([]);
  const [staffList, setStaffList] = useState<StaffDetail[]>([]);
  const [showNewChat, setShowNewChat] = useState(false);

  // Staff detail & filter state
  const [selectedStaffDetail, setSelectedStaffDetail] = useState<StaffDetail | null>(null);
  const [showStaffDetail, setShowStaffDetail] = useState(false);
  const [schools, setSchools] = useState<SchoolOption[]>([]);
  const [brands, setBrands] = useState<BrandOption[]>([]);
  const [filterSchool, setFilterSchool] = useState<string>('');
  const [filterBrand, setFilterBrand] = useState<string>('');
  const [showFilters, setShowFilters] = useState(false);

  const currentUserId = getCurrentUserId();

  function getCurrentUserId(): string {
    if (typeof window === 'undefined') return '';
    const token = getAccessToken();
    if (!token) return '';
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.user_id || '';
    } catch {
      return '';
    }
  }

  // URLパラメータからタブを設定
  useEffect(() => {
    const tab = searchParams.get('tab') as TabType | null;
    if (tab && ['guardian', 'group', 'staff'].includes(tab)) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  // 認証チェック
  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  // チャンネル一覧を取得
  useEffect(() => {
    if (activeTab === 'staff') {
      loadStaffChannels();
      loadStaffListWithDetails();
      loadSchoolsAndBrands();
    } else {
      loadChannels();
    }
  }, [activeTab]);

  // フィルター変更時にスタッフ一覧を再取得
  useEffect(() => {
    if (activeTab === 'staff' && showNewChat) {
      loadStaffListWithDetails();
    }
  }, [filterSchool, filterBrand]);

  // 選択したチャンネルのメッセージを取得
  useEffect(() => {
    if (selectedChannel) {
      loadMessages();
      const interval = setInterval(loadMessages, 5000);
      return () => clearInterval(interval);
    }
  }, [selectedChannel?.id]);

  // 選択したスタッフチャンネルのメッセージを取得
  useEffect(() => {
    if (selectedStaffChannel) {
      loadStaffMessagesForChannel();
      const interval = setInterval(loadStaffMessagesForChannel, 5000);
      return () => clearInterval(interval);
    }
  }, [selectedStaffChannel?.id]);

  // メッセージ更新時に自動スクロール
  useEffect(() => {
    scrollToBottom();
  }, [messages, staffMessages]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const loadChannels = async () => {
    try {
      setIsLoading(true);
      const channelType = activeTab === 'guardian' ? 'direct' : 'group';
      const data = await getChannels({ channelType, isArchived: false });
      setChannels(data);
    } catch (error) {
      console.error('Failed to load channels:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadStaffChannels = async () => {
    try {
      setIsLoading(true);
      const data = await getStaffChannels();
      setStaffChannels(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load staff channels:', error);
      setStaffChannels([]);
    } finally {
      setIsLoading(false);
    }
  };

  const loadStaffList = async () => {
    try {
      const data = await getStaffList();
      // Convert to StaffDetail format
      const staffDetails: StaffDetail[] = data.map((s: any) => ({
        id: s.id,
        employeeNo: s.employeeNo || '',
        fullName: s.name || s.fullName || '',
        lastName: s.lastName || '',
        firstName: s.firstName || '',
        email: s.email || '',
        phone: s.phone || '',
        department: s.department || '',
        positionName: s.position || s.positionName || null,
        schoolsList: [],
        brandsList: [],
      }));
      setStaffList(staffDetails);
    } catch (error) {
      console.error('Failed to load staff list:', error);
    }
  };

  const loadStaffListWithDetails = async () => {
    try {
      // Build query params for filtering
      const params = new URLSearchParams();
      if (filterSchool) params.append('school', filterSchool);
      if (filterBrand) params.append('brand', filterBrand);

      const url = `/tenants/employees/${params.toString() ? '?' + params.toString() : ''}`;
      const response = await api.get<any>(url);
      const results = response.results || response || [];

      const staffDetails: StaffDetail[] = results.map((e: any) => ({
        id: e.id,
        employeeNo: e.employee_no || '',
        fullName: e.full_name || `${e.last_name || ''}${e.first_name || ''}`.trim() || e.email,
        lastName: e.last_name || '',
        firstName: e.first_name || '',
        email: e.email || '',
        phone: e.phone || e.mobile_phone || '',
        department: e.department || '',
        positionName: e.position_name || e.position || null,
        schoolsList: (e.schools_list || []).map((s: any) => ({ id: s.id, name: s.school_name || s.name })),
        brandsList: (e.brands_list || []).map((b: any) => ({ id: b.id, name: b.brand_name || b.name })),
      }));

      setStaffList(staffDetails);
    } catch (error) {
      console.error('Failed to load staff list with details:', error);
      // Fallback to basic staff list
      loadStaffList();
    }
  };

  const loadSchoolsAndBrands = async () => {
    try {
      // Load schools
      const schoolsResponse = await api.get<any>('/schools/schools/');
      const schoolsData = schoolsResponse.results || schoolsResponse || [];
      setSchools(schoolsData.map((s: any) => ({
        id: s.id,
        schoolName: s.school_name || s.name,
      })));

      // Load brands
      const brandsResponse = await api.get<any>('/schools/brands/');
      const brandsData = brandsResponse.results || brandsResponse || [];
      setBrands(brandsData.map((b: any) => ({
        id: b.id,
        brandName: b.brand_name || b.name,
      })));
    } catch (error) {
      console.error('Failed to load schools and brands:', error);
    }
  };

  const loadStaffMessagesForChannel = async () => {
    if (!selectedStaffChannel) return;
    try {
      const data = await getStaffMessages(selectedStaffChannel.id);
      setStaffMessages(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load staff messages:', error);
    }
  };

  const loadMessages = async () => {
    if (!selectedChannel) return;
    try {
      const response = await getMessages(selectedChannel.id, { pageSize: 100 });
      const messageList = response?.data || response?.results || [];
      setMessages(messageList);
      if (selectedChannel.unreadCount > 0) {
        await markChannelAsRead(selectedChannel.id);
        setChannels(prev =>
          prev.map(ch =>
            ch.id === selectedChannel.id ? { ...ch, unreadCount: 0 } : ch
          )
        );
      }
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || isSending) return;

    const content = newMessage.trim();
    setNewMessage('');
    setIsSending(true);

    if (activeTab === 'staff' && selectedStaffChannel) {
      try {
        await sendStaffMessage(selectedStaffChannel.id, content);
        await loadStaffMessagesForChannel();
      } catch (error) {
        console.error('Failed to send staff message:', error);
        setNewMessage(content);
      } finally {
        setIsSending(false);
      }
    } else if (selectedChannel) {
      const tempMessage: Message = {
        id: `temp-${Date.now()}`,
        channel: selectedChannel.id,
        channelId: selectedChannel.id,
        senderName: 'あなた',
        messageType: 'text',
        content,
        isRead: false,
        isEdited: false,
        isBotMessage: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      setMessages(prev => [...prev, tempMessage]);

      try {
        const sentMessage = await sendMessage({
          channelId: selectedChannel.id,
          content,
          messageType: 'text',
        });
        setMessages(prev =>
          prev.map(msg => (msg.id === tempMessage.id ? sentMessage : msg))
        );
      } catch (error) {
        console.error('Failed to send message:', error);
        setMessages(prev => prev.filter(msg => msg.id !== tempMessage.id));
        setNewMessage(content);
      } finally {
        setIsSending(false);
      }
    }

    inputRef.current?.focus();
  };

  const handleCreateStaffDM = async (staffId: string) => {
    try {
      const channel = await createStaffDM(staffId);
      await loadStaffChannels();
      setSelectedStaffChannel(channel);
      setShowNewChat(false);
    } catch (error) {
      console.error('Failed to create staff DM:', error);
    }
  };

  // 日付フォーマット
  const formatMessageDate = (dateStr: string) => {
    const date = new Date(dateStr);
    if (isToday(date)) return '今日';
    if (isYesterday(date)) return '昨日';
    return format(date, 'M月d日(E)', { locale: ja });
  };

  // メッセージをグループ化（日付ごと）
  const groupMessagesByDate = (msgs: Message[]) => {
    const groups: { date: string; messages: Message[] }[] = [];
    let currentGroup: { date: string; messages: Message[] } | null = null;

    msgs.forEach(msg => {
      const msgDate = new Date(msg.createdAt);
      if (!currentGroup || !isSameDay(new Date(currentGroup.messages[0].createdAt), msgDate)) {
        currentGroup = { date: msg.createdAt, messages: [msg] };
        groups.push(currentGroup);
      } else {
        currentGroup.messages.push(msg);
      }
    });

    return groups;
  };

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

  const currentChannels = activeTab === 'staff' ? filteredStaffChannels : filteredChannels;
  const currentMessages = activeTab === 'staff' ? staffMessages : messages;
  const currentSelectedChannel = activeTab === 'staff' ? selectedStaffChannel : selectedChannel;

  // チャット詳細画面
  if (currentSelectedChannel) {
    const messageGroups = groupMessagesByDate(currentMessages);

    return (
      <div className="h-screen flex flex-col bg-[#7494C0]">
        {/* ヘッダー */}
        <div className="bg-[#7494C0] text-white px-2 py-3 flex items-center gap-2 safe-area-top">
          <button
            onClick={() => {
              if (activeTab === 'staff') {
                setSelectedStaffChannel(null);
                setStaffMessages([]);
              } else {
                setSelectedChannel(null);
                setMessages([]);
              }
            }}
            className="p-2 hover:bg-white/10 rounded-full transition-colors"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
          <Avatar className="w-10 h-10 border-2 border-white/30">
            <AvatarFallback className="bg-white/20 text-white font-bold">
              {getChannelAvatar(currentSelectedChannel)}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <h1 className="font-bold truncate">{getChannelDisplayName(currentSelectedChannel)}</h1>
            {'student' in currentSelectedChannel && currentSelectedChannel.student && (
              <p className="text-xs text-white/70">生徒: {currentSelectedChannel.student.fullName}</p>
            )}
          </div>
          <button className="p-2 hover:bg-white/10 rounded-full">
            <Phone className="w-5 h-5" />
          </button>
          <button className="p-2 hover:bg-white/10 rounded-full">
            <MoreVertical className="w-5 h-5" />
          </button>
        </div>

        {/* メッセージエリア */}
        <div className="flex-1 overflow-y-auto px-3 py-4 bg-[#8CABD9]">
          {currentMessages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-white/60 text-sm">メッセージがありません</p>
            </div>
          ) : (
            messageGroups.map((group, groupIndex) => (
              <div key={groupIndex}>
                {/* 日付セパレーター */}
                <div className="flex justify-center my-4">
                  <span className="bg-black/20 text-white text-xs px-3 py-1 rounded-full">
                    {formatMessageDate(group.date)}
                  </span>
                </div>

                {/* メッセージ */}
                {group.messages.map((message, msgIndex) => {
                  const senderId = message.sender || message.senderId;
                  const isOwnMessage = senderId === currentUserId;
                  const showAvatar = !isOwnMessage && (
                    msgIndex === 0 ||
                    (group.messages[msgIndex - 1].sender || group.messages[msgIndex - 1].senderId) !== senderId
                  );

                  return (
                    <div
                      key={message.id}
                      className={`flex items-end gap-2 mb-2 ${isOwnMessage ? 'flex-row-reverse' : ''}`}
                    >
                      {/* アバター（相手のメッセージのみ） */}
                      {!isOwnMessage && (
                        <div className="w-8 flex-shrink-0">
                          {showAvatar && (
                            <Avatar className="w-8 h-8">
                              <AvatarFallback className="bg-white text-gray-600 text-xs">
                                {(message.senderName || '?').substring(0, 2)}
                              </AvatarFallback>
                            </Avatar>
                          )}
                        </div>
                      )}

                      {/* メッセージバブル */}
                      <div className={`flex flex-col ${isOwnMessage ? 'items-end' : 'items-start'} max-w-[70%]`}>
                        {/* 送信者名（相手のメッセージで最初のみ） */}
                        {!isOwnMessage && showAvatar && (
                          <span className="text-xs text-white/70 mb-1 ml-1">
                            {message.senderName || '不明'}
                          </span>
                        )}

                        <div className={`flex items-end gap-1 ${isOwnMessage ? 'flex-row-reverse' : ''}`}>
                          {/* バブル */}
                          <div
                            className={`relative px-3 py-2 rounded-2xl shadow-sm ${
                              isOwnMessage
                                ? 'bg-[#A8D86D] text-gray-800 rounded-br-sm'
                                : 'bg-white text-gray-800 rounded-bl-sm'
                            }`}
                          >
                            <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
                          </div>

                          {/* 時刻と既読 */}
                          <div className={`flex items-center gap-0.5 ${isOwnMessage ? 'flex-row-reverse' : ''}`}>
                            {isOwnMessage && (
                              <span className="text-xs text-white/70">
                                {message.isRead ? '既読' : ''}
                              </span>
                            )}
                            <span className="text-xs text-white/70">
                              {format(new Date(message.createdAt), 'HH:mm')}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 入力エリア */}
        <div className="bg-[#F5F5F5] px-2 py-2 safe-area-bottom">
          <div className="flex items-center gap-2">
            <button className="p-2 text-gray-500 hover:text-gray-700">
              <Plus className="w-6 h-6" />
            </button>
            <button className="p-2 text-gray-500 hover:text-gray-700">
              <ImageIcon className="w-6 h-6" />
            </button>
            <div className="flex-1 relative">
              <Input
                ref={inputRef}
                placeholder="メッセージを入力"
                value={newMessage}
                onChange={e => setNewMessage(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                disabled={isSending}
                className="rounded-full bg-white border-0 pr-10"
              />
            </div>
            <Button
              onClick={handleSendMessage}
              disabled={!newMessage.trim() || isSending}
              size="icon"
              className="rounded-full bg-[#07B53B] hover:bg-[#06a035] w-10 h-10"
            >
              {isSending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // チャット一覧画面
  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* ヘッダー */}
      <div className="bg-white sticky top-0 z-10 safe-area-top shadow-sm">
        <div className="px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900">チャット</h1>
          {activeTab === 'staff' && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowNewChat(!showNewChat)}
              className="text-blue-600"
            >
              <UserPlus className="w-5 h-5" />
            </Button>
          )}
        </div>

        {/* タブ */}
        <div className="flex px-2">
          {[
            { key: 'guardian', label: '保護者' },
            { key: 'group', label: 'グループ' },
            { key: 'staff', label: '社内' },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => {
                setActiveTab(tab.key as TabType);
                setSelectedChannel(null);
                setSelectedStaffChannel(null);
                setShowNewChat(false);
              }}
              className={`flex-1 py-2.5 text-sm font-medium transition-all relative ${
                activeTab === tab.key
                  ? 'text-blue-600'
                  : 'text-gray-500'
              }`}
            >
              {tab.label}
              {activeTab === tab.key && (
                <div className="absolute bottom-0 left-2 right-2 h-0.5 bg-blue-600 rounded-full" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* 検索バー */}
      <div className="px-4 py-3 bg-white border-b">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="名前で検索..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="pl-10 bg-gray-100 border-0 rounded-full h-9 text-sm"
          />
        </div>
      </div>

      {/* 新規チャット作成（社員タブ） */}
      {activeTab === 'staff' && showNewChat && (
        <div className="bg-white border-b">
          <div className="px-4 py-2 bg-gray-50 flex items-center justify-between">
            <p className="text-xs font-medium text-gray-500">メンバーを選択</p>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full transition-colors ${
                showFilters || filterSchool || filterBrand
                  ? 'bg-blue-100 text-blue-600'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <Filter className="w-3 h-3" />
              絞り込み
              {(filterSchool || filterBrand) && (
                <span className="ml-1 bg-blue-500 text-white rounded-full w-4 h-4 flex items-center justify-center text-[10px]">
                  {(filterSchool ? 1 : 0) + (filterBrand ? 1 : 0)}
                </span>
              )}
            </button>
          </div>

          {/* フィルター */}
          {showFilters && (
            <div className="px-4 py-3 bg-gray-50 border-b space-y-2">
              <div className="flex gap-2">
                <Select value={filterSchool} onValueChange={setFilterSchool}>
                  <SelectTrigger className="flex-1 h-9 text-sm bg-white">
                    <SelectValue placeholder="教室で絞り込み" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">すべての教室</SelectItem>
                    {schools.map(school => (
                      <SelectItem key={school.id} value={school.id}>
                        {school.schoolName}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={filterBrand} onValueChange={setFilterBrand}>
                  <SelectTrigger className="flex-1 h-9 text-sm bg-white">
                    <SelectValue placeholder="ブランドで絞り込み" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">すべてのブランド</SelectItem>
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
                    setFilterSchool('');
                    setFilterBrand('');
                  }}
                  className="text-xs text-blue-600 hover:underline"
                >
                  フィルターをクリア
                </button>
              )}
            </div>
          )}

          <div className="max-h-64 overflow-y-auto">
            {staffList.map(staff => {
              const avatarColors = [
                'from-pink-400 to-rose-500',
                'from-blue-400 to-indigo-500',
                'from-green-400 to-emerald-500',
                'from-purple-400 to-violet-500',
                'from-orange-400 to-amber-500',
                'from-cyan-400 to-teal-500',
              ];
              const colorIndex = staff.fullName.charCodeAt(0) % avatarColors.length;

              return (
                <div
                  key={staff.id}
                  className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors border-b border-gray-50"
                >
                  {/* アバター - クリックで詳細表示 */}
                  <button
                    onClick={() => {
                      setSelectedStaffDetail(staff);
                      setShowStaffDetail(true);
                    }}
                    className="relative"
                  >
                    <Avatar className="w-11 h-11">
                      <AvatarFallback className={`bg-gradient-to-br ${avatarColors[colorIndex]} text-white text-sm font-medium`}>
                        {staff.fullName.substring(0, 2)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="absolute -bottom-0.5 -right-0.5 bg-white rounded-full p-0.5">
                      <User className="w-3 h-3 text-gray-400" />
                    </div>
                  </button>

                  {/* 情報 - クリックでDM作成 */}
                  <button
                    onClick={() => handleCreateStaffDM(staff.id)}
                    className="flex-1 text-left"
                  >
                    <p className="font-medium text-gray-900 text-sm">{staff.fullName}</p>
                    {staff.positionName && (
                      <p className="text-xs text-gray-500">{staff.positionName}</p>
                    )}
                    {(staff.schoolsList.length > 0 || staff.brandsList.length > 0) && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {staff.brandsList.slice(0, 2).map(b => (
                          <span key={b.id} className="text-[10px] px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded">
                            {b.name}
                          </span>
                        ))}
                        {staff.schoolsList.slice(0, 2).map(s => (
                          <span key={s.id} className="text-[10px] px-1.5 py-0.5 bg-blue-100 text-blue-600 rounded">
                            {s.name}
                          </span>
                        ))}
                        {(staff.schoolsList.length + staff.brandsList.length > 4) && (
                          <span className="text-[10px] text-gray-400">
                            +{staff.schoolsList.length + staff.brandsList.length - 4}
                          </span>
                        )}
                      </div>
                    )}
                  </button>

                  {/* メッセージアイコン */}
                  <button
                    onClick={() => handleCreateStaffDM(staff.id)}
                    className="p-2 text-blue-500 hover:bg-blue-50 rounded-full transition-colors"
                  >
                    <MessageCircle className="w-5 h-5" />
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

      {/* スタッフ詳細シート */}
      <Sheet open={showStaffDetail} onOpenChange={setShowStaffDetail}>
        <SheetContent side="bottom" className="h-[70vh] rounded-t-2xl">
          {selectedStaffDetail && (
            <>
              <SheetHeader className="text-left pb-4 border-b">
                <div className="flex items-start gap-4">
                  <Avatar className="w-16 h-16">
                    <AvatarFallback className="bg-gradient-to-br from-blue-400 to-indigo-500 text-white text-xl font-medium">
                      {selectedStaffDetail.fullName.substring(0, 2)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <SheetTitle className="text-lg">{selectedStaffDetail.fullName}</SheetTitle>
                    {selectedStaffDetail.positionName && (
                      <p className="text-sm text-gray-500 mt-0.5">{selectedStaffDetail.positionName}</p>
                    )}
                    {selectedStaffDetail.department && (
                      <p className="text-xs text-gray-400 mt-0.5">{selectedStaffDetail.department}</p>
                    )}
                  </div>
                </div>
              </SheetHeader>

              <div className="py-4 space-y-4">
                {/* 連絡先 */}
                <div className="space-y-2">
                  <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">連絡先</h3>
                  {selectedStaffDetail.email && (
                    <div className="flex items-center gap-3 px-3 py-2 bg-gray-50 rounded-lg">
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <MessageCircle className="w-4 h-4 text-blue-600" />
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">メール</p>
                        <p className="text-sm text-gray-900">{selectedStaffDetail.email}</p>
                      </div>
                    </div>
                  )}
                  {selectedStaffDetail.phone && (
                    <div className="flex items-center gap-3 px-3 py-2 bg-gray-50 rounded-lg">
                      <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                        <Phone className="w-4 h-4 text-green-600" />
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">電話</p>
                        <p className="text-sm text-gray-900">{selectedStaffDetail.phone}</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* 担当ブランド */}
                {selectedStaffDetail.brandsList.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider flex items-center gap-2">
                      <Briefcase className="w-3 h-3" />
                      担当ブランド
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedStaffDetail.brandsList.map(brand => (
                        <span
                          key={brand.id}
                          className="px-3 py-1.5 bg-purple-100 text-purple-700 rounded-full text-sm"
                        >
                          {brand.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* 担当教室 */}
                {selectedStaffDetail.schoolsList.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider flex items-center gap-2">
                      <MapPin className="w-3 h-3" />
                      担当教室
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedStaffDetail.schoolsList.map(school => (
                        <span
                          key={school.id}
                          className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-full text-sm"
                        >
                          {school.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* アクション */}
                <div className="pt-4 border-t">
                  <Button
                    onClick={() => {
                      handleCreateStaffDM(selectedStaffDetail.id);
                      setShowStaffDetail(false);
                    }}
                    className="w-full bg-blue-600 hover:bg-blue-700"
                  >
                    <MessageCircle className="w-4 h-4 mr-2" />
                    メッセージを送る
                  </Button>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* チャンネル一覧 */}
      <div className="bg-white">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
          </div>
        ) : currentChannels.length === 0 && !showNewChat ? (
          <div className="text-center py-16 px-4">
            <div className="w-20 h-20 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <MessageCircle className="w-10 h-10 text-gray-400" />
            </div>
            <p className="text-gray-500 text-sm">
              {searchQuery ? '検索結果がありません' : 'トークがありません'}
            </p>
            {activeTab === 'staff' && !searchQuery && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowNewChat(true)}
                className="mt-4"
              >
                <UserPlus className="w-4 h-4 mr-2" />
                トークを開始
              </Button>
            )}
          </div>
        ) : (
          !showNewChat && currentChannels.map(channel => {
            const lastMessage = 'lastMessage' in channel ? channel.lastMessage : null;
            const unreadCount = channel.unreadCount || 0;
            const displayName = getChannelDisplayName(channel);

            const avatarColors = [
              'from-pink-400 to-rose-500',
              'from-blue-400 to-indigo-500',
              'from-green-400 to-emerald-500',
              'from-purple-400 to-violet-500',
              'from-orange-400 to-amber-500',
              'from-cyan-400 to-teal-500',
            ];
            const colorIndex = displayName.charCodeAt(0) % avatarColors.length;

            return (
              <button
                key={channel.id}
                onClick={() => {
                  if (activeTab === 'staff') {
                    setSelectedStaffChannel(channel as StaffChannel);
                  } else {
                    setSelectedChannel(channel as Channel);
                  }
                }}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors active:bg-gray-100 border-b border-gray-100"
              >
                <div className="relative flex-shrink-0">
                  <Avatar className="w-12 h-12">
                    <AvatarFallback className={`bg-gradient-to-br ${avatarColors[colorIndex]} text-white font-medium`}>
                      {activeTab === 'group' ? (
                        <Users className="w-5 h-5" />
                      ) : (
                        getChannelAvatar(channel)
                      )}
                    </AvatarFallback>
                  </Avatar>
                  {unreadCount > 0 && (
                    <div className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-xs font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </div>
                  )}
                </div>

                <div className="flex-1 min-w-0 text-left">
                  <div className="flex items-center justify-between mb-0.5">
                    <h3 className={`text-[15px] truncate ${unreadCount > 0 ? 'font-semibold text-gray-900' : 'font-medium text-gray-800'}`}>
                      {displayName}
                    </h3>
                    {lastMessage && (
                      <span className="text-xs text-gray-400 flex-shrink-0 ml-2">
                        {isToday(new Date(lastMessage.createdAt))
                          ? format(new Date(lastMessage.createdAt), 'HH:mm')
                          : isYesterday(new Date(lastMessage.createdAt))
                          ? '昨日'
                          : format(new Date(lastMessage.createdAt), 'M/d')}
                      </span>
                    )}
                  </div>
                  {lastMessage ? (
                    <p className={`text-sm truncate ${unreadCount > 0 ? 'text-gray-700' : 'text-gray-500'}`}>
                      {lastMessage.content}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-400">メッセージがありません</p>
                  )}
                </div>
              </button>
            );
          })
        )}
      </div>

      <BottomNav />
    </div>
  );
}
