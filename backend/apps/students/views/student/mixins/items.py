"""
StudentViewSet Items Mixin - アイテム・チケット関連アクション
"""
from decimal import Decimal
from rest_framework.decorators import action
from rest_framework.response import Response


class StudentItemsMixin:
    """生徒アイテム・チケット関連のMixin"""

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """生徒の購入アイテム（StudentItem）一覧を取得"""
        from apps.contracts.models import StudentItem

        student = self.get_object()
        items = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True
        ).select_related('product', 'product__brand', 'contract', 'contract__school')

        billing_month = request.query_params.get('billing_month')
        if billing_month:
            items = items.filter(billing_month=billing_month)

        result = []
        for item in items:
            result.append({
                'id': str(item.id),
                'productId': str(item.product.id) if item.product else None,
                'productName': item.product.product_name if item.product else '',
                'productType': item.product.item_type if item.product else '',
                'brandName': item.product.brand.brand_name if item.product and item.product.brand else '',
                'brandCode': item.product.brand.brand_code if item.product and item.product.brand else '',
                'schoolName': item.contract.school.school_name if item.contract and item.contract.school else '',
                'billingMonth': item.billing_month,
                'quantity': item.quantity,
                'unitPrice': int(item.unit_price),
                'discountAmount': int(item.discount_amount),
                'finalPrice': int(item.final_price),
                'notes': item.notes,
                'createdAt': item.created_at.isoformat() if item.created_at else None,
            })

        return Response(result)

    @action(detail=True, methods=['get'])
    def tickets(self, request, pk=None):
        """生徒のチケット残高を取得"""
        from apps.contracts.models import StudentItem

        student = self.get_object()

        # チケット系のアイテム（item_type='ticket'）を集計
        items = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True
        ).select_related('product', 'product__brand')

        # ブランドごとにチケット残高を集計
        ticket_balances = {}
        total_tickets = Decimal('0')

        for item in items:
            if item.product and item.product.item_type == 'ticket':
                brand_name = item.product.brand.brand_name if item.product.brand else '未分類'
                if brand_name not in ticket_balances:
                    ticket_balances[brand_name] = {
                        'brandName': brand_name,
                        'totalTickets': Decimal('0'),
                        'usedTickets': Decimal('0'),
                        'remainingTickets': Decimal('0'),
                    }
                # 購入チケット数を加算（quantityがチケット枚数）
                ticket_balances[brand_name]['totalTickets'] += item.quantity
                ticket_balances[brand_name]['remainingTickets'] += item.quantity
                total_tickets += item.quantity

        # 辞書をリストに変換
        balances_list = list(ticket_balances.values())
        for balance in balances_list:
            balance['totalTickets'] = int(balance['totalTickets'])
            balance['usedTickets'] = int(balance['usedTickets'])
            balance['remainingTickets'] = int(balance['remainingTickets'])

        return Response({
            'studentId': str(student.id),
            'studentName': f'{student.last_name}{student.first_name}',
            'totalTickets': int(total_tickets),
            'usedTickets': 0,
            'remainingTickets': int(total_tickets),
            'balancesByBrand': balances_list,
        })

    @action(detail=True, methods=['get'], url_path='tickets/history')
    def tickets_history(self, request, pk=None):
        """生徒のチケット履歴を取得"""
        from apps.contracts.models import StudentItem

        student = self.get_object()

        # チケット系のアイテム（item_type='ticket'）を取得
        items = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True
        ).select_related('product', 'product__brand').order_by('-created_at')

        # フィルタリング
        brand_id = request.query_params.get('brand_id')
        if brand_id:
            items = items.filter(product__brand_id=brand_id)

        history = []
        for item in items:
            if item.product and item.product.item_type == 'ticket':
                history.append({
                    'id': str(item.id),
                    'date': item.created_at.isoformat() if item.created_at else None,
                    'type': 'purchase',
                    'description': f'{item.product.product_name} 購入',
                    'amount': item.quantity,
                    'brandName': item.product.brand.brand_name if item.product.brand else '',
                    'billingMonth': item.billing_month,
                })

        return Response(history)

    @action(detail=False, methods=['get'])
    def all_items(self, request):
        """保護者の全子どもの購入アイテム一覧を取得"""
        from apps.contracts.models import StudentItem
        from apps.schools.models import Brand

        # 保護者に紐づく全子どもの購入アイテムを取得
        students = self.get_queryset()
        student_ids = list(students.values_list('id', flat=True))

        items = StudentItem.objects.filter(
            student_id__in=student_ids,
            deleted_at__isnull=True
        ).select_related(
            'student', 'student__primary_school',  # 生徒の主校舎も含める
            'product', 'product__brand',
            'contract', 'contract__school', 'contract__course', 'contract__course__brand',
            'brand', 'school', 'course'  # StudentItemに直接保存された情報
        )

        billing_month = request.query_params.get('billing_month')
        if billing_month:
            items = items.filter(billing_month=billing_month)

        # ブランド名からブランドIDを取得するためのマッピング（遅延読み込み）
        brand_cache = None

        result = []
        for item in items:
            # コース名とブランド名の取得
            course_name = ''
            brand_name = ''
            brand_code = ''
            brand_id = None
            school_name = ''
            school_id = None
            start_date = None

            # 1. StudentItemに直接保存された情報を優先
            if item.brand:
                brand_name = item.brand.brand_name or ''
                brand_code = item.brand.brand_code or ''
                brand_id = str(item.brand.id)

            if item.school:
                school_name = item.school.school_name or ''
                school_id = str(item.school.id)

            if item.course:
                course_name = item.course.course_name or ''
                # コースからブランドを取得（StudentItemにbrandが設定されていない場合）
                if not brand_id and item.course.brand:
                    brand_name = item.course.brand.brand_name or ''
                    brand_code = item.course.brand.brand_code or ''
                    brand_id = str(item.course.brand.id)

            if item.start_date:
                start_date = item.start_date.isoformat()

            # 2. fallback: contractからcourseを取得してコース名・ブランド名を取得
            if not course_name and item.contract and item.contract.course:
                course_name = item.contract.course.course_name or ''
                if not brand_id and item.contract.course.brand:
                    brand_name = item.contract.course.brand.brand_name or ''
                    brand_code = item.contract.course.brand.brand_code or ''
                    brand_id = str(item.contract.course.brand.id)

            # 3. fallback: productから取得
            if not brand_id and item.product and item.product.brand:
                brand_name = item.product.brand.brand_name or ''
                brand_code = item.product.brand.brand_code or ''
                brand_id = str(item.product.brand.id)

            # 4. fallback: 商品名からブランドを推測（遅延読み込み）
            if not brand_id and item.product:
                product_name = item.product.product_name or ''
                # 必要な時だけブランドキャッシュを構築
                if brand_cache is None:
                    brand_cache = {}
                    for brand in Brand.objects.filter(tenant_id=request.user.tenant_id):
                        brand_cache[brand.brand_name] = {
                            'id': str(brand.id),
                            'code': brand.brand_code,
                            'name': brand.brand_name
                        }
                for bn, binfo in brand_cache.items():
                    if product_name.startswith(bn):
                        brand_name = bn
                        brand_code = binfo['code']
                        brand_id = binfo['id']
                        break

            # 5. fallback: contractからschoolを取得
            if not school_id and item.contract and item.contract.school:
                school_name = item.contract.school.school_name or ''
                school_id = str(item.contract.school.id)

            # 6. fallback: 生徒の主校舎から取得
            if not school_id and item.student and item.student.primary_school:
                school_name = item.student.primary_school.school_name or ''
                school_id = str(item.student.primary_school.id)

            result.append({
                'id': str(item.id),
                'studentId': str(item.student.id) if item.student else None,
                'studentName': f'{item.student.last_name}{item.student.first_name}' if item.student else '',
                'productId': str(item.product.id) if item.product else None,
                'productName': item.product.product_name if item.product else '',
                'productType': item.product.item_type if item.product else '',
                'courseName': course_name,
                'brandName': brand_name,
                'brandCode': brand_code,
                'brandId': brand_id,
                'schoolName': school_name,
                'schoolId': school_id,
                'startDate': start_date,  # 開始日を追加
                'billingMonth': item.billing_month,
                'quantity': item.quantity,
                'unitPrice': int(item.unit_price),
                'discountAmount': int(item.discount_amount),
                'finalPrice': int(item.final_price),
                'notes': item.notes,
                'createdAt': item.created_at.isoformat() if item.created_at else None,
            })

        # マイル情報とFS割引情報を取得
        mile_info = self._get_mile_info_for_customer(request.user)
        fs_discounts = self._get_fs_discounts_for_customer(request.user)

        return Response({
            'items': result,
            'mileInfo': mile_info,
            'fsDiscounts': fs_discounts,
        })

    def _get_mile_info_for_customer(self, user):
        """顧客用マイル情報を取得"""
        mile_info = {
            'balance': 0,
            'potentialDiscount': 0,
        }
        try:
            guardian = user.guardian
            if not guardian:
                return mile_info
            from apps.billing.models import MileTransaction
            mile_balance = MileTransaction.get_balance(guardian)
            potential_discount = MileTransaction.calculate_discount(mile_balance) if mile_balance >= 4 else 0
            mile_info = {
                'balance': mile_balance,
                'potentialDiscount': int(potential_discount),
            }
        except Exception:
            pass
        return mile_info

    def _get_fs_discounts_for_customer(self, user):
        """顧客用FS割引情報を取得"""
        fs_discount_list = []
        try:
            guardian = user.guardian
            if not guardian:
                return fs_discount_list
            fs_discounts = guardian.fs_discounts.filter(status='active')
            for fs in fs_discounts:
                fs_discount_list.append({
                    'id': str(fs.id),
                    'discountType': fs.discount_type,
                    'discountValue': int(fs.discount_value),
                    'validFrom': fs.valid_from.isoformat() if fs.valid_from else None,
                    'validUntil': fs.valid_until.isoformat() if fs.valid_until else None,
                })
        except Exception:
            pass
        return fs_discount_list
