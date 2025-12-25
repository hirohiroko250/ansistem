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
  Star,
  Copy,
  Pencil,
  Trash2,
  X,
  MessageSquare,
  Tag,
  FileText,
  Mail,
} from "lucide-react";

interface TemplateCategory {
  id: number;
  name: string;
  description: string;
  sortOrder: number;
  isActive: boolean;
}

interface ChatTemplate {
  id: number;
  title: string;
  content: string;
  subject: string;
  category: TemplateCategory | null;
  categoryId: number | null;
  templateType: string;
  scene: string;
  variables: string[];
  tags: string[];
  isDefault: boolean;
  isActive: boolean;
  useCount: number;
  createdAt: string;
  updatedAt: string;
}

const TEMPLATE_TYPES = [
  { value: "chat", label: "チャット" },
  { value: "email", label: "メール" },
  { value: "sms", label: "SMS" },
  { value: "notification", label: "通知" },
];

const SCENES = [
  "入会案内",
  "体験申込",
  "体験フォロー",
  "契約確認",
  "請求案内",
  "未払い督促",
  "退会手続き",
  "その他問い合わせ",
];

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<ChatTemplate[]>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<ChatTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("");
  const [isEditing, setIsEditing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [editForm, setEditForm] = useState({
    title: "",
    content: "",
    subject: "",
    categoryId: "",
    templateType: "chat",
    scene: "",
    tags: "",
    isDefault: false,
    isActive: true,
  });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [searchQuery, selectedType]);

  async function loadData() {
    setLoading(true);
    await Promise.all([loadTemplates(), loadCategories()]);
    setLoading(false);
  }

  async function loadTemplates() {
    try {
      const params: Record<string, string> = {};
      if (searchQuery) params.search = searchQuery;
      if (selectedType) params.type = selectedType;

      const response = await apiClient.get<any>("/knowledge/templates/", params);
      const data = response.results || response.data || response || [];
      setTemplates(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load templates:", error);
      setTemplates([]);
    }
  }

  async function loadCategories() {
    try {
      const response = await apiClient.get<any>("/knowledge/template-categories/");
      const data = response.results || response.data || response || [];
      setCategories(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load categories:", error);
      setCategories([]);
    }
  }

  async function handleSelectTemplate(template: ChatTemplate) {
    try {
      const detail = await apiClient.get<ChatTemplate>(`/knowledge/templates/${template.id}/`);
      setSelectedTemplate(detail);
      setIsEditing(false);
      setIsCreating(false);
    } catch (error) {
      console.error("Failed to load template detail:", error);
    }
  }

  function handleCloseDetail() {
    setSelectedTemplate(null);
    setIsEditing(false);
    setIsCreating(false);
  }

  function handleStartCreate() {
    setEditForm({
      title: "",
      content: "",
      subject: "",
      categoryId: "",
      templateType: "chat",
      scene: "",
      tags: "",
      isDefault: false,
      isActive: true,
    });
    setIsCreating(true);
    setIsEditing(false);
    setSelectedTemplate(null);
  }

  function handleStartEdit() {
    if (!selectedTemplate) return;
    setEditForm({
      title: selectedTemplate.title,
      content: selectedTemplate.content,
      subject: selectedTemplate.subject || "",
      categoryId: selectedTemplate.categoryId?.toString() || "",
      templateType: selectedTemplate.templateType,
      scene: selectedTemplate.scene || "",
      tags: selectedTemplate.tags?.join(", ") || "",
      isDefault: selectedTemplate.isDefault,
      isActive: selectedTemplate.isActive,
    });
    setIsEditing(true);
    setIsCreating(false);
  }

  async function handleSave() {
    try {
      const payload = {
        title: editForm.title,
        content: editForm.content,
        subject: editForm.subject,
        category_id: editForm.categoryId ? parseInt(editForm.categoryId) : null,
        template_type: editForm.templateType,
        scene: editForm.scene,
        tags: editForm.tags.split(",").map(t => t.trim()).filter(t => t),
        is_default: editForm.isDefault,
        is_active: editForm.isActive,
      };

      if (isCreating) {
        await apiClient.post("/knowledge/templates/", payload);
      } else if (selectedTemplate) {
        await apiClient.patch(`/knowledge/templates/${selectedTemplate.id}/`, payload);
      }

      await loadTemplates();
      handleCloseDetail();
    } catch (error) {
      console.error("Failed to save template:", error);
      alert("保存に失敗しました");
    }
  }

  async function handleDelete() {
    if (!selectedTemplate || !confirm("このテンプレートを削除しますか？")) return;
    try {
      await apiClient.delete(`/knowledge/templates/${selectedTemplate.id}/`);
      await loadTemplates();
      handleCloseDetail();
    } catch (error) {
      console.error("Failed to delete template:", error);
      alert("削除に失敗しました");
    }
  }

  async function handleCopy() {
    if (!selectedTemplate) return;
    try {
      await navigator.clipboard.writeText(selectedTemplate.content);
      setCopySuccess(true);
      // 使用回数をインクリメント
      await apiClient.post(`/knowledge/templates/${selectedTemplate.id}/use/`);
      await loadTemplates();
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  }

  const defaultTemplates = templates.filter(t => t.isDefault);
  const activeTemplates = templates.filter(t => t.isActive);
  const inactiveTemplates = templates.filter(t => !t.isActive);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "email": return <Mail className="w-4 h-4" />;
      case "chat": return <MessageSquare className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  const getTypeLabel = (type: string) => {
    return TEMPLATE_TYPES.find(t => t.value === type)?.label || type;
  };

  return (
    <ThreePaneLayout
      isRightPanelOpen={!!selectedTemplate || isCreating}
      onCloseRightPanel={handleCloseDetail}
      rightPanel={
        isCreating || isEditing ? (
          <div className="p-6 space-y-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">
                {isCreating ? "新規テンプレート" : "テンプレート編集"}
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
                  placeholder="テンプレートのタイトル"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>種類</Label>
                  <select
                    className="w-full p-2 border rounded-md"
                    value={editForm.templateType}
                    onChange={(e) => setEditForm({ ...editForm, templateType: e.target.value })}
                  >
                    {TEMPLATE_TYPES.map((type) => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
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
              </div>

              <div>
                <Label>場面</Label>
                <select
                  className="w-full p-2 border rounded-md"
                  value={editForm.scene}
                  onChange={(e) => setEditForm({ ...editForm, scene: e.target.value })}
                >
                  <option value="">場面を選択</option>
                  {SCENES.map((scene) => (
                    <option key={scene} value={scene}>{scene}</option>
                  ))}
                </select>
              </div>

              {(editForm.templateType === "email" || editForm.templateType === "notification") && (
                <div>
                  <Label>件名</Label>
                  <Input
                    value={editForm.subject}
                    onChange={(e) => setEditForm({ ...editForm, subject: e.target.value })}
                    placeholder="メール/通知の件名"
                  />
                </div>
              )}

              <div>
                <Label>内容</Label>
                <Textarea
                  value={editForm.content}
                  onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                  placeholder="テンプレートの本文&#10;&#10;変数を使用する場合は {{変数名}} の形式で記載&#10;例: {{保護者名}}様"
                  rows={10}
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
                    checked={editForm.isDefault}
                    onChange={(e) => setEditForm({ ...editForm, isDefault: e.target.checked })}
                  />
                  デフォルト
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editForm.isActive}
                    onChange={(e) => setEditForm({ ...editForm, isActive: e.target.checked })}
                  />
                  有効
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
        ) : selectedTemplate ? (
          <div className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  {selectedTemplate.isDefault && (
                    <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                  )}
                  {getTypeIcon(selectedTemplate.templateType)}
                  <h2 className="text-xl font-bold">{selectedTemplate.title}</h2>
                </div>
                <div className="flex gap-2">
                  <span className="text-sm bg-blue-100 text-blue-700 px-2 py-1 rounded">
                    {getTypeLabel(selectedTemplate.templateType)}
                  </span>
                  {selectedTemplate.scene && (
                    <span className="text-sm bg-green-100 text-green-700 px-2 py-1 rounded">
                      {selectedTemplate.scene}
                    </span>
                  )}
                  {selectedTemplate.category && (
                    <span className="text-sm bg-gray-100 px-2 py-1 rounded">
                      {selectedTemplate.category.name}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopy}
                  className={copySuccess ? "bg-green-100" : ""}
                >
                  <Copy className="w-4 h-4" />
                  {copySuccess ? "コピーしました" : ""}
                </Button>
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

            <div className="text-sm text-gray-500 mb-4">
              使用回数: {selectedTemplate.useCount}回
            </div>

            {selectedTemplate.subject && (
              <div className="mb-4">
                <span className="text-sm text-gray-500">件名:</span>
                <p className="font-medium">{selectedTemplate.subject}</p>
              </div>
            )}

            {selectedTemplate.tags && selectedTemplate.tags.length > 0 && (
              <div className="flex gap-2 mb-4">
                {selectedTemplate.tags.map((tag, idx) => (
                  <span key={idx} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded flex items-center gap-1">
                    <Tag className="w-3 h-3" />
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {selectedTemplate.variables && selectedTemplate.variables.length > 0 && (
              <div className="mb-4 p-3 bg-yellow-50 rounded-lg">
                <span className="text-sm font-medium text-yellow-800">変数:</span>
                <div className="flex flex-wrap gap-2 mt-1">
                  {selectedTemplate.variables.map((v, idx) => (
                    <code key={idx} className="text-sm bg-yellow-100 px-2 py-0.5 rounded">
                      {`{{${v}}}`}
                    </code>
                  ))}
                </div>
              </div>
            )}

            <div className="border-t pt-4">
              <div className="bg-gray-50 p-4 rounded-lg whitespace-pre-wrap font-mono text-sm">
                {selectedTemplate.content}
              </div>
            </div>
          </div>
        ) : null
      }
    >
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">チャットテンプレート</h1>
            <p className="text-gray-600">
              {templates.length}件のテンプレートがあります
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
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            <option value="">すべての種類</option>
            {TEMPLATE_TYPES.map((type) => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="text-center text-gray-500 py-8">読み込み中...</div>
        ) : (
          <Tabs defaultValue="all" className="w-full">
            <TabsList className="mb-4">
              <TabsTrigger value="all">すべて ({templates.length})</TabsTrigger>
              <TabsTrigger value="default">デフォルト ({defaultTemplates.length})</TabsTrigger>
              <TabsTrigger value="active">有効 ({activeTemplates.length})</TabsTrigger>
              <TabsTrigger value="inactive">無効 ({inactiveTemplates.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="all">
              <TemplateList templates={templates} onSelect={handleSelectTemplate} selectedId={selectedTemplate?.id} />
            </TabsContent>
            <TabsContent value="default">
              <TemplateList templates={defaultTemplates} onSelect={handleSelectTemplate} selectedId={selectedTemplate?.id} />
            </TabsContent>
            <TabsContent value="active">
              <TemplateList templates={activeTemplates} onSelect={handleSelectTemplate} selectedId={selectedTemplate?.id} />
            </TabsContent>
            <TabsContent value="inactive">
              <TemplateList templates={inactiveTemplates} onSelect={handleSelectTemplate} selectedId={selectedTemplate?.id} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </ThreePaneLayout>
  );
}

function TemplateList({
  templates,
  onSelect,
  selectedId
}: {
  templates: ChatTemplate[];
  onSelect: (template: ChatTemplate) => void;
  selectedId?: number;
}) {
  if (templates.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-300" />
        テンプレートがありません
      </div>
    );
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "email": return <Mail className="w-4 h-4" />;
      case "chat": return <MessageSquare className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-2">
      {templates.map((template) => (
        <div
          key={template.id}
          onClick={() => onSelect(template)}
          className={`p-4 border rounded-lg cursor-pointer transition-colors ${
            selectedId === template.id
              ? "border-blue-500 bg-blue-50"
              : "hover:bg-gray-50"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                {template.isDefault && <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />}
                {getTypeIcon(template.templateType)}
                <h3 className="font-medium">{template.title}</h3>
                {!template.isActive && (
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                    無効
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                {template.content.substring(0, 100)}...
              </p>
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                {template.scene && (
                  <span className="bg-green-50 text-green-700 px-2 py-0.5 rounded">
                    {template.scene}
                  </span>
                )}
                {template.category && (
                  <span className="bg-gray-100 px-2 py-0.5 rounded">
                    {template.category.name}
                  </span>
                )}
                <span>
                  使用: {template.useCount}回
                </span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
