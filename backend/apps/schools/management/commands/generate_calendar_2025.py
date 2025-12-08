"""
2025年度開講カレンダー生成コマンド

使用例:
  python manage.py generate_calendar_2025
  python manage.py generate_calendar_2025 --brand AEC --dry-run
"""
from django.core.management.base import BaseCommand
from apps.schools.models import Brand, School, LessonCalendar, BrandSchool
from apps.tenants.models import Tenant
from datetime import date, timedelta
import calendar

# 曜日名（日本語）
WEEKDAY_NAMES = ['月', '火', '水', '木', '金', '土', '日']

# 2025年度の祝日（2025/4/1 - 2026/3/31）
HOLIDAYS_2025 = {
    date(2025, 4, 29): '昭和の日',
    date(2025, 5, 3): '憲法記念日',
    date(2025, 5, 4): 'みどりの日',
    date(2025, 5, 5): 'こどもの日',
    date(2025, 5, 6): '振替休日',
    date(2025, 7, 21): '海の日',
    date(2025, 8, 11): '山の日',
    date(2025, 9, 15): '敬老の日',
    date(2025, 9, 23): '秋分の日',
    date(2025, 10, 13): 'スポーツの日',
    date(2025, 11, 3): '文化の日',
    date(2025, 11, 23): '勤労感謝の日',
    date(2025, 11, 24): '振替休日',
    date(2026, 1, 1): '元日',
    date(2026, 1, 13): '成人の日',
    date(2026, 2, 11): '建国記念の日',
    date(2026, 2, 23): '天皇誕生日',
    date(2026, 3, 20): '春分の日',
}

# 長期休暇期間（休講）
LONG_HOLIDAYS = [
    # 春休み（2025年度開始前）
    (date(2025, 4, 1), date(2025, 4, 6)),
    # GW
    (date(2025, 4, 29), date(2025, 5, 6)),
    # お盆
    (date(2025, 8, 10), date(2025, 8, 16)),
    # 年末年始
    (date(2025, 12, 28), date(2026, 1, 5)),
    # 春休み（2025年度末）
    (date(2026, 3, 25), date(2026, 3, 31)),
]


class Command(BaseCommand):
    help = '2025年度（2025/4〜2026/3）の開講カレンダーを生成'

    def add_arguments(self, parser):
        parser.add_argument(
            '--brand',
            type=str,
            help='特定ブランドのみ生成（ブランドコード）',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際に保存せずプレビューのみ',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='既存の2025年度カレンダーを削除してから生成',
        )

    def handle(self, *args, **options):
        brand_code = options.get('brand')
        dry_run = options.get('dry_run', False)
        clear = options.get('clear', False)

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # 期間設定
        start_date = date(2025, 4, 1)
        end_date = date(2026, 3, 31)

        # 既存データ削除
        if clear and not dry_run:
            deleted = LessonCalendar.objects.filter(
                lesson_date__gte=start_date,
                lesson_date__lte=end_date
            ).delete()
            self.stdout.write(f'既存カレンダー削除: {deleted[0]}件')

        # ブランドと開講校舎の組み合わせを取得
        brand_schools = BrandSchool.objects.filter(is_active=True).select_related('brand', 'school')

        if brand_code:
            brand_schools = brand_schools.filter(brand__brand_code=brand_code)

        if not brand_schools.exists():
            self.stdout.write(self.style.WARNING('開講校舎が見つかりません'))
            return

        created_count = 0

        for bs in brand_schools:
            brand = bs.brand
            school = bs.school

            # 校舎コードからカレンダーID用のコードを生成
            # S10001 → 0001
            school_num = school.school_code.replace('S1', '')

            # カレンダーパターン（A/B/P）を決定
            # ここでは仮にAパターンで生成
            calendar_types = ['A']  # 必要に応じて ['A', 'B', 'P'] など

            for cal_type in calendar_types:
                calendar_code = f"{school_num}_{brand.brand_code}_{cal_type}"

                # 日付ループ
                current_date = start_date
                ticket_seq = {}  # 月ごとのチケット連番

                while current_date <= end_date:
                    weekday = current_date.weekday()
                    weekday_name = WEEKDAY_NAMES[weekday]
                    month_key = f"{current_date.year}-{current_date.month}"

                    # 休講判定
                    is_holiday = current_date in HOLIDAYS_2025
                    is_long_holiday = any(
                        start <= current_date <= end
                        for start, end in LONG_HOLIDAYS
                    )
                    is_open = not (is_holiday or is_long_holiday or weekday == 6)  # 日曜は休講

                    # 開講日の場合の設定
                    display_label = '休'
                    ticket_type = None
                    ticket_sequence = None
                    holiday_name = HOLIDAYS_2025.get(current_date, '')

                    if is_open:
                        # チケット連番をカウント
                        if month_key not in ticket_seq:
                            ticket_seq[month_key] = 0
                        ticket_seq[month_key] += 1
                        ticket_sequence = ticket_seq[month_key]

                        # 表示ラベル（例: 水A1）
                        display_label = f"{weekday_name}{cal_type}{ticket_sequence}"
                        ticket_type = cal_type

                    if dry_run:
                        if is_open and current_date.day <= 15 and current_date.month == 4:
                            self.stdout.write(
                                f"  {calendar_code} | {current_date} | {weekday_name} | "
                                f"{display_label} | {'Y' if is_open else ''} | {ticket_type or ''}"
                            )
                    else:
                        LessonCalendar.objects.update_or_create(
                            tenant_id=tenant.id,
                            calendar_code=calendar_code,
                            lesson_date=current_date,
                            defaults={
                                'brand': brand,
                                'school': school,
                                'day_of_week': weekday_name,
                                'is_open': is_open,
                                'lesson_type': cal_type if is_open else 'closed',
                                'display_label': display_label,
                                'ticket_type': ticket_type or '',
                                'ticket_sequence': ticket_sequence,
                                'holiday_name': holiday_name,
                                'is_makeup_allowed': True,
                                'auto_send_notice': False,
                                'tenant_ref': tenant,
                            }
                        )
                        created_count += 1

                    current_date += timedelta(days=1)

                if dry_run:
                    self.stdout.write(f"[DRY-RUN] {calendar_code}: 365日分")

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'\n[DRY-RUN] 生成予定: {len(brand_schools) * 365}件'))
        else:
            self.stdout.write(self.style.SUCCESS(f'カレンダー生成完了: {created_count}件'))
