"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { TaskList } from "@/components/tasks/TaskList";
import { TaskDetail } from "@/components/tasks/TaskDetail";
import { KanbanBoard } from "@/components/tasks/KanbanBoard";
import { GanttChart } from "@/components/tasks/GanttChart";
import { TaskFilters, TaskFilterValues, defaultFilterValues } from "@/components/tasks/TaskFilters";
import { TaskCreateDialog } from "@/components/tasks/TaskCreateDialog";
import { TaskComments } from "@/components/tasks/TaskComments";
import { getTasks, getTaskDetail, updateTask, Task } from "@/lib/api/staff";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Plus, LayoutGrid, List, BarChart3, Loader2 } from "lucide-react";

type ViewMode = "kanban" | "list" | "gantt";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string>();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>("kanban");
  const [filters, setFilters] = useState<TaskFilterValues>(defaultFilterValues);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  // タスク一覧取得
  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const apiFilters: Record<string, string | undefined> = {};
      if (filters.status && filters.status !== "all") {
        apiFilters.status = filters.status;
      }
      if (filters.priority && filters.priority !== "all") {
        apiFilters.priority = filters.priority;
      }
      if (filters.task_type && filters.task_type !== "all") {
        apiFilters.task_type = filters.task_type;
      }
      const data = await getTasks(apiFilters);
      setTasks(data);
    } catch (error) {
      console.error("Failed to load tasks:", error);
    } finally {
      setLoading(false);
    }
  }, [filters.status, filters.priority, filters.task_type]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  // タスク詳細取得
  useEffect(() => {
    if (selectedTaskId) {
      getTaskDetail(selectedTaskId).then(setSelectedTask);
    }
  }, [selectedTaskId]);

  // フィルタリング（クライアントサイド）
  const filteredTasks = useMemo(() => {
    let result = tasks;

    // 検索
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      result = result.filter(
        (task) =>
          task.title.toLowerCase().includes(searchLower) ||
          task.description?.toLowerCase().includes(searchLower)
      );
    }

    // 担当者フィルター
    if (filters.assigned_to_id && filters.assigned_to_id !== "all") {
      if (filters.assigned_to_id === "unassigned") {
        result = result.filter((task) => !task.assigned_to_id);
      } else {
        result = result.filter(
          (task) => task.assigned_to_id === filters.assigned_to_id
        );
      }
    }

    return result;
  }, [tasks, filters.search, filters.assigned_to_id]);

  // タスク選択
  const handleSelectTask = (taskId: string) => {
    setSelectedTaskId(taskId);
  };

  // 詳細パネルを閉じる
  const handleCloseDetail = () => {
    setSelectedTaskId(undefined);
    setSelectedTask(null);
  };

  // タスク更新後のリロード
  const handleTaskUpdated = () => {
    loadTasks();
    handleCloseDetail();
  };

  // ステータス変更（カンバン用）
  const handleStatusChange = async (taskId: string, newStatus: string) => {
    try {
      await updateTask(taskId, { status: newStatus });
      // 楽観的更新
      setTasks((prev) =>
        prev.map((task) =>
          task.id === taskId ? { ...task, status: newStatus } : task
        )
      );
      // 選択中のタスクも更新
      if (selectedTask?.id === taskId) {
        setSelectedTask({ ...selectedTask, status: newStatus });
      }
    } catch (error) {
      console.error("Failed to update task status:", error);
      // エラー時は再読込
      loadTasks();
    }
  };

  // 新規タスク作成後
  const handleTaskCreated = (newTask: Task) => {
    setTasks((prev) => [newTask, ...prev]);
    setSelectedTaskId(newTask.id);
    setSelectedTask(newTask);
  };

  // フィルタークリア
  const handleClearFilters = () => {
    setFilters(defaultFilterValues);
  };

  // 統計情報
  const stats = useMemo(() => ({
    total: tasks.length,
    new: tasks.filter((t) => t.status === "new" || t.status === "pending").length,
    inProgress: tasks.filter((t) => t.status === "in_progress").length,
    waiting: tasks.filter((t) => t.status === "waiting").length,
    completed: tasks.filter((t) => t.status === "completed").length,
  }), [tasks]);

  return (
    <ThreePaneLayout
      isRightPanelOpen={!!selectedTaskId}
      onCloseRightPanel={handleCloseDetail}
      rightPanel={
        selectedTask ? (
          <div className="flex flex-col h-full">
            <div className="flex-1 overflow-auto p-4">
              <TaskDetail task={selectedTask} onTaskUpdated={handleTaskUpdated} />
            </div>
            <Separator />
            <div className="h-[300px]">
              <TaskComments taskId={selectedTask.id} />
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <Loader2 className="h-6 w-6 animate-spin mr-2" />
            読み込み中...
          </div>
        )
      }
    >
      <div className="p-6 h-full flex flex-col">
        {/* ヘッダー */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">タスク管理</h1>
            <p className="text-sm text-gray-500 mt-1">
              {stats.new > 0 && (
                <span className="text-blue-600 font-medium">{stats.new}件の新規タスク</span>
              )}
              {stats.new > 0 && stats.inProgress > 0 && " / "}
              {stats.inProgress > 0 && (
                <span className="text-yellow-600 font-medium">{stats.inProgress}件対応中</span>
              )}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* ビューモード切替 */}
            <div className="flex rounded-lg border p-1 bg-white">
              <Button
                variant={viewMode === "kanban" ? "secondary" : "ghost"}
                size="sm"
                className="h-8 px-3"
                onClick={() => setViewMode("kanban")}
              >
                <LayoutGrid className="h-4 w-4 mr-1.5" />
                カンバン
              </Button>
              <Button
                variant={viewMode === "list" ? "secondary" : "ghost"}
                size="sm"
                className="h-8 px-3"
                onClick={() => setViewMode("list")}
              >
                <List className="h-4 w-4 mr-1.5" />
                リスト
              </Button>
              <Button
                variant={viewMode === "gantt" ? "secondary" : "ghost"}
                size="sm"
                className="h-8 px-3"
                onClick={() => setViewMode("gantt")}
              >
                <BarChart3 className="h-4 w-4 mr-1.5" />
                ガント
              </Button>
            </div>

            {/* 新規タスク作成ボタン */}
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-1.5" />
              新規タスク
            </Button>
          </div>
        </div>

        {/* フィルター */}
        <div className="mb-4">
          <TaskFilters
            filters={filters}
            onFilterChange={setFilters}
            onClearFilters={handleClearFilters}
          />
        </div>

        {/* メインコンテンツ */}
        <div className="flex-1 min-h-0">
          {loading ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              <Loader2 className="h-8 w-8 animate-spin mr-2" />
              読み込み中...
            </div>
          ) : viewMode === "kanban" ? (
            <KanbanBoard
              tasks={filteredTasks}
              selectedTaskId={selectedTaskId}
              onSelectTask={handleSelectTask}
              onStatusChange={handleStatusChange}
            />
          ) : viewMode === "gantt" ? (
            <GanttChart
              tasks={filteredTasks}
              selectedTaskId={selectedTaskId}
              onSelectTask={handleSelectTask}
            />
          ) : (
            <div className="bg-white rounded-lg border h-full overflow-auto">
              <Tabs defaultValue="all" className="h-full flex flex-col">
                <div className="px-4 pt-4 border-b">
                  <TabsList>
                    <TabsTrigger value="all">
                      すべて ({filteredTasks.length})
                    </TabsTrigger>
                    <TabsTrigger value="new">
                      新規 ({filteredTasks.filter((t) => t.status === "new" || t.status === "pending").length})
                    </TabsTrigger>
                    <TabsTrigger value="in_progress">
                      対応中 ({filteredTasks.filter((t) => t.status === "in_progress").length})
                    </TabsTrigger>
                    <TabsTrigger value="waiting">
                      保留 ({filteredTasks.filter((t) => t.status === "waiting").length})
                    </TabsTrigger>
                    <TabsTrigger value="completed">
                      完了 ({filteredTasks.filter((t) => t.status === "completed").length})
                    </TabsTrigger>
                  </TabsList>
                </div>

                <div className="flex-1 overflow-auto p-4">
                  <TabsContent value="all" className="mt-0">
                    <TaskList
                      tasks={filteredTasks}
                      selectedTaskId={selectedTaskId}
                      onSelectTask={handleSelectTask}
                    />
                  </TabsContent>

                  <TabsContent value="new" className="mt-0">
                    <TaskList
                      tasks={filteredTasks.filter(
                        (t) => t.status === "new" || t.status === "pending"
                      )}
                      selectedTaskId={selectedTaskId}
                      onSelectTask={handleSelectTask}
                    />
                  </TabsContent>

                  <TabsContent value="in_progress" className="mt-0">
                    <TaskList
                      tasks={filteredTasks.filter((t) => t.status === "in_progress")}
                      selectedTaskId={selectedTaskId}
                      onSelectTask={handleSelectTask}
                    />
                  </TabsContent>

                  <TabsContent value="waiting" className="mt-0">
                    <TaskList
                      tasks={filteredTasks.filter((t) => t.status === "waiting")}
                      selectedTaskId={selectedTaskId}
                      onSelectTask={handleSelectTask}
                    />
                  </TabsContent>

                  <TabsContent value="completed" className="mt-0">
                    <TaskList
                      tasks={filteredTasks.filter((t) => t.status === "completed")}
                      selectedTaskId={selectedTaskId}
                      onSelectTask={handleSelectTask}
                    />
                  </TabsContent>
                </div>
              </Tabs>
            </div>
          )}
        </div>
      </div>

      {/* 新規タスク作成ダイアログ */}
      <TaskCreateDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        onTaskCreated={handleTaskCreated}
      />
    </ThreePaneLayout>
  );
}
