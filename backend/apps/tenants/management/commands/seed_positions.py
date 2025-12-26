"""
Seed Positions for Permission Settings
Based on the OZA system permission matrix
"""
from django.core.management.base import BaseCommand
from apps.tenants.models import Position, Tenant


class Command(BaseCommand):
    help = 'Seed positions for permission settings'

    # 役職マスタ定義（HTMLから抽出）
    POSITIONS = [
        {
            'code': '1',
            'name': 'システム',
            'rank': 100,
            'school_restriction': False,
            'brand_restriction': False,
            'bulk_email_restriction': False,
            'email_approval_required': False,
            'is_accounting': True,
        },
        {
            'code': '2',
            'name': '学長',
            'rank': 90,
            'school_restriction': False,
            'brand_restriction': False,
            'bulk_email_restriction': False,
            'email_approval_required': False,
            'is_accounting': False,
        },
        {
            'code': '3',
            'name': '幹部',
            'rank': 80,
            'school_restriction': False,
            'brand_restriction': False,
            'bulk_email_restriction': False,
            'email_approval_required': False,
            'is_accounting': False,
        },
        {
            'code': '4',
            'name': '経理',
            'rank': 70,
            'school_restriction': False,
            'brand_restriction': False,
            'bulk_email_restriction': False,
            'email_approval_required': False,
            'is_accounting': True,
        },
        {
            'code': '5',
            'name': '課長・部門長',
            'rank': 60,
            'school_restriction': False,
            'brand_restriction': False,
            'bulk_email_restriction': False,
            'email_approval_required': False,
            'is_accounting': False,
        },
        {
            'code': '6',
            'name': '社員',
            'rank': 50,
            'school_restriction': True,
            'brand_restriction': False,
            'bulk_email_restriction': False,
            'email_approval_required': False,
            'is_accounting': False,
        },
        {
            'code': '7',
            'name': '本部事務',
            'rank': 40,
            'school_restriction': False,
            'brand_restriction': False,
            'bulk_email_restriction': False,
            'email_approval_required': False,
            'is_accounting': False,
        },
        {
            'code': '8',
            'name': '電話受付',
            'rank': 30,
            'school_restriction': False,
            'brand_restriction': False,
            'bulk_email_restriction': False,
            'email_approval_required': False,
            'is_accounting': False,
        },
        {
            'code': '9',
            'name': '現場講師',
            'rank': 20,
            'school_restriction': True,
            'brand_restriction': True,
            'bulk_email_restriction': False,
            'email_approval_required': True,
            'is_accounting': False,
        },
        {
            'code': '10',
            'name': 'オーナー',
            'rank': 10,
            'school_restriction': True,
            'brand_restriction': True,
            'bulk_email_restriction': False,
            'email_approval_required': True,
            'is_accounting': False,
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Tenant code to seed positions for (default: all tenants)',
        )

    def handle(self, *args, **options):
        tenant_code = options.get('tenant')

        if tenant_code:
            tenants = Tenant.objects.filter(tenant_code=tenant_code)
            if not tenants.exists():
                self.stderr.write(self.style.ERROR(f'Tenant not found: {tenant_code}'))
                return
        else:
            tenants = Tenant.objects.filter(is_active=True)

        for tenant in tenants:
            self.stdout.write(f'Seeding positions for tenant: {tenant.tenant_name}')

            created_count = 0
            updated_count = 0

            for pos_data in self.POSITIONS:
                position, created = Position.objects.update_or_create(
                    tenant_ref=tenant,
                    tenant_id=tenant.id,
                    position_code=pos_data['code'],
                    defaults={
                        'position_name': pos_data['name'],
                        'rank': pos_data['rank'],
                        'school_restriction': pos_data['school_restriction'],
                        'brand_restriction': pos_data['brand_restriction'],
                        'bulk_email_restriction': pos_data['bulk_email_restriction'],
                        'email_approval_required': pos_data['email_approval_required'],
                        'is_accounting': pos_data['is_accounting'],
                        'is_active': True,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            self.stdout.write(self.style.SUCCESS(
                f'  Created: {created_count}, Updated: {updated_count}'
            ))

        self.stdout.write(self.style.SUCCESS('Positions seeded successfully!'))
