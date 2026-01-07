'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { X, User, MessageCircle, Edit, Phone, Mail, Calendar, School, Users, Ticket, FileText, AlertCircle, Loader2, ChevronRight, Send, History, ClipboardList } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { getStudent, getStudentGuardians } from '@/lib/api/students';
import { getChannels, createChannel, getMessages, sendMessage, type Channel, type Message } from '@/lib/api/chat';
import { getContracts, type Contract } from '@/lib/api/contracts';
import type { Student, StudentDetail, StudentGuardian } from '@/lib/api/types';

interface StudentDetailModalProps {
  student: Student;
  onClose: () => void;
  onEdit?: (student: Student) => void;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  inquiry: { label: '問い合わせ', color: 'bg-yellow-100 text-yellow-800' },
  trial: { label: '体験', color: 'bg-blue-100 text-blue-800' },
  enrolled: { label: '在籍', color: 'bg-green-100 text-green-800' },
  suspended: { label: '休会', color: 'bg-orange-100 text-orange-800' },
  withdrawn: { label: '退会', color: 'bg-gray-100 text-gray-800' },
};

export function StudentDetailModal({ student, onClose, onEdit }: StudentDetailModalProps) {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [studentDetail, setStudentDetail] = useState<StudentDetail | null>(null);
  const [guardians, setGuardians] = useState<StudentGuardian[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'basic' | 'guardian' | 'contract' | 'communication'>('basic');

  // チャット用state
  const [communicationTab, setCommunicationTab] = useState<'history' | 'chat' | 'request'>('chat');
  const [chatChannels, setChatChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [chatMessages, setChatMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [channelsLoading, setChannelsLoading] = useState(false);
  const [showNewChatForm, setShowNewChatForm] = useState(false);
  const [newChatTitle, setNewChatTitle] = useState('');
  const [creatingChat, setCreatingChat] = useState(false);

  const fetchDetails = useCallback(async () => {
    try {
      setLoading(true);
      const [detail, guardiansRes, contractsRes] = await Promise.all([
        getStudent(student.id).catch(() => null),
        getStudentGuardians(student.id).catch(() => []),
        getContracts({ studentId: student.id }).catch(() => ({ results: [] })),
      ]);
      if (detail) setStudentDetail(detail);
      setGuardians(guardiansRes || []);
      setContracts(contractsRes?.results || []);
    } catch (err) {
      console.error('Failed to fetch student details:', err);
    } finally {
      setLoading(false);
    }
  }, [student.id]);

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  const handleStartChat = async () => {
    // 保護者とのチャットを開始
    const guardianId = student.guardian_id || guardians[0]?.guardian_id;

    if (!guardianId) {
      alert('保護者情報が見つかりません');
      return;
    }

    setChatLoading(true);
    try {
      // 既存のチャンネルを探す
      const channels = await getChannels({ guardianId, studentId: student.id });

      if (channels && channels.length > 0) {
        // 既存のチャンネルがあればそこに遷移
        router.push(`/messages?channel_id=${channels[0].id}`);
      } else {
        // 新しいチャンネルを作成
        const studentName = student.full_name || `${student.last_name || ''} ${student.first_name || ''}`.trim() || '生徒';
        const newChannel = await createChannel({
          channelType: 'direct',
          name: `${studentName}様`,
          guardianId,
          studentId: student.id,
        });
        router.push(`/messages?channel_id=${newChannel.id}`);
      }
    } catch (err) {
      console.error('Failed to start chat:', err);
      alert('チャットの開始に失敗しました');
    } finally {
      setChatLoading(false);
    }
  };

  // チャンネル一覧を読み込む
  const loadChannels = useCallback(async () => {
    const guardianId = student.guardian_id || guardians[0]?.guardian_id;
    if (!guardianId) return;

    setChannelsLoading(true);
    try {
      const channels = await getChannels({ guardianId, studentId: student.id });
      setChatChannels(channels || []);
    } catch (err) {
      console.error('Failed to load channels:', err);
    } finally {
      setChannelsLoading(false);
    }
  }, [student.id, student.guardian_id, guardians]);

  // 選択したチャンネルのメッセージを読み込む
  const loadMessages = useCallback(async (channel: Channel) => {
    setMessagesLoading(true);
    try {
      const messagesRes = await getMessages(channel.id, { pageSize: 50 });
      const messages = messagesRes?.results || messagesRes?.data || [];
      setChatMessages(messages.reverse());
    } catch (err) {
      console.error('Failed to load messages:', err);
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  // やりとりタブを開いたときにチャンネル一覧を読み込む
  useEffect(() => {
    if (activeTab === 'communication' && communicationTab === 'chat' && !loading) {
      loadChannels();
    }
  }, [activeTab, communicationTab, loading, loadChannels]);

  // チャンネル選択時にメッセージを読み込む
  useEffect(() => {
    if (selectedChannel) {
      loadMessages(selectedChannel);
    }
  }, [selectedChannel, loadMessages]);

  // メッセージ送信
  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedChannel) return;

    setSendingMessage(true);
    try {
      const sentMessage = await sendMessage({
        channelId: selectedChannel.id,
        content: newMessage.trim(),
      });

      setChatMessages(prev => [...prev, sentMessage]);
      setNewMessage('');

      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch (err) {
      console.error('Failed to send message:', err);
      alert('メッセージの送信に失敗しました');
    } finally {
      setSendingMessage(false);
    }
  };

  // 新規チャット作成
  const handleCreateNewChat = async () => {
    const guardianId = student.guardian_id || guardians[0]?.guardian_id;
    if (!guardianId) {
      alert('保護者情報が見つかりません');
      return;
    }

    if (!newChatTitle.trim()) {
      alert('タイトルを入力してください');
      return;
    }

    setCreatingChat(true);
    try {
      const newChannel = await createChannel({
        channelType: 'direct',
        name: newChatTitle.trim(),
        guardianId,
        studentId: student.id,
      });

      setChatChannels(prev => [newChannel, ...prev]);
      setSelectedChannel(newChannel);
      setShowNewChatForm(false);
      setNewChatTitle('');
    } catch (err) {
      console.error('Failed to create chat:', err);
      alert('チャットの作成に失敗しました');
    } finally {
      setCreatingChat(false);
    }
  };

  // スレッド一覧に戻る
  const handleBackToList = () => {
    setSelectedChannel(null);
    setChatMessages([]);
  };

  // メッセージの日時フォーマット
  const formatMessageTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();

    if (isToday) {
      return date.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const handleEdit = () => {
    onEdit?.(student);
  };

  const statusInfo = STATUS_LABELS[student.status] || { label: student.status, color: 'bg-gray-100 text-gray-800' };
  const studentName = student.full_name || `${student.last_name || ''} ${student.first_name || ''}`.trim() || '名前未設定';
  const studentNameKana = `${student.last_name_kana || ''} ${student.first_name_kana || ''}`.trim();

  const tabs = [
    { key: 'basic', label: '基本情報' },
    { key: 'guardian', label: '保護者' },
    { key: 'contract', label: '契約' },
    { key: 'communication', label: 'やりとり' },
  ] as const;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 bg-gradient-to-r from-blue-600 to-blue-700 text-white px-5 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center">
                <User className="w-7 h-7" />
              </div>
              <div>
                <h2 className="text-xl font-bold">{studentName}</h2>
                {studentNameKana && (
                  <p className="text-blue-100 text-sm">{studentNameKana}</p>
                )}
                <p className="text-blue-200 text-xs mt-0.5">
                  No. {student.student_no || student.id.slice(0, 8)}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={`${statusInfo.color} font-medium`}>
                {statusInfo.label}
              </Badge>
              <button
                onClick={onClose}
                className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex-shrink-0 flex border-b bg-gray-50">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-white'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            </div>
          ) : (
            <>
              {activeTab === 'basic' && (
                <div className="space-y-4">
                  {/* 生徒情報 */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <User className="w-4 h-4 text-blue-600" />
                      生徒情報
                    </h3>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-gray-500">生徒ID:</span>
                        <span className="ml-2 font-medium">{student.student_no || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">学年:</span>
                        <span className="ml-2 font-medium">{student.grade_name || student.grade_text || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">生年月日:</span>
                        <span className="ml-2 font-medium">{student.birth_date || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">性別:</span>
                        <span className="ml-2 font-medium">
                          {student.gender === 'male' ? '男性' : student.gender === 'female' ? '女性' : '-'}
                        </span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-gray-500">学校名:</span>
                        <span className="ml-2 font-medium">{student.school_name || '-'}</span>
                      </div>
                    </div>
                  </div>

                  {/* 在籍情報 */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <School className="w-4 h-4 text-blue-600" />
                      在籍情報
                    </h3>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-gray-500">校舎:</span>
                        <span className="ml-2 font-medium">{student.primary_school_name || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">ブランド:</span>
                        <span className="ml-2 font-medium">{student.primary_brand_name || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">入塾日:</span>
                        <span className="ml-2 font-medium">{student.enrollment_date || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">ステータス:</span>
                        <Badge className={`ml-2 ${statusInfo.color}`}>{statusInfo.label}</Badge>
                      </div>
                    </div>
                  </div>

                  {/* チケット情報 */}
                  {studentDetail?.tickets && (
                    <div className="bg-blue-50 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        <Ticket className="w-4 h-4 text-blue-600" />
                        チケット残高
                      </h3>
                      <div className="flex items-center justify-between">
                        <span className="text-3xl font-bold text-blue-600">
                          {studentDetail.tickets.total_available}
                        </span>
                        <span className="text-gray-500">枚</span>
                      </div>
                    </div>
                  )}

                  {/* 備考 */}
                  {student.notes && (
                    <div className="bg-yellow-50 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                        <FileText className="w-4 h-4 text-yellow-600" />
                        特記事項
                      </h3>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">{student.notes}</p>
                    </div>
                  )}

                  {!student.notes && (
                    <div className="bg-gray-50 rounded-lg p-4 text-center text-gray-500 text-sm">
                      特記事項なし
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'guardian' && (
                <div className="space-y-4">
                  {/* 保護者情報 */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <Users className="w-4 h-4 text-blue-600" />
                      保護者情報
                    </h3>
                    {guardians.length > 0 ? (
                      <div className="space-y-3">
                        {guardians.map((g, idx) => (
                          <div key={g.id} className="bg-white rounded-lg p-3 border">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium">
                                {g.guardian?.full_name || g.guardian?.email || '保護者'}
                              </span>
                              {g.is_primary && (
                                <Badge className="bg-blue-100 text-blue-700 text-xs">主保護者</Badge>
                              )}
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                              <div className="flex items-center gap-1">
                                <Mail className="w-3 h-3" />
                                {g.guardian?.email || '-'}
                              </div>
                              <div className="flex items-center gap-1">
                                <Phone className="w-3 h-3" />
                                {g.guardian?.phone_number || '-'}
                              </div>
                              <div>
                                <span className="text-gray-500">続柄:</span>
                                <span className="ml-1">{g.relationship || '-'}</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-4">
                        <p className="text-gray-500 text-sm">保護者情報が登録されていません</p>
                        {/* 既存の保護者情報を表示 */}
                        {student.guardian_name && (
                          <div className="mt-3 bg-white rounded-lg p-3 border text-left">
                            <p className="font-medium">{student.guardian_name}</p>
                            {student.guardian_phone && (
                              <p className="text-sm text-gray-600 flex items-center gap-1 mt-1">
                                <Phone className="w-3 h-3" />
                                {student.guardian_phone}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'contract' && (
                <div className="space-y-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-blue-600" />
                      契約情報
                    </h3>
                    {contracts.length > 0 ? (
                      <div className="space-y-2">
                        {contracts.map(contract => (
                          <div
                            key={contract.id}
                            className="bg-white rounded-lg p-3 border flex items-center justify-between hover:bg-gray-50 cursor-pointer"
                            onClick={() => router.push(`/contracts/${contract.id}`)}
                          >
                            <div>
                              <p className="font-medium text-sm">
                                {contract.course_name || contract.contract_no || '契約'}
                              </p>
                              <p className="text-xs text-gray-500 mt-0.5">
                                {contract.start_date} ~ {contract.end_date || '継続中'}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge className={
                                contract.status === 'active' ? 'bg-green-100 text-green-700' :
                                contract.status === 'suspended' ? 'bg-orange-100 text-orange-700' :
                                contract.status === 'cancelled' ? 'bg-gray-100 text-gray-700' :
                                'bg-blue-100 text-blue-700'
                              }>
                                {contract.status === 'active' ? '有効' :
                                 contract.status === 'suspended' ? '休会中' :
                                 contract.status === 'cancelled' ? '退会' : contract.status}
                              </Badge>
                              <ChevronRight className="w-4 h-4 text-gray-400" />
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500 text-sm">
                        契約情報がありません
                      </div>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => router.push(`/contracts?student_id=${student.id}`)}
                  >
                    契約一覧を見る
                  </Button>
                </div>
              )}

              {activeTab === 'communication' && (
                <div className="flex flex-col h-full -mx-5 -mt-5">
                  {/* サブタブ */}
                  <div className="flex border-b bg-white px-4">
                    <button
                      onClick={() => setCommunicationTab('history')}
                      className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                        communicationTab === 'history'
                          ? 'text-blue-600 border-blue-600'
                          : 'text-gray-500 border-transparent hover:text-gray-700'
                      }`}
                    >
                      <History className="w-4 h-4 inline mr-1" />
                      対応履歴 (0)
                    </button>
                    <button
                      onClick={() => setCommunicationTab('chat')}
                      className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                        communicationTab === 'chat'
                          ? 'text-blue-600 border-blue-600'
                          : 'text-gray-500 border-transparent hover:text-gray-700'
                      }`}
                    >
                      <MessageCircle className="w-4 h-4 inline mr-1" />
                      チャット ({chatMessages.length})
                    </button>
                    <button
                      onClick={() => setCommunicationTab('request')}
                      className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                        communicationTab === 'request'
                          ? 'text-blue-600 border-blue-600'
                          : 'text-gray-500 border-transparent hover:text-gray-700'
                      }`}
                    >
                      <ClipboardList className="w-4 h-4 inline mr-1" />
                      申請履歴 (0)
                    </button>
                  </div>

                  {/* コンテンツエリア */}
                  <div className="flex-1 flex flex-col min-h-[300px]">
                    {communicationTab === 'history' && (
                      <div className="flex-1 flex items-center justify-center p-4">
                        <p className="text-gray-500 text-sm">対応履歴がありません</p>
                      </div>
                    )}

                    {communicationTab === 'chat' && (
                      <div className="flex-1 flex flex-col">
                        {/* スレッド選択中: メッセージ表示 */}
                        {selectedChannel ? (
                          <>
                            {/* スレッドヘッダー */}
                            <div className="flex items-center gap-2 px-4 py-2 bg-white border-b">
                              <button
                                onClick={handleBackToList}
                                className="p-1 hover:bg-gray-100 rounded"
                              >
                                <ChevronRight className="w-4 h-4 rotate-180 text-gray-500" />
                              </button>
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm truncate">{selectedChannel.name}</p>
                                <p className="text-xs text-gray-500">
                                  {selectedChannel.lastMessage?.createdAt
                                    ? formatMessageTime(selectedChannel.lastMessage.createdAt)
                                    : ''}
                                </p>
                              </div>
                            </div>

                            {/* メッセージエリア */}
                            <div className="flex-1 overflow-y-auto p-4 bg-gray-50 min-h-[200px] max-h-[250px]">
                              {messagesLoading ? (
                                <div className="flex items-center justify-center h-full">
                                  <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                                </div>
                              ) : chatMessages.length === 0 ? (
                                <div className="flex items-center justify-center h-full">
                                  <div className="text-center">
                                    <MessageCircle className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                                    <p className="text-gray-500 text-sm">メッセージがありません</p>
                                  </div>
                                </div>
                              ) : (
                                <div className="space-y-3">
                                  {chatMessages.map((msg) => {
                                    const isOwnMessage = !msg.senderGuardian;
                                    return (
                                      <div
                                        key={msg.id}
                                        className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}
                                      >
                                        <div
                                          className={`max-w-[80%] rounded-lg px-3 py-2 ${
                                            isOwnMessage
                                              ? 'bg-blue-600 text-white'
                                              : 'bg-white border text-gray-800'
                                          }`}
                                        >
                                          {!isOwnMessage && (
                                            <p className="text-xs text-gray-500 mb-1">{msg.senderName}</p>
                                          )}
                                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                                          <p className={`text-xs mt-1 ${isOwnMessage ? 'text-blue-200' : 'text-gray-400'}`}>
                                            {formatMessageTime(msg.createdAt)}
                                          </p>
                                        </div>
                                      </div>
                                    );
                                  })}
                                  <div ref={messagesEndRef} />
                                </div>
                              )}
                            </div>

                            {/* メッセージ入力エリア */}
                            <div className="border-t bg-white p-3">
                              <div className="flex gap-2">
                                <Input
                                  value={newMessage}
                                  onChange={(e) => setNewMessage(e.target.value)}
                                  placeholder="メッセージを入力..."
                                  className="flex-1"
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                      e.preventDefault();
                                      handleSendMessage();
                                    }
                                  }}
                                  disabled={sendingMessage}
                                />
                                <Button
                                  onClick={handleSendMessage}
                                  disabled={!newMessage.trim() || sendingMessage}
                                  className="bg-blue-600 hover:bg-blue-700"
                                >
                                  {sendingMessage ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <Send className="w-4 h-4" />
                                  )}
                                </Button>
                              </div>
                            </div>
                          </>
                        ) : (
                          /* スレッド一覧表示 */
                          <>
                            {/* 新規チャットボタン */}
                            <div className="px-4 py-3 border-b bg-white">
                              {showNewChatForm ? (
                                <div className="space-y-2">
                                  <Input
                                    value={newChatTitle}
                                    onChange={(e) => setNewChatTitle(e.target.value)}
                                    placeholder="チャットのタイトルを入力..."
                                    className="text-sm"
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') {
                                        handleCreateNewChat();
                                      }
                                    }}
                                  />
                                  <div className="flex gap-2">
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => {
                                        setShowNewChatForm(false);
                                        setNewChatTitle('');
                                      }}
                                      className="flex-1"
                                    >
                                      キャンセル
                                    </Button>
                                    <Button
                                      size="sm"
                                      onClick={handleCreateNewChat}
                                      disabled={!newChatTitle.trim() || creatingChat}
                                      className="flex-1 bg-blue-600 hover:bg-blue-700"
                                    >
                                      {creatingChat ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                      ) : (
                                        '作成'
                                      )}
                                    </Button>
                                  </div>
                                </div>
                              ) : (
                                <Button
                                  onClick={() => setShowNewChatForm(true)}
                                  className="w-full bg-blue-600 hover:bg-blue-700"
                                  size="sm"
                                >
                                  <MessageCircle className="w-4 h-4 mr-2" />
                                  新規チャット
                                </Button>
                              )}
                            </div>

                            {/* スレッド一覧 */}
                            <div className="flex-1 overflow-y-auto bg-gray-50 min-h-[200px] max-h-[300px]">
                              {channelsLoading ? (
                                <div className="flex items-center justify-center h-full py-8">
                                  <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                                </div>
                              ) : chatChannels.length === 0 ? (
                                <div className="flex items-center justify-center h-full py-8">
                                  <div className="text-center">
                                    <MessageCircle className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                                    <p className="text-gray-500 text-sm">チャット履歴がありません</p>
                                    <p className="text-gray-400 text-xs mt-1">上のボタンから新規チャットを開始できます</p>
                                  </div>
                                </div>
                              ) : (
                                <div className="divide-y">
                                  {chatChannels.map((channel) => (
                                    <button
                                      key={channel.id}
                                      onClick={() => setSelectedChannel(channel)}
                                      className="w-full px-4 py-3 flex items-center gap-3 hover:bg-white transition-colors text-left"
                                    >
                                      <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                                        <MessageCircle className="w-5 h-5 text-blue-600" />
                                      </div>
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between gap-2">
                                          <p className="font-medium text-sm truncate">{channel.name}</p>
                                          {channel.unreadCount > 0 && (
                                            <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                                              {channel.unreadCount}
                                            </span>
                                          )}
                                        </div>
                                        {channel.lastMessage && (
                                          <p className="text-xs text-gray-500 truncate mt-0.5">
                                            {channel.lastMessage.content}
                                          </p>
                                        )}
                                        <p className="text-xs text-gray-400 mt-0.5">
                                          {channel.lastMessage?.createdAt
                                            ? formatMessageTime(channel.lastMessage.createdAt)
                                            : formatMessageTime(channel.createdAt)}
                                        </p>
                                      </div>
                                      <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                    )}

                    {communicationTab === 'request' && (
                      <div className="flex-1 flex items-center justify-center p-4">
                        <p className="text-gray-500 text-sm">申請履歴がありません</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex-shrink-0 border-t bg-gray-50 px-5 py-3">
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setActiveTab('communication')}
              className="flex-1"
            >
              <MessageCircle className="w-4 h-4 mr-2" />
              やりとり
            </Button>
            <Button
              onClick={handleEdit}
              className="flex-1 bg-green-600 hover:bg-green-700"
            >
              <Edit className="w-4 h-4 mr-2" />
              編集
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
