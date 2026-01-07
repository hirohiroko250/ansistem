'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { BottomNav } from '@/components/bottom-nav';
import { ChatSidebar, ChatMessages, ThreadPanel, ChannelSettingsModal, SearchPanel, CreateGroupModal, CreateTaskModal, type TabType } from '@/components/chat';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { MessageCircle, Phone, Briefcase, MapPin, Menu } from 'lucide-react';
import {
  getChannels,
  getMessages,
  sendMessage,
  markChannelAsRead,
  getStaffChannels,
  getStaffMessages,
  sendStaffMessage,
  createStaffDM,
  addReaction,
  removeReaction,
  getMentionableUsers,
  uploadFile,
  toggleChannelPin,
  toggleChannelMute,
  archiveChannel,
  editMessage,
  deleteMessage,
  type Channel,
  type Message,
  type StaffChannel,
  type MessageReaction,
  type MentionableUser,
  type FileUploadProgress,
  type SearchResult,
} from '@/lib/api/chat';
import { getAccessToken } from '@/lib/api/client';
import api from '@/lib/api/client';
import { useChatWebSocket, useTypingUsers } from '@/lib/hooks/useWebSocket';

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

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = searchParams.get('tab') as TabType | null;

  const [activeTab, setActiveTab] = useState<TabType>(initialTab || 'guardian');
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);

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

  // Mobile view state - true: メッセージ画面, false: 一覧画面
  const [showMessages, setShowMessages] = useState(false);

  // Thread state
  const [threadMessage, setThreadMessage] = useState<Message | null>(null);
  const [showThread, setShowThread] = useState(false);

  // Mention state
  const [mentionableUsers, setMentionableUsers] = useState<MentionableUser[]>([]);

  // File upload state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<FileUploadProgress | null>(null);

  // Channel settings modal state
  const [showChannelSettings, setShowChannelSettings] = useState(false);

  // Search panel state
  const [showSearch, setShowSearch] = useState(false);

  // Create group modal state
  const [showCreateGroup, setShowCreateGroup] = useState(false);

  // Create task modal state
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [taskTargetMessage, setTaskTargetMessage] = useState<Message | null>(null);

  const currentUserId = getCurrentUserId();
  const accessToken = getAccessToken() || '';

  // WebSocket integration
  const currentChannelId = activeTab === 'staff'
    ? selectedStaffChannel?.id || null
    : selectedChannel?.id || null;

  const { typingUsers, handleTypingEvent } = useTypingUsers();

  const { isConnected, sendMessage: wsSendMessage, sendTyping } = useChatWebSocket(
    currentChannelId,
    accessToken,
    {
      onMessage: (msg) => {
        // Add new message to the list
        const newMsg: Message = {
          id: msg.id,
          channel: currentChannelId || '',
          channelId: currentChannelId || '',
          senderName: msg.senderName,
          sender: msg.senderId,
          senderId: msg.senderId,
          messageType: 'text',
          content: msg.content,
          isRead: false,
          isEdited: false,
          isBotMessage: msg.senderType === 'bot',
          createdAt: msg.createdAt,
          updatedAt: msg.createdAt,
        };
        if (activeTab === 'staff') {
          setStaffMessages(prev => [...prev, newMsg]);
        } else {
          setMessages(prev => [...prev, newMsg]);
        }
      },
      onTyping: handleTypingEvent,
      onThreadReply: (event) => {
        // Update reply count for parent message
        const updateFn = (msgs: Message[]) =>
          msgs.map(msg =>
            msg.id === event.parentMessageId
              ? { ...msg, replyCount: event.replyCount }
              : msg
          );

        if (activeTab === 'staff') {
          setStaffMessages(prev => updateFn(prev));
        } else {
          setMessages(prev => updateFn(prev));
        }
      },
      onReactionAdded: (event) => {
        // Add reaction to message
        const updateFn = (msgs: Message[]) =>
          msgs.map(msg => {
            if (msg.id !== event.messageId) return msg;

            const reactions = msg.reactions || [];
            const existingReaction = reactions.find(r => r.emoji === event.emoji);

            if (existingReaction) {
              // Add user to existing reaction
              const alreadyReacted = existingReaction.users.some(u => u.user_id === event.userId);
              if (!alreadyReacted) {
                return {
                  ...msg,
                  reactions: reactions.map(r =>
                    r.emoji === event.emoji
                      ? {
                          ...r,
                          count: r.count + 1,
                          users: [...r.users, { user_id: event.userId, user_name: event.userName }]
                        }
                      : r
                  )
                };
              }
              return msg;
            } else {
              // Create new reaction
              return {
                ...msg,
                reactions: [
                  ...reactions,
                  {
                    emoji: event.emoji,
                    count: 1,
                    users: [{ user_id: event.userId, user_name: event.userName }]
                  }
                ]
              };
            }
          });

        if (activeTab === 'staff') {
          setStaffMessages(prev => updateFn(prev));
        } else {
          setMessages(prev => updateFn(prev));
        }
      },
      onReactionRemoved: (event) => {
        // Remove reaction from message
        const updateFn = (msgs: Message[]) =>
          msgs.map(msg => {
            if (msg.id !== event.messageId) return msg;

            const reactions = msg.reactions || [];
            const updatedReactions = reactions
              .map(r => {
                if (r.emoji !== event.emoji) return r;
                const filteredUsers = r.users.filter(u => u.user_id !== event.userId);
                return filteredUsers.length > 0
                  ? { ...r, count: filteredUsers.length, users: filteredUsers }
                  : null;
              })
              .filter((r): r is MessageReaction => r !== null);

            return { ...msg, reactions: updatedReactions };
          });

        if (activeTab === 'staff') {
          setStaffMessages(prev => updateFn(prev));
        } else {
          setMessages(prev => updateFn(prev));
        }
      },
      autoConnect: !!currentChannelId,
    }
  );

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

  // 選択したチャンネルのメッセージを取得（WebSocket接続時は初回のみ）
  useEffect(() => {
    if (selectedChannel) {
      loadMessages();
      // WebSocket接続がない場合のみポーリング
      if (!isConnected) {
        const interval = setInterval(loadMessages, 5000);
        return () => clearInterval(interval);
      }
    }
  }, [selectedChannel?.id, isConnected]);

  // 選択したスタッフチャンネルのメッセージを取得
  useEffect(() => {
    if (selectedStaffChannel) {
      loadStaffMessagesForChannel();
      // WebSocket接続がない場合のみポーリング
      if (!isConnected) {
        const interval = setInterval(loadStaffMessagesForChannel, 5000);
        return () => clearInterval(interval);
      }
    }
  }, [selectedStaffChannel?.id, isConnected]);

  // メンション可能なユーザーを取得
  useEffect(() => {
    const channelId = activeTab === 'staff' ? selectedStaffChannel?.id : selectedChannel?.id;
    if (channelId) {
      loadMentionableUsers(channelId);
    } else {
      setMentionableUsers([]);
    }
  }, [selectedChannel?.id, selectedStaffChannel?.id, activeTab]);

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

  const loadStaffListWithDetails = async () => {
    try {
      const params = new URLSearchParams();
      if (filterSchool) params.append('school', filterSchool);
      if (filterBrand) params.append('brand', filterBrand);

      const url = `/tenants/employees/${params.toString() ? '?' + params.toString() : ''}`;
      const response = await api.get<any>(url);
      const results = response?.data || response?.results || response || [];

      if (!Array.isArray(results)) {
        console.warn('Staff list response is not an array:', results);
        setStaffList([]);
        return;
      }

      const staffDetails: StaffDetail[] = results.map((e: any) => {
        // APIがcamelCaseまたはsnake_caseで返す可能性があるため両方チェック
        const fullName = (e.fullName || e.full_name || '').trim();
        const lastName = e.lastName || e.last_name || '';
        const firstName = e.firstName || e.first_name || '';
        const combinedName = `${lastName}${firstName}`.trim();
        return {
          id: e.id,
          employeeNo: e.employeeNo || e.employee_no || '',
          fullName: fullName || combinedName || e.email,
          lastName,
          firstName,
          email: e.email || '',
          phone: e.phone || e.mobilePhone || e.mobile_phone || '',
          department: e.department || '',
          positionName: e.positionName || e.position_name || e.position || null,
          profileImageUrl: e.profileImageUrl || e.profile_image_url || null,
          schoolsList: Array.isArray(e.schoolsList || e.schools_list)
            ? (e.schoolsList || e.schools_list).map((s: any) => ({ id: s.id, name: s.schoolName || s.school_name || s.name }))
            : [],
          brandsList: Array.isArray(e.brandsList || e.brands_list)
            ? (e.brandsList || e.brands_list).map((b: any) => ({ id: b.id, name: b.brandName || b.brand_name || b.name }))
            : [],
        };
      });

      setStaffList(staffDetails);
    } catch (error) {
      console.error('Failed to load staff list with details:', error);
      setStaffList([]);
    }
  };

  const loadSchoolsAndBrands = async () => {
    try {
      const schoolsResponse = await api.get<any>('/schools/schools/');
      const schoolsData = schoolsResponse?.results || schoolsResponse || [];
      if (Array.isArray(schoolsData)) {
        setSchools(schoolsData.map((s: any) => ({
          id: s.id,
          schoolName: s.school_name || s.name,
        })));
      }

      const brandsResponse = await api.get<any>('/schools/brands/');
      const brandsData = brandsResponse?.results || brandsResponse || [];
      if (Array.isArray(brandsData)) {
        setBrands(brandsData.map((b: any) => ({
          id: b.id,
          brandName: b.brand_name || b.name,
        })));
      }
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

  const loadMentionableUsers = async (channelId: string) => {
    try {
      const users = await getMentionableUsers(channelId);
      setMentionableUsers(users);
    } catch (error) {
      console.error('Failed to load mentionable users:', error);
      setMentionableUsers([]);
    }
  };

  const handleSendMessage = async (content: string, replyTo?: string) => {
    if (!content.trim() || isSending) return;

    setIsSending(true);

    if (activeTab === 'staff' && selectedStaffChannel) {
      try {
        // Staff messages - use sendMessage with replyTo support
        await sendMessage({
          channelId: selectedStaffChannel.id,
          content,
          messageType: 'text',
          replyTo,
        });
        if (!isConnected) {
          await loadStaffMessagesForChannel();
        }
      } catch (error) {
        console.error('Failed to send staff message:', error);
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
        replyTo,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      setMessages(prev => [...prev, tempMessage]);

      try {
        const sentMessage = await sendMessage({
          channelId: selectedChannel.id,
          content,
          messageType: 'text',
          replyTo,
        });
        setMessages(prev =>
          prev.map(msg => (msg.id === tempMessage.id ? sentMessage : msg))
        );
      } catch (error) {
        console.error('Failed to send message:', error);
        setMessages(prev => prev.filter(msg => msg.id !== tempMessage.id));
      } finally {
        setIsSending(false);
      }
    }
  };

  const handleCreateStaffDM = async (staffId: string) => {
    try {
      const channel = await createStaffDM(staffId);
      await loadStaffChannels();
      setSelectedStaffChannel(channel);
      setShowNewChat(false);
      setShowMessages(true);
    } catch (error) {
      console.error('Failed to create staff DM:', error);
    }
  };

  const handleSelectChannel = (channel: Channel | StaffChannel) => {
    if (activeTab === 'staff') {
      setSelectedStaffChannel(channel as StaffChannel);
    } else {
      setSelectedChannel(channel as Channel);
    }
    setShowMessages(true);
  };

  // チャンネルのピン留めを切り替え
  const handleTogglePin = async (channelId: string) => {
    try {
      const result = await toggleChannelPin(channelId);
      // チャンネル一覧を更新
      if (activeTab === 'staff') {
        setStaffChannels(prev =>
          prev.map(c => c.id === channelId ? { ...c, isPinned: result.is_pinned } : c)
        );
      } else {
        setChannels(prev =>
          prev.map(c => c.id === channelId ? { ...c, isPinned: result.is_pinned } : c)
        );
      }
    } catch (error) {
      console.error('Failed to toggle pin:', error);
    }
  };

  // チャンネルのミュートを切り替え
  const handleToggleMute = async (channelId: string) => {
    try {
      const result = await toggleChannelMute(channelId);
      // チャンネル一覧を更新
      if (activeTab === 'staff') {
        setStaffChannels(prev =>
          prev.map(c => c.id === channelId ? { ...c, isMuted: result.is_muted } : c)
        );
      } else {
        setChannels(prev =>
          prev.map(c => c.id === channelId ? { ...c, isMuted: result.is_muted } : c)
        );
      }
    } catch (error) {
      console.error('Failed to toggle mute:', error);
    }
  };

  // チャンネルをアーカイブ
  const handleArchive = async (channelId: string) => {
    try {
      await archiveChannel(channelId);
      // チャンネル一覧から削除
      if (activeTab === 'staff') {
        setStaffChannels(prev => prev.filter(c => c.id !== channelId));
        if (selectedStaffChannel?.id === channelId) {
          setSelectedStaffChannel(null);
        }
      } else {
        setChannels(prev => prev.filter(c => c.id !== channelId));
        if (selectedChannel?.id === channelId) {
          setSelectedChannel(null);
        }
      }
    } catch (error) {
      console.error('Failed to archive channel:', error);
    }
  };

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    setSelectedChannel(null);
    setSelectedStaffChannel(null);
    setShowNewChat(false);
    setShowMessages(false);
  };

  const handleBack = () => {
    setShowMessages(false); // 一覧画面に戻る
  };

  const handleOpenThread = (message: Message) => {
    setThreadMessage(message);
    setShowThread(true);
  };

  const handleCloseThread = () => {
    setShowThread(false);
    setThreadMessage(null);
  };

  const handleReplyCountUpdate = (messageId: string, count: number) => {
    if (activeTab === 'staff') {
      setStaffMessages(prev =>
        prev.map(msg => msg.id === messageId ? { ...msg, replyCount: count } : msg)
      );
    } else {
      setMessages(prev =>
        prev.map(msg => msg.id === messageId ? { ...msg, replyCount: count } : msg)
      );
    }
  };

  const handleAddReaction = async (messageId: string, emoji: string) => {
    try {
      await addReaction(messageId, emoji);
      // WebSocket will update the UI via onReactionAdded event
    } catch (error) {
      console.error('Failed to add reaction:', error);
    }
  };

  const handleRemoveReaction = async (messageId: string, emoji: string) => {
    try {
      await removeReaction(messageId, emoji);
      // WebSocket will update the UI via onReactionRemoved event
    } catch (error) {
      console.error('Failed to remove reaction:', error);
    }
  };

  // メッセージ編集（Chatwork風）
  const handleEditMessage = async (messageId: string, content: string) => {
    try {
      const updated = await editMessage(messageId, content);
      // Update message in the list
      if (activeTab === 'staff') {
        setStaffMessages(prev =>
          prev.map(msg => msg.id === messageId ? { ...msg, content: updated.content, isEdited: true } : msg)
        );
      } else {
        setMessages(prev =>
          prev.map(msg => msg.id === messageId ? { ...msg, content: updated.content, isEdited: true } : msg)
        );
      }
    } catch (error) {
      console.error('Failed to edit message:', error);
      alert('メッセージの編集に失敗しました');
    }
  };

  // メッセージ削除（Chatwork風）
  const handleDeleteMessage = async (messageId: string) => {
    try {
      await deleteMessage(messageId);
      // Remove message from the list
      if (activeTab === 'staff') {
        setStaffMessages(prev => prev.filter(msg => msg.id !== messageId));
      } else {
        setMessages(prev => prev.filter(msg => msg.id !== messageId));
      }
    } catch (error) {
      console.error('Failed to delete message:', error);
      alert('メッセージの削除に失敗しました');
    }
  };

  // メッセージからタスク作成（Chatwork風）
  const handleCreateTask = (message: Message) => {
    setTaskTargetMessage(message);
    setShowCreateTask(true);
  };

  const handleTaskCreated = (task: { id: string; title: string }) => {
    alert(`タスク「${task.title}」を作成しました`);
    setShowCreateTask(false);
    setTaskTargetMessage(null);
  };

  const handleFileUpload = async (file: File, content?: string) => {
    const channelId = activeTab === 'staff' ? selectedStaffChannel?.id : selectedChannel?.id;
    if (!channelId) return;

    setIsUploading(true);
    setUploadProgress(null);

    try {
      const message = await uploadFile(
        { channelId, file, content },
        (progress) => setUploadProgress(progress)
      );

      // WebSocketがメッセージを追加するまで待つか、手動で追加
      if (!isConnected) {
        if (activeTab === 'staff') {
          setStaffMessages(prev => [...prev, message]);
        } else {
          setMessages(prev => [...prev, message]);
        }
      }
    } catch (error) {
      console.error('Failed to upload file:', error);
      alert(error instanceof Error ? error.message : 'ファイルのアップロードに失敗しました');
    } finally {
      setIsUploading(false);
      setUploadProgress(null);
    }
  };

  const handleChannelSettingsUpdate = (updatedChannel: StaffChannel) => {
    // Update the channel in the list
    setStaffChannels(prev =>
      prev.map(ch => ch.id === updatedChannel.id ? updatedChannel : ch)
    );
    // Update selected channel if it's the one being edited
    if (selectedStaffChannel?.id === updatedChannel.id) {
      setSelectedStaffChannel(updatedChannel);
    }
  };

  const handleGroupCreated = (channel: StaffChannel) => {
    // Add the new channel to the list
    setStaffChannels(prev => [channel, ...prev]);
    // Select the new channel
    setSelectedStaffChannel(channel);
    setShowMessages(true);
    setShowCreateGroup(false);
  };

  const handleSearchResultClick = (result: SearchResult, channelId: string) => {
    // Find the channel in staff channels first
    const staffChannel = staffChannels.find(ch => ch.id === channelId);
    if (staffChannel) {
      setActiveTab('staff');
      setSelectedStaffChannel(staffChannel);
      setShowMessages(true);
      return;
    }

    // Then check regular channels
    const channel = channels.find(ch => ch.id === channelId);
    if (channel) {
      // Determine the tab based on channel type
      if (channel.channelType === 'direct') {
        setActiveTab('guardian');
      } else {
        setActiveTab('group');
      }
      setSelectedChannel(channel);
      setShowMessages(true);
    }
  };

  const currentSelectedChannel = activeTab === 'staff' ? selectedStaffChannel : selectedChannel;
  const currentMessages = activeTab === 'staff' ? staffMessages : messages;

  return (
    <div className="h-screen flex flex-col bg-gray-50 overflow-hidden">
      {/* グループ作成画面 */}
      {showCreateGroup ? (
        <div className="flex-1 flex flex-col overflow-hidden">
          <CreateGroupModal
            onClose={() => setShowCreateGroup(false)}
            onGroupCreated={handleGroupCreated}
            staffList={staffList.map(s => ({
              id: s.id,
              fullName: s.fullName,
              positionName: s.positionName,
              email: s.email,
            }))}
            currentUserId={currentUserId}
          />
        </div>
      ) : !showMessages ? (
        // チャット一覧画面
        <div className="flex-1 flex flex-col overflow-hidden pb-16">
          <ChatSidebar
            activeTab={activeTab}
            onTabChange={handleTabChange}
            channels={channels}
            staffChannels={staffChannels}
            selectedChannelId={currentSelectedChannel?.id || null}
            onSelectChannel={handleSelectChannel}
            isLoading={isLoading}
            currentUserId={currentUserId}
            showNewChat={showNewChat}
            onToggleNewChat={() => setShowNewChat(!showNewChat)}
            staffList={staffList}
            onCreateStaffDM={handleCreateStaffDM}
            onShowStaffDetail={(staff) => {
              setSelectedStaffDetail(staff);
              setShowStaffDetail(true);
            }}
            onCreateGroup={() => setShowCreateGroup(true)}
            schools={schools}
            brands={brands}
            filterSchool={filterSchool}
            filterBrand={filterBrand}
            onFilterSchoolChange={setFilterSchool}
            onFilterBrandChange={setFilterBrand}
            onOpenSearch={() => setShowSearch(true)}
            onTogglePin={handleTogglePin}
            onToggleMute={handleToggleMute}
            onArchive={handleArchive}
          />
        </div>
      ) : (
        // メッセージ画面
        <div className="flex-1 relative pb-16">
          <ChatMessages
            channel={currentSelectedChannel}
            messages={currentMessages}
            currentUserId={currentUserId}
            isSending={isSending}
            onSendMessage={handleSendMessage}
            onBack={handleBack}
            showBackButton={true}
            typingUsers={typingUsers}
            onOpenThread={handleOpenThread}
            onAddReaction={handleAddReaction}
            onRemoveReaction={handleRemoveReaction}
            mentionableUsers={mentionableUsers}
            onFileUpload={handleFileUpload}
            isUploading={isUploading}
            uploadProgress={uploadProgress}
            onOpenSettings={activeTab === 'staff' && selectedStaffChannel ? () => setShowChannelSettings(true) : undefined}
            onEditMessage={handleEditMessage}
            onDeleteMessage={handleDeleteMessage}
            onCreateTask={handleCreateTask}
          />
        </div>
      )}

      {/* ボトムナビ（グループ作成時は非表示） */}
      {!showCreateGroup && <BottomNav />}

      {/* スレッドパネル */}
      {showThread && threadMessage && currentSelectedChannel && (
        <Sheet open={showThread} onOpenChange={(open) => !open && handleCloseThread()}>
          <SheetContent side="bottom" className="h-[85vh] rounded-t-2xl p-0">
            <ThreadPanel
              parentMessage={threadMessage}
              channelId={currentSelectedChannel.id}
              currentUserId={currentUserId}
              onClose={handleCloseThread}
              onReplyCountUpdate={handleReplyCountUpdate}
            />
          </SheetContent>
        </Sheet>
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

      {/* チャンネル設定モーダル */}
      {selectedStaffChannel && (
        <ChannelSettingsModal
          channel={selectedStaffChannel}
          isOpen={showChannelSettings}
          onClose={() => setShowChannelSettings(false)}
          onChannelUpdate={handleChannelSettingsUpdate}
          currentUserId={currentUserId}
        />
      )}

      {/* 検索パネル */}
      <SearchPanel
        isOpen={showSearch}
        onClose={() => setShowSearch(false)}
        onResultClick={handleSearchResultClick}
        channels={[...channels, ...staffChannels]}
        currentChannelId={currentSelectedChannel?.id}
      />

      {/* タスク作成モーダル */}
      {showCreateTask && taskTargetMessage && currentSelectedChannel && (
        <CreateTaskModal
          message={taskTargetMessage}
          channelId={currentSelectedChannel.id}
          onClose={() => {
            setShowCreateTask(false);
            setTaskTargetMessage(null);
          }}
          onSuccess={handleTaskCreated}
        />
      )}
    </div>
  );
}
