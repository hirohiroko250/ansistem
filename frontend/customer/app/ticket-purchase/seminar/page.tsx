'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ChevronLeft, Calendar, Loader2, AlertCircle, CheckCircle2, Users } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import api from '@/lib/api/client';
import { getChildren } from '@/lib/api/students';
import type { Child } from '@/lib/api/types';

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

export default function SeminarPurchasePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const childId = searchParams.get('childId');
  const brandId = searchParams.get('brandId');

  const [step, setStep] = useState(1);
  const [children, setChildren] = useState<Child[]>([]);
  const [selectedChild, setSelectedChild] = useState<Child | null>(null);
  const [seminars, setSeminars] = useState<Seminar[]>([]);
  const [selectedSeminars, setSelectedSeminars] = useState<Seminar[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  // 子ども取得
  useEffect(() => {
    const fetchChildren = async () => {
      try {
        const data = await getChildren();
        setChildren(data);
        if (childId) {
          const child = data.find(c => c.id === childId);
          if (child) {
            setSelectedChild(child);
            setStep(2);
          }
        }
      } catch (err) {
        setError('お子様情報の取得に失敗しました');
      }
    };
    fetchChildren();
  }, [childId]);

  // 講習会取得
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

  const handleChildSelect = (child: Child) => {
    setSelectedChild(child);
    setStep(2);
  };

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
    if (!selectedChild || selectedSeminars.length === 0) return;

    setIsSubmitting(true);
    setError(null);

    try {
      // 各講習会に対してEnrollmentを作成
      for (const seminar of selectedSeminars) {
        await api.post('/contracts/seminar-enrollments/', {
          student: selectedChild.id,
          seminar: seminar.id,
          status: 'applied',
          unit_price: seminar.base_price,
          discount_amount: 0,
          final_price: seminar.base_price,
          billing_month: new Date().toISOString().slice(0, 7), // 当月
        });
      }

      router.push('/ticket-purchase/complete?type=seminar');
    } catch (err: any) {
      setError(err.response?.data?.detail || '申込に失敗しました');
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-purple-50 pb-24">
      {/* Header */}
      <div className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center">
          <button
            onClick={() => step > 1 ? setStep(step - 1) : router.back()}
            className="p-2 -ml-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <ChevronLeft className="h-6 w-6 text-gray-600" />
          </button>
          <h1 className="text-lg font-semibold text-gray-800 ml-2">
            講習会申込
          </h1>
          <div className="ml-auto flex items-center gap-1 text-sm text-gray-500">
            <span className="font-medium text-purple-600">{step}</span>
            <span>/</span>
            <span>3</span>
          </div>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 py-6">
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 mb-4">
            <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Step 1: 子ども選択 */}
        {step === 1 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">お子様を選択</h2>
            <div className="space-y-3">
              {children.map((child) => (
                <Card
                  key={child.id}
                  className="rounded-xl shadow-md hover:shadow-lg transition-all cursor-pointer"
                  onClick={() => handleChildSelect(child)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
                        <Users className="h-6 w-6 text-purple-600" />
                      </div>
                      <div>
                        <p className="font-semibold text-gray-800">{child.fullName}</p>
                        <p className="text-sm text-gray-600">{child.grade || '学年未設定'}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: 講習会選択 */}
        {step === 2 && (
          <div>
            <Card className="rounded-xl shadow-sm bg-purple-50 border-purple-200 mb-4">
              <CardContent className="p-3">
                <p className="text-xs text-gray-600 mb-1">選択中のお子様</p>
                <p className="font-semibold text-gray-800">{selectedChild?.fullName}</p>
              </CardContent>
            </Card>

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
                          <Checkbox
                            checked={isSelected}
                            className="mt-1"
                          />
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge className={getSeminarTypeColor(seminar.seminar_type)}>
                                {getSeminarTypeLabel(seminar.seminar_type)}
                              </Badge>
                              {seminar.brand_name && (
                                <Badge variant="outline">{seminar.brand_name}</Badge>
                              )}
                            </div>
                            <h3 className="font-semibold text-gray-800">{seminar.seminar_name}</h3>
                            {seminar.description && (
                              <p className="text-sm text-gray-600 mt-1">{seminar.description}</p>
                            )}
                            <div className="flex justify-between items-center mt-2">
                              <span className="text-sm text-gray-500">
                                {seminar.year}年
                              </span>
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
              <div className="fixed bottom-20 left-0 right-0 bg-white border-t shadow-lg p-4">
                <div className="max-w-lg mx-auto">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-gray-600">選択中: {selectedSeminars.length}件</span>
                    <span className="text-xl font-bold text-purple-600">
                      合計 ¥{totalPrice.toLocaleString()}
                    </span>
                  </div>
                  <Button
                    className="w-full bg-purple-600 hover:bg-purple-700"
                    onClick={() => setStep(3)}
                  >
                    確認画面へ
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 3: 確認 */}
        {step === 3 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">申込内容の確認</h2>

            <Card className="rounded-xl shadow-md mb-4">
              <CardContent className="p-4">
                <p className="text-sm text-gray-600 mb-2">お子様</p>
                <p className="font-semibold text-gray-800 mb-4">{selectedChild?.fullName}</p>

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
                id="terms"
                checked={agreedToTerms}
                onCheckedChange={(checked) => setAgreedToTerms(checked as boolean)}
              />
              <label htmlFor="terms" className="text-sm text-gray-600">
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
        )}
      </div>

      <BottomTabBar />
    </div>
  );
}
