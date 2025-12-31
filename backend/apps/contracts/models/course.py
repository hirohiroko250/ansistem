"""
Course Models - コースマスタ
T08: コース (Course)
T52: コース→商品紐づけ (CourseItem)
"""
import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import TenantModel


class Course(TenantModel):
    """T08: コースマスタ"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_code = models.CharField('コースコード', max_length=50)
    course_name = models.CharField('コース名', max_length=100)

    # 関連
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='courses',
        verbose_name='ブランド'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='courses',
        verbose_name='教室'
    )
    grade = models.ForeignKey(
        'schools.Grade',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='courses',
        verbose_name='対象学年'
    )

    # 商品セット（入会金＋教材費＋授業料などの組み合わせ）
    product_set = models.ForeignKey(
        'contracts.ProductSet',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='courses',
        verbose_name='商品セット',
        help_text='入会金＋教材費＋授業料などの商品組み合わせ'
    )

    # コース料金（設定した場合はこちらを使用）
    course_price = models.DecimalField(
        '授業料',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='設定した場合、商品積み上げではなくこの料金を使用'
    )

    # 学年進級時の昇格先コース
    promotion_course = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotion_from',
        verbose_name='昇格先コース',
        help_text='学年が上がった際に自動で昇格するコース（例：RYellow→Red）'
    )

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_visible = models.BooleanField(
        '保護者に表示',
        default=True,
        help_text='チェックを外すと保護者アプリに表示されません'
    )
    is_active = models.BooleanField('有効', default=True)

    # マイル・割引
    mile = models.DecimalField('マイル', max_digits=10, decimal_places=0, default=0)

    class Meta:
        db_table = 't08_courses'
        verbose_name = 'T08_金魚の糞付き'
        verbose_name_plural = 'T08_金魚の糞付き'
        ordering = ['sort_order', 'course_code']
        unique_together = ['tenant_id', 'course_code']

    def __str__(self):
        return f"{self.course_name} ({self.course_code})"

    def get_product_set_display(self):
        """商品セットの内容を表示"""
        if self.product_set:
            return self.product_set.get_items_display()
        return ""

    def get_price(self):
        """コースの料金を取得"""
        if self.course_price is not None:
            return self.course_price
        # 商品積み上げ
        total = Decimal('0')
        for item in self.course_items.filter(is_active=True):
            total += item.get_price() * item.quantity
        return total


class CourseItem(TenantModel):
    """T52: コース商品構成"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='course_items',
        verbose_name='コース'
    )
    product = models.ForeignKey(
        'contracts.Product',
        on_delete=models.CASCADE,
        related_name='in_courses',
        verbose_name='商品'
    )

    quantity = models.IntegerField('数量', default=1)
    price_override = models.DecimalField(
        '単価上書き',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't52_course_items'
        verbose_name = 'T52_コース商品構成'
        verbose_name_plural = 'T52_コース商品構成'
        ordering = ['course', 'sort_order']
        unique_together = ['course', 'product']

    def __str__(self):
        return f"{self.course.course_name} ← {self.product.product_name}"

    def get_price(self):
        if self.price_override is not None:
            return self.price_override
        return self.product.base_price
