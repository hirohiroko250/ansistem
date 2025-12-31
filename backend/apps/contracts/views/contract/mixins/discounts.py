"""
Discount Actions Mixin - 割引管理アクション
DiscountActionsMixin
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from apps.contracts.models import Contract, StudentItem, StudentDiscount, DiscountOperationLog
from apps.contracts.serializers import ContractDetailSerializer


class DiscountActionsMixin:
    """割引管理アクションMixin"""

    @action(detail=True, methods=['post'], url_path='update-discounts')
    def update_discounts(self, request, pk=None):
        """契約の割引を更新（明細単位の割引に対応）"""
        contract = Contract.objects.filter(
            pk=pk,
            deleted_at__isnull=True
        ).select_related('student', 'brand', 'school', 'course').first()

        if not contract:
            return Response(
                {'error': '契約が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = request.tenant_id
        user = request.user
        # item_discounts を優先、後方互換性のため discounts もサポート
        discounts_data = request.data.get('item_discounts', request.data.get('discounts', []))
        notes = request.data.get('notes')

        # 割引Max取得（契約に紐づくコースまたは商品から）
        discount_max = 0
        if contract.course:
            # コースの商品から割引Maxを取得
            course_items = contract.course.course_items.filter(is_active=True).select_related('product')
            for ci in course_items:
                if ci.product and ci.product.discount_max:
                    discount_max = max(discount_max, ci.product.discount_max)
        # StudentItemから商品の割引Maxも確認
        student_items = StudentItem.objects.filter(
            student_id=contract.student_id,
            contract_id=contract.id
        ).select_related('product')
        for si in student_items:
            if si.product and si.product.discount_max:
                discount_max = max(discount_max, si.product.discount_max)

        # 操作前の合計割引額を計算
        existing_discounts = StudentDiscount.objects.filter(
            student_id=contract.student_id,
            is_active=True,
        ).filter(
            Q(brand_id__isnull=True) | Q(brand_id=contract.brand_id)
        )
        total_discount_before = sum(d.amount or 0 for d in existing_discounts)

        # 備考を更新
        if notes is not None:
            contract.notes = notes
            contract.save(update_fields=['notes', 'updated_at'])

        created_count = 0
        updated_count = 0
        deleted_count = 0
        operation_logs = []

        # IPアドレス取得
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')

        for discount_data in discounts_data:
            discount_id = discount_data.get('id')
            is_deleted = discount_data.get('is_deleted', False)
            is_new = discount_data.get('is_new', False)
            discount_name = discount_data.get('discount_name', '')
            discount_amount = discount_data.get('amount', 0)
            discount_unit = discount_data.get('discount_unit', 'yen')
            student_item_id = discount_data.get('student_item_id')
            # "default" は明細がない場合のデフォルト値なので None に変換
            if student_item_id == 'default':
                student_item_id = None

            if is_deleted and discount_id and not discount_id.startswith('new-'):
                # 既存の割引を削除（soft delete）
                old_discount = StudentDiscount.objects.filter(id=discount_id, tenant_id=tenant_id).first()
                if old_discount:
                    old_amount = old_discount.amount or 0
                    StudentDiscount.objects.filter(id=discount_id, tenant_id=tenant_id).update(is_active=False)
                    deleted_count += 1

                    # 操作ログを記録
                    total_after = total_discount_before - old_amount
                    log = DiscountOperationLog.log_operation(
                        contract=contract,
                        operation_type='delete',
                        discount_name=old_discount.discount_name,
                        discount_amount=old_amount,
                        discount_unit=old_discount.discount_unit,
                        discount_max=discount_max,
                        total_before=total_discount_before,
                        total_after=total_after,
                        user=user,
                        school=contract.school,
                        brand=contract.brand,
                        student_discount=old_discount,
                        ip_address=ip_address,
                        notes=f'割引削除: {old_discount.discount_name}'
                    )
                    operation_logs.append(log)
                    total_discount_before = total_after

            elif is_new or (discount_id and discount_id.startswith('new-')):
                # 新規割引を作成
                new_discount = StudentDiscount.objects.create(
                    tenant_id=tenant_id,
                    student_id=contract.student_id,
                    contract_id=contract.id,
                    student_item_id=student_item_id,  # 明細IDを保存
                    brand_id=contract.brand_id,
                    discount_name=discount_name,
                    amount=discount_amount,
                    discount_unit=discount_unit,
                    is_active=True,
                    is_recurring=True,
                )
                created_count += 1

                # 操作ログを記録
                total_after = total_discount_before + discount_amount
                log = DiscountOperationLog.log_operation(
                    contract=contract,
                    operation_type='add',
                    discount_name=discount_name,
                    discount_amount=discount_amount,
                    discount_unit=discount_unit,
                    discount_max=discount_max,
                    total_before=total_discount_before,
                    total_after=total_after,
                    user=user,
                    school=contract.school,
                    brand=contract.brand,
                    student_discount=new_discount,
                    ip_address=ip_address,
                    notes=f'割引追加: {discount_name}'
                )
                operation_logs.append(log)
                total_discount_before = total_after

            elif discount_id:
                # 既存の割引を更新
                old_discount = StudentDiscount.objects.filter(id=discount_id, tenant_id=tenant_id).first()
                if old_discount:
                    old_amount = old_discount.amount or 0
                    StudentDiscount.objects.filter(id=discount_id, tenant_id=tenant_id).update(
                        discount_name=discount_name,
                        amount=discount_amount,
                        discount_unit=discount_unit,
                    )
                    updated_count += 1

                    # 操作ログを記録
                    amount_diff = discount_amount - old_amount
                    total_after = total_discount_before + amount_diff
                    log = DiscountOperationLog.log_operation(
                        contract=contract,
                        operation_type='update',
                        discount_name=discount_name,
                        discount_amount=discount_amount,
                        discount_unit=discount_unit,
                        discount_max=discount_max,
                        total_before=total_discount_before,
                        total_after=total_after,
                        user=user,
                        school=contract.school,
                        brand=contract.brand,
                        student_discount=old_discount,
                        ip_address=ip_address,
                        notes=f'割引変更: {old_discount.discount_name} → {discount_name} ({old_amount}→{discount_amount})'
                    )
                    operation_logs.append(log)
                    total_discount_before = total_after

        # 操作ログの情報を返す
        logs_data = [{
            'id': str(log.id),
            'operation_type': log.operation_type,
            'discount_name': log.discount_name,
            'discount_amount': log.discount_amount,
            'discount_max': log.discount_max,
            'total_discount_after': log.total_discount_after,
            'excess_amount': log.excess_amount,
            'operated_by_name': log.operated_by_name,
            'created_at': log.created_at.isoformat(),
        } for log in operation_logs]

        return Response({
            'success': True,
            'created': created_count,
            'updated': updated_count,
            'deleted': deleted_count,
            'discount_max': discount_max,
            'operation_logs': logs_data,
            'contract': ContractDetailSerializer(contract).data
        })

    @action(detail=True, methods=['get'], url_path='discount-logs')
    def discount_logs(self, request, pk=None):
        """契約の割引操作履歴を取得"""
        contract = Contract.objects.filter(
            pk=pk,
            deleted_at__isnull=True
        ).first()

        if not contract:
            return Response(
                {'error': '契約が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        logs = DiscountOperationLog.objects.filter(
            contract_id=contract.id
        ).select_related('operated_by', 'school').order_by('-created_at')[:50]

        logs_data = [{
            'id': str(log.id),
            'operation_type': log.operation_type,
            'operation_type_display': log.get_operation_type_display(),
            'discount_name': log.discount_name,
            'discount_amount': log.discount_amount,
            'discount_unit': log.discount_unit,
            'discount_max': log.discount_max,
            'total_discount_before': log.total_discount_before,
            'total_discount_after': log.total_discount_after,
            'excess_amount': log.excess_amount,
            'school_name': log.school.school_name if log.school else '',
            'operated_by_name': log.operated_by_name,
            'notes': log.notes,
            'created_at': log.created_at.isoformat(),
        } for log in logs]

        return Response({
            'logs': logs_data,
            'total_count': len(logs_data)
        })
