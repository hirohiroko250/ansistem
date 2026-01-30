"use client";

import { useEffect, useState, useRef } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import apiClient, { getMediaUrl, getAccessToken } from "@/lib/api/client";
import {
  Plus,
  Heart,
  MessageCircle,
  Eye,
  Pin,
  Pencil,
  Trash2,
  Users,
  Building,
  Calendar,
  Globe,
  Lock,
  Loader2,
  ArrowLeft,
  Image as ImageIcon,
  Settings2,
} from "lucide-react";
import { MultiSelect } from "@/components/ui/multi-select";
import { FileUpload } from "@/components/ui/file-upload";
import FeedEditor, { type FeedEditorHandle } from "@/components/feed/FeedEditor";

interface FeedPost {
  id: string;
  postType: string;
  title?: string;
  content: string;
  visibility: string;
  authorName?: string;
  schoolName?: string;
  hashtags?: string[];
  isPinned: boolean;
  allowComments: boolean;
  allowLikes: boolean;
  likeCount: number;
  commentCount: number;
  viewCount: number;
  media?: Array<{ id: string; mediaType: string; fileUrl: string; thumbnailUrl?: string }>;
  targetBrands?: string[];
  targetBrandsDetail?: Array<{ id: string; name: string }>;
  targetSchools?: string[];
  targetSchoolsDetail?: Array<{ id: string; name: string }>;
  isPublished: boolean;
  publishedAt?: string;
  publishStartAt?: string;
  publishEndAt?: string;
  createdAt: string;
  updatedAt: string;
}

interface School {
  id: string;
  schoolName: string;
}

interface Brand {
  id: string;
  brandName: string;
}

export default function FeedPage() {
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPost, setSelectedPost] = useState<FeedPost | null>(null);
  const [editingMode, setEditingMode] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [sidebarTab, setSidebarTab] = useState<"media" | "settings">("media");
  const [mediaTab, setMediaTab] = useState<"photo" | "video">("photo");

  const editorRef = useRef<FeedEditorHandle>(null);

  const [formData, setFormData] = useState({
    title: "",
    content: "",
    visibility: "PUBLIC",
    school: "",
    targetBrands: [] as string[],
    targetSchools: [] as string[],
    hashtags: "",
    allowComments: true,
    allowLikes: true,
    isPublished: true,
    isPinned: false,
    publishStartAt: "",
    publishEndAt: "",
  });

  useEffect(() => {
    loadPosts();
    loadSchools();
    loadBrands();
  }, []);

  async function loadPosts() {
    try {
      setLoading(true);
      const response = await apiClient.get<any>("/communications/feed/posts/");
      const data = response.results || response.data || response || [];
      setPosts(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load posts:", error);
      setPosts([]);
    } finally {
      setLoading(false);
    }
  }

  async function loadSchools() {
    try {
      const response = await apiClient.get<any>("/schools/schools/?page_size=500");
      const data = response.results || response.data || response || [];
      setSchools(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load schools:", error);
    }
  }

  async function loadBrands() {
    try {
      const response = await apiClient.get<any>("/schools/brands/?page_size=500");
      const data = response.results || response.data || response || [];
      setBrands(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load brands:", error);
    }
  }

  function handleCreate() {
    setFormData({
      title: "",
      content: "",
      visibility: "PUBLIC",
      school: "",
      targetBrands: [],
      targetSchools: [],
      hashtags: "",
      allowComments: true,
      allowLikes: true,
      isPublished: true,
      isPinned: false,
      publishStartAt: "",
      publishEndAt: "",
    });
    setSelectedPost(null);
    setIsEditing(false);
    setEditingMode(true);
    setSidebarTab("media");
  }

  function handleEdit(post: FeedPost) {
    setFormData({
      title: post.title || "",
      content: post.content || "",
      visibility: post.visibility || "PUBLIC",
      school: "",
      targetBrands: post.targetBrands || [],
      targetSchools: post.targetSchools || [],
      hashtags: post.hashtags?.join(", ") || "",
      allowComments: post.allowComments ?? true,
      allowLikes: post.allowLikes ?? true,
      isPublished: post.isPublished ?? true,
      isPinned: post.isPinned ?? false,
      publishStartAt: post.publishStartAt ? post.publishStartAt.slice(0, 16) : "",
      publishEndAt: post.publishEndAt ? post.publishEndAt.slice(0, 16) : "",
    });
    setSelectedPost(post);
    setIsEditing(true);
    setEditingMode(true);
    setSidebarTab("media");
  }

  function handleBackToList() {
    setEditingMode(false);
    setSelectedPost(null);
  }

  async function handleSave(overrides?: Partial<typeof formData>) {
    try {
      setSaving(true);
      const data = { ...formData, ...overrides };
      const content = editorRef.current?.getContent() || data.content;

      // Detect media in HTML content
      const tempDiv = document.createElement("div");
      tempDiv.innerHTML = content;
      const images = tempDiv.querySelectorAll("img");
      const videos = tempDiv.querySelectorAll("video");

      let postType = "TEXT";
      if (videos.length > 0) {
        postType = "VIDEO";
      } else if (images.length > 1) {
        postType = "GALLERY";
      } else if (images.length === 1) {
        postType = "IMAGE";
      }

      const payload: any = {
        post_type: postType,
        title: data.title,
        content,
        visibility: data.visibility,
        hashtags: data.hashtags.split(",").map((t) => t.trim()).filter((t) => t),
        allow_comments: data.allowComments,
        allow_likes: data.allowLikes,
        is_published: data.isPublished,
        is_pinned: data.isPinned,
      };

      if (data.school && data.school !== "_none") {
        payload.school = data.school;
      }
      if (data.targetBrands.length > 0) {
        payload.target_brands = data.targetBrands;
      }
      if (data.targetSchools.length > 0) {
        payload.target_schools = data.targetSchools;
      }
      if (data.publishStartAt) {
        payload.publish_start_at = new Date(data.publishStartAt).toISOString();
      }
      if (data.publishEndAt) {
        payload.publish_end_at = new Date(data.publishEndAt).toISOString();
      }

      // Extract media items
      const mediaItems: any[] = [];
      images.forEach((img) => {
        const src = img.getAttribute("src");
        if (src) mediaItems.push({ media_type: "IMAGE", file_url: src });
      });
      videos.forEach((vid) => {
        const src = vid.getAttribute("src");
        if (src) mediaItems.push({ media_type: "VIDEO", file_url: src });
      });
      if (mediaItems.length > 0) {
        payload.media_items = mediaItems;
      }

      if (isEditing && selectedPost) {
        await apiClient.patch(`/communications/feed/posts/${selectedPost.id}/`, payload);
      } else {
        await apiClient.post("/communications/feed/posts/", payload);
      }

      await loadPosts();
      setEditingMode(false);
    } catch (error) {
      console.error("Failed to save post:", error);
      alert("保存に失敗しました");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(post: FeedPost) {
    if (!confirm("この投稿を削除しますか？")) return;
    try {
      await apiClient.delete(`/communications/feed/posts/${post.id}/`);
      await loadPosts();
    } catch (error) {
      console.error("Failed to delete post:", error);
      alert("削除に失敗しました");
    }
  }

  function handleMediaUpload(file: { url: string }) {
    const fullUrl = getMediaUrl(file.url);
    if (mediaTab === "photo") {
      editorRef.current?.insertImage(fullUrl);
    } else {
      editorRef.current?.insertVideo(fullUrl);
    }
  }

  async function handlePasteFile(file: File): Promise<string | null> {
    try {
      const token = getAccessToken();
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${baseUrl}/core/upload/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) return null;
      const data = await response.json();
      return getMediaUrl(data.url);
    } catch {
      return null;
    }
  }

  function getVisibilityIcon(visibility: string) {
    switch (visibility) {
      case "PUBLIC": return <Globe className="w-4 h-4" />;
      case "SCHOOL": return <Building className="w-4 h-4" />;
      case "STAFF": return <Lock className="w-4 h-4" />;
      default: return <Users className="w-4 h-4" />;
    }
  }

  function getVisibilityLabel(visibility: string) {
    switch (visibility) {
      case "PUBLIC": return "全体公開";
      case "SCHOOL": return "校舎限定";
      case "GRADE": return "学年限定";
      case "STAFF": return "スタッフのみ";
      default: return visibility;
    }
  }

  // ========== EDITOR MODE ==========
  if (editingMode) {
    return (
      <div className="flex h-screen bg-gray-50">
        <Sidebar />

        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Bar */}
          <div className="border-b px-4 py-3 flex items-center justify-between bg-white flex-shrink-0">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" onClick={handleBackToList} className="gap-1">
                <ArrowLeft className="w-4 h-4" />
                一覧に戻る
              </Button>
              <span className="text-sm text-gray-500">
                {isEditing ? "投稿を編集" : "新規投稿"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleSave({ isPublished: false })}
                disabled={saving}
              >
                {saving && <Loader2 className="w-4 h-4 animate-spin mr-1" />}
                下書き保存
              </Button>
              <Button
                size="sm"
                onClick={() => handleSave({ isPublished: true })}
                disabled={saving}
              >
                {saving && <Loader2 className="w-4 h-4 animate-spin mr-1" />}
                {isEditing ? "更新する" : "投稿する"}
              </Button>
            </div>
          </div>

          {/* Editor + Right Sidebar */}
          <div className="flex-1 flex overflow-hidden">
            {/* Left: Title + Editor */}
            <div className="flex-1 flex flex-col overflow-y-auto">
              <div className="max-w-4xl w-full mx-auto p-6 flex flex-col flex-1">
                {/* Title Input */}
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="タイトルを入力..."
                  className="text-lg font-medium mb-4 h-12 border-blue-200 focus:border-blue-500"
                />

                {/* Rich Text Editor */}
                <FeedEditor
                  key={selectedPost?.id || "new"}
                  ref={editorRef}
                  initialContent={formData.content}
                  onChange={(html) => setFormData((prev) => ({ ...prev, content: html }))}
                  onPasteFile={handlePasteFile}
                  className="flex-1"
                />
              </div>
            </div>

            {/* Right Sidebar: メディア / 設定 */}
            <div className="w-80 border-l bg-white flex flex-col flex-shrink-0">
              {/* Sidebar Tab Headers */}
              <div className="border-b flex">
                <button
                  type="button"
                  className={`flex-1 py-3 text-sm font-medium text-center transition-colors ${
                    sidebarTab === "media"
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                  onClick={() => setSidebarTab("media")}
                >
                  <ImageIcon className="w-4 h-4 inline mr-1" />
                  写真・動画
                </button>
                <button
                  type="button"
                  className={`flex-1 py-3 text-sm font-medium text-center transition-colors ${
                    sidebarTab === "settings"
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                  onClick={() => setSidebarTab("settings")}
                >
                  <Settings2 className="w-4 h-4 inline mr-1" />
                  設定
                </button>
              </div>

              {/* Sidebar Content */}
              <div className="flex-1 overflow-y-auto">
                {sidebarTab === "media" ? (
                  <div className="p-4">
                    {/* Photo / Video sub-tabs */}
                    <div className="flex gap-2 mb-4">
                      <button
                        type="button"
                        className={`flex-1 py-2 text-sm rounded-lg transition-colors ${
                          mediaTab === "photo"
                            ? "bg-blue-50 text-blue-700 font-medium"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        }`}
                        onClick={() => setMediaTab("photo")}
                      >
                        写真
                      </button>
                      <button
                        type="button"
                        className={`flex-1 py-2 text-sm rounded-lg transition-colors ${
                          mediaTab === "video"
                            ? "bg-blue-50 text-blue-700 font-medium"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        }`}
                        onClick={() => setMediaTab("video")}
                      >
                        動画
                      </button>
                    </div>

                    {/* Upload Area */}
                    <FileUpload
                      accept={mediaTab === "photo" ? "image/*" : "video/*"}
                      label={mediaTab === "photo" ? "画像をアップロード" : "動画をアップロード"}
                      enableImageEdit={false}
                      onUpload={handleMediaUpload}
                    />

                    <p className="text-xs text-gray-500 mt-3 text-center">
                      アップロードした{mediaTab === "photo" ? "画像" : "動画"}はエディタに挿入されます
                    </p>
                  </div>
                ) : (
                  /* Settings Tab */
                  <div className="p-4 space-y-4">
                    {/* Visibility */}
                    <div>
                      <label className="text-sm font-medium block mb-1">公開範囲</label>
                      <Select
                        value={formData.visibility}
                        onValueChange={(v) => setFormData({ ...formData, visibility: v })}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="PUBLIC">全体公開</SelectItem>
                          <SelectItem value="SCHOOL">校舎限定</SelectItem>
                          <SelectItem value="GRADE">学年限定</SelectItem>
                          <SelectItem value="STAFF">スタッフのみ</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* School */}
                    <div>
                      <label className="text-sm font-medium block mb-1">投稿校舎</label>
                      <Select
                        value={formData.school}
                        onValueChange={(v) => setFormData({ ...formData, school: v })}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="選択..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="_none">なし</SelectItem>
                          {schools.map((school) => (
                            <SelectItem key={school.id} value={school.id}>
                              {school.schoolName}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Target Brands */}
                    <div>
                      <label className="text-sm font-medium flex items-center gap-1 mb-1">
                        <Building className="w-3.5 h-3.5" />
                        対象ブランド
                      </label>
                      <MultiSelect
                        options={brands.map((brand) => ({
                          value: brand.id,
                          label: brand.brandName,
                        }))}
                        selected={formData.targetBrands}
                        onChange={(selected) => setFormData({ ...formData, targetBrands: selected })}
                        placeholder="ブランドを選択..."
                        emptyMessage="ブランドがありません"
                        badgeVariant="default"
                      />
                      <p className="text-xs text-gray-500 mt-1">未選択の場合は全ブランド</p>
                    </div>

                    {/* Target Schools */}
                    <div>
                      <label className="text-sm font-medium flex items-center gap-1 mb-1">
                        <Building className="w-3.5 h-3.5" />
                        対象校舎
                      </label>
                      <MultiSelect
                        options={schools.map((school) => ({
                          value: school.id,
                          label: school.schoolName,
                        }))}
                        selected={formData.targetSchools}
                        onChange={(selected) => setFormData({ ...formData, targetSchools: selected })}
                        placeholder="校舎を選択..."
                        emptyMessage="校舎がありません"
                        badgeVariant="outline"
                      />
                      <p className="text-xs text-gray-500 mt-1">未選択の場合は全校舎</p>
                    </div>

                    {/* Publish Period */}
                    <div>
                      <label className="text-sm font-medium flex items-center gap-1 mb-1">
                        <Calendar className="w-3.5 h-3.5" />
                        公開期間
                      </label>
                      <div className="space-y-2">
                        <div>
                          <label className="text-xs text-gray-500">開始日時</label>
                          <Input
                            type="datetime-local"
                            value={formData.publishStartAt}
                            onChange={(e) => setFormData({ ...formData, publishStartAt: e.target.value })}
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-500">終了日時</label>
                          <Input
                            type="datetime-local"
                            value={formData.publishEndAt}
                            onChange={(e) => setFormData({ ...formData, publishEndAt: e.target.value })}
                          />
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">未設定の場合は即時・無期限</p>
                    </div>

                    {/* Hashtags */}
                    <div>
                      <label className="text-sm font-medium block mb-1">ハッシュタグ</label>
                      <Input
                        value={formData.hashtags}
                        onChange={(e) => setFormData({ ...formData, hashtags: e.target.value })}
                        placeholder="カンマ区切り: タグ1, タグ2"
                      />
                    </div>

                    {/* Checkboxes */}
                    <div className="space-y-2 pt-2 border-t">
                      <label className="flex items-center gap-2 cursor-pointer text-sm">
                        <input
                          type="checkbox"
                          checked={formData.allowComments}
                          onChange={(e) => setFormData({ ...formData, allowComments: e.target.checked })}
                        />
                        コメント許可
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer text-sm">
                        <input
                          type="checkbox"
                          checked={formData.allowLikes}
                          onChange={(e) => setFormData({ ...formData, allowLikes: e.target.checked })}
                        />
                        いいね許可
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer text-sm">
                        <input
                          type="checkbox"
                          checked={formData.isPinned}
                          onChange={(e) => setFormData({ ...formData, isPinned: e.target.checked })}
                        />
                        ピン留め
                      </label>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ========== LIST MODE ==========
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 overflow-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">フィード管理</h1>
              <p className="text-sm text-gray-600">{posts.length}件の投稿</p>
            </div>
            <Button onClick={handleCreate}>
              <Plus className="w-4 h-4 mr-2" />
              新規投稿
            </Button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : posts.length === 0 ? (
            <Card className="p-12 text-center text-gray-500">
              <MessageCircle className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>投稿がありません</p>
              <Button onClick={handleCreate} className="mt-4">
                最初の投稿を作成
              </Button>
            </Card>
          ) : (
            <div className="bg-white border rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-100 border-b text-left">
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap w-12">No</th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap w-24">アクション</th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap w-20">ID</th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap w-20">状態</th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap min-w-[200px]">タイトル</th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap w-20">公開範囲</th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap w-32">開始日</th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap w-32">終了日</th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap w-36">対象ブランド</th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap w-36">対象校舎</th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap text-center w-16">
                        <Heart className="w-3.5 h-3.5 inline" />
                      </th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap text-center w-16">
                        <MessageCircle className="w-3.5 h-3.5 inline" />
                      </th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap text-center w-16">
                        <Eye className="w-3.5 h-3.5 inline" />
                      </th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap w-24">作成者</th>
                      <th className="px-3 py-2.5 font-semibold text-gray-700 whitespace-nowrap w-28">作成日</th>
                    </tr>
                  </thead>
                  <tbody>
                    {posts.map((post, index) => (
                      <tr
                        key={post.id}
                        className={`border-b last:border-b-0 hover:bg-blue-50/50 transition-colors ${
                          !post.isPublished ? "bg-gray-50/50" : ""
                        }`}
                      >
                        {/* No */}
                        <td className="px-3 py-2 text-gray-500 text-center">{index + 1}</td>

                        {/* アクション */}
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-1">
                            <button
                              type="button"
                              className="inline-flex items-center justify-center w-7 h-7 rounded hover:bg-blue-100 text-blue-600 transition-colors"
                              onClick={() => handleEdit(post)}
                              title="編集"
                            >
                              <Pencil className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              className="inline-flex items-center justify-center w-7 h-7 rounded hover:bg-red-100 text-red-500 transition-colors"
                              onClick={() => handleDelete(post)}
                              title="削除"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>

                        {/* ID */}
                        <td className="px-3 py-2 text-gray-500 font-mono text-xs">
                          {String(post.id).slice(0, 8)}
                        </td>

                        {/* 状態 */}
                        <td className="px-3 py-2">
                          {post.isPublished ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                              UP
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-600">
                              非表示
                            </span>
                          )}
                          {post.isPinned && (
                            <Pin className="w-3 h-3 text-blue-500 inline ml-1" />
                          )}
                        </td>

                        {/* タイトル */}
                        <td className="px-3 py-2">
                          <div className="max-w-[300px]">
                            <span
                              className="text-gray-900 font-medium hover:text-blue-600 cursor-pointer truncate block"
                              onClick={() => handleEdit(post)}
                              title={post.title || "(無題)"}
                            >
                              {post.title || <span className="text-gray-400">(無題)</span>}
                            </span>
                            <span className="text-gray-400 text-xs truncate block">
                              {post.content?.replace(/<[^>]*>/g, "").slice(0, 50)}
                            </span>
                          </div>
                        </td>

                        {/* 公開範囲 */}
                        <td className="px-3 py-2">
                          <span className="inline-flex items-center gap-1 text-xs text-gray-600">
                            {getVisibilityIcon(post.visibility)}
                            {getVisibilityLabel(post.visibility)}
                          </span>
                        </td>

                        {/* 開始日 */}
                        <td className="px-3 py-2 text-xs text-gray-600 whitespace-nowrap">
                          {post.publishStartAt
                            ? new Date(post.publishStartAt).toLocaleDateString("ja-JP", {
                                year: "numeric",
                                month: "2-digit",
                                day: "2-digit",
                              })
                            : <span className="text-gray-300">-</span>}
                        </td>

                        {/* 終了日 */}
                        <td className="px-3 py-2 text-xs text-gray-600 whitespace-nowrap">
                          {post.publishEndAt
                            ? new Date(post.publishEndAt).toLocaleDateString("ja-JP", {
                                year: "numeric",
                                month: "2-digit",
                                day: "2-digit",
                              })
                            : <span className="text-gray-300">-</span>}
                        </td>

                        {/* 対象ブランド */}
                        <td className="px-3 py-2">
                          {post.targetBrandsDetail && post.targetBrandsDetail.length > 0 ? (
                            <div className="flex flex-wrap gap-0.5">
                              {post.targetBrandsDetail.slice(0, 2).map((b) => (
                                <span key={b.id} className="inline-block px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded text-xs truncate max-w-[80px]">
                                  {b.name}
                                </span>
                              ))}
                              {post.targetBrandsDetail.length > 2 && (
                                <span className="text-xs text-gray-400">+{post.targetBrandsDetail.length - 2}</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-xs text-gray-300">全て</span>
                          )}
                        </td>

                        {/* 対象校舎 */}
                        <td className="px-3 py-2">
                          {post.targetSchoolsDetail && post.targetSchoolsDetail.length > 0 ? (
                            <div className="flex flex-wrap gap-0.5">
                              {post.targetSchoolsDetail.slice(0, 2).map((s) => (
                                <span key={s.id} className="inline-block px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-xs truncate max-w-[80px]">
                                  {s.name}
                                </span>
                              ))}
                              {post.targetSchoolsDetail.length > 2 && (
                                <span className="text-xs text-gray-400">+{post.targetSchoolsDetail.length - 2}</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-xs text-gray-300">全て</span>
                          )}
                        </td>

                        {/* いいね */}
                        <td className="px-3 py-2 text-center text-xs text-gray-600">{post.likeCount}</td>

                        {/* コメント */}
                        <td className="px-3 py-2 text-center text-xs text-gray-600">{post.commentCount}</td>

                        {/* 閲覧数 */}
                        <td className="px-3 py-2 text-center text-xs text-gray-600">{post.viewCount}</td>

                        {/* 作成者 */}
                        <td className="px-3 py-2 text-xs text-gray-700 whitespace-nowrap">
                          {post.authorName || "-"}
                        </td>

                        {/* 作成日 */}
                        <td className="px-3 py-2 text-xs text-gray-600 whitespace-nowrap">
                          {new Date(post.createdAt).toLocaleDateString("ja-JP", {
                            year: "numeric",
                            month: "2-digit",
                            day: "2-digit",
                          })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
