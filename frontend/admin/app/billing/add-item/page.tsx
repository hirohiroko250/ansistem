"use client";

import { useState, useEffect } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
} from "@/components/ui/dialog";
import {
  ArrowLeft,
  Search,
  Plus,
  Trash2,
  CheckCircle,
  Upload,
  FileSpreadsheet,
  Download,
  AlertCircle,
} from "lucide-react";
import { useRouter } from "next/navigation";
import apiClient from "@/lib/api/client";

interface Student {
  id: string;
  old_id: string;
  student_no: string;
  last_name: string;
  first_name: string;
  full_name: string;
  status: string;
  guardian?: {
    id: string;
    old_id: string;
    full_name: string;
  };
}

interface Product {
  id: string;
  product_code: string;
  product_name: string;
  item_type: string;
  base_price: number;
}

interface Brand {
  id: string;
  brand_code: string;
  brand_name: string;
}

interface AddItemForm {
  student: Student | null;
  billing_month: string;
  product_id: string;
  product_name: string;
  brand_id: string;
  unit_price: number;
  quantity: number;
  discount_amount: number;
  notes: string;
}

interface ImportResult {
  success: boolean;
  created_count: number;
  error_count: number;
  errors: { row: number; error: string }[];
}

export default function AddItemPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [activeTab, setActiveTab] = useState("single");

  // 生徒検索
  const [studentSearchOpen, setStudentSearchOpen] = useState(false);
  const [studentSearchQuery, setStudentSearchQuery] = useState("");
  const [studentSearchResults, setStudentSearchResults] = useState<Student[]>(
    []
  );
  const [searchingStudents, setSearchingStudents] = useState(false);

  // マスタデータ
  const [products, setProducts] = useState<Product[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);

  // 追加する明細のリスト
  const [items, setItems] = useState<AddItemForm[]>([]);

  // 現在編集中のフォーム
  const [currentForm, setCurrentForm] = useState<AddItemForm>({
    student: null,
    billing_month: `${new Date().getFullYear()}-${String(
      new Date().getMonth() + 2
    ).padStart(2, "0")}`,
    product_id: "",
    product_name: "",
    brand_id: "",
    unit_price: 0,
    quantity: 1,
    discount_amount: 0,
    notes: "",
  });

  // インポート関連
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  useEffect(() => {
    loadMasterData();
  }, []);

  async function loadMasterData() {
    try {
      const [productsRes, brandsRes] = await Promise.all([
        apiClient.get<{ results: Product[] }>(
          "/contracts/products/?page_size=500"
        ),
        apiClient.get<{ results: Brand[] }>("/master/brands/?page_size=100"),
      ]);
      setProducts(productsRes.results || []);
      setBrands(brandsRes.results || []);
    } catch (error) {
      console.error("Failed to load master data:", error);
    }
  }

  async function searchStudents() {
    if (!studentSearchQuery.trim()) return;

    setSearchingStudents(true);
    try {
      const res = await apiClient.get<{ results: Student[] }>(
        `/students/?search=${encodeURIComponent(
          studentSearchQuery
        )}&page_size=20`
      );
      setStudentSearchResults(res.results || []);
    } catch (error) {
      console.error("Failed to search students:", error);
    } finally {
      setSearchingStudents(false);
    }
  }

  function selectStudent(student: Student) {
    setCurrentForm((prev) => ({ ...prev, student }));
    setStudentSearchOpen(false);
    setStudentSearchQuery("");
    setStudentSearchResults([]);
  }

  function handleProductChange(productId: string) {
    const product = products.find((p) => p.id === productId);
    if (product) {
      setCurrentForm((prev) => ({
        ...prev,
        product_id: productId,
        product_name: product.product_name,
        unit_price: product.base_price || 0,
      }));
    }
  }

  function addItemToList() {
    if (!currentForm.student) {
      alert("生徒を選択してください");
      return;
    }
    if (!currentForm.unit_price && !currentForm.product_name) {
      alert("商品名または金額を入力してください");
      return;
    }

    setItems((prev) => [...prev, { ...currentForm }]);

    // フォームをリセット（生徒と請求月は保持）
    setCurrentForm((prev) => ({
      ...prev,
      product_id: "",
      product_name: "",
      brand_id: "",
      unit_price: 0,
      quantity: 1,
      discount_amount: 0,
      notes: "",
    }));
  }

  function removeItem(index: number) {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }

  async function submitItems() {
    if (items.length === 0) {
      alert("追加する明細がありません");
      return;
    }

    setLoading(true);
    try {
      for (const item of items) {
        const finalPrice =
          item.unit_price * item.quantity - item.discount_amount;

        await apiClient.post("/contracts/student-items/", {
          student: item.student?.id,
          billing_month: item.billing_month,
          product: item.product_id || null,
          brand: item.brand_id || null,
          unit_price: item.unit_price,
          quantity: item.quantity,
          discount_amount: item.discount_amount,
          final_price: finalPrice,
          notes: item.notes || item.product_name,
        });
      }

      setSuccess(true);
      setItems([]);

      setTimeout(() => {
        router.push("/billing/confirmed");
      }, 2000);
    } catch (error) {
      console.error("Failed to add items:", error);
      alert("登録に失敗しました");
    } finally {
      setLoading(false);
    }
  }

  // インポート処理
  async function handleImport() {
    if (!importFile) {
      alert("ファイルを選択してください");
      return;
    }

    setImporting(true);
    setImportResult(null);

    try {
      const formData = new FormData();
      formData.append("file", importFile);

      const result = await apiClient.upload<ImportResult>(
        "/contracts/student-items/import/",
        formData
      );

      setImportResult(result);

      if (result.success && result.created_count > 0 && result.error_count === 0) {
        setTimeout(() => {
          router.push("/billing/confirmed");
        }, 3000);
      }
    } catch (error) {
      console.error("Import failed:", error);
      setImportResult({
        success: false,
        created_count: 0,
        error_count: 1,
        errors: [{ row: 0, error: "インポートに失敗しました" }],
      });
    } finally {
      setImporting(false);
    }
  }

  // テンプレートダウンロード
  function downloadTemplate() {
    const headers = [
      "student_old_id",
      "billing_month",
      "product_name",
      "unit_price",
      "quantity",
      "discount_amount",
      "brand_code",
      "notes",
    ];
    const sampleRow = [
      "123456",
      "2026-02",
      "メプレス2026年2月分授業料",
      "30000",
      "1",
      "0",
      "",
      "",
    ];

    const csv = [headers.join(","), sampleRow.join(",")].join("\n");
    const bom = "\uFEFF";
    const blob = new Blob([bom + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "追加請求インポートテンプレート.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const totalAmount = items.reduce(
    (sum, item) => sum + item.unit_price * item.quantity - item.discount_amount,
    0
  );

  // 年月の選択肢を生成
  const monthOptions = [];
  const now = new Date();
  for (let i = -2; i <= 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(
      2,
      "0"
    )}`;
    const label = `${d.getFullYear()}年${d.getMonth() + 1}月`;
    monthOptions.push({ value, label });
  }

  if (success) {
    return (
      <ThreePaneLayout>
        <div className="p-6 h-full flex items-center justify-center">
          <Card className="p-8 text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">登録完了</h2>
            <p className="text-gray-600">追加請求を登録しました</p>
            <p className="text-sm text-gray-500 mt-4">
              請求確定データ画面に戻ります...
            </p>
          </Card>
        </div>
      </ThreePaneLayout>
    );
  }

  return (
    <ThreePaneLayout>
      <div className="p-6 h-full flex flex-col">
        {/* ヘッダー */}
        <div className="mb-6 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push("/billing/confirmed")}
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              戻る
            </Button>
            <div>
              <h1 className="text-2xl font-bold">追加請求登録</h1>
              <p className="text-sm text-gray-600">
                生徒ごとに追加請求を登録します
              </p>
            </div>
          </div>
        </div>

        {/* タブ切り替え */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="mb-4">
            <TabsTrigger value="single">
              <Plus className="w-4 h-4 mr-1" />
              個別登録
            </TabsTrigger>
            <TabsTrigger value="import">
              <Upload className="w-4 h-4 mr-1" />
              一括インポート
            </TabsTrigger>
          </TabsList>

          {/* 個別登録タブ */}
          <TabsContent value="single" className="flex-1 overflow-hidden">
            <div className="grid grid-cols-2 gap-6 h-full overflow-hidden">
              {/* 左: 入力フォーム */}
              <Card className="p-6 overflow-auto">
                <h2 className="text-lg font-semibold mb-4">請求明細入力</h2>

                <div className="space-y-4">
                  {/* 生徒選択 */}
                  <div>
                    <Label>生徒 *</Label>
                    <div className="flex gap-2 mt-1">
                      <Input
                        value={
                          currentForm.student
                            ? `${currentForm.student.old_id} ${currentForm.student.full_name}`
                            : ""
                        }
                        placeholder="生徒を選択してください"
                        readOnly
                        className="flex-1"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setStudentSearchOpen(true)}
                      >
                        <Search className="w-4 h-4 mr-1" />
                        検索
                      </Button>
                    </div>
                    {currentForm.student?.guardian && (
                      <p className="text-sm text-gray-500 mt-1">
                        保護者: {currentForm.student.guardian.old_id}{" "}
                        {currentForm.student.guardian.full_name}
                      </p>
                    )}
                  </div>

                  {/* 請求月 */}
                  <div>
                    <Label>請求月 *</Label>
                    <Select
                      value={currentForm.billing_month}
                      onValueChange={(v) =>
                        setCurrentForm((prev) => ({ ...prev, billing_month: v }))
                      }
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {monthOptions.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* 商品選択 or 手入力 */}
                  <div>
                    <Label>商品（マスタから選択）</Label>
                    <Select
                      value={currentForm.product_id}
                      onValueChange={handleProductChange}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="商品を選択（任意）" />
                      </SelectTrigger>
                      <SelectContent>
                        {products.map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.product_name} ({p.base_price?.toLocaleString()}円)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>商品名（手入力）</Label>
                    <Input
                      value={currentForm.product_name}
                      onChange={(e) =>
                        setCurrentForm((prev) => ({
                          ...prev,
                          product_name: e.target.value,
                        }))
                      }
                      placeholder="例: メプレス2026年2月分授業料"
                      className="mt-1"
                    />
                  </div>

                  {/* ブランド */}
                  <div>
                    <Label>ブランド</Label>
                    <Select
                      value={currentForm.brand_id}
                      onValueChange={(v) =>
                        setCurrentForm((prev) => ({ ...prev, brand_id: v }))
                      }
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="ブランドを選択（任意）" />
                      </SelectTrigger>
                      <SelectContent>
                        {brands.map((b) => (
                          <SelectItem key={b.id} value={b.id}>
                            {b.brand_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* 金額 */}
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label>単価 *</Label>
                      <Input
                        type="number"
                        value={currentForm.unit_price}
                        onChange={(e) =>
                          setCurrentForm((prev) => ({
                            ...prev,
                            unit_price: parseInt(e.target.value) || 0,
                          }))
                        }
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label>数量</Label>
                      <Input
                        type="number"
                        value={currentForm.quantity}
                        onChange={(e) =>
                          setCurrentForm((prev) => ({
                            ...prev,
                            quantity: parseInt(e.target.value) || 1,
                          }))
                        }
                        min={1}
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label>割引額</Label>
                      <Input
                        type="number"
                        value={currentForm.discount_amount}
                        onChange={(e) =>
                          setCurrentForm((prev) => ({
                            ...prev,
                            discount_amount: parseInt(e.target.value) || 0,
                          }))
                        }
                        className="mt-1"
                      />
                    </div>
                  </div>

                  <div className="text-right text-lg font-semibold">
                    小計:{" "}
                    {(
                      currentForm.unit_price * currentForm.quantity -
                      currentForm.discount_amount
                    ).toLocaleString()}
                    円
                  </div>

                  {/* 備考 */}
                  <div>
                    <Label>備考</Label>
                    <Textarea
                      value={currentForm.notes}
                      onChange={(e) =>
                        setCurrentForm((prev) => ({
                          ...prev,
                          notes: e.target.value,
                        }))
                      }
                      placeholder="備考（任意）"
                      className="mt-1"
                      rows={2}
                    />
                  </div>

                  <Button onClick={addItemToList} className="w-full">
                    <Plus className="w-4 h-4 mr-1" />
                    リストに追加
                  </Button>
                </div>
              </Card>

              {/* 右: 追加リスト */}
              <Card className="p-6 flex flex-col overflow-hidden">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold">
                    追加リスト ({items.length}件)
                  </h2>
                  <div className="text-xl font-bold">
                    合計: {totalAmount.toLocaleString()}円
                  </div>
                </div>

                <div className="flex-1 overflow-auto">
                  {items.length === 0 ? (
                    <div className="text-center text-gray-500 py-12">
                      <p>追加する明細がありません</p>
                      <p className="text-sm mt-1">
                        左のフォームから明細を追加してください
                      </p>
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>生徒</TableHead>
                          <TableHead>請求月</TableHead>
                          <TableHead>内容</TableHead>
                          <TableHead className="text-right">金額</TableHead>
                          <TableHead className="w-10"></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {items.map((item, index) => (
                          <TableRow key={index}>
                            <TableCell>
                              <div className="text-sm">{item.student?.old_id}</div>
                              <div className="text-xs text-gray-500">
                                {item.student?.full_name}
                              </div>
                            </TableCell>
                            <TableCell>{item.billing_month}</TableCell>
                            <TableCell>
                              <div className="text-sm">
                                {item.product_name || "(商品名なし)"}
                              </div>
                              {item.notes && (
                                <div className="text-xs text-gray-500">
                                  {item.notes}
                                </div>
                              )}
                            </TableCell>
                            <TableCell className="text-right">
                              {(
                                item.unit_price * item.quantity -
                                item.discount_amount
                              ).toLocaleString()}
                              円
                            </TableCell>
                            <TableCell>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => removeItem(index)}
                              >
                                <Trash2 className="w-4 h-4 text-red-500" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>

                <div className="pt-4 border-t mt-4">
                  <Button
                    onClick={submitItems}
                    disabled={items.length === 0 || loading}
                    className="w-full bg-green-600 hover:bg-green-700"
                  >
                    {loading ? "登録中..." : `${items.length}件を登録する`}
                  </Button>
                </div>
              </Card>
            </div>
          </TabsContent>

          {/* 一括インポートタブ */}
          <TabsContent value="import" className="flex-1">
            <Card className="p-6 max-w-2xl mx-auto">
              <h2 className="text-lg font-semibold mb-4">
                <FileSpreadsheet className="w-5 h-5 inline mr-2" />
                CSV/Excelから一括インポート
              </h2>

              <div className="space-y-6">
                {/* フォーマット説明 */}
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h3 className="font-medium text-blue-800 mb-2">
                    CSVフォーマット
                  </h3>
                  <p className="text-sm text-blue-700 mb-2">
                    以下の列を含むCSVファイルを用意してください：
                  </p>
                  <ul className="text-sm text-blue-700 space-y-1">
                    <li>
                      <code className="bg-blue-100 px-1">student_old_id</code> -
                      生徒ID（必須）
                    </li>
                    <li>
                      <code className="bg-blue-100 px-1">billing_month</code> -
                      請求月 YYYY-MM形式（必須）
                    </li>
                    <li>
                      <code className="bg-blue-100 px-1">product_name</code> -
                      商品名
                    </li>
                    <li>
                      <code className="bg-blue-100 px-1">unit_price</code> -
                      単価（必須）
                    </li>
                    <li>
                      <code className="bg-blue-100 px-1">quantity</code> -
                      数量（省略可、デフォルト1）
                    </li>
                    <li>
                      <code className="bg-blue-100 px-1">discount_amount</code>{" "}
                      - 割引額（省略可）
                    </li>
                    <li>
                      <code className="bg-blue-100 px-1">brand_code</code> -
                      ブランドコード（省略可）
                    </li>
                    <li>
                      <code className="bg-blue-100 px-1">notes</code> -
                      備考（省略可）
                    </li>
                  </ul>
                  <Button
                    variant="link"
                    className="mt-2 p-0 h-auto text-blue-700"
                    onClick={downloadTemplate}
                  >
                    <Download className="w-4 h-4 mr-1" />
                    テンプレートをダウンロード
                  </Button>
                </div>

                {/* ファイル選択 */}
                <div>
                  <Label>CSVファイル選択</Label>
                  <Input
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={(e) => {
                      setImportFile(e.target.files?.[0] || null);
                      setImportResult(null);
                    }}
                    className="mt-1"
                  />
                </div>

                {/* インポート結果 */}
                {importResult && (
                  <div
                    className={`p-4 rounded-lg border ${
                      importResult.error_count === 0
                        ? "bg-green-50 border-green-200"
                        : "bg-yellow-50 border-yellow-200"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      {importResult.error_count === 0 ? (
                        <CheckCircle className="w-5 h-5 text-green-600" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-yellow-600" />
                      )}
                      <span className="font-medium">
                        {importResult.error_count === 0
                          ? "インポート完了"
                          : "インポート完了（一部エラーあり）"}
                      </span>
                    </div>
                    <p className="text-sm">
                      成功: {importResult.created_count}件 / エラー:{" "}
                      {importResult.error_count}件
                    </p>
                    {importResult.errors.length > 0 && (
                      <div className="mt-2">
                        <p className="text-sm font-medium text-red-600">
                          エラー詳細:
                        </p>
                        <ul className="text-sm text-red-600 mt-1 space-y-1 max-h-40 overflow-auto">
                          {importResult.errors.map((err, i) => (
                            <li key={i}>
                              行{err.row}: {err.error}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {importResult.error_count === 0 && (
                      <p className="text-sm text-green-600 mt-2">
                        請求確定データ画面に戻ります...
                      </p>
                    )}
                  </div>
                )}

                {/* インポートボタン */}
                <Button
                  onClick={handleImport}
                  disabled={!importFile || importing}
                  className="w-full"
                >
                  {importing ? (
                    "インポート中..."
                  ) : (
                    <>
                      <Upload className="w-4 h-4 mr-2" />
                      インポート実行
                    </>
                  )}
                </Button>
              </div>
            </Card>
          </TabsContent>
        </Tabs>

        {/* 生徒検索ダイアログ */}
        <Dialog open={studentSearchOpen} onOpenChange={setStudentSearchOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>生徒検索</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="flex gap-2">
                <Input
                  value={studentSearchQuery}
                  onChange={(e) => setStudentSearchQuery(e.target.value)}
                  placeholder="生徒ID、名前で検索..."
                  onKeyDown={(e) => e.key === "Enter" && searchStudents()}
                />
                <Button onClick={searchStudents} disabled={searchingStudents}>
                  <Search className="w-4 h-4 mr-1" />
                  検索
                </Button>
              </div>

              <div className="max-h-96 overflow-auto">
                {searchingStudents ? (
                  <div className="text-center py-8 text-gray-500">検索中...</div>
                ) : studentSearchResults.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    {studentSearchQuery
                      ? "該当する生徒が見つかりません"
                      : "生徒IDまたは名前で検索してください"}
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>生徒ID</TableHead>
                        <TableHead>生徒名</TableHead>
                        <TableHead>保護者</TableHead>
                        <TableHead>状態</TableHead>
                        <TableHead></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {studentSearchResults.map((student) => (
                        <TableRow key={student.id}>
                          <TableCell>{student.old_id}</TableCell>
                          <TableCell>{student.full_name}</TableCell>
                          <TableCell>
                            {student.guardian?.full_name || "-"}
                          </TableCell>
                          <TableCell>{student.status}</TableCell>
                          <TableCell>
                            <Button
                              size="sm"
                              onClick={() => selectStudent(student)}
                            >
                              選択
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </ThreePaneLayout>
  );
}
