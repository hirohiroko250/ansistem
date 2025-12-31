'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, AlertCircle, ChevronLeft, CheckCircle2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import Link from 'next/link';
import api from '@/lib/api/client';

interface Seminar {
  id: string;
  seminar_code: string;
  seminar_name: string;
  seminar_type: string;
  brand_name?: string;
  year: number;
  start_date?: string;
  end_date?: string;
  base_price: number;
  description?: string;
  is_active: boolean;
}

interface SeminarSelectionProps {
  childId: string;
  brandId: string;
  schoolId: string;
  onBack: () => void;
}

export function SeminarSelection({ childId, brandId, schoolId, onBack }: SeminarSelectionProps) {
  const router = useRouter();
  const [subStep, setSubStep] = useState<'select' | 'confirm'>('select');
  const [seminars, setSeminars] = useState<Seminar[]>([]);
  const [selectedSeminars, setSelectedSeminars] = useState<Seminar[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  useEffect(() => {
    const fetchSeminars = async () => {
      setIsLoading(true);
      try {
        const params = new URLSearchParams({ is_active: 'true' });
        if (brandId) params.append('brand_id', brandId);
        const response = await api.get<{ results?: Seminar[] } | Seminar[]>(`/contracts/seminars/?${params.toString()}`);
        const data = Array.isArray(response) ? response : (response.results || []);
        setSeminars(data);
      } catch (err) {
        setError('講習会情報の取得に失敗しました');
      } finally {
        setIsLoading(false);
      }
    };
    fetchSeminars();
  }, [brandId]);

  const handleSeminarToggle = (seminar: Seminar) => {
    setSelectedSeminars(prev => {
      const exists = prev.find(s => s.id === seminar.id);
      if (exists) {
        return prev.filter(s => s.id !== seminar.id);
      }
      return [...prev, seminar];
    });
  };

  const handleConfirm = async () => {
    if (!childId || selectedSeminars.length === 0) return;

    setIsSubmitting(true);
    setError(null);

    try {
      for (const seminar of selectedSeminars) {
        await api.post('/contracts/seminar-enrollments/', {
          student: childId,
          seminar: seminar.id,
          status: 'applied',
          unit_price: seminar.base_price,
          discount_amount: 0,
          final_price: seminar.base_price,
          billing_month: new Date().toISOString().slice(0, 7),
        });
      }

      // 完了ページ用の結果を保存
      const purchaseResult = {
        orderId: `SEM-${Date.now()}`,
        childName: '',  // 子ども名は親コンポーネントから取得できない
        childId: childId,
        courseName: selectedSeminars.map(s => s.seminar_name).join('、'),
        courseId: selectedSeminars[0]?.id || '',
        amount: totalPrice,
        startDate: null,
        type: 'seminar',
      };
      sessionStorage.setItem('purchaseResult', JSON.stringify(purchaseResult));

      router.push('/ticket-purchase/complete?type=seminar');
    } catch (err: any) {
      setError(err.message || '申込に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalPrice = selectedSeminars.reduce((sum, s) => sum + s.base_price, 0);

  const getSeminarTypeLabel = (type: string) => {
    switch (type) {
      case 'summer': return '夏期講習';
      case 'winter': return '冬期講習';
      case 'spring': return '春期講習';
      default: return '講習会';
    }
  };

  const getSeminarTypeColor = (type: string) => {
    switch (type) {
      case 'summer': return 'bg-orange-100 text-orange-700';
      case 'winter': return 'bg-blue-100 text-blue-700';
      case 'spring': return 'bg-pink-100 text-pink-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  if (error) {
    return (
      <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
        <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
        <p className="text-sm text-red-800">{error}</p>
      </div>
    );
  }

  // 講習会選択画面
  if (subStep === 'select') {
    return (
      <div>
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-gray-600 mb-4 hover:text-gray-800"
        >
          <ChevronLeft className="h-4 w-4" />
          お子様選択に戻る
        </button>

        <h2 className="text-lg font-semibold text-gray-800 mb-4">講習会を選択</h2>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-purple-500 mb-3" />
            <p className="text-sm text-gray-600">講習会を読み込み中...</p>
          </div>
        ) : seminars.length === 0 ? (
          <p className="text-center text-gray-600 py-8">
            現在申込可能な講習会はありません
          </p>
        ) : (
          <div className="space-y-3">
            {seminars.map((seminar) => {
              const isSelected = selectedSeminars.some(s => s.id === seminar.id);
              return (
                <Card
                  key={seminar.id}
                  className={`rounded-xl shadow-md transition-all cursor-pointer border-2 ${
                    isSelected ? 'border-purple-500 bg-purple-50' : 'border-transparent'
                  }`}
                  onClick={() => handleSeminarToggle(seminar)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <Checkbox checked={isSelected} className="mt-1" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className={getSeminarTypeColor(seminar.seminar_type)}>
                            {getSeminarTypeLabel(seminar.seminar_type)}
                          </Badge>
                        </div>
                        <h3 className="font-semibold text-gray-800">{seminar.seminar_name}</h3>
                        {seminar.description && (
                          <p className="text-sm text-gray-600 mt-1">{seminar.description}</p>
                        )}
                        <div className="flex justify-between items-center mt-2">
                          <span className="text-sm text-gray-500">{seminar.year}年</span>
                          <span className="text-lg font-bold text-purple-600">
                            ¥{seminar.base_price.toLocaleString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {selectedSeminars.length > 0 && (
          <div className="mt-6 p-4 bg-purple-50 rounded-xl">
            <div className="flex justify-between items-center mb-3">
              <span className="text-gray-600">選択中: {selectedSeminars.length}件</span>
              <span className="text-xl font-bold text-purple-600">
                合計 ¥{totalPrice.toLocaleString()}
              </span>
            </div>
            <Button
              className="w-full bg-purple-600 hover:bg-purple-700"
              onClick={() => setSubStep('confirm')}
            >
              確認画面へ
            </Button>
          </div>
        )}
      </div>
    );
  }

  // 確認画面
  return (
    <div>
      <button
        onClick={() => setSubStep('select')}
        className="flex items-center gap-1 text-sm text-gray-600 mb-4 hover:text-gray-800"
      >
        <ChevronLeft className="h-4 w-4" />
        講習会選択に戻る
      </button>

      <h2 className="text-lg font-semibold text-gray-800 mb-4">申込内容の確認</h2>

      <Card className="rounded-xl shadow-md mb-4">
        <CardContent className="p-4">
          <p className="text-sm text-gray-600 mb-2">申込講習会</p>
          <div className="space-y-2">
            {selectedSeminars.map((seminar) => (
              <div key={seminar.id} className="flex justify-between items-center py-2 border-b">
                <div>
                  <p className="font-medium text-gray-800">{seminar.seminar_name}</p>
                  <Badge className={getSeminarTypeColor(seminar.seminar_type)}>
                    {getSeminarTypeLabel(seminar.seminar_type)}
                  </Badge>
                </div>
                <span className="font-semibold">¥{seminar.base_price.toLocaleString()}</span>
              </div>
            ))}
          </div>

          <div className="flex justify-between items-center mt-4 pt-4 border-t">
            <span className="text-lg font-semibold">合計</span>
            <span className="text-2xl font-bold text-purple-600">
              ¥{totalPrice.toLocaleString()}
            </span>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-start gap-3 mb-6">
        <Checkbox
          id="terms-seminar"
          checked={agreedToTerms}
          onCheckedChange={(checked) => setAgreedToTerms(checked as boolean)}
        />
        <label htmlFor="terms-seminar" className="text-sm text-gray-600">
          <Link href="/terms" className="text-purple-600 underline">利用規約</Link>
          に同意します
        </label>
      </div>

      <Button
        className="w-full bg-purple-600 hover:bg-purple-700"
        disabled={!agreedToTerms || isSubmitting}
        onClick={handleConfirm}
      >
        {isSubmitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
            申込中...
          </>
        ) : (
          '申込を確定する'
        )}
      </Button>
    </div>
  );
}
