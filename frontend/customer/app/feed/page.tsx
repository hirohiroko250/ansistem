'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { GuardianFeed } from '@/components/feed/guardian-feed';
import { StaffFeed } from '@/components/feed/staff-feed';
import { getMe } from '@/lib/api/auth';
import { isAuthenticated } from '@/lib/api/auth';
import { Loader2 } from 'lucide-react';

type UserType = 'guardian' | 'student' | 'staff' | 'teacher' | null;

export default function FeedPage() {
  const router = useRouter();
  const [userType, setUserType] = useState<UserType>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      // 未認証の場合はログインページへ
      if (!isAuthenticated()) {
        router.push('/login');
        return;
      }

      try {
        const profile = await getMe();
        setUserType(profile.userType as UserType);
      } catch (error) {
        // 認証エラーの場合はログインページへ
        router.push('/login');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [router]);

  // ローディング中
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-gray-600">読み込み中...</p>
        </div>
      </div>
    );
  }

  // userTypeに応じてFeedコンポーネントを切り替え
  const isStaffUser = userType === 'staff' || userType === 'teacher';

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      {isStaffUser ? <StaffFeed /> : <GuardianFeed />}
      <BottomTabBar />
    </div>
  );
}
