"""
月次請求を生成するマネジメントコマンド

- Contract/StudentItemから基本請求を取得
- CertificationEnrollment/SeminarEnrollmentから検定・講習を取得
- billing_monthでフィルタして対象月の請求を生成

Usage:
    # ドライラン
    python manage.py generate_monthly_billing --year 2025 --month 1 --dry-run

    # 実行
    python manage.py generate_monthly_billing --year 2025 --month 1

    # 既存データを上書き
    python manage.py generate_monthly_billing --year 2025 --month 1 --clear-existing
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.billing.models import ConfirmedBilling
from apps.contracts.models import (
    Contract, StudentItem,
    CertificationEnrollment, SeminarEnrollment
)
from apps.students.models import Student, Guardian
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = '月次請求を生成（Contract + Enrollment）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            required=True,
            help='対象年'
        )
        parser.add_argument(
            '--month',
            type=int,
            required=True,
            help='対象月'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='既存データを削除してから作成'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='既存請求にEnrollmentを追加'
        )

    def handle(self, *args, **options):
        year = options['year']
        month = options['month']
        dry_run = options['dry_run']
        clear_existing = options.get('clear_existing', False)
        update_existing = options.get('update_existing', False)
        billing_month = f'{year}-{month:02d}'

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # 既存データの削除
        if clear_existing and not dry_run:
            deleted = ConfirmedBilling.objects.filter(year=year, month=month).delete()[0]
            self.stdout.write(f'既存データを{deleted}件削除しました')

        # 検定申込を取得（billing_month指定）
        cert_enrollments = CertificationEnrollment.objects.filter(
            billing_month=billing_month,
            status__in=['applied', 'confirmed', 'passed', 'failed'],
            deleted_at__isnull=True
        ).select_related('student', 'certification')
        self.stdout.write(f'検定申込（{billing_month}）: {cert_enrollments.count()}件')

        # 講習申込を取得（billing_month指定）
        seminar_enrollments = SeminarEnrollment.objects.filter(
            billing_month=billing_month,
            status__in=['applied', 'confirmed'],
            deleted_at__isnull=True
        ).select_related('student', 'seminar')
        self.stdout.write(f'講習申込（{billing_month}）: {seminar_enrollments.count()}件')

        # 生徒ごとにEnrollmentをまとめる
        student_enrollments = {}  # student_id -> {'certifications': [], 'seminars': []}

        for ce in cert_enrollments:
            if ce.student_id not in student_enrollments:
                student_enrollments[ce.student_id] = {'certifications': [], 'seminars': []}
            student_enrollments[ce.student_id]['certifications'].append({
                'id': str(ce.id),
                'product_name': ce.certification.certification_name,
                'item_type': 'certification',
                'item_type_display': '検定',
                'brand_name': ce.certification.brand.brand_name if ce.certification.brand else '',
                'unit_price': float(ce.final_price),
                'quantity': 1,
                'subtotal': float(ce.final_price),
                'source': 'CertificationEnrollment',
            })

        for se in seminar_enrollments:
            if se.student_id not in student_enrollments:
                student_enrollments[se.student_id] = {'certifications': [], 'seminars': []}
            student_enrollments[se.student_id]['seminars'].append({
                'id': str(se.id),
                'product_name': se.seminar.seminar_name,
                'item_type': 'seminar',
                'item_type_display': '講習',
                'brand_name': se.seminar.brand.brand_name if se.seminar.brand else '',
                'unit_price': float(se.final_price),
                'quantity': 1,
                'subtotal': float(se.final_price),
                'source': 'SeminarEnrollment',
            })

        self.stdout.write(f'Enrollment対象生徒: {len(student_enrollments)}名')

        # 既存請求を更新するモード
        if update_existing:
            self._update_existing_billings(
                year, month, student_enrollments, dry_run
            )
            return

        # 新規請求を作成（既存請求からコピー + Enrollment追加）
        self._create_billings_from_base(
            tenant, year, month, student_enrollments, dry_run
        )

    def _update_existing_billings(self, year, month, student_enrollments, dry_run):
        """既存の請求にEnrollmentを追加"""
        updated_count = 0
        added_items = 0

        billings = ConfirmedBilling.objects.filter(
            year=year, month=month, deleted_at__isnull=True
        )

        for billing in billings:
            if billing.student_id not in student_enrollments:
                continue

            enrollments = student_enrollments[billing.student_id]
            items_to_add = enrollments['certifications'] + enrollments['seminars']

            if not items_to_add:
                continue

            items_snapshot = list(billing.items_snapshot or [])

            # 既存のEnrollment由来・T5由来の検定/講習アイテムを除外（重複防止）
            items_snapshot = [
                i for i in items_snapshot
                if i.get('source') not in ['CertificationEnrollment', 'SeminarEnrollment']
                and i.get('item_type') not in ['certification', 'seminar']
                and not self._is_certification_or_seminar(i.get('product_name', ''))
            ]

            # 新しいアイテムを追加
            items_snapshot.extend(items_to_add)

            # 合計再計算
            subtotal = sum(Decimal(str(i.get('subtotal', 0))) for i in items_snapshot)
            discount_total = sum(
                Decimal(str(d.get('amount', 0)))
                for d in (billing.discounts_snapshot or [])
            )
            total_amount = subtotal - discount_total
            balance = total_amount - billing.paid_amount

            if dry_run:
                self.stdout.write(
                    f'  [ドライラン] 更新: {billing.student.full_name} '
                    f'(+{len(items_to_add)}件, 新合計: {total_amount}円)'
                )
            else:
                billing.items_snapshot = items_snapshot
                billing.subtotal = subtotal
                billing.total_amount = total_amount
                billing.balance = balance
                billing.save(update_fields=[
                    'items_snapshot', 'subtotal', 'total_amount', 'balance'
                ])

            updated_count += 1
            added_items += len(items_to_add)

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
更新した請求: {updated_count}件
追加したアイテム: {added_items}件
'''))

    def _create_billings_from_base(self, tenant, year, month, student_enrollments, dry_run):
        """前月請求をベースに新規請求を作成"""
        # 前月を計算
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1

        # 前月請求を取得
        base_billings = ConfirmedBilling.objects.filter(
            year=prev_year, month=prev_month, deleted_at__isnull=True
        )
        self.stdout.write(f'ベース請求（{prev_year}年{prev_month}月）: {base_billings.count()}件')

        created_count = 0
        skipped_count = 0

        for base in base_billings:
            # 既存チェック
            existing = ConfirmedBilling.objects.filter(
                student=base.student, year=year, month=month
            ).first()

            if existing:
                skipped_count += 1
                continue

            # items_snapshotをコピー（T5由来は除外）
            items_snapshot = [
                i for i in (base.items_snapshot or [])
                if i.get('source') != 'T5'
            ]

            # Enrollmentを追加
            if base.student_id in student_enrollments:
                enrollments = student_enrollments[base.student_id]
                items_snapshot.extend(enrollments['certifications'])
                items_snapshot.extend(enrollments['seminars'])

            # 合計計算
            subtotal = sum(Decimal(str(i.get('subtotal', 0))) for i in items_snapshot)
            discounts_snapshot = list(base.discounts_snapshot or [])
            discount_total = sum(Decimal(str(d.get('amount', 0))) for d in discounts_snapshot)
            total_amount = subtotal - discount_total

            # 請求番号生成
            billing_no = f'CB{year}{month:02d}-{created_count + 1:04d}'

            if dry_run:
                student_name = base.student.full_name if base.student else '不明'
                self.stdout.write(
                    f'  [ドライラン] {billing_no}: {student_name} '
                    f'({len(items_snapshot)}件, 合計: {total_amount}円)'
                )
            else:
                with transaction.atomic():
                    ConfirmedBilling.objects.create(
                        tenant_id=tenant.id,
                        tenant_ref=tenant,
                        billing_no=billing_no,
                        student=base.student,
                        guardian=base.guardian,
                        year=year,
                        month=month,
                        subtotal=subtotal,
                        discount_total=discount_total,
                        tax_amount=Decimal('0'),
                        total_amount=total_amount,
                        paid_amount=Decimal('0'),
                        balance=total_amount,
                        items_snapshot=items_snapshot,
                        discounts_snapshot=discounts_snapshot,
                        status='confirmed',
                        payment_method=base.payment_method,
                        confirmed_at=timezone.now(),
                        notes='',
                    )

            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
作成: {created_count}件
スキップ（既存）: {skipped_count}件
'''))

    def _is_certification_or_seminar(self, product_name):
        """商品名から検定・講習かどうかを判定"""
        if not product_name:
            return False
        cert_keywords = ['検定', '英検', '漢検', '数検', '珠算', '暗算']
        seminar_keywords = ['講習', '夏期', '冬期', '春期']
        for kw in cert_keywords + seminar_keywords:
            if kw in product_name:
                return True
        return False
