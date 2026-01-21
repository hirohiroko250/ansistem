import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'ログイン | OZA',
  description: 'OZA保護者ページへログイン。お子様の授業スケジュール、チケット残高、お知らせを確認できます。',
  robots: {
    index: false, // ログインページは検索エンジンにインデックスしない
    follow: true,
  },
};

export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
