'use client';

import { useEffect, useState } from 'react';
import { ChevronLeft, Check, Loader2, Clock } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  getMyPayment,
  getMyBankAccounts,
  createBankAccountRequest,
  type PaymentInfo,
  type BankAccountRequestData,
  type BankAccount
} from '@/lib/api/payment';
import { BankSelector } from '@/components/bank-selector';

// ひらがな・全角カタカナ→半角カタカナ変換
function toHalfWidthKatakana(str: string): string {
  const kanaMap: Record<string, string> = {
    // ひらがな
    'あ': 'ｱ', 'い': 'ｲ', 'う': 'ｳ', 'え': 'ｴ', 'お': 'ｵ',
    'か': 'ｶ', 'き': 'ｷ', 'く': 'ｸ', 'け': 'ｹ', 'こ': 'ｺ',
    'さ': 'ｻ', 'し': 'ｼ', 'す': 'ｽ', 'せ': 'ｾ', 'そ': 'ｿ',
    'た': 'ﾀ', 'ち': 'ﾁ', 'つ': 'ﾂ', 'て': 'ﾃ', 'と': 'ﾄ',
    'な': 'ﾅ', 'に': 'ﾆ', 'ぬ': 'ﾇ', 'ね': 'ﾈ', 'の': 'ﾉ',
    'は': 'ﾊ', 'ひ': 'ﾋ', 'ふ': 'ﾌ', 'へ': 'ﾍ', 'ほ': 'ﾎ',
    'ま': 'ﾏ', 'み': 'ﾐ', 'む': 'ﾑ', 'め': 'ﾒ', 'も': 'ﾓ',
    'や': 'ﾔ', 'ゆ': 'ﾕ', 'よ': 'ﾖ',
    'ら': 'ﾗ', 'り': 'ﾘ', 'る': 'ﾙ', 'れ': 'ﾚ', 'ろ': 'ﾛ',
    'わ': 'ﾜ', 'を': 'ｦ', 'ん': 'ﾝ',
    'ぁ': 'ｧ', 'ぃ': 'ｨ', 'ぅ': 'ｩ', 'ぇ': 'ｪ', 'ぉ': 'ｫ',
    'っ': 'ｯ', 'ゃ': 'ｬ', 'ゅ': 'ｭ', 'ょ': 'ｮ',
    'が': 'ｶﾞ', 'ぎ': 'ｷﾞ', 'ぐ': 'ｸﾞ', 'げ': 'ｹﾞ', 'ご': 'ｺﾞ',
    'ざ': 'ｻﾞ', 'じ': 'ｼﾞ', 'ず': 'ｽﾞ', 'ぜ': 'ｾﾞ', 'ぞ': 'ｿﾞ',
    'だ': 'ﾀﾞ', 'ぢ': 'ﾁﾞ', 'づ': 'ﾂﾞ', 'で': 'ﾃﾞ', 'ど': 'ﾄﾞ',
    'ば': 'ﾊﾞ', 'び': 'ﾋﾞ', 'ぶ': 'ﾌﾞ', 'べ': 'ﾍﾞ', 'ぼ': 'ﾎﾞ',
    'ぱ': 'ﾊﾟ', 'ぴ': 'ﾋﾟ', 'ぷ': 'ﾌﾟ', 'ぺ': 'ﾍﾟ', 'ぽ': 'ﾎﾟ',
    // 全角カタカナ
    'ア': 'ｱ', 'イ': 'ｲ', 'ウ': 'ｳ', 'エ': 'ｴ', 'オ': 'ｵ',
    'カ': 'ｶ', 'キ': 'ｷ', 'ク': 'ｸ', 'ケ': 'ｹ', 'コ': 'ｺ',
    'サ': 'ｻ', 'シ': 'ｼ', 'ス': 'ｽ', 'セ': 'ｾ', 'ソ': 'ｿ',
    'タ': 'ﾀ', 'チ': 'ﾁ', 'ツ': 'ﾂ', 'テ': 'ﾃ', 'ト': 'ﾄ',
    'ナ': 'ﾅ', 'ニ': 'ﾆ', 'ヌ': 'ﾇ', 'ネ': 'ﾈ', 'ノ': 'ﾉ',
    'ハ': 'ﾊ', 'ヒ': 'ﾋ', 'フ': 'ﾌ', 'ヘ': 'ﾍ', 'ホ': 'ﾎ',
    'マ': 'ﾏ', 'ミ': 'ﾐ', 'ム': 'ﾑ', 'メ': 'ﾒ', 'モ': 'ﾓ',
    'ヤ': 'ﾔ', 'ユ': 'ﾕ', 'ヨ': 'ﾖ',
    'ラ': 'ﾗ', 'リ': 'ﾘ', 'ル': 'ﾙ', 'レ': 'ﾚ', 'ロ': 'ﾛ',
    'ワ': 'ﾜ', 'ヲ': 'ｦ', 'ン': 'ﾝ',
    'ァ': 'ｧ', 'ィ': 'ｨ', 'ゥ': 'ｩ', 'ェ': 'ｪ', 'ォ': 'ｫ',
    'ッ': 'ｯ', 'ャ': 'ｬ', 'ュ': 'ｭ', 'ョ': 'ｮ',
    'ガ': 'ｶﾞ', 'ギ': 'ｷﾞ', 'グ': 'ｸﾞ', 'ゲ': 'ｹﾞ', 'ゴ': 'ｺﾞ',
    'ザ': 'ｻﾞ', 'ジ': 'ｼﾞ', 'ズ': 'ｽﾞ', 'ゼ': 'ｾﾞ', 'ゾ': 'ｿﾞ',
    'ダ': 'ﾀﾞ', 'ヂ': 'ﾁﾞ', 'ヅ': 'ﾂﾞ', 'デ': 'ﾃﾞ', 'ド': 'ﾄﾞ',
    'バ': 'ﾊﾞ', 'ビ': 'ﾋﾞ', 'ブ': 'ﾌﾞ', 'ベ': 'ﾍﾞ', 'ボ': 'ﾎﾞ',
    'パ': 'ﾊﾟ', 'ピ': 'ﾋﾟ', 'プ': 'ﾌﾟ', 'ペ': 'ﾍﾟ', 'ポ': 'ﾎﾟ',
    'ヴ': 'ｳﾞ',
    // 記号
    'ー': 'ｰ', '－': 'ｰ', '-': 'ｰ', ' ': ' ', '　': ' ',
  };
  return str.split('').map(char => kanaMap[char] || char).join('');
}

// 半角カタカナ・スペースのみを許可するフィルター
function filterHalfWidthKatakana(str: string): string {
  // 許可する文字: 半角カタカナ(ｦ-ﾟ)、半角スペース、濁点・半濁点
  return str.replace(/[^ｦ-ﾟ ]/g, '');
}

export default function PaymentEditPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [hasExistingAccount, setHasExistingAccount] = useState(false);
  const [existingAccountId, setExistingAccountId] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    bank_name: '',
    bank_code: '',
    branch_name: '',
    branch_code: '',
    account_type: 'ordinary' as 'ordinary' | 'current' | 'savings',
    account_number: '',
    account_holder: '',
    account_holder_kana: '',
  });

  useEffect(() => {
    fetchPayment();
  }, []);

  const fetchPayment = async () => {
    try {
      setLoading(true);
      const [paymentData, bankAccounts] = await Promise.all([
        getMyPayment(),
        getMyBankAccounts()
      ]);

      if (paymentData && paymentData.paymentRegistered && paymentData.bankName) {
        setHasExistingAccount(true);
        setFormData({
          bank_name: paymentData.bankName || '',
          bank_code: paymentData.bankCode || '',
          branch_name: paymentData.branchName || '',
          branch_code: paymentData.branchCode || '',
          account_type: paymentData.accountType || 'ordinary',
          account_number: paymentData.accountNumber || '',
          account_holder: paymentData.accountHolder || '',
          account_holder_kana: paymentData.accountHolderKana || '',
        });

        // 既存口座IDを取得（プライマリ口座を優先）
        const primaryAccount = bankAccounts.find(acc => acc.is_primary) || bankAccounts[0];
        if (primaryAccount) {
          setExistingAccountId(primaryAccount.id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch payment:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBankSelect = (data: {
    bankName: string;
    bankCode: string;
    branchName: string;
    branchCode: string;
  }) => {
    setFormData(prev => ({
      ...prev,
      bank_name: data.bankName,
      bank_code: data.bankCode,
      branch_name: data.branchName,
      branch_code: data.branchCode,
    }));
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
      // 送信時に半角カタカナに変換
      const kanaConverted = toHalfWidthKatakana(formData.account_holder_kana);
      const requestData: BankAccountRequestData = {
        request_type: hasExistingAccount ? 'update' : 'new',
        bank_name: formData.bank_name,
        bank_code: formData.bank_code,
        branch_name: formData.branch_name,
        branch_code: formData.branch_code,
        account_type: formData.account_type,
        account_number: formData.account_number,
        account_holder: formData.account_holder,
        account_holder_kana: kanaConverted,
        is_primary: true,
      };
      // 変更の場合は既存口座IDを含める
      if (hasExistingAccount && existingAccountId) {
        requestData.existing_account = existingAccountId;
      }
      await createBankAccountRequest(requestData);
      setSuccess(true);
    } catch (err: any) {
      console.error('Bank account request error:', err);
      const errorMessage = err?.data?.existing_account || err?.data?.detail || err?.message || '申請に失敗しました。もう一度お試しください。';
      setError(typeof errorMessage === 'string' ? errorMessage : '申請に失敗しました。もう一度お試しください。');
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
          <div className="w-20 h-20 rounded-full bg-amber-100 flex items-center justify-center mx-auto mb-6">
            <Clock className="w-10 h-10 text-amber-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-3">申請を受け付けました</h2>
          <p className="text-gray-600 mb-4">
            銀行口座の{hasExistingAccount ? '変更' : '登録'}申請を受け付けました。
          </p>
          <p className="text-sm text-gray-500 mb-8">
            担当者が確認後、登録を完了いたします。<br />
            しばらくお待ちください。
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

              {/* 銀行・支店選択コンポーネント */}
              <BankSelector
                onSelect={handleBankSelect}
                initialBank={formData.bank_code ? { name: formData.bank_name, code: formData.bank_code } : undefined}
                initialBranch={formData.branch_code ? { name: formData.branch_name, code: formData.branch_code } : undefined}
              />

              {/* 選択された銀行・支店の表示 */}
              {formData.bank_name && formData.branch_name && (
                <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                  <p className="text-sm text-blue-800">
                    <span className="font-medium">選択中:</span> {formData.bank_name} ({formData.bank_code}) / {formData.branch_name} ({formData.branch_code})
                  </p>
                </div>
              )}

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
                  placeholder="例: ｶﾂﾉ ﾋﾛﾅｵ"
                  value={formData.account_holder_kana}
                  onChange={(e) => {
                    // 入力を半角カタカナに自動変換
                    const converted = toHalfWidthKatakana(e.target.value);
                    setFormData({ ...formData, account_holder_kana: converted });
                  }}
                  className="rounded-xl h-12"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">ひらがな・カタカナ入力で半角カナに自動変換されます</p>
              </div>

            </CardContent>
          </Card>

          <Card className="rounded-xl shadow-md mb-6 border-amber-200 bg-amber-50">
            <CardContent className="p-4">
              <h3 className="text-sm font-semibold text-amber-900 mb-2">銀行口座の登録について</h3>
              <ul className="text-xs text-amber-800 space-y-1">
                <li>* 銀行口座の登録・変更は承認制となっております</li>
                <li>* 申請後、担当者が確認し承認処理を行います</li>
                <li>* 承認完了後、支払い方法として設定されます</li>
              </ul>
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
                申請中...
              </span>
            ) : (
              hasExistingAccount ? '変更を申請する' : '登録を申請する'
            )}
          </Button>
        </form>
      </main>
    </div>
  );
}
