"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  X,
  Send,
  Download,
  Upload,
  Loader2,
  CheckCircle,
  AlertCircle,
  ChevronRight,
  Edit,
  Trash2,
  RefreshCw,
} from "lucide-react";
import Image from "next/image";
import { cn } from "@/lib/utils";

export type AgentMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  status?: "pending" | "success" | "error";
  actions?: AgentAction[];
};

export type AgentAction = {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  variant?: "default" | "outline" | "destructive";
};

export type QuickAction = {
  id: string;
  label: string;
  icon: React.ReactNode;
  description: string;
  command: string;
};

interface ContractAgentProps {
  onExportCSV?: (type: "contracts" | "items" | "discounts") => Promise<string | null>;
  onImportCSV?: (type: "contracts" | "items" | "discounts", file: File) => Promise<{ success: boolean; imported: number; errors: string[] }>;
  onBulkUpdate?: (type: "contracts" | "items" | "discounts", ids: string[], updates: Record<string, unknown>) => Promise<boolean>;
  onRefreshData?: () => void;
  selectedIds?: string[];
  activeTab?: string;
}

const quickActions: QuickAction[] = [
  {
    id: "export-csv",
    label: "CSVエクスポート",
    icon: <Download className="w-4 h-4" />,
    description: "データをCSV出力",
    command: "CSVエクスポート",
  },
  {
    id: "import-csv",
    label: "CSVインポート",
    icon: <Upload className="w-4 h-4" />,
    description: "CSVからデータを更新",
    command: "CSVインポート",
  },
  {
    id: "bulk-edit",
    label: "一括編集",
    icon: <Edit className="w-4 h-4" />,
    description: "選択項目を一括変更",
    command: "一括編集",
  },
  {
    id: "refresh",
    label: "データ更新",
    icon: <RefreshCw className="w-4 h-4" />,
    description: "最新データを取得",
    command: "更新",
  },
];

export default function ContractAgent({
  onExportCSV,
  onImportCSV,
  onBulkUpdate,
  onRefreshData,
  selectedIds = [],
  activeTab = "contracts",
}: ContractAgentProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<AgentMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "契約管理エージェントです。契約・生徒商品・割引の一括操作をお手伝いします。",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importType, setImportType] = useState<"contracts" | "items" | "discounts">("contracts");

  const tabLabels: Record<string, string> = {
    contracts: "契約",
    items: "生徒商品",
    discounts: "割引",
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = (message: Omit<AgentMessage, "id" | "timestamp">) => {
    const newMessage: AgentMessage = {
      ...message,
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMessage]);
    return newMessage.id;
  };

  const updateMessage = (id: string, updates: Partial<AgentMessage>) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === id ? { ...msg, ...updates } : msg))
    );
  };

  const handleCommand = async (command: string) => {
    setIsProcessing(true);
    addMessage({ role: "user", content: command });

    const lowerCommand = command.toLowerCase();

    try {
      // CSVエクスポート
      if (lowerCommand.includes("エクスポート") || lowerCommand.includes("export") || lowerCommand.includes("出力")) {
        const type = activeTab as "contracts" | "items" | "discounts";
        addMessage({
          role: "assistant",
          content: `${tabLabels[type]}データをCSVでエクスポートします。`,
          actions: [
            {
              id: "export-now",
              label: "エクスポート実行",
              icon: <Download className="w-4 h-4" />,
              onClick: async () => {
                const msgId = addMessage({
                  role: "assistant",
                  content: "CSVエクスポートを実行中...",
                  status: "pending",
                });

                if (onExportCSV) {
                  const url = await onExportCSV(type);

                  updateMessage(msgId, {
                    content: url
                      ? "CSVエクスポートが完了しました。ダウンロードが開始されます。"
                      : "CSVエクスポートに失敗しました。",
                    status: url ? "success" : "error",
                  });

                  if (url) {
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = `${type}_export_${new Date().toISOString().split("T")[0]}.csv`;
                    link.click();
                  }
                }
              },
            },
            {
              id: "cancel-export",
              label: "キャンセル",
              variant: "outline",
              onClick: () => {
                addMessage({
                  role: "assistant",
                  content: "エクスポートをキャンセルしました。",
                });
              },
            },
          ],
        });
      }
      // CSVインポート
      else if (lowerCommand.includes("インポート") || lowerCommand.includes("import") || lowerCommand.includes("取込")) {
        setImportType(activeTab as "contracts" | "items" | "discounts");
        addMessage({
          role: "assistant",
          content: `${tabLabels[activeTab]}データをCSVからインポートします。ファイルを選択してください。`,
          actions: [
            {
              id: "select-file",
              label: "ファイルを選択",
              icon: <Upload className="w-4 h-4" />,
              onClick: () => {
                fileInputRef.current?.click();
              },
            },
          ],
        });
      }
      // 一括編集
      else if (lowerCommand.includes("一括") || lowerCommand.includes("bulk") || lowerCommand.includes("編集")) {
        if (selectedIds.length === 0) {
          addMessage({
            role: "assistant",
            content: "一括編集を行うには、テーブルから対象の行を選択してください。\n\n現在、行選択機能は未実装です。今後のアップデートでご利用いただけるようになります。",
            status: "error",
          });
        } else {
          addMessage({
            role: "assistant",
            content: `${selectedIds.length}件の${tabLabels[activeTab]}を選択中です。どのような変更を行いますか？\n\n例: ステータスを「有効」に変更、金額を10%増加 など`,
          });
        }
      }
      // データ更新
      else if (lowerCommand.includes("更新") || lowerCommand.includes("refresh") || lowerCommand.includes("リロード")) {
        if (onRefreshData) {
          const msgId = addMessage({
            role: "assistant",
            content: "データを更新中...",
            status: "pending",
          });

          onRefreshData();

          setTimeout(() => {
            updateMessage(msgId, {
              content: "データを更新しました。",
              status: "success",
            });
          }, 1000);
        }
      }
      // ヘルプ
      else if (lowerCommand.includes("ヘルプ") || lowerCommand.includes("help") || lowerCommand === "?") {
        addMessage({
          role: "assistant",
          content: `利用可能なコマンド:

• CSVエクスポート - 現在のタブのデータをCSV出力
• CSVインポート - CSVからデータを更新
• 一括編集 - 選択した項目を一括変更
• 更新 - データを再読み込み

下のクイックアクションボタンからも実行できます。`,
        });
      }
      // 不明なコマンド
      else {
        addMessage({
          role: "assistant",
          content: `「${command}」は認識できませんでした。「ヘルプ」と入力すると利用可能なコマンドを確認できます。`,
        });
      }
    } catch (error) {
      console.error("Command execution error:", error);
      addMessage({
        role: "assistant",
        content: "エラーが発生しました。もう一度お試しください。",
        status: "error",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const msgId = addMessage({
      role: "assistant",
      content: `「${file.name}」をインポート中...`,
      status: "pending",
    });

    if (onImportCSV) {
      const result = await onImportCSV(importType, file);

      updateMessage(msgId, {
        content: result.success
          ? `「${file.name}」のインポートが完了しました。\n${result.imported}件のデータを取り込みました。`
          : `「${file.name}」のインポートに失敗しました。\n${result.errors.join("\n")}`,
        status: result.success ? "success" : "error",
      });
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isProcessing) return;

    handleCommand(inputValue.trim());
    setInputValue("");
  };

  const handleQuickAction = (action: QuickAction) => {
    handleCommand(action.command);
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFileSelect}
      />

      {/* Floating button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-lg z-50 transition-all duration-300 flex items-center justify-center overflow-hidden",
          isOpen
            ? "bg-gray-600 hover:bg-gray-700"
            : "bg-transparent hover:scale-105"
        )}
      >
        {isOpen ? (
          <X className="w-6 h-6 text-white" />
        ) : (
          <Image
            src="/anlogo.svg"
            alt="アンシステム"
            width={56}
            height={56}
            className="w-full h-full object-cover"
          />
        )}
      </button>

      {/* Chat panel */}
      {isOpen && (
        <Card className="fixed bottom-24 right-6 w-96 h-[500px] shadow-2xl z-50 flex flex-col overflow-hidden border-2">
          {/* Header */}
          <div className="bg-gradient-to-r from-green-600 to-teal-600 text-white p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full overflow-hidden flex-shrink-0">
              <Image
                src="/anlogo.svg"
                alt="アンシステム"
                width={40}
                height={40}
                className="w-full h-full object-cover"
              />
            </div>
            <div className="flex-1">
              <h3 className="font-bold">契約管理エージェント</h3>
              <p className="text-xs text-white/80">AI アシスタント</p>
            </div>
            <Badge variant="secondary" className="bg-white/20 text-white text-[10px]">
              Beta
            </Badge>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex",
                  message.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                <div
                  className={cn(
                    "max-w-[85%] rounded-lg p-3",
                    message.role === "user"
                      ? "bg-green-600 text-white"
                      : "bg-white shadow-sm border"
                  )}
                >
                  <div className="flex items-start gap-2">
                    {message.status === "pending" && (
                      <Loader2 className="w-4 h-4 animate-spin text-green-500 flex-shrink-0 mt-0.5" />
                    )}
                    {message.status === "success" && (
                      <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                    )}
                    {message.status === "error" && (
                      <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      {message.actions && message.actions.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-3">
                          {message.actions.map((action) => (
                            <Button
                              key={action.id}
                              size="sm"
                              variant={action.variant || "default"}
                              onClick={action.onClick}
                              className="h-7 text-xs"
                            >
                              {action.icon && <span className="mr-1">{action.icon}</span>}
                              {action.label}
                            </Button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  <p className={cn(
                    "text-[10px] mt-1",
                    message.role === "user" ? "text-white/60" : "text-gray-400"
                  )}>
                    {message.timestamp.toLocaleTimeString("ja-JP", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick actions */}
          <div className="p-2 border-t bg-white">
            <div className="text-[10px] text-gray-500 mb-1.5 px-1">クイックアクション</div>
            <div className="grid grid-cols-2 gap-1.5">
              {quickActions.map((action) => (
                <button
                  key={action.id}
                  onClick={() => handleQuickAction(action)}
                  disabled={isProcessing}
                  className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 transition-colors text-left group disabled:opacity-50"
                >
                  <div className="w-8 h-8 rounded-lg bg-gray-100 group-hover:bg-green-100 flex items-center justify-center text-gray-600 group-hover:text-green-600 transition-colors">
                    {action.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-gray-700 truncate">
                      {action.label}
                    </div>
                    <div className="text-[10px] text-gray-400 truncate">
                      {action.description}
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500" />
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="p-3 border-t bg-white">
            <div className="flex gap-2">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="コマンドを入力..."
                disabled={isProcessing}
                className="flex-1 h-9 text-sm"
              />
              <Button
                type="submit"
                size="sm"
                disabled={!inputValue.trim() || isProcessing}
                className="h-9 w-9 p-0 bg-green-600 hover:bg-green-700"
              >
                {isProcessing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
          </form>
        </Card>
      )}
    </>
  );
}
