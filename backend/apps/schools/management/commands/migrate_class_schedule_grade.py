"""
開講時間割の対象学年を保護者用説明欄から抽出して設定

display_descriptionのパターン例:
- 【対象】①幼児(英語歴0年～)
- 【対象】②小１以上(英語歴0～2年以上)
- 【対象】③小４以上(英語歴3年以上)
- 【対象】④小５以上(英語歴5年以上)
- 【対象】⑤小６以上(英語歴9年以上)
- 【対象】⑥中2以上(英語歴11年以上)
"""
import re
from django.core.management.base import BaseCommand
from apps.schools.models import ClassSchedule, Grade


# 対象パターンからGrade名へのマッピング
GRADE_MAPPINGS = {
    # 幼児系
    '幼児': ['年少～', '年少以上', '年少～年長'],
    '年少': ['年少', '年少～', '年少以上'],
    '年中': ['年中', '年中～'],
    '年長': ['年長', '年長～', '年長以上'],
    # 小学生系
    '小1': ['小１', '小1', '小１以上', '小1以上', '小1～'],
    '小１': ['小１', '小1', '小１以上', '小1以上', '小１～'],
    '小2': ['小2', '小２', '小2以上', '小２以上'],
    '小３': ['小３', '小3', '小３以上', '小3以上'],
    '小3': ['小３', '小3', '小３以上', '小3以上'],
    '小４': ['小４', '小4', '小４以上', '小4以上'],
    '小4': ['小４', '小4', '小４以上', '小4以上'],
    '小５': ['小５', '小5', '小５以上', '小5以上'],
    '小5': ['小５', '小5', '小５以上', '小5以上'],
    '小６': ['小６', '小6', '小６以上', '小6以上'],
    '小6': ['小６', '小6', '小６以上', '小6以上'],
    # 中学生系
    '中1': ['中１', '中1', '中学生以上'],
    '中２': ['中２', '中2', '中学生以上'],
    '中2': ['中２', '中2', '中学生以上'],
    '中3': ['中3', '中３', '中学生以上'],
    # 高校生系
    '高1': ['高1', '高１'],
    '高2': ['高2', '高２'],
    '高3': ['高3', '高３'],
}


class Command(BaseCommand):
    help = '開講時間割の対象学年をdisplay_descriptionから抽出して設定'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には更新せず、何が更新されるかを表示'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='既存のgradeを上書き（デフォルトは空の場合のみ設定）'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        overwrite = options['overwrite']

        # Gradeのキャッシュを作成（grade_nameで検索できるように）
        grades_by_name = {}
        for grade in Grade.objects.all():
            grades_by_name[grade.grade_name] = grade
            # 全角/半角の揺れに対応
            normalized = grade.grade_name.replace('～', '~').replace('１', '1').replace('２', '2').replace('３', '3').replace('４', '4').replace('５', '5').replace('６', '6')
            grades_by_name[normalized] = grade

        self.stdout.write(f"利用可能な対象学年定義: {len(Grade.objects.all())}件")

        # ClassScheduleを処理
        queryset = ClassSchedule.objects.exclude(display_description='')
        if not overwrite:
            queryset = queryset.filter(grade__isnull=True)

        updated_count = 0
        not_found = []

        for schedule in queryset:
            target_info = self.extract_target(schedule.display_description)
            if not target_info:
                continue

            # Gradeを検索
            grade = self.find_matching_grade(target_info, grades_by_name, schedule.tenant_id)

            if grade:
                self.stdout.write(
                    f"  {schedule.schedule_code}: 【対象】{target_info} -> {grade.grade_name}"
                )
                if not dry_run:
                    schedule.grade = grade
                    schedule.save(update_fields=['grade'])
                updated_count += 1
            else:
                not_found.append((schedule.schedule_code, target_info))

        # サマリー
        self.stdout.write("\n=== サマリー ===")
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] {updated_count}件が更新対象"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{updated_count}件を更新しました"
            ))

        # 見つからなかったものの一覧
        if not_found:
            self.stdout.write("\n=== 対応するGradeが見つからなかったもの ===")
            unique_missing = set([x[1] for x in not_found])
            for missing in sorted(unique_missing):
                count = len([x for x in not_found if x[1] == missing])
                self.stdout.write(f"  - {missing} ({count}件)")

    def extract_target(self, description):
        """display_descriptionから対象情報を抽出

        Returns:
            str: 対象情報（例: "幼児", "小１以上"）または None
        """
        if not description:
            return None

        # パターン: 【対象】の後に続く文字列を抽出
        # 例: 【対象】①幼児(英語歴0年～) -> 幼児
        # 例: 【対象】②小１以上(英語歴0～2年以上) -> 小１以上
        pattern = r'【対象】[①②③④⑤⑥⑦⑧⑨⑩]?([^(（【]+)'
        match = re.search(pattern, description)

        if match:
            target = match.group(1).strip()
            # 括弧の前で切る
            target = re.split(r'[(（]', target)[0].strip()
            return target

        return None

    def find_matching_grade(self, target_info, grades_by_name, tenant_id):
        """対象情報に一致するGradeレコードを探す

        Args:
            target_info: 対象情報（例: "幼児", "小１以上"）
            grades_by_name: grade_nameでインデックスされたGradeの辞書
            tenant_id: テナントID

        Returns:
            Grade or None
        """
        # 直接一致を試す
        if target_info in grades_by_name:
            grade = grades_by_name[target_info]
            if grade.tenant_id == tenant_id:
                return grade

        # マッピングから候補を探す
        for pattern, candidates in GRADE_MAPPINGS.items():
            if pattern in target_info:
                for candidate in candidates:
                    if candidate in grades_by_name:
                        grade = grades_by_name[candidate]
                        if grade.tenant_id == tenant_id:
                            return grade

        # テナントを無視して検索（フォールバック）
        if target_info in grades_by_name:
            return grades_by_name[target_info]

        for pattern, candidates in GRADE_MAPPINGS.items():
            if pattern in target_info:
                for candidate in candidates:
                    if candidate in grades_by_name:
                        return grades_by_name[candidate]

        return None
