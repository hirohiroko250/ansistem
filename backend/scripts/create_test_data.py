#!/usr/bin/env python
"""
テストデータ作成スクリプト
OZAシステムのDocker開発環境用テストデータを生成します。

使用方法:
    docker compose -f docker-compose.dev.yml exec backend python scripts/create_test_data.py
"""
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

# パスを追加
sys.path.insert(0, '/app')

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant
from apps.schools.models import Brand, School, Grade, Subject, Classroom
from apps.students.models import Student, Guardian, StudentGuardian
from apps.contracts.models import Product, Contract, ContractDetail
from apps.hr.models import Staff, Attendance
from apps.lessons.models import LessonSchedule

User = get_user_model()


def create_tenant():
    """テストテナントを作成"""
    print("テナントを作成中...")
    tenant, created = Tenant.objects.get_or_create(
        tenant_code='TEST001',
        defaults={
            'tenant_name': 'テスト塾運営会社',
            'contact_email': 'admin@test-juku.com',
            'contact_phone': '03-1234-5678',
            'plan_type': Tenant.PlanType.STANDARD,
            'max_schools': 10,
            'max_users': 100,
            'is_active': True,
            'settings': {
                'lesson_duration_minutes': 50,
                'break_duration_minutes': 10,
            },
            'features': {
                'chat_enabled': True,
                'notification_enabled': True,
            }
        }
    )
    if created:
        print(f"  ✅ テナント作成: {tenant.tenant_name}")
    else:
        print(f"  ⏭️ テナント既存: {tenant.tenant_name}")
    return tenant


def create_users(tenant):
    """テストユーザーを作成"""
    print("\nユーザーを作成中...")
    users = {}

    # 管理者
    admin, created = User.objects.get_or_create(
        email='admin@test-juku.com',
        defaults={
            'tenant_id': tenant.id,
            'last_name': '管理',
            'first_name': '太郎',
            'last_name_kana': 'カンリ',
            'first_name_kana': 'タロウ',
            'user_type': User.UserType.ADMIN,
            'role': User.Role.ADMIN,
            'is_staff': True,
            'is_superuser': False,
            'is_active': True,
        }
    )
    if created:
        admin.set_password('admin123')
        admin.save()
        print(f"  ✅ 管理者作成: {admin.email}")
    else:
        print(f"  ⏭️ 管理者既存: {admin.email}")
    users['admin'] = admin

    # 講師1
    instructor1, created = User.objects.get_or_create(
        email='instructor1@test-juku.com',
        defaults={
            'tenant_id': tenant.id,
            'last_name': '山田',
            'first_name': '花子',
            'last_name_kana': 'ヤマダ',
            'first_name_kana': 'ハナコ',
            'user_type': User.UserType.TEACHER,
            'role': User.Role.TEACHER,
            'is_staff': False,
            'is_active': True,
        }
    )
    if created:
        instructor1.set_password('instructor123')
        instructor1.save()
        print(f"  ✅ 講師作成: {instructor1.email}")
    else:
        print(f"  ⏭️ 講師既存: {instructor1.email}")
    users['instructor1'] = instructor1

    # 講師2
    instructor2, created = User.objects.get_or_create(
        email='instructor2@test-juku.com',
        defaults={
            'tenant_id': tenant.id,
            'last_name': '佐藤',
            'first_name': '次郎',
            'last_name_kana': 'サトウ',
            'first_name_kana': 'ジロウ',
            'user_type': User.UserType.TEACHER,
            'role': User.Role.TEACHER,
            'is_staff': False,
            'is_active': True,
        }
    )
    if created:
        instructor2.set_password('instructor123')
        instructor2.save()
        print(f"  ✅ 講師作成: {instructor2.email}")
    else:
        print(f"  ⏭️ 講師既存: {instructor2.email}")
    users['instructor2'] = instructor2

    # 保護者
    parent, created = User.objects.get_or_create(
        email='parent@test-juku.com',
        defaults={
            'tenant_id': tenant.id,
            'last_name': '鈴木',
            'first_name': '一郎',
            'last_name_kana': 'スズキ',
            'first_name_kana': 'イチロウ',
            'user_type': User.UserType.GUARDIAN,
            'role': User.Role.USER,
            'is_staff': False,
            'is_active': True,
        }
    )
    if created:
        parent.set_password('parent123')
        parent.save()
        print(f"  ✅ 保護者作成: {parent.email}")
    else:
        print(f"  ⏭️ 保護者既存: {parent.email}")
    users['parent'] = parent

    return users


def create_schools(tenant):
    """ブランドと校舎を作成"""
    print("\nブランド・校舎を作成中...")

    # ブランド
    brand, created = Brand.objects.get_or_create(
        tenant_id=tenant.id,
        brand_code='BRAND001',
        defaults={
            'brand_name': '個別指導アカデミー',
            'brand_name_short': '個別アカ',
            'brand_type': 'individual',
            'description': '1対1の個別指導塾',
            'color_primary': '#2563EB',
            'color_secondary': '#3B82F6',
            'is_active': True,
        }
    )
    if created:
        print(f"  ✅ ブランド作成: {brand.brand_name}")
    else:
        print(f"  ⏭️ ブランド既存: {brand.brand_name}")

    # 校舎
    school, created = School.objects.get_or_create(
        tenant_id=tenant.id,
        school_code='SCH001',
        defaults={
            'brand': brand,
            'school_name': '新宿校',
            'school_name_short': '新宿',
            'school_type': 'main',
            'postal_code': '160-0023',
            'prefecture': '東京都',
            'city': '新宿区',
            'address1': '西新宿1-1-1',
            'address2': 'テストビル5F',
            'phone': '03-1111-2222',
            'email': 'shinjuku@test-juku.com',
            'capacity': 50,
            'opening_date': date(2020, 4, 1),
            'is_active': True,
        }
    )
    if created:
        print(f"  ✅ 校舎作成: {school.school_name}")
    else:
        print(f"  ⏭️ 校舎既存: {school.school_name}")

    # 教室
    classrooms = []
    for i in range(1, 4):
        classroom, created = Classroom.objects.get_or_create(
            school=school,
            classroom_code=f'ROOM{i:02d}',
            defaults={
                'tenant_id': tenant.id,
                'classroom_name': f'教室{i}',
                'capacity': 4,
                'floor': '5F',
                'room_type': 'individual',
                'equipment': ['whiteboard', 'pc'],
                'is_active': True,
            }
        )
        classrooms.append(classroom)
        if created:
            print(f"  ✅ 教室作成: {classroom.classroom_name}")

    return brand, school, classrooms


def create_grades_and_subjects(tenant):
    """学年と教科を作成"""
    print("\n学年・教科を作成中...")

    grades = []
    grade_data = [
        ('E1', '小学1年', 'elementary', 1),
        ('E2', '小学2年', 'elementary', 2),
        ('E3', '小学3年', 'elementary', 3),
        ('E4', '小学4年', 'elementary', 4),
        ('E5', '小学5年', 'elementary', 5),
        ('E6', '小学6年', 'elementary', 6),
        ('J1', '中学1年', 'junior_high', 7),
        ('J2', '中学2年', 'junior_high', 8),
        ('J3', '中学3年', 'junior_high', 9),
        ('H1', '高校1年', 'high_school', 10),
        ('H2', '高校2年', 'high_school', 11),
        ('H3', '高校3年', 'high_school', 12),
    ]

    for i, (code, name, category, year) in enumerate(grade_data):
        grade, created = Grade.objects.get_or_create(
            tenant_id=tenant.id,
            grade_code=code,
            defaults={
                'grade_name': name,
                'grade_name_short': name[:3],
                'category': category,
                'school_year': year,
                'sort_order': i,
                'is_active': True,
            }
        )
        grades.append(grade)
        if created:
            print(f"  ✅ 学年作成: {grade.grade_name}")

    subjects = []
    subject_data = [
        ('MATH', '数学', 'main', '#EF4444'),
        ('ENG', '英語', 'main', '#3B82F6'),
        ('JPN', '国語', 'main', '#22C55E'),
        ('SCI', '理科', 'main', '#A855F7'),
        ('SOC', '社会', 'main', '#F59E0B'),
    ]

    for i, (code, name, category, color) in enumerate(subject_data):
        subject, created = Subject.objects.get_or_create(
            tenant_id=tenant.id,
            subject_code=code,
            defaults={
                'subject_name': name,
                'subject_name_short': name,
                'category': category,
                'color': color,
                'sort_order': i,
                'is_active': True,
            }
        )
        subjects.append(subject)
        if created:
            print(f"  ✅ 教科作成: {subject.subject_name}")

    return grades, subjects


def create_students(tenant, school, brand, grades):
    """生徒を作成"""
    print("\n生徒を作成中...")

    students = []
    student_data = [
        ('STU001', '田中', '太郎', 'タナカ', 'タロウ', 'male', date(2012, 4, 15), 6),  # 小6
        ('STU002', '高橋', '美咲', 'タカハシ', 'ミサキ', 'female', date(2011, 8, 20), 7),  # 中1
        ('STU003', '伊藤', '健太', 'イトウ', 'ケンタ', 'male', date(2010, 2, 10), 8),  # 中2
        ('STU004', '渡辺', 'さくら', 'ワタナベ', 'サクラ', 'female', date(2009, 11, 5), 9),  # 中3
        ('STU005', '小林', '大輔', 'コバヤシ', 'ダイスケ', 'male', date(2008, 6, 25), 10),  # 高1
    ]

    for student_no, last, first, last_kana, first_kana, gender, birth, grade_idx in student_data:
        student, created = Student.objects.get_or_create(
            tenant_id=tenant.id,
            student_no=student_no,
            defaults={
                'last_name': last,
                'first_name': first,
                'last_name_kana': last_kana,
                'first_name_kana': first_kana,
                'gender': gender,
                'birth_date': birth,
                'grade': grades[grade_idx - 1] if grade_idx <= len(grades) else None,
                'primary_school': school,
                'primary_brand': brand,
                'status': 'active',
                'enrollment_date': date(2024, 4, 1),
                'email': f'{student_no.lower()}@student.test-juku.com',
            }
        )
        students.append(student)
        if created:
            print(f"  ✅ 生徒作成: {student.full_name} ({student.student_no})")
        else:
            print(f"  ⏭️ 生徒既存: {student.full_name}")

    return students


def create_guardians(tenant, students, parent_user):
    """保護者を作成"""
    print("\n保護者を作成中...")

    # 田中太郎の保護者
    guardian1, created = Guardian.objects.get_or_create(
        tenant_id=tenant.id,
        guardian_no='GRD001',
        defaults={
            'last_name': '田中',
            'first_name': '一男',
            'last_name_kana': 'タナカ',
            'first_name_kana': 'カズオ',
            'email': 'tanaka.kazuo@test.com',
            'phone': '090-1111-2222',
            'postal_code': '160-0001',
            'prefecture': '東京都',
            'city': '新宿区',
            'address1': '新宿1-1-1',
            'user': parent_user,
        }
    )
    if created:
        print(f"  ✅ 保護者作成: {guardian1.full_name}")
        # 生徒との紐付け
        StudentGuardian.objects.get_or_create(
            tenant_id=tenant.id,
            student=students[0],
            guardian=guardian1,
            defaults={
                'relationship': 'father',
                'is_primary': True,
                'is_emergency_contact': True,
                'is_billing_target': True,
            }
        )
        print(f"    └─ 紐付け: {students[0].full_name}")

    # 高橋美咲の保護者
    guardian2, created = Guardian.objects.get_or_create(
        tenant_id=tenant.id,
        guardian_no='GRD002',
        defaults={
            'last_name': '高橋',
            'first_name': '恵子',
            'last_name_kana': 'タカハシ',
            'first_name_kana': 'ケイコ',
            'email': 'takahashi.keiko@test.com',
            'phone': '090-2222-3333',
        }
    )
    if created:
        print(f"  ✅ 保護者作成: {guardian2.full_name}")
        StudentGuardian.objects.get_or_create(
            tenant_id=tenant.id,
            student=students[1],
            guardian=guardian2,
            defaults={
                'relationship': 'mother',
                'is_primary': True,
                'is_emergency_contact': True,
                'is_billing_target': True,
            }
        )
        print(f"    └─ 紐付け: {students[1].full_name}")

    return [guardian1, guardian2]


def create_products(tenant, brand, subjects):
    """商品を作成"""
    print("\n商品を作成中...")

    products = []

    # 通常授業商品
    product1, created = Product.objects.get_or_create(
        tenant_id=tenant.id,
        product_code='PROD001',
        defaults={
            'product_name': '個別指導（週1回）',
            'product_name_short': '個別週1',
            'product_type': 'regular',
            'billing_type': 'monthly',
            'brand': brand,
            'base_price': Decimal('15000'),
            'tax_rate': Decimal('0.10'),
            'is_tax_included': False,
            'unit': '月',
            'is_active': True,
        }
    )
    products.append(product1)
    if created:
        print(f"  ✅ 商品作成: {product1.product_name}")

    product2, created = Product.objects.get_or_create(
        tenant_id=tenant.id,
        product_code='PROD002',
        defaults={
            'product_name': '個別指導（週2回）',
            'product_name_short': '個別週2',
            'product_type': 'regular',
            'billing_type': 'monthly',
            'brand': brand,
            'base_price': Decimal('28000'),
            'tax_rate': Decimal('0.10'),
            'is_tax_included': False,
            'unit': '月',
            'is_active': True,
        }
    )
    products.append(product2)
    if created:
        print(f"  ✅ 商品作成: {product2.product_name}")

    return products


def create_staff(tenant, school, users, subjects):
    """スタッフを作成"""
    print("\nスタッフを作成中...")

    staff_list = []

    staff1, created = Staff.objects.get_or_create(
        tenant_id=tenant.id,
        staff_no='STF001',
        defaults={
            'last_name': '山田',
            'first_name': '花子',
            'last_name_kana': 'ヤマダ',
            'first_name_kana': 'ハナコ',
            'email': 'instructor1@test-juku.com',
            'phone': '090-3333-4444',
            'staff_type': 'part_time',
            'position': 'teacher',
            'status': 'active',
            'hire_date': date(2023, 4, 1),
            'primary_school': school,
            'user': users['instructor1'],
        }
    )
    if created:
        # 指導可能教科を追加
        staff1.teachable_subjects.add(subjects[0], subjects[1])  # 数学、英語
        print(f"  ✅ スタッフ作成: {staff1.full_name}")
    staff_list.append(staff1)

    staff2, created = Staff.objects.get_or_create(
        tenant_id=tenant.id,
        staff_no='STF002',
        defaults={
            'last_name': '佐藤',
            'first_name': '次郎',
            'last_name_kana': 'サトウ',
            'first_name_kana': 'ジロウ',
            'email': 'instructor2@test-juku.com',
            'phone': '090-4444-5555',
            'staff_type': 'part_time',
            'position': 'teacher',
            'status': 'active',
            'hire_date': date(2023, 10, 1),
            'primary_school': school,
            'user': users['instructor2'],
        }
    )
    if created:
        staff2.teachable_subjects.add(subjects[2], subjects[3], subjects[4])  # 国語、理科、社会
        print(f"  ✅ スタッフ作成: {staff2.full_name}")
    staff_list.append(staff2)

    return staff_list


def create_contracts(tenant, school, brand, students, products):
    """契約を作成"""
    print("\n契約を作成中...")

    contracts = []

    for i, student in enumerate(students[:3]):  # 最初の3人
        contract, created = Contract.objects.get_or_create(
            tenant_id=tenant.id,
            contract_no=f'CNT{2024}{i+1:04d}',
            defaults={
                'student': student,
                'school': school,
                'brand': brand,
                'contract_date': date(2024, 4, 1),
                'start_date': date(2024, 4, 1),
                'status': 'active',
                'monthly_total': products[0].base_price,
            }
        )
        if created:
            # 契約詳細
            ContractDetail.objects.create(
                tenant_id=tenant.id,
                contract=contract,
                product=products[0],
                detail_type='individual',
                quantity=1,
                unit_price=products[0].base_price,
                subtotal=products[0].base_price,
                total=products[0].base_price,
                start_date=date(2024, 4, 1),
                lessons_per_week=1,
                minutes_per_lesson=50,
            )
            print(f"  ✅ 契約作成: {contract.contract_no} ({student.full_name})")
        contracts.append(contract)

    return contracts


def create_attendance_records(tenant, staff_list, school):
    """勤怠記録を作成"""
    print("\n勤怠記録を作成中...")

    today = date.today()

    for staff in staff_list:
        for days_ago in range(7):
            work_date = today - timedelta(days=days_ago)
            if work_date.weekday() < 5:  # 平日のみ
                attendance, created = Attendance.objects.get_or_create(
                    tenant_id=tenant.id,
                    staff=staff,
                    date=work_date,
                    school=school,
                    defaults={
                        'attendance_type': 'normal',
                        'clock_in': datetime.strptime('14:00', '%H:%M').time(),
                        'clock_out': datetime.strptime('21:00', '%H:%M').time(),
                        'break_minutes': 30,
                        'work_minutes': 390,
                        'lesson_count': 4,
                    }
                )
                if created:
                    print(f"  ✅ 勤怠作成: {staff.full_name} - {work_date}")


def main():
    """メイン処理"""
    print("=" * 60)
    print("OZAシステム テストデータ作成スクリプト")
    print("=" * 60)

    try:
        # テナント作成
        tenant = create_tenant()

        # ユーザー作成
        users = create_users(tenant)

        # ブランド・校舎作成
        brand, school, classrooms = create_schools(tenant)

        # 学年・教科作成
        grades, subjects = create_grades_and_subjects(tenant)

        # 生徒作成
        students = create_students(tenant, school, brand, grades)

        # 保護者作成
        guardians = create_guardians(tenant, students, users['parent'])

        # 商品作成
        products = create_products(tenant, brand, subjects)

        # スタッフ作成
        staff_list = create_staff(tenant, school, users, subjects)

        # 契約作成
        contracts = create_contracts(tenant, school, brand, students, products)

        # 勤怠記録作成
        create_attendance_records(tenant, staff_list, school)

        print("\n" + "=" * 60)
        print("テストデータ作成完了!")
        print("=" * 60)
        print("\n【ログイン情報】")
        print("管理者:")
        print("  Email: admin@test-juku.com")
        print("  Password: admin123")
        print("\n講師1:")
        print("  Email: instructor1@test-juku.com")
        print("  Password: instructor123")
        print("\n講師2:")
        print("  Email: instructor2@test-juku.com")
        print("  Password: instructor123")
        print("\n保護者:")
        print("  Email: parent@test-juku.com")
        print("  Password: parent123")
        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
