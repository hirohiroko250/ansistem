"""
Product Views - 商品・割引管理
ProductViewSet, DiscountViewSet
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from ..models import Product, Discount
from ..serializers import (
    ProductListSerializer, ProductDetailSerializer,
    DiscountListSerializer, DiscountDetailSerializer,
)


class ProductViewSet(CSVMixin, viewsets.ModelViewSet):
    """商品ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'products'
    csv_export_fields = [
        'product_code', 'product_name', 'product_name_short', 'item_type',
        'brand.brand_code', 'brand.brand_name',
        'base_price', 'tax_rate', 'tax_type',
        'is_one_time',
        'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'product_code': '商品コード',
        'product_name': '商品名',
        'product_name_short': '商品名略称',
        'item_type': '商品種別',
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'base_price': '基本価格',
        'tax_rate': '税率',
        'tax_type': '税区分',
        'is_one_time': '一回きり',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }
    csv_import_mapping = {
        '商品コード': 'product_code',
        '商品名': 'product_name',
        '商品名略称': 'product_name_short',
        '商品種別': 'item_type',
        '基本価格': 'base_price',
        '税率': 'tax_rate',
        '税区分': 'tax_type',
        '一回きり': 'is_one_time',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['商品コード', '商品名']
    csv_unique_fields = ['product_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Product.objects.select_related(
            'brand', 'school', 'grade'
        ).filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        )

        item_type = self.request.query_params.get('item_type')
        if item_type:
            queryset = queryset.filter(item_type=item_type)

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['get'])
    def export(self, request):
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        return self.get_csv_template(request)


class DiscountViewSet(CSVMixin, viewsets.ModelViewSet):
    """割引ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'discounts'
    csv_export_fields = [
        'discount_code', 'discount_name', 'discount_type', 'calculation_type',
        'value', 'valid_from', 'valid_until', 'is_active'
    ]
    csv_export_headers = {
        'discount_code': '割引コード',
        'discount_name': '割引名',
        'discount_type': '割引種別',
        'calculation_type': '計算方法',
        'value': '割引値',
        'valid_from': '有効開始日',
        'valid_until': '有効終了日',
        'is_active': '有効',
    }
    csv_import_mapping = {
        '割引コード': 'discount_code',
        '割引名': 'discount_name',
        '割引種別': 'discount_type',
        '計算方法': 'calculation_type',
        '割引値': 'value',
        '有効開始日': 'valid_from',
        '有効終了日': 'valid_until',
        '有効': 'is_active',
    }
    csv_required_fields = ['割引コード', '割引名']
    csv_unique_fields = ['discount_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Discount.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        )

        discount_type = self.request.query_params.get('discount_type')
        if discount_type:
            queryset = queryset.filter(discount_type=discount_type)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return DiscountListSerializer
        return DiscountDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['get'])
    def export(self, request):
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        return self.get_csv_template(request)
