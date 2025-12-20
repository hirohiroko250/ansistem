"""
説明欄から対象学年を抽出してgradeフィールドに設定

説明欄のパターン例:
- "対象学年: 年長~小4"
- "対象学年: 小3~中1"
- "対象学年: 小4~高3"

対象学年定義(Grade)のgrade_nameと照合して紐付ける
"""
import re
from django.core.management.base import BaseCommand
from apps.contracts.models import Course, Pack
from apps.schools.models import Grade


class Command(BaseCommand):
    help = '説明欄から対象学年をgradeフィールドに移行'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には更新せず、何が更新されるかを表示'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Gradeのキャッシュを作成（grade_nameで検索できるように）
        grades_by_name = {}
        for grade in Grade.objects.all():
            grades_by_name[grade.grade_name] = grade
            # 「～」を「~」に置き換えたバージョンも追加
            grades_by_name[grade.grade_name.replace('～', '~')] = grade

        self.stdout.write(f"利用可能な対象学年定義: {len(grades_by_name)}件")

        # コースを処理
        self.stdout.write("\n=== コースの処理 ===")
        courses_updated = 0
        courses_not_found = []

        for course in Course.objects.filter(description__icontains='対象学年'):
            grade_range = self.extract_grade_range(course.description)
            if grade_range:
                # 対応するGradeレコードを探す
                grade = self.find_matching_grade(grade_range, grades_by_name, course.tenant_id)

                if grade:
                    self.stdout.write(
                        f"  {course.course_code}: {course.description[:50]} -> {grade.grade_name}"
                    )
                    if not dry_run:
                        course.grade = grade
                        course.save(update_fields=['grade'])
                    courses_updated += 1
                else:
                    courses_not_found.append((course.course_code, grade_range))
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {course.course_code}: Grade '{grade_range}' が見つかりません"
                        )
                    )

        # パックを処理
        self.stdout.write("\n=== パックの処理 ===")
        packs_updated = 0
        packs_not_found = []

        for pack in Pack.objects.filter(description__icontains='対象学年'):
            grade_range = self.extract_grade_range(pack.description)
            if grade_range:
                grade = self.find_matching_grade(grade_range, grades_by_name, pack.tenant_id)

                if grade:
                    self.stdout.write(
                        f"  {pack.pack_code}: {pack.description[:50]} -> {grade.grade_name}"
                    )
                    if not dry_run:
                        pack.grade = grade
                        pack.save(update_fields=['grade'])
                    packs_updated += 1
                else:
                    packs_not_found.append((pack.pack_code, grade_range))
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {pack.pack_code}: Grade '{grade_range}' が見つかりません"
                        )
                    )

        # サマリー
        self.stdout.write("\n=== サマリー ===")
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] コース: {courses_updated}件, パック: {packs_updated}件 が更新対象"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"コース: {courses_updated}件, パック: {packs_updated}件 を更新しました"
            ))

        # 見つからなかった対象学年の一覧
        if courses_not_found or packs_not_found:
            self.stdout.write("\n=== 見つからなかった対象学年 ===")
            unique_missing = set([x[1] for x in courses_not_found + packs_not_found])
            for missing in sorted(unique_missing):
                self.stdout.write(f"  - {missing}")

    def extract_grade_range(self, description):
        """説明欄から対象学年範囲を抽出

        Returns:
            str: 対象学年範囲（例: "年長～小4"）または None
        """
        if not description:
            return None

        # パターン: "対象学年: XXX~YYY" or "対象学年：XXX～YYY"
        pattern = r'対象学年[:\s：]+([^\s~～]+)[~～]([^\s~～\n]+)'
        match = re.search(pattern, description)

        if match:
            min_grade = match.group(1).strip()
            max_grade = match.group(2).strip()
            # 正規化：「~」→「～」
            return f"{min_grade}～{max_grade}"

        return None

    def find_matching_grade(self, grade_range, grades_by_name, tenant_id):
        """対象学年範囲に一致するGradeレコードを探す

        Args:
            grade_range: 対象学年範囲（例: "年長～小4"）
            grades_by_name: grade_nameでインデックスされたGradeの辞書
            tenant_id: テナントID

        Returns:
            Grade or None
        """
        # 直接一致を試す
        if grade_range in grades_by_name:
            grade = grades_by_name[grade_range]
            # テナントIDが一致するか確認
            if grade.tenant_id == tenant_id:
                return grade

        # 「~」を「～」に置き換えて再試行
        normalized = grade_range.replace('~', '～')
        if normalized in grades_by_name:
            grade = grades_by_name[normalized]
            if grade.tenant_id == tenant_id:
                return grade

        # テナントを無視して検索（見つからない場合のフォールバック）
        for name, grade in grades_by_name.items():
            if name == grade_range or name == normalized:
                return grade

        return None
