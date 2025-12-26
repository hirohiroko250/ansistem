"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import {
  User,
  Bell,
  Shield,
  Palette,
  LogOut,
  Users,
  ChevronRight,
  Loader2,
  Save,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import Link from "next/link";
import apiClient from "@/lib/api/client";

interface Profile {
  id: string;
  email: string;
  user_type: string;
  role: string;
  last_name: string;
  first_name: string;
  full_name: string;
  display_name: string;
  phone: string;
  profile_image_url: string;
}

interface NotificationSettings {
  newMessage: boolean;
  taskReminder: boolean;
  classReminder: boolean;
}

interface DisplaySettings {
  darkMode: boolean;
  compactView: boolean;
}

export default function SettingsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // プロフィールフォーム
  const [formData, setFormData] = useState({
    last_name: "",
    first_name: "",
    display_name: "",
    phone: "",
  });

  // パスワード変更フォーム
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    new_password_confirm: "",
  });

  // 通知設定（ローカルストレージ）
  const [notifications, setNotifications] = useState<NotificationSettings>({
    newMessage: true,
    taskReminder: true,
    classReminder: true,
  });

  // 表示設定（ローカルストレージ）
  const [display, setDisplay] = useState<DisplaySettings>({
    darkMode: false,
    compactView: false,
  });

  // プロフィール読み込み
  useEffect(() => {
    loadProfile();
    loadLocalSettings();
  }, []);

  async function loadProfile() {
    try {
      setLoading(true);
      const data = await apiClient.get<Profile>("/users/profile/");
      setProfile(data);
      setFormData({
        last_name: data.last_name || "",
        first_name: data.first_name || "",
        display_name: data.display_name || "",
        phone: data.phone || "",
      });
    } catch (error) {
      console.error("Failed to load profile:", error);
      showMessage("error", "プロフィールの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }

  function loadLocalSettings() {
    // 通知設定
    const savedNotifications = localStorage.getItem("notification_settings");
    if (savedNotifications) {
      setNotifications(JSON.parse(savedNotifications));
    }

    // 表示設定
    const savedDisplay = localStorage.getItem("display_settings");
    if (savedDisplay) {
      setDisplay(JSON.parse(savedDisplay));
    }
  }

  function showMessage(type: "success" | "error", text: string) {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  }

  // プロフィール保存
  async function handleSaveProfile() {
    try {
      setSaving(true);
      const data = await apiClient.patch<Profile>("/users/profile/", formData);
      setProfile(data);
      showMessage("success", "プロフィールを保存しました");
    } catch (error) {
      console.error("Failed to save profile:", error);
      showMessage("error", "プロフィールの保存に失敗しました");
    } finally {
      setSaving(false);
    }
  }

  // パスワード変更
  async function handleChangePassword() {
    if (passwordForm.new_password !== passwordForm.new_password_confirm) {
      showMessage("error", "新しいパスワードが一致しません");
      return;
    }

    if (passwordForm.new_password.length < 8) {
      showMessage("error", "パスワードは8文字以上で入力してください");
      return;
    }

    try {
      setChangingPassword(true);
      await apiClient.post("/users/profile/", passwordForm);
      setPasswordForm({
        current_password: "",
        new_password: "",
        new_password_confirm: "",
      });
      showMessage("success", "パスワードを変更しました");
    } catch (error: any) {
      console.error("Failed to change password:", error);
      const errorMsg = error?.data?.error || "パスワードの変更に失敗しました";
      showMessage("error", errorMsg);
    } finally {
      setChangingPassword(false);
    }
  }

  // 通知設定保存
  function handleNotificationChange(key: keyof NotificationSettings, value: boolean) {
    const newSettings = { ...notifications, [key]: value };
    setNotifications(newSettings);
    localStorage.setItem("notification_settings", JSON.stringify(newSettings));
  }

  // 表示設定保存
  function handleDisplayChange(key: keyof DisplaySettings, value: boolean) {
    const newSettings = { ...display, [key]: value };
    setDisplay(newSettings);
    localStorage.setItem("display_settings", JSON.stringify(newSettings));
  }

  const handleLogout = () => {
    apiClient.setToken(null);
    router.push("/login");
  };

  return (
    <ThreePaneLayout>
      <div className="p-6 max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">設定</h1>
          <p className="text-gray-600">アカウントとアプリケーションの設定</p>
        </div>

        {/* メッセージ表示 */}
        {message && (
          <div
            className={`mb-4 p-4 rounded-lg flex items-center gap-2 ${
              message.type === "success"
                ? "bg-green-50 text-green-800 border border-green-200"
                : "bg-red-50 text-red-800 border border-red-200"
            }`}
          >
            {message.type === "success" ? (
              <CheckCircle className="w-5 h-5" />
            ) : (
              <AlertCircle className="w-5 h-5" />
            )}
            {message.text}
          </div>
        )}

        <div className="space-y-6">
          {/* プロフィール設定 */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <User className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">
                プロフィール設定
              </h2>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="last_name">姓</Label>
                    <Input
                      id="last_name"
                      value={formData.last_name}
                      onChange={(e) =>
                        setFormData({ ...formData, last_name: e.target.value })
                      }
                      placeholder="山田"
                      className="mt-2"
                    />
                  </div>
                  <div>
                    <Label htmlFor="first_name">名</Label>
                    <Input
                      id="first_name"
                      value={formData.first_name}
                      onChange={(e) =>
                        setFormData({ ...formData, first_name: e.target.value })
                      }
                      placeholder="太郎"
                      className="mt-2"
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="email">メールアドレス</Label>
                  <Input
                    id="email"
                    type="email"
                    value={profile?.email || ""}
                    disabled
                    className="mt-2 bg-gray-50"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    メールアドレスは変更できません
                  </p>
                </div>
                <div>
                  <Label htmlFor="display_name">表示名</Label>
                  <Input
                    id="display_name"
                    value={formData.display_name}
                    onChange={(e) =>
                      setFormData({ ...formData, display_name: e.target.value })
                    }
                    placeholder="ニックネーム"
                    className="mt-2"
                  />
                </div>
                <div>
                  <Label htmlFor="phone">電話番号</Label>
                  <Input
                    id="phone"
                    value={formData.phone}
                    onChange={(e) =>
                      setFormData({ ...formData, phone: e.target.value })
                    }
                    placeholder="090-1234-5678"
                    className="mt-2"
                  />
                </div>
                <div>
                  <Label htmlFor="role">役職</Label>
                  <Input
                    id="role"
                    value={profile?.role || ""}
                    disabled
                    className="mt-2 bg-gray-50"
                  />
                </div>
                <Button onClick={handleSaveProfile} disabled={saving}>
                  {saving ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <Save className="w-4 h-4 mr-2" />
                  )}
                  プロフィールを保存
                </Button>
              </div>
            )}
          </Card>

          {/* 通知設定 */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <Bell className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">通知設定</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label>新しいメッセージ</Label>
                  <p className="text-sm text-gray-500">
                    新しいメッセージが届いたときに通知
                  </p>
                </div>
                <Switch
                  checked={notifications.newMessage}
                  onCheckedChange={(v) => handleNotificationChange("newMessage", v)}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>タスクリマインダー</Label>
                  <p className="text-sm text-gray-500">
                    タスクの期限が近づいたときに通知
                  </p>
                </div>
                <Switch
                  checked={notifications.taskReminder}
                  onCheckedChange={(v) => handleNotificationChange("taskReminder", v)}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>授業リマインダー</Label>
                  <p className="text-sm text-gray-500">授業の開始前に通知</p>
                </div>
                <Switch
                  checked={notifications.classReminder}
                  onCheckedChange={(v) => handleNotificationChange("classReminder", v)}
                />
              </div>
            </div>
          </Card>

          {/* 表示設定 */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <Palette className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">表示設定</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label>ダークモード</Label>
                  <p className="text-sm text-gray-500">
                    ダークテーマを有効にする
                  </p>
                </div>
                <Switch
                  checked={display.darkMode}
                  onCheckedChange={(v) => handleDisplayChange("darkMode", v)}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>コンパクト表示</Label>
                  <p className="text-sm text-gray-500">
                    リストアイテムを密に表示
                  </p>
                </div>
                <Switch
                  checked={display.compactView}
                  onCheckedChange={(v) => handleDisplayChange("compactView", v)}
                />
              </div>
            </div>
          </Card>

          {/* セキュリティ */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <Shield className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">
                セキュリティ
              </h2>
            </div>
            <div className="space-y-4">
              <div>
                <Label htmlFor="current-password">現在のパスワード</Label>
                <Input
                  id="current-password"
                  type="password"
                  value={passwordForm.current_password}
                  onChange={(e) =>
                    setPasswordForm({
                      ...passwordForm,
                      current_password: e.target.value,
                    })
                  }
                  className="mt-2"
                />
              </div>
              <div>
                <Label htmlFor="new-password">新しいパスワード</Label>
                <Input
                  id="new-password"
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(e) =>
                    setPasswordForm({
                      ...passwordForm,
                      new_password: e.target.value,
                    })
                  }
                  className="mt-2"
                />
                <p className="text-xs text-gray-500 mt-1">8文字以上</p>
              </div>
              <div>
                <Label htmlFor="confirm-password">
                  新しいパスワード（確認）
                </Label>
                <Input
                  id="confirm-password"
                  type="password"
                  value={passwordForm.new_password_confirm}
                  onChange={(e) =>
                    setPasswordForm({
                      ...passwordForm,
                      new_password_confirm: e.target.value,
                    })
                  }
                  className="mt-2"
                />
              </div>
              <Button
                onClick={handleChangePassword}
                disabled={
                  changingPassword ||
                  !passwordForm.current_password ||
                  !passwordForm.new_password ||
                  !passwordForm.new_password_confirm
                }
              >
                {changingPassword ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Shield className="w-4 h-4 mr-2" />
                )}
                パスワードを変更
              </Button>
            </div>
          </Card>

          {/* 権限管理 */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <Users className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">権限管理</h2>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              役職ごとの機能アクセス権限を設定
            </p>
            <Link href="/settings/permissions">
              <Button variant="outline" className="w-full justify-between">
                <span>権限設定を開く</span>
                <ChevronRight className="w-4 h-4" />
              </Button>
            </Link>
          </Card>

          {/* ログアウト */}
          <Card className="p-6 border-red-200 bg-red-50">
            <div className="flex items-center gap-3 mb-4">
              <LogOut className="w-5 h-5 text-red-600" />
              <h2 className="text-lg font-semibold text-red-900">ログアウト</h2>
            </div>
            <p className="text-sm text-red-700 mb-4">
              ログアウトすると、再度ログインが必要になります。
            </p>
            <Button variant="destructive" onClick={handleLogout}>
              <LogOut className="w-4 h-4 mr-2" />
              ログアウト
            </Button>
          </Card>
        </div>
      </div>
    </ThreePaneLayout>
  );
}
