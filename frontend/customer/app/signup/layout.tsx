import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '新規登録 | OZA',
  description: 'OZA保護者アカウントの新規登録。お子様の学習管理、授業予約、お知らせ受信ができるようになります。',
  robots: {
    index: false,
    follow: true,
  },
};

export default function SignupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
