"""
コースにチケットを自動割り当て

コース名からパターンを解析し、適切なチケットを割り当てる。
"""
import re
from django.core.management.base import BaseCommand
from apps.contracts.models import Course, CourseTicket, Ticket


# コース名パターン → チケットコードのマッピング
# リレーは外国人講師ticket優先（学校のチケット設定に合わせる）
TICKET_MAPPINGS = {
    # White系（40分）
    ('White', 'ペア'): 'T10000001',
    ('White', 'リレー'): 'T10000003',  # 外国人講師
    ('White', 'ネイティブ'): 'T10000007',
    ('White', 'web1：4'): 'T10000045',
    ('White', 'web1:4'): 'T10000045',
    ('White', 'web1：1'): 'T10000057',
    ('White', 'web1:1'): 'T10000057',

    # Yellow系（50分）
    ('Yellow', 'ペア'): 'T10000009',
    ('Yellow', 'リレー'): 'T10000013',  # 外国人講師
    ('Yellow', 'ネイティブ'): 'T10000015',
    ('Yellow', 'web1：6'): 'T10000047',
    ('Yellow', 'web1:6'): 'T10000047',
    ('Yellow', 'web1：1'): 'T10000059',
    ('Yellow', 'web1:1'): 'T10000059',

    # Red系（50分）
    ('Red', 'ペア'): 'T10000017',
    ('Red', 'リレー'): 'T10000019',  # 外国人講師
    ('Red', 'ネイティブ'): 'T10000023',
    ('Red', 'web1：6'): 'T10000049',
    ('Red', 'web1:6'): 'T10000049',
    ('Red', 'web1：1'): 'T10000061',
    ('Red', 'web1:1'): 'T10000061',

    # Purple系（50分）
    ('Purple', 'ペア'): 'T10000025',
    ('Purple', 'リレー'): 'T10000027',  # 外国人講師
    ('Purple', 'ネイティブ'): 'T10000031',
    ('Purple', 'web1：6'): 'T10000051',
    ('Purple', 'web1:6'): 'T10000051',
    ('Purple', 'web1：1'): 'T10000063',
    ('Purple', 'web1:1'): 'T10000063',

    # 英会話A系（50分）
    ('英会話A', 'ペア'): 'T10000033',
    ('英会話A', 'リレー'): 'T10000035',  # 外国人講師
    ('英会話A', 'ネイティブ'): 'T10000037',
    ('英会話A', 'web1：6'): 'T10000053',
    ('英会話A', 'web1:6'): 'T10000053',
    ('英会話A', 'web1：1'): 'T10000065',
    ('英会話A', 'web1:1'): 'T10000065',

    # 英会話B系（50分）
    ('英会話B', 'ペア'): 'T10000039',
    ('英会話B', 'リレー'): 'T10000041',  # 外国人講師
    ('英会話B', 'ネイティブ'): 'T10000043',
    ('英会話B', 'web1：6'): 'T10000055',
    ('英会話B', 'web1:6'): 'T10000055',
    ('英会話B', 'web1：1'): 'T10000067',
    ('英会話B', 'web1:1'): 'T10000067',
}

# 色・レベルのパターン
COLORS = ['White', 'Yellow', 'Red', 'Purple', '英会話A', '英会話B']
# クラスタイプのパターン
CLASS_TYPES = ['ペア', 'リレー', 'ネイティブ', 'web1：4', 'web1:4', 'web1：6', 'web1:6', 'web1：1', 'web1:1']


class Command(BaseCommand):
    help = 'コース名からパターンを解析し、チケットを割り当てる'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には更新せず、何が更新されるかを表示'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='既存のCourseTicketを上書き（デフォルトは新規のみ）'
        )
        parser.add_argument(
            '--brand',
            type=str,
            default='アンイングリッシュクラブ',
            help='対象のブランド名（デフォルト: アンイングリッシュクラブ）'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        overwrite = options['overwrite']
        brand_name = options['brand']

        # Ticketのキャッシュを作成
        tickets_by_code = {}
        for ticket in Ticket.objects.all():
            tickets_by_code[ticket.ticket_code] = ticket

        self.stdout.write(f"利用可能なチケット: {len(tickets_by_code)}件")

        # 既存のCourseTicketを確認
        existing_course_ids = set(
            CourseTicket.objects.values_list('course_id', flat=True)
        )
        self.stdout.write(f"既存のCourseTicket: {len(existing_course_ids)}件")

        # 対象のコースを取得
        queryset = Course.objects.filter(brand__brand_name=brand_name)
        if not overwrite:
            queryset = queryset.exclude(id__in=existing_course_ids)

        self.stdout.write(f"処理対象のコース: {queryset.count()}件")

        created_count = 0
        not_matched = []

        for course in queryset:
            ticket_code = self.find_matching_ticket(course.course_name)

            if ticket_code and ticket_code in tickets_by_code:
                ticket = tickets_by_code[ticket_code]
                self.stdout.write(
                    f"  {course.course_code}: {course.course_name}"
                )
                self.stdout.write(
                    self.style.SUCCESS(f"    -> {ticket_code}: {ticket.ticket_name}")
                )

                if not dry_run:
                    # 既存のものがあれば削除（overwriteモードの場合）
                    if overwrite:
                        CourseTicket.objects.filter(course=course).delete()

                    # 新規作成
                    CourseTicket.objects.create(
                        course=course,
                        ticket=ticket,
                        quantity=1,
                        per_week=1,
                        tenant_id=course.tenant_id
                    )
                created_count += 1
            else:
                not_matched.append((course.course_code, course.course_name))

        # サマリー
        self.stdout.write("\n=== サマリー ===")
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] {created_count}件のCourseTicketを作成予定"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{created_count}件のCourseTicketを作成しました"
            ))

        # マッチしなかったものの一覧
        if not_matched:
            self.stdout.write(f"\n=== マッチしなかったコース ({len(not_matched)}件) ===")
            for code, name in not_matched[:20]:
                self.stdout.write(f"  - {code}: {name}")
            if len(not_matched) > 20:
                self.stdout.write(f"  ... 他 {len(not_matched) - 20}件")

    def find_matching_ticket(self, course_name):
        """コース名からマッチするチケットコードを見つける"""
        if not course_name:
            return None

        # 色・レベルを検出
        detected_color = None
        for color in COLORS:
            if color in course_name:
                detected_color = color
                break

        if not detected_color:
            return None

        # クラスタイプを検出
        detected_type = None
        for class_type in CLASS_TYPES:
            if class_type in course_name:
                detected_type = class_type
                break

        if not detected_type:
            return None

        # マッピングを検索
        key = (detected_color, detected_type)
        return TICKET_MAPPINGS.get(key)
