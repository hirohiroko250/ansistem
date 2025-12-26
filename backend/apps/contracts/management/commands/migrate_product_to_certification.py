"""
Productの検定データをCertificationマスタに移行するコマンド

Usage:
    # ドライラン（確認のみ）
    python manage.py migrate_product_to_certification --dry-run

    # 実行
    python manage.py migrate_product_to_certification

    # 移行後にProductを無効化
    python manage.py migrate_product_to_certification --deactivate-products
"""
import re
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from apps.contracts.models import Product, Certification
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'Product内の検定データ（検定を含む商品名）をCertificationマスタに移行'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--deactivate-products',
            action='store_true',
            help='移行後に元のProductを無効化（is_active=False）'
        )
        parser.add_argument(
            '--show-duplicates',
            action='store_true',
            help='重複している検定名を表示'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        deactivate_products = options['deactivate_products']
        show_duplicates = options['show_duplicates']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ===\n'))

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # 検定関連のProductを取得（商品名に「検定」を含むもの）
        products = Product.objects.filter(
            product_name__icontains='検定'
        ).select_related('brand', 'grade')

        self.stdout.write(f'対象Product総数: {products.count()}件\n')

        if products.count() == 0:
            self.stdout.write(self.style.SUCCESS('移行対象のProductがありません'))
            return

        # ユニークな検定を抽出（商品名 + 金額でグループ化）
        unique_certs = defaultdict(list)
        for product in products:
            # 検定名を正規化
            cert_name = self._normalize_cert_name(product.product_name)
            key = (cert_name, float(product.base_price or 0))
            unique_certs[key].append(product)

        self.stdout.write(f'ユニークな検定パターン: {len(unique_certs)}件\n')

        if show_duplicates:
            self.stdout.write('\n=== 重複パターン（5件以上） ===')
            for (name, price), prods in sorted(unique_certs.items(), key=lambda x: -len(x[1])):
                if len(prods) >= 5:
                    self.stdout.write(f'  [{len(prods)}件] {name} (¥{price:,.0f})')

        created_count = 0
        skipped_count = 0
        product_count = 0

        for (cert_name, price), product_list in unique_certs.items():
            sample_product = product_list[0]

            # 検定種別を判定
            cert_type = self._detect_certification_type(cert_name)

            # 級・レベルを抽出
            level = self._extract_level(cert_name)

            # 年度を抽出
            year = self._extract_year(cert_name)

            # 検定コードを生成
            cert_code = self._generate_cert_code(cert_type, year, level, cert_name, price)

            self.stdout.write(f'\n検定: {cert_name[:60]}...' if len(cert_name) > 60 else f'\n検定: {cert_name}')
            self.stdout.write(f'  種別: {cert_type}, 級: {level or "なし"}, 年度: {year}, 金額: ¥{price:,.0f}')
            self.stdout.write(f'  対象Product数: {len(product_list)}件')
            self.stdout.write(f'  → 検定コード: {cert_code}')

            # 既存チェック
            existing = Certification.objects.filter(
                tenant_id=sample_product.tenant_id,
                certification_code=cert_code
            ).first()

            if existing:
                self.stdout.write(self.style.WARNING(f'  → スキップ（既存あり）'))
                skipped_count += 1
                continue

            if dry_run:
                self.stdout.write(self.style.SUCCESS('  → [ドライラン] 作成予定'))
                created_count += 1
            else:
                with transaction.atomic():
                    cert = Certification.objects.create(
                        tenant_id=sample_product.tenant_id,
                        tenant_ref=sample_product.tenant_ref,
                        certification_code=cert_code,
                        certification_name=cert_name[:200],
                        certification_type=cert_type,
                        level=level,
                        brand=sample_product.brand,
                        year=year,
                        exam_fee=Decimal(str(price)),
                        description=f'Productから移行: {len(product_list)}件',
                        sort_order=0,
                        is_active=True,
                    )
                    self.stdout.write(self.style.SUCCESS(f'  → 作成完了'))
                    created_count += 1

                    # Productを無効化
                    if deactivate_products:
                        for prod in product_list:
                            prod.is_active = False
                            prod.description = f'[移行済] → Certification: {cert_code}\n{prod.description or ""}'
                            prod.save(update_fields=['is_active', 'description', 'updated_at'])
                            product_count += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
Certification作成: {created_count}件
スキップ（既存あり）: {skipped_count}件
Product無効化: {product_count}件
'''))

    def _normalize_cert_name(self, name: str) -> str:
        """商品名から検定名を正規化"""
        # 不要なプレフィックスを削除
        name = re.sub(r'^[A-Z0-9_]+\s*', '', name)
        # 前後の空白を削除
        return name.strip()

    def _detect_certification_type(self, name: str) -> str:
        """商品名から検定種別を判定"""
        name_lower = name.lower()

        if '英検' in name or 'eiken' in name_lower:
            return 'eiken'
        elif '漢検' in name or '漢字検定' in name:
            return 'kanken'
        elif '数検' in name or '数学検定' in name or '算数検定' in name:
            return 'suken'
        else:
            return 'other'

    def _extract_level(self, name: str) -> str:
        """商品名から級・レベルを抽出"""
        # 準X級パターン
        prep_match = re.search(r'準(\d+)級', name)
        if prep_match:
            return f'準{prep_match.group(1)}級'

        # X級パターン（複数ある場合は最初のものを取得）
        level_match = re.search(r'【(\d+)】級|(\d+)級', name)
        if level_match:
            level_num = level_match.group(1) or level_match.group(2)
            return f'{level_num}級'

        # 段位パターン
        dan_match = re.search(r'(\d+)段', name)
        if dan_match:
            return f'{dan_match.group(1)}段'

        return ''

    def _extract_year(self, name: str) -> int:
        """商品名から年度を抽出"""
        # 2025年 形式
        year_match = re.search(r'(20\d{2})年', name)
        if year_match:
            return int(year_match.group(1))

        # 202507 形式
        ym_match = re.search(r'(20\d{2})\d{2}', name)
        if ym_match:
            return int(ym_match.group(1))

        # R6, R7 形式（令和）
        reiwa_match = re.search(r'R(\d+)', name)
        if reiwa_match:
            reiwa_year = int(reiwa_match.group(1))
            return 2018 + reiwa_year

        # 24XXX 形式（年度の下2桁）
        code_year_match = re.search(r'^(\d{2})[A-Z]', name)
        if code_year_match:
            year_2digit = int(code_year_match.group(1))
            if 20 <= year_2digit <= 30:
                return 2000 + year_2digit

        # デフォルトは現在年度
        return datetime.now().year

    def _generate_cert_code(self, cert_type: str, year: int, level: str, name: str, price: float = 0) -> str:
        """検定コードを生成"""
        # 名前+金額からユニークな識別子を作成
        unique_str = f'{name}_{price}'
        name_hash = abs(hash(unique_str)) % 100000

        level_code = ''
        if level:
            level_code = '_' + level.replace('準', 'J').replace('級', 'K').replace('段', 'D')

        return f'{cert_type.upper()}_{year}{level_code}_{name_hash:05d}'
