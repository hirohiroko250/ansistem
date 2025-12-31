"""
T6 割引情報インポートコマンド
CSVファイルから割引データをインポートする
"""
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction, models
from apps.contracts.models import StudentDiscount
from apps.students.models import Guardian, Student, FriendshipRegistration
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'T6 割引情報CSVをインポート'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='CSVファイルのパス')
        parser.add_argument('--tenant', type=str, default=None, help='テナントID')
        parser.add_argument('--dry-run', action='store_true', help='実際には保存しない')
        parser.add_argument('--create-fs-registration', action='store_true',
                          help='FS割引の場合にFriendshipRegistrationも作成')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        tenant_id = options.get('tenant')
        create_fs_registration = options.get('create_fs_registration', False)

        # テナント取得
        if tenant_id:
            tenant = Tenant.objects.get(id=tenant_id)
        else:
            tenant = Tenant.objects.first()

        if not tenant:
            self.stderr.write(self.style.ERROR('テナントが見つかりません'))
            return

        self.stdout.write(f'テナント: {tenant.tenant_name} ({tenant.id})')
        self.stdout.write(f'CSVファイル: {csv_file}')
        self.stdout.write(f'Dry run: {dry_run}')
        self.stdout.write(f'FS登録作成: {create_fs_registration}')

        new_count = 0
        updated_count = 0
        skipped_count = 0
        fs_registration_count = 0
        errors = []

        # 割引種別ごとのカウント
        discount_types = {}

        # キャッシュ
        self.guardian_cache = {}
        self.student_cache = {}

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'総行数: {len(rows)}')

        for row in rows:
            try:
                with transaction.atomic():
                    result, discount_name, guardian = self._import_discount(row, tenant, dry_run)
                    if result == 'new':
                        new_count += 1
                    elif result == 'updated':
                        updated_count += 1
                    elif result == 'skipped':
                        skipped_count += 1

                    # 割引種別カウント
                    if discount_name:
                        # 割引名を簡略化（最初の10文字）
                        short_name = discount_name[:15] if len(discount_name) > 15 else discount_name
                        discount_types[short_name] = discount_types.get(short_name, 0) + 1

                    # FS割引の場合、FriendshipRegistrationを作成
                    if create_fs_registration and guardian and 'FS' in discount_name:
                        fs_created = self._create_fs_registration(guardian, tenant, dry_run)
                        if fs_created:
                            fs_registration_count += 1

            except Exception as e:
                errors.append(f"割引ID {row.get('割引ID', 'unknown')}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f'''
インポート完了:
- 新規: {new_count}件
- 更新: {updated_count}件
- スキップ: {skipped_count}件
- FS登録作成: {fs_registration_count}件
- エラー: {len(errors)}件
'''))

        # 割引種別サマリー
        self.stdout.write('\n割引種別サマリー:')
        for name, count in sorted(discount_types.items(), key=lambda x: -x[1]):
            self.stdout.write(f'  {name}: {count}件')

        if errors[:10]:
            self.stderr.write('\nエラー詳細（最初の10件）:')
            for err in errors[:10]:
                self.stderr.write(f'  {err}')

    def _parse_date(self, date_str):
        """日付文字列をパース"""
        if not date_str or date_str.strip() == '':
            return None
        try:
            return datetime.strptime(date_str, '%Y/%m/%d').date()
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return None

    def _get_guardian(self, guardian_id, tenant):
        """保護者を取得（キャッシュ使用）"""
        if not guardian_id:
            return None
        if guardian_id not in self.guardian_cache:
            guardian = Guardian.objects.filter(
                models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
            ).filter(
                models.Q(old_id=guardian_id) | models.Q(guardian_no=guardian_id)
            ).first()
            self.guardian_cache[guardian_id] = guardian
        return self.guardian_cache.get(guardian_id)

    def _get_student(self, student_id, tenant):
        """生徒を取得（キャッシュ使用）"""
        if not student_id:
            return None
        if student_id not in self.student_cache:
            student = Student.objects.filter(
                models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
            ).filter(
                models.Q(old_id=student_id) | models.Q(student_no=student_id)
            ).first()
            self.student_cache[student_id] = student
        return self.student_cache.get(student_id)

    def _create_fs_registration(self, guardian, tenant, dry_run):
        """FS割引用のFriendshipRegistrationを作成"""
        from django.utils import timezone

        # 既存のFS登録があるか確認（自己登録）
        existing = FriendshipRegistration.objects.filter(
            models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
        ).filter(
            requester=guardian
        ).exists()

        if existing:
            return False  # 既に登録済み

        if dry_run:
            return True

        # FS登録を作成（requester=target=自分自身として、後で相手を設定する想定）
        # targetはrequesterと同じにはできないため、プレースホルダーとしてnotes記載
        # 実際の運用では管理画面からtargetを設定してもらう
        try:
            fs_reg = FriendshipRegistration(
                tenant_ref=tenant,
                requester=guardian,
                target=guardian,  # 一時的に自己参照（後で修正必要）
                status=FriendshipRegistration.Status.ACCEPTED,  # 割引適用済みなので承認済み
                accepted_at=timezone.now(),
                notes='CSVインポートにより自動作成。対象者の設定が必要です。'
            )
            fs_reg.save()
            return True
        except Exception as e:
            # unique_togetherエラーなどの場合はスキップ
            return False

    def _import_discount(self, row, tenant, dry_run):
        """割引をインポート"""
        discount_id = row.get('割引ID', '')

        if not discount_id:
            return 'skipped', '', None

        # 有効/無効チェック
        is_active = row.get('有無', '1') == '1'

        # 保護者・生徒を取得
        guardian_id = row.get('保護者ID', '')
        student_id = row.get('生徒ID', '')

        guardian = self._get_guardian(guardian_id, tenant)
        student = self._get_student(student_id, tenant)

        # 保護者も生徒もいない場合はスキップ
        if not guardian and not student:
            return 'skipped', '', None

        # 金額
        amount_str = row.get('金額', '0') or '0'
        try:
            amount = Decimal(amount_str.replace(',', ''))
        except (InvalidOperation, ValueError, AttributeError):
            amount = Decimal('0')

        # 割引単位
        unit_str = row.get('割引単位', '円')
        if unit_str == '%':
            discount_unit = 'percent'
        else:
            discount_unit = 'yen'

        # 割引名
        discount_name = row.get('顧客表記用割引名（契約、請求IDの割引は、そのすぐ下に表記）', '') or row.get('割引名', '') or '割引'

        # 終了条件
        end_condition_str = row.get('終了条件', '')
        if end_condition_str == '毎月':
            end_condition = 'monthly'
        elif end_condition_str == '終了日まで':
            end_condition = 'until_end_date'
        else:
            end_condition = 'once'

        # 繰り返し・自動割引
        is_recurring = row.get('繰り返し', '0') == '1'
        is_auto = row.get('自動割引', '0') == '1'

        # 日付
        start_date = self._parse_date(row.get('開始日', ''))
        end_date = self._parse_date(row.get('終了日', ''))

        # 備考
        notes_parts = []
        if row.get('社長のIF文用備考', ''):
            notes_parts.append(row.get('社長のIF文用備考', ''))
        if row.get('返金時の注意', ''):
            notes_parts.append(f"返金時注意: {row.get('返金時の注意', '')}")
        notes = '\n'.join(notes_parts)

        # 既存の割引を検索
        discount = StudentDiscount.objects.filter(
            models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
        ).filter(old_id=discount_id).first()

        created = discount is None
        if created:
            discount = StudentDiscount(tenant_ref=tenant)

        # フィールド設定
        discount.old_id = discount_id
        discount.guardian = guardian
        discount.student = student
        discount.discount_name = discount_name[:200] if discount_name else '割引'
        discount.amount = amount
        discount.discount_unit = discount_unit
        discount.start_date = start_date
        discount.end_date = end_date
        discount.is_recurring = is_recurring
        discount.is_auto = is_auto
        discount.end_condition = end_condition
        discount.is_active = is_active
        discount.notes = notes

        # deleted_at も管理（is_active=Falseの場合）
        if not is_active:
            from django.utils import timezone
            discount.deleted_at = timezone.now()
        else:
            discount.deleted_at = None

        if not dry_run:
            discount.save()

        return ('new' if created else 'updated'), discount_name, guardian
