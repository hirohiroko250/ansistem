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
import { Search, X, Check, FileText, ScrollText, Receipt, BookOpen, ClipboardList, ChevronRight } from "lucide-react";
import { getStudents, type Student, type PaginatedResult } from "@/lib/api/staff";
import { useRouter } from "next/navigation";
import { useToast } from "@/hooks/use-toast";
import apiClient from "@/lib/api/client";

interface MessageMemoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MessageMemoModal({ isOpen, onClose }: MessageMemoModalProps) {
  const { toast } = useToast();
  const router = useRouter();
  const [step, setStep] = useState<"search" | "form">("search");
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);

  // 検索フィールド
  const [guardianId, setGuardianId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [lastName, setLastName] = useState("");
  const [firstName, setFirstName] = useState("");

  // 検索結果
  const [searchResults, setSearchResults] = useState<Student[]>([]);
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

  const handleSelectStudent = (student: Student) => {
    setSelectedStudent(student);
    setStep("form");
  };

  const handleClearSearch = () => {
    setGuardianId("");
    setStudentId("");
    setLastName("");
    setFirstName("");
    setSearchResults([]);
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

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
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
                    placeholder="保護者ID"
                    className="h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs text-gray-500">生徒ID</Label>
                  <Input
                    value={studentId}
                    onChange={(e) => setStudentId(e.target.value)}
                    placeholder="生徒ID"
                    className="h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs text-gray-500">苗字</Label>
                  <Input
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="苗字"
                    className="h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs text-gray-500">お名前</Label>
                  <Input
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
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
                      <TableHead className="w-12">No.</TableHead>
                      <TableHead>家族ID</TableHead>
                      <TableHead>生徒ID</TableHead>
                      <TableHead>学年</TableHead>
                      <TableHead>苗字</TableHead>
                      <TableHead>お名前</TableHead>
                      <TableHead>性別</TableHead>
                      <TableHead className="w-24">アクション</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {searchResults.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center text-gray-500 py-8">
                          {isSearching ? "検索中..." : "データがありません"}
                        </TableCell>
                      </TableRow>
                    ) : (
                      searchResults.map((student, index) => (
                        <TableRow
                          key={student.id}
                          className="cursor-pointer hover:bg-blue-50"
                          onClick={() => handleSelectStudent(student)}
                        >
                          <TableCell>{index + 1}</TableCell>
                          <TableCell>{student.guardian_no || student.guardianNo || "-"}</TableCell>
                          <TableCell>{student.student_no || student.studentNo || "-"}</TableCell>
                          <TableCell>{student.grade_text || student.gradeText || "-"}</TableCell>
                          <TableCell>{student.last_name || student.lastName || "-"}</TableCell>
                          <TableCell>{student.first_name || student.firstName || "-"}</TableCell>
                          <TableCell>{student.gender === "male" ? "男" : student.gender === "female" ? "女" : "-"}</TableCell>
                          <TableCell>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectStudent(student);
                              }}
                            >
                              選択
                            </Button>
                          </TableCell>
                        </TableRow>
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
              <Button variant="outline" onClick={onClose}>
                戻る
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
