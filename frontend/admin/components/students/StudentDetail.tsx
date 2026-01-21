"use client";

import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { Student, Guardian, Contract, Invoice, StudentDiscount } from "@/lib/api/types";
import { ContactLog, ChatLog, ChatMessage, createContactLog, ContactLogCreateData, getStudentContactLogs, getStudentQRCode, type QRCodeInfo } from "@/lib/api/staff";
import { QRCodeCanvas } from "qrcode.react";
import { getChannels, getMessages, sendMessage, getOrCreateChannelForGuardian, uploadFile, type Channel, type Message } from "@/lib/api/chat";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Phone,
  Edit,
  MessageCircle,
  FileText,
  CreditCard,
  PauseCircle,
  XCircle,
  User,
  Mail,
  MapPin,
  History,
  Users,
  Calendar,
  Pencil,
  ExternalLink,
  Plus,
  Loader2,
  Send,
  ChevronLeft,
  ArrowLeft,
  Image as ImageIcon,
  Paperclip,
  X,
  QrCode,
} from "lucide-react";
import { ContractEditDialog } from "./ContractEditDialog";
import { NewContractDialog } from "./NewContractDialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import apiClient from "@/lib/api/client";

interface ContractUpdate {
  discounts?: {
    id?: string;
    discount_name: string;
    amount: number;
    discount_unit: "yen" | "percent";
    is_new?: boolean;
    is_deleted?: boolean;
  }[];
  notes?: string;
}

interface StudentDetailProps {
  student: Student;
  parents: Guardian[];
  contracts: Contract[];
  invoices: Invoice[];
  contactLogs?: ContactLog[];
  chatLogs?: ChatLog[];
  messages?: ChatMessage[];
  siblings?: Student[];
  onSelectSibling?: (studentId: string) => void;
  onContractUpdate?: (contractId: string, updates: ContractUpdate) => Promise<void>;
  onRefresh?: () => void;
}

function getStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    registered: "登録済",
    enrolled: "在籍中",
    suspended: "休会中",
    withdrawn: "退会",
    graduated: "卒業",
  };
  return statusMap[status] || status;
}

function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    registered: "bg-yellow-100 text-yellow-800",
    enrolled: "bg-green-100 text-green-800",
    suspended: "bg-orange-100 text-orange-800",
    withdrawn: "bg-gray-100 text-gray-800",
    graduated: "bg-blue-100 text-blue-800",
  };
  return colorMap[status] || "bg-gray-100 text-gray-800";
}

function getContractStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    active: "有効",
    pending: "保留",
    cancelled: "解約",
    expired: "期限切れ",
  };
  return statusMap[status] || status;
}

function getInvoiceStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    draft: "下書き",
    pending: "未払い",
    unpaid: "未払い",
    partial: "一部入金",
    paid: "支払済",
    overdue: "延滞",
    cancelled: "キャンセル",
    confirmed: "確定",
  };
  return statusMap[status] || status;
}

function getContactTypeLabel(type: string): string {
  const typeMap: Record<string, string> = {
    PHONE_IN: "電話（受信）",
    PHONE_OUT: "電話（発信）",
    EMAIL_IN: "メール（受信）",
    EMAIL_OUT: "メール（送信）",
    VISIT: "来校",
    MEETING: "面談",
    ONLINE_MEETING: "オンライン面談",
    CHAT: "チャット",
    OTHER: "その他",
  };
  return typeMap[type] || type;
}

function getContactStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    OPEN: "対応中",
    PENDING: "保留",
    RESOLVED: "解決",
    CLOSED: "クローズ",
  };
  return statusMap[status] || status;
}

function getContactStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    OPEN: "bg-blue-100 text-blue-800",
    PENDING: "bg-yellow-100 text-yellow-800",
    RESOLVED: "bg-green-100 text-green-800",
    CLOSED: "bg-gray-100 text-gray-800",
  };
  return colorMap[status] || "bg-gray-100 text-gray-800";
}

function getSenderTypeLabel(type: string): string {
  const typeMap: Record<string, string> = {
    GUARDIAN: "保護者",
    STAFF: "スタッフ",
    BOT: "ボット",
  };
  return typeMap[type] || type;
}

export function StudentDetail({ student, parents, contracts, invoices, contactLogs = [], chatLogs = [], messages = [], siblings = [], onSelectSibling, onContractUpdate, onRefresh }: StudentDetailProps) {
  const [activeTab, setActiveTab] = useState("basic");
  const [editingContract, setEditingContract] = useState<Contract | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);

  // 新規契約登録ダイアログ
  const [newContractDialogOpen, setNewContractDialogOpen] = useState(false);

  // 生徒編集ダイアログ
  const [studentEditDialogOpen, setStudentEditDialogOpen] = useState(false);
  const [studentForm, setStudentForm] = useState({
    last_name: '',
    first_name: '',
    last_name_kana: '',
    first_name_kana: '',
    birth_date: '',
    gender: '',
    phone: '',
    email: '',
    school_name: '',
    notes: '',
  });

  // 保護者編集ダイアログ
  const [guardianEditDialogOpen, setGuardianEditDialogOpen] = useState(false);
  const [editingGuardian, setEditingGuardian] = useState<Guardian | null>(null);
  const [guardianForm, setGuardianForm] = useState({
    last_name: '',
    first_name: '',
    last_name_kana: '',
    first_name_kana: '',
    phone: '',
    phone_mobile: '',
    email: '',
    postal_code: '',
    prefecture: '',
    city: '',
    address1: '',
    address2: '',
  });

  // 休会・退会ダイアログ
  const [suspensionDialogOpen, setSuspensionDialogOpen] = useState(false);
  const [withdrawalDialogOpen, setWithdrawalDialogOpen] = useState(false);
  const [suspensionForm, setSuspensionForm] = useState({
    suspend_from: new Date().toISOString().split('T')[0],
    suspend_until: '',
    keep_seat: true,
    reason: 'other',
    reason_detail: '',
  });
  const [withdrawalForm, setWithdrawalForm] = useState({
    withdrawal_date: new Date().toISOString().split('T')[0],
    last_lesson_date: '',
    reason: 'other',
    reason_detail: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 休会・退会申請履歴
  const [suspensionRequests, setSuspensionRequests] = useState<any[]>([]);
  const [withdrawalRequests, setWithdrawalRequests] = useState<any[]>([]);

  // 対応履歴追加ダイアログ
  const [contactLogDialogOpen, setContactLogDialogOpen] = useState(false);
  const [contactLogForm, setContactLogForm] = useState<ContactLogCreateData>({
    contact_type: 'PHONE_OUT',
    subject: '',
    content: '',
    priority: 'NORMAL',
    status: 'RESOLVED',
  });
  const [isSubmittingContactLog, setIsSubmittingContactLog] = useState(false);
  const [localContactLogs, setLocalContactLogs] = useState<ContactLog[]>(contactLogs);

  // QRコード情報
  const [qrCodeInfo, setQrCodeInfo] = useState<QRCodeInfo | null>(null);
  const [qrCodeDialogOpen, setQrCodeDialogOpen] = useState(false);

  // 保護者画面を開く
  const [isOpeningGuardianView, setIsOpeningGuardianView] = useState(false);
  const [guardianAccountCreated, setGuardianAccountCreated] = useState<Record<string, boolean>>({});

  // 写真アップロード
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false);
  const photoInputRef = useRef<HTMLInputElement>(null);

  // contactLogs propが変わったらlocalContactLogsを更新
  useEffect(() => {
    setLocalContactLogs(contactLogs);
  }, [contactLogs]);

  // 生徒が変わったらQRコードを取得
  useEffect(() => {
    if (student?.id) {
      getStudentQRCode(student.id).then(setQrCodeInfo);
    }
  }, [student?.id]);

  // 対応履歴を追加
  const handleCreateContactLog = async () => {
    if (!contactLogForm.subject || !contactLogForm.content) {
      alert('件名と内容は必須です');
      return;
    }

    setIsSubmittingContactLog(true);
    try {
      const data: ContactLogCreateData = {
        ...contactLogForm,
        student_id: student.id,
        guardian_id: parents[0]?.id,
      };

      const result = await createContactLog(data);
      if (result) {
        // ローカルの対応履歴を更新
        const updatedLogs = await getStudentContactLogs(student.id);
        setLocalContactLogs(updatedLogs);

        // フォームをリセット
        setContactLogForm({
          contact_type: 'PHONE_OUT',
          subject: '',
          content: '',
          priority: 'NORMAL',
          status: 'RESOLVED',
        });
        setContactLogDialogOpen(false);
      }
    } catch (error) {
      console.error('対応履歴の追加に失敗しました:', error);
      alert('対応履歴の追加に失敗しました');
    } finally {
      setIsSubmittingContactLog(false);
    }
  };

  // 保護者画面を開く
  const openGuardianView = async (guardian: Guardian) => {
    const guardianId = guardian.id;
    if (!guardianId) return;

    setIsOpeningGuardianView(true);
    try {
      // アカウント未設定の場合は自動作成
      const hasAccount = guardian.has_account || guardian.hasAccount || guardianAccountCreated[guardianId];
      if (!hasAccount) {
        const hasContactInfo = guardian.email || guardian.phone || guardian.phone_mobile || guardian.phoneMobile;
        if (!hasContactInfo) {
          alert('電話番号またはメールアドレスが設定されていません。先に連絡先を登録してください。');
          setIsOpeningGuardianView(false);
          return;
        }
        // アカウントを自動作成
        await apiClient.post(`/students/guardians/${guardianId}/setup_account/`);
        setGuardianAccountCreated(prev => ({ ...prev, [guardianId]: true }));
      }

      // 保護者画面を開く
      const response = await apiClient.post<{ access: string; refresh: string }>('/auth/impersonate-guardian/', {
        guardian_id: guardianId
      });
      const customerUrl = process.env.NEXT_PUBLIC_CUSTOMER_URL || 'http://localhost:3000';
      const url = `${customerUrl}/auth/callback?access=${response.access}&refresh=${response.refresh}`;
      window.open(url, '_blank');
    } catch (error: any) {
      console.error('Failed to open guardian view:', error);
      const errorMessage = error.data?.error || error.message || '';
      alert(errorMessage || '保護者画面を開けませんでした。');
    } finally {
      setIsOpeningGuardianView(false);
    }
  };

  // 写真アップロード
  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // ファイルサイズチェック（5MB）
    if (file.size > 5 * 1024 * 1024) {
      alert('ファイルサイズは5MB以下にしてください');
      return;
    }

    // ファイル形式チェック
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      alert('JPG, PNG, GIF, WEBPファイルのみアップロード可能です');
      return;
    }

    setIsUploadingPhoto(true);
    try {
      const formData = new FormData();
      formData.append('photo', file);

      await apiClient.postFormData(`/students/${student.id}/upload-photo/`, formData);

      alert('写真をアップロードしました');
      onRefresh?.();
    } catch (error: any) {
      console.error('Photo upload error:', error);
      alert(error.data?.error || '写真のアップロードに失敗しました');
    } finally {
      setIsUploadingPhoto(false);
      // inputをリセット
      if (photoInputRef.current) {
        photoInputRef.current.value = '';
      }
    }
  };

  // 締め済み月の情報
  const [closedMonths, setClosedMonths] = useState<Set<string>>(new Set());

  // 保護者の預り金残高
  const [guardianBalance, setGuardianBalance] = useState<{
    balance: number;
    lastUpdated: string | null;
  } | null>(null);

  // 保護者の預り金残高を取得
  useEffect(() => {
    const fetchGuardianBalance = async () => {
      // 最初の保護者のIDを取得
      const guardian = parents[0];
      if (!guardian?.id) return;

      try {
        const data = await apiClient.get<{
          guardian_id: string;
          balance: number;
          last_updated: string | null;
        }>(`/billing/balances/by-guardian/${guardian.id}/`);
        setGuardianBalance({
          balance: data.balance || 0,
          lastUpdated: data.last_updated,
        });
      } catch (error) {
        // 残高レコードがない場合は0として扱う
        setGuardianBalance({ balance: 0, lastUpdated: null });
      }
    };
    if (parents.length > 0) {
      fetchGuardianBalance();
    }
  }, [parents]);

  // 締め済み月の情報を取得
  useEffect(() => {
    const fetchBillingDeadlines = async () => {
      try {
        const data = await apiClient.get<{
          months: { year: number; month: number; is_closed: boolean }[];
        }>('/billing/deadlines/status_list/');
        const closed = new Set<string>();
        if (data.months) {
          data.months.forEach((m) => {
            if (m.is_closed) {
              closed.add(`${m.year}-${String(m.month).padStart(2, '0')}`);
            }
          });
        }
        setClosedMonths(closed);
      } catch (error) {
        console.error('Failed to fetch billing deadlines:', error);
      }
    };
    fetchBillingDeadlines();
  }, []);

  // 日付から請求月を計算
  // 契約開始月 = 請求月（シンプルなロジック）
  // 例: 2月1日開始 → 2月請求
  const getBillingMonthForDate = (date: Date, closingDay: number = 10): { year: number; month: number } => {
    // 契約開始月をそのまま請求月とする
    return {
      year: date.getFullYear(),
      month: date.getMonth() + 1
    };
  };

  // 現在の作業対象請求月を計算（締日ロジック使用）
  // 締日（10日）を過ぎていれば翌々月が請求対象
  // 例: 12月26日 → 2月請求、12月5日 → 1月請求
  const getCurrentWorkingBillingPeriod = (closingDay: number = 10): { year: number; month: number } => {
    const today = new Date();
    const currentDay = today.getDate();
    const currentMonth = today.getMonth() + 1; // 1-12
    const currentYear = today.getFullYear();

    // 締日を過ぎていれば翌々月
    if (currentDay > closingDay) {
      if (currentMonth === 11) {
        // 11月 → 1月
        return { year: currentYear + 1, month: 1 };
      }
      if (currentMonth === 12) {
        // 12月 → 2月
        return { year: currentYear + 1, month: 2 };
      }
      return { year: currentYear, month: currentMonth + 2 };
    }
    // 締日以前なら翌月
    if (currentMonth === 12) {
      return { year: currentYear + 1, month: 1 };
    }
    return { year: currentYear, month: currentMonth + 1 };
  };

  const currentBillingPeriod = getCurrentWorkingBillingPeriod();

  // 契約の請求月を取得（表示用）
  const getContractBillingMonth = (contract: Contract): string => {
    const startDateStr = contract.start_date || (contract as any).startDate;
    if (!startDateStr) return "";
    const startDate = new Date(startDateStr);
    if (isNaN(startDate.getTime())) return "";
    const billing = getBillingMonthForDate(startDate);
    return `${billing.year}-${String(billing.month).padStart(2, '0')}`;
  };

  // 契約の請求月が締め済みかどうかをチェック
  const isContractPeriodClosed = (contract: Contract): boolean => {
    const startDateStr = contract.start_date || (contract as any).startDate;
    if (!startDateStr) return false;

    const startDate = new Date(startDateStr);
    if (isNaN(startDate.getTime())) return false;

    // 契約の開始日から請求期間を計算
    const contractBillingPeriod = getBillingMonthForDate(startDate);

    // 契約の請求期間が現在以降であれば編集可能
    const contractPeriodValue = contractBillingPeriod.year * 100 + contractBillingPeriod.month;
    const currentPeriodValue = currentBillingPeriod.year * 100 + currentBillingPeriod.month;

    if (contractPeriodValue >= currentPeriodValue) {
      return false; // 現在または将来の請求期間は編集可能
    }

    // 過去の請求期間は締め済みセットでチェック
    const monthKey = `${contractBillingPeriod.year}-${String(contractBillingPeriod.month).padStart(2, '0')}`;
    return closedMonths.has(monthKey);
  };

  // 休会・退会申請を取得
  useEffect(() => {
    const fetchRequests = async () => {
      try {
        const [suspensions, withdrawals] = await Promise.all([
          apiClient.get<{ results?: any[]; data?: any[] } | any[]>(`/students/suspension-requests/?student_id=${student.id}`),
          apiClient.get<{ results?: any[]; data?: any[] } | any[]>(`/students/withdrawal-requests/?student_id=${student.id}`),
        ]);
        const suspensionData = Array.isArray(suspensions) ? suspensions : (suspensions.results || suspensions.data || []);
        const withdrawalData = Array.isArray(withdrawals) ? withdrawals : (withdrawals.results || withdrawals.data || []);
        setSuspensionRequests(suspensionData);
        setWithdrawalRequests(withdrawalData);
      } catch (error) {
        console.error('Failed to fetch requests:', error);
      }
    };
    if (student.id) {
      fetchRequests();
    }
  }, [student.id]);

  // 現在の請求月（動的に計算）
  const currentBillingMonth = {
    year: String(currentBillingPeriod.year),
    month: String(currentBillingPeriod.month),
  };
  const defaultYearMonth = currentBillingMonth;

  // 契約フィルター用の年月選択（デフォルト：すべて表示）
  const [contractYear, setContractYear] = useState<string>("all");
  const [contractMonth, setContractMonth] = useState<string>("all");

  // 請求フィルター用の年月選択（デフォルト：翌月）
  const [invoiceYear, setInvoiceYear] = useState<string>(defaultYearMonth.year);
  const [invoiceMonth, setInvoiceMonth] = useState<string>(defaultYearMonth.month);

  // 生徒カルテタブのサブタブと日付フィルター
  const [commTab, setCommTab] = useState<"logs" | "chat" | "requests">("logs");
  const [commDateFrom, setCommDateFrom] = useState<string>("");
  const [commDateTo, setCommDateTo] = useState<string>("");

  // チャットスレッド用state
  const [chatChannels, setChatChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [channelMessages, setChannelMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [channelsLoading, setChannelsLoading] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [showNewChatForm, setShowNewChatForm] = useState(false);
  const [newChatTitle, setNewChatTitle] = useState("");
  const [creatingChat, setCreatingChat] = useState(false);

  // 画像アップロード用state
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [filePreviewUrl, setFilePreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 日付フィルタリングされた対応ログ
  const filteredContactLogs = useMemo(() => {
    return localContactLogs.filter((log) => {
      const logDate = new Date(log.created_at);
      if (commDateFrom && logDate < new Date(commDateFrom)) return false;
      if (commDateTo && logDate > new Date(commDateTo + "T23:59:59")) return false;
      return true;
    });
  }, [localContactLogs, commDateFrom, commDateTo]);

  // 日付フィルタリングされたメッセージ
  const filteredMessages = useMemo(() => {
    const allMessages = messages.length > 0 ? messages : chatLogs;
    return allMessages.filter((msg: any) => {
      const msgDate = new Date(msg.created_at || msg.timestamp);
      if (commDateFrom && msgDate < new Date(commDateFrom)) return false;
      if (commDateTo && msgDate > new Date(commDateTo + "T23:59:59")) return false;
      return true;
    });
  }, [messages, chatLogs, commDateFrom, commDateTo]);

  // 日付フィルターをクリア
  const clearCommDateFilter = () => {
    setCommDateFrom("");
    setCommDateTo("");
  };

  // チャンネル一覧を読み込む
  const loadChatChannels = async () => {
    const guardianId = parents[0]?.id;
    console.log("[loadChatChannels] parents:", parents);
    console.log("[loadChatChannels] guardianId:", guardianId);
    if (!guardianId) {
      console.log("[loadChatChannels] No guardianId, returning");
      return;
    }

    setChannelsLoading(true);
    try {
      // 保護者IDでフィルタしてチャンネルを取得（チャンネルにはstudent_idが設定されていないため）
      console.log("[loadChatChannels] Calling getChannels with guardianId:", guardianId);
      const channels = await getChannels({ guardianId });
      console.log("[loadChatChannels] Received channels:", channels);
      setChatChannels(channels || []);
    } catch (err) {
      console.error("Failed to load channels:", err);
    } finally {
      setChannelsLoading(false);
    }
  };

  // 選択したチャンネルのメッセージを読み込む
  const loadChannelMessages = async (channel: Channel) => {
    setMessagesLoading(true);
    try {
      const res = await getMessages(channel.id, { pageSize: 50 });
      const msgs = res?.results || res?.data || [];
      // 古い順に表示（新しいメッセージは下に溜まる）
      setChannelMessages(msgs);
    } catch (err) {
      console.error("Failed to load messages:", err);
    } finally {
      setMessagesLoading(false);
    }
  };

  // チャットタブを開いたときにチャンネル一覧を読み込む
  useEffect(() => {
    if (commTab === "chat" && parents.length > 0) {
      loadChatChannels();
    }
  }, [commTab, parents]);

  // チャンネル選択時にメッセージを読み込む
  useEffect(() => {
    if (selectedChannel) {
      loadChannelMessages(selectedChannel);
    }
  }, [selectedChannel]);

  // メッセージ送信
  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedChannel) return;

    setSendingMessage(true);
    try {
      const sentMsg = await sendMessage({
        channelId: selectedChannel.id,
        content: newMessage.trim(),
      });
      setChannelMessages((prev) => [...prev, sentMsg]);
      setNewMessage("");
    } catch (err) {
      console.error("Failed to send message:", err);
      alert("メッセージの送信に失敗しました");
    } finally {
      setSendingMessage(false);
    }
  };

  // ファイル選択処理
  const handleFileSelect = useCallback((file: File) => {
    // 画像ファイルのみ許可
    if (!file.type.startsWith('image/')) {
      alert('画像ファイルのみアップロードできます');
      return;
    }
    // 10MB制限
    if (file.size > 10 * 1024 * 1024) {
      alert('ファイルサイズは10MB以下にしてください');
      return;
    }
    setPendingFile(file);
    const url = URL.createObjectURL(file);
    setFilePreviewUrl(url);
  }, []);

  // ペースト処理
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          handleFileSelect(file);
        }
        break;
      }
    }
  }, [handleFileSelect]);

  // ファイル入力変更処理
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
    // 入力をリセットして同じファイルを再選択できるようにする
    e.target.value = '';
  }, [handleFileSelect]);

  // 選択ファイルをクリア
  const clearPendingFile = useCallback(() => {
    if (filePreviewUrl) {
      URL.revokeObjectURL(filePreviewUrl);
    }
    setPendingFile(null);
    setFilePreviewUrl(null);
  }, [filePreviewUrl]);

  // 画像送信
  const handleSendFile = async () => {
    if (!pendingFile || !selectedChannel) return;

    setSendingMessage(true);
    try {
      const sentMsg = await uploadFile({
        file: pendingFile,
        channelId: selectedChannel.id,
        content: newMessage.trim() || undefined,
      });
      setChannelMessages((prev) => [...prev, sentMsg]);
      setNewMessage("");
      clearPendingFile();
    } catch (err) {
      console.error("Failed to upload file:", err);
      alert("ファイルのアップロードに失敗しました");
    } finally {
      setSendingMessage(false);
    }
  };

  // 新規チャット作成
  const handleCreateNewChat = async () => {
    const guardianId = parents[0]?.id;
    if (!guardianId) {
      alert("保護者情報が見つかりません");
      return;
    }

    setCreatingChat(true);
    try {
      const newChannel = await getOrCreateChannelForGuardian(guardianId);
      setChatChannels((prev) => [newChannel, ...prev.filter((c) => c.id !== newChannel.id)]);
      setSelectedChannel(newChannel);
      setShowNewChatForm(false);
      setNewChatTitle("");
    } catch (err) {
      console.error("Failed to create chat:", err);
      alert("チャットの作成に失敗しました");
    } finally {
      setCreatingChat(false);
    }
  };

  // スレッド一覧に戻る
  const handleBackToChannelList = () => {
    setSelectedChannel(null);
    setChannelMessages([]);
  };

  // メッセージ日時フォーマット
  const formatMsgTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    if (isToday) {
      return date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
    }
    return date.toLocaleDateString("ja-JP", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  };

  // 年の選択肢を生成（過去3年〜今年まで）
  const currentYear = new Date().getFullYear();
  const yearOptions = useMemo(() => {
    const years = [];
    for (let y = currentYear - 3; y <= currentYear + 1; y++) {
      years.push(y);
    }
    return years;
  }, [currentYear]);

  // 月の選択肢
  const monthOptions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

  // 日付文字列をDateに変換（複数フォーマット対応）
  const parseDate = (dateStr: string | null | undefined): Date | null => {
    if (!dateStr) return null;
    // ISO形式 (2025-10-01)
    let date = new Date(dateStr);
    if (!isNaN(date.getTime())) return date;
    // スラッシュ形式 (2025/10/1)
    const slashMatch = dateStr.match(/(\d{4})\/(\d{1,2})\/(\d{1,2})/);
    if (slashMatch) {
      return new Date(parseInt(slashMatch[1]), parseInt(slashMatch[2]) - 1, parseInt(slashMatch[3]));
    }
    // 日本語形式 (2025年10月1日)
    const jpMatch = dateStr.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
    if (jpMatch) {
      return new Date(parseInt(jpMatch[1]), parseInt(jpMatch[2]) - 1, parseInt(jpMatch[3]));
    }
    return null;
  };

  // 契約フィルター処理（請求月ベース）
  const filteredContracts = useMemo(() => {
    if (contractYear === "all" && contractMonth === "all") {
      return contracts;
    }

    const filterYear = contractYear !== "all" ? parseInt(contractYear) : null;
    const filterMonth = contractMonth !== "all" ? parseInt(contractMonth) : null;

    const filtered = contracts.filter((contract) => {
      const startDateStr = contract.start_date || contract.startDate;
      const endDateStr = contract.end_date || contract.endDate;

      if (!startDateStr) return false; // 開始日なしは非表示

      const startDate = parseDate(startDateStr);
      const endDate = parseDate(endDateStr);

      if (!startDate) return false; // パース失敗は非表示

      // フィルター期間の設定（請求月ベースで判定）
      if (filterYear && filterMonth) {
        // 締め日ロジック: フィルターの請求月に対応する期間を計算
        // 例: 2月請求 → 12/11〜1/10の期間に開始した契約
        // 期間 = 請求月 - 1ヶ月
        const periodMonth = filterMonth - 1 === 0 ? 12 : filterMonth - 1;
        const periodYear = filterMonth - 1 === 0 ? filterYear - 1 : filterYear;

        // 期間の開始日（前月11日）と終了日（当月10日）
        const prevMonth = periodMonth - 1 === 0 ? 12 : periodMonth - 1;
        const prevYear = periodMonth - 1 === 0 ? periodYear - 1 : periodYear;
        const periodStart = new Date(prevYear, prevMonth - 1, 11); // 前月11日
        const periodEnd = new Date(periodYear, periodMonth - 1, 10, 23, 59, 59); // 当月10日

        // フィルター月の範囲（表示用：請求月の月初〜月末も含める）
        const filterMonthStart = new Date(filterYear, filterMonth - 1, 1);
        const filterMonthEnd = new Date(filterYear, filterMonth, 0, 23, 59, 59);

        // 契約の請求月を計算
        const contractBilling = getBillingMonthForDate(startDate);
        const isBillingMonthMatch = contractBilling.year === filterYear && contractBilling.month === filterMonth;

        // 請求月が一致するか、契約期間がフィルター月に有効かどうか
        // 月額契約は開始月以降も有効なので、請求月以降のフィルターでも表示
        if (isBillingMonthMatch) {
          return true; // 請求月が一致
        }

        // 継続契約の場合: 開始月の請求月がフィルター月以前、かつ終了日がフィルター月以降
        const startBeforeOrInMonth = contractBilling.year < filterYear ||
          (contractBilling.year === filterYear && contractBilling.month <= filterMonth);
        const endAfterOrInMonth = !endDate || endDate >= filterMonthStart;

        return startBeforeOrInMonth && endAfterOrInMonth;
      } else if (filterYear) {
        // 年のみ指定: その年に請求対象となる契約
        const yearStart = new Date(filterYear, 0, 1);
        const yearEnd = new Date(filterYear, 11, 31, 23, 59, 59);

        const startBeforeOrInYear = startDate <= yearEnd;
        const endAfterOrInYear = !endDate || endDate >= yearStart;

        return startBeforeOrInYear && endAfterOrInYear;
      } else if (filterMonth) {
        // 月のみ指定: 現在の年のその月に有効な契約
        const thisYear = new Date().getFullYear();
        const contractBilling = getBillingMonthForDate(startDate);
        const isBillingMonthMatch = contractBilling.year === thisYear && contractBilling.month === filterMonth;

        if (isBillingMonthMatch) {
          return true;
        }

        const filterMonthStart = new Date(thisYear, filterMonth - 1, 1);
        const startBeforeOrInMonth = contractBilling.year < thisYear ||
          (contractBilling.year === thisYear && contractBilling.month <= filterMonth);
        const endAfterOrInMonth = !endDate || endDate >= filterMonthStart;

        return startBeforeOrInMonth && endAfterOrInMonth;
      }
      return true;
    });

    // 開始日でソート（新しいものが先）
    return filtered.sort((a, b) => {
      const aDateStr = a.start_date || a.startDate;
      const bDateStr = b.start_date || b.startDate;
      const aDate = aDateStr ? parseDate(aDateStr) : null;
      const bDate = bDateStr ? parseDate(bDateStr) : null;
      if (!aDate && !bDate) return 0;
      if (!aDate) return 1;
      if (!bDate) return -1;
      return bDate.getTime() - aDate.getTime(); // 降順
    });
  }, [contracts, contractYear, contractMonth]);

  // 請求フィルター処理
  const filteredInvoices = useMemo(() => {
    if (invoiceYear === "all" && invoiceMonth === "all") {
      return invoices;
    }
    return invoices.filter((invoice) => {
      const billingMonth = String(invoice.billingMonth || invoice.billing_month || "");
      // billing_monthは "2024年1月" のような形式を想定
      if (!billingMonth || billingMonth === "未設定") return true;

      const match = billingMonth.match(/(\d{4})年(\d{1,2})月/);
      if (!match) return true;

      const invYear = parseInt(match[1]);
      const invMonth = parseInt(match[2]);

      const filterYear = invoiceYear !== "all" ? parseInt(invoiceYear) : null;
      const filterMonth = invoiceMonth !== "all" ? parseInt(invoiceMonth) : null;

      if (filterYear && filterMonth) {
        return invYear === filterYear && invMonth === filterMonth;
      } else if (filterYear) {
        return invYear === filterYear;
      } else if (filterMonth) {
        return invMonth === filterMonth;
      }
      return true;
    });
  }, [invoices, invoiceYear, invoiceMonth]);

  // フィールド名の両対応 (eslint-disable-next-line @typescript-eslint/no-explicit-any)
  const s = student as any;
  const lastName = s.lastName || s.last_name || "";
  const firstName = s.firstName || s.first_name || "";
  const lastNameKana = s.lastNameKana || s.last_name_kana || "";
  const firstNameKana = s.firstNameKana || s.first_name_kana || "";
  const studentNo = s.studentNo || s.student_no || "";
  const gradeText = s.gradeText || s.grade_text || s.gradeName || "";
  const schoolName = s.schoolName || s.school_name || "";
  const primarySchoolName = s.primarySchoolName || s.primary_school_name || "";
  const primaryBrandName = s.primaryBrandName || s.primary_brand_name || "";
  const brandNames = s.brandNames || s.brand_names || [];
  const email = s.email || "";
  const phone = s.phone || "";
  const gender = s.gender || "";
  // 日付情報
  const birthDate = s.birthDate || s.birth_date || "";
  const enrollmentDate = s.enrollmentDate || s.enrollment_date || "";
  const registeredDate = s.registeredDate || s.registered_date || "";
  const trialDate = s.trialDate || s.trial_date || "";

  // 日付フォーマット
  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "-";
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
  };

  // 生徒編集ダイアログを開く
  const openStudentEditDialog = () => {
    setStudentForm({
      last_name: student.last_name || student.lastName || '',
      first_name: student.first_name || student.firstName || '',
      last_name_kana: student.last_name_kana || student.lastNameKana || '',
      first_name_kana: student.first_name_kana || student.firstNameKana || '',
      birth_date: student.birth_date || student.birthDate || '',
      gender: student.gender || '',
      phone: student.phone || '',
      email: student.email || '',
      school_name: student.school_name || student.schoolName || '',
      notes: (student as any).notes || '',
    });
    setStudentEditDialogOpen(true);
  };

  // 生徒情報を更新
  const handleStudentUpdate = async () => {
    setIsSubmitting(true);
    try {
      await apiClient.patch(`/students/${student.id}/`, studentForm);
      alert('生徒情報を更新しました');
      setStudentEditDialogOpen(false);
      onRefresh?.();
    } catch (error: any) {
      console.error('Student update error:', error);
      alert(error.data?.detail || error.message || '生徒情報の更新に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 保護者編集ダイアログを開く
  const openGuardianEditDialog = (g: Guardian) => {
    setEditingGuardian(g);
    setGuardianForm({
      last_name: g.lastName || g.last_name || '',
      first_name: g.firstName || g.first_name || '',
      last_name_kana: g.lastNameKana || g.last_name_kana || '',
      first_name_kana: g.firstNameKana || g.first_name_kana || '',
      phone: g.phone || '',
      phone_mobile: g.phoneMobile || g.phone_mobile || '',
      email: g.email || '',
      postal_code: g.postalCode || g.postal_code || '',
      prefecture: g.prefecture || '',
      city: g.city || '',
      address1: g.address1 || '',
      address2: g.address2 || '',
    });
    setGuardianEditDialogOpen(true);
  };

  // 保護者情報を更新
  const handleGuardianUpdate = async () => {
    if (!editingGuardian) return;
    setIsSubmitting(true);
    try {
      await apiClient.patch(`/students/guardians/${editingGuardian.id}/`, guardianForm);
      alert('保護者情報を更新しました');
      setGuardianEditDialogOpen(false);
      onRefresh?.();
    } catch (error: any) {
      console.error('Guardian update error:', error);
      alert(error.message || '保護者情報の更新に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 休会申請を送信
  const handleSuspensionSubmit = async () => {
    setIsSubmitting(true);
    try {
      const response = await apiClient.post<{ id: string }>('/students/suspension-requests/', {
        student: student.id,
        brand: student.primary_brand?.id || student.primary_brand_id || (student as any).primaryBrand?.id,
        school: student.primary_school?.id || student.primary_school_id || (student as any).primarySchool?.id,
        ...suspensionForm,
      });

      // 承認処理も同時に実行（管理者なので）
      await apiClient.post(`/students/suspension-requests/${response.id}/approve/`, {});

      alert('休会登録が完了しました');
      setSuspensionDialogOpen(false);
      onRefresh?.();
    } catch (error: any) {
      console.error('Suspension error:', error);
      alert(error.message || '休会登録に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 退会申請を送信
  const handleWithdrawalSubmit = async () => {
    setIsSubmitting(true);
    try {
      const response = await apiClient.post<{ id: string }>('/students/withdrawal-requests/', {
        student: student.id,
        brand: student.primary_brand?.id || student.primary_brand_id || (student as any).primaryBrand?.id,
        school: student.primary_school?.id || student.primary_school_id || (student as any).primarySchool?.id,
        ...withdrawalForm,
      });

      // 承認処理も同時に実行（管理者なので）
      await apiClient.post(`/students/withdrawal-requests/${response.id}/approve/`, {});

      alert('退会登録が完了しました');
      setWithdrawalDialogOpen(false);
      onRefresh?.();
    } catch (error: any) {
      console.error('Withdrawal error:', error);
      alert(error.message || '退会登録に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 保護者情報
  const guardian = parents[0] || student.guardian;
  const guardianNo = guardian?.guardianNo || guardian?.guardian_no || "";
  const guardianLastName = guardian?.lastName || guardian?.last_name || "";
  const guardianFirstName = guardian?.firstName || guardian?.first_name || "";
  const guardianName = `${guardianLastName} ${guardianFirstName}`.trim();
  const guardianPhone = guardian?.phone || guardian?.phoneMobile || guardian?.phone_mobile || "";
  const guardianEmail = guardian?.email || "";

  // 写真URL
  const profileImageUrl = student.profile_image_url || (student as any).profileImageUrl || "";

  return (
    <div className="h-full flex flex-col bg-white">
      {/* ヘッダー - ファーストビューで重要情報を表示 */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4">
        <div className="flex items-start gap-4 mb-3">
          {/* 生徒写真 */}
          <div className="relative group">
            <input
              type="file"
              ref={photoInputRef}
              onChange={handlePhotoUpload}
              accept="image/jpeg,image/png,image/gif,image/webp"
              className="hidden"
            />
            <button
              onClick={() => photoInputRef.current?.click()}
              disabled={isUploadingPhoto}
              className="relative cursor-pointer focus:outline-none focus:ring-2 focus:ring-white/50 rounded-full"
            >
              {profileImageUrl ? (
                <img
                  src={profileImageUrl}
                  alt={`${lastName} ${firstName}`}
                  className="w-16 h-16 rounded-full object-cover border-2 border-white/50"
                />
              ) : (
                <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center border-2 border-white/50">
                  <User className="w-8 h-8 text-white/70" />
                </div>
              )}
              {/* カメラアイコンオーバーレイ */}
              <div className="absolute inset-0 rounded-full bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                {isUploadingPhoto ? (
                  <Loader2 className="w-6 h-6 text-white animate-spin" />
                ) : (
                  <ImageIcon className="w-6 h-6 text-white" />
                )}
              </div>
            </button>
          </div>

          <div className="flex-1">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-bold">{lastName} {firstName}</h2>
                <p className="text-blue-100 text-sm">{lastNameKana} {firstNameKana}</p>
              </div>
              <Badge className={getStatusColor(student.status)}>
                {getStatusLabel(student.status)}
              </Badge>
            </div>
          </div>
        </div>

        {/* 生徒・保護者の主要情報 */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          {/* 生徒情報 */}
          <div className="bg-white/10 rounded p-2">
            <div className="grid grid-cols-2 gap-x-3 gap-y-1">
              <div>
                <span className="text-blue-200 text-xs">生徒ID</span>
                <p className="font-mono">{studentNo}</p>
              </div>
              <div>
                <span className="text-blue-200 text-xs">学年</span>
                <p>{gradeText || "-"}</p>
              </div>
              <div>
                <span className="text-blue-200 text-xs">性別</span>
                <p>{gender === "male" ? "男" : gender === "female" ? "女" : "-"}</p>
              </div>
              <div>
                <span className="text-blue-200 text-xs">校舎</span>
                <p className="truncate">{schoolName || "-"}</p>
              </div>
            </div>
          </div>

          {/* 保護者情報 */}
          <div className="bg-white/10 rounded p-2">
            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <div>
                  <span className="text-blue-200 text-xs">保護者</span>
                  <p>{guardianName || "-"}</p>
                </div>
                {guardian && (
                  <Button
                    size="sm"
                    variant="secondary"
                    className="h-6 text-xs bg-white/20 hover:bg-white/30 text-white border-0"
                    onClick={() => guardian && openGuardianView(guardian)}
                    disabled={isOpeningGuardianView}
                  >
                    <ExternalLink className="w-3 h-3 mr-1" />
                    保護者画面
                  </Button>
                )}
              </div>
              <div>
                <span className="text-blue-200 text-xs">TEL</span>
                <p className="font-mono text-xs">{guardianPhone || "-"}</p>
              </div>
              <div>
                <span className="text-blue-200 text-xs">Mail</span>
                <p className="text-xs truncate">{guardianEmail || "-"}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* タブ */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="w-full justify-start rounded-none border-b bg-gray-50 p-0">
          <TabsTrigger
            value="basic"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-white px-4 py-2"
          >
            基本情報
          </TabsTrigger>
          <TabsTrigger
            value="guardian"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-white px-4 py-2"
          >
            保護者
          </TabsTrigger>
          <TabsTrigger
            value="contracts"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-white px-4 py-2"
          >
            契約
          </TabsTrigger>
          <TabsTrigger
            value="billing"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-white px-4 py-2"
          >
            請求
          </TabsTrigger>
          <TabsTrigger
            value="communications"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-white px-4 py-2"
          >
            生徒カルテ
          </TabsTrigger>
        </TabsList>

        {/* 基本情報タブ */}
        <TabsContent value="basic" className="flex-1 overflow-auto p-0 m-0">
          <div className="p-3 space-y-2">
            {/* 上段: 生徒情報 + 在籍情報 (2列) */}
            <div className="grid grid-cols-2 gap-2">
              {/* 生徒基本情報 */}
              <div>
                <h3 className="text-xs font-semibold text-gray-700 mb-1">生徒情報</h3>
                <table className="w-full text-xs border">
                  <tbody>
                    <tr className="border-b bg-gray-50">
                      <th className="px-2 py-1 text-left text-gray-600 font-medium w-16 border-r">生徒ID</th>
                      <td className="px-2 py-1 font-mono">{studentNo}</td>
                    </tr>
                    <tr className="border-b">
                      <th className="px-2 py-1 text-left text-gray-600 font-medium border-r">学年</th>
                      <td className="px-2 py-1">{gradeText || "-"}</td>
                    </tr>
                    <tr className="border-b bg-gray-50">
                      <th className="px-2 py-1 text-left text-gray-600 font-medium border-r">生年月日</th>
                      <td className="px-2 py-1">{formatDate(birthDate)}</td>
                    </tr>
                    <tr className="border-b">
                      <th className="px-2 py-1 text-left text-gray-600 font-medium border-r">性別</th>
                      <td className="px-2 py-1">{gender === "male" ? "男" : gender === "female" ? "女" : "-"}</td>
                    </tr>
                    <tr className="border-b bg-gray-50">
                      <th className="px-2 py-1 text-left text-gray-600 font-medium border-r">学校名</th>
                      <td className="px-2 py-1 truncate max-w-[120px]">{schoolName || "-"}</td>
                    </tr>
                    <tr className="border-b">
                      <th className="px-2 py-1 text-left text-gray-600 font-medium border-r">電話</th>
                      <td className="px-2 py-1">{phone || "-"}</td>
                    </tr>
                    <tr className="border-b bg-gray-50">
                      <th className="px-2 py-1 text-left text-gray-600 font-medium border-r">メール</th>
                      <td className="px-2 py-1 truncate max-w-[120px]">{email || "-"}</td>
                    </tr>
                  </tbody>
                </table>

                {/* QRコード */}
                <div className="mt-2">
                  <h3 className="text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
                    <QrCode className="w-3 h-3" />
                    出席用QRコード
                  </h3>
                  {qrCodeInfo ? (
                    <div
                      className="flex items-center gap-2 p-2 bg-gray-50 border rounded cursor-pointer hover:bg-gray-100 transition-colors"
                      onClick={() => setQrCodeDialogOpen(true)}
                    >
                      <div className="bg-white p-1 rounded border">
                        <QRCodeCanvas value={qrCodeInfo.qr_code} size={48} level="M" />
                      </div>
                      <p className="text-[10px] text-gray-500">クリックで拡大表示</p>
                    </div>
                  ) : (
                    <div className="p-2 bg-gray-50 border rounded text-xs text-gray-400">
                      QRコードを取得できません
                    </div>
                  )}
                </div>
              </div>

              {/* 在籍情報 */}
              <div>
                <h3 className="text-xs font-semibold text-gray-700 mb-1">在籍情報</h3>

                {/* 契約中のブランド・コース（目立つ表示） */}
                {(() => {
                  // 有効な契約を抽出（解約済み以外は全て表示）
                  const activeContracts = contracts.filter(c =>
                    c.status !== 'cancelled' && c.status !== 'expired'
                  );

                  // デバッグ用（本番では削除可）
                  console.log('[StudentDetail] contracts:', contracts.length, 'active:', activeContracts.length);

                  if (activeContracts.length > 0) {
                    return (
                      <div className="mb-2 space-y-1">
                        {activeContracts.map((contract, idx) => {
                          const brandName = contract.brand_name || contract.brandName || (contract.brand as any)?.brand_name || (contract.brand as any)?.name || '';
                          const courseName = contract.course_name || contract.courseName || (contract.course as any)?.course_name || (contract.course as any)?.name || '';
                          const schoolName = contract.school_name || contract.schoolName || (contract.school as any)?.school_name || (contract.school as any)?.name || '';
                          const statusLabel = contract.status === 'active' ? '契約中' : contract.status === 'pending' ? '保留' : '契約';
                          return (
                            <div key={contract.id || idx} className="bg-blue-50 border border-blue-200 rounded-lg p-2">
                              <div className="flex items-center gap-2">
                                <Badge className="text-[10px] px-1.5 py-0.5 bg-blue-600 text-white">{statusLabel}</Badge>
                                <span className="text-xs font-bold text-blue-900">{brandName || '不明'}</span>
                              </div>
                              {courseName && (
                                <p className="text-[11px] text-blue-700 mt-0.5 ml-1">{courseName}</p>
                              )}
                              {schoolName && (
                                <p className="text-[10px] text-blue-600 mt-0.5 ml-1">📍 {schoolName}</p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    );
                  }
                  // 契約がない場合のメッセージ
                  return (
                    <div className="mb-2 p-2 bg-gray-50 border border-gray-200 rounded-lg">
                      <p className="text-xs text-gray-500">契約情報なし</p>
                    </div>
                  );
                })()}

                <table className="w-full text-xs border">
                  <tbody>
                    <tr className="border-b bg-gray-50">
                      <th className="px-2 py-1 text-left text-gray-600 font-medium w-16 border-r">校舎</th>
                      <td className="px-2 py-1">{primarySchoolName || "-"}</td>
                    </tr>
                    <tr className="border-b">
                      <th className="px-2 py-1 text-left text-gray-600 font-medium border-r">体験日</th>
                      <td className="px-2 py-1">{formatDate(trialDate)}</td>
                    </tr>
                    <tr className="border-b bg-gray-50">
                      <th className="px-2 py-1 text-left text-gray-600 font-medium border-r">登録日</th>
                      <td className="px-2 py-1">{formatDate(registeredDate)}</td>
                    </tr>
                  </tbody>
                </table>

                {/* ブランド別入会・退会情報 */}
                {(() => {
                  // ブランドごとにグループ化して入会日・退会日を集計
                  const brandDates = contracts.reduce((acc, contract) => {
                    // brandはUUID文字列またはオブジェクトの場合がある
                    const brandId = contract.brand_id || (typeof contract.brand === 'string' ? contract.brand : (contract.brand as any)?.id);
                    const brandName = contract.brand_name || contract.brandName || (contract.brand as any)?.brand_name || (contract.brand as any)?.brandName || "";
                    if (!brandId || !brandName) return acc;

                    if (!acc[brandId]) {
                      acc[brandId] = {
                        brandName,
                        enrollmentDate: null as string | null,
                        withdrawalDate: null as string | null,
                        status: contract.status,
                      };
                    }

                    // 入会日: 最も古いstart_date
                    const startDate = contract.start_date || contract.startDate;
                    if (startDate) {
                      if (!acc[brandId].enrollmentDate || startDate < acc[brandId].enrollmentDate!) {
                        acc[brandId].enrollmentDate = startDate;
                      }
                    }

                    // 退会日: end_dateがあり、statusがcancelled/expiredの場合
                    const endDate = contract.end_date || contract.endDate;
                    if (endDate && (contract.status === 'cancelled' || contract.status === 'expired')) {
                      if (!acc[brandId].withdrawalDate || endDate > acc[brandId].withdrawalDate!) {
                        acc[brandId].withdrawalDate = endDate;
                      }
                      acc[brandId].status = contract.status;
                    }

                    // アクティブな契約があればステータスを更新
                    if (contract.status === 'active') {
                      acc[brandId].status = 'active';
                      acc[brandId].withdrawalDate = null;
                    }

                    return acc;
                  }, {} as Record<string, { brandName: string; enrollmentDate: string | null; withdrawalDate: string | null; status: string }>);

                  const brandList = Object.entries(brandDates);

                  if (brandList.length === 0) {
                    return (
                      <div className="mt-2 text-xs text-gray-400 px-2 py-1 bg-gray-50 rounded">
                        契約情報なし
                      </div>
                    );
                  }

                  return (
                    <div className="mt-2">
                      <p className="text-[10px] text-gray-500 mb-1">入会履歴</p>
                      <table className="w-full text-xs border">
                        <thead>
                          <tr className="bg-gray-100">
                            <th className="px-2 py-1 text-left text-gray-600 font-medium border-r">ブランド</th>
                            <th className="px-2 py-1 text-left text-gray-600 font-medium border-r">入会日</th>
                            <th className="px-2 py-1 text-left text-gray-600 font-medium">退会日</th>
                          </tr>
                        </thead>
                        <tbody>
                          {brandList.map(([brandId, data], idx) => (
                            <tr key={brandId} className={idx % 2 === 0 ? "bg-gray-50" : ""}>
                              <td className="px-2 py-1 border-r">
                                <div className="flex items-center gap-1">
                                  <span className="font-medium">{data.brandName}</span>
                                  {data.status === 'active' && (
                                    <Badge className="text-[9px] px-1 py-0 bg-green-100 text-green-700">在籍</Badge>
                                  )}
                                  {(data.status === 'cancelled' || data.status === 'expired') && (
                                    <Badge className="text-[9px] px-1 py-0 bg-gray-100 text-gray-600">退会</Badge>
                                  )}
                                </div>
                              </td>
                              <td className="px-2 py-1 border-r">{formatDate(data.enrollmentDate)}</td>
                              <td className="px-2 py-1">{data.withdrawalDate ? formatDate(data.withdrawalDate) : "-"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* 中段: 保護者情報 (コンパクト) + FS割 */}
            <div>
              <h3 className="text-xs font-semibold text-gray-700 mb-1">保護者情報</h3>
              <div className="grid grid-cols-4 gap-x-3 gap-y-1 text-xs border rounded p-2 bg-gray-50">
                <div><span className="text-gray-500">名前:</span> <span className="font-medium">{guardianName || "-"}</span></div>
                <div><span className="text-gray-500">ID:</span> <span className="font-mono">{guardianNo || "-"}</span></div>
                <div><span className="text-gray-500">電話:</span> {guardianPhone || "-"}</div>
                <div className="truncate"><span className="text-gray-500">メール:</span> {guardianEmail || "-"}</div>
              </div>
              {/* FS割情報 */}
              {guardian?.fs_discounts && guardian.fs_discounts.length > 0 && (
                <div className="mt-1 p-2 bg-green-50 border border-green-200 rounded text-xs">
                  <span className="text-green-700 font-medium">FS割:</span>
                  {guardian.fs_discounts.map((fs: any, idx: number) => (
                    <span key={fs.id || idx} className="ml-2 text-green-800">
                      {fs.role === 'referrer' ? (
                        <>紹介 → <span className="font-medium">{fs.partner_name}</span></>
                      ) : (
                        <><span className="font-medium">{fs.partner_name}</span> → 紹介</>
                      )}
                      <span className="text-green-600 ml-1">
                        ({fs.discount_type_display}: {fs.discount_type === 'percentage' ? `${fs.discount_value}%` : fs.discount_type === 'months_free' ? `${fs.discount_value}ヶ月無料` : `¥${fs.discount_value}`})
                      </span>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* 兄弟情報 */}
            {siblings.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                  <Users className="w-4 h-4 mr-1" />
                  兄弟姉妹
                </h3>
                <div className="flex flex-wrap gap-2">
                  {siblings.map((sibling) => {
                    const siblingName = `${sibling.lastName || sibling.last_name || ""} ${sibling.firstName || sibling.first_name || ""}`.trim();
                    const siblingGrade = sibling.gradeText || sibling.grade_text || sibling.gradeName || "";
                    const siblingStatus = sibling.status;
                    return (
                      <button
                        key={sibling.id}
                        onClick={() => onSelectSibling?.(sibling.id)}
                        className="flex items-center gap-2 p-2 border rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors cursor-pointer text-left"
                      >
                        <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                          <User className="w-4 h-4 text-gray-500" />
                        </div>
                        <div>
                          <div className="font-medium text-sm">{siblingName}</div>
                          <div className="text-xs text-gray-500">
                            {siblingGrade && <span>{siblingGrade}</span>}
                            {siblingGrade && siblingStatus && <span> / </span>}
                            {siblingStatus && (
                              <Badge className={`text-xs ${getStatusColor(siblingStatus)}`}>
                                {getStatusLabel(siblingStatus)}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 銀行口座情報 */}
            {guardian && (guardian.bank_name || guardian.bankName) && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">引落口座</h3>
                <table className="w-full text-sm border">
                  <tbody>
                    <tr className="border-b bg-gray-50">
                      <th className="px-3 py-2 text-left text-gray-600 font-medium w-28 border-r">金融機関</th>
                      <td className="px-3 py-2">{guardian.bank_name || guardian.bankName || "-"}</td>
                    </tr>
                    <tr className="border-b">
                      <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">支店</th>
                      <td className="px-3 py-2">{guardian.branch_name || guardian.branchName || "-"}</td>
                    </tr>
                    <tr className="border-b bg-gray-50">
                      <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">口座番号</th>
                      <td className="px-3 py-2 font-mono">
                        {(guardian.account_type || guardian.accountType) === "ordinary" ? "普通" : "当座"}{" "}
                        {guardian.account_number || guardian.accountNumber || "-"}
                      </td>
                    </tr>
                    <tr className="border-b">
                      <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">名義</th>
                      <td className="px-3 py-2">{guardian.account_holder_kana || guardian.accountHolderKana || "-"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}

            {/* 特記事項 */}
            {(s.notes || s.tags) && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">特記事項</h3>
                <div className="border rounded p-3 bg-yellow-50 text-sm">
                  {s.tags && Array.isArray(s.tags) && s.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {s.tags.map((tag: string, i: number) => (
                        <Badge key={i} className="bg-yellow-200 text-yellow-800 text-xs">{tag}</Badge>
                      ))}
                    </div>
                  )}
                  <p className="whitespace-pre-wrap text-gray-700">{s.notes || "特記事項なし"}</p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <Button size="sm" className="w-full">
                <MessageCircle className="w-4 h-4 mr-1" />
                チャット
              </Button>
              <Button size="sm" variant="outline" className="w-full" onClick={openStudentEditDialog}>
                <Edit className="w-4 h-4 mr-1" />
                編集
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* 保護者タブ */}
        <TabsContent value="guardian" className="flex-1 overflow-auto p-0 m-0">
          <div className="p-4">
            {parents.length > 0 || guardian ? (
              <div className="space-y-4">
                {(parents.length > 0 ? parents : [guardian]).filter(Boolean).map((g, idx) => {
                  const gNo = g?.guardianNo || g?.guardian_no || "";
                  const gLastName = g?.lastName || g?.last_name || "";
                  const gFirstName = g?.firstName || g?.first_name || "";
                  const gLastNameKana = g?.lastNameKana || g?.last_name_kana || "";
                  const gFirstNameKana = g?.firstNameKana || g?.first_name_kana || "";
                  const gPhone = g?.phone || "";
                  const gPhoneMobile = g?.phoneMobile || g?.phone_mobile || "";
                  const gEmail = g?.email || "";
                  const gPostalCode = g?.postalCode || g?.postal_code || "";
                  const gPrefecture = g?.prefecture || "";
                  const gCity = g?.city || "";
                  const gAddress1 = g?.address1 || "";
                  const gAddress2 = g?.address2 || "";

                  return (
                    <div key={g?.id || idx} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-start gap-3">
                          <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
                            <User className="w-6 h-6 text-gray-500" />
                          </div>
                          <div>
                            <h3 className="font-bold text-lg">{gLastName} {gFirstName}</h3>
                            <p className="text-sm text-gray-500">{gLastNameKana} {gFirstNameKana}</p>
                            <p className="text-xs text-gray-400">No. {gNo}</p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="default"
                            className="bg-blue-600 hover:bg-blue-700"
                            onClick={() => g && openGuardianView(g)}
                            disabled={isOpeningGuardianView}
                          >
                            <ExternalLink className="w-4 h-4 mr-1" />
                            {isOpeningGuardianView ? '開いています...' : '保護者画面を開く'}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => g && openGuardianEditDialog(g)}
                          >
                            <Pencil className="w-4 h-4 mr-1" />
                            編集
                          </Button>
                        </div>
                      </div>

                      <table className="w-full text-sm border">
                        <tbody>
                          <tr className="border-b bg-gray-50">
                            <th className="px-3 py-2 text-left text-gray-600 font-medium w-28 border-r">
                              <Phone className="w-4 h-4 inline mr-1" />電話
                            </th>
                            <td className="px-3 py-2">{gPhone || "-"}</td>
                          </tr>
                          <tr className="border-b">
                            <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">
                              <Phone className="w-4 h-4 inline mr-1" />携帯
                            </th>
                            <td className="px-3 py-2">{gPhoneMobile || "-"}</td>
                          </tr>
                          <tr className="border-b bg-gray-50">
                            <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">
                              <Mail className="w-4 h-4 inline mr-1" />メール
                            </th>
                            <td className="px-3 py-2 break-all">{gEmail || "-"}</td>
                          </tr>
                          <tr className="border-b">
                            <th className="px-3 py-2 text-left text-gray-600 font-medium border-r">
                              <MapPin className="w-4 h-4 inline mr-1" />住所
                            </th>
                            <td className="px-3 py-2">
                              {gPostalCode && <span className="text-gray-500">〒{gPostalCode}<br /></span>}
                              {gPrefecture}{gCity}{gAddress1}{gAddress2 || "-"}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                保護者情報が登録されていません
              </div>
            )}
          </div>
        </TabsContent>

        {/* 契約タブ */}
        <TabsContent value="contracts" className="flex-1 overflow-auto p-0 m-0">
          <div className="p-4">
            {/* 設備費の重複排除: 全契約から設備費を集め、最高額のみを有効にする */}
            {(() => {
              // 全契約の設備費を収集
              const facilityTypes = ['facility', 'enrollment_facility'];
              const allFacilityItems: { contractId: string; itemId: string; price: number }[] = [];

              filteredContracts.forEach((contract: any) => {
                const items = contract.student_items || contract.studentItems || contract.items || [];
                items.forEach((item: any) => {
                  const itemType = (item.item_type || item.itemType || '').toLowerCase();
                  if (facilityTypes.includes(itemType)) {
                    const price = Number(item.final_price || item.finalPrice || item.unit_price || item.unitPrice || 0);
                    allFacilityItems.push({
                      contractId: contract.id,
                      itemId: item.id || item.product_id || item.productId || '',
                      price,
                    });
                  }
                });
              });

              // 最高額の設備費を特定
              const highestFacility = allFacilityItems.length > 0
                ? allFacilityItems.reduce((max, item) => item.price > max.price ? item : max, allFacilityItems[0])
                : null;

              // 除外すべき設備費のセット（最高額以外）
              const excludedFacilitySet = new Set(
                allFacilityItems
                  .filter(item => highestFacility && (item.contractId !== highestFacility.contractId || item.itemId !== highestFacility.itemId))
                  .map(item => `${item.contractId}-${item.itemId}`)
              );

              // ===== 合計金額を計算 =====
              const oneTimeItemTypes = [
                'enrollment', 'enrollment_tuition', 'enrollment_monthly_fee',
                'enrollment_facility', 'enrollment_textbook', 'enrollment_expense',
                'enrollment_management', 'bag', 'abacus'
              ];
              const textbookItemTypes = ['textbook', 'material'];

              let totalMonthly = 0;
              let totalEnrollment = 0;
              let totalTextbook = 0;
              let totalDiscount = 0;
              let totalMileDiscount = 0;

              // 税込価格計算用関数（消費税10%）
              const withTaxSummary = (price: number) => Math.floor(price * 1.1);

              // ブランドごとの集計
              const brandTotals = new Map<string, { monthly: number; enrollment: number; textbook: number; discount: number }>();

              filteredContracts.forEach((contract: any) => {
                const brandName = contract.brand_name || contract.brandName || "その他";
                const items = contract.student_items || contract.studentItems || [];
                const discounts = contract.discounts || [];
                const discountTotal = contract.discount_total || contract.discountTotal || 0;
                const discountApplied = contract.discount_applied || contract.discountApplied || 0;
                const contractDiscount = Number(discounts.length > 0 ? discountTotal : discountApplied);

                if (!brandTotals.has(brandName)) {
                  brandTotals.set(brandName, { monthly: 0, enrollment: 0, textbook: 0, discount: 0 });
                }
                const bt = brandTotals.get(brandName)!;

                items.forEach((item: any) => {
                  const itemType = (item.item_type || item.itemType || '').toLowerCase();
                  const itemName = (item.product_name || item.productName || '').toLowerCase();
                  const price = withTaxSummary(Number(item.final_price || item.finalPrice || item.unit_price || item.unitPrice || 0));

                  // 設備費の重複排除チェック
                  const itemId = item.id || item.product_id || item.productId || '';
                  const isExcluded = facilityTypes.includes(itemType) && excludedFacilitySet.has(`${contract.id}-${itemId}`);
                  if (isExcluded) return;

                  if (oneTimeItemTypes.includes(itemType) || itemName.includes('入会金')) {
                    totalEnrollment += price;
                    bt.enrollment += price;
                  } else if (textbookItemTypes.includes(itemType)) {
                    totalTextbook += price;
                    bt.textbook += price;
                  } else {
                    totalMonthly += price;
                    bt.monthly += price;
                  }
                });

                totalDiscount += contractDiscount;
                bt.discount += contractDiscount;

                // マイル割引を確認（notesに含まれる場合）
                items.forEach((item: any) => {
                  const notes = item.notes || '';
                  if (notes.includes('マイル')) {
                    const mileMatch = notes.match(/マイル.*?(\d+)/);
                    if (mileMatch) {
                      totalMileDiscount += parseInt(mileMatch[1]);
                    }
                  }
                });
              });

              const grandTotal = totalMonthly + totalEnrollment + totalTextbook - totalDiscount - totalMileDiscount;

              return (
                <>
                  {/* ===== 合計金額サマリー ===== */}
                  <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl p-4 mb-4 shadow-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Calendar className="w-4 h-4" />
                      <span className="text-sm opacity-90">
                        {contractYear === "all" && contractMonth === "all"
                          ? "全期間"
                          : contractYear === "all"
                          ? `${contractMonth}月分（全年）`
                          : contractMonth === "all"
                          ? `${contractYear}年（全月）`
                          : `${contractYear}年${contractMonth}月分`}
                      </span>
                      <span className="text-xs opacity-75 ml-1">
                        ({filteredContracts.length}件の契約)
                      </span>
                    </div>
                    <div className="text-3xl font-bold mb-2">
                      ¥{grandTotal.toLocaleString()}
                      <span className="text-sm font-normal opacity-75 ml-2">（税込）</span>
                    </div>
                    <div className="text-xs opacity-80 space-y-0.5">
                      {totalMonthly > 0 && <div>月額: ¥{totalMonthly.toLocaleString()}</div>}
                      {totalEnrollment > 0 && <div>入会時費用: ¥{totalEnrollment.toLocaleString()}</div>}
                      {totalTextbook > 0 && <div>教材費: ¥{totalTextbook.toLocaleString()}</div>}
                      {totalDiscount > 0 && <div className="text-yellow-200">割引: -¥{totalDiscount.toLocaleString()}</div>}
                      {totalMileDiscount > 0 && <div className="text-green-200">マイル: -¥{totalMileDiscount.toLocaleString()}</div>}
                    </div>
                  </div>

                  {/* ===== ブランド別サマリー ===== */}
                  {brandTotals.size > 1 && (
                    <div className="grid grid-cols-2 gap-2 mb-4">
                      {Array.from(brandTotals.entries()).map(([brand, totals]) => {
                        const brandTotal = totals.monthly + totals.enrollment + totals.textbook - totals.discount;
                        return (
                          <div key={brand} className="bg-gray-50 rounded-lg p-2 text-xs">
                            <div className="font-medium text-gray-700 truncate">{brand}</div>
                            <div className="text-blue-600 font-bold">¥{brandTotal.toLocaleString()}</div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {filteredContracts.length > 0 ? (
              <div className="space-y-3">
                {filteredContracts.map((contract) => {
                  // 除外される設備費をチェックするヘルパー
                  const isFacilityExcluded = (item: any) => {
                    const itemType = (item.item_type || item.itemType || '').toLowerCase();
                    if (!facilityTypes.includes(itemType)) return false;
                    const itemId = item.id || item.product_id || item.productId || '';
                    return excludedFacilitySet.has(`${contract.id}-${itemId}`);
                  };

                  // 各種フィールド取得
                  const courseName = contract.course_name || contract.courseName || "";
                  const brandName = contract.brand_name || contract.brandName || "";
                  const schoolName = contract.school_name || contract.schoolName || "";
                  const contractNo = contract.contract_no || contract.contractNo || "";
                  const contractName = courseName || brandName || contractNo || "-";
                  // monthlyTotalは後でフィルタ後のアイテムから計算
                  const originalMonthlyTotal = contract.monthly_total || contract.monthlyTotal || 0;
                  const discountApplied = contract.discount_applied || contract.discountApplied || 0;
                  const discountType = contract.discount_type || contract.discountType || "";
                  const dayOfWeek = contract.day_of_week || contract.dayOfWeek;
                  const startTime = contract.start_time || contract.startTime || "";

                  // 生徒商品（明細）を取得
                  const allStudentItems = contract.student_items || contract.studentItems || [];

                  // 契約の開始月を取得（この契約の請求月）
                  const contractStartDate = contract.start_date || contract.startDate || "";
                  const contractBillingMonth = contractStartDate ? contractStartDate.substring(0, 7) : ""; // "YYYY-MM"

                  // billing_monthを正規化する関数（"202503" → "2025-03", "2025-03" → "2025-03"）
                  const normalizeBillingMonth = (bm: string): string => {
                    if (!bm) return "";
                    // 既に "YYYY-MM" 形式の場合
                    if (bm.includes("-")) return bm;
                    // "YYYYMM" 形式の場合
                    if (bm.length === 6) return `${bm.substring(0, 4)}-${bm.substring(4, 6)}`;
                    return bm;
                  };

                  // 契約内のすべてのStudentItemsを表示（フィルタなし）
                  // ※ 契約の絞り込みは filteredContracts で行われているため、
                  //    各契約内のアイテムはすべて表示する（入会時費用、月額費用、教材費など）
                  const studentItems = allStudentItems;

                  // 割引情報を取得
                  const discounts = contract.discounts || [];
                  const discountTotal = contract.discount_total || contract.discountTotal || 0;

                  // 請求月を取得（フィルタ後のStudentItemから）
                  const billingMonths = Array.from(new Set(studentItems.map((item: { billing_month?: string; billingMonth?: string }) =>
                    item.billing_month || item.billingMonth
                  ).filter(Boolean)));
                  const billingMonthLabel = billingMonths.length > 0 ? billingMonths.join(", ") : "";

                  // 一回限りの費用タイプ（月額合計から除外）
                  // ※ textbook/material は2ヶ月目以降の教材費なので入会時費用から除外
                  const oneTimeItemTypes = [
                    'enrollment', 'enrollment_tuition', 'enrollment_monthly_fee',
                    'enrollment_facility', 'enrollment_textbook', 'enrollment_expense',
                    'enrollment_management', 'bag', 'abacus'
                  ];

                  // 2ヶ月目以降の教材費タイプ
                  const textbookItemTypes = ['textbook', 'material'];

                  // 月額アイテムと一回限りアイテムを分離
                  const monthlyItems = studentItems.filter((item: any) => {
                    const itemType = (item.item_type || item.itemType || '').toLowerCase();
                    const itemName = (item.product_name || item.productName || '').toLowerCase();
                    // 入会時費用、教材費を除外
                    if (oneTimeItemTypes.includes(itemType)) return false;
                    if (textbookItemTypes.includes(itemType)) return false;
                    if (itemName.includes('入会金')) return false;
                    return true;
                  });

                  const oneTimeItems = studentItems.filter((item: any) => {
                    const itemType = (item.item_type || item.itemType || '').toLowerCase();
                    const itemName = (item.product_name || item.productName || '').toLowerCase();
                    if (oneTimeItemTypes.includes(itemType)) return true;
                    if (itemName.includes('入会金')) return true;
                    return false;
                  });

                  // 2ヶ月目以降の教材費アイテム
                  const textbookItems = studentItems.filter((item: any) => {
                    const itemType = (item.item_type || item.itemType || '').toLowerCase();
                    return textbookItemTypes.includes(itemType);
                  });

                  // フィルタ後のアイテムから月額合計を計算（一回限りの費用と除外設備費を除外）
                  const monthlyTotal = monthlyItems.length > 0
                    ? monthlyItems.reduce((sum: number, item: any) => {
                        // 除外された設備費は合計から除外
                        if (isFacilityExcluded(item)) return sum;
                        const price = Number(item.final_price || item.finalPrice || item.unit_price || item.unitPrice || 0);
                        return sum + price;
                      }, 0)
                    : originalMonthlyTotal;

                  // 一回限りの費用合計
                  const oneTimeTotal = oneTimeItems.reduce((sum: number, item: { final_price?: number | string; finalPrice?: number | string; unit_price?: number | string; unitPrice?: number | string }) => {
                    const price = Number(item.final_price || item.finalPrice || item.unit_price || item.unitPrice || 0);
                    return sum + price;
                  }, 0);

                  // 曜日表示
                  const dayOfWeekLabel = dayOfWeek ? ["", "月", "火", "水", "木", "金", "土", "日"][dayOfWeek] || "" : "";

                  // 日付フォーマット（YYYY-MM形式）
                  const startDateStr = contract.start_date || contract.startDate;
                  const endDateStr = contract.end_date || contract.endDate;
                  const formatYearMonth = (dateStr: string | null | undefined) => {
                    if (!dateStr) return "-";
                    const date = new Date(dateStr);
                    if (isNaN(date.getTime())) return "-";
                    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
                  };
                  const startYearMonth = formatYearMonth(startDateStr);
                  const endYearMonth = formatYearMonth(endDateStr);
                  const status = contract.status || "";

                  // ステータスカラー
                  const statusColor = status === "active" ? "bg-green-100 text-green-700 border-green-300"
                    : status === "cancelled" ? "bg-red-100 text-red-700 border-red-300"
                    : "bg-gray-100 text-gray-700 border-gray-300";

                  return (
                    <div key={contract.id} className="border rounded-lg overflow-hidden hover:shadow-md transition-shadow">
                      {/* ヘッダー */}
                      <div className="bg-gray-50 px-4 py-2 flex items-center justify-between border-b">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm">{contractName}</span>
                          <Badge className={`text-xs ${statusColor}`}>
                            {getContractStatusLabel(status)}
                          </Badge>
                          {startYearMonth !== "-" && (
                            <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                              {/* フィルターで年月指定がある場合はフィルター月を表示、なければ契約の初回請求月を表示 */}
                              {(contractYear !== "all" && contractMonth !== "all")
                                ? `${contractYear}-${String(contractMonth).padStart(2, '0')}`
                                : getContractBillingMonth(contract)}請求分
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">No. {contractNo}</span>
                          {isContractPeriodClosed(contract) ? (
                            <span
                              className="h-6 px-2 flex items-center text-xs text-gray-400 bg-gray-100 rounded"
                              title="締め済みのため編集不可"
                            >
                              締め済み
                            </span>
                          ) : (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 w-6 p-0 text-gray-500 hover:text-blue-600"
                              onClick={() => {
                                setEditingContract(contract);
                                setEditDialogOpen(true);
                              }}
                            >
                              <Pencil className="w-3 h-3" />
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* 基本情報 */}
                      <div className="px-4 py-2 border-b bg-white">
                        <div className="grid grid-cols-4 gap-2 text-xs">
                          <div>
                            <span className="text-gray-500">ブランド:</span>
                            <span className="font-medium ml-1">{brandName || "-"}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">校舎:</span>
                            <span className="font-medium ml-1">{schoolName || "-"}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">曜日:</span>
                            <span className="font-medium ml-1">
                              {dayOfWeekLabel ? `${dayOfWeekLabel}曜 ${startTime || ""}` : "-"}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">期間:</span>
                            <span className="font-medium ml-1">{startYearMonth} 〜 {endYearMonth}</span>
                          </div>
                        </div>
                      </div>

                      {/* 教材費選択 */}
                      {(() => {
                        const textbookOptions = contract.textbook_options || contract.textbookOptions || [];
                        const selectedIds = new Set(contract.selected_textbook_ids || contract.selectedTextbookIds || []);

                        if (textbookOptions.length > 0) {
                          return (
                            <div className="px-4 py-2 border-b bg-amber-50">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-xs font-medium text-amber-700">教材費選択:</span>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {textbookOptions.map((option: { id: string; product_name?: string; productName?: string; price: number }) => {
                                  const isSelected = selectedIds.has(option.id);
                                  const optionName = option.product_name || option.productName || "教材費";

                                  return (
                                    <label
                                      key={option.id}
                                      className={`flex items-center gap-1 px-2 py-1 rounded border cursor-pointer text-xs transition-colors ${
                                        isSelected
                                          ? 'bg-amber-200 border-amber-400 text-amber-800'
                                          : 'bg-white border-gray-200 text-gray-600 hover:border-amber-300'
                                      }`}
                                    >
                                      <input
                                        type="checkbox"
                                        checked={isSelected}
                                        onChange={async (e) => {
                                          const newSelectedIds = new Set(selectedIds);
                                          if (e.target.checked) {
                                            newSelectedIds.add(option.id);
                                          } else {
                                            newSelectedIds.delete(option.id);
                                          }

                                          try {
                                            await apiClient.post(`/contracts/${contract.id}/update-textbooks/`, {
                                              selected_textbook_ids: Array.from(newSelectedIds)
                                            });
                                            onRefresh?.();
                                          } catch (err) {
                                            console.error('Failed to update textbooks:', err);
                                            alert('教材費の更新に失敗しました');
                                          }
                                        }}
                                        className="w-3 h-3"
                                        disabled={false}
                                      />
                                      <span>{optionName}</span>
                                      <span className="text-gray-500">¥{option.price.toLocaleString()}</span>
                                    </label>
                                  );
                                })}
                              </div>
                              {selectedIds.size === 0 && (
                                <p className="text-xs text-amber-600 mt-1">※ 教材費が選択されていません</p>
                              )}
                            </div>
                          );
                        }
                        return null;
                      })()}

                      {/* 料金内訳（カテゴリ別シンプル表示） */}
                      <div className="p-3">
                        {(() => {
                          // 契約開始日から請求月を計算
                          const contractStartDate = contract.start_date || contract.startDate;
                          let startMonth = '';
                          let startYear = 0;
                          let startMonthNum = 0;
                          if (contractStartDate) {
                            const d = new Date(contractStartDate);
                            if (!isNaN(d.getTime())) {
                              startYear = d.getFullYear();
                              startMonthNum = d.getMonth() + 1;
                              startMonth = `${startYear}-${String(startMonthNum).padStart(2, '0')}`;
                            }
                          }

                          // 入会月かどうかを判定（契約開始日が今月以降なら入会月とみなす）
                          const today = new Date();
                          const currentYear = today.getFullYear();
                          const currentMonth = today.getMonth() + 1;
                          const isEnrollmentMonth = startYear > currentYear ||
                            (startYear === currentYear && startMonthNum >= currentMonth);

                          // 翌月、翌々月を計算
                          const getNextMonth = (year: number, month: number) => {
                            if (month === 12) return { year: year + 1, month: 1 };
                            return { year, month: month + 1 };
                          };
                          const next1 = getNextMonth(startYear, startMonthNum);
                          const next2 = getNextMonth(next1.year, next1.month);

                          // 請求月ラベルの生成
                          const formatMonthLabel = (year: number, month: number) => {
                            return `${year}年${month}月請求分`;
                          };

                          // アイテムを種別で分類
                          const enrollmentItems = studentItems.filter((item: any) => {
                            const itemType = (item.item_type || item.itemType || '').toLowerCase();
                            const itemName = (item.product_name || item.productName || '').toLowerCase();
                            if (oneTimeItemTypes.includes(itemType)) return true;
                            if (itemName.includes('入会金')) return true;
                            return false;
                          });

                          // 季節講習会・特別費用の判定用ヘルパー（先に定義）
                          const checkSeasonalOrSpecial = (itemName: string): boolean => {
                            const name = itemName.toLowerCase();
                            return name.includes('春期') || name.includes('夏期') ||
                                   name.includes('冬期') || name.includes('講習') ||
                                   name.includes('合宿') || name.includes('テスト対策') ||
                                   name.includes('模試');
                          };

                          // 月額費用（季節講習会・特別費用は除外）
                          const monthlyItems2 = studentItems.filter((item: any) => {
                            const itemType = (item.item_type || item.itemType || '').toLowerCase();
                            const itemName = (item.product_name || item.productName || '');
                            if (oneTimeItemTypes.includes(itemType)) return false;
                            if (textbookItemTypes.includes(itemType)) return false;
                            if (itemName.includes('入会金')) return false;
                            if (checkSeasonalOrSpecial(itemName)) return false; // 季節講習会を除外
                            return true;
                          });

                          // 季節講習会・特別費用
                          const seasonalItems = studentItems.filter((item: any) => {
                            const itemType = (item.item_type || item.itemType || '').toLowerCase();
                            const itemName = (item.product_name || item.productName || '');
                            if (oneTimeItemTypes.includes(itemType)) return false;
                            if (textbookItemTypes.includes(itemType)) return false;
                            return checkSeasonalOrSpecial(itemName);
                          });

                          const textbookItems2 = studentItems.filter((item: any) => {
                            const itemType = (item.item_type || item.itemType || '').toLowerCase();
                            return textbookItemTypes.includes(itemType);
                          });

                          // 税込価格計算用関数（消費税10%）
                          const withTax = (price: number) => Math.floor(price * 1.1);

                          // 季節講習会・特別費用の判定（春期・夏期・冬期講習、テスト対策、模試代など）
                          const isSeasonalOrSpecialItem = (item: any): boolean => {
                            const itemName = (item.product_name || item.productName || '').toLowerCase();
                            return itemName.includes('春期') || itemName.includes('夏期') ||
                                   itemName.includes('冬期') || itemName.includes('講習') ||
                                   itemName.includes('合宿') || itemName.includes('テスト対策') ||
                                   itemName.includes('模試');
                          };

                          // 季節講習会の請求月を判定
                          const getSeasonalItemBillingMonths = (item: any): number[] => {
                            const itemName = (item.product_name || item.productName || '').toLowerCase();
                            if (itemName.includes('春期')) return [3, 4]; // 3月・4月請求
                            if (itemName.includes('夏期')) return [7, 8]; // 7月・8月請求
                            if (itemName.includes('冬期')) return [12, 1]; // 12月・1月請求
                            if (itemName.includes('合宿')) return [7, 8]; // 合宿は夏期扱い
                            // テスト対策・模試は年3回（5月、10月、1月）
                            if (itemName.includes('テスト対策') || itemName.includes('模試')) return [5, 10, 1];
                            return []; // 判定できない場合
                          };

                          // 季節講習会の請求月ラベル
                          const getSeasonalItemLabel = (item: any): string => {
                            const itemName = (item.product_name || item.productName || '').toLowerCase();
                            if (itemName.includes('春期')) return '3～4月請求';
                            if (itemName.includes('夏期')) return '7～8月請求';
                            if (itemName.includes('冬期')) return '12～1月請求';
                            if (itemName.includes('合宿')) return '7～8月請求';
                            if (itemName.includes('テスト対策') || itemName.includes('模試')) return '5・10・1月請求';
                            return '';
                          };

                          // 季節講習会・特別費用が当月請求かどうか
                          const isSeasonalItemDueThisMonth = (item: any): boolean => {
                            const billingMonths = getSeasonalItemBillingMonths(item);
                            if (billingMonths.length === 0) return true; // 判定できない場合は表示
                            // 現在の契約月（フィルター月 or 契約開始月）で判定
                            const checkMonth = contractMonth !== 'all' ? parseInt(contractMonth) : startMonthNum;
                            return billingMonths.includes(checkMonth);
                          };

                          // 教材費の請求タイミング判定（半年払いなど）
                          const isTextbookDueThisMonth = (item: any): boolean => {
                            const itemName = (item.product_name || item.productName || '').toLowerCase();
                            // 半年払い（4月・10月）の場合
                            if (itemName.includes('半年払い') || itemName.includes('4月') || itemName.includes('10月')) {
                              // 入会月が4月または10月の場合のみ請求
                              return startMonthNum === 4 || startMonthNum === 10;
                            }
                            // 月払いまたはその他の場合は毎月請求
                            return true;
                          };

                          // 教材費の次回請求月を取得
                          const getNextTextbookBillingMonth = (item: any): string => {
                            const itemName = (item.product_name || item.productName || '').toLowerCase();
                            if (itemName.includes('半年払い') || itemName.includes('4月') || itemName.includes('10月')) {
                              // 次の4月か10月を計算
                              if (startMonthNum >= 1 && startMonthNum <= 3) return '4月';
                              if (startMonthNum >= 4 && startMonthNum <= 9) return '10月';
                              return '翌年4月';
                            }
                            return '';
                          };

                          // 合計計算（税込み）
                          const enrollmentTotal = enrollmentItems.reduce((sum: number, item: any) =>
                            sum + withTax(Number(item.final_price || item.finalPrice || 0)), 0);

                          const monthlyTotal2 = monthlyItems2.reduce((sum: number, item: any) => {
                            if (isFacilityExcluded(item)) return sum;
                            return sum + withTax(Number(item.final_price || item.finalPrice || 0));
                          }, 0);

                          // 教材費: 当月請求分のみ合計（半年払いは4月・10月以外は含めない）
                          const textbookTotal2 = textbookItems2.reduce((sum: number, item: any) => {
                            if (!isTextbookDueThisMonth(item)) return sum;
                            return sum + withTax(Number(item.final_price || item.finalPrice || item.unit_price || item.unitPrice || 0));
                          }, 0);

                          // 季節講習会・特別費用: 該当月のみ合計
                          const seasonalTotal = seasonalItems.reduce((sum: number, item: any) => {
                            if (!isSeasonalItemDueThisMonth(item)) return sum;
                            return sum + withTax(Number(item.final_price || item.finalPrice || item.unit_price || item.unitPrice || 0));
                          }, 0);

                          const discountAmount = Number(discounts.length > 0 ? discountTotal : discountApplied);
                          const monthlyAfterDiscount = monthlyTotal2 - discountAmount;

                          // 合計計算
                          // 既存契約（入会月ではない）: 月額 + 当月請求の季節費用 + 当月請求の教材費
                          // 新規入会: 入会時費用 + 月額 + 当月請求の季節費用 + 当月請求の教材費
                          const monthlyTotal = isEnrollmentMonth
                            ? enrollmentTotal + monthlyAfterDiscount + seasonalTotal + textbookTotal2
                            : monthlyAfterDiscount + seasonalTotal + textbookTotal2;

                          return (
                            <>
                              {/* 入会時費用（新規入会の場合のみ表示） */}
                              {isEnrollmentMonth && enrollmentItems.length > 0 && (
                                <div className="mb-3">
                                  <p className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                                    <span className="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded text-[10px]">入会時</span>
                                    {startMonthNum > 0 && `${startMonthNum}月請求`}
                                  </p>
                                  <table className="w-full text-xs">
                                    <tbody>
                                      {enrollmentItems.map((item: any, idx: number) => {
                                        const categoryName = item.category_name || item.categoryName;
                                        const itemName = categoryName || item.product_name || item.productName || "-";
                                        const finalPrice = withTax(Number(item.final_price || item.finalPrice || 0));
                                        return (
                                          <tr key={item.id || idx} className="border-b border-gray-100">
                                            <td className="py-1 text-gray-700">{itemName}</td>
                                            <td className="py-1 text-right w-20">¥{finalPrice.toLocaleString()}</td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              )}

                              {/* 月額費用 */}
                              {monthlyItems2.length > 0 && (
                                <div className="mb-3">
                                  <p className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                                    <span className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded text-[10px]">月額</span>
                                    毎月請求
                                  </p>
                                  <table className="w-full text-xs">
                                    <tbody>
                                      {monthlyItems2.map((item: any, idx: number) => {
                                        const categoryName = item.category_name || item.categoryName;
                                        const itemName = categoryName || item.product_name || item.productName || "-";
                                        const finalPrice = withTax(Number(item.final_price || item.finalPrice || 0));
                                        const isExcluded = isFacilityExcluded(item);
                                        return (
                                          <tr key={item.id || idx} className={`border-b border-gray-100 ${isExcluded ? 'opacity-50' : ''}`}>
                                            <td className={`py-1 text-gray-700 ${isExcluded ? 'line-through' : ''}`}>
                                              {itemName}
                                              {isExcluded && <span className="ml-1 text-[10px] text-orange-600">(除外)</span>}
                                            </td>
                                            <td className={`py-1 text-right w-20 ${isExcluded ? 'line-through' : ''}`}>
                                              ¥{finalPrice.toLocaleString()}
                                            </td>
                                          </tr>
                                        );
                                      })}
                                      {discountAmount > 0 && (
                                        <tr className="border-b border-gray-100 text-orange-600">
                                          <td className="py-1">割引</td>
                                          <td className="py-1 text-right">-¥{discountAmount.toLocaleString()}</td>
                                        </tr>
                                      )}
                                    </tbody>
                                    <tfoot>
                                      <tr className="font-medium">
                                        <td className="pt-1 text-gray-700">月額小計</td>
                                        <td className="pt-1 text-right text-blue-600">¥{monthlyAfterDiscount.toLocaleString()}</td>
                                      </tr>
                                    </tfoot>
                                  </table>
                                </div>
                              )}

                              {/* 季節講習会・特別費用 */}
                              {seasonalItems.length > 0 && (
                                <div className="mb-3">
                                  <p className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                                    <span className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded text-[10px]">季節</span>
                                    講習会・特別費用
                                  </p>
                                  <table className="w-full text-xs">
                                    <tbody>
                                      {seasonalItems.map((item: any, idx: number) => {
                                        const categoryName = item.category_name || item.categoryName;
                                        const itemName = categoryName || item.product_name || item.productName || "-";
                                        const finalPrice = withTax(Number(item.final_price || item.finalPrice || item.unit_price || item.unitPrice || 0));
                                        const isDueThisMonth = isSeasonalItemDueThisMonth(item);
                                        const billingLabel = getSeasonalItemLabel(item);
                                        return (
                                          <tr key={item.id || idx} className={`border-b border-gray-100 ${!isDueThisMonth ? 'opacity-60' : ''}`}>
                                            <td className="py-1 text-gray-700">
                                              {itemName}
                                              {billingLabel && (
                                                <span className={`ml-1 text-[10px] ${isDueThisMonth ? 'text-green-600' : 'text-gray-400'}`}>
                                                  ({billingLabel})
                                                </span>
                                              )}
                                            </td>
                                            <td className={`py-1 text-right w-20 ${!isDueThisMonth ? 'text-gray-400' : ''}`}>
                                              {isDueThisMonth ? `¥${finalPrice.toLocaleString()}` : '-'}
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              )}

                              {/* 教材費 */}
                              {textbookItems2.length > 0 && (
                                <div className="mb-3">
                                  <p className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                                    <span className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded text-[10px]">教材</span>
                                    選択中の教材費
                                  </p>
                                  <table className="w-full text-xs">
                                    <tbody>
                                      {textbookItems2.map((item: any, idx: number) => {
                                        const categoryName = item.category_name || item.categoryName;
                                        const itemName = categoryName || item.product_name || item.productName || "-";
                                        const finalPrice = withTax(Number(item.final_price || item.finalPrice || item.unit_price || item.unitPrice || 0));
                                        const isDueThisMonth = isTextbookDueThisMonth(item);
                                        const nextBillingMonth = getNextTextbookBillingMonth(item);
                                        return (
                                          <tr key={item.id || idx} className={`border-b border-gray-100 ${!isDueThisMonth ? 'opacity-60' : ''}`}>
                                            <td className="py-1 text-gray-700">
                                              {itemName}
                                              {!isDueThisMonth && nextBillingMonth && (
                                                <span className="ml-1 text-[10px] text-amber-600">({nextBillingMonth}請求予定)</span>
                                              )}
                                            </td>
                                            <td className={`py-1 text-right w-20 ${!isDueThisMonth ? 'text-gray-400' : ''}`}>
                                              {isDueThisMonth ? `¥${finalPrice.toLocaleString()}` : '-'}
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              )}

                              {/* 合計 */}
                              <div className="mt-3 pt-3 border-t-2 border-blue-200 bg-blue-50 -mx-3 px-3 pb-3 rounded-b-lg">
                                <div className="flex justify-between items-center">
                                  <span className="text-sm font-bold text-blue-800">
                                    {isEnrollmentMonth ? '初月合計（税込）' : '当月合計（税込）'}
                                  </span>
                                  <span className="text-lg font-bold text-blue-600">¥{monthlyTotal.toLocaleString()}</span>
                                </div>
                                <p className="text-xs text-gray-500 mt-1">
                                  {isEnrollmentMonth && enrollmentTotal > 0 && `入会時 ¥${enrollmentTotal.toLocaleString()}`}
                                  {isEnrollmentMonth && enrollmentTotal > 0 && monthlyAfterDiscount > 0 && ' + '}
                                  {monthlyAfterDiscount > 0 && `月額 ¥${monthlyAfterDiscount.toLocaleString()}`}
                                  {(isEnrollmentMonth ? (enrollmentTotal > 0 || monthlyAfterDiscount > 0) : monthlyAfterDiscount > 0) && seasonalTotal > 0 && ' + '}
                                  {seasonalTotal > 0 && `講習等 ¥${seasonalTotal.toLocaleString()}`}
                                  {(monthlyAfterDiscount > 0 || seasonalTotal > 0) && textbookTotal2 > 0 && ' + '}
                                  {textbookTotal2 > 0 && `教材 ¥${textbookTotal2.toLocaleString()}`}
                                </p>
                                {isEnrollmentMonth && monthlyAfterDiscount > 0 && (
                                  <p className="text-xs text-gray-400 mt-0.5">
                                    ※ 翌月以降の月額: ¥{monthlyAfterDiscount.toLocaleString()}/月
                                  </p>
                                )}
                              </div>
                            </>
                          );
                        })()}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                {contracts.length > 0 ? "該当期間の契約がありません" : "契約情報がありません"}
              </div>
            )}
                </>
              );
            })()}
            <div className="mt-4">
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={() => setNewContractDialogOpen(true)}
              >
                <FileText className="w-4 h-4 mr-1" />
                新規契約登録
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* 請求タブ */}
        <TabsContent value="billing" className="flex-1 overflow-auto p-0 m-0">
          <div className="p-4">
            {/* 預り金残高表示 */}
            {guardianBalance !== null && (
              <div className={`mb-4 p-3 rounded-lg border ${
                guardianBalance.balance > 0
                  ? 'bg-green-50 border-green-200'
                  : guardianBalance.balance < 0
                    ? 'bg-red-50 border-red-200'
                    : 'bg-gray-50 border-gray-200'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CreditCard className="w-4 h-4 text-gray-500" />
                    <span className="text-sm font-medium text-gray-700">預り金残高</span>
                  </div>
                  <div className="text-right">
                    <span className={`text-lg font-bold ${
                      guardianBalance.balance > 0
                        ? 'text-green-600'
                        : guardianBalance.balance < 0
                          ? 'text-red-600'
                          : 'text-gray-600'
                    }`}>
                      {guardianBalance.balance >= 0 ? '' : '-'}¥{Math.abs(guardianBalance.balance).toLocaleString()}
                    </span>
                    {guardianBalance.balance > 0 && (
                      <div className="text-xs text-green-600">次回請求で相殺可能</div>
                    )}
                    {guardianBalance.balance < 0 && (
                      <div className="text-xs text-red-600">未払い残高あり</div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 年月フィルター */}
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-4 h-4 text-gray-500" />
              <Select value={invoiceYear} onValueChange={setInvoiceYear}>
                <SelectTrigger className="w-24 h-8">
                  <SelectValue placeholder="年" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全て</SelectItem>
                  {yearOptions.map((y) => (
                    <SelectItem key={y} value={String(y)}>{y}年</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={invoiceMonth} onValueChange={setInvoiceMonth}>
                <SelectTrigger className="w-20 h-8">
                  <SelectValue placeholder="月" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全て</SelectItem>
                  {monthOptions.map((m) => (
                    <SelectItem key={m} value={String(m)}>{m}月</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-xs text-gray-500 ml-2">
                {filteredInvoices.length}件
              </span>
            </div>

            {filteredInvoices.length > 0 ? (
              <div className="space-y-4">
                {/* 請求月ごとにグループ化（バケツ形式） */}
                {(() => {
                  // 請求月でグループ化
                  const groupedInvoices: Record<string, typeof invoices> = {};
                  filteredInvoices.forEach((invoice) => {
                    const billingMonth = invoice.billingMonth || invoice.billing_month || "未設定";
                    if (!groupedInvoices[billingMonth]) {
                      groupedInvoices[billingMonth] = [];
                    }
                    groupedInvoices[billingMonth].push(invoice);
                  });

                  return Object.entries(groupedInvoices).map(([month, monthInvoices]) => {
                    // 月の請求合計
                    const monthTotal = monthInvoices.reduce((sum, inv) => {
                      const amount = inv.totalAmount || inv.total_amount || 0;
                      return sum + Number(amount);
                    }, 0);

                    // 入金済み金額
                    const paidAmount = monthInvoices.reduce((sum, inv) => {
                      const paid = inv.paidAmount || inv.paid_amount || 0;
                      return sum + Number(paid);
                    }, 0);

                    // 前月繰越（マイナス=過払い、プラス=未払い）
                    const carryOver = monthInvoices.reduce((sum, inv) => {
                      const carry = inv.carryOverAmount || inv.carry_over_amount || 0;
                      return sum + Number(carry);
                    }, 0);

                    // 今月請求額（繰越含む）
                    const totalDue = monthTotal + carryOver;

                    // 残高（プラス=未払い、マイナス=過払い）
                    const balance = totalDue - paidAmount;

                    // 次月繰越が必要か
                    const needsCarryForward = balance !== 0;

                    // 残高の色
                    const balanceColor = balance > 0 ? "text-red-600" : balance < 0 ? "text-blue-600" : "text-green-600";
                    const balanceLabel = balance > 0 ? "不足" : balance < 0 ? "過払い" : "精算済";

                    return (
                      <div key={month} className="border rounded-lg overflow-hidden">
                        {/* 月ヘッダー（バケツサマリー） */}
                        <div className="bg-gradient-to-r from-gray-100 to-gray-50 px-4 py-3 border-b">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-bold text-lg">{month}</span>
                            <Badge className={`${balance === 0 ? 'bg-green-100 text-green-700' : balance > 0 ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                              {balanceLabel}
                            </Badge>
                          </div>

                          {/* 金額サマリー */}
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="space-y-1">
                              {carryOver !== 0 && (
                                <div className="flex justify-between">
                                  <span className="text-gray-500">前月繰越:</span>
                                  <span className={carryOver > 0 ? "text-red-600" : "text-blue-600"}>
                                    {carryOver > 0 ? "+" : ""}¥{carryOver.toLocaleString()}
                                  </span>
                                </div>
                              )}
                              <div className="flex justify-between">
                                <span className="text-gray-500">今月請求:</span>
                                <span className="font-medium">¥{monthTotal.toLocaleString()}</span>
                              </div>
                              <div className="flex justify-between border-t pt-1">
                                <span className="text-gray-600 font-medium">請求合計:</span>
                                <span className="font-bold">¥{totalDue.toLocaleString()}</span>
                              </div>
                            </div>
                            <div className="space-y-1 border-l pl-3">
                              <div className="flex justify-between">
                                <span className="text-gray-500">入金済み:</span>
                                <span className="font-medium text-green-600">¥{paidAmount.toLocaleString()}</span>
                              </div>
                              <div className="flex justify-between border-t pt-1">
                                <span className="text-gray-600 font-medium">残高:</span>
                                <span className={`font-bold ${balanceColor}`}>
                                  {balance > 0 ? "-" : balance < 0 ? "+" : ""}¥{Math.abs(balance).toLocaleString()}
                                </span>
                              </div>
                              {needsCarryForward && (
                                <div className="flex justify-between text-orange-600">
                                  <span className="text-xs">→ 翌月繰越</span>
                                  <span className="text-xs font-medium">
                                    {balance > 0 ? `-¥${balance.toLocaleString()}` : `+¥${Math.abs(balance).toLocaleString()}`}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* 明細 */}
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-3 py-2 text-left border-r">内容</th>
                              <th className="px-3 py-2 text-right border-r w-20">請求額</th>
                              <th className="px-3 py-2 text-right border-r w-20">入金額</th>
                              <th className="px-3 py-2 text-left border-r w-16">方法</th>
                              <th className="px-3 py-2 text-left w-16">状態</th>
                            </tr>
                          </thead>
                          <tbody>
                            {monthInvoices.map((invoice) => {
                              const totalAmount = invoice.totalAmount || invoice.total_amount || 0;
                              const paidAmt = invoice.paidAmount || invoice.paid_amount || 0;
                              const status = invoice.status || "";
                              const paymentMethod = invoice.paymentMethod || invoice.payment_method || "direct_debit";
                              const description = invoice.description || invoice.invoiceNo || invoice.invoice_no || "-";
                              const courseName = invoice.courseName || invoice.course_name || "";
                              const brandName = invoice.brandName || invoice.brand_name || "";

                              // 支払方法の表示
                              const paymentMethodLabel = paymentMethod === "direct_debit" ? "引落"
                                : paymentMethod === "bank_transfer" ? "振込"
                                : paymentMethod === "credit_card" ? "カード"
                                : paymentMethod === "cash" ? "現金"
                                : paymentMethod;

                              return (
                                <tr key={invoice.id} className="border-b hover:bg-gray-50">
                                  <td className="px-3 py-2 border-r">
                                    <div className="text-xs">
                                      <span className="font-medium">{courseName || description}</span>
                                      {brandName && <span className="text-gray-400 ml-1">({brandName})</span>}
                                    </div>
                                  </td>
                                  <td className="px-3 py-2 border-r text-right text-xs">¥{Number(totalAmount).toLocaleString()}</td>
                                  <td className="px-3 py-2 border-r text-right text-xs">
                                    {Number(paidAmt) > 0 ? (
                                      <span className="text-green-600">¥{Number(paidAmt).toLocaleString()}</span>
                                    ) : (
                                      <span className="text-gray-400">-</span>
                                    )}
                                  </td>
                                  <td className="px-3 py-2 border-r">
                                    <Badge variant="secondary" className="text-xs px-1">
                                      {paymentMethodLabel}
                                    </Badge>
                                  </td>
                                  <td className="px-3 py-2">
                                    <Badge
                                      variant="outline"
                                      className={`text-xs px-1 ${status === 'paid' ? 'bg-green-50 text-green-700' : status === 'overdue' ? 'bg-red-50 text-red-700' : status === 'partial' ? 'bg-yellow-50 text-yellow-700' : ''}`}
                                    >
                                      {getInvoiceStatusLabel(status)}
                                    </Badge>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    );
                  });
                })()}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                {invoices.length > 0 ? "該当期間の請求がありません" : "請求情報がありません"}
              </div>
            )}
            <div className="mt-4">
              <Button size="sm" variant="outline" className="w-full">
                <CreditCard className="w-4 h-4 mr-1" />
                請求書発行
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* 生徒カルテタブ */}
        <TabsContent value="communications" className="flex-1 overflow-auto p-0 m-0">
          <div className="p-4 space-y-4">
            {/* 日付範囲フィルター */}
            <div className="flex items-center gap-2 flex-wrap bg-gray-50 p-2 rounded-lg">
              <Calendar className="w-4 h-4 text-gray-500" />
              <Input
                type="date"
                value={commDateFrom}
                onChange={(e) => setCommDateFrom(e.target.value)}
                className="w-36 h-8 text-sm"
              />
              <span className="text-gray-400">〜</span>
              <Input
                type="date"
                value={commDateTo}
                onChange={(e) => setCommDateTo(e.target.value)}
                className="w-36 h-8 text-sm"
              />
              {(commDateFrom || commDateTo) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearCommDateFilter}
                  className="h-8 text-xs"
                >
                  クリア
                </Button>
              )}
            </div>

            {/* サブタブ切り替え */}
            <div className="flex gap-1 border-b">
              <button
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  commTab === "logs"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
                onClick={() => setCommTab("logs")}
              >
                対応履歴 ({filteredContactLogs.length})
              </button>
              <button
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  commTab === "chat"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
                onClick={() => setCommTab("chat")}
              >
                チャット ({filteredMessages.length})
              </button>
              <button
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  commTab === "requests"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
                onClick={() => setCommTab("requests")}
              >
                申請履歴 ({suspensionRequests.length + withdrawalRequests.length})
              </button>
            </div>

            {/* 対応履歴 */}
            {commTab === "logs" && (
              <div className="space-y-3">
                {/* 追加ボタン */}
                <div className="flex justify-end">
                  <Button
                    size="sm"
                    onClick={() => setContactLogDialogOpen(true)}
                    className="flex items-center gap-1"
                  >
                    <Plus className="w-4 h-4" />
                    対応履歴を追加
                  </Button>
                </div>

                {filteredContactLogs.length > 0 ? (
                  filteredContactLogs.map((log) => (
                    <div key={log.id} className="border rounded-lg p-3 hover:bg-gray-50">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {getContactTypeLabel(log.contact_type)}
                          </Badge>
                          <Badge className={`text-xs ${getContactStatusColor(log.status)}`}>
                            {getContactStatusLabel(log.status)}
                          </Badge>
                        </div>
                        <span className="text-xs text-gray-400">
                          {log.created_at ? new Date(log.created_at).toLocaleDateString("ja-JP", {
                            year: 'numeric',
                            month: 'numeric',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          }) : "-"}
                        </span>
                      </div>
                      {/* 誰から誰へ */}
                      <div className="text-xs text-gray-500 mb-1">
                        {log.handled_by_name || "スタッフ"} → {log.guardian_name || log.student_name || student.full_name}
                      </div>
                      <h4 className="font-medium text-sm mb-1">{log.subject}</h4>
                      <p className="text-xs text-gray-600 whitespace-pre-wrap">{log.content}</p>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-gray-500 py-8 text-sm">
                    {localContactLogs.length === 0
                      ? "対応履歴がありません"
                      : "該当する期間の対応履歴がありません"}
                  </div>
                )}
              </div>
            )}

            {/* チャット履歴 - スレッド表示 */}
            {commTab === "chat" && (
              <div className="border rounded-lg bg-gray-50 overflow-hidden">
                {selectedChannel ? (
                  /* メッセージ表示画面 */
                  <div className="flex flex-col h-[60vh]">
                    {/* ヘッダー */}
                    <div className="flex items-center gap-2 px-3 py-2 bg-white border-b">
                      <button
                        onClick={handleBackToChannelList}
                        className="p-1 hover:bg-gray-100 rounded"
                      >
                        <ArrowLeft className="w-4 h-4 text-gray-500" />
                      </button>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{selectedChannel.name}</p>
                        <p className="text-xs text-gray-500">
                          {selectedChannel.guardian?.fullName || "保護者"}
                        </p>
                      </div>
                    </div>

                    {/* メッセージ一覧 */}
                    <div className="flex-1 overflow-y-auto p-3 space-y-2">
                      {messagesLoading ? (
                        <div className="flex items-center justify-center h-full">
                          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                        </div>
                      ) : channelMessages.length === 0 ? (
                        <div className="flex items-center justify-center h-full">
                          <div className="text-center text-gray-500 text-sm">
                            <MessageCircle className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                            メッセージがありません
                          </div>
                        </div>
                      ) : (
                        channelMessages.map((msg) => {
                          const isStaff = !msg.senderGuardian;
                          return (
                            <div
                              key={msg.id}
                              className={`flex ${isStaff ? "justify-end" : "justify-start"}`}
                            >
                              <div
                                className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                                  isStaff
                                    ? "bg-blue-600 text-white"
                                    : "bg-white border text-gray-800"
                                }`}
                              >
                                {!isStaff && (
                                  <p className="text-xs text-gray-500 mb-1">
                                    {msg.senderGuardianName || msg.senderName || "保護者"}
                                  </p>
                                )}
                                {/* 画像メッセージの場合 */}
                                {(() => {
                                  const msgType = msg.messageType || (msg as any).message_type || '';
                                  const attachUrl = msg.attachmentUrl || msg.attachment_url;
                                  const attachName = msg.attachmentName || msg.attachment_name;
                                  const isImage = msgType.toUpperCase() === 'IMAGE' && attachUrl;

                                  if (isImage) {
                                    return (
                                      <div className="mb-1">
                                        <img
                                          src={attachUrl}
                                          alt={attachName || "添付画像"}
                                          className="max-w-full max-h-64 rounded cursor-pointer hover:opacity-90"
                                          onClick={() => window.open(attachUrl, '_blank')}
                                        />
                                        {msg.content && msg.content !== attachName && (
                                          <p className="whitespace-pre-wrap mt-1">{msg.content}</p>
                                        )}
                                      </div>
                                    );
                                  }
                                  return <p className="whitespace-pre-wrap">{msg.content}</p>;
                                })()}
                                <p className={`text-xs mt-1 ${isStaff ? "text-blue-200" : "text-gray-400"}`}>
                                  {formatMsgTime(msg.createdAt)}
                                </p>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>

                    {/* 入力エリア */}
                    <div className="border-t bg-white p-2">
                      {/* 画像プレビュー */}
                      {filePreviewUrl && (
                        <div className="mb-2 relative inline-block">
                          <img
                            src={filePreviewUrl}
                            alt="プレビュー"
                            className="max-h-32 rounded border"
                          />
                          <button
                            onClick={clearPendingFile}
                            className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                            type="button"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                      <div className="flex gap-2">
                        {/* 隠しファイル入力 */}
                        <input
                          type="file"
                          ref={fileInputRef}
                          onChange={handleFileInputChange}
                          accept="image/*"
                          className="hidden"
                        />
                        {/* ファイル選択ボタン */}
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={sendingMessage}
                          className="flex-shrink-0"
                          title="画像を添付 (Ctrl+Vでペーストも可能)"
                        >
                          <ImageIcon className="w-4 h-4" />
                        </Button>
                        <Input
                          value={newMessage}
                          onChange={(e) => setNewMessage(e.target.value)}
                          onPaste={handlePaste}
                          placeholder={pendingFile ? "コメントを追加（任意）..." : "メッセージを入力...（画像はCtrl+Vでペースト可）"}
                          className="flex-1 text-sm"
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                              e.preventDefault();
                              if (pendingFile) {
                                handleSendFile();
                              } else {
                                handleSendMessage();
                              }
                            }
                          }}
                          disabled={sendingMessage}
                        />
                        <Button
                          size="sm"
                          onClick={pendingFile ? handleSendFile : handleSendMessage}
                          disabled={(!newMessage.trim() && !pendingFile) || sendingMessage}
                          className="bg-blue-600 hover:bg-blue-700"
                        >
                          {sendingMessage ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Send className="w-4 h-4" />
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* スレッド一覧画面 */
                  <div className="max-h-[60vh] overflow-y-auto">
                    {/* 新規チャットボタン */}
                    <div className="p-3 border-b bg-white">
                      <Button
                        size="sm"
                        onClick={handleCreateNewChat}
                        disabled={creatingChat || parents.length === 0}
                        className="w-full bg-blue-600 hover:bg-blue-700"
                      >
                        {creatingChat ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                          <Plus className="w-4 h-4 mr-2" />
                        )}
                        新規チャット
                      </Button>
                    </div>

                    {/* スレッド一覧 */}
                    {channelsLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                      </div>
                    ) : chatChannels.length === 0 ? (
                      <div className="text-center text-gray-500 py-8 text-sm">
                        <MessageCircle className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                        チャット履歴がありません
                        <p className="text-xs text-gray-400 mt-1">上のボタンから新規チャットを開始できます</p>
                      </div>
                    ) : (
                      <div className="divide-y">
                        {chatChannels.map((channel) => {
                          // 未返信判定：未読があれば未返信とみなす
                          const hasUnread = channel.unreadCount > 0;
                          const isUnreplied = hasUnread;

                          return (
                            <button
                              key={channel.id}
                              onClick={() => setSelectedChannel(channel)}
                              className={`w-full px-3 py-3 flex items-center gap-3 hover:bg-white transition-colors text-left ${
                                hasUnread || isUnreplied ? "bg-red-50 border-l-4 border-l-red-500" : ""
                              }`}
                            >
                              <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                                hasUnread || isUnreplied ? "bg-red-100" : "bg-blue-100"
                              }`}>
                                <MessageCircle className={`w-5 h-5 ${
                                  hasUnread || isUnreplied ? "text-red-600" : "text-blue-600"
                                }`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-2">
                                  <p className="font-medium text-sm truncate">{channel.name}</p>
                                  {(hasUnread || isUnreplied) && (
                                    <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                                      {hasUnread ? channel.unreadCount : "未返信"}
                                    </span>
                                  )}
                                </div>
                                {channel.lastMessage && (
                                  <p className={`text-xs truncate mt-0.5 ${
                                    hasUnread || isUnreplied ? "text-red-600 font-medium" : "text-gray-500"
                                  }`}>
                                    <span className="font-medium">{channel.lastMessage.senderName || "不明"}: </span>
                                    {channel.lastMessage.content}
                                  </p>
                                )}
                                <p className="text-xs text-gray-400 mt-0.5">
                                  {channel.lastMessage?.createdAt
                                    ? formatMsgTime(channel.lastMessage.createdAt)
                                    : formatMsgTime(channel.createdAt)}
                                </p>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 休会・退会申請履歴 */}
            {commTab === "requests" && (
              <div className="space-y-3">
                {(suspensionRequests.length > 0 || withdrawalRequests.length > 0) ? (
                  <>
                    {/* 休会申請 */}
                    {suspensionRequests.map((req) => (
                      <div key={req.id} className="border rounded-lg p-3 hover:bg-orange-50 border-orange-200">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge className="bg-orange-100 text-orange-800 text-xs">
                              休会申請
                            </Badge>
                            <Badge className={`text-xs ${
                              req.status === 'approved' ? 'bg-green-100 text-green-800' :
                              req.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                              req.status === 'rejected' ? 'bg-red-100 text-red-800' :
                              req.status === 'resumed' ? 'bg-blue-100 text-blue-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {req.status === 'approved' ? '承認済' :
                               req.status === 'pending' ? '申請中' :
                               req.status === 'rejected' ? '却下' :
                               req.status === 'resumed' ? '復会済' :
                               req.status === 'cancelled' ? '取消' : req.status}
                            </Badge>
                          </div>
                          <span className="text-xs text-gray-400">
                            {req.requested_at && new Date(req.requested_at).toLocaleDateString("ja-JP")}
                          </span>
                        </div>
                        <div className="text-sm text-gray-700">
                          <p>休会期間: {req.suspend_from} 〜 {req.suspend_until || '未定'}</p>
                          {req.keep_seat && <p className="text-xs text-orange-600">座席保持あり（休会費800円/月）</p>}
                          {req.reason_detail && <p className="text-xs text-gray-500 mt-1">{req.reason_detail}</p>}
                        </div>
                      </div>
                    ))}
                    {/* 退会申請 */}
                    {withdrawalRequests.map((req) => (
                      <div key={req.id} className="border rounded-lg p-3 hover:bg-red-50 border-red-200">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge className="bg-red-100 text-red-800 text-xs">
                              退会申請
                            </Badge>
                            <Badge className={`text-xs ${
                              req.status === 'approved' ? 'bg-green-100 text-green-800' :
                              req.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                              req.status === 'rejected' ? 'bg-red-100 text-red-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {req.status === 'approved' ? '承認済' :
                               req.status === 'pending' ? '申請中' :
                               req.status === 'rejected' ? '却下' :
                               req.status === 'cancelled' ? '取消' : req.status}
                            </Badge>
                          </div>
                          <span className="text-xs text-gray-400">
                            {req.requested_at && new Date(req.requested_at).toLocaleDateString("ja-JP")}
                          </span>
                        </div>
                        <div className="text-sm text-gray-700">
                          <p>退会日: {req.withdrawal_date}</p>
                          {req.last_lesson_date && <p className="text-xs">最終授業日: {req.last_lesson_date}</p>}
                          {req.reason_detail && <p className="text-xs text-gray-500 mt-1">{req.reason_detail}</p>}
                        </div>
                      </div>
                    ))}
                  </>
                ) : (
                  <div className="text-center text-gray-500 py-8 text-sm">
                    休会・退会申請履歴がありません
                  </div>
                )}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* フッターボタン */}
      <div className="border-t p-3 bg-gray-50">
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-orange-600 border-orange-300 hover:bg-orange-50"
            onClick={() => setSuspensionDialogOpen(true)}
            disabled={student.status === 'suspended' || student.status === 'withdrawn'}
          >
            <PauseCircle className="w-4 h-4 mr-1" />
            休会登録
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-red-600 border-red-300 hover:bg-red-50"
            onClick={() => setWithdrawalDialogOpen(true)}
            disabled={student.status === 'withdrawn'}
          >
            <XCircle className="w-4 h-4 mr-1" />
            退会登録
          </Button>
        </div>
      </div>

      {/* 生徒編集ダイアログ */}
      <Dialog open={studentEditDialogOpen} onOpenChange={setStudentEditDialogOpen}>
        <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>生徒情報の編集</DialogTitle>
            <DialogDescription>
              生徒の基本情報を編集します。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {/* 氏名 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right">氏名</Label>
              <div className="col-span-3 flex gap-2">
                <Input
                  placeholder="姓"
                  value={studentForm.last_name}
                  onChange={(e) => setStudentForm({ ...studentForm, last_name: e.target.value })}
                  className="flex-1"
                />
                <Input
                  placeholder="名"
                  value={studentForm.first_name}
                  onChange={(e) => setStudentForm({ ...studentForm, first_name: e.target.value })}
                  className="flex-1"
                />
              </div>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right">氏名（カナ）</Label>
              <div className="col-span-3 flex gap-2">
                <Input
                  placeholder="セイ"
                  value={studentForm.last_name_kana}
                  onChange={(e) => setStudentForm({ ...studentForm, last_name_kana: e.target.value })}
                  className="flex-1"
                />
                <Input
                  placeholder="メイ"
                  value={studentForm.first_name_kana}
                  onChange={(e) => setStudentForm({ ...studentForm, first_name_kana: e.target.value })}
                  className="flex-1"
                />
              </div>
            </div>
            {/* 生年月日 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="student_birth_date" className="text-right">
                生年月日
              </Label>
              <Input
                id="student_birth_date"
                type="date"
                value={studentForm.birth_date}
                onChange={(e) => setStudentForm({ ...studentForm, birth_date: e.target.value })}
                className="col-span-3"
              />
            </div>
            {/* 性別 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right">性別</Label>
              <Select
                value={studentForm.gender}
                onValueChange={(value) => setStudentForm({ ...studentForm, gender: value })}
              >
                <SelectTrigger className="col-span-3">
                  <SelectValue placeholder="選択してください" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="male">男</SelectItem>
                  <SelectItem value="female">女</SelectItem>
                  <SelectItem value="other">その他</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {/* 電話番号 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="student_phone" className="text-right">
                電話番号
              </Label>
              <Input
                id="student_phone"
                value={studentForm.phone}
                onChange={(e) => setStudentForm({ ...studentForm, phone: e.target.value })}
                className="col-span-3"
                placeholder="090-1234-5678"
              />
            </div>
            {/* メール */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="student_email" className="text-right">
                メール
              </Label>
              <Input
                id="student_email"
                type="email"
                value={studentForm.email}
                onChange={(e) => setStudentForm({ ...studentForm, email: e.target.value })}
                className="col-span-3"
                placeholder="example@email.com"
              />
            </div>
            {/* 学校名 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="student_school_name" className="text-right">
                学校名
              </Label>
              <Input
                id="student_school_name"
                value={studentForm.school_name}
                onChange={(e) => setStudentForm({ ...studentForm, school_name: e.target.value })}
                className="col-span-3"
                placeholder="〇〇小学校"
              />
            </div>
            {/* 備考 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="student_notes" className="text-right">
                備考
              </Label>
              <Textarea
                id="student_notes"
                value={studentForm.notes}
                onChange={(e) => setStudentForm({ ...studentForm, notes: e.target.value })}
                className="col-span-3"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStudentEditDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleStudentUpdate} disabled={isSubmitting}>
              {isSubmitting ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 保護者編集ダイアログ */}
      <Dialog open={guardianEditDialogOpen} onOpenChange={setGuardianEditDialogOpen}>
        <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>保護者情報の編集</DialogTitle>
            <DialogDescription>
              保護者の連絡先・住所情報を編集します。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {/* 氏名 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right">氏名</Label>
              <div className="col-span-3 flex gap-2">
                <Input
                  placeholder="姓"
                  value={guardianForm.last_name}
                  onChange={(e) => setGuardianForm({ ...guardianForm, last_name: e.target.value })}
                  className="flex-1"
                />
                <Input
                  placeholder="名"
                  value={guardianForm.first_name}
                  onChange={(e) => setGuardianForm({ ...guardianForm, first_name: e.target.value })}
                  className="flex-1"
                />
              </div>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right">氏名（カナ）</Label>
              <div className="col-span-3 flex gap-2">
                <Input
                  placeholder="セイ"
                  value={guardianForm.last_name_kana}
                  onChange={(e) => setGuardianForm({ ...guardianForm, last_name_kana: e.target.value })}
                  className="flex-1"
                />
                <Input
                  placeholder="メイ"
                  value={guardianForm.first_name_kana}
                  onChange={(e) => setGuardianForm({ ...guardianForm, first_name_kana: e.target.value })}
                  className="flex-1"
                />
              </div>
            </div>
            {/* 連絡先 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_phone" className="text-right">
                電話番号
              </Label>
              <Input
                id="guardian_phone"
                value={guardianForm.phone}
                onChange={(e) => setGuardianForm({ ...guardianForm, phone: e.target.value })}
                className="col-span-3"
                placeholder="0561-12-3456"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_mobile" className="text-right">
                携帯電話
              </Label>
              <Input
                id="guardian_mobile"
                value={guardianForm.phone_mobile}
                onChange={(e) => setGuardianForm({ ...guardianForm, phone_mobile: e.target.value })}
                className="col-span-3"
                placeholder="090-1234-5678"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_email" className="text-right">
                メールアドレス
              </Label>
              <Input
                id="guardian_email"
                type="email"
                value={guardianForm.email}
                onChange={(e) => setGuardianForm({ ...guardianForm, email: e.target.value })}
                className="col-span-3"
                placeholder="example@email.com"
              />
            </div>
            {/* 住所 */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_postal" className="text-right">
                郵便番号
              </Label>
              <Input
                id="guardian_postal"
                value={guardianForm.postal_code}
                onChange={(e) => setGuardianForm({ ...guardianForm, postal_code: e.target.value })}
                className="col-span-3"
                placeholder="488-0001"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_prefecture" className="text-right">
                都道府県
              </Label>
              <Input
                id="guardian_prefecture"
                value={guardianForm.prefecture}
                onChange={(e) => setGuardianForm({ ...guardianForm, prefecture: e.target.value })}
                className="col-span-3"
                placeholder="愛知県"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_city" className="text-right">
                市区町村
              </Label>
              <Input
                id="guardian_city"
                value={guardianForm.city}
                onChange={(e) => setGuardianForm({ ...guardianForm, city: e.target.value })}
                className="col-span-3"
                placeholder="尾張旭市"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_address1" className="text-right">
                住所1
              </Label>
              <Input
                id="guardian_address1"
                value={guardianForm.address1}
                onChange={(e) => setGuardianForm({ ...guardianForm, address1: e.target.value })}
                className="col-span-3"
                placeholder="東印場町3-9-31"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="guardian_address2" className="text-right">
                住所2
              </Label>
              <Input
                id="guardian_address2"
                value={guardianForm.address2}
                onChange={(e) => setGuardianForm({ ...guardianForm, address2: e.target.value })}
                className="col-span-3"
                placeholder="建物名・部屋番号"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setGuardianEditDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleGuardianUpdate} disabled={isSubmitting}>
              {isSubmitting ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 契約編集ダイアログ */}
      <ContractEditDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        contract={editingContract}
        onSave={async (contractId, updates) => {
          if (onContractUpdate) {
            await onContractUpdate(contractId, updates);
          }
        }}
      />

      {/* 休会登録ダイアログ */}
      <Dialog open={suspensionDialogOpen} onOpenChange={setSuspensionDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>休会登録</DialogTitle>
            <DialogDescription>
              {lastName} {firstName}さんの休会を登録します。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="suspend_from" className="text-right">
                休会開始日
              </Label>
              <Input
                id="suspend_from"
                type="date"
                value={suspensionForm.suspend_from}
                onChange={(e) => setSuspensionForm({ ...suspensionForm, suspend_from: e.target.value })}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="suspend_until" className="text-right">
                休会終了日
              </Label>
              <Input
                id="suspend_until"
                type="date"
                value={suspensionForm.suspend_until}
                onChange={(e) => setSuspensionForm({ ...suspensionForm, suspend_until: e.target.value })}
                className="col-span-3"
                placeholder="未定の場合は空欄"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right">座席保持</Label>
              <div className="col-span-3 flex items-center space-x-2">
                <Checkbox
                  id="keep_seat"
                  checked={suspensionForm.keep_seat}
                  onCheckedChange={(checked) => setSuspensionForm({ ...suspensionForm, keep_seat: !!checked })}
                />
                <label htmlFor="keep_seat" className="text-sm text-gray-600">
                  座席を保持する（休会費800円/月が発生）
                </label>
              </div>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="reason" className="text-right">
                理由
              </Label>
              <select
                id="reason"
                value={suspensionForm.reason}
                onChange={(e) => setSuspensionForm({ ...suspensionForm, reason: e.target.value })}
                className="col-span-3 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="travel">旅行・帰省</option>
                <option value="illness">病気・怪我</option>
                <option value="exam">受験準備</option>
                <option value="schedule">スケジュール都合</option>
                <option value="other">その他</option>
              </select>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="reason_detail" className="text-right">
                詳細
              </Label>
              <Textarea
                id="reason_detail"
                value={suspensionForm.reason_detail}
                onChange={(e) => setSuspensionForm({ ...suspensionForm, reason_detail: e.target.value })}
                className="col-span-3"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSuspensionDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleSuspensionSubmit} disabled={isSubmitting}>
              {isSubmitting ? '処理中...' : '休会登録'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 退会登録ダイアログ */}
      <Dialog open={withdrawalDialogOpen} onOpenChange={setWithdrawalDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>退会登録</DialogTitle>
            <DialogDescription>
              {lastName} {firstName}さんの退会を登録します。この操作は取り消せません。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="withdrawal_date" className="text-right">
                退会日
              </Label>
              <Input
                id="withdrawal_date"
                type="date"
                value={withdrawalForm.withdrawal_date}
                onChange={(e) => setWithdrawalForm({ ...withdrawalForm, withdrawal_date: e.target.value })}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="last_lesson_date" className="text-right">
                最終授業日
              </Label>
              <Input
                id="last_lesson_date"
                type="date"
                value={withdrawalForm.last_lesson_date}
                onChange={(e) => setWithdrawalForm({ ...withdrawalForm, last_lesson_date: e.target.value })}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="withdrawal_reason" className="text-right">
                理由
              </Label>
              <select
                id="withdrawal_reason"
                value={withdrawalForm.reason}
                onChange={(e) => setWithdrawalForm({ ...withdrawalForm, reason: e.target.value })}
                className="col-span-3 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="moving">転居</option>
                <option value="school_change">学校変更</option>
                <option value="graduation">卒業</option>
                <option value="schedule">スケジュール都合</option>
                <option value="financial">経済的理由</option>
                <option value="satisfaction">満足度</option>
                <option value="other_school">他塾への変更</option>
                <option value="other">その他</option>
              </select>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="withdrawal_reason_detail" className="text-right">
                詳細
              </Label>
              <Textarea
                id="withdrawal_reason_detail"
                value={withdrawalForm.reason_detail}
                onChange={(e) => setWithdrawalForm({ ...withdrawalForm, reason_detail: e.target.value })}
                className="col-span-3"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setWithdrawalDialogOpen(false)}>
              キャンセル
            </Button>
            <Button variant="destructive" onClick={handleWithdrawalSubmit} disabled={isSubmitting}>
              {isSubmitting ? '処理中...' : '退会登録'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 新規契約登録ダイアログ */}
      <NewContractDialog
        open={newContractDialogOpen}
        onOpenChange={setNewContractDialogOpen}
        student={student}
        guardian={parents[0]}
        onSuccess={() => {
          onRefresh?.();
        }}
      />

      {/* 対応履歴追加ダイアログ */}
      <Dialog open={contactLogDialogOpen} onOpenChange={setContactLogDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>対応履歴を追加</DialogTitle>
            <DialogDescription>
              {student.full_name} への対応内容を記録します
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="contact_type">対応種別</Label>
                <Select
                  value={contactLogForm.contact_type}
                  onValueChange={(value) => setContactLogForm({ ...contactLogForm, contact_type: value as ContactLogCreateData['contact_type'] })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PHONE_IN">電話（受信）</SelectItem>
                    <SelectItem value="PHONE_OUT">電話（発信）</SelectItem>
                    <SelectItem value="EMAIL_IN">メール（受信）</SelectItem>
                    <SelectItem value="EMAIL_OUT">メール（送信）</SelectItem>
                    <SelectItem value="VISIT">来校</SelectItem>
                    <SelectItem value="MEETING">面談</SelectItem>
                    <SelectItem value="ONLINE_MEETING">オンライン面談</SelectItem>
                    <SelectItem value="CHAT">チャット</SelectItem>
                    <SelectItem value="OTHER">その他</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="priority">優先度</Label>
                <Select
                  value={contactLogForm.priority}
                  onValueChange={(value) => setContactLogForm({ ...contactLogForm, priority: value as ContactLogCreateData['priority'] })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="LOW">低</SelectItem>
                    <SelectItem value="NORMAL">通常</SelectItem>
                    <SelectItem value="HIGH">高</SelectItem>
                    <SelectItem value="URGENT">緊急</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="contact_status">ステータス</Label>
              <Select
                value={contactLogForm.status}
                onValueChange={(value) => setContactLogForm({ ...contactLogForm, status: value as ContactLogCreateData['status'] })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="OPEN">未対応</SelectItem>
                  <SelectItem value="IN_PROGRESS">対応中</SelectItem>
                  <SelectItem value="RESOLVED">解決済</SelectItem>
                  <SelectItem value="CLOSED">クローズ</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="subject">件名 *</Label>
              <Input
                id="subject"
                value={contactLogForm.subject}
                onChange={(e) => setContactLogForm({ ...contactLogForm, subject: e.target.value })}
                placeholder="対応内容の件名"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="content">内容 *</Label>
              <Textarea
                id="content"
                value={contactLogForm.content}
                onChange={(e) => setContactLogForm({ ...contactLogForm, content: e.target.value })}
                placeholder="対応内容の詳細を入力"
                rows={5}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="follow_up_date">フォローアップ日</Label>
              <Input
                id="follow_up_date"
                type="date"
                value={contactLogForm.follow_up_date || ''}
                onChange={(e) => setContactLogForm({ ...contactLogForm, follow_up_date: e.target.value || undefined })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setContactLogDialogOpen(false)} disabled={isSubmittingContactLog}>
              キャンセル
            </Button>
            <Button onClick={handleCreateContactLog} disabled={isSubmittingContactLog}>
              {isSubmittingContactLog ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  保存中...
                </>
              ) : (
                '保存'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* QRコード拡大ダイアログ */}
      <Dialog open={qrCodeDialogOpen} onOpenChange={setQrCodeDialogOpen}>
        <DialogContent className="max-w-xs">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <QrCode className="w-5 h-5" />
              出席用QRコード
            </DialogTitle>
            <DialogDescription>
              このQRコードを校舎のタブレットにかざして出席
            </DialogDescription>
          </DialogHeader>
          {qrCodeInfo && (
            <div className="flex flex-col items-center py-4">
              <div className="bg-white p-4 rounded-xl border-2 border-gray-200">
                <QRCodeCanvas value={qrCodeInfo.qr_code} size={200} level="H" includeMargin={true} />
              </div>
              <div className="mt-4 text-center">
                <p className="font-bold text-gray-800">{qrCodeInfo.student_name}</p>
                <p className="text-sm text-gray-500">生徒番号: {qrCodeInfo.student_no}</p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setQrCodeDialogOpen(false)}>
              閉じる
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
