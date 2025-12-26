"use client";

import { useState, useEffect } from "react";
import { Student, Guardian, Course, Brand, School } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import apiClient from "@/lib/api/client";

interface NewContractDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  student: Student;
  guardian?: Guardian | null;
  onSuccess?: () => void;
}

interface TextbookOption {
  productId: string;
  productCode: string;
  productName: string;
  itemType: string;
  unitPrice: number;
  priceWithTax: number;
  taxRate: number;
  paymentType: "monthly" | "semi_annual" | "annual";
  billingMonths: number[];
  source: string;
}

interface PricingPreviewResponse {
  items: any[];
  subtotal: number;
  grandTotal: number;
  discounts: any[];
  discountTotal: number;
  billingByMonth: {
    enrollment: { label: string; items: any[]; total: number };
    currentMonth: { label: string; items: any[]; total: number };
    month1: { label: string; items: any[]; total: number };
    month2: { label: string; items: any[]; total: number };
  };
  textbookOptions: TextbookOption[];
  enrollmentFeesCalculated: any[];
  courseItems: any[];
}

const DAY_OF_WEEK_OPTIONS = [
  { value: "1", label: "月曜日" },
  { value: "2", label: "火曜日" },
  { value: "3", label: "水曜日" },
  { value: "4", label: "木曜日" },
  { value: "5", label: "金曜日" },
  { value: "6", label: "土曜日" },
  { value: "7", label: "日曜日" },
];

export function NewContractDialog({
  open,
  onOpenChange,
  student,
  guardian,
  onSuccess,
}: NewContractDialogProps) {
  // Form state
  const [courses, setCourses] = useState<Course[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>("");
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [dayOfWeek, setDayOfWeek] = useState<string>("");

  // Textbook selection
  const [selectedTextbookIds, setSelectedTextbookIds] = useState<string[]>([]);

  // Preview state
  const [preview, setPreview] = useState<PricingPreviewResponse | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Submit state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  // Load initial data
  useEffect(() => {
    if (open) {
      loadCourses();
      loadBrands();
      loadSchools();
      // Reset form
      setSelectedCourseId("");
      setSelectedBrandId("");
      setSelectedSchoolId("");
      setStartDate("");
      setDayOfWeek("");
      setSelectedTextbookIds([]);
      setPreview(null);
      setPreviewError(null);
      setSubmitError(null);
      setSubmitSuccess(false);
    }
  }, [open]);

  // Load preview when form changes
  useEffect(() => {
    if (selectedCourseId && startDate && dayOfWeek) {
      loadPreview();
    }
  }, [selectedCourseId, startDate, dayOfWeek]);

  const loadCourses = async () => {
    try {
      const data = await apiClient.get<{ results: Course[] }>("/contracts/courses/", {
        is_active: true,
        page_size: 100,
      });
      setCourses(data.results || []);
    } catch (error) {
      console.error("Failed to load courses:", error);
    }
  };

  const loadBrands = async () => {
    try {
      const data = await apiClient.get<{ results: Brand[] }>("/schools/brands/", {
        is_active: true,
      });
      setBrands(data.results || []);
    } catch (error) {
      console.error("Failed to load brands:", error);
    }
  };

  const loadSchools = async () => {
    try {
      const data = await apiClient.get<{ results: School[] }>("/schools/schools/", {
        is_active: true,
      });
      setSchools(data.results || []);
    } catch (error) {
      console.error("Failed to load schools:", error);
    }
  };

  const loadPreview = async () => {
    if (!selectedCourseId || !startDate || !dayOfWeek) return;

    setIsLoadingPreview(true);
    setPreviewError(null);

    try {
      const response = await apiClient.post<PricingPreviewResponse>("/pricing/preview/", {
        student_id: student.id,
        course_id: selectedCourseId,
        start_date: startDate,
        day_of_week: parseInt(dayOfWeek),
      });
      setPreview(response);
      // Reset textbook selection when preview changes
      setSelectedTextbookIds([]);
    } catch (error: any) {
      console.error("Failed to load preview:", error);
      setPreviewError(error.message || "料金プレビューの取得に失敗しました");
    } finally {
      setIsLoadingPreview(false);
    }
  };

  const handleTextbookToggle = (productId: string) => {
    setSelectedTextbookIds((prev) => {
      if (prev.includes(productId)) {
        return prev.filter((id) => id !== productId);
      } else {
        return [...prev, productId];
      }
    });
  };

  const handleSubmit = async () => {
    if (!selectedCourseId || !startDate) {
      setSubmitError("コースと開始日を選択してください");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await apiClient.post("/pricing/confirm/", {
        student_id: student.id,
        course_id: selectedCourseId,
        brand_id: selectedBrandId || undefined,
        school_id: selectedSchoolId || undefined,
        start_date: startDate,
        schedules: dayOfWeek ? [{ day_of_week: parseInt(dayOfWeek) }] : [],
        selected_textbook_ids: selectedTextbookIds,
      });

      setSubmitSuccess(true);
      setTimeout(() => {
        onOpenChange(false);
        onSuccess?.();
      }, 1500);
    } catch (error: any) {
      console.error("Failed to create contract:", error);
      setSubmitError(error.message || "契約の作成に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Filter courses by selected brand
  const filteredCourses = selectedBrandId
    ? courses.filter((c) => c.brand_id === selectedBrandId)
    : courses;

  // Filter schools by selected brand
  const filteredSchools = selectedBrandId
    ? schools.filter((s) => s.brand_id === selectedBrandId)
    : schools;

  // Get selected course
  const selectedCourse = courses.find((c) => c.id === selectedCourseId);

  // Calculate textbook total
  const textbookTotal = selectedTextbookIds.reduce((total, id) => {
    const textbook = preview?.textbookOptions.find((t) => t.productId === id);
    return total + (textbook?.priceWithTax || 0);
  }, 0);

  // Calculate grand total (monthly + textbook)
  const monthlyTotal = preview?.billingByMonth?.month1?.total || 0;
  const enrollmentTotal = preview?.billingByMonth?.enrollment?.total || 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>新規契約登録</DialogTitle>
          <DialogDescription>
            {student.last_name}{student.first_name} さんの新規契約を登録します
          </DialogDescription>
        </DialogHeader>

        {submitSuccess ? (
          <div className="flex flex-col items-center justify-center py-8">
            <CheckCircle2 className="w-16 h-16 text-green-500 mb-4" />
            <p className="text-lg font-medium">契約が正常に作成されました</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Brand Selection First */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>ブランド *</Label>
                <Select value={selectedBrandId} onValueChange={(v) => {
                  setSelectedBrandId(v);
                  setSelectedCourseId(""); // Reset course when brand changes
                  setSelectedSchoolId(""); // Reset school when brand changes
                }}>
                  <SelectTrigger>
                    <SelectValue placeholder="ブランドを選択" />
                  </SelectTrigger>
                  <SelectContent>
                    {brands.map((brand) => (
                      <SelectItem key={brand.id} value={brand.id}>
                        {brand.brand_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>コース *</Label>
                <Select
                  value={selectedCourseId}
                  onValueChange={setSelectedCourseId}
                  disabled={!selectedBrandId}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={selectedBrandId ? "コースを選択" : "先にブランドを選択"} />
                  </SelectTrigger>
                  <SelectContent>
                    {filteredCourses.map((course) => (
                      <SelectItem key={course.id} value={course.id}>
                        {course.course_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedBrandId && filteredCourses.length === 0 && (
                  <p className="text-xs text-orange-500 mt-1">このブランドにコースがありません</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>校舎</Label>
                <Select value={selectedSchoolId} onValueChange={setSelectedSchoolId}>
                  <SelectTrigger>
                    <SelectValue placeholder="校舎を選択" />
                  </SelectTrigger>
                  <SelectContent>
                    {filteredSchools.map((school) => (
                      <SelectItem key={school.id} value={school.id}>
                        {school.school_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>開始日 *</Label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>

              <div>
                <Label>曜日 *</Label>
                <Select value={dayOfWeek} onValueChange={setDayOfWeek}>
                  <SelectTrigger>
                    <SelectValue placeholder="曜日を選択" />
                  </SelectTrigger>
                  <SelectContent>
                    {DAY_OF_WEEK_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Preview Loading */}
            {isLoadingPreview && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin mr-2" />
                <span>料金を計算中...</span>
              </div>
            )}

            {/* Preview Error */}
            {previewError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center gap-2 text-red-600">
                  <AlertCircle className="w-5 h-5" />
                  <span>{previewError}</span>
                </div>
              </div>
            )}

            {/* Pricing Preview */}
            {preview && !isLoadingPreview && (
              <div className="space-y-4">
                {/* Monthly Items */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold mb-3">月額料金</h3>
                  <div className="space-y-2">
                    {preview.billingByMonth.month1.items.map((item, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span>{item.productName}</span>
                        <span>¥{item.priceWithTax?.toLocaleString()}</span>
                      </div>
                    ))}
                    <div className="flex justify-between font-medium border-t pt-2">
                      <span>月額合計</span>
                      <span>¥{monthlyTotal.toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                {/* Enrollment Fees */}
                {preview.billingByMonth.enrollment.items.length > 0 && (
                  <div className="bg-blue-50 rounded-lg p-4">
                    <h3 className="font-semibold mb-3">入会時費用</h3>
                    <div className="space-y-2">
                      {preview.billingByMonth.enrollment.items.map((item, idx) => (
                        <div key={idx} className="flex justify-between text-sm">
                          <span>{item.productName}</span>
                          <span>¥{item.priceWithTax?.toLocaleString()}</span>
                        </div>
                      ))}
                      <div className="flex justify-between font-medium border-t pt-2">
                        <span>入会時費用合計</span>
                        <span>¥{enrollmentTotal.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Textbook Selection */}
                {preview.textbookOptions && preview.textbookOptions.length > 0 && (
                  <div className="bg-yellow-50 rounded-lg p-4">
                    <h3 className="font-semibold mb-3">教材費の選択</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      教材費の支払い方法を選択してください。選択しない場合は教材費なしとなります。
                    </p>
                    <div className="space-y-3">
                      {preview.textbookOptions.map((textbook) => (
                        <div
                          key={textbook.productId}
                          className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                            selectedTextbookIds.includes(textbook.productId)
                              ? "bg-yellow-100 border-yellow-400"
                              : "bg-white border-gray-200 hover:bg-gray-50"
                          }`}
                          onClick={() => handleTextbookToggle(textbook.productId)}
                        >
                          <Checkbox
                            checked={selectedTextbookIds.includes(textbook.productId)}
                            onCheckedChange={() => handleTextbookToggle(textbook.productId)}
                          />
                          <div className="flex-1">
                            <div className="font-medium">{textbook.productName}</div>
                            <div className="text-sm text-gray-500">
                              {textbook.paymentType === "monthly" && "毎月払い"}
                              {textbook.paymentType === "semi_annual" && `半年払い（${textbook.billingMonths.join("月・")}月）`}
                              {textbook.paymentType === "annual" && "年払い"}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium">¥{textbook.priceWithTax.toLocaleString()}</div>
                            <div className="text-xs text-gray-500">税込</div>
                          </div>
                        </div>
                      ))}
                    </div>
                    {selectedTextbookIds.length > 0 && (
                      <div className="flex justify-between font-medium mt-3 pt-3 border-t">
                        <span>選択した教材費</span>
                        <span>¥{textbookTotal.toLocaleString()}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Total Summary */}
                <div className="bg-gray-100 rounded-lg p-4">
                  <h3 className="font-semibold mb-3">合計</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>月額料金</span>
                      <span>¥{monthlyTotal.toLocaleString()}</span>
                    </div>
                    {enrollmentTotal > 0 && (
                      <div className="flex justify-between text-sm">
                        <span>入会時費用</span>
                        <span>¥{enrollmentTotal.toLocaleString()}</span>
                      </div>
                    )}
                    {textbookTotal > 0 && (
                      <div className="flex justify-between text-sm">
                        <span>教材費</span>
                        <span>¥{textbookTotal.toLocaleString()}</span>
                      </div>
                    )}
                    <div className="flex justify-between font-bold text-lg border-t pt-2">
                      <span>初回請求額</span>
                      <span className="text-blue-600">
                        ¥{(monthlyTotal + enrollmentTotal + textbookTotal).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Submit Error */}
            {submitError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center gap-2 text-red-600">
                  <AlertCircle className="w-5 h-5" />
                  <span>{submitError}</span>
                </div>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            キャンセル
          </Button>
          {!submitSuccess && (
            <Button
              onClick={handleSubmit}
              disabled={!selectedBrandId || !selectedCourseId || !startDate || !dayOfWeek || isSubmitting || isLoadingPreview}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  登録中...
                </>
              ) : (
                "契約を登録"
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
