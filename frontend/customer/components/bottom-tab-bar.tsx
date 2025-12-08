'use client';

import { useEffect, useState } from 'react';
import { Home, Image, Calendar, MessageCircle, BookOpen, Settings, Users, ClipboardList } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { getMe } from '@/lib/api/auth';
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

            return (
              <Link
                key={tab.name}
                href={tab.href}
                className={`flex flex-col items-center justify-center flex-1 py-2 transition-colors ${
                  isActive ? 'text-blue-500' : 'text-gray-500 hover:text-blue-400'
                }`}
              >
                <Icon className="h-6 w-6" />
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
