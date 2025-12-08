'use client';

import { useEffect, useState } from 'react';
import { ChevronLeft, Check, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  getMyPayment,
  updateMyPayment,
  type PaymentInfo,
  type PaymentUpdateData
} from '@/lib/api/payment';

export default function PaymentEditPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState<PaymentUpdateData>({
    bank_name: '',
    bank_code: '',
    branch_name: '',
    branch_code: '',
    account_type: 'ordinary',
    account_number: '',
    account_holder: '',
    account_holder_kana: '',
    withdrawal_day: 27,
  });

  useEffect(() => {
    fetchPayment();
  }, []);

  const fetchPayment = async () => {
    try {
      setLoading(true);
      const data = await getMyPayment();
      if (data) {
        setFormData({
          bank_name: data.bank_name || '',
          bank_code: data.bank_code || '',
          branch_name: data.branch_name || '',
          branch_code: data.branch_code || '',
          account_type: data.account_type || 'ordinary',
          account_number: data.account_number || '',
          account_holder: data.account_holder || '',
          account_holder_kana: data.account_holder_kana || '',
          withdrawal_day: data.withdrawal_day || 27,
        });
      }
    } catch (error) {
      console.error('Failed to fetch payment:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // バリデーション
    if (!formData.bank_name || !formData.branch_name || !formData.account_number || !formData.account_holder_kana) {
      setError('必須項目を入力してください');
      return;
    }

    try {
      setSaving(true);
      await updateMyPayment(formData);
      setSuccess(true);
    } catch (err) {
      setError('保存に失敗しました。もう一度お試しください。');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center px-4">
        <div className="text-center max-w-[390px] w-full">
          <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-6">
            <Check className="w-10 h-10 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-3">登録完了</h2>
          <p className="text-gray-600 mb-8">
            支払い方法の登録が完了しました。
          </p>
          <Link href="/settings/payment">
            <Button className="w-full h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg">
              支払い方法ページへ戻る
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/settings/payment" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">支払い方法の登録</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        <form onSubmit={handleSubmit}>
          <Card className="rounded-xl shadow-md mb-6">
            <CardContent className="p-6 space-y-4">
              <h2 className="text-lg font-bold text-gray-800 mb-4">銀行口座情報</h2>

              <div>
                <Label htmlFor="bank_name" className="text-sm font-medium text-gray-700 mb-2 block">
                  金融機関名 <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="bank_name"
                  placeholder="例: 三菱UFJ銀行"
                  value={formData.bank_name}
                  onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                  className="rounded-xl h-12"
                  required
                />
              </div>

              <div>
                <Label htmlFor="bank_code" className="text-sm font-medium text-gray-700 mb-2 block">
                  金融機関コード（4桁）
                </Label>
                <Input
                  id="bank_code"
                  placeholder="例: 0005"
                  value={formData.bank_code}
                  onChange={(e) => setFormData({ ...formData, bank_code: e.target.value })}
                  className="rounded-xl h-12"
                  maxLength={4}
                />
              </div>

              <div>
                <Label htmlFor="branch_name" className="text-sm font-medium text-gray-700 mb-2 block">
                  支店名 <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="branch_name"
                  placeholder="例: 渋谷支店"
                  value={formData.branch_name}
                  onChange={(e) => setFormData({ ...formData, branch_name: e.target.value })}
                  className="rounded-xl h-12"
                  required
                />
              </div>

              <div>
                <Label htmlFor="branch_code" className="text-sm font-medium text-gray-700 mb-2 block">
                  支店コード（3桁）
                </Label>
                <Input
                  id="branch_code"
                  placeholder="例: 150"
                  value={formData.branch_code}
                  onChange={(e) => setFormData({ ...formData, branch_code: e.target.value })}
                  className="rounded-xl h-12"
                  maxLength={3}
                />
              </div>

              <div>
                <Label className="text-sm font-medium text-gray-700 mb-2 block">
                  口座種別 <span className="text-red-500">*</span>
                </Label>
                <div className="flex gap-4">
                  {[
                    { value: 'ordinary', label: '普通' },
                    { value: 'current', label: '当座' },
                    { value: 'savings', label: '貯蓄' },
                  ].map((type) => (
                    <label key={type.value} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="account_type"
                        value={type.value}
                        checked={formData.account_type === type.value}
                        onChange={(e) => setFormData({ ...formData, account_type: e.target.value as 'ordinary' | 'current' | 'savings' })}
                        className="w-4 h-4 text-blue-600"
                      />
                      <span className="text-sm text-gray-700">{type.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <Label htmlFor="account_number" className="text-sm font-medium text-gray-700 mb-2 block">
                  口座番号（7〜8桁） <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="account_number"
                  placeholder="例: 1234567"
                  value={formData.account_number}
                  onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                  className="rounded-xl h-12"
                  maxLength={8}
                  required
                />
              </div>

              <div>
                <Label htmlFor="account_holder" className="text-sm font-medium text-gray-700 mb-2 block">
                  口座名義（漢字）
                </Label>
                <Input
                  id="account_holder"
                  placeholder="例: 田中 太郎"
                  value={formData.account_holder}
                  onChange={(e) => setFormData({ ...formData, account_holder: e.target.value })}
                  className="rounded-xl h-12"
                />
              </div>

              <div>
                <Label htmlFor="account_holder_kana" className="text-sm font-medium text-gray-700 mb-2 block">
                  口座名義（カナ） <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="account_holder_kana"
                  placeholder="例: タナカ タロウ"
                  value={formData.account_holder_kana}
                  onChange={(e) => setFormData({ ...formData, account_holder_kana: e.target.value })}
                  className="rounded-xl h-12"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">通帳に記載されている名義をカタカナで入力してください</p>
              </div>

              <div>
                <Label htmlFor="withdrawal_day" className="text-sm font-medium text-gray-700 mb-2 block">
                  引き落とし日
                </Label>
                <select
                  id="withdrawal_day"
                  value={formData.withdrawal_day || 27}
                  onChange={(e) => setFormData({ ...formData, withdrawal_day: parseInt(e.target.value) })}
                  className="w-full h-12 rounded-xl border border-gray-300 px-3 text-base"
                >
                  {[10, 15, 20, 25, 27, 28].map((day) => (
                    <option key={day} value={day}>毎月{day}日</option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>

          {error && (
            <Card className="rounded-xl shadow-md mb-6 border-red-200 bg-red-50">
              <CardContent className="p-4">
                <p className="text-sm text-red-800">{error}</p>
              </CardContent>
            </Card>
          )}

          <Button
            type="submit"
            disabled={saving}
            className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg"
          >
            {saving ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin" />
                保存中...
              </span>
            ) : (
              '登録する'
            )}
          </Button>
        </form>
      </main>
    </div>
  );
}
