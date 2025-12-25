'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, AlertCircle, ChevronLeft } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import Link from 'next/link';
import api from '@/lib/api/client';

interface Certification {
  id: string;
  certification_code: string;
  certification_name: string;
  certification_type: string;
  level?: string;
  brand_name?: string;
  year: number;
  exam_date?: string;
  exam_fee: number;
  description?: string;
  is_active: boolean;
}

interface CertificationSelectionProps {
  childId: string;
  brandId: string;
  schoolId: string;
  onBack: () => void;
}

export function CertificationSelection({ childId, brandId, schoolId, onBack }: CertificationSelectionProps) {
  const router = useRouter();
  const [subStep, setSubStep] = useState<'select' | 'confirm'>('select');
  const [certifications, setCertifications] = useState<Certification[]>([]);
  const [selectedCertifications, setSelectedCertifications] = useState<Certification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  useEffect(() => {
    const fetchCertifications = async () => {
      setIsLoading(true);
      try {
        const params = new URLSearchParams({ is_active: 'true' });
        if (brandId) params.append('brand_id', brandId);
        const response = await api.get<{ results?: Certification[] } | Certification[]>(`/contracts/certifications/?${params.toString()}`);
        const data = Array.isArray(response) ? response : (response.results || []);
        setCertifications(data);
      } catch (err) {
        setError('検定情報の取得に失敗しました');
      } finally {
        setIsLoading(false);
      }
    };
    fetchCertifications();
  }, [brandId]);

  const handleCertificationToggle = (certification: Certification) => {
    setSelectedCertifications(prev => {
      const exists = prev.find(c => c.id === certification.id);
      if (exists) {
        return prev.filter(c => c.id !== certification.id);
      }
      return [...prev, certification];
    });
  };

  const handleConfirm = async () => {
    if (!childId || selectedCertifications.length === 0) return;

    setIsSubmitting(true);
    setError(null);

    try {
      for (const certification of selectedCertifications) {
        await api.post('/contracts/certification-enrollments/', {
          student: childId,
          certification: certification.id,
          status: 'applied',
          unit_price: certification.exam_fee,
          discount_amount: 0,
          final_price: certification.exam_fee,
          billing_month: new Date().toISOString().slice(0, 7),
        });
      }

      router.push('/ticket-purchase/complete?type=certification');
    } catch (err: any) {
      setError(err.message || '申込に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalPrice = selectedCertifications.reduce((sum, c) => sum + c.exam_fee, 0);

  const getCertificationTypeLabel = (type: string) => {
    switch (type) {
      case 'eiken': return '英検';
      case 'kanken': return '漢検';
      case 'suken': return '数検';
      case 'shuzan': return '珠算検定';
      case 'anzan': return '暗算検定';
      default: return '検定';
    }
  };

  const getCertificationTypeColor = (type: string) => {
    switch (type) {
      case 'eiken': return 'bg-blue-100 text-blue-700';
      case 'kanken': return 'bg-red-100 text-red-700';
      case 'suken': return 'bg-green-100 text-green-700';
      case 'shuzan': return 'bg-amber-100 text-amber-700';
      case 'anzan': return 'bg-orange-100 text-orange-700';
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

  // 検定選択画面
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

        <h2 className="text-lg font-semibold text-gray-800 mb-4">検定を選択</h2>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-amber-500 mb-3" />
            <p className="text-sm text-gray-600">検定を読み込み中...</p>
          </div>
        ) : certifications.length === 0 ? (
          <p className="text-center text-gray-600 py-8">
            現在申込可能な検定はありません
          </p>
        ) : (
          <div className="space-y-3">
            {certifications.map((certification) => {
              const isSelected = selectedCertifications.some(c => c.id === certification.id);
              return (
                <Card
                  key={certification.id}
                  className={`rounded-xl shadow-md transition-all cursor-pointer border-2 ${
                    isSelected ? 'border-amber-500 bg-amber-50' : 'border-transparent'
                  }`}
                  onClick={() => handleCertificationToggle(certification)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <Checkbox checked={isSelected} className="mt-1" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className={getCertificationTypeColor(certification.certification_type)}>
                            {getCertificationTypeLabel(certification.certification_type)}
                          </Badge>
                        </div>
                        <h3 className="font-semibold text-gray-800">{certification.certification_name}</h3>
                        {certification.description && (
                          <p className="text-sm text-gray-600 mt-1">{certification.description}</p>
                        )}
                        {certification.exam_date && (
                          <p className="text-sm text-gray-500 mt-1">
                            試験日: {new Date(certification.exam_date).toLocaleDateString('ja-JP')}
                          </p>
                        )}
                        <div className="flex justify-between items-center mt-2">
                          <span className="text-sm text-gray-500">{certification.year}年{certification.level && ` ${certification.level}`}</span>
                          <span className="text-lg font-bold text-amber-600">
                            ¥{certification.exam_fee.toLocaleString()}
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

        {selectedCertifications.length > 0 && (
          <div className="mt-6 p-4 bg-amber-50 rounded-xl">
            <div className="flex justify-between items-center mb-3">
              <span className="text-gray-600">選択中: {selectedCertifications.length}件</span>
              <span className="text-xl font-bold text-amber-600">
                合計 ¥{totalPrice.toLocaleString()}
              </span>
            </div>
            <Button
              className="w-full bg-amber-600 hover:bg-amber-700"
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
        検定選択に戻る
      </button>

      <h2 className="text-lg font-semibold text-gray-800 mb-4">申込内容の確認</h2>

      <Card className="rounded-xl shadow-md mb-4">
        <CardContent className="p-4">
          <p className="text-sm text-gray-600 mb-2">申込検定</p>
          <div className="space-y-2">
            {selectedCertifications.map((certification) => (
              <div key={certification.id} className="flex justify-between items-center py-2 border-b">
                <div>
                  <p className="font-medium text-gray-800">{certification.certification_name}</p>
                  <Badge className={getCertificationTypeColor(certification.certification_type)}>
                    {getCertificationTypeLabel(certification.certification_type)}
                  </Badge>
                </div>
                <span className="font-semibold">¥{certification.exam_fee.toLocaleString()}</span>
              </div>
            ))}
          </div>

          <div className="flex justify-between items-center mt-4 pt-4 border-t">
            <span className="text-lg font-semibold">合計</span>
            <span className="text-2xl font-bold text-amber-600">
              ¥{totalPrice.toLocaleString()}
            </span>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-start gap-3 mb-6">
        <Checkbox
          id="terms-certification"
          checked={agreedToTerms}
          onCheckedChange={(checked) => setAgreedToTerms(checked as boolean)}
        />
        <label htmlFor="terms-certification" className="text-sm text-gray-600">
          <Link href="/terms" className="text-amber-600 underline">利用規約</Link>
          に同意します
        </label>
      </div>

      <Button
        className="w-full bg-amber-600 hover:bg-amber-700"
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
