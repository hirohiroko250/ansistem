'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { useAuth } from '@/lib/auth';
import { supabase } from '@/lib/supabase';

interface Campus {
  id: string;
  name: string;
}

export default function ProfileSetupPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [campuses, setCampuses] = useState<Campus[]>([]);
  const [selectedCampuses, setSelectedCampuses] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    loadCampuses();
  }, [user, loading]);

  const loadCampuses = async () => {
    const { data } = await supabase
      .from('campuses')
      .select('id, name')
      .order('name');

    if (data) {
      setCampuses(data);
    }
  };

  const handleCampusToggle = (campusId: string) => {
    setSelectedCampuses((prev) =>
      prev.includes(campusId)
        ? prev.filter((id) => id !== campusId)
        : [...prev, campusId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    setSubmitting(true);

    const { error: profileError } = await supabase
      .from('profiles')
      .upsert({
        id: user.id,
        full_name: fullName,
        phone,
        email,
        profile_completed: true,
        updated_at: new Date().toISOString(),
      });

    if (profileError) {
      console.error('Profile error:', profileError);
      setSubmitting(false);
      return;
    }

    for (const campusId of selectedCampuses) {
      await supabase
        .from('instructor_campuses')
        .upsert({
          instructor_id: user.id,
          campus_id: campusId,
        });
    }

    router.push('/home');
  };

  if (loading) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100" />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 p-4 pb-24">
      <div className="max-w-[390px] mx-auto pt-8">
        <Card className="shadow-xl border-0">
          <CardHeader>
            <CardTitle className="text-2xl">プロフィール登録</CardTitle>
            <CardDescription>
              初回ログイン時は必須項目を入力してください
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="fullName">氏名 *</Label>
                <Input
                  id="fullName"
                  type="text"
                  placeholder="山田 太郎"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  className="h-12"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">電話番号 *</Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="090-1234-5678"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  required
                  className="h-12"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">メールアドレス *</Label>
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

              <div className="space-y-3">
                <Label>勤務可能校舎 *</Label>
                <div className="space-y-2 max-h-48 overflow-y-auto p-2 border rounded-lg">
                  {campuses.map((campus) => (
                    <div key={campus.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={campus.id}
                        checked={selectedCampuses.includes(campus.id)}
                        onCheckedChange={() => handleCampusToggle(campus.id)}
                      />
                      <label
                        htmlFor={campus.id}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        {campus.name}
                      </label>
                    </div>
                  ))}
                  {campuses.length === 0 && (
                    <p className="text-sm text-gray-500 text-center py-4">
                      校舎データがありません
                    </p>
                  )}
                </div>
              </div>

              <Button
                type="submit"
                className="w-full h-12 bg-blue-600 hover:bg-blue-700"
                disabled={submitting || selectedCampuses.length === 0}
              >
                {submitting ? '登録中...' : '登録完了'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
