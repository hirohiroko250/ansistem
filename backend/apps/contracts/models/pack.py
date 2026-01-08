"""
Pack Models - パックマスタ
T09: パック (Pack)
T53: パック→コース紐づけ (PackCourse)
T52: パック→商品紐づけ (PackItem)
T09b: パック→チケット紐づけ (PackTicket)
"""
import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import TenantModel


class Pack(TenantModel):
    """T09: パックマスタ

    複数のコースをまとめたセット商品
    例：アンイングリッシュクラブ + そろばんコース
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pack_code = models.CharField('パックコード', max_length=50)
    pack_name = models.CharField('パック名', max_length=100)

    # 関連
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='packs',
        verbose_name='ブランド'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='packs',
        verbose_name='校舎'
    )
    grade = models.ForeignKey(
        'schools.Grade',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='packs',
        verbose_name='対象学年'
    )

    # 商品セット（入会金＋教材費＋授業料などの組み合わせ）
    product_set = models.ForeignKey(
        'contracts.ProductSet',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='packs',
        verbose_name='商品セット',
        help_text='入会金＋教材費＋授業料などの商品組み合わせ'
    )

    # パック料金（設定した場合、各コースの合計ではなくこちらを使用）
    pack_price = models.DecimalField(
        '授業料',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='設定した場合、コース積み上げではなくこの料金を使用'
    )

    # 割引設定
    discount_type = models.CharField(
        '割引種別',
        max_length=20,
        choices=[
            ('none', '割引なし'),
            ('percentage', '割合割引'),
            ('fixed', '固定割引'),
        ],
        default='none'
    )
    discount_value = models.DecimalField(
        '割引値',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='割合の場合は%、固定の場合は円'
    )

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't09_packs'
        verbose_name = 'T09_パック'
        verbose_name_plural = 'T09_パック'
        ordering = ['sort_order', 'pack_code']
        unique_together = ['tenant_id', 'pack_code']

    def __str__(self):
        return f"{self.pack_name} ({self.pack_code})"

    def get_price(self):
        """パックの料金を取得"""
        if self.pack_price is not None:
            return self.pack_price

        # コース積み上げ（prefetchキャッシュを活用するためall()を使用）
        total = Decimal('0')
        for item in self.pack_courses.all():
            if item.is_active:
                total += item.course.get_price()

        # 割引適用
        if self.discount_type == 'percentage':
            total = total * (1 - self.discount_value / 100)
        elif self.discount_type == 'fixed':
            total = total - self.discount_value

        return max(total, Decimal('0'))


class PackCourse(TenantModel):
    """T53: パックコース構成"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pack = models.ForeignKey(
        Pack,
        on_delete=models.CASCADE,
        related_name='pack_courses',
        verbose_name='パック'
    )
    course = models.ForeignKey(
        'contracts.Course',
        on_delete=models.CASCADE,
        related_name='in_packs',
        verbose_name='コース'
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't53_pack_courses'
        verbose_name = 'T53_パックコース構成'
        verbose_name_plural = 'T53_パックコース構成'
        ordering = ['pack', 'sort_order']
        unique_together = ['pack', 'course']

    def __str__(self):
        return f"{self.pack.pack_name} ← {self.course.course_name}"


class PackItem(TenantModel):
    """T52: パック商品構成

    パックに直接紐づく商品（D列=4の商品）
    コースの商品構成（CourseItem）と同様の構造
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pack = models.ForeignKey(
        Pack,
        on_delete=models.CASCADE,
        related_name='pack_items',
        verbose_name='パック'
    )
    product = models.ForeignKey(
        'contracts.Product',
        on_delete=models.CASCADE,
        related_name='in_packs',
        verbose_name='商品'
    )

    quantity = models.IntegerField('数量', default=1)
    price_override = models.DecimalField(
        '価格上書き',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='設定した場合、商品の基本価格ではなくこの価格を使用'
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't52_pack_items'
        verbose_name = 'T52_パック商品構成'
        verbose_name_plural = 'T52_パック商品構成'
        ordering = ['pack', 'sort_order']
        unique_together = ['pack', 'product']

    def __str__(self):
        return f"{self.pack.pack_name} ← {self.product.product_name}"

    def get_price(self):
        """この商品の価格を取得"""
        if self.price_override is not None:
            return self.price_override
        return self.product.base_price * self.quantity


class PackTicket(TenantModel):
    """T09b: パックチケット構成

    パックに直接紐づくチケットを定義
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pack = models.ForeignKey(
        Pack,
        on_delete=models.CASCADE,
        related_name='pack_tickets',
        verbose_name='パック'
    )
    ticket = models.ForeignKey(
        'contracts.Ticket',
        on_delete=models.CASCADE,
        related_name='in_packs',
        verbose_name='チケット'
    )

    quantity = models.IntegerField('付与枚数', default=1)
    per_week = models.IntegerField('週あたり', default=1)

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't09b_pack_tickets'
        verbose_name = 'T09b_パックチケット'
        verbose_name_plural = 'T09b_パックチケット'
        ordering = ['pack', 'sort_order']
        unique_together = ['pack', 'ticket']

    def __str__(self):
        return f"{self.pack.pack_name} ← {self.ticket.ticket_name}"
