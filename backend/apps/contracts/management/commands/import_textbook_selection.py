"""
教材費選択の一括インポートコマンド

Excelファイルから教材費の支払い方法（半年払い/月払い）を読み込み、
契約に教材費商品を紐付ける。
"""
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import Contract, Product, Course
from apps.students.models import Student


class Command(BaseCommand):
    help = '教材費選択をExcelからインポートして契約に紐付ける'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_file',
            type=str,
            help='インポートするExcelファイルのパス',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には変更せず、処理対象の確認のみ行う',
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            help='テナントID（指定しない場合は最初のテナントを使用）',
        )

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        dry_run = options['dry_run']
        tenant_id = options.get('tenant_id')

        self.stdout.write('='*70)
        self.stdout.write('教材費選択インポート')
        self.stdout.write('='*70)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN モード: 実際の変更は行いません'))

        # テナントIDの取得
        if not tenant_id:
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.filter(is_active=True).first()
            if tenant:
                tenant_id = str(tenant.id)
            else:
                self.stdout.write(self.style.ERROR('アクティブなテナントが見つかりません'))
                return

        self.stdout.write(f'テナントID: {tenant_id}')
        self.stdout.write(f'Excelファイル: {excel_file}')
        self.stdout.write('-'*70)

        # Excelを読み込み
        df = pd.read_excel(excel_file)

        # 統計
        stats = {
            'total': 0,
            'half_yearly': 0,
            'monthly': 0,
            'no_material': 0,
            'student_found': 0,
            'student_not_found': 0,
            'contract_found': 0,
            'contract_not_found': 0,
            'textbook_found': 0,
            'textbook_not_found': 0,
            'already_set': 0,
            'updated': 0,
            'errors': 0,
        }

        results = {
            'updated': [],
            'not_found': [],
            'errors': [],
        }

        for idx, row in df.iterrows():
            stats['total'] += 1

            student_old_id = str(int(row['生徒ID']))
            contract_no = row['契約ID']  # contract_no（例: 24SOR_1000038）
            payment_type = row['請求月']

            # 支払い方法の分類
            if payment_type == '半年払い':
                stats['half_yearly'] += 1
                textbook_keyword = '半年払い'
            elif payment_type == '月払い':
                stats['monthly'] += 1
                textbook_keyword = '月払い'
            elif payment_type == '教材代なし':
                stats['no_material'] += 1
                continue  # 教材代なしはスキップ
            else:
                stats['errors'] += 1
                results['errors'].append({
                    'student_old_id': student_old_id,
                    'contract_no': contract_no,
                    'reason': f'不明な請求月: {payment_type}'
                })
                continue

            # 生徒を検索
            student = Student.objects.filter(
                tenant_id=tenant_id,
                old_id=student_old_id,
                deleted_at__isnull=True
            ).first()

            if not student:
                stats['student_not_found'] += 1
                results['not_found'].append({
                    'type': 'student',
                    'student_old_id': student_old_id,
                    'contract_no': contract_no,
                })
                continue

            stats['student_found'] += 1

            # 契約を検索（contract_no + student で一意に特定）
            contract = Contract.objects.filter(
                tenant_id=tenant_id,
                student=student,
                contract_no=contract_no,
                deleted_at__isnull=True
            ).first()

            # contract_noで見つからない場合、old_idでも検索
            if not contract:
                contract = Contract.objects.filter(
                    tenant_id=tenant_id,
                    student=student,
                    old_id=contract_no,
                    deleted_at__isnull=True
                ).first()

            if not contract:
                stats['contract_not_found'] += 1
                results['not_found'].append({
                    'type': 'contract',
                    'student_old_id': student_old_id,
                    'student_name': student.full_name,
                    'contract_no': contract_no,
                })
                continue

            stats['contract_found'] += 1

            # 教材費商品を検索（契約番号 + サフィックスで）
            # 半年払い: _4 (通常) または _2 (マンツー)
            # 月払い: _5 (通常) または _3 (マンツー)
            # 注: 商品が別テナントに存在する場合があるため、tenant_idフィルタは使用しない
            textbook = None

            # まず契約番号に基づくproduct_codeで検索
            if textbook_keyword == '半年払い':
                # _4 または _2 サフィックスを試す
                for suffix in ['_4', '_2']:
                    textbook = Product.objects.filter(
                        product_code=f'{contract_no}{suffix}',
                        item_type='textbook',
                        is_active=True,
                        deleted_at__isnull=True
                    ).first()
                    if textbook:
                        break
            else:  # 月払い
                # _5 または _3 サフィックスを試す
                for suffix in ['_5', '_3']:
                    textbook = Product.objects.filter(
                        product_code=f'{contract_no}{suffix}',
                        item_type='textbook',
                        is_active=True,
                        deleted_at__isnull=True
                    ).first()
                    if textbook:
                        break

            # 見つからない場合、product_nameで検索
            if not textbook:
                textbook = Product.objects.filter(
                    product_code__startswith=contract_no,
                    item_type='textbook',
                    product_name__icontains=textbook_keyword,
                    is_active=True,
                    deleted_at__isnull=True
                ).first()

            # それでも見つからない場合、ブランドから検索
            if not textbook and contract.brand:
                textbook = Product.objects.filter(
                    brand=contract.brand,
                    item_type='textbook',
                    product_name__icontains=textbook_keyword,
                    is_active=True,
                    deleted_at__isnull=True
                ).first()

            if not textbook:
                stats['textbook_not_found'] += 1
                results['not_found'].append({
                    'type': 'textbook',
                    'student_old_id': student_old_id,
                    'student_name': student.full_name,
                    'contract_no': contract_no,
                    'keyword': textbook_keyword,
                })
                continue

            stats['textbook_found'] += 1

            # すでに設定されているか確認
            if contract.selected_textbooks.filter(id=textbook.id).exists():
                stats['already_set'] += 1
                continue

            # 教材費を契約に紐付け
            if not dry_run:
                with transaction.atomic():
                    contract.selected_textbooks.add(textbook)
                    stats['updated'] += 1

            results['updated'].append({
                'student_old_id': student_old_id,
                'student_name': student.full_name,
                'contract_no': contract_no,
                'textbook': textbook.product_name,
                'payment_type': payment_type,
            })

        # 結果サマリー
        self.stdout.write('')
        self.stdout.write('='*70)
        self.stdout.write('処理結果サマリー')
        self.stdout.write('='*70)
        self.stdout.write(f"総レコード数: {stats['total']}")
        self.stdout.write(f"  半年払い: {stats['half_yearly']}")
        self.stdout.write(f"  月払い: {stats['monthly']}")
        self.stdout.write(f"  教材代なし: {stats['no_material']}")
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f"生徒発見: {stats['student_found']}"))
        self.stdout.write(self.style.WARNING(f"生徒未発見: {stats['student_not_found']}"))
        self.stdout.write(self.style.SUCCESS(f"契約発見: {stats['contract_found']}"))
        self.stdout.write(self.style.WARNING(f"契約未発見: {stats['contract_not_found']}"))
        self.stdout.write(self.style.SUCCESS(f"教材費発見: {stats['textbook_found']}"))
        self.stdout.write(self.style.WARNING(f"教材費未発見: {stats['textbook_not_found']}"))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f"設定済み（スキップ）: {stats['already_set']}"))
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"更新完了: {stats['updated']}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"更新対象: {len(results['updated'])}"))

        # 更新サンプル
        if results['updated']:
            self.stdout.write('')
            self.stdout.write('-'*70)
            self.stdout.write('更新サンプル（最初の10件）:')
            for r in results['updated'][:10]:
                self.stdout.write(
                    f"  {r['student_old_id']} {r['student_name']}: "
                    f"{r['contract_no']} → {r['payment_type']}"
                )

        # 未発見リスト
        if results['not_found']:
            self.stdout.write('')
            self.stdout.write('-'*70)
            self.stdout.write(self.style.WARNING(f'未発見リスト（最初の20件）:'))
            for r in results['not_found'][:20]:
                self.stdout.write(
                    f"  [{r['type']}] {r.get('student_old_id', '-')} "
                    f"{r.get('student_name', '')} - {r.get('contract_no', '')}"
                )

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUNのため、実際の変更は行われていません'))
