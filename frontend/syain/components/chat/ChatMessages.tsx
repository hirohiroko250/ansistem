'use client';

import { useRef, useEffect, useCallback, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Send,
  Loader2,
  ChevronLeft,
  Plus,
  Image as ImageIcon,
  Phone,
  MoreVertical,
  MessageCircle,
  Reply,
  Smile,
  Paperclip,
  Pencil,
  Trash2,
  Quote,
  Check,
  X,
  ClipboardList,
} from 'lucide-react';
import { format, isToday, isYesterday, isSameDay } from 'date-fns';
import { ja } from 'date-fns/locale';
import type { Channel, Message, StaffChannel, MessageReaction, MentionableUser, FileUploadProgress } from '@/lib/api/chat';
import { EmojiButton } from './EmojiPicker';
import { MentionInput, formatMessageWithMentions } from './MentionInput';
import { FileAttachmentInput, FilePreviewPanel, AttachmentDisplay, DragDropZone } from './FileAttachment';

// よく使うリアクション絵文字（Chatwork風）
const QUICK_REACTIONS = ['👍', '❤️', '😊', '🎉', '👀', '🙏'];

interface ChatMessagesProps {
  channel: Channel | StaffChannel | null;
  messages: Message[];
  currentUserId: string;
  isSending: boolean;
  onSendMessage: (content: string, replyTo?: string) => void;
  onBack?: () => void;
  showBackButton?: boolean;
  // WebSocket typing indicator
  typingUsers?: string[];
  // Thread support
  onOpenThread?: (message: Message) => void;
  // Reaction support
  onAddReaction?: (messageId: string, emoji: string) => void;
  onRemoveReaction?: (messageId: string, emoji: string) => void;
  // Mention support
  mentionableUsers?: MentionableUser[];
  // File attachment support
  onFileUpload?: (file: File, content?: string) => Promise<void>;
  isUploading?: boolean;
  uploadProgress?: FileUploadProgress | null;
  // Channel settings
  onOpenSettings?: () => void;
  // Mobile sidebar
  onOpenSidebar?: () => void;
  // Message edit/delete support (Chatwork style)
  onEditMessage?: (messageId: string, content: string) => Promise<void>;
  onDeleteMessage?: (messageId: string) => Promise<void>;
  // Task creation from message (Chatwork style)
  onCreateTask?: (message: Message) => void;
}

export function ChatMessages({
  channel,
  messages,
  currentUserId,
  isSending,
  onSendMessage,
  onBack,
  showBackButton = false,
  typingUsers = [],
  onOpenThread,
  onAddReaction,
  onRemoveReaction,
  mentionableUsers = [],
  onFileUpload,
  isUploading = false,
  uploadProgress = null,
  onOpenSettings,
  onOpenSidebar,
  onEditMessage,
  onDeleteMessage,
  onCreateTask,
}: ChatMessagesProps) {
  const [hoveredMessageId, setHoveredMessageId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  // 編集中のメッセージ
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  // 引用返信
  const [quotedMessage, setQuotedMessage] = useState<Message | null>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
  };

  const handleFileUpload = async () => {
    if (!selectedFile || !onFileUpload) return;
    try {
      await onFileUpload(selectedFile);
      setSelectedFile(null);
    } catch (error) {
      console.error('Failed to upload file:', error);
    }
  };

  const handleCancelFile = () => {
    setSelectedFile(null);
  };

  const handleReactionClick = (messageId: string, emoji: string, reactions: MessageReaction[] = []) => {
    // Check if user already reacted with this emoji
    const reaction = reactions.find(r => r.emoji === emoji);
    const hasReacted = reaction?.users.some(u => u.user_id === currentUserId);

    if (hasReacted) {
      onRemoveReaction?.(messageId, emoji);
    } else {
      onAddReaction?.(messageId, emoji);
    }
  };

  // 編集開始
  const handleStartEdit = (message: Message) => {
    setEditingMessageId(message.id);
    setEditContent(message.content);
  };

  // 編集キャンセル
  const handleCancelEdit = () => {
    setEditingMessageId(null);
    setEditContent('');
  };

  // 編集保存
  const handleSaveEdit = async () => {
    if (!editingMessageId || !editContent.trim() || !onEditMessage) return;
    try {
      await onEditMessage(editingMessageId, editContent.trim());
      setEditingMessageId(null);
      setEditContent('');
    } catch (error) {
      console.error('Failed to edit message:', error);
    }
  };

  // メッセージ削除
  const handleDeleteMessage = async (messageId: string) => {
    if (!onDeleteMessage) return;
    if (!confirm('このメッセージを削除しますか？')) return;
    try {
      await onDeleteMessage(messageId);
    } catch (error) {
      console.error('Failed to delete message:', error);
    }
  };

  // 引用返信
  const handleQuoteReply = (message: Message) => {
    setQuotedMessage(message);
  };

  // 引用をキャンセル
  const handleCancelQuote = () => {
    setQuotedMessage(null);
  };

  const [newMessage, setNewMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = () => {
    if (!newMessage.trim() || isSending) return;
    onSendMessage(newMessage.trim(), quotedMessage?.id);
    setNewMessage('');
    setQuotedMessage(null);
  };

  const getChannelDisplayName = (ch: Channel | StaffChannel) => {
    if ('guardian' in ch && ch.guardian?.fullName) {
      return ch.guardian.fullName;
    }
    if ('members' in ch && ch.members?.length === 2) {
      const other = ch.members.find((m: any) => m.user?.id !== currentUserId);
      return other?.user?.fullName || other?.user?.email || ch.name;
    }
    return ch.name || '不明';
  };

  const getChannelAvatar = (ch: Channel | StaffChannel) => {
    const name = getChannelDisplayName(ch);
    return name.substring(0, 2);
  };

  const formatMessageDate = (dateStr: string) => {
    const date = new Date(dateStr);
    if (isToday(date)) return '今日';
    if (isYesterday(date)) return '昨日';
    return format(date, 'M月d日(E)', { locale: ja });
  };

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

  // 空状態（チャンネル未選択）
  if (!channel) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-gray-50 text-gray-500">
        <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <MessageCircle className="w-12 h-12 text-gray-300" />
        </div>
        <p className="text-lg font-medium text-gray-400">チャットを選択</p>
        {/* トーク一覧ボタン */}
        {onOpenSidebar && (
          <button
            onClick={onOpenSidebar}
            className="mt-4 px-6 py-3 bg-blue-500 text-white rounded-full font-medium flex items-center gap-2 hover:bg-blue-600 transition-colors"
          >
            <MessageCircle className="w-5 h-5" />
            トーク一覧を開く
          </button>
        )}
      </div>
    );
  }

  const messageGroups = groupMessagesByDate(messages);

  const mainContent = (
    <div className="h-full flex flex-col bg-[#7AACB8]">
      {/* LINE風ヘッダー */}
      <div className="flex-shrink-0 bg-[#00B900] text-white px-3 py-3 flex items-center gap-3 shadow-md">
        {/* 戻るボタン */}
        {onOpenSidebar && (
          <button
            onClick={onOpenSidebar}
            className="p-1 hover:bg-white/20 rounded-full transition-colors"
            title="トーク一覧"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
        )}
        <Avatar className="w-10 h-10 border-2 border-white/30">
          <AvatarFallback className="bg-white text-[#00B900] text-sm font-bold">
            {getChannelAvatar(channel)}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <h1 className="font-bold text-base truncate">{getChannelDisplayName(channel)}</h1>
          {'student' in channel && channel.student && (
            <p className="text-xs text-white/80">生徒: {channel.student.fullName}</p>
          )}
          {typingUsers.length > 0 && (
            <p className="text-xs text-white/90 animate-pulse">
              {typingUsers.join(', ')} が入力中...
            </p>
          )}
        </div>
        <button className="p-2 hover:bg-white/20 rounded-full transition-colors" title="通話">
          <Phone className="w-5 h-5" />
        </button>
        {onOpenSettings && (
          <button
            onClick={onOpenSettings}
            className="p-2 hover:bg-white/20 rounded-full transition-colors"
            title="設定"
          >
            <MoreVertical className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* LINE風メッセージエリア */}
      <div className="flex-1 overflow-y-auto px-3 py-4 flex flex-col min-h-0">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center flex-1">
            <p className="text-white/70 text-sm">メッセージがありません</p>
          </div>
        ) : (
          <div className="mt-auto">
          {messageGroups.map((group, groupIndex) => (
            <div key={groupIndex}>
              {/* LINE風日付セパレーター */}
              <div className="flex items-center justify-center my-4">
                <span className="bg-black/20 text-white text-xs px-4 py-1 rounded-full">
                  {formatMessageDate(group.date)}
                </span>
              </div>

              {/* LINE風メッセージ */}
              {group.messages.map((message, msgIndex) => {
                const senderId = message.sender || message.senderId;
                const isOwnMessage = senderId === currentUserId;
                const showAvatar = !isOwnMessage && (
                  msgIndex === 0 ||
                  (group.messages[msgIndex - 1].sender || group.messages[msgIndex - 1].senderId) !== senderId
                );
                const replyCount = message.replyCount || 0;
                const isHovered = hoveredMessageId === message.id;
                const isEditing = editingMessageId === message.id;
                const readCount = message.readCount || 0;

                return (
                  <div
                    key={message.id}
                    className={`flex items-end gap-2 mb-2 ${isOwnMessage ? 'flex-row-reverse' : ''}`}
                    onMouseEnter={() => setHoveredMessageId(message.id)}
                    onMouseLeave={() => setHoveredMessageId(null)}
                  >
                    {/* LINE風アバター */}
                    {!isOwnMessage && (
                      <div className="w-10 flex-shrink-0 mb-1">
                        {showAvatar && (
                          <Avatar className="w-10 h-10 shadow-md">
                            <AvatarFallback className="bg-white text-[#00B900] text-sm font-bold">
                              {(message.senderName || '?').substring(0, 2)}
                            </AvatarFallback>
                          </Avatar>
                        )}
                      </div>
                    )}

                    {/* LINE風メッセージバブル */}
                    <div className={`flex flex-col ${isOwnMessage ? 'items-end' : 'items-start'} max-w-[70%]`}>
                      {/* 送信者名（相手のメッセージで最初のみ） */}
                      {!isOwnMessage && showAvatar && (
                        <span className="text-xs text-white/80 mb-1 ml-2 font-medium">
                          {message.senderName || '不明'}
                        </span>
                      )}

                      <div className={`flex items-end gap-1.5 ${isOwnMessage ? 'flex-row-reverse' : ''}`}>
                        {/* アクションボタン（ホバー時に表示） */}
                        {isHovered && !isEditing && (
                          <div className={`flex items-center gap-0.5 bg-white/90 backdrop-blur rounded-full shadow-lg p-1 ${isOwnMessage ? 'flex-row-reverse' : ''}`}>
                            {/* クイックリアクション */}
                            {onAddReaction && (
                              <>
                                {QUICK_REACTIONS.slice(0, 3).map((emoji) => (
                                  <button
                                    key={emoji}
                                    onClick={() => onAddReaction(message.id, emoji)}
                                    className="p-1.5 hover:bg-gray-100 rounded-full transition-colors text-sm"
                                    title={emoji}
                                  >
                                    {emoji}
                                  </button>
                                ))}
                                <EmojiButton
                                  onSelect={(emoji) => onAddReaction(message.id, emoji)}
                                />
                              </>
                            )}
                            {/* 引用返信 */}
                            <button
                              onClick={() => handleQuoteReply(message)}
                              className="p-1.5 hover:bg-gray-100 rounded-full transition-colors"
                              title="引用返信"
                            >
                              <Quote className="w-4 h-4 text-gray-500" />
                            </button>
                            {/* スレッド返信 */}
                            {onOpenThread && (
                              <button
                                onClick={() => onOpenThread(message)}
                                className="p-1.5 hover:bg-gray-100 rounded-full transition-colors"
                                title="スレッドで返信"
                              >
                                <Reply className="w-4 h-4 text-gray-500" />
                              </button>
                            )}
                            {/* その他メニュー */}
                            {(onCreateTask || (isOwnMessage && (onEditMessage || onDeleteMessage))) && (
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <button className="p-1.5 hover:bg-gray-100 rounded-full transition-colors">
                                    <MoreVertical className="w-4 h-4 text-gray-500" />
                                  </button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align={isOwnMessage ? 'end' : 'start'}>
                                  {onCreateTask && (
                                    <DropdownMenuItem onClick={() => onCreateTask(message)}>
                                      <ClipboardList className="w-4 h-4 mr-2" />
                                      タスクを作成
                                    </DropdownMenuItem>
                                  )}
                                  {isOwnMessage && onEditMessage && (
                                    <>
                                      {onCreateTask && <DropdownMenuSeparator />}
                                      <DropdownMenuItem onClick={() => handleStartEdit(message)}>
                                        <Pencil className="w-4 h-4 mr-2" />
                                        編集
                                      </DropdownMenuItem>
                                    </>
                                  )}
                                  {isOwnMessage && onDeleteMessage && (
                                    <DropdownMenuItem
                                      onClick={() => handleDeleteMessage(message.id)}
                                      className="text-red-600"
                                    >
                                      <Trash2 className="w-4 h-4 mr-2" />
                                      削除
                                    </DropdownMenuItem>
                                  )}
                                </DropdownMenuContent>
                              </DropdownMenu>
                            )}
                          </div>
                        )}

                        {/* バブル */}
                        <div className="flex flex-col">
                          {/* 編集モード */}
                          {isEditing ? (
                            <div className="bg-white rounded-lg shadow-md p-2 min-w-[200px]">
                              <textarea
                                value={editContent}
                                onChange={(e) => setEditContent(e.target.value)}
                                className="w-full p-2 border rounded text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                                rows={3}
                                autoFocus
                              />
                              <div className="flex justify-end gap-2 mt-2">
                                <button
                                  onClick={handleCancelEdit}
                                  className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded"
                                >
                                  キャンセル
                                </button>
                                <button
                                  onClick={handleSaveEdit}
                                  disabled={!editContent.trim()}
                                  className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                                >
                                  保存
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div
                              className={`relative px-4 py-2.5 shadow-md ${
                                isOwnMessage
                                  ? 'bg-[#00B900] text-white rounded-[20px] rounded-br-md'
                                  : 'bg-white text-gray-800 rounded-[20px] rounded-bl-md'
                              }`}
                            >
                              {/* LINE風引用元表示 */}
                              {message.replyTo && message.replyToContent && (
                                <div className={`mb-2 pl-2.5 border-l-2 ${isOwnMessage ? 'border-white/50 bg-white/10' : 'border-[#00B900] bg-gray-100'} -mx-1 px-2 py-1.5 rounded`}>
                                  <p className={`text-[11px] font-medium ${isOwnMessage ? 'text-white/80' : 'text-gray-600'}`}>
                                    {message.replyToSenderName || '返信'}
                                  </p>
                                  <p className={`text-xs truncate max-w-[200px] ${isOwnMessage ? 'text-white/70' : 'text-gray-500'}`}>
                                    {message.replyToContent}
                                  </p>
                                </div>
                              )}

                              {/* テキスト内容 */}
                              {message.content && message.content !== message.attachmentName && (
                                <p className="text-[14px] leading-relaxed whitespace-pre-wrap break-words">
                                  {formatMessageWithMentions(message.content, message.mentions)}
                                </p>
                              )}

                              {/* 編集済みラベル */}
                              {message.isEdited && (
                                <span className={`text-[10px] ml-1 ${isOwnMessage ? 'text-white/60' : 'text-gray-400'}`}>(編集済み)</span>
                              )}

                              {/* 添付ファイル表示 */}
                              {message.attachmentUrl && message.attachmentName && (
                                <AttachmentDisplay
                                  attachmentUrl={message.attachmentUrl}
                                  attachmentName={message.attachmentName}
                                  messageType={message.messageType}
                                  isOwnMessage={isOwnMessage}
                                />
                              )}

                              {/* 返信数バッジ */}
                              {replyCount > 0 && (
                                <button
                                  onClick={() => onOpenThread && onOpenThread(message)}
                                  className={`flex items-center gap-1 mt-2 text-xs font-medium ${isOwnMessage ? 'text-white/80 hover:text-white' : 'text-[#00B900] hover:text-[#009900]'}`}
                                >
                                  <MessageCircle className="w-3 h-3" />
                                  {replyCount}件の返信
                                </button>
                              )}
                            </div>
                          )}

                          {/* リアクション表示 */}
                          {message.reactions && message.reactions.length > 0 && (
                            <div className={`flex flex-wrap gap-1 mt-1 ${isOwnMessage ? 'justify-end' : 'justify-start'}`}>
                              {message.reactions.map((reaction) => {
                                const hasReacted = reaction.users.some(u => u.user_id === currentUserId);
                                return (
                                  <button
                                    key={reaction.emoji}
                                    onClick={() => handleReactionClick(message.id, reaction.emoji, message.reactions)}
                                    title={reaction.users.map(u => u.user_name).join(', ')}
                                    className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs transition-colors ${
                                      hasReacted
                                        ? 'bg-blue-100 border border-blue-300 text-blue-700'
                                        : 'bg-white/80 hover:bg-white border border-gray-200 text-gray-700'
                                    }`}
                                  >
                                    <span>{reaction.emoji}</span>
                                    <span className="font-medium">{reaction.count}</span>
                                  </button>
                                );
                              })}
                            </div>
                          )}
                        </div>

                        {/* LINE風時刻と既読 */}
                        <div className={`flex flex-col gap-0.5 ${isOwnMessage ? 'items-end' : 'items-start'}`}>
                          {isOwnMessage && readCount > 0 && (
                            <span className="text-[10px] text-white/70 font-medium">
                              既読
                            </span>
                          )}
                          <span className="text-[10px] text-white/60">
                            {format(new Date(message.createdAt), 'HH:mm')}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* LINE風入力エリア */}
      <div className="flex-shrink-0 bg-[#F7F7F7] border-t border-gray-200 px-3 py-2 relative">
        {/* 引用プレビューパネル */}
        {quotedMessage && (
          <div className="mb-2 bg-white rounded-lg p-2.5 border-l-4 border-[#00B900] flex items-start justify-between shadow-sm">
            <div className="flex-1 min-w-0">
              <p className="text-[11px] text-[#00B900] font-semibold">{quotedMessage.senderName}への返信</p>
              <p className="text-xs text-gray-600 truncate mt-0.5">{quotedMessage.content}</p>
            </div>
            <button
              onClick={handleCancelQuote}
              className="p-1 hover:bg-gray-100 rounded-full ml-2 flex-shrink-0"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        )}

        {/* ファイルプレビューパネル */}
        {selectedFile && (
          <FilePreviewPanel
            file={selectedFile}
            uploadProgress={uploadProgress}
            onCancel={handleCancelFile}
            onUpload={handleFileUpload}
            isUploading={isUploading}
          />
        )}

        <div className="flex items-center gap-2">
          {/* ファイル添付ボタン */}
          {onFileUpload && (
            <FileAttachmentInput
              onFileSelect={handleFileSelect}
              disabled={isSending || isUploading}
            />
          )}
          <MentionInput
            value={newMessage}
            onChange={setNewMessage}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                handleSend();
              }
            }}
            mentionableUsers={mentionableUsers}
            placeholder="メッセージを入力　（@でメンション）"
            disabled={isSending || isUploading}
            className="rounded-full bg-white border border-gray-300 focus:border-[#00B900] focus:ring-1 focus:ring-[#00B900] px-4"
          />
          <Button
            onClick={handleSend}
            disabled={!newMessage.trim() || isSending || isUploading}
            size="icon"
            className="rounded-full bg-[#00B900] hover:bg-[#009900] w-10 h-10 shadow-md"
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

  // ドラッグ&ドロップ対応
  if (onFileUpload) {
    return (
      <DragDropZone onFileDrop={handleFileSelect} disabled={isSending || isUploading}>
        {mainContent}
      </DragDropZone>
    );
  }

  return mainContent;
}
