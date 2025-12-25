"use client";

import { useEffect, useState } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { apiClient } from "@/lib/api/client";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Search,
  Plus,
  Pin,
  Eye,
  Pencil,
  Trash2,
  X,
  BookOpen,
  Tag,
  Clock,
  User
} from "lucide-react";

interface ManualCategory {
  id: number;
  name: string;
  description: string;
  sortOrder: number;
  isActive: boolean;
}

interface Manual {
  id: number;
  title: string;
  summary: string;
  content: string;
  category: ManualCategory | null;
  categoryId: number | null;
  author: { id: number; fullName: string } | null;
  tags: string[];
  isPinned: boolean;
  isPublished: boolean;
  viewCount: number;
  createdAt: string;
  updatedAt: string;
}

export default function ManualsPage() {
  const [manuals, setManuals] = useState<Manual[]>([]);
  const [categories, setCategories] = useState<ManualCategory[]>([]);
  const [selectedManual, setSelectedManual] = useState<Manual | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [isEditing, setIsEditing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [editForm, setEditForm] = useState({
    title: "",
    summary: "",
    content: "",
    categoryId: "",
    tags: "",
    isPinned: false,
    isPublished: true,
  });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadManuals();
  }, [searchQuery, selectedCategory]);

  async function loadData() {
    setLoading(true);
    await Promise.all([loadManuals(), loadCategories()]);
    setLoading(false);
  }

  async function loadManuals() {
    try {
      const params: Record<string, string> = {};
      if (searchQuery) params.search = searchQuery;
      if (selectedCategory) params.category = selectedCategory;

      const response = await apiClient.get<any>("/knowledge/manuals/", params);
      const data = response.results || response.data || response || [];
      setManuals(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load manuals:", error);
      setManuals([]);
    }
  }

  async function loadCategories() {
    try {
      const response = await apiClient.get<any>("/knowledge/manual-categories/");
      const data = response.results || response.data || response || [];
      setCategories(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load categories:", error);
      setCategories([]);
    }
  }

  async function handleSelectManual(manual: Manual) {
    try {
      const detail = await apiClient.get<Manual>(`/knowledge/manuals/${manual.id}/`);
      setSelectedManual(detail);
      setIsEditing(false);
      setIsCreating(false);
    } catch (error) {
      console.error("Failed to load manual detail:", error);
    }
  }

  function handleCloseDetail() {
    setSelectedManual(null);
    setIsEditing(false);
    setIsCreating(false);
  }

  function handleStartCreate() {
    setEditForm({
      title: "",
      summary: "",
      content: "",
      categoryId: "",
      tags: "",
      isPinned: false,
      isPublished: true,
    });
    setIsCreating(true);
    setIsEditing(false);
    setSelectedManual(null);
  }

  function handleStartEdit() {
    if (!selectedManual) return;
    setEditForm({
      title: selectedManual.title,
      summary: selectedManual.summary || "",
      content: selectedManual.content,
      categoryId: selectedManual.categoryId?.toString() || "",
      tags: selectedManual.tags?.join(", ") || "",
      isPinned: selectedManual.isPinned,
      isPublished: selectedManual.isPublished,
    });
    setIsEditing(true);
    setIsCreating(false);
  }

  async function handleSave() {
    try {
      const payload = {
        title: editForm.title,
        summary: editForm.summary,
        content: editForm.content,
        category_id: editForm.categoryId ? parseInt(editForm.categoryId) : null,
        tags: editForm.tags.split(",").map(t => t.trim()).filter(t => t),
        is_pinned: editForm.isPinned,
        is_published: editForm.isPublished,
      };

      if (isCreating) {
        await apiClient.post("/knowledge/manuals/", payload);
      } else if (selectedManual) {
        await apiClient.patch(`/knowledge/manuals/${selectedManual.id}/`, payload);
      }

      await loadManuals();
      handleCloseDetail();
    } catch (error) {
      console.error("Failed to save manual:", error);
      alert("保存に失敗しました");
    }
  }

  async function handleDelete() {
    if (!selectedManual || !confirm("このマニュアルを削除しますか？")) return;
    try {
      await apiClient.delete(`/knowledge/manuals/${selectedManual.id}/`);
      await loadManuals();
      handleCloseDetail();
    } catch (error) {
      console.error("Failed to delete manual:", error);
      alert("削除に失敗しました");
    }
  }

  const pinnedManuals = manuals.filter(m => m.isPinned);
  const publishedManuals = manuals.filter(m => m.isPublished);
  const draftManuals = manuals.filter(m => !m.isPublished);

  return (
    <ThreePaneLayout
      isRightPanelOpen={!!selectedManual || isCreating}
      onCloseRightPanel={handleCloseDetail}
      rightPanel={
        isCreating || isEditing ? (
          <div className="p-6 space-y-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">
                {isCreating ? "新規マニュアル" : "マニュアル編集"}
              </h2>
              <Button variant="ghost" size="sm" onClick={handleCloseDetail}>
                <X className="w-4 h-4" />
              </Button>
            </div>

            <div className="space-y-4">
              <div>
                <Label>タイトル</Label>
                <Input
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  placeholder="マニュアルのタイトル"
                />
              </div>

              <div>
                <Label>カテゴリ</Label>
                <select
                  className="w-full p-2 border rounded-md"
                  value={editForm.categoryId}
                  onChange={(e) => setEditForm({ ...editForm, categoryId: e.target.value })}
                >
                  <option value="">カテゴリなし</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <Label>概要</Label>
                <Textarea
                  value={editForm.summary}
                  onChange={(e) => setEditForm({ ...editForm, summary: e.target.value })}
                  placeholder="簡単な説明"
                  rows={2}
                />
              </div>

              <div>
                <Label>内容</Label>
                <Textarea
                  value={editForm.content}
                  onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                  placeholder="マニュアルの本文（Markdown対応）"
                  rows={12}
                />
              </div>

              <div>
                <Label>タグ（カンマ区切り）</Label>
                <Input
                  value={editForm.tags}
                  onChange={(e) => setEditForm({ ...editForm, tags: e.target.value })}
                  placeholder="タグ1, タグ2, タグ3"
                />
              </div>

              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editForm.isPinned}
                    onChange={(e) => setEditForm({ ...editForm, isPinned: e.target.checked })}
                  />
                  ピン留め
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editForm.isPublished}
                    onChange={(e) => setEditForm({ ...editForm, isPublished: e.target.checked })}
                  />
                  公開
                </label>
              </div>

              <div className="flex gap-2 pt-4">
                <Button onClick={handleSave} className="flex-1">
                  保存
                </Button>
                <Button variant="outline" onClick={handleCloseDetail}>
                  キャンセル
                </Button>
              </div>
            </div>
          </div>
        ) : selectedManual ? (
          <div className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  {selectedManual.isPinned && (
                    <Pin className="w-4 h-4 text-blue-500" />
                  )}
                  <h2 className="text-xl font-bold">{selectedManual.title}</h2>
                </div>
                {selectedManual.category && (
                  <span className="text-sm bg-gray-100 px-2 py-1 rounded">
                    {selectedManual.category.name}
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleStartEdit}>
                  <Pencil className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={handleDelete}>
                  <Trash2 className="w-4 h-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={handleCloseDetail}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {selectedManual.summary && (
              <p className="text-gray-600 mb-4">{selectedManual.summary}</p>
            )}

            <div className="flex gap-4 text-sm text-gray-500 mb-4">
              <span className="flex items-center gap-1">
                <Eye className="w-4 h-4" />
                {selectedManual.viewCount}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {new Date(selectedManual.updatedAt).toLocaleDateString("ja-JP")}
              </span>
              {selectedManual.author && (
                <span className="flex items-center gap-1">
                  <User className="w-4 h-4" />
                  {selectedManual.author.fullName}
                </span>
              )}
            </div>

            {selectedManual.tags && selectedManual.tags.length > 0 && (
              <div className="flex gap-2 mb-4">
                {selectedManual.tags.map((tag, idx) => (
                  <span key={idx} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded flex items-center gap-1">
                    <Tag className="w-3 h-3" />
                    {tag}
                  </span>
                ))}
              </div>
            )}

            <div className="border-t pt-4">
              <div className="prose prose-sm max-w-none whitespace-pre-wrap">
                {selectedManual.content}
              </div>
            </div>
          </div>
        ) : null
      }
    >
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">社内マニュアル</h1>
            <p className="text-gray-600">
              {manuals.length}件のマニュアルがあります
            </p>
          </div>
          <Button onClick={handleStartCreate}>
            <Plus className="w-4 h-4 mr-2" />
            新規作成
          </Button>
        </div>

        <div className="flex gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="検索..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <select
            className="p-2 border rounded-md"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            <option value="">すべてのカテゴリ</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="text-center text-gray-500 py-8">読み込み中...</div>
        ) : (
          <Tabs defaultValue="all" className="w-full">
            <TabsList className="mb-4">
              <TabsTrigger value="all">すべて ({manuals.length})</TabsTrigger>
              <TabsTrigger value="pinned">ピン留め ({pinnedManuals.length})</TabsTrigger>
              <TabsTrigger value="published">公開中 ({publishedManuals.length})</TabsTrigger>
              <TabsTrigger value="draft">下書き ({draftManuals.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="all">
              <ManualList manuals={manuals} onSelect={handleSelectManual} selectedId={selectedManual?.id} />
            </TabsContent>
            <TabsContent value="pinned">
              <ManualList manuals={pinnedManuals} onSelect={handleSelectManual} selectedId={selectedManual?.id} />
            </TabsContent>
            <TabsContent value="published">
              <ManualList manuals={publishedManuals} onSelect={handleSelectManual} selectedId={selectedManual?.id} />
            </TabsContent>
            <TabsContent value="draft">
              <ManualList manuals={draftManuals} onSelect={handleSelectManual} selectedId={selectedManual?.id} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </ThreePaneLayout>
  );
}

function ManualList({
  manuals,
  onSelect,
  selectedId
}: {
  manuals: Manual[];
  onSelect: (manual: Manual) => void;
  selectedId?: number;
}) {
  if (manuals.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        <BookOpen className="w-12 h-12 mx-auto mb-2 text-gray-300" />
        マニュアルがありません
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {manuals.map((manual) => (
        <div
          key={manual.id}
          onClick={() => onSelect(manual)}
          className={`p-4 border rounded-lg cursor-pointer transition-colors ${
            selectedId === manual.id
              ? "border-blue-500 bg-blue-50"
              : "hover:bg-gray-50"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                {manual.isPinned && <Pin className="w-4 h-4 text-blue-500" />}
                <h3 className="font-medium">{manual.title}</h3>
                {!manual.isPublished && (
                  <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">
                    下書き
                  </span>
                )}
              </div>
              {manual.summary && (
                <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                  {manual.summary}
                </p>
              )}
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                {manual.category && (
                  <span className="bg-gray-100 px-2 py-0.5 rounded">
                    {manual.category.name}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Eye className="w-3 h-3" />
                  {manual.viewCount}
                </span>
                <span>
                  更新: {new Date(manual.updatedAt).toLocaleDateString("ja-JP")}
                </span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
