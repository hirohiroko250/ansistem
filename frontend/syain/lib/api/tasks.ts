/**
 * Task API Client
 */
import api from './client';

export interface Task {
  id: string;
  taskType: string;
  taskTypeDisplay: string;
  category: string | null;
  categoryName: string | null;
  title: string;
  description: string;
  status: string;
  statusDisplay: string;
  priority: string;
  priorityDisplay: string;
  school: string | null;
  schoolName: string | null;
  brand: string | null;
  brandName: string | null;
  student: string | null;
  studentName: string | null;
  guardian: string | null;
  guardianName: string | null;
  assignedToId: string | null;
  assignedToName: string | null;
  createdById: string | null;
  createdByName: string | null;
  dueDate: string | null;
  completedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface TaskComment {
  id: string;
  task: string;
  comment: string;
  commentedById: string | null;
  commentedByName?: string;
  isInternal: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface TaskCategory {
  id: string;
  categoryCode: string;
  categoryName: string;
  icon: string;
  color: string;
  sortOrder: number;
  isActive: boolean;
}

export interface Staff {
  id: string;
  fullName: string;
  email: string;
  position?: string;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// タスク一覧取得
export async function getTasks(params?: {
  status?: string;
  priority?: string;
  taskType?: string;
  assignedToId?: string;
}): Promise<Task[]> {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.append('status', params.status);
  if (params?.priority) queryParams.append('priority', params.priority);
  if (params?.taskType) queryParams.append('task_type', params.taskType);
  if (params?.assignedToId) queryParams.append('assigned_to_id', params.assignedToId);

  const url = `/tasks/tasks/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
  const response = await api.get<PaginatedResponse<any>>(url);
  return (response.results || []).map(transformTask);
}

// 自分に割り当てられたタスク取得
export async function getMyTasks(params?: { status?: string }): Promise<Task[]> {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.append('status', params.status);

  const url = `/tasks/tasks/my_tasks/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
  const response = await api.get<PaginatedResponse<any> | any[]>(url);
  const results = Array.isArray(response) ? response : response.results || [];
  return results.map(transformTask);
}

// 未完了タスク取得
export async function getPendingTasks(): Promise<Task[]> {
  const response = await api.get<any[]>('/tasks/tasks/pending/');
  return (response || []).map(transformTask);
}

// 今日の期限タスク取得
export async function getTodayTasks(): Promise<Task[]> {
  const response = await api.get<any[]>('/tasks/tasks/today/');
  return (response || []).map(transformTask);
}

// 期限切れタスク取得
export async function getOverdueTasks(): Promise<Task[]> {
  const response = await api.get<any[]>('/tasks/tasks/overdue/');
  return (response || []).map(transformTask);
}

// タスク詳細取得
export async function getTask(taskId: string): Promise<Task> {
  const response = await api.get<any>(`/tasks/tasks/${taskId}/`);
  return transformTask(response);
}

// タスク作成
export async function createTask(data: {
  title: string;
  description?: string;
  taskType?: string;
  priority?: string;
  assignedToId?: string;
  dueDate?: string;
  school?: string;
  student?: string;
  guardian?: string;
}): Promise<Task> {
  const payload = {
    title: data.title,
    description: data.description || '',
    task_type: data.taskType || 'other',
    priority: data.priority || 'normal',
    assigned_to_id: data.assignedToId,
    due_date: data.dueDate,
    school: data.school,
    student: data.student,
    guardian: data.guardian,
    status: 'new',
  };
  const response = await api.post<any>('/tasks/tasks/', payload);
  return transformTask(response);
}

// タスク更新
export async function updateTask(taskId: string, data: Partial<{
  title: string;
  description: string;
  status: string;
  priority: string;
  assignedToId: string;
  dueDate: string;
}>): Promise<Task> {
  const payload: Record<string, any> = {};
  if (data.title !== undefined) payload.title = data.title;
  if (data.description !== undefined) payload.description = data.description;
  if (data.status !== undefined) payload.status = data.status;
  if (data.priority !== undefined) payload.priority = data.priority;
  if (data.assignedToId !== undefined) payload.assigned_to_id = data.assignedToId;
  if (data.dueDate !== undefined) payload.due_date = data.dueDate;

  const response = await api.patch<any>(`/tasks/tasks/${taskId}/`, payload);
  return transformTask(response);
}

// タスク完了
export async function completeTask(taskId: string): Promise<Task> {
  const response = await api.post<any>(`/tasks/tasks/${taskId}/complete/`);
  return transformTask(response);
}

// タスク再開
export async function reopenTask(taskId: string): Promise<Task> {
  const response = await api.post<any>(`/tasks/tasks/${taskId}/reopen/`);
  return transformTask(response);
}

// コメント一覧取得
export async function getTaskComments(taskId: string): Promise<TaskComment[]> {
  const response = await api.get<PaginatedResponse<any>>(`/tasks/comments/?task=${taskId}`);
  return (response.results || []).map(transformComment);
}

// コメント追加
export async function addTaskComment(taskId: string, comment: string, isInternal?: boolean): Promise<TaskComment> {
  const response = await api.post<any>('/tasks/comments/', {
    task: taskId,
    comment,
    is_internal: isInternal || false,
  });
  return transformComment(response);
}

// カテゴリ一覧取得
export async function getTaskCategories(): Promise<TaskCategory[]> {
  const response = await api.get<PaginatedResponse<any>>('/tasks/categories/');
  return (response.results || []).map((c: any) => ({
    id: c.id,
    categoryCode: c.category_code,
    categoryName: c.category_name,
    icon: c.icon,
    color: c.color,
    sortOrder: c.sort_order,
    isActive: c.is_active,
  }));
}

// スタッフ一覧取得（タスク割り当て用）
export async function getStaffForAssignment(): Promise<Staff[]> {
  try {
    const response = await api.get<any>('/tenants/employees/');
    const results = response.results || response || [];
    return results.map((e: any) => ({
      id: e.id,
      fullName: e.full_name || `${e.last_name || ''}${e.first_name || ''}`.trim() || e.email,
      email: e.email,
      position: e.position,
    }));
  } catch (error) {
    console.error('Failed to get staff list:', error);
    return [];
  }
}

// データ変換
function transformTask(data: any): Task {
  return {
    id: data.id,
    taskType: data.task_type,
    taskTypeDisplay: data.task_type_display,
    category: data.category,
    categoryName: data.category_name,
    title: data.title,
    description: data.description,
    status: data.status,
    statusDisplay: data.status_display,
    priority: data.priority,
    priorityDisplay: data.priority_display,
    school: data.school,
    schoolName: data.school_name,
    brand: data.brand,
    brandName: data.brand_name,
    student: data.student,
    studentName: data.student_name,
    guardian: data.guardian,
    guardianName: data.guardian_name,
    assignedToId: data.assigned_to_id,
    assignedToName: data.assigned_to_name,
    createdById: data.created_by_id,
    createdByName: data.created_by_name,
    dueDate: data.due_date,
    completedAt: data.completed_at,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
  };
}

function transformComment(data: any): TaskComment {
  return {
    id: data.id,
    task: data.task,
    comment: data.comment,
    commentedById: data.commented_by_id,
    isInternal: data.is_internal,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
  };
}
