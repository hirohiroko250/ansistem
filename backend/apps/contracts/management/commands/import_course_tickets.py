"""
T8 Excelからコースチケットとパックチケットをインポートするコマンド
"""
import csv
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import Course, Pack, Ticket, CourseTicket, PackTicket


class Command(BaseCommand):
    help = 'T8 CSVからコースチケット・パックチケットをインポート'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='/app/data/T8_契約とチケット情報.csv',
            help='T8 CSVファイルパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存しない'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        dry_run = options['dry_run']

        self.stdout.write(f'CSV: {csv_path}')
        self.stdout.write(f'Dry Run: {dry_run}')

        # 既存のtenant_idを取得
        existing_course = Course.objects.first()
        if existing_course:
            tenant_id = str(existing_course.tenant_id)
            self.stdout.write(f'tenant_id: {tenant_id}')
        else:
            self.stdout.write(self.style.ERROR('既存のコースがありません'))
            return

        # コース・パックをマッピング（契約IDベース）
        courses_by_contract_id = {}
        for course in Course.objects.filter(tenant_id=tenant_id):
            # course_code (CAEC1000007) -> contract_id (24AEC_1000007)
            # C -> 24, AEC1000007 -> AEC_1000007
            code = course.course_code
            if code.startswith('C'):
                contract_id = '24' + code[1:4] + '_' + code[4:]
                courses_by_contract_id[contract_id] = course
        self.stdout.write(f'コース数: {len(courses_by_contract_id)}')

        packs_by_contract_id = {}
        for pack in Pack.objects.filter(tenant_id=tenant_id):
            code = pack.pack_code
            if code.startswith('PK'):
                contract_id = '24' + code[2:5] + '_' + code[5:]
                packs_by_contract_id[contract_id] = pack
        self.stdout.write(f'パック数: {len(packs_by_contract_id)}')

        # チケットをコードでマッピング（Ch -> T変換済み）
        tickets_by_code = {}
        for ticket in Ticket.objects.filter(tenant_id=tenant_id):
            tickets_by_code[ticket.ticket_code] = ticket
            # 元のChコードでもマッピング
            original_code = ticket.ticket_code.replace('T', 'Ch')
            tickets_by_code[original_code] = ticket
        self.stdout.write(f'チケット数: {len(tickets_by_code)}')

        stats = {
            'course_tickets': 0,
            'pack_tickets': 0,
            'skipped': 0,
        }

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                with transaction.atomic():
                    for row in reader:
                        contract_id = row.get('契約ID', '').strip()
                        pack_type = row.get('基本/パック', '1')  # 1=コース, 3=パック

                        if not contract_id:
                            continue

                        # チケットIDカラムを探索（最大11個）
                        for i in range(1, 12):
                            ticket_id = row.get(f'チケットID_{i}', '').strip()
                            quantity_str = row.get(f'チケットID_個数_{i}', '1')

                            if not ticket_id or ticket_id == 'NaN':
                                continue

                            ticket = tickets_by_code.get(ticket_id)
                            if not ticket:
                                stats['skipped'] += 1
                                continue

                            try:
                                quantity = int(float(quantity_str)) if quantity_str else 1
                            except:
                                quantity = 1

                            # コースの場合
                            if pack_type == '1' and contract_id in courses_by_contract_id:
                                course = courses_by_contract_id[contract_id]

                                if not dry_run:
                                    ct, created = CourseTicket.objects.update_or_create(
                                        tenant_id=tenant_id,
                                        course=course,
                                        ticket=ticket,
                                        defaults={
                                            'quantity': quantity,
                                            'per_week': 1,
                                            'sort_order': i,
                                            'is_active': True,
                                        }
                                    )
                                    if created:
                                        stats['course_tickets'] += 1
                                else:
                                    if stats['course_tickets'] < 20:
                                        self.stdout.write(
                                            f'  [DRY] CourseTicket: {course.course_name[:20]} <- {ticket.ticket_name[:30]} x{quantity}'
                                        )
                                    stats['course_tickets'] += 1

                            # パックの場合
                            elif pack_type == '3' and contract_id in packs_by_contract_id:
                                pack = packs_by_contract_id[contract_id]

                                if not dry_run:
                                    pt, created = PackTicket.objects.update_or_create(
                                        tenant_id=tenant_id,
                                        pack=pack,
                                        ticket=ticket,
                                        defaults={
                                            'quantity': quantity,
                                            'per_week': 1,
                                            'sort_order': i,
                                            'is_active': True,
                                        }
                                    )
                                    if created:
                                        stats['pack_tickets'] += 1
                                else:
                                    if stats['pack_tickets'] < 20:
                                        self.stdout.write(
                                            f'  [DRY] PackTicket: {pack.pack_name[:20]} <- {ticket.ticket_name[:30]} x{quantity}'
                                        )
                                    stats['pack_tickets'] += 1

                    if dry_run:
                        raise Exception('Dry run - rolling back')

        except FileNotFoundError:
            self.stdout.write(self.style.WARNING(f'CSVが見つかりません: {csv_path}'))
            return

        self.stdout.write(self.style.SUCCESS(
            f"\n=== 完了 ===\n"
            f"CourseTicket: {stats['course_tickets']}件\n"
            f"PackTicket: {stats['pack_tickets']}件\n"
            f"Skipped: {stats['skipped']}件\n"
        ))
