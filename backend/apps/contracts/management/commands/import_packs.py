"""
パックおよびPackCourse（パック→コース紐付け）をインポート

データソース:
1. T3_契約情報.csv から契約種類=4のレコードでPackを作成
2. T51_パック組み合わせ情報.csv からPackCourse（紐付け）を作成
"""
from django.core.management.base import BaseCommand
from django.db import transaction
import csv
from apps.contracts.models import Course, Pack, PackCourse
from apps.schools.models import Brand


def convert_contract_id_to_course_code(contract_id):
    """
    契約ID形式をDBのcourse_code形式に変換
    例: 24AEC_1000007 → CAEC1000007
    """
    if not contract_id:
        return None
    contract_id = contract_id.strip()
    # 24AEC_1000007 → parts[0]=24AEC, parts[1]=1000007
    parts = contract_id.split('_')
    if len(parts) != 2:
        return contract_id  # 変換できない場合はそのまま
    prefix = parts[0]  # 24AEC
    num = parts[1]     # 1000007
    # 年度2桁を除去してブランドコードを取得
    if len(prefix) >= 4 and prefix[:2].isdigit():
        brand_code = prefix[2:]  # AEC
        return f"C{brand_code}{num}"  # CAEC1000007
    return contract_id


class Command(BaseCommand):
    help = 'パックとPackCourse（コース紐付け）をインポート'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='/app/data/T3_契約情報_202512021655_UTF8.csv',
            help='T3_契約情報CSVのパス',
        )
        parser.add_argument(
            '--t51-path',
            type=str,
            default='/app/data/T51_パック組み合わせ情報.csv',
            help='T51_パック組み合わせ情報CSVのパス',
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            default='10cb2ac9-72cc-4159-9862-004609b84e7d',
            help='テナントID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='プレビューのみ（DBに書き込まない）',
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        t51_path = options['t51_path']
        tenant_id = options['tenant_id']
        dry_run = options['dry_run']

        self.stdout.write(f"テナントID: {tenant_id}")
        self.stdout.write(f"CSVパス: {csv_path}")
        self.stdout.write(f"T51パス: {t51_path}")
        self.stdout.write(f"ドライラン: {dry_run}")
        self.stdout.write("")

        # ========================================
        # Step 1: T3からパックを作成
        # ========================================
        self.stdout.write("=== Step 1: T3からPackをインポート ===")

        # CSVを読み込み
        unique_packs = {}  # pack_code -> {name, brand_name}
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    contract_type = row.get('契約種類', '')
                    if contract_type != '4':  # パックのみ
                        continue

                    pack_code = row.get('契約ID', '').strip()
                    if not pack_code:
                        continue

                    if pack_code not in unique_packs:
                        unique_packs[pack_code] = {
                            'name': row.get('契約名', pack_code).strip(),
                            'brand_name': row.get('契約ブランド名', '').strip(),
                        }
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"CSVの読み込みに失敗: {e}"))
            return

        self.stdout.write(f"ユニークなパック数: {len(unique_packs):,}件")

        # ブランドのマッピングを作成
        brand_map = {}
        for brand in Brand.objects.filter(tenant_id=tenant_id):
            brand_map[brand.brand_name] = brand

        pack_created = 0
        pack_updated = 0
        pack_errors = 0

        if not dry_run:
            with transaction.atomic():
                for pack_code, info in unique_packs.items():
                    try:
                        brand = brand_map.get(info['brand_name']) if info['brand_name'] else None

                        pack, created = Pack.objects.update_or_create(
                            tenant_id=tenant_id,
                            pack_code=pack_code,
                            defaults={
                                'pack_name': info['name'],
                                'brand': brand,
                                'is_active': True,
                            }
                        )

                        if created:
                            pack_created += 1
                        else:
                            pack_updated += 1

                    except Exception as e:
                        pack_errors += 1
                        if pack_errors <= 5:
                            self.stdout.write(f"  エラー: {e}")

        self.stdout.write(f"Pack作成: {pack_created:,}件, 更新: {pack_updated:,}件, エラー: {pack_errors}件")

        # ========================================
        # Step 2: T51からPackCourseを作成
        # ========================================
        self.stdout.write("")
        self.stdout.write("=== Step 2: T51からPackCourseをインポート ===")

        # T51 CSVを読み込み
        t51_rows = []
        try:
            with open(t51_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    t51_rows.append(row)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"T51の読み込みに失敗: {e}"))
            return

        self.stdout.write(f"T51行数: {len(t51_rows):,}件")

        # パックのマッピングを作成
        pack_map = {}
        for pack in Pack.objects.filter(tenant_id=tenant_id):
            pack_map[pack.pack_code] = pack

        # コースのマッピングを作成
        course_map = {}
        for course in Course.objects.filter(tenant_id=tenant_id):
            course_map[course.course_code] = course

        pc_created = 0
        pc_updated = 0
        pc_errors = 0
        missing_packs = set()
        missing_courses = set()

        if not dry_run:
            with transaction.atomic():
                for row in t51_rows:
                    try:
                        pack_code = row.get('パック契約ID', '').strip()
                        if not pack_code:
                            continue

                        pack = pack_map.get(pack_code)
                        if not pack:
                            missing_packs.add(pack_code)
                            continue

                        # コースコードを取得
                        course_cols = ['基本契約ID_1', '基本契約ID_2', '基本契約ID_3', '基本契約ID_4']
                        for sort_order, col_name in enumerate(course_cols, start=1):
                            csv_course_code = row.get(col_name, '').strip()
                            if not csv_course_code:
                                continue

                            # 契約ID形式をDB形式に変換
                            course_code = convert_contract_id_to_course_code(csv_course_code)
                            course = course_map.get(course_code)

                            if not course:
                                missing_courses.add(course_code)
                                continue

                            pc, created = PackCourse.objects.update_or_create(
                                pack=pack,
                                course=course,
                                defaults={
                                    'tenant_id': tenant_id,
                                    'sort_order': sort_order,
                                    'is_active': True,
                                }
                            )

                            if created:
                                pc_created += 1
                            else:
                                pc_updated += 1

                    except Exception as e:
                        pc_errors += 1
                        if pc_errors <= 5:
                            self.stdout.write(f"  エラー: {e}")

        self.stdout.write(f"PackCourse作成: {pc_created:,}件, 更新: {pc_updated:,}件, エラー: {pc_errors}件")

        if missing_packs:
            self.stdout.write(f"存在しないPack: {len(missing_packs)}件")
            for code in sorted(missing_packs)[:10]:
                self.stdout.write(f"  - {code}")

        if missing_courses:
            self.stdout.write(f"存在しないCourse: {len(missing_courses)}件")
            for code in sorted(missing_courses)[:10]:
                self.stdout.write(f"  - {code}")

        # ========================================
        # 結果確認
        # ========================================
        self.stdout.write("")
        self.stdout.write("=== 結果確認 ===")
        self.stdout.write(f"Pack総数: {Pack.objects.filter(tenant_id=tenant_id).count():,}件")
        self.stdout.write(f"PackCourse総数: {PackCourse.objects.filter(tenant_id=tenant_id).count():,}件")

        # サンプル表示
        self.stdout.write("")
        self.stdout.write("=== サンプル（最初の5パック）===")
        for pack in Pack.objects.filter(tenant_id=tenant_id).prefetch_related('pack_courses__course')[:5]:
            self.stdout.write(f"\n【{pack.pack_code}】{pack.pack_name}")
            for pc in pack.pack_courses.all().order_by('sort_order'):
                self.stdout.write(f"  └ {pc.sort_order}: {pc.course.course_name}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("インポート完了！"))
