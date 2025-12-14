"use client";

import { useEffect, useState } from "react";
import { ThreePaneLayout } from "@/components/layout/ThreePaneLayout";
import { TaskList } from "@/components/tasks/TaskList";
import { TaskDetail } from "@/components/tasks/TaskDetail";
import { getTasks, getTaskDetail, Task } from "@/lib/api/staff";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string>();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTasks();
  }, []);

  useEffect(() => {
    if (selectedTaskId) {
      loadTaskDetail(selectedTaskId);
    }
  }, [selectedTaskId]);

  async function loadTasks() {
    setLoading(true);
    const data = await getTasks();
    setTasks(data);
    setLoading(false);
  }

  async function loadTaskDetail(taskId: string) {
    const task = await getTaskDetail(taskId);
    setSelectedTask(task);
  }

  function handleSelectTask(taskId: string) {
    setSelectedTaskId(taskId);
  }

  function handleCloseDetail() {
    setSelectedTaskId(undefined);
    setSelectedTask(null);
  }

  const todayTasks = tasks.filter((task) => {
    if (!task.due_date) return false;
    const taskDate = new Date(task.due_date);
    const today = new Date();
    return (
      taskDate.getDate() === today.getDate() &&
      taskDate.getMonth() === today.getMonth() &&
      taskDate.getFullYear() === today.getFullYear()
    );
  });

  const pendingTasks = tasks.filter((task) => task.status === "pending");
  const inProgressTasks = tasks.filter((task) => task.status === "in_progress");
  const completedTasks = tasks.filter((task) => task.status === "completed");

  return (
    <ThreePaneLayout
      isRightPanelOpen={!!selectedTaskId}
      onCloseRightPanel={handleCloseDetail}
      rightPanel={
        selectedTask ? (
          <TaskDetail task={selectedTask} />
        ) : (
          <div className="text-center text-gray-500">読み込み中...</div>
        )
      }
    >
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">タスク管理</h1>
          <p className="text-gray-600">
            {pendingTasks.length}件の未着手タスクがあります
          </p>
        </div>

        {loading ? (
          <div className="text-center text-gray-500 py-8">読み込み中...</div>
        ) : (
          <Tabs defaultValue="today" className="w-full">
            <TabsList className="mb-4">
              <TabsTrigger value="today">
                今日のタスク ({todayTasks.length})
              </TabsTrigger>
              <TabsTrigger value="pending">
                未着手 ({pendingTasks.length})
              </TabsTrigger>
              <TabsTrigger value="in_progress">
                進行中 ({inProgressTasks.length})
              </TabsTrigger>
              <TabsTrigger value="completed">
                完了 ({completedTasks.length})
              </TabsTrigger>
              <TabsTrigger value="all">すべて ({tasks.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="today">
              {todayTasks.length > 0 ? (
                <TaskList
                  tasks={todayTasks}
                  selectedTaskId={selectedTaskId}
                  onSelectTask={handleSelectTask}
                />
              ) : (
                <div className="text-center text-gray-500 py-8">
                  今日のタスクはありません
                </div>
              )}
            </TabsContent>

            <TabsContent value="pending">
              {pendingTasks.length > 0 ? (
                <TaskList
                  tasks={pendingTasks}
                  selectedTaskId={selectedTaskId}
                  onSelectTask={handleSelectTask}
                />
              ) : (
                <div className="text-center text-gray-500 py-8">
                  未着手のタスクはありません
                </div>
              )}
            </TabsContent>

            <TabsContent value="in_progress">
              {inProgressTasks.length > 0 ? (
                <TaskList
                  tasks={inProgressTasks}
                  selectedTaskId={selectedTaskId}
                  onSelectTask={handleSelectTask}
                />
              ) : (
                <div className="text-center text-gray-500 py-8">
                  進行中のタスクはありません
                </div>
              )}
            </TabsContent>

            <TabsContent value="completed">
              {completedTasks.length > 0 ? (
                <TaskList
                  tasks={completedTasks}
                  selectedTaskId={selectedTaskId}
                  onSelectTask={handleSelectTask}
                />
              ) : (
                <div className="text-center text-gray-500 py-8">
                  完了したタスクはありません
                </div>
              )}
            </TabsContent>

            <TabsContent value="all">
              <TaskList
                tasks={tasks}
                selectedTaskId={selectedTaskId}
                onSelectTask={handleSelectTask}
              />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </ThreePaneLayout>
  );
}
