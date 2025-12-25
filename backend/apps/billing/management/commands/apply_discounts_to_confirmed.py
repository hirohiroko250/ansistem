"""
既存のConfirmedBillingにFS割引・マイル割引を適用するマネジメントコマンド

Usage:
    # ドライラン（変更しない）
    python manage.py apply_discounts_to_confirmed --dry-run

    # 特定の年月に適用
    python manage.py apply_discounts_to_confirmed --year 2025 --month 1

    # 実行
    python manage.py apply_discounts_to_confirmed
"""
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import models, transaction

from apps.billing.models import ConfirmedBilling
from apps.students.models import FSDiscount
from apps.pricing.calculations import calculate_mile_discount


class Command(BaseCommand):
    help = '既存のConfirmedBillingにFS割引・マイル割引を適用'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='対象年（指定しない場合は全て）'
        )
        parser.add_argument(
            '--month',
            type=int,
            help='対象月（指定しない場合は全て）'
        )
        parser.add_argument(
            '--tenant',
            type=str,
            default=None,
            help='テナントID（UUID形式、指定しない場合は全テナント）'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='既存の割引があっても上書き'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        year = options.get('year')
        month = options.get('month')
        tenant_id = options['tenant']
        force = options['force']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # 対象のConfirmedBillingを取得
        queryset = ConfirmedBilling.objects.filter(
            deleted_at__isnull=True
        ).select_related('student', 'guardian')

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        if year:
            queryset = queryset.filter(year=year)
        if month:
            queryset = queryset.filter(month=month)

        total_count = queryset.count()
        updated_count = 0
        skipped_count = 0
        fs_applied_count = 0
        mile_applied_count = 0

        self.stdout.write(f'対象件数: {total_count}件')

        # 保護者ごとにグループ化（マイル割引は保護者単位で1回のみ）
        from collections import defaultdict
        guardian_billings = defaultdict(list)
        for billing in queryset:
            if billing.guardian_id:
                key = (billing.guardian_id, billing.year, billing.month)
                guardian_billings[key].append(billing)

        # マイル割引を適用済みの保護者を追跡
        mile_applied_guardians = set()

        for billing in queryset:
            try:
                # この保護者にマイル割引を適用済みかチェック
                guardian_key = (billing.guardian_id, billing.year, billing.month)
                skip_mile = guardian_key in mile_applied_guardians

                result = self.apply_discounts(billing, dry_run, force, skip_mile_discount=skip_mile)
                if result['updated']:
                    updated_count += 1
                    if result['fs_applied']:
                        fs_applied_count += 1
                    if result['mile_applied']:
                        mile_applied_count += 1
                        mile_applied_guardians.add(guardian_key)
                else:
                    skipped_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'エラー: {billing.billing_no} - {e}')
                )

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
対象件数: {total_count}件
更新件数: {updated_count}件
スキップ: {skipped_count}件
FS割引適用: {fs_applied_count}件
マイル割引適用: {mile_applied_count}件
'''))

    def apply_discounts(self, billing: ConfirmedBilling, dry_run: bool, force: bool, skip_mile_discount: bool = False) -> dict:
        """個別の請求確定データに割引を適用

        Args:
            skip_mile_discount: Trueの場合、マイル割引をスキップ（同一保護者の2人目以降）
        """
        guardian = billing.guardian
        student = billing.student
        year = billing.year
        month = billing.month

        result = {
            'updated': False,
            'fs_applied': False,
            'mile_applied': False,
        }

        # 既存の割引スナップショットを取得
        existing_discounts = billing.discounts_snapshot or []

        # 既存のFS割引・マイル割引をチェック
        has_fs_discount = any(
            'FS' in (d.get('discount_name', '') or '') or
            '友達' in (d.get('discount_name', '') or '') or
            '紹介' in (d.get('discount_name', '') or '')
            for d in existing_discounts
        )
        has_mile_discount = any(
            'マイル' in (d.get('discount_name', '') or '')
            for d in existing_discounts
        )

        if not force and has_fs_discount and has_mile_discount:
            self.stdout.write(f'  スキップ: {billing.billing_no} - 既に割引あり')
            return result

        # 新しい割引を計算
        new_discounts = []
        new_discount_total = Decimal('0')

        # 既存の割引（FS割引・マイル割引以外）をコピー
        for d in existing_discounts:
            discount_name = d.get('discount_name', '') or ''
            if ('FS' not in discount_name and
                '友達' not in discount_name and
                '紹介' not in discount_name and
                'マイル' not in discount_name):
                new_discounts.append(d)
                new_discount_total += Decimal(str(d.get('amount', 0)))

        # 請求月の日付を計算（割引の有効期限チェック用）
        billing_date = date(year, month, 1)

        # FS割引を取得・適用
        if not has_fs_discount or force:
            fs_discounts = FSDiscount.objects.filter(
                tenant_id=billing.tenant_id,
                guardian=guardian,
                status=FSDiscount.Status.ACTIVE,
                valid_from__lte=billing_date,
            ).filter(
                models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=billing_date)
            )

            for fs in fs_discounts:
                if fs.discount_type == FSDiscount.DiscountType.PERCENTAGE:
                    # パーセント割引
                    amount = float(fs.discount_value)
                    discount_unit = 'percent'
                else:
                    # 固定額割引
                    amount = float(fs.discount_value)
                    discount_unit = 'yen'

                fs_discount_data = {
                    'discount_name': f'FS割引（{fs.friendship.friend_guardian.full_name if fs.friendship and fs.friendship.friend_guardian else "友達紹介"}）',
                    'amount': amount,
                    'discount_unit': discount_unit,
                    'source': 'fs_discount',
                    'fs_discount_id': str(fs.id),
                }
                new_discounts.append(fs_discount_data)

                if discount_unit == 'percent':
                    # パーセント割引の場合は小計から計算
                    discount_amount = Decimal(str(billing.subtotal)) * Decimal(str(amount)) / Decimal('100')
                else:
                    discount_amount = Decimal(str(amount))
                new_discount_total += discount_amount
                result['fs_applied'] = True

                self.stdout.write(
                    self.style.SUCCESS(f'  FS割引追加: {billing.billing_no} - {fs_discount_data["discount_name"]} (-{amount}{"%"if discount_unit=="percent" else "円"})')
                )

        # マイル割引を計算・適用（保護者単位で1回のみ）
        if not skip_mile_discount and (not has_mile_discount or force):
            mile_discount_amount, total_miles, mile_discount_name = calculate_mile_discount(guardian)

            if mile_discount_amount > 0:
                mile_discount_data = {
                    'discount_name': mile_discount_name,
                    'amount': float(mile_discount_amount),
                    'discount_unit': 'yen',
                    'source': 'mile_discount',
                    'total_miles': total_miles,
                    'is_family_discount': True,  # 保護者単位の割引
                }
                new_discounts.append(mile_discount_data)
                new_discount_total += mile_discount_amount
                result['mile_applied'] = True

                self.stdout.write(
                    self.style.SUCCESS(f'  マイル割引追加（家族）: {billing.billing_no} - {mile_discount_name} (-¥{mile_discount_amount})')
                )

        # 更新が必要かチェック
        if not result['fs_applied'] and not result['mile_applied']:
            return result

        # 合計金額を再計算
        new_total = Decimal(str(billing.subtotal)) - new_discount_total
        if new_total < 0:
            new_total = Decimal('0')

        if dry_run:
            self.stdout.write(
                f'  [ドライラン] {billing.billing_no}: 割引合計 {billing.discount_total} → {new_discount_total}, 請求額 {billing.total_amount} → {new_total}'
            )
        else:
            with transaction.atomic():
                billing.discounts_snapshot = new_discounts
                billing.discount_total = new_discount_total
                billing.total_amount = new_total
                billing.balance = new_total - billing.paid_amount
                billing.save(update_fields=[
                    'discounts_snapshot',
                    'discount_total',
                    'total_amount',
                    'balance',
                ])

            self.stdout.write(
                self.style.SUCCESS(f'  更新完了: {billing.billing_no}')
            )

        result['updated'] = True
        return result
