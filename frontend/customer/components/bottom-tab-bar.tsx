'use client';

import { useEffect, useState } from 'react';
import { Home, Image, Calendar, MessageCircle, BookOpen, Settings, Users, ClipboardList } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { getMe } from '@/lib/api/auth';
import { getChannels } from '@/lib/api/chat';
import type { UserType } from '@/lib/api/types';

// 保護者・生徒用タブ
const guardianTabs = [
  { name: 'Home', icon: Home, href: '/' },
  { name: 'Feed', icon: Image, href: '/feed' },
  { name: '通帳', icon: BookOpen, href: '/purchase-history' },
  { name: 'Chat', icon: MessageCircle, href: '/chat' },
  { name: 'Settings', icon: Settings, href: '/settings' },
];

// 講師・スタッフ用タブ
const staffTabs = [
  { name: 'Feed', icon: Image, href: '/feed' },
  { name: 'スケジュール', icon: Calendar, href: '/schedule' },
  { name: '出欠', icon: ClipboardList, href: '/attendance' },
  { name: '生徒', icon: Users, href: '/students' },
  { name: 'Settings', icon: Settings, href: '/settings' },
];

export function BottomTabBar() {
  const pathname = usePathname();
  const [userType, setUserType] = useState<UserType | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const fetchUserType = async () => {
      try {
        const profile = await getMe();
        setUserType(profile.userType as UserType);
      } catch {
        // 認証エラー時はデフォルトで保護者用を表示
        setUserType('guardian');
      }
    };

    fetchUserType();
  }, []);

  // チャットの未読件数を取得
  useEffect(() => {
    const fetchUnreadCount = async () => {
      try {
        const channels = await getChannels();
        // EXTERNALチャンネルの未読件数のみカウント（ボットチャットは除外）
        const total = (channels || [])
          .filter(ch => ch.channelType?.toUpperCase() === 'EXTERNAL')
          .reduce((sum, ch) => sum + (ch.unreadCount || 0), 0);
        setUnreadCount(total);
      } catch {
        // エラー時は0を維持
      }
    };

    fetchUnreadCount();
    // 30秒ごとに更新
    const interval = setInterval(fetchUnreadCount, 30000);

    // ページがvisibleになった時に更新
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchUnreadCount();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const isStaff = userType === 'staff' || userType === 'teacher';
  const tabs = isStaff ? staffTabs : guardianTabs;

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 pb-safe">
      <div className="max-w-[390px] mx-auto px-2">
        <div className="flex justify-around items-center h-16">
          {tabs.map((tab) => {
            const isActive = pathname === tab.href ||
              (tab.href !== '/' && pathname.startsWith(tab.href));
            const Icon = tab.icon;

            const showBadge = tab.href === '/chat' && unreadCount > 0;

            return (
              <Link
                key={tab.name}
                href={tab.href}
                className={`flex flex-col items-center justify-center flex-1 py-2 transition-colors ${
                  isActive ? 'text-blue-500' : 'text-gray-500 hover:text-blue-400'
                }`}
              >
                <div className="relative">
                  <Icon className="h-6 w-6" />
                  {showBadge && (
                    <span className="absolute -top-1 -right-1 min-w-[16px] h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
                </div>
                <span className={`text-xs mt-1 ${isActive ? 'font-medium' : ''}`}>
                  {tab.name}
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
