import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'パスワードリセット | OZA',
  description: 'OZAアカウントのパスワードをリセット。登録メールアドレスにリセットリンクをお送りします。',
  robots: {
    index: false,
    follow: true,
  },
};

export default function PasswordResetLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
