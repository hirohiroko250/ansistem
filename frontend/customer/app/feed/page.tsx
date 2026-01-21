'use client';

import { BottomTabBar } from '@/components/bottom-tab-bar';
import { GuardianFeed } from '@/components/feed/guardian-feed';
import { StaffFeed } from '@/components/feed/staff-feed';
import { AuthGuard } from '@/components/auth';
import { useUser } from '@/lib/hooks';
import { Loader2 } from 'lucide-react';

type UserType = 'guardian' | 'student' | 'staff' | 'teacher';

function FeedContent() {
  const { data: user, isLoading } = useUser();

  // ローディング中
  if (isLoading) {
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
  const userType = user?.userType as UserType | undefined;
  const isStaffUser = userType === 'staff' || userType === 'teacher';

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      {isStaffUser ? <StaffFeed /> : <GuardianFeed />}
      <BottomTabBar />
    </div>
  );
}

export default function FeedPage() {
  return (
    <AuthGuard>
      <FeedContent />
    </AuthGuard>
  );
}
