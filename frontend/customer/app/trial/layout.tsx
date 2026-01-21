import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '無料体験予約 | OZA',
  description: 'OZAの無料体験授業を予約。英会話、そろばん、プログラミングなど、お子様に合った習い事を体験できます。',
  keywords: ['無料体験', '習い事', '英会話', 'そろばん', 'プログラミング', '子供', '教室'],
  openGraph: {
    title: '無料体験予約 | OZA',
    description: 'OZAの無料体験授業を予約。英会話、そろばん、プログラミングなど、お子様に合った習い事を体験できます。',
    type: 'website',
  },
  robots: {
    index: true, // 体験ページは検索エンジンにインデックス
    follow: true,
  },
};

export default function TrialLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
