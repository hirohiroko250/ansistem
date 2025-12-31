"""
History Views - 操作履歴
OperationHistoryViewSet
"""
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsTenantUser
from apps.core.pagination import AdminResultsSetPagination


class OperationHistoryViewSet(viewsets.ViewSet):
    """操作履歴ビューセット

    契約履歴、割引操作ログ、引落結果などを統合して返す。
    """
    permission_classes = [IsAuthenticated, IsTenantUser]
    pagination_class = AdminResultsSetPagination

    def list(self, request):
        """操作履歴一覧を取得"""
        from apps.billing.models import DirectDebitResult
        from ..models import ContractHistory, DiscountOperationLog

        tenant_id = getattr(request, 'tenant_id', None)
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        limit = int(request.query_params.get('limit', 100))

        results = []

        # 日付フィルター用のクエリ作成
        date_filter = {}
        if year and year != 'all':
            date_filter['created_at__year'] = int(year)
        if month and month != 'all':
            date_filter['created_at__month'] = int(month)

        # 1. 契約履歴
        contract_histories = ContractHistory.objects.filter(
            tenant_id=tenant_id,
            **date_filter
        ).select_related('contract', 'contract__student', 'changed_by').order_by('-created_at')[:limit]

        for h in contract_histories:
            results.append({
                'id': str(h.id),
                'date': h.created_at.strftime('%Y-%m-%d') if h.created_at else None,
                'type': f'contract_{h.action_type}',
                'type_display': h.get_action_type_display(),
                'student_id': str(h.contract.student.id) if h.contract and h.contract.student else None,
                'student_name': h.contract.student.full_name if h.contract and h.contract.student else None,
                'guardian_id': None,
                'guardian_name': None,
                'content': h.change_summary,
                'status': None,
                'status_display': None,
                'amount': float(h.amount_after) if h.amount_after else None,
                'operator': h.changed_by.get_full_name() if h.changed_by else None,
                'created_at': h.created_at.isoformat() if h.created_at else None,
            })

        # 2. 割引操作ログ
        discount_logs = DiscountOperationLog.objects.filter(
            tenant_id=tenant_id,
            **date_filter
        ).select_related('student', 'operated_by').order_by('-created_at')[:limit]

        for d in discount_logs:
            results.append({
                'id': str(d.id),
                'date': d.created_at.strftime('%Y-%m-%d') if d.created_at else None,
                'type': f'discount_{d.operation_type}',
                'type_display': d.get_operation_type_display(),
                'student_id': str(d.student.id) if d.student else None,
                'student_name': d.student.full_name if d.student else None,
                'guardian_id': None,
                'guardian_name': None,
                'content': f'{d.discount_name} ¥{int(d.discount_amount):,}',
                'status': None,
                'status_display': None,
                'amount': float(d.discount_amount) if d.discount_amount else None,
                'operator': d.operated_by.get_full_name() if d.operated_by else None,
                'created_at': d.created_at.isoformat() if d.created_at else None,
            })

        # 3. 引落結果
        debit_results = DirectDebitResult.objects.filter(
            tenant_id=tenant_id,
            **date_filter
        ).select_related('guardian', 'invoice').order_by('-created_at')[:limit]

        for dr in debit_results:
            status_map = {
                'success': ('success', '成功'),
                'failed': ('failed', '失敗'),
                'pending': ('pending', '処理中'),
            }
            status_info = status_map.get(dr.result_status, (dr.result_status, dr.result_status))

            results.append({
                'id': str(dr.id),
                'date': dr.created_at.strftime('%Y-%m-%d') if dr.created_at else None,
                'type': f'debit_{dr.result_status}',
                'type_display': f'口座振替{status_info[1]}',
                'student_id': None,
                'student_name': None,
                'guardian_id': str(dr.guardian.id) if dr.guardian else None,
                'guardian_name': dr.guardian.full_name if dr.guardian else None,
                'content': f'{dr.billing_month}分 ¥{int(dr.amount):,}' if dr.amount else '',
                'status': status_info[0],
                'status_display': status_info[1],
                'amount': float(dr.amount) if dr.amount else None,
                'operator': None,
                'created_at': dr.created_at.isoformat() if dr.created_at else None,
            })

        # 日時でソート
        results.sort(key=lambda x: x['created_at'] or '', reverse=True)

        # limitを適用
        results = results[:limit]

        return Response({
            'data': results,
            'meta': {
                'total': len(results),
                'page': 1,
                'limit': limit,
                'total_pages': 1,
            }
        })
