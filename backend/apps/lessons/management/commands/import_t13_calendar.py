"""
T13 開講カレンダーをインポートするコマンド
"""
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.lessons.models import LessonCalendar, LessonCalendarDay
from apps.schools.models import Brand


class Command(BaseCommand):
    help = 'T13 開講カレンダーExcelをインポート'

    def add_arguments(self, parser):
        parser.add_argument(
            '--xlsx',
            type=str,
            default='/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/OZA/T13_開講カレンダー202411181844.xlsx',
            help='Excelファイルパス'
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            default='3bec66b2-36ff-4206-9220-f2d7da1515ac',
            help='テナントID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存しない'
        )
        parser.add_argument(
            '--sheets',
            type=str,
            nargs='*',
            help='インポートするシート名（指定しない場合は全シート）'
        )

    def handle(self, *args, **options):
        xlsx_path = options['xlsx']
        tenant_id = options['tenant_id']
        dry_run = options['dry_run']
        target_sheets = options['sheets']

        self.stdout.write(f'Excelファイル: {xlsx_path}')
        self.stdout.write(f'テナントID: {tenant_id}')
        self.stdout.write(f'Dry Run: {dry_run}')

        # Excelを読み込む
        xlsx = pd.ExcelFile(xlsx_path)
        self.stdout.write(f'シート一覧: {xlsx.sheet_names}')

        # カレンダーシートを特定（カレンダーIDカラムを持つシート）
        calendar_sheets = []
        for sheet_name in xlsx.sheet_names:
            try:
                df = pd.read_excel(xlsx, sheet_name=sheet_name, nrows=5)
                if 'カレンダーID' in df.columns or (len(df.columns) > 0 and df.columns[0] == 'カレンダーID'):
                    calendar_sheets.append(sheet_name)
            except Exception:
                pass

        self.stdout.write(f'カレンダーシート: {calendar_sheets}')

        if target_sheets:
            calendar_sheets = [s for s in calendar_sheets if s in target_sheets]

        calendars_created = 0
        days_created = 0

        for sheet_name in calendar_sheets:
            self.stdout.write(f'\n=== {sheet_name} ===')

            df = pd.read_excel(xlsx, sheet_name=sheet_name)

            # カラム名の確認
            if 'カレンダーID' not in df.columns:
                self.stdout.write(self.style.WARNING(f'  スキップ: カレンダーIDカラムなし'))
                continue

            # カレンダーIDを取得
            calendar_code = df['カレンダーID'].iloc[0] if len(df) > 0 else None
            if not calendar_code or pd.isna(calendar_code):
                self.stdout.write(self.style.WARNING(f'  スキップ: カレンダーIDが空'))
                continue

            calendar_code = str(calendar_code).strip()
            self.stdout.write(f'  カレンダーコード: {calendar_code}')

            # ブランドを推定
            brand = self._find_brand(calendar_code, tenant_id)

            # パターンコードを抽出（末尾のA, B, Pなど）
            pattern_code = ''
            if '_' in calendar_code:
                parts = calendar_code.split('_')
                if len(parts) >= 2:
                    pattern_code = parts[-1]

            if dry_run:
                self.stdout.write(f'  [DRY] カレンダー作成: {calendar_code}')
                self.stdout.write(f'  [DRY] ブランド: {brand}')
                self.stdout.write(f'  [DRY] パターン: {pattern_code}')
                self.stdout.write(f'  [DRY] データ行数: {len(df)}')
                calendars_created += 1
                days_created += len(df)
                continue

            # カレンダーマスタを作成
            calendar, created = LessonCalendar.objects.update_or_create(
                tenant_id=tenant_id,
                calendar_code=calendar_code,
                defaults={
                    'calendar_name': f'{calendar_code} - {sheet_name}',
                    'brand': brand,
                    'pattern_code': pattern_code,
                    'year': 2024,
                    'is_active': True,
                }
            )

            if created:
                calendars_created += 1
                self.stdout.write(self.style.SUCCESS(f'  作成: {calendar_code}'))
            else:
                self.stdout.write(f'  更新: {calendar_code}')

            # 日別データを登録
            for idx, row in df.iterrows():
                date = row.get('日付')
                if pd.isna(date):
                    continue

                # 日付をパース
                if isinstance(date, str):
                    try:
                        date = pd.to_datetime(date).date()
                    except Exception:
                        continue
                elif hasattr(date, 'date'):
                    date = date.date()

                day_of_week = str(row.get('曜日', ''))
                display_label = str(row.get('保護者カレンダー表示', '')) if not pd.isna(row.get('保護者カレンダー表示')) else ''
                is_open = str(row.get('開講日', '')) == 'Y'
                transfer_reject = str(row.get('振替拒否', '')) if not pd.isna(row.get('振替拒否')) else ''
                ticket_type = str(row.get('消化・発行チケット券種', '')) if not pd.isna(row.get('消化・発行チケット券種')) else ''
                ticket_issue = row.get('権利発券数')
                ticket_type_no = row.get('チケット券種No')
                valid_days = row.get('有効期限')
                notice = str(row.get('お知らせ', '')) if not pd.isna(row.get('お知らせ')) else ''
                reject_reason = str(row.get('拒否理由', '')) if not pd.isna(row.get('拒否理由')) else ''
                holiday = str(row.get('祝日名', '')) if not pd.isna(row.get('祝日名')) else ''

                # ステータス判定
                status = 'open' if is_open else 'closed'
                if holiday:
                    status = 'holiday'
                if display_label == '講':
                    status = 'special'

                # 振替ステータス
                transfer_status = 'allowed'
                if transfer_reject == 'C':
                    transfer_status = 'conditional'

                day, day_created = LessonCalendarDay.objects.update_or_create(
                    tenant_id=tenant_id,
                    calendar=calendar,
                    date=date,
                    defaults={
                        'day_of_week': day_of_week,
                        'display_label': display_label,
                        'is_open': is_open,
                        'status': status,
                        'transfer_status': transfer_status,
                        'transfer_reject_reason': reject_reason,
                        'ticket_type': ticket_type,
                        'ticket_issue_count': int(ticket_issue) if not pd.isna(ticket_issue) else None,
                        'ticket_type_no': int(ticket_type_no) if not pd.isna(ticket_type_no) else None,
                        'ticket_valid_days': int(valid_days) if not pd.isna(valid_days) else None,
                        'notice': notice,
                        'holiday_name': holiday,
                    }
                )

                if day_created:
                    days_created += 1

            self.stdout.write(f'  日数: {calendar.days.count()}件')

        self.stdout.write(self.style.SUCCESS(
            f'\n完了: LessonCalendar {calendars_created}件, LessonCalendarDay {days_created}件'
        ))

    def _find_brand(self, calendar_code, tenant_id):
        """カレンダーコードからブランドを推定"""
        # コード例: 1001_SKAEC_A, 1003_AEC_P
        brand_map = {
            'AEC': ['アンイングリッシュクラブ', 'AEC'],
            'SKAEC': ['アンイングリッシュクラブ', 'AEC'],  # 星煌アン
            'SOR': ['アンそろばんクラブ', 'SOROBAN'],
            'Fude': ['アン美文字クラブ', 'FUDE'],
            'juku': ['アン進学ジム', 'GYM'],
            'suda': ['須田塾', 'SUDA'],
            'Int': ['アンインターナショナル', 'INT'],
        }

        for key, (brand_name, brand_code) in brand_map.items():
            if key in calendar_code:
                try:
                    return Brand.objects.get(tenant_id=tenant_id, brand_code=brand_code)
                except Brand.DoesNotExist:
                    try:
                        return Brand.objects.filter(
                            tenant_id=tenant_id,
                            brand_name__icontains=brand_name.split('【')[0]
                        ).first()
                    except Exception:
                        pass
        return None
