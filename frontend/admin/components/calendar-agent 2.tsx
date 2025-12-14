"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Bot,
  X,
  Send,
  ArrowLeftRight,
  CalendarOff,
  Download,
  Upload,
  Loader2,
  CheckCircle,
  AlertCircle,
  ChevronRight,
  Sparkles,
} from "lucide-react";
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

interface CalendarAgentProps {
  onABSwap?: (params: { calendarPattern: string; date: string; newType?: string }) => Promise<boolean>;
  onSetClosure?: (params: { schoolId: string; date: string; reason?: string }) => Promise<boolean>;
  onExportCSV?: () => Promise<string | null>;
  onImportCSV?: (file: File) => Promise<boolean>;
  selectedSchool?: string;
  selectedDate?: string;
  selectedEvent?: { calendarPattern?: string; lessonType?: string } | null;
}

const quickActions: QuickAction[] = [
  {
    id: "ab-swap",
    label: "ABスワップ",
    icon: <ArrowLeftRight className="w-4 h-4" />,
    description: "レッスンタイプをA↔B切り替え",
    command: "ABスワップ",
  },
  {
    id: "set-closure",
    label: "休校設定",
    icon: <CalendarOff className="w-4 h-4" />,
    description: "指定日を休校に設定",
    command: "休校設定",
  },
  {
    id: "export-csv",
    label: "CSVエクスポート",
    icon: <Download className="w-4 h-4" />,
    description: "カレンダーデータをCSV出力",
    command: "CSVエクスポート",
  },
  {
    id: "import-csv",
    label: "CSVインポート",
    icon: <Upload className="w-4 h-4" />,
    description: "CSVからカレンダーを更新",
    command: "CSVインポート",
  },
];

export default function CalendarAgent({
  onABSwap,
  onSetClosure,
  onExportCSV,
  onImportCSV,
  selectedSchool,
  selectedDate,
  selectedEvent,
}: CalendarAgentProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<AgentMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "カレンダーエージェントです。何をお手伝いしましょうか？",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeCommand, setActiveCommand] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto scroll to bottom
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
      // ABスワップ
      if (lowerCommand.includes("abスワップ") || lowerCommand.includes("ab swap") || lowerCommand.includes("スワップ")) {
        if (!selectedEvent?.calendarPattern) {
          addMessage({
            role: "assistant",
            content: "ABスワップを実行するには、カレンダーでイベントを選択してください。",
            status: "error",
          });
        } else {
          const msgId = addMessage({
            role: "assistant",
            content: `ABスワップを実行中... (${selectedEvent.lessonType} → ${selectedEvent.lessonType === "A" ? "B" : "A"})`,
            status: "pending",
          });

          if (onABSwap && selectedDate) {
            const success = await onABSwap({
              calendarPattern: selectedEvent.calendarPattern,
              date: selectedDate,
            });

            updateMessage(msgId, {
              content: success
                ? `ABスワップが完了しました。(${selectedEvent.lessonType} → ${selectedEvent.lessonType === "A" ? "B" : "A"})`
                : "ABスワップに失敗しました。",
              status: success ? "success" : "error",
            });
          }
        }
      }
      // 休校設定
      else if (lowerCommand.includes("休校") || lowerCommand.includes("closure")) {
        if (!selectedSchool || !selectedDate) {
          addMessage({
            role: "assistant",
            content: "休校設定を行うには、校舎と日付を選択してください。",
            status: "error",
          });
        } else {
          setActiveCommand("closure");
          addMessage({
            role: "assistant",
            content: `${selectedDate} を休校に設定しますか？`,
            actions: [
              {
                id: "confirm-closure",
                label: "休校に設定",
                onClick: async () => {
                  const msgId = addMessage({
                    role: "assistant",
                    content: "休校設定を実行中...",
                    status: "pending",
                  });

                  if (onSetClosure) {
                    const success = await onSetClosure({
                      schoolId: selectedSchool,
                      date: selectedDate,
                    });

                    updateMessage(msgId, {
                      content: success
                        ? `${selectedDate} を休校に設定しました。`
                        : "休校設定に失敗しました。",
                      status: success ? "success" : "error",
                    });
                  }
                  setActiveCommand(null);
                },
              },
              {
                id: "cancel-closure",
                label: "キャンセル",
                variant: "outline",
                onClick: () => {
                  addMessage({
                    role: "assistant",
                    content: "休校設定をキャンセルしました。",
                  });
                  setActiveCommand(null);
                },
              },
            ],
          });
        }
      }
      // CSVエクスポート
      else if (lowerCommand.includes("エクスポート") || lowerCommand.includes("export") || lowerCommand.includes("出力")) {
        const msgId = addMessage({
          role: "assistant",
          content: "CSVエクスポートを実行中...",
          status: "pending",
        });

        if (onExportCSV) {
          const url = await onExportCSV();

          updateMessage(msgId, {
            content: url
              ? "CSVエクスポートが完了しました。ダウンロードが開始されます。"
              : "CSVエクスポートに失敗しました。",
            status: url ? "success" : "error",
          });

          if (url) {
            // Trigger download
            const link = document.createElement("a");
            link.href = url;
            link.download = `calendar_export_${new Date().toISOString().split("T")[0]}.csv`;
            link.click();
          }
        }
      }
      // CSVインポート
      else if (lowerCommand.includes("インポート") || lowerCommand.includes("import") || lowerCommand.includes("取込")) {
        addMessage({
          role: "assistant",
          content: "CSVファイルを選択してください。",
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
      // ヘルプ
      else if (lowerCommand.includes("ヘルプ") || lowerCommand.includes("help") || lowerCommand === "?") {
        addMessage({
          role: "assistant",
          content: `利用可能なコマンド:
• ABスワップ - 選択したイベントのA/Bタイプを切り替え
• 休校設定 - 選択した日を休校に設定
• CSVエクスポート - カレンダーデータをCSV出力
• CSVインポート - CSVからカレンダーを更新

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
      const success = await onImportCSV(file);

      updateMessage(msgId, {
        content: success
          ? `「${file.name}」のインポートが完了しました。`
          : `「${file.name}」のインポートに失敗しました。`,
        status: success ? "success" : "error",
      });
    }

    // Reset file input
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
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFileSelect}
      />

      {/* Floating button */}
      <Button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-lg z-50 transition-all duration-300",
          isOpen
            ? "bg-gray-600 hover:bg-gray-700"
            : "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
        )}
      >
        {isOpen ? (
          <X className="w-6 h-6" />
        ) : (
          <Bot className="w-6 h-6" />
        )}
      </Button>

      {/* Chat panel */}
      {isOpen && (
        <Card className="fixed bottom-24 right-6 w-96 h-[500px] shadow-2xl z-50 flex flex-col overflow-hidden border-2">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <h3 className="font-bold">カレンダーエージェント</h3>
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
                      ? "bg-blue-600 text-white"
                      : "bg-white shadow-sm border"
                  )}
                >
                  <div className="flex items-start gap-2">
                    {message.status === "pending" && (
                      <Loader2 className="w-4 h-4 animate-spin text-blue-500 flex-shrink-0 mt-0.5" />
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
                  <div className="w-8 h-8 rounded-lg bg-gray-100 group-hover:bg-blue-100 flex items-center justify-center text-gray-600 group-hover:text-blue-600 transition-colors">
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
                className="h-9 w-9 p-0"
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
