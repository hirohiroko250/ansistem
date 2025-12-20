"use client";

import { useRouter } from "next/navigation";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { User, Bell, Shield, Palette, LogOut } from "lucide-react";
import apiClient from "@/lib/api/client";

export default function SettingsPage() {
  const router = useRouter();

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

        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <User className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">
                プロフィール設定
              </h2>
            </div>
            <div className="space-y-4">
              <div>
                <Label htmlFor="name">名前</Label>
                <Input id="name" placeholder="山田太郎" className="mt-2" />
              </div>
              <div>
                <Label htmlFor="email">メールアドレス</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="yamada@example.com"
                  className="mt-2"
                />
              </div>
              <div>
                <Label htmlFor="role">役職</Label>
                <Input id="role" placeholder="講師" className="mt-2" />
              </div>
              <Button>プロフィールを保存</Button>
            </div>
          </Card>

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
                <Switch />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>タスクリマインダー</Label>
                  <p className="text-sm text-gray-500">
                    タスクの期限が近づいたときに通知
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>授業リマインダー</Label>
                  <p className="text-sm text-gray-500">
                    授業の開始前に通知
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
            </div>
          </Card>

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
                <Switch />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>コンパクト表示</Label>
                  <p className="text-sm text-gray-500">
                    リストアイテムを密に表示
                  </p>
                </div>
                <Switch />
              </div>
            </div>
          </Card>

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
                  className="mt-2"
                />
              </div>
              <div>
                <Label htmlFor="new-password">新しいパスワード</Label>
                <Input id="new-password" type="password" className="mt-2" />
              </div>
              <div>
                <Label htmlFor="confirm-password">
                  新しいパスワード（確認）
                </Label>
                <Input
                  id="confirm-password"
                  type="password"
                  className="mt-2"
                />
              </div>
              <Button>パスワードを変更</Button>
            </div>
          </Card>

          <Card className="p-6 border-red-200 bg-red-50">
            <div className="flex items-center gap-3 mb-4">
              <LogOut className="w-5 h-5 text-red-600" />
              <h2 className="text-lg font-semibold text-red-900">
                ログアウト
              </h2>
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
