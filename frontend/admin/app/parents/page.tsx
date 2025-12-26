"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { GuardianList } from "@/components/guardians/GuardianList";
import { GuardianDetail } from "@/components/guardians/GuardianDetail";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";
import {
  searchParents,
  getParentDetail,
  getGuardianContactLogs,
  getGuardianMessages,
  type ContactLog,
  type ChatMessage,
} from "@/lib/api/staff";
import apiClient from "@/lib/api/client";
import type { Guardian, Student, Invoice } from "@/lib/api/types";

// Billing summary type
interface BillingSummary {
  guardianId: string;
  guardianName: string;
  children: any[];
  guardianDiscounts: any[];
  fsDiscounts: any[];
  totalAmount: number;
  totalDiscount: number;
  netAmount: number;
}

// デバウンス用hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

export default function ParentsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [guardians, setGuardians] = useState<Guardian[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  // Selected guardian state
  const [selectedGuardianId, setSelectedGuardianId] = useState<string>();
  const [selectedGuardian, setSelectedGuardian] = useState<Guardian | null>(null);
  const [selectedGuardianChildren, setSelectedGuardianChildren] = useState<Student[]>([]);
  const [selectedGuardianInvoices, setSelectedGuardianInvoices] = useState<Invoice[]>([]);
  const [selectedGuardianContactLogs, setSelectedGuardianContactLogs] = useState<ContactLog[]>([]);
  const [selectedGuardianMessages, setSelectedGuardianMessages] = useState<ChatMessage[]>([]);
  const [billingSummary, setBillingSummary] = useState<BillingSummary | null>(null);

  // 検索クエリをデバウンス（300ms）
  const debouncedSearch = useDebounce(searchQuery, 300);

  useEffect(() => {
    // 認証チェック
    const token = apiClient.getToken();
    if (!token) {
      router.push("/login");
      return;
    }
  }, [router]);

  // URLパラメータから保護者を選択/検索
  useEffect(() => {
    const selectedId = searchParams.get('selected') || searchParams.get('id');
    const search = searchParams.get('search');

    if (selectedId) {
      setSelectedGuardianId(selectedId);
    }
    if (search) {
      setSearchQuery(search);
    }
  }, [searchParams]);

  const loadGuardians = useCallback(async (search?: string) => {
    setLoading(true);
    const { results, count } = await searchParents(search);
    setGuardians(results);
    setTotal(count);
    setLoading(false);
  }, []);

  useEffect(() => {
    const token = apiClient.getToken();
    if (!token) return;
    loadGuardians(debouncedSearch || undefined);
  }, [debouncedSearch, loadGuardians]);

  // Load guardian detail when selected
  useEffect(() => {
    if (selectedGuardianId) {
      loadGuardianDetail(selectedGuardianId);
    }
  }, [selectedGuardianId]);

  async function loadGuardianDetail(guardianId: string) {
    const guardian = await getParentDetail(guardianId);
    if (!guardian) return;

    setSelectedGuardian(guardian);

    // Get children, contact logs, messages, and billing summary in parallel
    const [children, contactLogs, messages, billing] = await Promise.all([
      // Children
      apiClient.get<any>(`/students/guardians/${guardianId}/students/`).then(res => {
        const data = res.data || res.results || res || [];
        return Array.isArray(data) ? data : [];
      }).catch(() => []),
      // Contact logs
      getGuardianContactLogs(guardianId),
      // Messages
      getGuardianMessages(guardianId),
      // Billing summary (new API)
      apiClient.get<BillingSummary>(`/students/guardians/${guardianId}/billing_summary/`).catch(() => null),
    ]);

    setSelectedGuardianChildren(children);
    setSelectedGuardianContactLogs(contactLogs);
    setSelectedGuardianMessages(messages);
    setBillingSummary(billing);

    // Get invoices from billing API
    try {
      const response = await apiClient.get<any>("/billing/invoices/", {
        guardian_id: guardianId,
        page_size: 20,
      });
      const invoices = response.data || response.results || [];
      setSelectedGuardianInvoices(invoices);
    } catch {
      setSelectedGuardianInvoices([]);
    }
  }

  function handleSelectGuardian(guardianId: string) {
    setSelectedGuardianId(guardianId);
  }

  function handleCloseDetail() {
    setSelectedGuardianId(undefined);
    setSelectedGuardian(null);
    setSelectedGuardianChildren([]);
    setSelectedGuardianInvoices([]);
    setSelectedGuardianContactLogs([]);
    setSelectedGuardianMessages([]);
    setBillingSummary(null);
  }

  function handleSelectChild(studentId: string) {
    // Navigate to the student page to view
    router.push(`/students?id=${studentId}`);
  }

  function handleEditChild(studentId: string) {
    // Navigate to the student page with edit mode
    router.push(`/students?id=${studentId}&edit=true`);
  }

  return (
    <ThreePaneLayout
      isRightPanelOpen={!!selectedGuardianId}
      onCloseRightPanel={handleCloseDetail}
      rightPanel={
        selectedGuardian ? (
          <GuardianDetail
            guardian={selectedGuardian}
            children={selectedGuardianChildren}
            invoices={selectedGuardianInvoices}
            contactLogs={selectedGuardianContactLogs}
            messages={selectedGuardianMessages}
            billingSummary={billingSummary}
            onSelectChild={handleSelectChild}
            onEditChild={handleEditChild}
          />
        ) : (
          <div className="p-6 text-center text-gray-500">読み込み中...</div>
        )
      }
    >
      <div className="p-6 h-full flex flex-col">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">保護者一覧</h1>
          <p className="text-gray-600">
            {total.toLocaleString()}名の保護者が登録されています
            {searchQuery && ` （検索結果: ${guardians.length}件）`}
          </p>
        </div>

        <div className="mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <Input
              type="text"
              placeholder="保護者名、お子様名、メール、電話番号で検索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="text-center text-gray-500 py-8">読み込み中...</div>
          ) : (
            <GuardianList
              guardians={guardians}
              selectedGuardianId={selectedGuardianId}
              onSelectGuardian={handleSelectGuardian}
            />
          )}
        </div>
      </div>
    </ThreePaneLayout>
  );
}
