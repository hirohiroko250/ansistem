'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function TicketPurchaseSelectionPage() {
  const router = useRouter();

  useEffect(() => {
    // チケット購入ページに直接リダイレクト
    router.replace('/ticket-purchase/from-ticket');
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
    </div>
  );
}
