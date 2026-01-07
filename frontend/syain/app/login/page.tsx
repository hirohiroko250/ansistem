'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/lib/auth';
import { GraduationCap } from 'lucide-react';
import Link from 'next/link';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { signIn } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const { error } = await signIn(email, password);

    if (error) {
      setError('ログインに失敗しました。メールアドレスとパスワードを確認してください。');
      setLoading(false);
    } else {
      router.push('/feed');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center p-4">
      <div className="w-full max-w-[390px]">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mb-4 shadow-lg">
            <GraduationCap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">講師業務システム</h1>
          <p className="text-sm text-gray-600 mt-1">Instructor Portal</p>
        </div>

        <Card className="shadow-xl border-0">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">ログイン</CardTitle>
            <CardDescription className="text-center">
              社員発行のアカウントでログインしてください
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">メールアドレス</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="instructor@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="h-12"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">パスワード</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="h-12"
                />
              </div>
              {error && (
                <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">
                  {error}
                </div>
              )}
              <Button
                type="submit"
                className="w-full h-12 bg-blue-600 hover:bg-blue-700"
                disabled={loading}
              >
                {loading ? 'ログイン中...' : 'ログイン'}
              </Button>
              <div className="text-center mt-4">
                <p className="text-sm text-gray-600">
                  アカウントをお持ちでない方は
                  <Link href="/register" className="text-blue-600 hover:underline ml-1">
                    新規登録
                  </Link>
                </p>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
