'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { supabase } from '@/lib/supabase';
import { CheckCircle2, Loader2 } from 'lucide-react';

export default function SetupPage() {
  const [loading, setLoading] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState('');

  const setupTestData = async () => {
    setLoading(true);
    setError('');

    try {
      const testEmail = 'instructor@example.com';
      const testPassword = 'password123';

      const { data: signUpData, error: signUpError } = await supabase.auth.signUp({
        email: testEmail,
        password: testPassword,
      });

      if (signUpError) {
        if (signUpError.message.includes('already registered')) {
          setError('テストユーザーは既に作成されています');
        } else {
          setError(`エラー: ${signUpError.message}`);
        }
        setLoading(false);
        return;
      }

      await new Promise(resolve => setTimeout(resolve, 1000));

      const { error: campusError } = await supabase
        .from('campuses')
        .insert([
          { name: '新宿校', address: '東京都新宿区' },
          { name: '渋谷校', address: '東京都渋谷区' },
          { name: '池袋校', address: '東京都豊島区' },
        ]);

      if (campusError && !campusError.message.includes('duplicate')) {
        console.error('Campus error:', campusError);
      }

      if (signUpData.user) {
        const today = new Date().toISOString().split('T')[0];

        const { data: campuses } = await supabase
          .from('campuses')
          .select('id')
          .limit(1)
          .single();

        if (campuses) {
          await supabase.from('classes').insert([
            {
              campus_id: campuses.id,
              class_name: 'そろばん基礎',
              classroom: 'A教室',
              instructor_id: signUpData.user.id,
              date: today,
              start_time: '17:00:00',
              end_time: '18:00:00',
              status: 'scheduled',
            },
          ]);

          await supabase.from('students').insert([
            { name: '山田太郎', grade: '小学3年', campus_id: campuses.id },
            { name: '佐藤花子', grade: '小学4年', campus_id: campuses.id },
            { name: '鈴木一郎', grade: '小学5年', campus_id: campuses.id },
          ]);
        }

        await supabase.from('chat_groups').insert([
          { name: '新宿校グループ', type: 'campus' },
          { name: '業務連絡', type: 'employee' },
        ]);

        await supabase.from('tasks').insert([
          {
            title: '月次報告書の提出',
            description: '今月の授業実施状況をまとめて提出してください',
            assigned_to: signUpData.user.id,
            status: 'not_started',
            due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          },
        ]);
      }

      setCompleted(true);
    } catch (err: any) {
      setError(`エラーが発生しました: ${err.message}`);
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader>
          <CardTitle className="text-2xl">テストデータセットアップ</CardTitle>
          <CardDescription>
            デモ用のテストユーザーとサンプルデータを作成します
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!completed ? (
            <>
              <div className="p-4 bg-blue-50 rounded-lg space-y-2 text-sm">
                <p className="font-semibold">作成されるテストアカウント：</p>
                <p>メール: instructor@example.com</p>
                <p>パスワード: password123</p>
              </div>

              {error && (
                <div className="p-4 bg-red-50 text-red-700 rounded-lg text-sm">
                  {error}
                </div>
              )}

              <Button
                onClick={setupTestData}
                disabled={loading}
                className="w-full h-12 bg-blue-600 hover:bg-blue-700"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    セットアップ中...
                  </>
                ) : (
                  'テストデータを作成'
                )}
              </Button>
            </>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-center py-8">
                <CheckCircle2 className="w-16 h-16 text-green-600" />
              </div>
              <div className="p-4 bg-green-50 rounded-lg space-y-2">
                <p className="font-semibold text-green-900 text-center">
                  セットアップ完了！
                </p>
                <div className="mt-4 p-3 bg-white rounded border border-green-200 text-sm">
                  <p className="font-semibold mb-2">ログイン情報：</p>
                  <p>メール: instructor@example.com</p>
                  <p>パスワード: password123</p>
                </div>
              </div>
              <Button
                onClick={() => window.location.href = '/login'}
                className="w-full h-12 bg-blue-600 hover:bg-blue-700"
              >
                ログイン画面へ
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
