"use client";

import { useEffect, useState, useRef } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import apiClient from "@/lib/api/client";
import {
  MessageSquare,
  Plus,
  Send,
  Users,
  User,
  Search,
  MoreVertical,
  Hash,
  Check,
  CheckCheck,
} from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

interface Channel {
  id: string;
  name: string;
  channelType: string;
  description?: string;
  updatedAt: string;
  members?: Array<{
    id: string;
    user?: { id: string; fullName?: string; email: string };
  }>;
  unreadCount?: number;
}

interface Message {
  id: string;
  content: string;
  messageType: string;
  sender?: { id: string; fullName?: string; email: string };
  senderName?: string;
  createdAt: string;
  isEdited?: boolean;
}

interface Staff {
  id: string;
  name: string;
  email?: string;
  position?: string;
}

export default function ChatPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [staffList, setStaffList] = useState<Staff[]>([]);
  const [showNewChat, setShowNewChat] = useState(false);
  const [showNewGroup, setShowNewGroup] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [currentUserId, setCurrentUserId] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadChannels();
    loadStaff();
    loadCurrentUser();
  }, []);

  useEffect(() => {
    if (selectedChannel) {
      loadMessages(selectedChannel.id);
      const interval = setInterval(() => {
        loadMessages(selectedChannel.id);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [selectedChannel?.id]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  function scrollToBottom() {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  async function loadCurrentUser() {
    try {
      const response = await apiClient.get<any>("/auth/me/");
      const user = response.user || response;
      setCurrentUserId(user.id);
    } catch (error) {
      console.error("Failed to load current user:", error);
    }
  }

  async function loadChannels() {
    try {
      setLoading(true);
      const response = await apiClient.get<any>("/communications/channels/my-channels/", {
        channel_type: "INTERNAL",
      });
      const data = response.results || response.data || response || [];
      setChannels(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load channels:", error);
      setChannels([]);
    } finally {
      setLoading(false);
    }
  }

  async function loadStaff() {
    try {
      const response = await apiClient.get<any>("/tenants/employees/");
      const data = response.results || response.data || response || [];
      setStaffList(
        (Array.isArray(data) ? data : []).map((e: any) => ({
          id: e.id,
          name: e.fullName || e.full_name || e.email,
          email: e.email,
          position: e.positionName || e.position_name,
        }))
      );
    } catch (error) {
      console.error("Failed to load staff:", error);
    }
  }

  async function loadMessages(channelId: string) {
    try {
      const response = await apiClient.get<any>(`/communications/channels/${channelId}/messages/`);
      const data = response.results || response.data || response || [];
      setMessages(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load messages:", error);
    }
  }

  async function sendMessage() {
    if (!selectedChannel || !newMessage.trim()) return;

    setSending(true);
    try {
      await apiClient.post(`/communications/channels/${selectedChannel.id}/send_message/`, {
        content: newMessage.trim(),
        message_type: "TEXT",
      });
      setNewMessage("");
      await loadMessages(selectedChannel.id);
    } catch (error) {
      console.error("Failed to send message:", error);
      alert("Failed to send message");
    } finally {
      setSending(false);
    }
  }

  async function createDM(targetUserId: string) {
    try {
      const response = await apiClient.post<any>("/communications/channels/create-dm/", {
        target_user_id: targetUserId,
      });
      await loadChannels();
      setSelectedChannel(response);
      setShowNewChat(false);
    } catch (error) {
      console.error("Failed to create DM:", error);
      alert("Failed to create chat");
    }
  }

  async function createGroup() {
    if (!groupName.trim()) {
      alert("Please enter group name");
      return;
    }

    try {
      const response = await apiClient.post<any>("/communications/channels/create-group/", {
        name: groupName.trim(),
        member_ids: selectedMembers,
      });
      await loadChannels();
      setSelectedChannel(response);
      setShowNewGroup(false);
      setGroupName("");
      setSelectedMembers([]);
    } catch (error) {
      console.error("Failed to create group:", error);
      alert("Failed to create group");
    }
  }

  function getChannelDisplayName(channel: Channel) {
    if (channel.members && channel.members.length === 2) {
      const other = channel.members.find((m) => m.user?.id !== currentUserId);
      return other?.user?.fullName || other?.user?.email || channel.name;
    }
    return channel.name;
  }

  function formatTime(dateString: string) {
    const date = new Date(dateString);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();

    if (isToday) {
      return date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
    }
    return date.toLocaleDateString("ja-JP", { month: "short", day: "numeric" });
  }

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />

      <div className="w-80 bg-white border-r flex flex-col">
        <div className="p-4 border-b">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-xl font-bold flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              Staff Chat
            </h1>
            <div className="flex gap-1">
              <Popover open={showNewChat} onOpenChange={setShowNewChat}>
                <PopoverTrigger asChild>
                  <Button variant="ghost" size="icon" title="New DM">
                    <User className="w-4 h-4" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-64 p-0" align="end">
                  <Command>
                    <CommandInput placeholder="Search staff..." />
                    <CommandList>
                      <CommandEmpty>Not found</CommandEmpty>
                      <CommandGroup heading="Staff">
                        {staffList.map((staff) => (
                          <CommandItem
                            key={staff.id}
                            onSelect={() => createDM(staff.id)}
                          >
                            <User className="mr-2 h-4 w-4" />
                            <span>{staff.name}</span>
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>

              <Popover open={showNewGroup} onOpenChange={setShowNewGroup}>
                <PopoverTrigger asChild>
                  <Button variant="ghost" size="icon" title="New Group">
                    <Users className="w-4 h-4" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-72 p-4" align="end">
                  <h3 className="font-medium mb-3">Create Group</h3>
                  <Input
                    placeholder="Group name"
                    value={groupName}
                    onChange={(e) => setGroupName(e.target.value)}
                    className="mb-3"
                  />
                  <div className="text-sm text-gray-500 mb-2">Select members</div>
                  <div className="max-h-40 overflow-y-auto space-y-1 mb-3">
                    {staffList.map((staff) => (
                      <label
                        key={staff.id}
                        className="flex items-center gap-2 p-2 rounded hover:bg-gray-100 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={selectedMembers.includes(staff.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedMembers([...selectedMembers, staff.id]);
                            } else {
                              setSelectedMembers(
                                selectedMembers.filter((id) => id !== staff.id)
                              );
                            }
                          }}
                        />
                        <span className="text-sm">{staff.name}</span>
                      </label>
                    ))}
                  </div>
                  <Button onClick={createGroup} className="w-full" size="sm">
                    Create
                  </Button>
                </PopoverContent>
              </Popover>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="text-center text-gray-500 py-8">Loading...</div>
          ) : channels.length === 0 ? (
            <div className="text-center text-gray-500 py-8 px-4">
              <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>No chats yet</p>
              <p className="text-sm mt-2">
                Start a new chat using the buttons above
              </p>
            </div>
          ) : (
            channels.map((channel) => (
              <div
                key={channel.id}
                onClick={() => setSelectedChannel(channel)}
                className={`p-3 border-b cursor-pointer transition-colors ${
                  selectedChannel?.id === channel.id
                    ? "bg-blue-50 border-l-4 border-l-blue-500"
                    : "hover:bg-gray-50"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback className="bg-blue-100 text-blue-600">
                      {channel.members && channel.members.length === 2 ? (
                        <User className="w-5 h-5" />
                      ) : (
                        <Users className="w-5 h-5" />
                      )}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="font-medium truncate">
                        {getChannelDisplayName(channel)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {formatTime(channel.updatedAt)}
                      </span>
                    </div>
                    {channel.description && (
                      <p className="text-sm text-gray-500 truncate">
                        {channel.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        {selectedChannel ? (
          <>
            <div className="p-4 bg-white border-b flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Avatar className="h-10 w-10">
                  <AvatarFallback className="bg-blue-100 text-blue-600">
                    {selectedChannel.members &&
                    selectedChannel.members.length === 2 ? (
                      <User className="w-5 h-5" />
                    ) : (
                      <Users className="w-5 h-5" />
                    )}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <h2 className="font-bold">
                    {getChannelDisplayName(selectedChannel)}
                  </h2>
                  {selectedChannel.members && (
                    <p className="text-sm text-gray-500">
                      {selectedChannel.members.length} members
                    </p>
                  )}
                </div>
              </div>
              <Button variant="ghost" size="icon">
                <MoreVertical className="w-4 h-4" />
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
              {messages.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  No messages yet. Send the first message!
                </div>
              ) : (
                messages.map((message) => {
                  const isMe = message.sender?.id === currentUserId;
                  return (
                    <div
                      key={message.id}
                      className={`flex ${isMe ? "justify-end" : "justify-start"}`}
                    >
                      <div className={`max-w-[70%] ${isMe ? "order-2" : "order-1"}`}>
                        {!isMe && (
                          <div className="text-xs text-gray-500 mb-1">
                            {message.senderName ||
                              message.sender?.fullName ||
                              message.sender?.email ||
                              "Unknown"}
                          </div>
                        )}
                        <div
                          className={`p-3 rounded-lg ${
                            isMe
                              ? "bg-blue-500 text-white rounded-br-none"
                              : "bg-white border rounded-bl-none"
                          }`}
                        >
                          <p className="whitespace-pre-wrap">{message.content}</p>
                        </div>
                        <div
                          className={`text-xs text-gray-400 mt-1 flex items-center gap-1 ${
                            isMe ? "justify-end" : "justify-start"
                          }`}
                        >
                          {formatTime(message.createdAt)}
                          {isMe && <CheckCheck className="w-3 h-3" />}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 bg-white border-t">
              <div className="flex gap-2">
                <Input
                  placeholder="Type a message..."
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
                  disabled={sending}
                />
                <Button onClick={sendMessage} disabled={sending || !newMessage.trim()}>
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-50">
            <div className="text-center text-gray-500">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <h2 className="text-xl font-medium mb-2">Select a chat</h2>
              <p className="text-sm">
                Choose a chat from the list or start a new one
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
