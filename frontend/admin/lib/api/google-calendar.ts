/**
 * Google Calendar API Client
 */

import apiClient from "./client";

export interface GoogleCalendarEvent {
  id: string;
  title: string;
  description: string;
  location: string;
  startTime: string;
  endTime: string;
  isAllDay: boolean;
  status: string;
  htmlLink: string;
  creator: string;
  colorId: string | null;
  source: "google_calendar";
}

export interface GoogleCalendar {
  id: string;
  summary: string;
  description: string;
  primary: boolean;
  backgroundColor: string;
  foregroundColor: string;
  accessRole: string;
}

export interface GoogleCalendarEventsResponse {
  calendarId: string;
  view: "month" | "week";
  events: GoogleCalendarEvent[];
}

export interface GoogleCalendarListResponse {
  calendars: GoogleCalendar[];
}

/**
 * 月間のGoogle Calendarイベントを取得
 */
export async function getGoogleCalendarEventsForMonth(
  calendarId: string,
  year: number,
  month: number
): Promise<GoogleCalendarEvent[]> {
  try {
    const response = await apiClient.get<GoogleCalendarEventsResponse>(
      "/schools/admin/google-calendar/events/",
      {
        calendar_id: calendarId,
        view: "month",
        year: String(year),
        month: String(month),
      }
    );
    return response.events || [];
  } catch (error) {
    console.error("Error fetching Google Calendar events:", error);
    return [];
  }
}

/**
 * 週間のGoogle Calendarイベントを取得
 */
export async function getGoogleCalendarEventsForWeek(
  calendarId: string,
  weekStart: Date
): Promise<GoogleCalendarEvent[]> {
  try {
    const weekStartStr = weekStart.toISOString().split("T")[0]; // YYYY-MM-DD
    const response = await apiClient.get<GoogleCalendarEventsResponse>(
      "/schools/admin/google-calendar/events/",
      {
        calendar_id: calendarId,
        view: "week",
        week_start: weekStartStr,
      }
    );
    return response.events || [];
  } catch (error) {
    console.error("Error fetching Google Calendar events:", error);
    return [];
  }
}

/**
 * アクセス可能なカレンダー一覧を取得
 */
export async function getGoogleCalendars(): Promise<GoogleCalendar[]> {
  try {
    const response = await apiClient.get<GoogleCalendarListResponse>(
      "/schools/admin/google-calendar/calendars/"
    );
    return response.calendars || [];
  } catch (error) {
    console.error("Error fetching Google Calendars:", error);
    return [];
  }
}

/**
 * イベントの日付をDateオブジェクトに変換
 */
export function parseEventDateTime(dateTimeStr: string): Date {
  return new Date(dateTimeStr);
}

/**
 * イベントの時間を「HH:MM」形式で取得
 */
export function formatEventTime(dateTimeStr: string): string {
  const date = new Date(dateTimeStr);
  return date.toLocaleTimeString("ja-JP", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/**
 * イベントの日付を「MM/DD」形式で取得
 */
export function formatEventDate(dateTimeStr: string): string {
  const date = new Date(dateTimeStr);
  return `${date.getMonth() + 1}/${date.getDate()}`;
}
