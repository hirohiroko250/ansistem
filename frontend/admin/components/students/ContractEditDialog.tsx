"use client";

import { useState, useEffect } from "react";
import { Contract, StudentDiscount, StudentItem } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
import { Plus, Trash2, Save, X, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

interface ContractEditDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  contract: Contract | null;
  onSave: (contractId: string, updates: ContractUpdate) => Promise<void>;
}

interface ContractUpdate {
  item_discounts?: ItemDiscountInput[];
  notes?: string;
}

interface ItemDiscountInput {
  student_item_id?: string;
  product_name?: string;
  discount_name: string;
  amount: number;
  discount_unit: "yen" | "percent";
  is_new?: boolean;
  is_deleted?: boolean;
  id?: string;
}

interface ItemWithDiscounts {
  id: string;
  product_name: string;
  unit_price: number;
  quantity: number;
  final_price: number;
  discounts: ItemDiscountInput[];
  showAddForm: boolean;
}

export function ContractEditDialog({
  open,
  onOpenChange,
  contract,
  onSave,
}: ContractEditDialogProps) {
  const [items, setItems] = useState<ItemWithDiscounts[]>([]);
  const [notes, setNotes] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // Initialize from contract data
  useEffect(() => {
    if (contract) {
      const studentItems = contract.student_items || contract.studentItems || [];
      const existingDiscounts = contract.discounts || [];

      // Track which discounts have been assigned to avoid duplicates
      const assignedDiscountIds = new Set<string>();

      const itemsWithDiscounts: ItemWithDiscounts[] = studentItems.map((item: StudentItem) => {
        // Find discounts for this specific item only
        const itemDiscounts = existingDiscounts
          .filter((d: StudentDiscount) => {
            // Skip if already assigned
            if (d.id && assignedDiscountIds.has(d.id)) return false;

            // Get the student_item ID from various possible field names
            // API returns student_item as ID (camelCase: studentItem)
            const discountItemId = d.student_item_id
              || (d as any).studentItemId
              || d.student_item
              || (d as any).studentItem;

            // Check if this discount belongs to this item
            // discountItemId can be the ID directly, or an object with .id
            const matchingId = typeof discountItemId === 'object' && discountItemId !== null
              ? discountItemId.id
              : discountItemId;

            if (matchingId === item.id) {
              if (d.id) assignedDiscountIds.add(d.id);
              return true;
            }

            return false;
          })
          .map((d: StudentDiscount) => ({
            id: d.id,
            student_item_id: item.id,
            product_name: item.product_name || item.productName || "",
            discount_name: d.discount_name || d.discountName || "",
            amount: Math.abs(Number(d.amount) || 0),
            discount_unit: (d.discount_unit || d.discountUnit || "yen") as "yen" | "percent",
          }));

        return {
          id: item.id,
          product_name: item.product_name || item.productName || "商品",
          unit_price: Number(item.unit_price || item.unitPrice || 0),
          quantity: item.quantity || 1,
          final_price: Number(item.final_price || item.finalPrice || 0),
          discounts: itemDiscounts,
          showAddForm: false,
        };
      });

      // Handle unassigned discounts (contract-level discounts without student_item)
      // Try to match them to items by name, or assign to appropriate item
      const unassignedDiscounts = existingDiscounts.filter((d: StudentDiscount) => {
        if (d.id && assignedDiscountIds.has(d.id)) return false;
        return true;
      });

      for (const discount of unassignedDiscounts) {
        const discountName = (discount.discount_name || (discount as any).discountName || "").toLowerCase();

        // Try to find matching item by checking if discount name contains product keywords
        let targetItemIndex = -1;

        // Look for item whose product name appears in the discount name
        for (let i = 0; i < itemsWithDiscounts.length; i++) {
          const productName = itemsWithDiscounts[i].product_name.toLowerCase();
          // Check if product name keywords are in discount name
          // e.g., "入会金" in "アンそろばんクラブ【入会金_半額】友人紹介のため"
          if (productName && discountName.includes(productName)) {
            targetItemIndex = i;
            break;
          }
          // Also check common keywords
          if (productName.includes("入会金") && discountName.includes("入会金")) {
            targetItemIndex = i;
            break;
          }
        }

        // If no match by name, assign to first item with price > 0 as fallback
        if (targetItemIndex === -1 && itemsWithDiscounts.length > 0) {
          targetItemIndex = itemsWithDiscounts.findIndex(item => item.unit_price > 0) || 0;
        }

        if (targetItemIndex >= 0) {
          const targetItem = itemsWithDiscounts[targetItemIndex];
          targetItem.discounts.push({
            id: discount.id,
            student_item_id: targetItem.id,
            product_name: targetItem.product_name,
            discount_name: discount.discount_name || (discount as any).discountName || "",
            amount: Math.abs(Number(discount.amount) || 0),
            discount_unit: ((discount.discount_unit || (discount as any).discountUnit || "yen") as "yen" | "percent"),
          });
          if (discount.id) assignedDiscountIds.add(discount.id);
        }
      }

      // If no items exist, create a default "monthly fee" item
      if (itemsWithDiscounts.length === 0) {
        const monthlyTotal = contract.monthly_total || contract.monthlyTotal || 0;
        itemsWithDiscounts.push({
          id: "default",
          product_name: "月額料金",
          unit_price: Number(monthlyTotal),
          quantity: 1,
          final_price: Number(monthlyTotal),
          discounts: existingDiscounts.map((d: StudentDiscount) => ({
            id: d.id,
            student_item_id: "default",
            product_name: "月額料金",
            discount_name: d.discount_name || d.discountName || "",
            amount: Math.abs(Number(d.amount) || 0),
            discount_unit: (d.discount_unit || d.discountUnit || "yen") as "yen" | "percent",
          })),
          showAddForm: false,
        });
      }

      setItems(itemsWithDiscounts);
      setNotes(contract.notes || "");
      // Expand all items by default
      setExpandedItems(new Set(itemsWithDiscounts.map(i => i.id)));
    }
  }, [contract]);

  if (!contract) return null;

  const contractNo = contract.contract_no || contract.contractNo || "";
  const courseName = contract.course_name || contract.courseName || "";
  const brandName = contract.brand_name || contract.brandName || "";
  const schoolName = contract.school_name || contract.schoolName || "";
  const discountMax = Number(contract.discount_max || contract.discountMax || 0);

  const toggleItemExpanded = (itemId: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(itemId)) {
      newExpanded.delete(itemId);
    } else {
      newExpanded.add(itemId);
    }
    setExpandedItems(newExpanded);
  };

  const handleAddDiscount = (itemIndex: number, discount: { name: string; amount: number; unit: "yen" | "percent" }) => {
    if (!discount.name || discount.amount <= 0) return;

    const newItems = [...items];
    newItems[itemIndex].discounts.push({
      id: `new-${Date.now()}`,
      student_item_id: newItems[itemIndex].id,
      product_name: newItems[itemIndex].product_name,
      discount_name: discount.name,
      amount: discount.amount,
      discount_unit: discount.unit,
      is_new: true,
    });
    newItems[itemIndex].showAddForm = false;
    setItems(newItems);
  };

  const handleRemoveDiscount = (itemIndex: number, discountIndex: number) => {
    const newItems = [...items];
    const discount = newItems[itemIndex].discounts[discountIndex];
    if (discount.id && !discount.is_new) {
      discount.is_deleted = true;
    } else {
      newItems[itemIndex].discounts.splice(discountIndex, 1);
    }
    setItems(newItems);
  };

  const toggleAddForm = (itemIndex: number) => {
    const newItems = [...items];
    newItems[itemIndex].showAddForm = !newItems[itemIndex].showAddForm;
    setItems(newItems);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Collect all discounts from all items
      const allDiscounts: ItemDiscountInput[] = items.flatMap(item =>
        item.discounts.map(d => ({
          ...d,
          student_item_id: item.id !== "default" ? item.id : undefined,
        }))
      );

      await onSave(contract.id, {
        item_discounts: allDiscounts,
        notes: notes,
      });
      onOpenChange(false);
    } catch (error) {
      console.error("Failed to save contract:", error);
    } finally {
      setIsSaving(false);
    }
  };

  // Calculate totals per item and overall
  const calculateItemTotal = (item: ItemWithDiscounts) => {
    const activeDiscounts = item.discounts.filter(d => !d.is_deleted);
    const discountTotal = activeDiscounts.reduce((sum, d) => {
      if (d.discount_unit === "percent") {
        return sum + (item.unit_price * item.quantity * d.amount) / 100;
      }
      return sum + d.amount;
    }, 0);
    return {
      basePrice: item.unit_price * item.quantity,
      discountTotal,
      finalPrice: item.unit_price * item.quantity - discountTotal,
    };
  };

  const overallTotals = items.reduce(
    (acc, item) => {
      const itemCalc = calculateItemTotal(item);
      return {
        baseTotal: acc.baseTotal + itemCalc.basePrice,
        discountTotal: acc.discountTotal + itemCalc.discountTotal,
        finalTotal: acc.finalTotal + itemCalc.finalPrice,
      };
    },
    { baseTotal: 0, discountTotal: 0, finalTotal: 0 }
  );

  const excessAmount = discountMax > 0 ? Math.max(0, overallTotals.discountTotal - discountMax) : 0;
  const hasExcess = excessAmount > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>契約編集</DialogTitle>
          <DialogDescription>
            契約番号: {contractNo}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Contract Info (Read-only) */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-semibold text-sm mb-3">契約情報</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">コース:</span>
                <span className="ml-2 font-medium">{courseName || "-"}</span>
              </div>
              <div>
                <span className="text-gray-500">ブランド:</span>
                <span className="ml-2 font-medium">{brandName || "-"}</span>
              </div>
              <div>
                <span className="text-gray-500">校舎:</span>
                <span className="ml-2 font-medium">{schoolName || "-"}</span>
              </div>
              {discountMax > 0 && (
                <div>
                  <span className="text-gray-500">割引Max:</span>
                  <span className="ml-2 font-medium">¥{discountMax.toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>

          {/* Items with Discounts */}
          <div>
            <h3 className="font-semibold text-sm mb-3">明細・割引</h3>
            <div className="space-y-3">
              {items.map((item, itemIndex) => {
                const itemCalc = calculateItemTotal(item);
                const isExpanded = expandedItems.has(item.id);
                const activeDiscounts = item.discounts.filter(d => !d.is_deleted);

                return (
                  <div
                    key={item.id}
                    className="border rounded-lg overflow-hidden"
                  >
                    {/* Item Header */}
                    <div
                      className="flex items-center justify-between p-3 bg-gray-50 cursor-pointer hover:bg-gray-100"
                      onClick={() => toggleItemExpanded(item.id)}
                    >
                      <div className="flex items-center gap-2">
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-gray-500" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-gray-500" />
                        )}
                        <span className="font-medium">{item.product_name}</span>
                        {activeDiscounts.length > 0 && (
                          <Badge variant="secondary" className="text-xs">
                            割引{activeDiscounts.length}件
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-gray-500">
                          ¥{itemCalc.basePrice.toLocaleString()}
                        </span>
                        {itemCalc.discountTotal > 0 && (
                          <span className="text-orange-600">
                            -¥{itemCalc.discountTotal.toLocaleString()}
                          </span>
                        )}
                        <span className="font-medium text-blue-600">
                          ¥{itemCalc.finalPrice.toLocaleString()}
                        </span>
                      </div>
                    </div>

                    {/* Item Details (expanded) */}
                    {isExpanded && (
                      <div className="p-3 space-y-3 border-t">
                        {/* Item price details */}
                        <div className="text-sm text-gray-600 flex gap-4">
                          <span>単価: ¥{item.unit_price.toLocaleString()}</span>
                          <span>数量: {item.quantity}</span>
                        </div>

                        {/* Discounts for this item */}
                        <div className="space-y-2">
                          {activeDiscounts.length === 0 && !item.showAddForm && (
                            <p className="text-sm text-gray-400">割引なし</p>
                          )}

                          {activeDiscounts.map((discount, discountIndex) => (
                            <div
                              key={discount.id || discountIndex}
                              className="flex items-center gap-2 p-2 bg-orange-50 border border-orange-200 rounded"
                            >
                              <div className="flex-1">
                                <span className="font-medium text-sm">{discount.discount_name}</span>
                                {discount.is_new && (
                                  <Badge className="ml-2 text-xs bg-green-100 text-green-700">新規</Badge>
                                )}
                              </div>
                              <div className="text-orange-600 font-medium text-sm">
                                {discount.discount_unit === "percent"
                                  ? `-${discount.amount}%`
                                  : `-¥${discount.amount.toLocaleString()}`}
                              </div>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-6 w-6 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRemoveDiscount(itemIndex, item.discounts.indexOf(discount));
                                }}
                              >
                                <Trash2 className="w-3 h-3" />
                              </Button>
                            </div>
                          ))}

                          {/* Add Discount Form */}
                          {item.showAddForm && (
                            <AddDiscountForm
                              onAdd={(discount) => handleAddDiscount(itemIndex, discount)}
                              onCancel={() => toggleAddForm(itemIndex)}
                            />
                          )}
                        </div>

                        {/* Add Discount Button */}
                        {!item.showAddForm && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleAddForm(itemIndex);
                            }}
                            className="h-7"
                          >
                            <Plus className="w-3 h-3 mr-1" />
                            割引追加
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Totals */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-500">小計:</span>
              <span>¥{overallTotals.baseTotal.toLocaleString()}</span>
            </div>
            {overallTotals.discountTotal > 0 && (
              <div className={`flex justify-between text-sm mb-2 ${hasExcess ? 'text-red-600' : 'text-orange-600'}`}>
                <span>割引合計:</span>
                <span>-¥{overallTotals.discountTotal.toLocaleString()}</span>
              </div>
            )}
            {hasExcess && (
              <div className="flex items-center justify-between text-sm mb-2 p-2 bg-red-50 border border-red-200 rounded text-red-600">
                <div className="flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="font-medium">校舎負担分:</span>
                </div>
                <span className="font-bold">¥{excessAmount.toLocaleString()}</span>
              </div>
            )}
            <div className="flex justify-between font-bold border-t pt-2">
              <span>請求額:</span>
              <span className="text-blue-600">¥{overallTotals.finalTotal.toLocaleString()}</span>
            </div>
          </div>

          {/* Excess Warning */}
          {hasExcess && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5" />
                <div className="text-sm text-red-700">
                  <p className="font-medium">割引Maxを超過しています</p>
                  <p className="mt-1">
                    割引Max（¥{discountMax.toLocaleString()}）を超えた
                    <span className="font-bold">¥{excessAmount.toLocaleString()}</span>
                    は校舎（{schoolName}）の負担となります。
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Notes */}
          <div>
            <h3 className="font-semibold text-sm mb-2">備考</h3>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full h-20 p-2 border rounded text-sm resize-none"
              placeholder="契約に関する備考..."
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            キャンセル
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            <Save className="w-4 h-4 mr-1" />
            {isSaving ? "保存中..." : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Separate component for add discount form
function AddDiscountForm({
  onAdd,
  onCancel,
}: {
  onAdd: (discount: { name: string; amount: number; unit: "yen" | "percent" }) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [amount, setAmount] = useState<number>(0);
  const [unit, setUnit] = useState<"yen" | "percent">("yen");

  return (
    <div className="p-3 bg-blue-50 border border-blue-200 rounded space-y-3">
      <div className="flex items-center gap-2">
        <Input
          placeholder="割引名（例：社割_正社員、マイル割引）"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 h-8 text-sm"
          onClick={(e) => e.stopPropagation()}
        />
      </div>
      <div className="flex items-center gap-2">
        <Input
          type="number"
          placeholder="金額"
          value={amount || ""}
          onChange={(e) => setAmount(Number(e.target.value))}
          className="w-32 h-8 text-sm"
          onClick={(e) => e.stopPropagation()}
        />
        <Select
          value={unit}
          onValueChange={(value: "yen" | "percent") => setUnit(value)}
        >
          <SelectTrigger className="w-20 h-8" onClick={(e) => e.stopPropagation()}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="yen">円</SelectItem>
            <SelectItem value="percent">%</SelectItem>
          </SelectContent>
        </Select>
        <Button
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onAdd({ name, amount, unit });
          }}
          disabled={!name || amount <= 0}
          className="h-8"
        >
          追加
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={(e) => {
            e.stopPropagation();
            onCancel();
          }}
          className="h-8"
        >
          <X className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
