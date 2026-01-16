"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  CheckSquare,
  Users,
  UserCircle,
  UserCog,
  BookOpen,
  FileText,
  MessageSquare,
  MessagesSquare,
  Calendar,
  Settings,
  Receipt,
  Landmark,
  Library,
  ClipboardList,
  Newspaper,
  Shield,
} from "lucide-react";

const menuItems = [
  {
    name: "ダッシュボード",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    name: "カレンダー",
    href: "/calendar",
    icon: Calendar,
  },
  {
    name: "タスク",
    href: "/tasks",
    icon: CheckSquare,
  },
  {
    name: "生徒",
    href: "/students",
    icon: Users,
  },
  {
    name: "保護者",
    href: "/parents",
    icon: UserCircle,
  },
  {
    name: "スタッフ",
    href: "/staff",
    icon: UserCog,
  },
  {
    name: "授業",
    href: "/lessons",
    icon: BookOpen,
  },
  {
    name: "契約",
    href: "/contracts",
    icon: FileText,
  },
  {
    name: "請求",
    href: "/billing",
    icon: Receipt,
  },
  {
    name: "口座振替依頼",
    href: "/billing/bank-requests",
    icon: Landmark,
  },
  {
    name: "メッセージ",
    href: "/messages",
    icon: MessageSquare,
  },
  {
    name: "社内チャット",
    href: "/chat",
    icon: MessagesSquare,
  },
  {
    name: "フィード",
    href: "/feed",
    icon: Newspaper,
  },
  {
    name: "マニュアル",
    href: "/knowledge/manuals",
    icon: Library,
  },
  {
    name: "テンプレート",
    href: "/knowledge/templates",
    icon: ClipboardList,
  },
  {
    name: "権限管理",
    href: "/permissions",
    icon: Shield,
  },
  {
    name: "設定",
    href: "/settings",
    icon: Settings,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 h-screen bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-900">社員管理画面</h1>
      </div>
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");

          return (
            <Link
              key={item.href}
              href={item.href}
              prefetch={false}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-gray-100 text-gray-900"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              )}
            >
              <Icon className="w-5 h-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
