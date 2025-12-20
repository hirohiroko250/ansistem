"""
カタカナからローマ字に変換するコマンド

保護者・生徒のカタカナ姓名をローマ字に変換して設定します。
"""
from django.core.management.base import BaseCommand
from pykakasi import kakasi
from apps.students.models import Guardian, Student


class Command(BaseCommand):
    help = 'カタカナ姓名をローマ字に変換'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には更新せず、何が更新されるかを表示'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='既存のローマ字を上書き（デフォルトは空の場合のみ設定）'
        )
        parser.add_argument(
            '--guardian-only',
            action='store_true',
            help='保護者のみ処理'
        )
        parser.add_argument(
            '--student-only',
            action='store_true',
            help='生徒のみ処理'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        overwrite = options['overwrite']
        guardian_only = options['guardian_only']
        student_only = options['student_only']

        # kakasi初期化
        kks = kakasi()
        kks.setMode('K', 'a')  # カタカナ→ローマ字
        kks.setMode('H', 'a')  # ひらがな→ローマ字
        kks.setMode('J', 'a')  # 漢字→ローマ字
        conv = kks.getConverter()

        def to_roman(kana_text):
            """カタカナをローマ字に変換（先頭大文字）"""
            if not kana_text:
                return ''
            roman = conv.do(kana_text)
            return roman.capitalize()

        # 保護者を処理
        if not student_only:
            self.stdout.write("\n=== 保護者の処理 ===")
            guardians_updated = 0

            queryset = Guardian.objects.all()
            if not overwrite:
                # ローマ字が空のものだけ
                queryset = queryset.filter(
                    last_name_kana__isnull=False
                ).exclude(last_name_kana='')

            for guardian in queryset:
                updated = False
                new_last = None
                new_first = None

                # 姓のローマ字
                if guardian.last_name_kana and (overwrite or not guardian.last_name_roman):
                    new_last = to_roman(guardian.last_name_kana)
                    if new_last and new_last != guardian.last_name_roman:
                        updated = True

                # 名のローマ字
                if guardian.first_name_kana and (overwrite or not guardian.first_name_roman):
                    new_first = to_roman(guardian.first_name_kana)
                    if new_first and new_first != guardian.first_name_roman:
                        updated = True

                if updated:
                    self.stdout.write(
                        f"  {guardian.guardian_no}: "
                        f"{guardian.last_name_kana} {guardian.first_name_kana} -> "
                        f"{new_last or guardian.last_name_roman} {new_first or guardian.first_name_roman}"
                    )
                    if not dry_run:
                        if new_last:
                            guardian.last_name_roman = new_last
                        if new_first:
                            guardian.first_name_roman = new_first
                        guardian.save(update_fields=['last_name_roman', 'first_name_roman'])
                    guardians_updated += 1

            self.stdout.write(f"保護者: {guardians_updated}件")

        # 生徒を処理
        if not guardian_only:
            self.stdout.write("\n=== 生徒の処理 ===")
            students_updated = 0

            queryset = Student.objects.all()
            if not overwrite:
                queryset = queryset.filter(
                    last_name_kana__isnull=False
                ).exclude(last_name_kana='')

            for student in queryset:
                updated = False
                new_last = None
                new_first = None

                # 姓のローマ字
                if student.last_name_kana and (overwrite or not student.last_name_roman):
                    new_last = to_roman(student.last_name_kana)
                    if new_last and new_last != student.last_name_roman:
                        updated = True

                # 名のローマ字
                if student.first_name_kana and (overwrite or not student.first_name_roman):
                    new_first = to_roman(student.first_name_kana)
                    if new_first and new_first != student.first_name_roman:
                        updated = True

                if updated:
                    self.stdout.write(
                        f"  {student.student_no}: "
                        f"{student.last_name_kana} {student.first_name_kana} -> "
                        f"{new_last or student.last_name_roman} {new_first or student.first_name_roman}"
                    )
                    if not dry_run:
                        if new_last:
                            student.last_name_roman = new_last
                        if new_first:
                            student.first_name_roman = new_first
                        student.save(update_fields=['last_name_roman', 'first_name_roman'])
                    students_updated += 1

            self.stdout.write(f"生徒: {students_updated}件")

        # サマリー
        self.stdout.write("\n=== サマリー ===")
        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY RUN] 上記が更新対象です"))
        else:
            self.stdout.write(self.style.SUCCESS("変換が完了しました"))
