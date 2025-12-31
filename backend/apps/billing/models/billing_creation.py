"""
Billing Creation Helpers - 請求確定データ作成ヘルパー
ConfirmedBilling.create_from_* メソッドで使用する共通関数
"""
from decimal import Decimal
from django.db import models


def build_seminar_items_snapshot(tenant_id, student, year, month):
    """講習申込（SeminarEnrollment）から明細スナップショットを作成"""
    from apps.contracts.models import SeminarEnrollment

    billing_month_hyphen = f"{year}-{str(month).zfill(2)}"
    billing_month_compact = f"{year}{str(month).zfill(2)}"

    seminar_enrollments = SeminarEnrollment.objects.filter(
        tenant_id=tenant_id,
        student=student,
        status__in=[SeminarEnrollment.Status.APPLIED, SeminarEnrollment.Status.CONFIRMED],
        deleted_at__isnull=True
    ).filter(
        models.Q(billing_month=billing_month_hyphen) | models.Q(billing_month=billing_month_compact)
    ).select_related('seminar', 'seminar__brand')

    items = []
    subtotal = Decimal('0')

    for enrollment in seminar_enrollments:
        seminar = enrollment.seminar
        unit_price = enrollment.unit_price or Decimal('0')
        discount_amount = enrollment.discount_amount or Decimal('0')
        final_price = enrollment.final_price or (unit_price - discount_amount)

        # 講習会タイプに基づくitem_type
        seminar_type_map = {
            'spring': 'seminar_spring',
            'summer': 'seminar_summer',
            'winter': 'seminar_winter',
            'autumn': 'seminar_autumn',
            'special': 'seminar_special',
            'other': 'seminar',
        }
        item_type = seminar_type_map.get(seminar.seminar_type, 'seminar') if seminar else 'seminar'

        item_data = {
            'seminar_enrollment_id': str(enrollment.id),
            'old_id': seminar.old_id if seminar else '',
            'seminar_id': str(seminar.id) if seminar else None,
            'seminar_code': seminar.seminar_code if seminar else '',
            'product_name': seminar.seminar_name if seminar else '',
            'product_code': seminar.seminar_code if seminar else '',
            'brand_id': str(seminar.brand.id) if seminar and seminar.brand else None,
            'brand_name': seminar.brand.brand_name if seminar and seminar.brand else None,
            'item_type': item_type,
            'item_type_display': '講習会',
            'is_required': enrollment.is_required,
            'quantity': 1,
            'unit_price': str(unit_price),
            'discount_amount': str(discount_amount),
            'final_price': str(final_price),
            'notes': enrollment.notes or '',
        }
        items.append(item_data)
        subtotal += final_price

    return items, subtotal


def calculate_shawari_items(items_snapshot):
    """社割対象の授業料アイテムと割引額を計算"""
    from apps.contracts.models import Product

    tuition_types = ['tuition', 'TUITION']
    shawari_items = []

    for item in items_snapshot:
        if item.get('item_type') not in tuition_types:
            continue
        product_name = item.get('product_name', '') or ''
        if '社割' in product_name:
            continue
        item_amount = Decimal(str(item.get('final_price', 0) or item.get('unit_price', 0)))
        if item_amount <= 0:
            continue
        product_code = item.get('product_code', '') or item.get('old_id', '')
        discount_max_rate = Decimal('50')
        if product_code:
            product_obj = Product.objects.filter(product_code=product_code).first()
            if product_obj and product_obj.discount_max is not None:
                discount_max_rate = min(Decimal('50'), Decimal(str(product_obj.discount_max)))
        if discount_max_rate > 0:
            shawari_items.append({
                'product_name': product_name,
                'item_amount': item_amount,
                'discount_rate': discount_max_rate,
                'discount_amount': item_amount * discount_max_rate / Decimal('100'),
                'item_id': item.get('id', ''),
            })

    return shawari_items


def build_discounts_snapshot(tenant_id, student, guardian, year, month, items_snapshot, subtotal):
    """割引スナップショットを作成（共通処理）"""
    from apps.contracts.models import StudentDiscount, Product
    from apps.students.models import FSDiscount
    from apps.pricing.calculations import calculate_mile_discount
    from datetime import date as date_class

    billing_date = f"{year}-{str(month).zfill(2)}-01"
    billing_date_obj = date_class(year, month, 1)

    # 教材費があるかチェック
    has_material_fee = any(
        item.get('item_type') in [Product.ItemType.TEXTBOOK, Product.ItemType.ENROLLMENT_TEXTBOOK, 'textbook', 'enrollment_textbook']
        for item in items_snapshot
    )

    # 割引を取得（生徒レベル + 保護者レベル）
    discounts = StudentDiscount.objects.filter(
        tenant_id=tenant_id,
        is_active=True,
        deleted_at__isnull=True
    ).filter(
        models.Q(student=student) | models.Q(guardian=guardian, student__isnull=True)
    ).filter(
        models.Q(start_date__isnull=True) | models.Q(start_date__lte=billing_date),
        models.Q(end_date__isnull=True) | models.Q(end_date__gte=billing_date)
    )

    discounts_snapshot = []
    discount_total = Decimal('0')

    # 社割対象アイテムを計算
    shawari_items = calculate_shawari_items(items_snapshot)
    shawari_applied = False

    for discount in discounts:
        # コロナ割（教材費のみ）のチェック
        if 'コロナ' in (discount.discount_name or '') and not has_material_fee:
            continue

        # 社割は各授業料ごとに割引を適用
        if '社割' in (discount.discount_name or ''):
            if shawari_applied:
                continue
            if shawari_items:
                shawari_applied = True
                for idx, shawari_item in enumerate(shawari_items):
                    discount_data = {
                        'id': f"{discount.id}_item{idx}" if discount.id else f"shawari_item{idx}",
                        'old_id': discount.old_id or '',
                        'discount_name': f"社割（{shawari_item['product_name']}）",
                        'amount': str(shawari_item['discount_amount']),
                        'discount_unit': 'yen',
                        'discount_rate': str(shawari_item['discount_rate']),
                        'target_item_id': shawari_item['item_id'],
                        'is_shawari': True,
                    }
                    discounts_snapshot.append(discount_data)
                    discount_total += shawari_item['discount_amount']
            continue
        elif discount.discount_unit == 'percent':
            amount = subtotal * discount.amount / 100
        else:
            amount = discount.amount

        discount_data = {
            'id': str(discount.id),
            'old_id': discount.old_id or '',
            'discount_name': discount.discount_name,
            'amount': str(amount),
            'discount_unit': discount.discount_unit,
        }
        discounts_snapshot.append(discount_data)
        discount_total += amount

    # FS割引（友達紹介割引）
    fs_discounts = FSDiscount.objects.filter(
        tenant_id=tenant_id,
        guardian=guardian,
        status=FSDiscount.Status.ACTIVE,
        valid_from__lte=billing_date_obj,
        valid_until__gte=billing_date_obj
    )
    for fs in fs_discounts:
        if fs.discount_type == FSDiscount.DiscountType.PERCENTAGE:
            amount = subtotal * fs.discount_value / 100
        else:
            amount = fs.discount_value
        discount_data = {
            'id': str(fs.id),
            'old_id': '',
            'discount_name': 'FS割引（友達紹介）',
            'amount': str(amount),
            'discount_unit': 'percent' if fs.discount_type == FSDiscount.DiscountType.PERCENTAGE else 'yen',
        }
        discounts_snapshot.append(discount_data)
        discount_total += amount

    # マイル割引（家族割）
    mile_discount_amount, total_miles, mile_discount_name = calculate_mile_discount(guardian)
    if mile_discount_amount > 0:
        discount_data = {
            'id': '',
            'old_id': '',
            'discount_name': mile_discount_name or f'家族割（{total_miles}マイル）',
            'amount': str(mile_discount_amount),
            'discount_unit': 'yen',
        }
        discounts_snapshot.append(discount_data)
        discount_total += mile_discount_amount

    return discounts_snapshot, discount_total


def get_withdrawal_info(tenant_id, student):
    """退会日・休会日・復会日情報を取得"""
    from apps.students.models import StudentEnrollment, SuspensionRequest

    # 全退会日（生徒の退会日）
    student_withdrawal_date = student.withdrawal_date if hasattr(student, 'withdrawal_date') else None

    # ブランド退会日（各ブランドの終了日）
    brand_withdrawal_dates = {}
    enrollments = StudentEnrollment.objects.filter(
        tenant_id=tenant_id,
        student=student,
        end_date__isnull=False,
        deleted_at__isnull=True
    ).select_related('brand')
    for enrollment in enrollments:
        if enrollment.brand_id and enrollment.end_date:
            brand_withdrawal_dates[str(enrollment.brand_id)] = enrollment.end_date.isoformat()

    # 休会日・復会日を取得
    student_suspension_date = student.suspended_date if hasattr(student, 'suspended_date') else None
    student_return_date = None
    latest_suspension = SuspensionRequest.objects.filter(
        tenant_id=tenant_id,
        student=student,
        resumed_at__isnull=False,
        deleted_at__isnull=True
    ).order_by('-resumed_at').first()
    if latest_suspension:
        student_return_date = latest_suspension.resumed_at

    return {
        'withdrawal_date': student_withdrawal_date,
        'brand_withdrawal_dates': brand_withdrawal_dates,
        'suspension_date': student_suspension_date,
        'return_date': student_return_date,
    }


def build_student_items_snapshot(tenant_id, student, year, month):
    """StudentItem（生徒商品）から明細スナップショットを作成"""
    from apps.contracts.models import StudentItem

    billing_month_hyphen = f"{year}-{str(month).zfill(2)}"
    billing_month_compact = f"{year}{str(month).zfill(2)}"

    student_items = StudentItem.objects.filter(
        tenant_id=tenant_id,
        student=student,
        deleted_at__isnull=True
    ).filter(
        models.Q(billing_month=billing_month_hyphen) | models.Q(billing_month=billing_month_compact)
    ).select_related('product', 'brand', 'school', 'course', 'contract')

    items_snapshot = []
    subtotal = Decimal('0')

    for item in student_items:
        product = item.product
        unit_price = item.unit_price or Decimal('0')
        quantity = item.quantity or 1
        discount_amount = item.discount_amount or Decimal('0')
        final_price = item.final_price or (unit_price * quantity - discount_amount)

        item_data = {
            'student_item_id': str(item.id),
            'old_id': item.old_id or '',
            'contract_id': str(item.contract.id) if item.contract else None,
            'contract_no': item.contract.contract_no if item.contract else None,
            'course_id': str(item.course.id) if item.course else None,
            'course_name': item.course.course_name if item.course else None,
            'product_id': str(product.id) if product else None,
            'product_name': product.product_name if product else '',
            'product_code': product.product_code if product else '',
            'brand_id': str(item.brand.id) if item.brand else None,
            'brand_name': item.brand.brand_name if item.brand else None,
            'school_name': item.school.school_name if item.school else None,
            'item_type': product.item_type if product else 'other',
            'item_type_display': product.get_item_type_display() if product else '',
            'quantity': quantity,
            'unit_price': str(unit_price),
            'discount_amount': str(discount_amount),
            'final_price': str(final_price),
            'notes': item.notes or '',
        }
        items_snapshot.append(item_data)
        subtotal += final_price

    return items_snapshot, subtotal


def build_contract_items_snapshot(tenant_id, student, year, month):
    """Contract（契約）から明細スナップショットを作成"""
    from apps.contracts.models import Contract, Product
    from datetime import date

    billing_start = date(year, month, 1)
    if month == 12:
        billing_end = date(year + 1, 1, 1)
    else:
        billing_end = date(year, month + 1, 1)

    contracts = Contract.objects.filter(
        tenant_id=tenant_id,
        student=student,
        status=Contract.Status.ACTIVE,
        start_date__lt=billing_end,
    ).filter(
        models.Q(end_date__isnull=True) | models.Q(end_date__gte=billing_start)
    ).select_related('course', 'brand', 'school')

    items_snapshot = []
    subtotal = Decimal('0')

    # 月額請求対象の商品タイプ
    MONTHLY_BILLING_TYPES = [
        Product.ItemType.TUITION,
        Product.ItemType.MONTHLY_FEE,
        Product.ItemType.FACILITY,
        Product.ItemType.CUSTODY,
        Product.ItemType.SNACK,
        Product.ItemType.LUNCH,
        Product.ItemType.ABACUS,
        Product.ItemType.EXTRA_TUITION,
        Product.ItemType.TEXTBOOK,
    ]

    for contract in contracts:
        course = contract.course
        if not course:
            continue

        course_items = course.course_items.filter(
            is_active=True,
            product__item_type__in=MONTHLY_BILLING_TYPES
        ).select_related('product')

        selected_textbook_ids = set(contract.selected_textbooks.values_list('id', flat=True))

        for course_item in course_items:
            product = course_item.product
            if not product or not product.is_active:
                continue

            if product.item_type == Product.ItemType.TEXTBOOK:
                if product.id not in selected_textbook_ids:
                    continue

            unit_price = course_item.price_override if course_item.price_override is not None else (product.base_price or Decimal('0'))
            quantity = course_item.quantity or 1
            final_price = unit_price * quantity

            item_data = {
                'contract_id': str(contract.id),
                'contract_no': contract.contract_no,
                'old_id': product.product_code or contract.old_id or '',
                'course_id': str(course.id) if course else None,
                'course_name': course.course_name if course else None,
                'product_id': str(product.id),
                'product_name': product.product_name,
                'product_name_short': product.product_name_short or '',
                'brand_id': str(contract.brand.id) if contract.brand else None,
                'brand_name': contract.brand.brand_name if contract.brand else None,
                'quantity': quantity,
                'unit_price': str(unit_price),
                'discount_amount': '0',
                'final_price': str(final_price),
                'item_type': product.item_type,
                'item_type_display': product.get_item_type_display() if product.item_type else '',
            }
            items_snapshot.append(item_data)
            subtotal += final_price

    return items_snapshot, subtotal


def deduplicate_facility_items(items_snapshot):
    """設備費は1生徒につき1つのみ（最高額を採用）"""
    facility_types = ['facility', 'enrollment_facility']
    facility_items = [i for i in items_snapshot if i.get('item_type') in facility_types]
    non_facility_items = [i for i in items_snapshot if i.get('item_type') not in facility_types]

    if len(facility_items) > 1:
        highest_facility = max(facility_items, key=lambda x: Decimal(str(x.get('final_price', 0) or 0)))
        return non_facility_items + [highest_facility]

    return items_snapshot


def update_confirmed_data(confirmed, guardian, subtotal, discount_total, items_snapshot,
                          discounts_snapshot, withdrawal_info, carry_over, user=None):
    """確定データを更新する共通処理"""
    confirmed.guardian = guardian
    confirmed.subtotal = subtotal
    confirmed.discount_total = discount_total
    confirmed.total_amount = subtotal - discount_total
    confirmed.carry_over_amount = carry_over
    confirmed.balance = confirmed.total_amount + carry_over - confirmed.paid_amount
    confirmed.items_snapshot = items_snapshot
    confirmed.discounts_snapshot = discounts_snapshot
    confirmed.withdrawal_date = withdrawal_info['withdrawal_date']
    confirmed.brand_withdrawal_dates = withdrawal_info['brand_withdrawal_dates']
    confirmed.suspension_date = withdrawal_info['suspension_date']
    confirmed.return_date = withdrawal_info['return_date']
    if user:
        confirmed.confirmed_by = user
    confirmed.save()

    if confirmed.paid_amount > 0:
        confirmed.update_payment_status()

    return confirmed
