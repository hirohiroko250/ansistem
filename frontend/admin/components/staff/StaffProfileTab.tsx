"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Star,
  Globe,
  MapPin,
  Video,
  MessageCircle,
  Plus,
  X,
  Loader2,
  Save,
} from "lucide-react";
import apiClient from "@/lib/api/client";

interface StaffSkill {
  id: string;
  category: string;
  name: string;
  level: number;
  color: string;
}

interface StaffProfile {
  id: string;
  employee_id: string;
  employee_name: string;
  profile_image_url?: string;
  display_name: string;
  greeting: string;
  bio: string;
  lesson_style: string;
  career: string;
  origin_country: string;
  residence_country: string;
  communication_tool: string;
  communication_url: string;
  rating: number;
  review_count: number;
  lesson_count: number;
  points: number;
  is_public: boolean;
  is_bookable: boolean;
  admin_comment: string;
  skills: StaffSkill[];
  brands: { id: string; name: string }[];
}

interface StaffProfileTabProps {
  staffId: string;
}

const skillColors = [
  { value: "blue", label: "青", class: "bg-blue-500" },
  { value: "green", label: "緑", class: "bg-green-500" },
  { value: "red", label: "赤", class: "bg-red-500" },
  { value: "purple", label: "紫", class: "bg-purple-500" },
  { value: "orange", label: "オレンジ", class: "bg-orange-500" },
  { value: "pink", label: "ピンク", class: "bg-pink-500" },
  { value: "yellow", label: "黄", class: "bg-yellow-500" },
  { value: "cyan", label: "シアン", class: "bg-cyan-500" },
];

const skillCategories = [
  { value: "subject", label: "教科" },
  { value: "language", label: "言語" },
  { value: "certification", label: "資格" },
  { value: "specialty", label: "得意分野" },
  { value: "other", label: "その他" },
];

export function StaffProfileTab({ staffId }: StaffProfileTabProps) {
  const [profile, setProfile] = useState<StaffProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 編集中のデータ
  const [editData, setEditData] = useState({
    display_name: "",
    greeting: "",
    bio: "",
    lesson_style: "",
    career: "",
    origin_country: "",
    residence_country: "",
    communication_tool: "",
    communication_url: "",
    is_public: false,
    is_bookable: false,
    admin_comment: "",
  });

  // スキル追加モーダル
  const [skillModalOpen, setSkillModalOpen] = useState(false);
  const [newSkill, setNewSkill] = useState({
    category: "specialty",
    name: "",
    level: 3,
    color: "blue",
  });

  useEffect(() => {
    loadProfile();
  }, [staffId]);

  async function loadProfile() {
    setLoading(true);
    setError(null);
    try {
      // まずプロフィールを取得（employee_idから）
      const response = await apiClient.get<{ results?: StaffProfile[] } | StaffProfile[]>(`/hr/profiles/?employee_id=${staffId}`);
      const profiles = Array.isArray(response) ? response : (response.results || []);

      if (profiles.length > 0) {
        const p = profiles[0];
        setProfile(p);
        setEditData({
          display_name: p.display_name || "",
          greeting: p.greeting || "",
          bio: p.bio || "",
          lesson_style: p.lesson_style || "",
          career: p.career || "",
          origin_country: p.origin_country || "",
          residence_country: p.residence_country || "",
          communication_tool: p.communication_tool || "",
          communication_url: p.communication_url || "",
          is_public: p.is_public || false,
          is_bookable: p.is_bookable || false,
          admin_comment: p.admin_comment || "",
        });
      } else {
        // プロフィールがない場合は新規作成
        setProfile(null);
      }
    } catch (err) {
      console.error("Failed to load profile:", err);
      setError("プロフィールの読み込みに失敗しました");
    }
    setLoading(false);
  }

  async function handleSave() {
    if (!profile) return;
    setSaving(true);
    try {
      await apiClient.patch<StaffProfile>(`/hr/profiles/${profile.id}/`, editData);
      await loadProfile();
    } catch (err) {
      console.error("Failed to save profile:", err);
      setError("保存に失敗しました");
    }
    setSaving(false);
  }

  async function handleAddSkill() {
    if (!profile || !newSkill.name.trim()) return;
    try {
      await apiClient.post<StaffSkill>(`/hr/profiles/${profile.id}/add_skill/`, newSkill);
      setSkillModalOpen(false);
      setNewSkill({ category: "specialty", name: "", level: 3, color: "blue" });
      await loadProfile();
    } catch (err) {
      console.error("Failed to add skill:", err);
    }
  }

  async function handleRemoveSkill(skillId: string) {
    if (!profile) return;
    try {
      await apiClient.delete<void>(`/hr/profiles/${profile.id}/remove_skill/${skillId}/`);
      await loadProfile();
    } catch (err) {
      console.error("Failed to remove skill:", err);
    }
  }

  function getSkillColor(color: string) {
    const found = skillColors.find((c) => c.value === color);
    return found?.class || "bg-gray-500";
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 text-red-600 rounded-lg">
        {error}
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="p-4 text-center text-gray-500">
        <p>プロフィールがまだ作成されていません</p>
        <p className="text-sm mt-1">社員がログインしてプロフィールを作成すると表示されます</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 基本情報サマリー */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white text-xl font-bold">
            {profile.display_name?.substring(0, 2) || profile.employee_name?.substring(0, 2) || "??"}
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-bold text-gray-900">
              {profile.display_name || profile.employee_name}
            </h3>
            <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
              <span className="flex items-center gap-1">
                <Star className="w-4 h-4 text-yellow-500" />
                {profile.rating?.toFixed(1) || "0.0"} ({profile.review_count}件)
              </span>
              <span>レッスン {profile.lesson_count}回</span>
              <span>{profile.points}pt</span>
            </div>
          </div>
          <div className="flex gap-2">
            {profile.is_public && (
              <Badge className="bg-green-100 text-green-800">公開中</Badge>
            )}
            {profile.is_bookable && (
              <Badge className="bg-blue-100 text-blue-800">予約可</Badge>
            )}
          </div>
        </div>
      </div>

      {/* スキルタグ */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-gray-700">スキル・得意分野</h4>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setSkillModalOpen(true)}
          >
            <Plus className="w-4 h-4 mr-1" />
            追加
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {profile.skills?.length > 0 ? (
            profile.skills.map((skill) => (
              <Badge
                key={skill.id}
                className={`${getSkillColor(skill.color)} text-white group cursor-pointer`}
              >
                {skill.name}
                <button
                  className="ml-1 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={() => handleRemoveSkill(skill.id)}
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))
          ) : (
            <span className="text-sm text-gray-500">スキルが登録されていません</span>
          )}
        </div>
      </div>

      {/* プロフィール編集フォーム */}
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="display_name">表示名</Label>
            <Input
              id="display_name"
              value={editData.display_name}
              onChange={(e) => setEditData({ ...editData, display_name: e.target.value })}
              placeholder="○○先生"
            />
          </div>
          <div>
            <Label htmlFor="communication_tool">通話ツール</Label>
            <Select
              value={editData.communication_tool}
              onValueChange={(v) => setEditData({ ...editData, communication_tool: v })}
            >
              <SelectTrigger>
                <SelectValue placeholder="選択..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="google_meet">Google Meet</SelectItem>
                <SelectItem value="zoom">Zoom</SelectItem>
                <SelectItem value="skype">Skype</SelectItem>
                <SelectItem value="teams">Microsoft Teams</SelectItem>
                <SelectItem value="line">LINE</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="origin_country">出身国</Label>
            <Input
              id="origin_country"
              value={editData.origin_country}
              onChange={(e) => setEditData({ ...editData, origin_country: e.target.value })}
              placeholder="日本"
            />
          </div>
          <div>
            <Label htmlFor="residence_country">居住国</Label>
            <Input
              id="residence_country"
              value={editData.residence_country}
              onChange={(e) => setEditData({ ...editData, residence_country: e.target.value })}
              placeholder="日本"
            />
          </div>
        </div>

        <div>
          <Label htmlFor="greeting">ごあいさつ</Label>
          <Textarea
            id="greeting"
            value={editData.greeting}
            onChange={(e) => setEditData({ ...editData, greeting: e.target.value })}
            placeholder="はじめまして！..."
            rows={3}
          />
        </div>

        <div>
          <Label htmlFor="bio">自己紹介</Label>
          <Textarea
            id="bio"
            value={editData.bio}
            onChange={(e) => setEditData({ ...editData, bio: e.target.value })}
            placeholder="経験や得意分野について..."
            rows={4}
          />
        </div>

        <div>
          <Label htmlFor="lesson_style">レッスン内容・スタイル</Label>
          <Textarea
            id="lesson_style"
            value={editData.lesson_style}
            onChange={(e) => setEditData({ ...editData, lesson_style: e.target.value })}
            placeholder="レッスンの進め方について..."
            rows={3}
          />
        </div>

        <div>
          <Label htmlFor="career">経歴・趣味</Label>
          <Textarea
            id="career"
            value={editData.career}
            onChange={(e) => setEditData({ ...editData, career: e.target.value })}
            placeholder="学歴、資格、趣味など..."
            rows={3}
          />
        </div>

        <div>
          <Label htmlFor="admin_comment">事務局より（管理者のみ編集可）</Label>
          <Textarea
            id="admin_comment"
            value={editData.admin_comment}
            onChange={(e) => setEditData({ ...editData, admin_comment: e.target.value })}
            placeholder="事務局からのコメント..."
            rows={2}
          />
        </div>

        {/* 公開設定 */}
        <div className="flex items-center gap-6 pt-4 border-t">
          <div className="flex items-center gap-2">
            <Switch
              id="is_public"
              checked={editData.is_public}
              onCheckedChange={(c) => setEditData({ ...editData, is_public: c })}
            />
            <Label htmlFor="is_public">プロフィール公開</Label>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              id="is_bookable"
              checked={editData.is_bookable}
              onCheckedChange={(c) => setEditData({ ...editData, is_bookable: c })}
            />
            <Label htmlFor="is_bookable">予約受付可</Label>
          </div>
        </div>

        <div className="flex justify-end pt-4">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                保存
              </>
            )}
          </Button>
        </div>
      </div>

      {/* スキル追加モーダル */}
      <Dialog open={skillModalOpen} onOpenChange={setSkillModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>スキルを追加</DialogTitle>
            <DialogDescription>
              講師のスキルや得意分野を追加します
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>カテゴリ</Label>
              <Select
                value={newSkill.category}
                onValueChange={(v) => setNewSkill({ ...newSkill, category: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {skillCategories.map((cat) => (
                    <SelectItem key={cat.value} value={cat.value}>
                      {cat.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>スキル名</Label>
              <Input
                value={newSkill.name}
                onChange={(e) => setNewSkill({ ...newSkill, name: e.target.value })}
                placeholder="例: 英会話、数学、プログラミング"
              />
            </div>
            <div>
              <Label>レベル (1-5)</Label>
              <Select
                value={String(newSkill.level)}
                onValueChange={(v) => setNewSkill({ ...newSkill, level: parseInt(v) })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5].map((l) => (
                    <SelectItem key={l} value={String(l)}>
                      {"★".repeat(l)}{"☆".repeat(5 - l)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>表示色</Label>
              <div className="flex gap-2 mt-2">
                {skillColors.map((color) => (
                  <button
                    key={color.value}
                    onClick={() => setNewSkill({ ...newSkill, color: color.value })}
                    className={`w-8 h-8 rounded-full ${color.class} ${
                      newSkill.color === color.value ? "ring-2 ring-offset-2 ring-gray-400" : ""
                    }`}
                    title={color.label}
                  />
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSkillModalOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleAddSkill} disabled={!newSkill.name.trim()}>
              追加
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
