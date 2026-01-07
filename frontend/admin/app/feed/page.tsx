"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import apiClient, { getMediaUrl } from "@/lib/api/client";
import {
  Plus,
  Heart,
  MessageCircle,
  Eye,
  Pin,
  Pencil,
  Trash2,
  Image as ImageIcon,
  Users,
  Building,
  Calendar,
  Globe,
  Lock,
  X,
  Loader2,
  Film,
} from "lucide-react";
import { FileUpload } from "@/components/ui/file-upload";
import { MultiSelect } from "@/components/ui/multi-select";

interface FeedPost {
  id: string;
  postType: string;
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
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const [formData, setFormData] = useState({
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
    mediaFiles: [] as Array<{ url: string; type: "image" | "video"; filename: string }>,
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
      // 全件取得するためpage_sizeを大きく設定
      const response = await apiClient.get<any>("/schools/schools/?page_size=500");
      const data = response.results || response.data || response || [];
      setSchools(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load schools:", error);
    }
  }

  async function loadBrands() {
    try {
      // 全件取得するためpage_sizeを大きく設定
      const response = await apiClient.get<any>("/schools/brands/?page_size=500");
      const data = response.results || response.data || response || [];
      setBrands(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load brands:", error);
    }
  }

  function handleCreate() {
    setFormData({
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
      mediaFiles: [],
    });
    setSelectedPost(null);
    setIsEditing(false);
    setIsDialogOpen(true);
  }

  function handleEdit(post: FeedPost) {
    setFormData({
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
      mediaFiles: (post.media || []).map(m => ({
        url: m.fileUrl,
        type: m.mediaType === "VIDEO" ? "video" as const : "image" as const,
        filename: m.fileUrl.split("/").pop() || "",
      })),
    });
    setSelectedPost(post);
    setIsEditing(true);
    setIsDialogOpen(true);
  }

  async function handleSave() {
    try {
      setSaving(true);

      // 投稿タイプを判定
      let postType = "TEXT";
      if (formData.mediaFiles.length > 0) {
        const hasVideo = formData.mediaFiles.some(f => f.type === "video");
        postType = hasVideo ? "VIDEO" : (formData.mediaFiles.length > 1 ? "GALLERY" : "IMAGE");
      }

      const payload: any = {
        post_type: postType,
        content: formData.content,
        visibility: formData.visibility,
        hashtags: formData.hashtags.split(",").map(t => t.trim()).filter(t => t),
        allow_comments: formData.allowComments,
        allow_likes: formData.allowLikes,
        is_published: formData.isPublished,
        is_pinned: formData.isPinned,
      };

      if (formData.school && formData.school !== "_none") {
        payload.school = formData.school;
      }

      // ブランド・校舎フィルター
      if (formData.targetBrands.length > 0) {
        payload.target_brands = formData.targetBrands;
      }
      if (formData.targetSchools.length > 0) {
        payload.target_schools = formData.targetSchools;
      }

      // 公開日時
      if (formData.publishStartAt) {
        payload.publish_start_at = new Date(formData.publishStartAt).toISOString();
      }
      if (formData.publishEndAt) {
        payload.publish_end_at = new Date(formData.publishEndAt).toISOString();
      }

      if (formData.mediaFiles.length > 0) {
        payload.media_items = formData.mediaFiles.map(f => ({
          media_type: f.type.toUpperCase(),
          file_url: f.url,
        }));
      }

      if (isEditing && selectedPost) {
        await apiClient.patch(`/communications/feed/posts/${selectedPost.id}/`, payload);
      } else {
        await apiClient.post("/communications/feed/posts/", payload);
      }

      await loadPosts();
      setIsDialogOpen(false);
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

  function getVisibilityIcon(visibility: string) {
    switch (visibility) {
      case "PUBLIC":
        return <Globe className="w-4 h-4" />;
      case "SCHOOL":
        return <Building className="w-4 h-4" />;
      case "STAFF":
        return <Lock className="w-4 h-4" />;
      default:
        return <Users className="w-4 h-4" />;
    }
  }

  function getVisibilityLabel(visibility: string) {
    switch (visibility) {
      case "PUBLIC":
        return "全体公開";
      case "SCHOOL":
        return "校舎限定";
      case "GRADE":
        return "学年限定";
      case "STAFF":
        return "スタッフのみ";
      default:
        return visibility;
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 overflow-auto">
        <div className="p-6 max-w-4xl mx-auto">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">フィード管理</h1>
              <p className="text-gray-600">
                {posts.length}件の投稿
              </p>
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
            <div className="space-y-4">
              {posts.map((post) => (
                <Card key={post.id} className="p-4">
                  <div className="flex gap-4">
                    {/* メディアサムネイル */}
                    {post.media && post.media.length > 0 && (
                      <div className="flex-shrink-0">
                        <img
                          src={getMediaUrl(post.media[0].thumbnailUrl || post.media[0].fileUrl)}
                          alt=""
                          className="w-24 h-24 object-cover rounded"
                        />
                      </div>
                    )}

                    <div className="flex-1 min-w-0">
                      {/* ヘッダー */}
                      <div className="flex items-center gap-2 mb-2">
                        {post.isPinned && (
                          <Pin className="w-4 h-4 text-blue-500" />
                        )}
                        <span className="text-sm font-medium">{post.authorName || "スタッフ"}</span>
                        {post.schoolName && (
                          <Badge variant="outline" className="text-xs">
                            {post.schoolName}
                          </Badge>
                        )}
                        <span className="text-xs text-gray-500 flex items-center gap-1">
                          {getVisibilityIcon(post.visibility)}
                          {getVisibilityLabel(post.visibility)}
                        </span>
                        {!post.isPublished && (
                          <Badge variant="secondary">下書き</Badge>
                        )}
                      </div>

                      {/* コンテンツ */}
                      <p className="text-gray-700 mb-2 line-clamp-3 whitespace-pre-wrap">
                        {post.content}
                      </p>

                      {/* ハッシュタグ */}
                      {post.hashtags && post.hashtags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-2">
                          {post.hashtags.map((tag, idx) => (
                            <span key={idx} className="text-blue-500 text-sm">
                              #{tag}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* 統計 */}
                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        <span className="flex items-center gap-1">
                          <Heart className="w-4 h-4" />
                          {post.likeCount}
                        </span>
                        <span className="flex items-center gap-1">
                          <MessageCircle className="w-4 h-4" />
                          {post.commentCount}
                        </span>
                        <span className="flex items-center gap-1">
                          <Eye className="w-4 h-4" />
                          {post.viewCount}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          {new Date(post.createdAt).toLocaleDateString("ja-JP")}
                        </span>
                      </div>
                    </div>

                    {/* アクション */}
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => handleEdit(post)}>
                        <Pencil className="w-4 h-4" />
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => handleDelete(post)}>
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 投稿ダイアログ */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>
              {isEditing ? "投稿を編集" : "新規投稿"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4 overflow-y-auto flex-1">
            <div>
              <label className="text-sm font-medium">内容</label>
              <Textarea
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                placeholder="投稿内容を入力..."
                rows={6}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">公開範囲</label>
                <Select
                  value={formData.visibility}
                  onValueChange={(v) => setFormData({ ...formData, visibility: v })}
                >
                  <SelectTrigger>
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

              <div>
                <label className="text-sm font-medium">投稿校舎</label>
                <Select
                  value={formData.school}
                  onValueChange={(v) => setFormData({ ...formData, school: v })}
                >
                  <SelectTrigger>
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
            </div>

            {/* 対象ブランド選択 */}
            <div>
              <label className="text-sm font-medium flex items-center gap-1 mb-2">
                <Building className="w-4 h-4" />
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
              <p className="text-xs text-gray-500 mt-1">未選択の場合は全ブランドに表示されます</p>
            </div>

            {/* 対象校舎選択 */}
            <div>
              <label className="text-sm font-medium flex items-center gap-1 mb-2">
                <Building className="w-4 h-4" />
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
              <p className="text-xs text-gray-500 mt-1">未選択の場合は全校舎に表示されます</p>
            </div>

            {/* 公開期間設定 */}
            <div>
              <label className="text-sm font-medium flex items-center gap-1 mb-2">
                <Calendar className="w-4 h-4" />
                公開期間
              </label>
              <div className="grid grid-cols-2 gap-4">
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
              <p className="text-xs text-gray-500 mt-1">未設定の場合は即時公開・無期限となります</p>
            </div>

            {/* メディアアップロード */}
            <div>
              <label className="text-sm font-medium flex items-center gap-1 mb-2">
                <ImageIcon className="w-4 h-4" />
                <Film className="w-4 h-4" />
                画像・動画
              </label>
              <FileUpload
                accept="image/*,video/*"
                multiple
                label="画像・動画をアップロード"
                onUpload={(file) => {
                  setFormData({
                    ...formData,
                    mediaFiles: [...formData.mediaFiles, {
                      url: file.url,
                      type: file.type,
                      filename: file.filename,
                    }],
                  });
                }}
              />
              {formData.mediaFiles.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {formData.mediaFiles.map((file, idx) => (
                    <div key={idx} className="relative">
                      {file.type === "video" ? (
                        <video
                          src={getMediaUrl(file.url)}
                          className="w-20 h-20 object-cover rounded border"
                        />
                      ) : (
                        <img
                          src={getMediaUrl(file.url)}
                          alt={file.filename}
                          className="w-20 h-20 object-cover rounded border"
                        />
                      )}
                      <button
                        type="button"
                        onClick={() => setFormData({
                          ...formData,
                          mediaFiles: formData.mediaFiles.filter((_, i) => i !== idx),
                        })}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                      >
                        <X className="w-3 h-3" />
                      </button>
                      {file.type === "video" && (
                        <div className="absolute bottom-1 left-1 bg-black/50 text-white text-xs px-1 rounded">
                          動画
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="text-sm font-medium">ハッシュタグ（カンマ区切り）</label>
              <Input
                value={formData.hashtags}
                onChange={(e) => setFormData({ ...formData, hashtags: e.target.value })}
                placeholder="タグ1, タグ2, タグ3"
              />
            </div>

            <div className="flex flex-wrap gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.allowComments}
                  onChange={(e) => setFormData({ ...formData, allowComments: e.target.checked })}
                />
                <span className="text-sm">コメント許可</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.allowLikes}
                  onChange={(e) => setFormData({ ...formData, allowLikes: e.target.checked })}
                />
                <span className="text-sm">いいね許可</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.isPinned}
                  onChange={(e) => setFormData({ ...formData, isPinned: e.target.checked })}
                />
                <span className="text-sm">ピン留め</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.isPublished}
                  onChange={(e) => setFormData({ ...formData, isPublished: e.target.checked })}
                />
                <span className="text-sm">公開</span>
              </label>
            </div>
          </div>

          <DialogFooter className="flex-shrink-0 border-t pt-4 mt-2">
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleSave} disabled={saving || !formData.content.trim()}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              {isEditing ? "更新" : "投稿"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
