"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Search, X, Check, FileText, ScrollText, Receipt, BookOpen, ClipboardList, ChevronDown, ChevronRight, User, Phone, Mail, MessageSquare, UserX } from "lucide-react";
import { getStudents, getStudentDetail, getStudentParents, type Student, type PaginatedResult, type Parent } from "@/lib/api/staff";
import { useRouter } from "next/navigation";
import { useToast } from "@/hooks/use-toast";
import apiClient from "@/lib/api/client";

interface MessageMemoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface StudentWithDetails extends Student {
  parents?: Parent[];
  loadingDetails?: boolean;
}

export function MessageMemoModal({ isOpen, onClose }: MessageMemoModalProps) {
  const { toast } = useToast();
  const router = useRouter();
  const [step, setStep] = useState<"search" | "form">("search");
  const [selectedStudent, setSelectedStudent] = useState<StudentWithDetails | null>(null);
  const [expandedStudentId, setExpandedStudentId] = useState<string | null>(null);

  // 検索フィールド
  const [guardianId, setGuardianId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [lastName, setLastName] = useState("");
  const [firstName, setFirstName] = useState("");

  // 検索結果
  const [searchResults, setSearchResults] = useState<StudentWithDetails[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // メモフォーム
  const [memoContent, setMemoContent] = useState("");
  const [priority, setPriority] = useState<string>("normal");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      // モーダルが閉じたらリセット
      setStep("search");
      setSelectedStudent(null);
      setExpandedStudentId(null);
      setGuardianId("");
      setStudentId("");
      setLastName("");
      setFirstName("");
      setSearchResults([]);
      setMemoContent("");
      setPriority("normal");
    }
  }, [isOpen]);

  const handleSearch = async () => {
    setIsSearching(true);
    try {
      const searchQuery = [lastName, firstName].filter(Boolean).join(" ");
      const result = await getStudents({
        search: searchQuery || undefined,
        student_no: studentId || undefined,
        page: 1,
        page_size: 50,
      });

      // guardian_noでフィルタ（APIがサポートしていない場合はフロントでフィルタ）
      let filtered = result.data;
      if (guardianId) {
        filtered = filtered.filter(s =>
          (s.guardian_no || s.guardianNo || "").includes(guardianId)
        );
      }

      setSearchResults(filtered);
      setExpandedStudentId(null);
    } catch (error) {
      console.error("Search error:", error);
      toast({
        title: "検索エラー",
        description: "生徒の検索に失敗しました",
        variant: "destructive",
      });
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleToggleExpand = async (student: StudentWithDetails) => {
    if (expandedStudentId === student.id) {
      setExpandedStudentId(null);
      return;
    }

    setExpandedStudentId(student.id);

    // 詳細情報がまだ読み込まれていない場合は読み込む
    if (!student.parents) {
      // 検索結果を更新してロード中表示
      setSearchResults(prev => prev.map(s =>
        s.id === student.id ? { ...s, loadingDetails: true } : s
      ));

      try {
        const [detail, parents] = await Promise.all([
          getStudentDetail(student.id),
          getStudentParents(student.id),
        ]);

        setSearchResults(prev => prev.map(s =>
          s.id === student.id ? {
            ...s,
            ...detail,
            parents,
            loadingDetails: false,
          } : s
        ));
      } catch (error) {
        console.error("Failed to load student details:", error);
        setSearchResults(prev => prev.map(s =>
          s.id === student.id ? { ...s, loadingDetails: false } : s
        ));
      }
    }
  };

  const handleSelectStudent = (student: StudentWithDetails) => {
    setSelectedStudent(student);
    setStep("form");
  };

  const handleClearSearch = () => {
    setGuardianId("");
    setStudentId("");
    setLastName("");
    setFirstName("");
    setSearchResults([]);
    setExpandedStudentId(null);
  };

  const handleSaveMemo = async () => {
    if (!selectedStudent || !memoContent.trim()) {
      toast({
        title: "入力エラー",
        description: "メモ内容を入力してください",
        variant: "destructive",
      });
      return;
    }

    setIsSaving(true);
    try {
      await apiClient.post("/communications/message-memos/", {
        student_id: selectedStudent.id,
        content: memoContent,
        priority: priority,
      });

      toast({
        title: "保存完了",
        description: "伝言メモを保存しました",
      });
      onClose();
    } catch (error) {
      console.error("Save error:", error);
      toast({
        title: "保存エラー",
        description: "伝言メモの保存に失敗しました",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  // 性別の表示
  const getGenderDisplay = (gender?: string) => {
    if (gender === "male") return "男";
    if (gender === "female") return "女";
    return "-";
  };

  // 画像URL取得
  const getImageUrl = (student: StudentWithDetails) => {
    return student.profile_image_url || student.profileImageUrl || null;
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-lg font-bold text-yellow-600 bg-yellow-50 px-4 py-2 -mx-6 -mt-6">
            伝言メモ
          </DialogTitle>
        </DialogHeader>

        {step === "search" ? (
          <div className="space-y-4">
            {/* 検索フォーム */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-medium mb-3">生徒検索</h3>
              <div className="grid grid-cols-4 gap-3">
                <div>
                  <Label className="text-xs text-gray-500">保護者ID</Label>
                  <Input
                    value={guardianId}
                    onChange={(e) => setGuardianId(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="保護者ID"
                    className="h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs text-gray-500">生徒ID</Label>
                  <Input
                    value={studentId}
                    onChange={(e) => setStudentId(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="生徒ID"
                    className="h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs text-gray-500">苗字</Label>
                  <Input
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="苗字"
                    className="h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs text-gray-500">お名前</Label>
                  <Input
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="お名前"
                    className="h-9"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearSearch}
                >
                  <X className="w-4 h-4 mr-1" />
                  クリア
                </Button>
                <Button
                  size="sm"
                  onClick={handleSearch}
                  disabled={isSearching}
                  className="bg-cyan-500 hover:bg-cyan-600"
                >
                  <Search className="w-4 h-4 mr-1" />
                  検索
                </Button>
              </div>
            </div>

            {/* 検索結果 */}
            <div>
              <h3 className="font-medium mb-2 text-sm text-gray-600">生徒検索結果</h3>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50">
                      <TableHead className="w-8"></TableHead>
                      <TableHead className="w-12">No.</TableHead>
                      <TableHead>保護者ID</TableHead>
                      <TableHead>個人ID</TableHead>
                      <TableHead>現在の学年</TableHead>
                      <TableHead>苗字</TableHead>
                      <TableHead>お名前</TableHead>
                      <TableHead>性別</TableHead>
                      <TableHead className="w-64">アクション</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {searchResults.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={9} className="text-center text-gray-500 py-8">
                          {isSearching ? "検索中..." : "検索条件を入力して検索してください"}
                        </TableCell>
                      </TableRow>
                    ) : (
                      searchResults.map((student, index) => (
                        <>
                          <TableRow
                            key={student.id}
                            className={`cursor-pointer hover:bg-blue-50 ${expandedStudentId === student.id ? "bg-blue-100" : ""}`}
                            onClick={() => handleToggleExpand(student)}
                          >
                            <TableCell className="p-2">
                              {expandedStudentId === student.id ? (
                                <ChevronDown className="w-4 h-4 text-blue-600" />
                              ) : (
                                <ChevronRight className="w-4 h-4 text-gray-400" />
                              )}
                            </TableCell>
                            <TableCell className="font-medium">{index + 1}</TableCell>
                            <TableCell>{student.guardian_no || student.guardianNo || "-"}</TableCell>
                            <TableCell className="font-medium text-blue-600">{student.student_no || student.studentNo || "-"}</TableCell>
                            <TableCell>{student.grade_text || student.gradeText || student.grade || "-"}</TableCell>
                            <TableCell>{student.last_name || student.lastName || "-"}</TableCell>
                            <TableCell className="font-medium">{student.first_name || student.firstName || "-"}</TableCell>
                            <TableCell>{getGenderDisplay(student.gender)}</TableCell>
                            <TableCell>
                              <div className="flex flex-wrap gap-1">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="h-6 text-[10px] px-2 bg-green-50 border-green-300 text-green-700 hover:bg-green-100"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    const studentNo = student.student_no || student.studentNo;
                                    if (studentNo) {
                                      router.push(`/billing?student_no=${studentNo}`);
                                      onClose();
                                    }
                                  }}
                                >
                                  請求一覧
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="h-6 text-[10px] px-2 bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (student.id) {
                                      router.push(`/contracts?student=${student.id}`);
                                      onClose();
                                    }
                                  }}
                                >
                                  契約情報
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="h-6 text-[10px] px-2"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (student.id) {
                                      router.push(`/students?id=${student.id}`);
                                      onClose();
                                    }
                                  }}
                                >
                                  詳細
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="h-6 text-[10px] px-2 bg-orange-50 border-orange-300 text-orange-700 hover:bg-orange-100"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleSelectStudent(student);
                                  }}
                                >
                                  退塾
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                          {/* 展開された詳細行 */}
                          {expandedStudentId === student.id && (
                            <TableRow className="bg-blue-50 border-l-4 border-l-blue-500">
                              <TableCell colSpan={9} className="p-4">
                                {student.loadingDetails ? (
                                  <div className="text-center text-gray-500 py-4">読み込み中...</div>
                                ) : (
                                  <div className="flex gap-6">
                                    {/* 写真 */}
                                    <div className="shrink-0">
                                      {getImageUrl(student) ? (
                                        <img
                                          src={getImageUrl(student)!}
                                          alt={`${student.last_name || student.lastName} ${student.first_name || student.firstName}`}
                                          className="w-24 h-32 object-cover rounded-lg border-2 border-gray-200"
                                        />
                                      ) : (
                                        <div className="w-24 h-32 bg-gray-200 rounded-lg flex items-center justify-center border-2 border-gray-300">
                                          <User className="w-12 h-12 text-gray-400" />
                                        </div>
                                      )}
                                    </div>

                                    {/* 詳細情報 */}
                                    <div className="flex-1 grid grid-cols-2 gap-4">
                                      {/* 保護者情報 */}
                                      <div className="bg-white p-3 rounded-lg border">
                                        <h4 className="text-xs font-medium text-gray-500 mb-2 border-b pb-1">保護者情報</h4>
                                        {student.parents && student.parents.length > 0 ? (
                                          student.parents.map((parent, idx) => (
                                            <div key={idx} className="space-y-1 text-sm">
                                              <div className="flex items-center gap-2">
                                                <span className="text-gray-500 text-xs w-16">保護者名</span>
                                                <span className="font-medium">{parent.full_name || parent.fullName || "-"}</span>
                                                {parent.relationship && (
                                                  <Badge variant="outline" className="text-[10px] h-4">
                                                    {parent.relationship}
                                                  </Badge>
                                                )}
                                              </div>
                                              <div className="flex items-center gap-2">
                                                <Phone className="w-3 h-3 text-gray-400" />
                                                <span className="text-xs">{parent.phone || parent.phone_mobile || "-"}</span>
                                              </div>
                                              <div className="flex items-center gap-2">
                                                <Mail className="w-3 h-3 text-gray-400" />
                                                <span className="text-xs truncate max-w-[200px]">{parent.email || "-"}</span>
                                              </div>
                                            </div>
                                          ))
                                        ) : (
                                          <p className="text-xs text-gray-400">保護者情報なし</p>
                                        )}
                                      </div>

                                      {/* 生徒情報 */}
                                      <div className="bg-white p-3 rounded-lg border">
                                        <h4 className="text-xs font-medium text-gray-500 mb-2 border-b pb-1">生徒情報</h4>
                                        <div className="space-y-1 text-sm">
                                          <div className="flex items-center gap-2">
                                            <span className="text-gray-500 text-xs w-16">生徒名</span>
                                            <span className="font-medium">
                                              {student.last_name || student.lastName} {student.first_name || student.firstName}
                                            </span>
                                          </div>
                                          <div className="flex items-center gap-2">
                                            <Phone className="w-3 h-3 text-gray-400" />
                                            <span className="text-xs">{student.phone || "-"}</span>
                                          </div>
                                          <div className="flex items-center gap-2">
                                            <Mail className="w-3 h-3 text-gray-400" />
                                            <span className="text-xs truncate max-w-[200px]">{student.email || "-"}</span>
                                          </div>
                                          <div className="flex items-center gap-2">
                                            <span className="text-gray-500 text-xs w-16">会員種別</span>
                                            <Badge variant={student.status === "enrolled" ? "default" : "secondary"} className="text-[10px]">
                                              {student.status === "enrolled" ? "在籍" : student.status === "trial" ? "体験" : student.status || "-"}
                                            </Badge>
                                          </div>
                                          <div className="flex items-center gap-2">
                                            <span className="text-gray-500 text-xs w-16">登録日</span>
                                            <span className="text-xs">{(student as any).enrollment_date || (student as any).enrollmentDate || (student as any).created_at?.slice(0, 10) || "-"}</span>
                                          </div>
                                        </div>
                                      </div>
                                    </div>

                                    {/* アクションボタン */}
                                    <div className="shrink-0 flex flex-col gap-2">
                                      <Button
                                        size="sm"
                                        className="h-8 text-xs bg-green-600 hover:bg-green-700"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          if (student.id) {
                                            router.push(`/contracts?student=${student.id}`);
                                            onClose();
                                          }
                                        }}
                                      >
                                        <FileText className="w-3 h-3 mr-1" />
                                        契約情報
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        className="h-8 text-xs"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          const studentNo = student.student_no || student.studentNo;
                                          if (studentNo) {
                                            router.push(`/billing/confirmed?student_no=${studentNo}`);
                                            onClose();
                                          }
                                        }}
                                      >
                                        <ScrollText className="w-3 h-3 mr-1" />
                                        詳細
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        className="h-8 text-xs text-orange-600 border-orange-300 hover:bg-orange-50"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          // 退塾処理へ
                                        }}
                                      >
                                        <UserX className="w-3 h-3 mr-1" />
                                        退塾
                                      </Button>
                                      <Button
                                        size="sm"
                                        className="h-8 text-xs bg-blue-600 hover:bg-blue-700"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          const guardianId = student.guardian_id || student.guardianId;
                                          if (guardianId) {
                                            router.push(`/chat?guardian=${guardianId}`);
                                            onClose();
                                          }
                                        }}
                                      >
                                        <MessageSquare className="w-3 h-3 mr-1" />
                                        チャット開始
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="secondary"
                                        className="h-8 text-xs mt-2"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          handleSelectStudent(student);
                                        }}
                                      >
                                        <Check className="w-3 h-3 mr-1" />
                                        この生徒を選択
                                      </Button>
                                    </div>
                                  </div>
                                )}
                              </TableCell>
                            </TableRow>
                          )}
                        </>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* 選択した生徒情報 - 統一フォーマット */}
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <div className="flex gap-4">
                {/* 写真 */}
                <div className="shrink-0">
                  {getImageUrl(selectedStudent!) ? (
                    <img
                      src={getImageUrl(selectedStudent!)!}
                      alt={`${selectedStudent?.last_name || selectedStudent?.lastName} ${selectedStudent?.first_name || selectedStudent?.firstName}`}
                      className="w-20 h-24 object-cover rounded-lg border-2 border-gray-200"
                    />
                  ) : (
                    <div className="w-20 h-24 bg-gray-200 rounded-lg flex items-center justify-center border-2 border-gray-300">
                      <User className="w-10 h-10 text-gray-400" />
                    </div>
                  )}
                </div>

                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">選択中の生徒</p>
                      <p className="font-bold text-lg text-gray-900">
                        {selectedStudent?.last_name || selectedStudent?.lastName}{" "}
                        {selectedStudent?.first_name || selectedStudent?.firstName}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        家族ID: {selectedStudent?.guardian_no || selectedStudent?.guardianNo || "-"} /
                        生徒ID: {selectedStudent?.student_no || selectedStudent?.studentNo || "-"}
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setStep("search")}
                    >
                      変更
                    </Button>
                  </div>
                </div>
              </div>

              {/* アクションメニュー */}
              <div className="mt-4 pt-3 border-t border-blue-200">
                <p className="text-xs text-gray-500 mb-2">アクション（個人）</p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs bg-white"
                    onClick={() => {
                      const studentNo = selectedStudent?.student_no || selectedStudent?.studentNo;
                      if (studentNo) {
                        router.push(`/billing?student_no=${studentNo}`);
                        onClose();
                      }
                    }}
                  >
                    <Receipt className="w-3 h-3 mr-1" />
                    請求一覧
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs bg-white"
                    onClick={() => {
                      const studentId = selectedStudent?.id;
                      if (studentId) {
                        router.push(`/contracts?student=${studentId}`);
                        onClose();
                      }
                    }}
                  >
                    <FileText className="w-3 h-3 mr-1" />
                    契約情報
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs bg-white"
                    onClick={() => {
                      const studentNo = selectedStudent?.student_no || selectedStudent?.studentNo;
                      if (studentNo) {
                        router.push(`/billing/confirmed?student_no=${studentNo}`);
                        onClose();
                      }
                    }}
                  >
                    <ScrollText className="w-3 h-3 mr-1" />
                    請求詳細
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs bg-white"
                    onClick={() => {
                      const guardianNo = selectedStudent?.guardian_no || selectedStudent?.guardianNo;
                      if (guardianNo) {
                        router.push(`/billing/payments?guardian_no=${guardianNo}`);
                        onClose();
                      }
                    }}
                  >
                    <BookOpen className="w-3 h-3 mr-1" />
                    通帳（家族）
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs bg-white"
                    onClick={() => {
                      const studentId = selectedStudent?.id;
                      if (studentId) {
                        router.push(`/students?selected=${studentId}&tab=karte`);
                        onClose();
                      }
                    }}
                  >
                    <ClipboardList className="w-3 h-3 mr-1" />
                    カルテ
                  </Button>
                </div>

                {/* 家族アクション */}
                {(selectedStudent?.guardian_no || selectedStudent?.guardianNo) && (
                  <>
                    <p className="text-xs text-gray-500 mb-2 mt-3">アクション（家族）</p>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs bg-white"
                        onClick={() => {
                          const guardianNo = selectedStudent?.guardian_no || selectedStudent?.guardianNo;
                          if (guardianNo) {
                            router.push(`/billing?guardian_no=${guardianNo}`);
                            onClose();
                          }
                        }}
                      >
                        <Receipt className="w-3 h-3 mr-1" />
                        請求一覧（家族）
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs bg-white"
                        onClick={() => {
                          const guardianNo = selectedStudent?.guardian_no || selectedStudent?.guardianNo;
                          if (guardianNo) {
                            router.push(`/contracts?guardian_no=${guardianNo}`);
                            onClose();
                          }
                        }}
                      >
                        <FileText className="w-3 h-3 mr-1" />
                        契約情報（家族）
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs bg-white"
                        onClick={() => {
                          const guardianNo = selectedStudent?.guardian_no || selectedStudent?.guardianNo;
                          if (guardianNo) {
                            router.push(`/billing/confirmed?guardian_no=${guardianNo}`);
                            onClose();
                          }
                        }}
                      >
                        <ScrollText className="w-3 h-3 mr-1" />
                        請求詳細（家族）
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs bg-white"
                        onClick={() => {
                          const guardianNo = selectedStudent?.guardian_no || selectedStudent?.guardianNo;
                          if (guardianNo) {
                            router.push(`/students?guardian_no=${guardianNo}&tab=karte`);
                            onClose();
                          }
                        }}
                      >
                        <ClipboardList className="w-3 h-3 mr-1" />
                        カルテ（家族）
                      </Button>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* メモ入力フォーム */}
            <div className="space-y-3">
              <div>
                <Label>優先度</Label>
                <Select value={priority} onValueChange={setPriority}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">低</SelectItem>
                    <SelectItem value="normal">通常</SelectItem>
                    <SelectItem value="high">高</SelectItem>
                    <SelectItem value="urgent">緊急</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>メモ内容</Label>
                <Textarea
                  value={memoContent}
                  onChange={(e) => setMemoContent(e.target.value)}
                  placeholder="伝言メモの内容を入力してください..."
                  rows={5}
                />
              </div>
            </div>

            {/* ボタン */}
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="outline" onClick={() => setStep("search")}>
                キャンセル
              </Button>
              <Button
                onClick={handleSaveMemo}
                disabled={isSaving || !memoContent.trim()}
                className="bg-green-600 hover:bg-green-700"
              >
                <Check className="w-4 h-4 mr-1" />
                保存
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
