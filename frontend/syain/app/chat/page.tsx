'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { BottomNav } from '@/components/bottom-nav';
import { MessageCircle, Users, CheckSquare, Send, Pin, MoreVertical } from 'lucide-react';
import { format } from 'date-fns';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ChatGroup {
  id: string;
  name: string;
  type: string;
  last_message?: string;
  unread_count: number;
}

interface Message {
  id: string;
  content: string;
  sender_id: string;
  sender_name: string;
  created_at: string;
  is_pinned: boolean;
}

export default function ChatPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('personal');
  const [groups, setGroups] = useState<ChatGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    loadGroups();
  }, [user, loading, activeTab]);

  useEffect(() => {
    if (selectedGroup) {
      loadMessages();
    }
  }, [selectedGroup]);

  const loadGroups = async () => {
    if (!user) return;

    const { data: memberData } = await supabase
      .from('chat_members')
      .select(`
        group:chat_groups (
          id,
          name,
          type
        )
      `)
      .eq('user_id', user.id);

    if (memberData) {
      const groupsList: ChatGroup[] = memberData
        .filter((m: any) => m.group && m.group.type === activeTab)
        .map((m: any) => ({
          id: m.group.id,
          name: m.group.name,
          type: m.group.type,
          unread_count: 0,
        }));

      setGroups(groupsList);

      if (groupsList.length > 0 && !selectedGroup) {
        setSelectedGroup(groupsList[0].id);
      }
    }
  };

  const loadMessages = async () => {
    if (!selectedGroup) return;

    const { data: messagesData } = await supabase
      .from('chat_messages')
      .select(`
        id,
        content,
        sender_id,
        created_at,
        is_pinned,
        sender:profiles!chat_messages_sender_id_fkey (
          full_name
        )
      `)
      .eq('group_id', selectedGroup)
      .order('created_at', { ascending: true })
      .limit(100);

    if (messagesData) {
      const messagesList: Message[] = messagesData.map((m: any) => ({
        id: m.id,
        content: m.content,
        sender_id: m.sender_id,
        sender_name: m.sender?.full_name || 'Unknown',
        created_at: m.created_at,
        is_pinned: m.is_pinned,
      }));

      setMessages(messagesList);
    }
  };

  const handleSendMessage = async () => {
    if (!user || !selectedGroup || !newMessage.trim()) return;

    const { error } = await supabase
      .from('chat_messages')
      .insert({
        group_id: selectedGroup,
        sender_id: user.id,
        content: newMessage,
      });

    if (!error) {
      setNewMessage('');
      loadMessages();
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100" />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-[390px] mx-auto">
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <h1 className="text-2xl font-bold text-gray-900">チャット</h1>
          </div>
        </div>

        <div className="p-4">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-4">
              <TabsTrigger value="personal" className="text-xs">
                <MessageCircle className="w-4 h-4 mr-1" />
                個人
              </TabsTrigger>
              <TabsTrigger value="campus" className="text-xs">
                <Users className="w-4 h-4 mr-1" />
                グループ
              </TabsTrigger>
              <TabsTrigger value="task" className="text-xs">
                <CheckSquare className="w-4 h-4 mr-1" />
                タスク
              </TabsTrigger>
            </TabsList>

            <TabsContent value={activeTab} className="space-y-4">
              {groups.length === 0 ? (
                <Card className="p-8 text-center text-gray-500">
                  チャットグループがありません
                </Card>
              ) : (
                <div className="grid grid-cols-1 gap-2">
                  {groups.map((group) => (
                    <Card
                      key={group.id}
                      className={`p-4 cursor-pointer transition-all ${
                        selectedGroup === group.id
                          ? 'ring-2 ring-blue-500 bg-blue-50'
                          : 'hover:bg-gray-50'
                      }`}
                      onClick={() => setSelectedGroup(group.id)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold text-gray-900">{group.name}</h3>
                        </div>
                        {group.unread_count > 0 && (
                          <Badge className="bg-red-500">{group.unread_count}</Badge>
                        )}
                      </div>
                    </Card>
                  ))}
                </div>
              )}

              {selectedGroup && (
                <Card className="shadow-lg border-0">
                  <div className="p-4 border-b">
                    <h3 className="font-semibold text-gray-900">
                      {groups.find((g) => g.id === selectedGroup)?.name}
                    </h3>
                  </div>

                  <ScrollArea className="h-96 p-4">
                    <div className="space-y-3">
                      {messages.map((message) => (
                        <div
                          key={message.id}
                          className={`flex ${
                            message.sender_id === user?.id
                              ? 'justify-end'
                              : 'justify-start'
                          }`}
                        >
                          <div
                            className={`max-w-[75%] ${
                              message.sender_id === user?.id
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-100 text-gray-900'
                            } rounded-2xl p-3 shadow-sm`}
                          >
                            {message.sender_id !== user?.id && (
                              <p className="text-xs font-semibold mb-1 opacity-70">
                                {message.sender_name}
                              </p>
                            )}
                            <p className="text-sm break-words">{message.content}</p>
                            <div className="flex items-center justify-between mt-1">
                              <p className="text-xs opacity-70">
                                {format(new Date(message.created_at), 'HH:mm')}
                              </p>
                              {message.is_pinned && (
                                <Pin className="w-3 h-3 ml-2" />
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                      {messages.length === 0 && (
                        <p className="text-center text-gray-500 py-8">
                          メッセージがありません
                        </p>
                      )}
                    </div>
                  </ScrollArea>

                  <div className="p-4 border-t bg-white">
                    <div className="flex gap-2">
                      <Input
                        placeholder="メッセージを入力..."
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            handleSendMessage();
                          }
                        }}
                        className="flex-1"
                      />
                      <Button
                        onClick={handleSendMessage}
                        disabled={!newMessage.trim()}
                        size="icon"
                        className="bg-blue-600 hover:bg-blue-700"
                      >
                        <Send className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
