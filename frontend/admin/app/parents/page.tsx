"use client";

import { useEffect, useState, useCallback } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Search, Mail, Phone, User } from "lucide-react";
import { searchParents, Parent } from "@/lib/api/staff";

// Helper to get guardian display name
function getGuardianName(guardian: Parent): string {
  return guardian.name || guardian.full_name || `${guardian.last_name || ""}${guardian.first_name || ""}`;
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
  const [parents, setParents] = useState<Parent[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  // 検索クエリをデバウンス（300ms）
  const debouncedSearch = useDebounce(searchQuery, 300);

  const loadParents = useCallback(async (search?: string) => {
    setLoading(true);
    const { results, count } = await searchParents(search);
    setParents(results);
    setTotal(count);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadParents(debouncedSearch || undefined);
  }, [debouncedSearch, loadParents]);

  return (
    <ThreePaneLayout>
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">保護者一覧</h1>
          <p className="text-gray-600">
            {total}名の保護者が登録されています
            {searchQuery && ` （検索結果: ${parents.length}件）`}
          </p>
        </div>

        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <Input
              type="text"
              placeholder="保護者名、メール、電話番号で検索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {loading ? (
          <div className="text-center text-gray-500 py-8">読み込み中...</div>
        ) : parents.length > 0 ? (
          <div className="space-y-2">
            {parents.map((parent) => (
              <Card key={parent.id} className="p-4 hover:shadow-md transition-all">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-gray-100 rounded-lg">
                    <User className="w-6 h-6 text-gray-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1">
                      {getGuardianName(parent)}
                    </h3>
                    {parent.relationship && (
                      <p className="text-sm text-gray-600 mb-2">
                        {parent.relationship}
                      </p>
                    )}
                    <div className="space-y-1">
                      {parent.email && (
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                          <Mail className="w-4 h-4" />
                          {parent.email}
                        </div>
                      )}
                      {(parent.phone || parent.phone_mobile) && (
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                          <Phone className="w-4 h-4" />
                          {parent.phone || parent.phone_mobile}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center text-gray-500 py-8">
            保護者が見つかりませんでした
          </div>
        )}
      </div>
    </ThreePaneLayout>
  );
}
