'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Home, CheckSquare, MessageCircle, Image, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getAccessToken } from '@/lib/api/client';

const tabs = [
  { name: 'Home', href: '/home', icon: Home },
  { name: 'Task', href: '/tasks', icon: CheckSquare },
  { name: 'Feed', href: '/feed', icon: Image },
  { name: 'Chat', href: '/chat', icon: MessageCircle },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function BottomNav() {
  const pathname = usePathname();
  const [unreadCount, setUnreadCount] = useState(0);
  const [taskCount, setTaskCount] = useState(0);

  // 未読メッセージ数と未完了タスク数を取得
  useEffect(() => {
    const fetchCounts = async () => {
      const token = getAccessToken();
      if (!token) return;

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

      // 未読チャット数を取得
      try {
        const chatResponse = await fetch(`${apiUrl}/communications/channels/`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (chatResponse.ok) {
          const data = await chatResponse.json();
          const channels = data.data || data.results || data || [];
          const total = channels.reduce((sum: number, ch: { unreadCount?: number; unread_count?: number }) => {
            return sum + (ch.unreadCount || ch.unread_count || 0);
          }, 0);
          setUnreadCount(total);
        }
      } catch (error) {
        console.error('Failed to fetch unread count:', error);
      }

      // 未完了タスク数を取得
      try {
        const taskResponse = await fetch(`${apiUrl}/communications/tasks/?status=pending`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (taskResponse.ok) {
          const data = await taskResponse.json();
          const tasks = data.data || data.results || data || [];
          setTaskCount(Array.isArray(tasks) ? tasks.length : 0);
        }
      } catch (error) {
        console.error('Failed to fetch task count:', error);
      }
    };

    fetchCounts();
    // 30秒ごとに更新
    const interval = setInterval(fetchCounts, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
      <div className="max-w-[420px] mx-auto flex justify-around items-center h-16 px-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = pathname === tab.href || pathname.startsWith(tab.href + '/');
          const showChatBadge = tab.name === 'Chat' && unreadCount > 0;
          const showTaskBadge = tab.name === 'Task' && taskCount > 0;
          const badgeCount = showChatBadge ? unreadCount : showTaskBadge ? taskCount : 0;

          return (
            <Link
              key={tab.name}
              href={tab.href}
              className={cn(
                "flex flex-col items-center justify-center gap-1 flex-1 h-full transition-colors relative",
                isActive ? "text-blue-600" : "text-gray-500"
              )}
            >
              <div className="relative">
                <Icon className="w-5 h-5" />
                {(showChatBadge || showTaskBadge) && (
                  <span className={cn(
                    "absolute -top-2 -right-3 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1",
                    showTaskBadge ? "bg-orange-500" : "bg-red-500"
                  )}>
                    {badgeCount > 99 ? '99+' : badgeCount}
                  </span>
                )}
              </div>
              <span className="text-xs font-medium">{tab.name}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
