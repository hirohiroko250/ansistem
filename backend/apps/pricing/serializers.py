"""
料金計算API用シリアライザー
"""
from datetime import date
from rest_framework import serializers


class PricingPreviewRequestSerializer(serializers.Serializer):
    """料金プレビューリクエスト"""
    product_id = serializers.UUIDField(required=False, help_text='商品ID')
    course_id = serializers.UUIDField(required=False, help_text='コースID')
    pack_id = serializers.UUIDField(required=False, help_text='パックID')
    enrollment_date = serializers.DateField(help_text='入会日')
    target_month = serializers.IntegerField(min_value=1, max_value=12, help_text='計算対象月')
    target_year = serializers.IntegerField(min_value=2000, max_value=2100, help_text='計算対象年')
    additional_tickets = serializers.IntegerField(min_value=0, default=0, help_text='追加チケット枚数')
    tax_category = serializers.IntegerField(min_value=1, max_value=3, default=1, help_text='税区分（1,2=課税, 3=非課税）')

    def validate(self, data):
        """少なくとも1つのIDが必要"""
        if not any([data.get('product_id'), data.get('course_id'), data.get('pack_id')]):
            raise serializers.ValidationError(
                'product_id, course_id, pack_id のいずれかを指定してください'
            )
        return data


class PricingItemResultSerializer(serializers.Serializer):
    """商品料金計算結果"""
    product_id = serializers.CharField()
    product_name = serializers.CharField()
    item_type = serializers.CharField()
    quantity = serializers.IntegerField(required=False, default=1)
    base_price = serializers.IntegerField(help_text='基本料金（税抜）')
    additional_ticket_price = serializers.IntegerField(help_text='追加チケット料金（税抜）')
    subtotal = serializers.IntegerField(help_text='小計（税抜）')
    tax_amount = serializers.IntegerField(help_text='消費税額')
    total_price = serializers.IntegerField(help_text='合計金額（税込）')
    is_first_month = serializers.BooleanField(help_text='初月かどうか')
    tax_category = serializers.IntegerField(help_text='税区分')
    applies_ticket_calc = serializers.BooleanField(help_text='3.3計算適用')
    additional_tickets = serializers.IntegerField()


class PricingCourseResultSerializer(serializers.Serializer):
    """コース料金計算結果"""
    course_id = serializers.CharField()
    course_name = serializers.CharField()
    items = PricingItemResultSerializer(many=True)
    subtotal = serializers.IntegerField(help_text='小計（税抜）')
    tax_amount = serializers.IntegerField(help_text='消費税合計')
    total_price = serializers.IntegerField(help_text='合計金額（税込）')
    is_first_month = serializers.BooleanField()
    enrollment_month = serializers.IntegerField()
    target_month = serializers.IntegerField()
    additional_tickets = serializers.IntegerField()


class PricingPackResultSerializer(serializers.Serializer):
    """パック料金計算結果"""
    pack_id = serializers.CharField()
    pack_name = serializers.CharField()
    courses = PricingCourseResultSerializer(many=True)
    pack_items = PricingItemResultSerializer(many=True)
    subtotal_before_discount = serializers.IntegerField(help_text='割引前小計')
    discount_amount = serializers.IntegerField(help_text='割引額')
    discount_type = serializers.CharField()
    subtotal = serializers.IntegerField(help_text='割引後小計（税抜）')
    tax_amount = serializers.IntegerField(help_text='消費税合計')
    total_price = serializers.IntegerField(help_text='合計金額（税込）')
    is_first_month = serializers.BooleanField()
    enrollment_month = serializers.IntegerField()
    target_month = serializers.IntegerField()
    additional_tickets = serializers.IntegerField()


class ContractBillingPreviewRequestSerializer(serializers.Serializer):
    """契約月次請求プレビューリクエスト"""
    contract_id = serializers.UUIDField(help_text='契約ID')
    target_month = serializers.IntegerField(min_value=1, max_value=12, help_text='計算対象月')
    target_year = serializers.IntegerField(min_value=2000, max_value=2100, help_text='計算対象年')
    additional_tickets = serializers.IntegerField(min_value=0, default=0, help_text='追加チケット枚数')


class ContractBillingPreviewResultSerializer(serializers.Serializer):
    """契約月次請求プレビュー結果"""
    contract_id = serializers.CharField()
    contract_no = serializers.CharField()
    course_id = serializers.CharField(required=False)
    course_name = serializers.CharField(required=False)
    items = PricingItemResultSerializer(many=True, required=False)
    subtotal = serializers.IntegerField(help_text='小計（税抜）', required=False)
    tax_amount = serializers.IntegerField(help_text='消費税合計', required=False)
    total_price = serializers.IntegerField(help_text='合計金額（税込）', required=False)
    is_first_month = serializers.BooleanField(required=False)
    enrollment_month = serializers.IntegerField(required=False)
    target_month = serializers.IntegerField(required=False)
    additional_tickets = serializers.IntegerField(required=False)
    error = serializers.CharField(required=False)
