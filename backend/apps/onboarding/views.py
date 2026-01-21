"""
Onboarding Views - ユースケース単位のAPI

複数の処理を1トランザクションで実行し、フロントエンドを簡素化する。
"""
from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.exceptions import (
    ValidationException,
    NotFoundError,
    GuardianNotFoundError,
    SchoolNotFoundError,
)


class OnboardingRegisterView(APIView):
    """新規登録（Onboarding）API

    処理内容:
    1. User作成
    2. Guardian作成
    3. Task作成（signalsで自動）
    4. チャンネル作成（任意）
    5. ウェルカムメール送信（任意）

    POST /api/v1/onboarding/register/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.users.models import User
        from apps.students.models import Guardian
        from apps.tenants.models import Tenant
        from apps.schools.models import School, Brand

        data = request.data

        # 必須フィールドの検証
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()

        if not email:
            raise ValidationException('メールアドレスは必須です', field_errors={'email': ['メールアドレスを入力してください']})
        if not password:
            raise ValidationException('パスワードは必須です', field_errors={'password': ['パスワードを入力してください']})
        if len(password) < 8:
            raise ValidationException('パスワードは8文字以上で入力してください', field_errors={'password': ['パスワードは8文字以上で入力してください']})
        if not full_name:
            raise ValidationException('氏名は必須です', field_errors={'full_name': ['氏名を入力してください']})

        # メールアドレスの重複チェック
        if User.objects.filter(email=email).exists():
            raise ValidationException(
                'このメールアドレスは既に登録されています',
                field_errors={'email': ['このメールアドレスは既に登録されています']}
            )

        # 名前の分割
        name_parts = full_name.split(' ', 1)
        last_name = name_parts[0] if len(name_parts) > 0 else ''
        first_name = name_parts[1] if len(name_parts) > 1 else ''

        full_name_kana = data.get('full_name_kana', '').strip()
        kana_parts = full_name_kana.split(' ', 1) if full_name_kana else ['', '']
        last_name_kana = kana_parts[0] if len(kana_parts) > 0 else ''
        first_name_kana = kana_parts[1] if len(kana_parts) > 1 else ''

        # テナント取得
        tenant_code = data.get('tenant_code')
        if tenant_code:
            try:
                tenant = Tenant.objects.get(tenant_code=tenant_code, is_active=True)
            except Tenant.DoesNotExist:
                raise ValidationException('無効なテナントコードです')
        else:
            tenant = Tenant.objects.filter(is_active=True).first()
            if not tenant:
                raise ValidationException('テナントが設定されていません')

        # 最寄り校舎の検証
        nearest_school = None
        nearest_school_id = data.get('nearest_school_id')
        if nearest_school_id:
            try:
                nearest_school = School.objects.get(id=nearest_school_id)
            except School.DoesNotExist:
                raise SchoolNotFoundError()

        # トランザクション開始
        with transaction.atomic():
            # 1. User作成
            user = User(
                email=email,
                last_name=last_name,
                first_name=first_name,
                user_type=User.UserType.GUARDIAN,
                role=User.Role.USER,
                tenant_id=tenant.id,
            )
            user.set_password(password)
            user.save()

            # 2. Guardian作成（→ signalでTaskも自動作成）
            guardian = Guardian(
                tenant_id=tenant.id,
                user=user,
                last_name=last_name,
                first_name=first_name,
                last_name_kana=last_name_kana,
                first_name_kana=first_name_kana,
                email=email,
                phone_mobile=data.get('phone', ''),
                postal_code=data.get('postal_code', ''),
                prefecture=data.get('prefecture', ''),
                city=data.get('city', ''),
                address1=data.get('address1', ''),
                address2=data.get('address2', ''),
                nearest_school=nearest_school,
                interested_brands=data.get('interested_brands', []),
                referral_source=data.get('referral_source', ''),
                expectations=data.get('expectations', ''),
            )
            guardian.save()

            # 3. チャンネル作成（任意）
            create_channel = data.get('create_channel', False)
            channel = None
            if create_channel and nearest_school:
                from apps.communications.models import Channel
                channel = Channel.objects.create(
                    tenant_id=tenant.id,
                    channel_type='direct',
                    name=f'{last_name}{first_name}',
                    guardian=guardian,
                    school=nearest_school,
                )

            # 4. トークン生成
            refresh = RefreshToken.for_user(user)

        # レスポンス
        return Response({
            'success': True,
            'message': 'ユーザー登録が完了しました',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'fullName': user.full_name,
            },
            'guardian': {
                'id': str(guardian.id),
                'guardianNo': guardian.guardian_no or '',
            },
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            'channel': {
                'id': str(channel.id),
            } if channel else None,
        }, status=status.HTTP_201_CREATED)


class AddStudentView(APIView):
    """生徒追加API

    処理内容:
    1. Student作成
    2. Guardian紐付け
    3. Task作成（signalsで自動）
    4. 学年・校舎設定

    POST /api/v1/onboarding/add-student/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.students.models import Student, Guardian, StudentSchool
        from apps.schools.models import School, Brand, Grade

        data = request.data
        user = request.user

        # 保護者を取得
        guardian = None
        guardian_id = data.get('guardian_id')
        if guardian_id:
            try:
                guardian = Guardian.objects.get(id=guardian_id, deleted_at__isnull=True)
            except Guardian.DoesNotExist:
                raise GuardianNotFoundError()
        else:
            # ログインユーザーの保護者プロフィールを使用
            guardian = getattr(user, 'guardian_profile', None)
            if not guardian:
                raise ValidationException('保護者情報が見つかりません')

        # 必須フィールドの検証
        last_name = data.get('last_name', '').strip()
        first_name = data.get('first_name', '').strip()
        if not last_name or not first_name:
            raise ValidationException('生徒の氏名は必須です')

        # 校舎の検証
        school = None
        school_id = data.get('school_id')
        if school_id:
            try:
                school = School.objects.get(id=school_id)
            except School.DoesNotExist:
                raise SchoolNotFoundError()

        # ブランドの検証
        brand = None
        brand_id = data.get('brand_id')
        if brand_id:
            try:
                brand = Brand.objects.get(id=brand_id)
            except Brand.DoesNotExist:
                raise NotFoundError('ブランドが見つかりません')

        # 学年の検証
        grade = None
        grade_id = data.get('grade_id')
        if grade_id:
            try:
                grade = Grade.objects.get(id=grade_id)
            except Grade.DoesNotExist:
                raise NotFoundError('学年が見つかりません')

        tenant_id = guardian.tenant_id

        with transaction.atomic():
            # 1. Student作成（→ signalでTaskも自動作成）
            student = Student(
                tenant_id=tenant_id,
                guardian=guardian,
                last_name=last_name,
                first_name=first_name,
                last_name_kana=data.get('last_name_kana', ''),
                first_name_kana=data.get('first_name_kana', ''),
                birth_date=data.get('birth_date'),
                gender=data.get('gender', ''),
                grade=grade,
                grade_text=data.get('grade_text', ''),
                school_name=data.get('school_name', ''),
                primary_school=school,
                primary_brand=brand,
                status='inquiry',  # 初期ステータス
            )
            student.save()

            # 2. StudentSchool作成（校舎・ブランドとの紐付け）
            if school and brand:
                StudentSchool.objects.create(
                    tenant_id=tenant_id,
                    student=student,
                    school=school,
                    brand=brand,
                    enrollment_status='inquiry',
                )

        return Response({
            'success': True,
            'message': '生徒を登録しました',
            'student': {
                'id': str(student.id),
                'studentNo': student.student_no or '',
                'fullName': f'{student.last_name}{student.first_name}',
                'grade': student.grade_text,
            },
        }, status=status.HTTP_201_CREATED)


class PurchaseCompleteView(APIView):
    """チケット購入完了API

    処理内容:
    1. 料金計算の確定
    2. StudentItem（契約）作成
    3. Invoice（請求）作成
    4. Task作成（signalsで自動）
    5. 確認メール送信（任意）

    POST /api/v1/onboarding/purchase/complete/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.students.models import Student
        from apps.contracts.models import StudentItem
        from apps.billing.models import Invoice
        from apps.schools.models import ClassSchedule
        from apps.pricing.models import Course
        from decimal import Decimal

        data = request.data
        user = request.user

        # 必須パラメータの検証
        student_id = data.get('student_id')
        course_id = data.get('course_id')
        preview_data = data.get('preview_data', {})

        if not student_id:
            raise ValidationException('student_id は必須です')
        if not course_id:
            raise ValidationException('course_id は必須です')

        # 生徒の取得と権限チェック
        try:
            student = Student.objects.select_related('guardian').get(
                id=student_id, deleted_at__isnull=True
            )
        except Student.DoesNotExist:
            raise NotFoundError('生徒が見つかりません')

        # 保護者の権限チェック（自分の子供か確認）
        guardian = getattr(user, 'guardian_profile', None)
        if guardian and student.guardian_id != guardian.id:
            # 管理者でなければエラー
            if not user.is_staff and not user.is_superuser:
                raise ValidationException('この生徒の契約を作成する権限がありません')

        # コースの取得
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            raise NotFoundError('コースが見つかりません')

        tenant_id = student.tenant_id

        # クラススケジュールの取得（任意）
        class_schedule = None
        schedule_id = data.get('schedule_id')
        if schedule_id:
            try:
                class_schedule = ClassSchedule.objects.get(id=schedule_id)
            except ClassSchedule.DoesNotExist:
                pass

        # 料金情報
        grand_total = Decimal(str(preview_data.get('grand_total', 0)))
        items = preview_data.get('items', [])

        with transaction.atomic():
            # 1. StudentItem（契約）作成（→ signalでTaskも自動作成）
            student_item = StudentItem(
                tenant_id=tenant_id,
                student=student,
                course=course,
                brand=course.brand,
                school=data.get('school_id') and student.primary_school,
                class_schedule=class_schedule,
                status='active',
                start_date=data.get('start_date'),
                day_of_week=class_schedule.day_of_week if class_schedule else data.get('day_of_week'),
                start_time=class_schedule.start_time if class_schedule else None,
            )
            student_item.save()

            # 2. Invoice（請求）作成
            invoice = None
            if grand_total > 0:
                from datetime import date
                today = date.today()
                invoice = Invoice.objects.create(
                    tenant_id=tenant_id,
                    guardian=student.guardian,
                    student=student,
                    billing_year=today.year,
                    billing_month=today.month,
                    total_amount=grand_total,
                    balance_due=grand_total,
                    status=Invoice.Status.ISSUED,
                    notes=f'オンライン申込: {course.course_name}',
                )

                # InvoiceItem作成
                from apps.billing.models import InvoiceItem
                for item in items:
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product_name=item.get('productName', ''),
                        quantity=item.get('quantity', 1),
                        unit_price=Decimal(str(item.get('unitPrice', 0))),
                        subtotal=Decimal(str(item.get('subtotal', 0))),
                        tax_rate=Decimal(str(item.get('taxRate', 0.1))),
                        tax_amount=Decimal(str(item.get('taxAmount', 0))),
                    )

            # 3. 生徒ステータスを更新
            if student.status == 'inquiry':
                student.status = 'enrolled'
                student.save(update_fields=['status', 'updated_at'])

        return Response({
            'success': True,
            'message': '契約が完了しました',
            'studentItem': {
                'id': str(student_item.id),
                'courseName': course.course_name,
            },
            'invoice': {
                'id': str(invoice.id),
                'invoiceNo': invoice.invoice_no,
                'totalAmount': int(invoice.total_amount),
            } if invoice else None,
        }, status=status.HTTP_201_CREATED)
