"""
Billing URLs - 請求・入金・預り金・マイル管理
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InvoiceViewSet,
    PaymentViewSet,
    GuardianBalanceViewSet,
    OffsetLogViewSet,
    RefundRequestViewSet,
    MileTransactionViewSet,
)

app_name = 'billing'

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'balances', GuardianBalanceViewSet, basename='guardian-balance')
router.register(r'offset-logs', OffsetLogViewSet, basename='offset-log')
router.register(r'refund-requests', RefundRequestViewSet, basename='refund-request')
router.register(r'miles', MileTransactionViewSet, basename='mile-transaction')

urlpatterns = [
    path('', include(router.urls)),
]
