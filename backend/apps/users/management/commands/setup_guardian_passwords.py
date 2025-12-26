"""
既存保護者の初期パスワード設定コマンド

電話番号をログインIDとして、初期パスワードを「1+電話番号下4桁」で設定する
ログイン後にパスワード変更を強制する
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.students.models import Guardian
from apps.users.models import User


class Command(BaseCommand):
    help = '既存保護者に対してユーザーアカウントを作成し、初期パスワードを設定する'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には変更せず、処理対象の確認のみ行う',
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            help='特定のテナントIDのみ処理する',
        )
        parser.add_argument(
            '--guardian-id',
            type=str,
            help='特定の保護者IDのみ処理する（テスト用）',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        tenant_id = options.get('tenant_id')
        guardian_id = options.get('guardian_id')

        self.stdout.write('='*60)
        self.stdout.write('保護者初期パスワード設定')
        self.stdout.write('='*60)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN モード: 実際の変更は行いません'))

        # 保護者を取得
        guardians = Guardian.objects.filter(deleted_at__isnull=True)

        if tenant_id:
            guardians = guardians.filter(tenant_id=tenant_id)
            self.stdout.write(f'テナントID: {tenant_id}')

        if guardian_id:
            guardians = guardians.filter(id=guardian_id)
            self.stdout.write(f'保護者ID: {guardian_id}')

        total_count = guardians.count()
        self.stdout.write(f'対象保護者数: {total_count}')
        self.stdout.write('-'*60)

        created_count = 0
        updated_count = 0
        skipped_no_phone = 0
        skipped_already_has_user = 0
        error_count = 0
        results = []

        for guardian in guardians:
            try:
                result = self.process_guardian(guardian, dry_run)
                results.append(result)

                if result['status'] == 'created':
                    created_count += 1
                elif result['status'] == 'updated':
                    updated_count += 1
                elif result['status'] == 'skipped_no_phone':
                    skipped_no_phone += 1
                elif result['status'] == 'skipped_has_user':
                    skipped_already_has_user += 1
                elif result['status'] == 'error':
                    error_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(
                    f'エラー: {guardian.full_name} - {str(e)}'
                ))

        # 結果サマリー
        self.stdout.write('')
        self.stdout.write('='*60)
        self.stdout.write('処理結果サマリー')
        self.stdout.write('='*60)
        self.stdout.write(f'合計処理: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'  新規作成: {created_count}'))
        self.stdout.write(f'  更新: {updated_count}')
        self.stdout.write(self.style.WARNING(f'  スキップ（電話番号なし）: {skipped_no_phone}'))
        self.stdout.write(f'  スキップ（既にユーザーあり）: {skipped_already_has_user}')
        self.stdout.write(self.style.ERROR(f'  エラー: {error_count}'))

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUNのため、実際の変更は行われていません'))

    def process_guardian(self, guardian, dry_run=False):
        """個別の保護者を処理"""
        # 電話番号を取得（phone_mobileを優先、なければphone）
        phone = guardian.phone_mobile or guardian.phone

        if not phone:
            return {
                'guardian': guardian,
                'status': 'skipped_no_phone',
                'message': '電話番号がありません'
            }

        # 電話番号を正規化（ハイフンや空白を除去）
        normalized_phone = ''.join(c for c in phone if c.isdigit())

        if len(normalized_phone) < 4:
            return {
                'guardian': guardian,
                'status': 'skipped_no_phone',
                'message': f'電話番号が短すぎます: {phone}'
            }

        # 既にユーザーアカウントが紐付いているか確認
        if guardian.user:
            # 既存ユーザーのパスワードを更新
            initial_password = '1' + normalized_phone[-4:]

            if not dry_run:
                guardian.user.set_password(initial_password)
                guardian.user.phone = normalized_phone
                guardian.user.must_change_password = True
                guardian.user.save()

            self.stdout.write(
                f'更新: {guardian.full_name} ({normalized_phone}) -> パスワード: {initial_password}'
            )
            return {
                'guardian': guardian,
                'status': 'updated',
                'phone': normalized_phone,
                'password': initial_password
            }

        # 初期パスワードを生成（1+電話番号下4桁）
        initial_password = '1' + normalized_phone[-4:]

        # メールアドレスを生成（電話番号ベース）
        # Userモデルはemail必須なので、ダミーのメールを生成
        email = guardian.email if guardian.email else f'{normalized_phone}@phone.local'

        # 既存のメールアドレスと重複チェック
        if User.objects.filter(email=email).exists():
            # 重複する場合はUUIDを追加
            import uuid
            email = f'{normalized_phone}_{str(uuid.uuid4())[:8]}@phone.local'

        if not dry_run:
            with transaction.atomic():
                # ユーザーを作成
                user = User.objects.create_user(
                    email=email,
                    password=initial_password,
                    last_name=guardian.last_name,
                    first_name=guardian.first_name,
                    last_name_kana=guardian.last_name_kana,
                    first_name_kana=guardian.first_name_kana,
                    phone=normalized_phone,
                    user_type=User.UserType.GUARDIAN,
                    role=User.Role.USER,
                    tenant_id=guardian.tenant_id,
                    must_change_password=True,
                    is_active=True,
                )

                # 保護者とユーザーを紐付け
                guardian.user = user
                guardian.save(update_fields=['user', 'updated_at'])

        self.stdout.write(self.style.SUCCESS(
            f'作成: {guardian.full_name} ({normalized_phone}) -> パスワード: {initial_password}'
        ))

        return {
            'guardian': guardian,
            'status': 'created',
            'phone': normalized_phone,
            'password': initial_password,
            'email': email
        }
