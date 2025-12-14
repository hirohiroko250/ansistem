"""
Google Calendar API Service
Googleカレンダーとの連携サービス
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Google Calendar API連携サービス"""

    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    CACHE_KEY_PREFIX = 'google_calendar_events'
    CACHE_TIMEOUT = 300  # 5 minutes

    def __init__(self, credentials_dict: Optional[Dict] = None):
        """
        初期化

        Args:
            credentials_dict: OAuth2認証情報の辞書（サービスアカウントまたはOAuth2トークン）
        """
        self.credentials_dict = credentials_dict or self._load_credentials()
        self._service = None

    def _load_credentials(self) -> Optional[Dict]:
        """設定ファイルまたは環境変数から認証情報を読み込む"""
        # 環境変数から読み込む
        creds_json = os.environ.get('GOOGLE_CALENDAR_CREDENTIALS')
        if creds_json:
            try:
                return json.loads(creds_json)
            except json.JSONDecodeError:
                logger.error("Invalid GOOGLE_CALENDAR_CREDENTIALS JSON")
                return None

        # ファイルから読み込む
        creds_path = getattr(settings, 'GOOGLE_CALENDAR_CREDENTIALS_PATH', None)
        if creds_path and os.path.exists(creds_path):
            try:
                with open(creds_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load credentials from {creds_path}: {e}")
                return None

        return None

    def _get_service(self):
        """Google Calendar APIサービスを取得"""
        if self._service is not None:
            return self._service

        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build

            if not self.credentials_dict:
                logger.warning("No Google Calendar credentials configured")
                return None

            credentials = Credentials.from_service_account_info(
                self.credentials_dict,
                scopes=self.SCOPES
            )
            self._service = build('calendar', 'v3', credentials=credentials)
            return self._service

        except ImportError:
            logger.error(
                "Google API client libraries not installed. "
                "Run: pip install google-api-python-client google-auth google-auth-oauthlib"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar service: {e}")
            return None

    def get_events(
        self,
        calendar_id: str,
        start_date: datetime,
        end_date: datetime,
        max_results: int = 250
    ) -> List[Dict[str, Any]]:
        """
        指定期間のイベントを取得

        Args:
            calendar_id: GoogleカレンダーID（メールアドレス形式）
            start_date: 開始日時
            end_date: 終了日時
            max_results: 最大取得件数

        Returns:
            イベントリスト
        """
        # キャッシュキー生成
        cache_key = f"{self.CACHE_KEY_PREFIX}:{calendar_id}:{start_date.date()}:{end_date.date()}"
        cached_events = cache.get(cache_key)
        if cached_events is not None:
            return cached_events

        service = self._get_service()
        if not service:
            return []

        try:
            # RFC3339形式に変換
            time_min = start_date.isoformat() + 'Z' if start_date.tzinfo is None else start_date.isoformat()
            time_max = end_date.isoformat() + 'Z' if end_date.tzinfo is None else end_date.isoformat()

            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            formatted_events = [self._format_event(event) for event in events]

            # キャッシュに保存
            cache.set(cache_key, formatted_events, self.CACHE_TIMEOUT)

            return formatted_events

        except Exception as e:
            logger.error(f"Failed to fetch Google Calendar events: {e}")
            return []

    def get_events_for_month(
        self,
        calendar_id: str,
        year: int,
        month: int
    ) -> List[Dict[str, Any]]:
        """
        指定月のイベントを取得

        Args:
            calendar_id: GoogleカレンダーID
            year: 年
            month: 月

        Returns:
            イベントリスト
        """
        start_date = datetime(year, month, 1, 0, 0, 0)

        # 翌月の初日を計算
        if month == 12:
            end_date = datetime(year + 1, 1, 1, 0, 0, 0)
        else:
            end_date = datetime(year, month + 1, 1, 0, 0, 0)

        return self.get_events(calendar_id, start_date, end_date)

    def get_events_for_week(
        self,
        calendar_id: str,
        week_start: datetime
    ) -> List[Dict[str, Any]]:
        """
        指定週のイベントを取得

        Args:
            calendar_id: GoogleカレンダーID
            week_start: 週の開始日

        Returns:
            イベントリスト
        """
        start_date = datetime(week_start.year, week_start.month, week_start.day, 0, 0, 0)
        end_date = start_date + timedelta(days=7)
        return self.get_events(calendar_id, start_date, end_date)

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Google Calendar APIのイベントを共通フォーマットに変換

        Args:
            event: Google Calendar APIからのイベント

        Returns:
            フォーマット済みイベント
        """
        start = event.get('start', {})
        end = event.get('end', {})

        # 終日イベントかどうかを判定
        is_all_day = 'date' in start

        if is_all_day:
            start_time = start.get('date')
            end_time = end.get('date')
        else:
            start_time = start.get('dateTime')
            end_time = end.get('dateTime')

        return {
            'id': event.get('id'),
            'title': event.get('summary', '(タイトルなし)'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'startTime': start_time,
            'endTime': end_time,
            'isAllDay': is_all_day,
            'status': event.get('status', 'confirmed'),
            'htmlLink': event.get('htmlLink', ''),
            'creator': event.get('creator', {}).get('email', ''),
            'colorId': event.get('colorId'),
            'source': 'google_calendar'
        }

    def list_calendars(self) -> List[Dict[str, Any]]:
        """
        アクセス可能なカレンダー一覧を取得

        Returns:
            カレンダーリスト
        """
        service = self._get_service()
        if not service:
            return []

        try:
            calendar_list = service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])

            return [
                {
                    'id': cal.get('id'),
                    'summary': cal.get('summary'),
                    'description': cal.get('description', ''),
                    'primary': cal.get('primary', False),
                    'backgroundColor': cal.get('backgroundColor'),
                    'foregroundColor': cal.get('foregroundColor'),
                    'accessRole': cal.get('accessRole'),
                }
                for cal in calendars
            ]

        except Exception as e:
            logger.error(f"Failed to list calendars: {e}")
            return []


# シングルトンインスタンス（必要に応じて使用）
def get_google_calendar_service() -> GoogleCalendarService:
    """GoogleCalendarServiceのインスタンスを取得"""
    return GoogleCalendarService()
