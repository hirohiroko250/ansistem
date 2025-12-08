'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Checkbox } from '@/components/ui/checkbox';
import { useAuth } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { BottomNav } from '@/components/bottom-nav';
import { User, Bell, MapPin, LogOut, Save } from 'lucide-react';

interface Campus {
  id: string;
  name: string;
}

export default function SettingsPage() {
  const { user, loading, signOut } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<any>(null);
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [campuses, setCampuses] = useState<Campus[]>([]);
  const [selectedCampuses, setSelectedCampuses] = useState<string[]>([]);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    loadData();
  }, [user, loading]);

  const loadData = async () => {
    if (!user) return;

    const { data: profileData } = await supabase
      .from('profiles')
      .select('*')
      .eq('id', user.id)
      .single();

    if (profileData) {
      setProfile(profileData);
      setFullName(profileData.full_name);
      setPhone(profileData.phone);
      setEmail(profileData.email);
    }

    const { data: campusesData } = await supabase
      .from('campuses')
      .select('id, name')
      .order('name');

    if (campusesData) {
      setCampuses(campusesData);
    }

    const { data: instructorCampusesData } = await supabase
      .from('instructor_campuses')
      .select('campus_id')
      .eq('instructor_id', user.id);

    if (instructorCampusesData) {
      setSelectedCampuses(instructorCampusesData.map((ic) => ic.campus_id));
    }
  };

  const handleCampusToggle = (campusId: string) => {
    setSelectedCampuses((prev) =>
      prev.includes(campusId)
        ? prev.filter((id) => id !== campusId)
        : [...prev, campusId]
    );
  };

  const handleSave = async () => {
    if (!user) return;
    setSubmitting(true);

    const { error: profileError } = await supabase
      .from('profiles')
      .update({
        full_name: fullName,
        phone,
        email,
        updated_at: new Date().toISOString(),
      })
      .eq('id', user.id);

    if (profileError) {
      console.error('Profile update error:', profileError);
      setSubmitting(false);
      return;
    }

    const { error: deleteError } = await supabase
      .from('instructor_campuses')
      .delete()
      .eq('instructor_id', user.id);

    for (const campusId of selectedCampuses) {
      await supabase
        .from('instructor_campuses')
        .insert({
          instructor_id: user.id,
          campus_id: campusId,
        });
    }

    setSubmitting(false);
    alert('設定を保存しました');
  };

  const handleLogout = async () => {
    await signOut();
    router.push('/login');
  };

  if (loading || !profile) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100" />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-[390px] mx-auto">
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <h1 className="text-2xl font-bold text-gray-900">設定</h1>
          </div>
        </div>

        <div className="p-4 space-y-4">
          <Card className="shadow-md border-0">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <User className="w-5 h-5" />
                プロフィール
              </CardTitle>
              <CardDescription>基本情報の編集</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="fullName">氏名</Label>
                <Input
                  id="fullName"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="h-12"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">電話番号</Label>
                <Input
                  id="phone"
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="h-12"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">メールアドレス</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-12"
                />
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-md border-0">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <MapPin className="w-5 h-5" />
                勤務可能校舎
              </CardTitle>
              <CardDescription>担当する校舎を選択してください</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-64 overflow-y-auto p-2 border rounded-lg">
                {campuses.map((campus) => (
                  <div key={campus.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`campus-${campus.id}`}
                      checked={selectedCampuses.includes(campus.id)}
                      onCheckedChange={() => handleCampusToggle(campus.id)}
                    />
                    <label
                      htmlFor={`campus-${campus.id}`}
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
            </CardContent>
          </Card>

          <Card className="shadow-md border-0">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Bell className="w-5 h-5" />
                通知設定
              </CardTitle>
              <CardDescription>プッシュ通知の管理</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-sm">通知を受け取る</p>
                  <p className="text-xs text-gray-600">チャットやタスクの通知</p>
                </div>
                <Switch
                  checked={notificationsEnabled}
                  onCheckedChange={setNotificationsEnabled}
                />
              </div>
            </CardContent>
          </Card>

          <Button
            onClick={handleSave}
            disabled={submitting}
            className="w-full h-12 bg-blue-600 hover:bg-blue-700"
          >
            <Save className="w-4 h-4 mr-2" />
            {submitting ? '保存中...' : '設定を保存'}
          </Button>

          <Card className="shadow-md border-0 border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <Button
                onClick={handleLogout}
                variant="destructive"
                className="w-full h-12"
              >
                <LogOut className="w-4 h-4 mr-2" />
                ログアウト
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
