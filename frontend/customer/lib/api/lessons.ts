/**
 * Lessons API
 * 授業スケジュール・出欠・振替関連のAPI関数（保護者・顧客向け）
 */

import api from './client';
import type {
  LessonSchedule,
  LessonRecord,
  Attendance,
  MakeupRequest,
  MakeupResponse,
  CalendarEvent,
  ScheduleParams,
  AttendanceParams,
  MakeupAvailableDate,
  MarkAbsentRequest,
  TimeSlot,
  PaginatedResponse,
} from './types';

// ============================================
// スケジュール関連
// ============================================

/**
 * 授業スケジュール一覧を取得
 * カレンダー表示やスケジュール管理で使用
 *
 * @param params - 検索パラメータ（生徒ID、日付範囲など）
 * @returns スケジュール一覧
 */
export async function getSchedules(params?: ScheduleParams): Promise<PaginatedResponse<LessonSchedule>> {
  const query = new URLSearchParams();

  if (params?.studentId) query.set('student', params.studentId);
  if (params?.schoolId) query.set('school', params.schoolId);
  if (params?.teacherId) query.set('teacher', params.teacherId);
  if (params?.dateFrom) query.set('date_from', params.dateFrom);
  if (params?.dateTo) query.set('date_to', params.dateTo);
  if (params?.status) query.set('status', params.status);
  if (params?.lessonType) query.set('lesson_type', params.lessonType);
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));

  const queryString = query.toString();
  const endpoint = queryString ? `/lessons/schedules/?${queryString}` : '/lessons/schedules/';

  return api.get<PaginatedResponse<LessonSchedule>>(endpoint);
}

/**
 * 授業スケジュール詳細を取得
 *
 * @param scheduleId - スケジュールID
 * @returns スケジュール詳細
 */
export async function getScheduleDetail(scheduleId: string): Promise<LessonSchedule> {
  return api.get<LessonSchedule>(`/lessons/schedules/${scheduleId}/`);
}

/**
 * カレンダー表示用のイベントデータを取得
 * 指定期間の授業をカレンダー形式で取得
 *
 * @param studentId - 生徒ID
 * @param dateFrom - 開始日（YYYY-MM-DD）
 * @param dateTo - 終了日（YYYY-MM-DD）
 * @returns カレンダーイベント一覧
 */
export async function getCalendarEvents(
  studentId: string,
  dateFrom: string,
  dateTo: string
): Promise<CalendarEvent[]> {
  const query = new URLSearchParams({
    student: studentId,
    date_from: dateFrom,
    date_to: dateTo,
    format: 'calendar',
  });

  return api.get<CalendarEvent[]>(`/lessons/schedules/?${query.toString()}`);
}

// ============================================
// 授業記録関連
// ============================================

/**
 * 授業記録一覧を取得
 * 過去の授業内容や講師コメントを確認
 *
 * @param studentId - 生徒ID
 * @param page - ページ番号
 * @param pageSize - 1ページあたりの件数
 * @returns 授業記録一覧
 */
export async function getLessonRecords(
  studentId: string,
  page?: number,
  pageSize?: number
): Promise<PaginatedResponse<LessonRecord>> {
  const query = new URLSearchParams({ student: studentId });
  if (page) query.set('page', String(page));
  if (pageSize) query.set('page_size', String(pageSize));

  return api.get<PaginatedResponse<LessonRecord>>(`/lessons/records/?${query.toString()}`);
}

/**
 * 授業記録詳細を取得
 *
 * @param recordId - 記録ID
 * @returns 授業記録詳細
 */
export async function getLessonRecordDetail(recordId: string): Promise<LessonRecord> {
  return api.get<LessonRecord>(`/lessons/records/${recordId}/`);
}

// ============================================
// 出欠関連
// ============================================

/**
 * 出欠情報一覧を取得
 *
 * @param params - 検索パラメータ
 * @returns 出欠一覧
 */
export async function getAttendances(params?: AttendanceParams): Promise<PaginatedResponse<Attendance>> {
  const query = new URLSearchParams();

  if (params?.studentId) query.set('student', params.studentId);
  if (params?.scheduleId) query.set('schedule', params.scheduleId);
  if (params?.status) query.set('status', params.status);
  if (params?.dateFrom) query.set('date_from', params.dateFrom);
  if (params?.dateTo) query.set('date_to', params.dateTo);
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));

  const queryString = query.toString();
  const endpoint = queryString ? `/lessons/attendances/?${queryString}` : '/lessons/attendances/';

  return api.get<PaginatedResponse<Attendance>>(endpoint);
}

/**
 * 生徒の出欠一覧を取得（簡易版）
 *
 * @param studentId - 生徒ID
 * @returns 出欠一覧
 */
export async function getStudentAttendances(studentId: string): Promise<PaginatedResponse<Attendance>> {
  return getAttendances({ studentId });
}

/**
 * 出欠詳細を取得
 *
 * @param attendanceId - 出欠ID
 * @returns 出欠詳細
 */
export async function getAttendanceDetail(attendanceId: string): Promise<Attendance> {
  return api.get<Attendance>(`/lessons/attendances/${attendanceId}/`);
}

/**
 * 欠席登録
 * 授業を欠席として登録し、オプションで振替申請も行う
 *
 * @param attendanceId - 出欠ID
 * @param data - 欠席登録データ
 * @returns 更新された出欠情報
 */
export async function markAbsent(
  attendanceId: string,
  data?: MarkAbsentRequest
): Promise<Attendance> {
  return api.patch<Attendance>(`/lessons/attendances/${attendanceId}/`, {
    status: 'absent_notice',
    absence_reason: data?.absenceReason,
    request_makeup: data?.requestMakeup,
  });
}

/**
 * 出欠ステータスを更新
 *
 * @param attendanceId - 出欠ID
 * @param status - 新しいステータス
 * @param reason - 理由（欠席の場合）
 * @returns 更新された出欠情報
 */
export async function updateAttendanceStatus(
  attendanceId: string,
  status: Attendance['status'],
  reason?: string
): Promise<Attendance> {
  return api.patch<Attendance>(`/lessons/attendances/${attendanceId}/`, {
    status,
    absence_reason: reason,
  });
}

// ============================================
// 振替関連
// ============================================

/**
 * 振替申請一覧を取得
 *
 * @param studentId - 生徒ID（オプション）
 * @param page - ページ番号
 * @param pageSize - 1ページあたりの件数
 * @returns 振替一覧
 */
export async function getMakeups(
  studentId?: string,
  page?: number,
  pageSize?: number
): Promise<PaginatedResponse<MakeupResponse>> {
  const query = new URLSearchParams();
  if (studentId) query.set('student', studentId);
  if (page) query.set('page', String(page));
  if (pageSize) query.set('page_size', String(pageSize));

  const queryString = query.toString();
  const endpoint = queryString ? `/lessons/makeups/?${queryString}` : '/lessons/makeups/';

  return api.get<PaginatedResponse<MakeupResponse>>(endpoint);
}

/**
 * 振替詳細を取得
 *
 * @param makeupId - 振替ID
 * @returns 振替詳細
 */
export async function getMakeupDetail(makeupId: string): Promise<MakeupResponse> {
  return api.get<MakeupResponse>(`/lessons/makeups/${makeupId}/`);
}

/**
 * 振替申請を作成
 *
 * @param data - 振替申請データ
 * @returns 作成された振替申請
 */
export async function requestMakeup(data: MakeupRequest): Promise<MakeupResponse> {
  return api.post<MakeupResponse>('/lessons/makeups/', {
    original_schedule: data.originalScheduleId,
    student: data.studentId,
    preferred_date: data.preferredDate,
    preferred_time_slot: data.preferredTimeSlotId,
    reason: data.reason,
  });
}

/**
 * 振替申請をキャンセル
 *
 * @param makeupId - 振替ID
 * @returns 更新された振替情報
 */
export async function cancelMakeup(makeupId: string): Promise<MakeupResponse> {
  return api.patch<MakeupResponse>(`/lessons/makeups/${makeupId}/`, {
    status: 'cancelled',
  });
}

/**
 * 振替可能日を取得
 * 指定したコース・校舎で振替可能な日時一覧を返す
 *
 * @param courseId - コースID（または元のスケジュールに関連するコース）
 * @param schoolId - 校舎ID（オプション）
 * @param dateFrom - 検索開始日（YYYY-MM-DD）
 * @param dateTo - 検索終了日（YYYY-MM-DD）
 * @returns 振替可能日一覧
 */
export async function getMakeupAvailableDates(
  courseId: string,
  schoolId?: string,
  dateFrom?: string,
  dateTo?: string
): Promise<MakeupAvailableDate[]> {
  const query = new URLSearchParams({ course: courseId });
  if (schoolId) query.set('school', schoolId);
  if (dateFrom) query.set('date_from', dateFrom);
  if (dateTo) query.set('date_to', dateTo);

  return api.get<MakeupAvailableDate[]>(`/lessons/makeups/available-dates/?${query.toString()}`);
}

// ============================================
// 時間割関連
// ============================================

/**
 * 時間割一覧を取得
 *
 * @param schoolId - 校舎ID（オプション）
 * @returns 時間割一覧
 */
export async function getTimeSlots(schoolId?: string): Promise<TimeSlot[]> {
  const query = schoolId ? `?school=${schoolId}` : '';
  const response = await api.get<PaginatedResponse<TimeSlot>>(`/lessons/time-slots/${query}`);
  return response.results;
}

/**
 * 時間割詳細を取得
 *
 * @param timeSlotId - 時間割ID
 * @returns 時間割詳細
 */
export async function getTimeSlotDetail(timeSlotId: string): Promise<TimeSlot> {
  return api.get<TimeSlot>(`/lessons/time-slots/${timeSlotId}/`);
}

// ============================================
// 講師向けスケジュール関連
// ============================================

/**
 * 講師用スケジュール検索パラメータ
 */
export interface StaffScheduleSearchParams {
  page?: number;
  pageSize?: number;
  startDate?: string;
  endDate?: string;
  instructorId?: string;
  schoolId?: string;
  courseId?: string;
  status?: string;
}

/**
 * 講師用授業スケジュール型（syain互換）
 */
export interface StaffLessonSchedule {
  id: string;
  courseId: string;
  course: {
    id: string;
    name: string;
    shortName?: string;
    category: string;
    ticketCost: number;
    durationMinutes?: number;
  };
  instructorId?: string;
  instructor?: {
    id: string;
    fullName: string;
    profileImageUrl?: string;
  };
  schoolId: string;
  school: {
    id: string;
    name: string;
    shortName?: string;
  };
  scheduledDate: string;
  startTime: string;
  endTime: string;
  capacity?: number;
  currentEnrollment: number;
  status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
  notes?: string;
  createdAt: string;
}

/**
 * 講師用カレンダーイベント型
 */
export interface StaffCalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  status: string;
  courseName: string;
  instructorName?: string;
  schoolName: string;
  currentEnrollment: number;
  capacity?: number;
  color?: string;
}

/**
 * 講師用授業スケジュール一覧取得
 */
export async function getStaffLessonSchedules(
  params?: StaffScheduleSearchParams
): Promise<PaginatedResponse<StaffLessonSchedule>> {
  const queryParams = new URLSearchParams();

  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.pageSize) queryParams.append('page_size', params.pageSize.toString());
  if (params?.startDate) queryParams.append('start_date', params.startDate);
  if (params?.endDate) queryParams.append('end_date', params.endDate);
  if (params?.instructorId) queryParams.append('instructor_id', params.instructorId);
  if (params?.schoolId) queryParams.append('school_id', params.schoolId);
  if (params?.courseId) queryParams.append('course_id', params.courseId);
  if (params?.status) queryParams.append('status', params.status);

  const query = queryParams.toString();
  const endpoint = `/lessons/schedules/${query ? `?${query}` : ''}`;

  return api.get<PaginatedResponse<StaffLessonSchedule>>(endpoint);
}

/**
 * 講師用授業スケジュール詳細取得
 */
export async function getStaffLessonScheduleDetail(id: string): Promise<StaffLessonSchedule> {
  return api.get<StaffLessonSchedule>(`/lessons/schedules/${id}/`);
}

/**
 * 講師用カレンダー形式でスケジュール取得
 */
export async function getStaffCalendarSchedules(
  params: { year: number; month: number; instructorId?: string; schoolId?: string; courseId?: string }
): Promise<StaffCalendarEvent[]> {
  const queryParams = new URLSearchParams();

  queryParams.append('year', params.year.toString());
  queryParams.append('month', params.month.toString());
  if (params.instructorId) queryParams.append('instructor_id', params.instructorId);
  if (params.schoolId) queryParams.append('school_id', params.schoolId);
  if (params.courseId) queryParams.append('course_id', params.courseId);

  const query = queryParams.toString();
  return api.get<StaffCalendarEvent[]>(`/lessons/schedules/calendar/?${query}`);
}

/**
 * 今日の授業一覧取得（講師用）
 */
export async function getTodayLessons(): Promise<StaffLessonSchedule[]> {
  const today = new Date().toISOString().split('T')[0];
  const response = await getStaffLessonSchedules({
    startDate: today,
    endDate: today,
    pageSize: 100,
  });
  return response.results;
}

/**
 * 今週の授業一覧取得（講師用）
 */
export async function getWeekLessons(): Promise<StaffLessonSchedule[]> {
  const today = new Date();
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay());
  const endOfWeek = new Date(startOfWeek);
  endOfWeek.setDate(startOfWeek.getDate() + 6);

  const response = await getStaffLessonSchedules({
    startDate: startOfWeek.toISOString().split('T')[0],
    endDate: endOfWeek.toISOString().split('T')[0],
    pageSize: 100,
  });
  return response.results;
}

// ============================================
// クラス詳細・出欠管理（講師向け）
// ============================================

/**
 * クラス詳細情報型
 */
export interface ClassDetail {
  id: string;
  className: string;
  classroom: string;
  startTime: string;
  endTime: string;
  campus: {
    id: string;
    name: string;
  };
  course?: {
    id: string;
    name: string;
  };
  instructor?: {
    id: string;
    fullName: string;
  };
}

/**
 * クラス受講生徒型
 */
export interface ClassStudent {
  id: string;
  name: string;
  grade?: string;
  isSubstitute: boolean;
  attendanceStatus?: 'present' | 'absent' | 'late' | 'excused';
}

/**
 * クラス詳細取得
 */
export async function getClassDetail(classId: string): Promise<ClassDetail> {
  return api.get<ClassDetail>(`/lessons/classes/${classId}/`);
}

/**
 * クラスの生徒一覧取得
 */
export async function getClassStudents(classId: string): Promise<ClassStudent[]> {
  return api.get<ClassStudent[]>(`/lessons/classes/${classId}/students/`);
}

/**
 * 出欠更新リクエスト型
 */
export interface UpdateClassAttendanceRequest {
  studentId: string;
  status: 'present' | 'absent' | 'late' | 'excused';
}

/**
 * クラスの出欠を更新
 */
export async function updateClassAttendance(
  classId: string,
  data: UpdateClassAttendanceRequest
): Promise<{ success: boolean; message: string }> {
  return api.post<{ success: boolean; message: string }>(
    `/lessons/classes/${classId}/attendance/`,
    {
      student_id: data.studentId,
      status: data.status,
    }
  );
}

/**
 * 日報型
 */
export interface DailyReport {
  id?: string;
  classId: string;
  instructorId: string;
  reportContent: string;
  createdAt?: string;
  updatedAt?: string;
}

/**
 * 日報取得
 */
export async function getClassDailyReport(classId: string): Promise<DailyReport | null> {
  try {
    return await api.get<DailyReport>(`/lessons/classes/${classId}/report/`);
  } catch (err: unknown) {
    const error = err as { status?: number };
    if (error.status === 404) {
      return null;
    }
    throw err;
  }
}

/**
 * 日報送信
 */
export async function submitClassDailyReport(
  classId: string,
  reportContent: string
): Promise<DailyReport> {
  return api.post<DailyReport>(`/lessons/classes/${classId}/report/`, {
    report_content: reportContent,
  });
}
