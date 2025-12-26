'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Save, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface Position {
  id: string;
  position_code: string;
  position_name: string;
  rank: number;
  school_restriction: boolean;
  brand_restriction: boolean;
  bulk_email_restriction: boolean;
  email_approval_required: boolean;
  is_accounting: boolean;
  is_active: boolean;
}

interface Feature {
  id: string;
  feature_code: string;
  feature_name: string;
  parent_code: string;
  category: string;
  display_order: number;
  is_active: boolean;
}

interface MatrixRow {
  feature_id: string;
  feature_code: string;
  feature_name: string;
  parent_code: string;
  category: string;
  permissions: Record<string, boolean>;
}

interface PermissionMatrix {
  positions: Position[];
  features: Feature[];
  matrix: MatrixRow[];
}

interface GlobalPermissions {
  [positionId: string]: {
    school_restriction: boolean;
    brand_restriction: boolean;
    bulk_email_restriction: boolean;
    email_approval_required: boolean;
    is_accounting: boolean;
  };
}

export default function PermissionsPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [positions, setPositions] = useState<Position[]>([]);
  const [matrix, setMatrix] = useState<MatrixRow[]>([]);
  const [globalPermissions, setGlobalPermissions] = useState<GlobalPermissions>({});

  // 変更追跡
  const [changedPermissions, setChangedPermissions] = useState<Set<string>>(new Set());
  const [changedGlobalPermissions, setChangedGlobalPermissions] = useState<Set<string>>(new Set());

  const loadPermissions = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // 権限マトリックスを取得
      const data = await apiClient.get<PermissionMatrix>('/tenants/permissions/matrix/');

      setPositions(data.positions);
      setMatrix(data.matrix);

      // グローバル権限を初期化
      const globalPerms: GlobalPermissions = {};
      data.positions.forEach(pos => {
        globalPerms[pos.id] = {
          school_restriction: pos.school_restriction,
          brand_restriction: pos.brand_restriction,
          bulk_email_restriction: pos.bulk_email_restriction,
          email_approval_required: pos.email_approval_required,
          is_accounting: pos.is_accounting,
        };
      });
      setGlobalPermissions(globalPerms);

    } catch (err) {
      console.error('Failed to load permissions:', err);
      setError('権限データの読み込みに失敗しました');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPermissions();
  }, [loadPermissions]);

  // 機能権限の変更
  const handlePermissionChange = (featureId: string, positionId: string, checked: boolean) => {
    setMatrix(prev => prev.map(row => {
      if (row.feature_id === featureId) {
        return {
          ...row,
          permissions: {
            ...row.permissions,
            [positionId]: checked,
          },
        };
      }
      return row;
    }));
    setChangedPermissions(prev => new Set(prev).add(`${featureId}_${positionId}`));
    setSuccess(null);
  };

  // グローバル権限の変更
  const handleGlobalPermissionChange = (
    positionId: string,
    field: keyof GlobalPermissions[string],
    checked: boolean
  ) => {
    setGlobalPermissions(prev => ({
      ...prev,
      [positionId]: {
        ...prev[positionId],
        [field]: checked,
      },
    }));
    setChangedGlobalPermissions(prev => new Set(prev).add(`${positionId}_${field}`));
    setSuccess(null);
  };

  // 保存処理
  const handleSave = async () => {
    try {
      setIsSaving(true);
      setError(null);
      setSuccess(null);

      // グローバル権限の更新
      const changedGlobalArray = Array.from(changedGlobalPermissions);
      for (const positionId of Object.keys(globalPermissions)) {
        if (changedGlobalArray.some(key => key.startsWith(positionId))) {
          await apiClient.patch(`/tenants/positions/${positionId}/update_global_permissions/`,
            globalPermissions[positionId]
          );
        }
      }

      // 機能権限の更新
      if (changedPermissions.size > 0) {
        const permissions: { position_id: string; feature_id: string; has_permission: boolean }[] = [];
        const changedArray = Array.from(changedPermissions);

        for (const key of changedArray) {
          const [featureId, positionId] = key.split('_');
          const row = matrix.find(r => r.feature_id === featureId);
          if (row) {
            permissions.push({
              position_id: positionId,
              feature_id: featureId,
              has_permission: row.permissions[positionId] || false,
            });
          }
        }

        if (permissions.length > 0) {
          await apiClient.post('/tenants/permissions/bulk_update/', { permissions });
        }
      }

      setChangedPermissions(new Set());
      setChangedGlobalPermissions(new Set());
      setSuccess('権限設定を保存しました');

    } catch (err) {
      console.error('Failed to save permissions:', err);
      setError('権限設定の保存に失敗しました');
    } finally {
      setIsSaving(false);
    }
  };

  const hasChanges = changedPermissions.size > 0 || changedGlobalPermissions.size > 0;

  // カテゴリごとにグループ化
  const groupedFeatures = matrix.reduce((acc, row) => {
    const category = row.category || '機能一覧';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(row);
    return acc;
  }, {} as Record<string, MatrixRow[]>);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-full overflow-x-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">権限設定</h1>
        <Button
          onClick={handleSave}
          disabled={isSaving || !hasChanges}
          className="min-w-[150px]"
        >
          {isSaving ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              保存中...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-2" />
              変更を保存
            </>
          )}
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="mb-4 border-green-500 bg-green-50">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-600">{success}</AlertDescription>
        </Alert>
      )}

      {/* グローバル権限 */}
      <Card className="mb-6">
        <CardHeader className="py-3 bg-blue-50">
          <CardTitle className="text-lg">グローバル権限</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border border-gray-300 px-4 py-2 text-left font-medium text-gray-700 min-w-[200px]">
                    権限名
                  </th>
                  {positions.map(pos => (
                    <th
                      key={pos.id}
                      className="border border-gray-300 px-2 py-2 text-center font-medium text-gray-700 min-w-[100px] text-sm"
                    >
                      {pos.position_name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { key: 'school_restriction', label: '校舎制限' },
                  { key: 'brand_restriction', label: 'ブランド制限' },
                  { key: 'bulk_email_restriction', label: 'メール一括送信制限' },
                  { key: 'email_approval_required', label: 'メール上長承認必要' },
                  { key: 'is_accounting', label: '経理' },
                ].map(({ key, label }) => (
                  <tr key={key} className="hover:bg-gray-50">
                    <th className="border border-gray-300 px-4 py-2 text-left font-medium text-gray-700 bg-gray-50">
                      {label}
                    </th>
                    {positions.map(pos => (
                      <td key={pos.id} className="border border-gray-300 px-2 py-2 text-center">
                        <Checkbox
                          checked={globalPermissions[pos.id]?.[key as keyof GlobalPermissions[string]] || false}
                          onCheckedChange={(checked) =>
                            handleGlobalPermissionChange(pos.id, key as keyof GlobalPermissions[string], !!checked)
                          }
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* 機能権限 */}
      {Object.entries(groupedFeatures).map(([category, features]) => (
        <Card key={category} className="mb-6">
          <CardHeader className="py-3 bg-blue-50">
            <CardTitle className="text-lg">{category}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="border border-gray-300 px-4 py-2 text-left font-medium text-gray-700 min-w-[300px]">
                      機能名
                    </th>
                    {positions.map(pos => (
                      <th
                        key={pos.id}
                        className="border border-gray-300 px-2 py-2 text-center font-medium text-gray-700 min-w-[100px] text-sm"
                      >
                        {pos.position_name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {features.map(row => (
                    <tr key={row.feature_id} className="hover:bg-gray-50">
                      <th className="border border-gray-300 px-4 py-2 text-left font-normal text-gray-700 bg-gray-50">
                        <span className="text-gray-500 mr-2">{row.feature_code}.</span>
                        {row.feature_name}
                      </th>
                      {positions.map(pos => (
                        <td key={pos.id} className="border border-gray-300 px-2 py-2 text-center">
                          <Checkbox
                            checked={row.permissions[pos.id] || false}
                            onCheckedChange={(checked) =>
                              handlePermissionChange(row.feature_id, pos.id, !!checked)
                            }
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ))}

      {matrix.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-gray-500">
            <p>機能マスタが登録されていません。</p>
            <p className="text-sm mt-2">Django管理画面から機能マスタを登録してください。</p>
          </CardContent>
        </Card>
      )}

      {/* フッターの保存ボタン */}
      {hasChanges && (
        <div className="fixed bottom-6 right-6 z-50">
          <Button
            onClick={handleSave}
            disabled={isSaving}
            size="lg"
            className="shadow-lg"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                変更を保存 ({changedPermissions.size + changedGlobalPermissions.size}件)
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
