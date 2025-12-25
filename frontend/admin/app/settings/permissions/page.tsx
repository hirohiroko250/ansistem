"use client";

import { useEffect, useState, useCallback } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ChevronLeft,
  Loader2,
  RefreshCw,
  Shield,
  Users,
  Settings,
  PlusCircle,
  Save,
  Building2,
  Tag,
  Mail,
  Calculator,
} from "lucide-react";
import Link from "next/link";
import apiClient from "@/lib/api/client";

// 型定義
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

export default function PermissionsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [positions, setPositions] = useState<Position[]>([]);
  const [matrix, setMatrix] = useState<MatrixRow[]>([]);
  const [activeTab, setActiveTab] = useState("matrix");

  // 役職作成ダイアログ
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newPositionName, setNewPositionName] = useState("");
  const [newPositionCode, setNewPositionCode] = useState("");
  const [newPositionRank, setNewPositionRank] = useState(0);
  const [creating, setCreating] = useState(false);

  // データ取得
  const loadMatrix = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.get<PermissionMatrix>("/tenants/permissions/matrix/");
      setPositions(data.positions || []);
      setMatrix(data.matrix || []);
    } catch (error) {
      console.error("Error loading permission matrix:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMatrix();
  }, [loadMatrix]);

  // 権限トグル
  const handleTogglePermission = async (positionId: string, featureId: string) => {
    try {
      await apiClient.post<{ success: boolean; has_permission: boolean }>(
        "/tenants/permissions/toggle/",
        { position_id: positionId, feature_id: featureId }
      );
      // ローカル状態を更新
      setMatrix((prev) =>
        prev.map((row) => {
          if (row.feature_id === featureId) {
            return {
              ...row,
              permissions: {
                ...row.permissions,
                [positionId]: !row.permissions[positionId],
              },
            };
          }
          return row;
        })
      );
    } catch (error) {
      console.error("Error toggling permission:", error);
    }
  };

  // グローバル権限トグル
  const handleToggleGlobalPermission = async (
    positionId: string,
    field: keyof Pick<Position, 'school_restriction' | 'brand_restriction' | 'bulk_email_restriction' | 'email_approval_required' | 'is_accounting'>
  ) => {
    const position = positions.find((p) => p.id === positionId);
    if (!position) return;

    setSaving(true);
    try {
      await apiClient.patch(`/tenants/positions/${positionId}/update_global_permissions/`, {
        [field]: !position[field],
      });
      // ローカル状態を更新
      setPositions((prev) =>
        prev.map((p) => {
          if (p.id === positionId) {
            return { ...p, [field]: !p[field] };
          }
          return p;
        })
      );
    } catch (error) {
      console.error("Error updating global permission:", error);
    } finally {
      setSaving(false);
    }
  };

  // 新規役職作成
  const handleCreatePosition = async () => {
    if (!newPositionName) return;
    setCreating(true);
    try {
      await apiClient.post("/tenants/positions/", {
        position_name: newPositionName,
        position_code: newPositionCode,
        rank: newPositionRank,
      });
      setCreateDialogOpen(false);
      setNewPositionName("");
      setNewPositionCode("");
      setNewPositionRank(0);
      loadMatrix();
    } catch (error) {
      console.error("Error creating position:", error);
    } finally {
      setCreating(false);
    }
  };

  // カテゴリでグループ化
  const groupedMatrix = matrix.reduce((acc, row) => {
    const category = row.category || "その他";
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(row);
    return acc;
  }, {} as Record<string, MatrixRow[]>);

  return (
    <ThreePaneLayout>
      <div className="p-6 h-full flex flex-col">
        {/* ヘッダー */}
        <div className="mb-6">
          <div className="flex items-center gap-4 mb-2">
            <Link href="/settings">
              <Button variant="ghost" size="sm">
                <ChevronLeft className="w-4 h-4 mr-1" />
                設定
              </Button>
            </Link>
          </div>
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">権限設定</h1>
              <p className="text-gray-600">役職ごとの機能アクセス権限を設定します</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={loadMatrix} disabled={loading}>
                <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
                更新
              </Button>
              <Button onClick={() => setCreateDialogOpen(true)}>
                <PlusCircle className="w-4 h-4 mr-1" />
                役職追加
              </Button>
            </div>
          </div>
        </div>

        {/* タブ */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="mb-4">
            <TabsTrigger value="matrix" className="flex items-center gap-2">
              <Shield className="w-4 h-4" />
              権限マトリックス
            </TabsTrigger>
            <TabsTrigger value="global" className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              グローバル権限
            </TabsTrigger>
          </TabsList>

          {/* 権限マトリックスタブ */}
          <TabsContent value="matrix" className="flex-1 flex flex-col overflow-hidden">
            <Card className="flex-1 flex flex-col overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Shield className="w-5 h-5" />
                  機能別権限設定
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 overflow-auto p-0">
                {loading ? (
                  <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                  </div>
                ) : positions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                    <Users className="w-12 h-12 text-gray-300 mb-4" />
                    <p>役職が登録されていません</p>
                    <Button
                      variant="outline"
                      className="mt-4"
                      onClick={() => setCreateDialogOpen(true)}
                    >
                      <PlusCircle className="w-4 h-4 mr-1" />
                      役職を追加
                    </Button>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="sticky left-0 bg-white z-10 min-w-[200px]">
                            機能
                          </TableHead>
                          {positions.map((position) => (
                            <TableHead
                              key={position.id}
                              className="text-center min-w-[100px]"
                            >
                              <div className="flex flex-col items-center gap-1">
                                <Badge variant="outline" className="text-xs">
                                  {position.rank}
                                </Badge>
                                <span className="text-xs font-medium">
                                  {position.position_name}
                                </span>
                              </div>
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(groupedMatrix).map(([category, rows]) => (
                          <>
                            {/* カテゴリヘッダー */}
                            <TableRow key={`cat-${category}`} className="bg-gray-100">
                              <TableCell
                                colSpan={positions.length + 1}
                                className="font-semibold text-gray-700"
                              >
                                {category}
                              </TableCell>
                            </TableRow>
                            {/* 機能行 */}
                            {rows.map((row) => (
                              <TableRow key={row.feature_id}>
                                <TableCell className="sticky left-0 bg-white z-10">
                                  <div className="flex items-center gap-2">
                                    {row.parent_code && (
                                      <span className="text-gray-400 ml-4">└</span>
                                    )}
                                    <span className={row.parent_code ? "text-sm" : "font-medium"}>
                                      {row.feature_name}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                      [{row.feature_code}]
                                    </span>
                                  </div>
                                </TableCell>
                                {positions.map((position) => (
                                  <TableCell
                                    key={`${row.feature_id}-${position.id}`}
                                    className="text-center"
                                  >
                                    <Checkbox
                                      checked={row.permissions[position.id] || false}
                                      onCheckedChange={() =>
                                        handleTogglePermission(position.id, row.feature_id)
                                      }
                                    />
                                  </TableCell>
                                ))}
                              </TableRow>
                            ))}
                          </>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* グローバル権限タブ */}
          <TabsContent value="global" className="flex-1 flex flex-col overflow-hidden">
            <Card className="flex-1 flex flex-col overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  グローバル権限設定
                  {saving && <Loader2 className="w-4 h-4 animate-spin ml-2" />}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 overflow-auto p-0">
                {loading ? (
                  <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="min-w-[150px]">役職</TableHead>
                        <TableHead className="text-center">
                          <div className="flex flex-col items-center gap-1">
                            <Building2 className="w-4 h-4" />
                            <span className="text-xs">校舎制限</span>
                          </div>
                        </TableHead>
                        <TableHead className="text-center">
                          <div className="flex flex-col items-center gap-1">
                            <Tag className="w-4 h-4" />
                            <span className="text-xs">ブランド制限</span>
                          </div>
                        </TableHead>
                        <TableHead className="text-center">
                          <div className="flex flex-col items-center gap-1">
                            <Mail className="w-4 h-4" />
                            <span className="text-xs">一括送信制限</span>
                          </div>
                        </TableHead>
                        <TableHead className="text-center">
                          <div className="flex flex-col items-center gap-1">
                            <Mail className="w-4 h-4" />
                            <span className="text-xs">上長承認必要</span>
                          </div>
                        </TableHead>
                        <TableHead className="text-center">
                          <div className="flex flex-col items-center gap-1">
                            <Calculator className="w-4 h-4" />
                            <span className="text-xs">経理権限</span>
                          </div>
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {positions.map((position) => (
                        <TableRow key={position.id}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-xs">
                                {position.rank}
                              </Badge>
                              <span className="font-medium">{position.position_name}</span>
                            </div>
                          </TableCell>
                          <TableCell className="text-center">
                            <Switch
                              checked={position.school_restriction}
                              onCheckedChange={() =>
                                handleToggleGlobalPermission(position.id, "school_restriction")
                              }
                            />
                          </TableCell>
                          <TableCell className="text-center">
                            <Switch
                              checked={position.brand_restriction}
                              onCheckedChange={() =>
                                handleToggleGlobalPermission(position.id, "brand_restriction")
                              }
                            />
                          </TableCell>
                          <TableCell className="text-center">
                            <Switch
                              checked={position.bulk_email_restriction}
                              onCheckedChange={() =>
                                handleToggleGlobalPermission(position.id, "bulk_email_restriction")
                              }
                            />
                          </TableCell>
                          <TableCell className="text-center">
                            <Switch
                              checked={position.email_approval_required}
                              onCheckedChange={() =>
                                handleToggleGlobalPermission(position.id, "email_approval_required")
                              }
                            />
                          </TableCell>
                          <TableCell className="text-center">
                            <Switch
                              checked={position.is_accounting}
                              onCheckedChange={() =>
                                handleToggleGlobalPermission(position.id, "is_accounting")
                              }
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* 役職作成ダイアログ */}
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <PlusCircle className="w-5 h-5" />
                新規役職追加
              </DialogTitle>
              <DialogDescription>
                新しい役職を作成します
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label>役職名 *</Label>
                <Input
                  value={newPositionName}
                  onChange={(e) => setNewPositionName(e.target.value)}
                  placeholder="例: 課長"
                  className="mt-2"
                />
              </div>
              <div>
                <Label>役職コード</Label>
                <Input
                  value={newPositionCode}
                  onChange={(e) => setNewPositionCode(e.target.value)}
                  placeholder="例: MGR"
                  className="mt-2"
                />
              </div>
              <div>
                <Label>ランク（数字が大きいほど上位）</Label>
                <Input
                  type="number"
                  value={newPositionRank}
                  onChange={(e) => setNewPositionRank(Number(e.target.value))}
                  className="mt-2"
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setCreateDialogOpen(false)}
                disabled={creating}
              >
                キャンセル
              </Button>
              <Button onClick={handleCreatePosition} disabled={creating || !newPositionName}>
                {creating ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Save className="w-4 h-4 mr-2" />
                )}
                作成
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </ThreePaneLayout>
  );
}
