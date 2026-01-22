'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { useUser } from '@/lib/hooks/use-user';
import { useContracts } from '@/lib/hooks/use-contracts';
import type { ContractSearchParams } from '@/lib/api/contracts';
import {
  Search,
  FileText,
  ChevronLeft,
  ChevronRight,
  Calendar,
  BookOpen,
  AlertCircle,
} from 'lucide-react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import { AuthGuard } from '@/components/auth';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: '下書き', color: 'bg-gray-100 text-gray-800' },
  pending: { label: '承認待ち', color: 'bg-yellow-100 text-yellow-800' },
  active: { label: '有効', color: 'bg-green-100 text-green-800' },
  suspended: { label: '休会中', color: 'bg-orange-100 text-orange-800' },
  cancelled: { label: '解約済', color: 'bg-red-100 text-red-800' },
  expired: { label: '期限切れ', color: 'bg-gray-100 text-gray-600' },
};

const STATUS_OPTIONS = [
  { value: '', label: '全ステータス' },
  { value: 'active', label: '有効' },
  { value: 'pending', label: '承認待ち' },
  { value: 'suspended', label: '休会中' },
  { value: 'cancelled', label: '解約済' },
  { value: 'expired', label: '期限切れ' },
];

function ContractsContent() {
  const router = useRouter();
  const [searchParams, setSearchParams] = useState<ContractSearchParams>({
    page: 1,
    pageSize: 20,
    search: '',
    status: '',
  });

  // ユーザー情報を取得
  const { data: user, isLoading: userLoading } = useUser();
  const isStaff = user?.userType === 'staff' || user?.userType === 'teacher';

  // 契約一覧を取得
  const { data: contractsData, isLoading: contractsLoading, error: contractsError, refetch } = useContracts(searchParams);

  const contracts = contractsData?.contracts || [];
  const pagination = {
    count: contractsData?.count || 0,
    hasNext: contractsData?.hasNext || false,
    hasPrev: contractsData?.hasPrev || false,
  };
  const loading = userLoading || contractsLoading;
  const error = contractsError ? '契約情報の取得に失敗しました' : null;

  const handleSearchChange = (value: string) => {
    setSearchParams((prev) => ({ ...prev, search: value, page: 1 }));
  };

  const handleStatusChange = (value: string) => {
    setSearchParams((prev) => ({ ...prev, status: value, page: 1 }));
  };

  const handlePageChange = (newPage: number) => {
    setSearchParams((prev) => ({ ...prev, page: newPage }));
  };

  const getStatusBadge = (status: string) => {
    const statusInfo = STATUS_LABELS[status] || { label: status, color: 'bg-gray-100 text-gray-800' };
    return (
      <Badge className={`${statusInfo.color} font-medium`}>
        {statusInfo.label}
      </Badge>
    );
  };

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'yyyy/MM/dd', { locale: ja });
    } catch {
      return dateString;
    }
  };

  const formatCurrency = (amount: string | number | undefined) => {
    if (!amount) return '-';
    const num = typeof amount === 'string' ? parseFloat(amount) : amount;
    return `¥${num.toLocaleString()}`;
  };

  if (userLoading) {
    return <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100" />;
  }

  if (user && !isStaff) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center">
        <Card className="max-w-md mx-4">
          <CardContent className="p-4 text-center">
            <AlertCircle className="w-10 h-10 text-yellow-500 mx-auto mb-3" />
            <p className="text-sm text-gray-600">このページは講師専用です</p>
            <Button className="mt-3" size="sm" onClick={() => router.push('/feed')}>
              フィードに戻る
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 pb-20">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              <h1 className="text-xl font-bold text-gray-900">契約一覧</h1>
            </div>
            <p className="text-sm text-gray-600 mt-1">
              {pagination.count}件の契約
            </p>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="p-4 space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              type="text"
              placeholder="生徒名・契約番号で検索..."
              value={searchParams.search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-10"
            />
          </div>

          <div className="flex gap-2">
            <Select value={searchParams.status} onValueChange={handleStatusChange}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="ステータス" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 pt-0">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="animate-pulse">
                  <CardContent className="p-4">
                    <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : error ? (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="p-4">
                <p className="text-red-600">{error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => refetch()}
                >
                  再読み込み
                </Button>
              </CardContent>
            </Card>
          ) : contracts.length === 0 ? (
            <Card>
              <CardContent className="p-6 text-center">
                <FileText className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">契約が見つかりません</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {contracts.map((contract) => (
                <Card
                  key={contract.id}
                  className="shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => router.push(`/contracts/${contract.id}`)}
                >
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-semibold text-gray-900">
                            {contract.student?.user?.fullName || '生徒情報なし'}
                          </h3>
                          {getStatusBadge(contract.status)}
                        </div>

                        {contract.contractNumber && (
                          <p className="text-xs text-gray-400 mb-2">
                            契約番号: {contract.contractNumber}
                          </p>
                        )}

                        <div className="flex flex-wrap gap-3 text-sm text-gray-600">
                          {contract.course && (
                            <div className="flex items-center gap-1">
                              <BookOpen className="w-3.5 h-3.5" />
                              <span>{contract.course.name}</span>
                            </div>
                          )}
                          {contract.startDate && (
                            <div className="flex items-center gap-1">
                              <Calendar className="w-3.5 h-3.5" />
                              <span>{formatDate(contract.startDate)}</span>
                              {contract.endDate && (
                                <span>〜 {formatDate(contract.endDate)}</span>
                              )}
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-3 mt-2 text-sm">
                          {contract.monthlyFee && (
                            <div className="flex items-center gap-1 text-green-600 font-medium">
                              <span>{formatCurrency(contract.monthlyFee)}/月</span>
                            </div>
                          )}
                          {contract.discountRate && contract.discountRate > 0 && (
                            <Badge variant="outline" className="text-xs">
                              {contract.discountRate}%OFF
                            </Badge>
                          )}
                        </div>
                      </div>

                      <ChevronRight className="w-5 h-5 text-gray-400 mt-1" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Pagination */}
          {!loading && !error && pagination.count > 0 && (
            <div className="flex justify-between items-center mt-4 px-2">
              <p className="text-sm text-gray-600">
                {((searchParams.page || 1) - 1) * (searchParams.pageSize || 20) + 1} - {Math.min((searchParams.page || 1) * (searchParams.pageSize || 20), pagination.count)} / {pagination.count}件
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!pagination.hasPrev}
                  onClick={() => handlePageChange((searchParams.page || 1) - 1)}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!pagination.hasNext}
                  onClick={() => handlePageChange((searchParams.page || 1) + 1)}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      <BottomTabBar />
    </div>
  );
}


export default function ContractsPage() {
  return (
    <AuthGuard>
      <ContractsContent />
    </AuthGuard>
  );
}
