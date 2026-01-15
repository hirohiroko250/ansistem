"""
Seminar & Certification Models - 講習・検定マスタ
T11: 講習マスタ (Seminar)
T11b: コース講習紐づけ (CourseSeminar)
T12: 検定マスタ (Certification)
T54: コース必須講習 (CourseRequiredSeminar)
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class Seminar(TenantModel):
    """T11: 講習マスタ（買い切り）"""

    class SeminarType(models.TextChoices):
        SPRING = 'spring', '春期講習'
        SUMMER = 'summer', '夏期講習'
        AUTUMN = 'autumn', '秋期講習'
        WINTER = 'winter', '冬期講習'
        SPECIAL = 'special', '特別講習'
        OTHER = 'other', 'その他'

    class TaxType(models.TextChoices):
        TAXABLE = '1', '課税'
        TAX_FREE = '2', '非課税'
        TAX_EXEMPT = '3', '不課税'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seminar_code = models.CharField('講習コード', max_length=50)
    seminar_name = models.CharField('講習名', max_length=200)
    seminar_name_short = models.CharField('講習名（短縮）', max_length=50, blank=True)
    old_id = models.CharField('旧システムID', max_length=50, blank=True, db_index=True)

    seminar_type = models.CharField(
        '講習種別',
        max_length=20,
        choices=SeminarType.choices,
        default=SeminarType.OTHER
    )

    # 必須/選択
    is_required = models.BooleanField('必須講習', default=False, help_text='コースに紐づく必須講習の場合はTrue')

    # 関連
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='seminars',
        verbose_name='ブランド'
    )
    grade = models.ForeignKey(
        'schools.Grade',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='seminars',
        verbose_name='対象学年'
    )

    # 期間
    year = models.IntegerField('年度')
    start_date = models.DateField('開始日', null=True, blank=True)
    end_date = models.DateField('終了日', null=True, blank=True)

    # 価格
    base_price = models.DecimalField('価格', max_digits=10, decimal_places=0, default=0)
    per_ticket_price = models.DecimalField('チケット単価', max_digits=10, decimal_places=0, default=0)
    tax_type = models.CharField('税区分', max_length=1, choices=TaxType.choices, default=TaxType.TAXABLE)

    # 月別請求価格（カレンダー価格）
    billing_price_jan = models.DecimalField('1月請求価格', max_digits=10, decimal_places=0, default=0)
    billing_price_feb = models.DecimalField('2月請求価格', max_digits=10, decimal_places=0, default=0)
    billing_price_mar = models.DecimalField('3月請求価格', max_digits=10, decimal_places=0, default=0)
    billing_price_apr = models.DecimalField('4月請求価格', max_digits=10, decimal_places=0, default=0)
    billing_price_may = models.DecimalField('5月請求価格', max_digits=10, decimal_places=0, default=0)
    billing_price_jun = models.DecimalField('6月請求価格', max_digits=10, decimal_places=0, default=0)
    billing_price_jul = models.DecimalField('7月請求価格', max_digits=10, decimal_places=0, default=0)
    billing_price_aug = models.DecimalField('8月請求価格', max_digits=10, decimal_places=0, default=0)
    billing_price_sep = models.DecimalField('9月請求価格', max_digits=10, decimal_places=0, default=0)
    billing_price_oct = models.DecimalField('10月請求価格', max_digits=10, decimal_places=0, default=0)
    billing_price_nov = models.DecimalField('11月請求価格', max_digits=10, decimal_places=0, default=0)
    billing_price_dec = models.DecimalField('12月請求価格', max_digits=10, decimal_places=0, default=0)

    # 入会者用月別価格
    enrollment_price_jan = models.DecimalField('1月入会者価格', max_digits=10, decimal_places=0, default=0)
    enrollment_price_feb = models.DecimalField('2月入会者価格', max_digits=10, decimal_places=0, default=0)
    enrollment_price_mar = models.DecimalField('3月入会者価格', max_digits=10, decimal_places=0, default=0)
    enrollment_price_apr = models.DecimalField('4月入会者価格', max_digits=10, decimal_places=0, default=0)
    enrollment_price_may = models.DecimalField('5月入会者価格', max_digits=10, decimal_places=0, default=0)
    enrollment_price_jun = models.DecimalField('6月入会者価格', max_digits=10, decimal_places=0, default=0)
    enrollment_price_jul = models.DecimalField('7月入会者価格', max_digits=10, decimal_places=0, default=0)
    enrollment_price_aug = models.DecimalField('8月入会者価格', max_digits=10, decimal_places=0, default=0)
    enrollment_price_sep = models.DecimalField('9月入会者価格', max_digits=10, decimal_places=0, default=0)
    enrollment_price_oct = models.DecimalField('10月入会者価格', max_digits=10, decimal_places=0, default=0)
    enrollment_price_nov = models.DecimalField('11月入会者価格', max_digits=10, decimal_places=0, default=0)
    enrollment_price_dec = models.DecimalField('12月入会者価格', max_digits=10, decimal_places=0, default=0)

    # マイル・割引
    mile = models.IntegerField('マイル', default=0)
    discount_max = models.IntegerField('割引MAX(%)', default=0)

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't11_seminars'
        verbose_name = 'T11_講習'
        verbose_name_plural = 'T11_講習'
        ordering = ['year', 'seminar_type', 'sort_order']
        unique_together = ['tenant_id', 'seminar_code']

    def __str__(self):
        return f"{self.seminar_name} ({self.year})"

    def get_billing_price_for_month(self, month: int):
        """指定月の請求価格を取得"""
        month_map = {
            1: self.billing_price_jan, 2: self.billing_price_feb, 3: self.billing_price_mar,
            4: self.billing_price_apr, 5: self.billing_price_may, 6: self.billing_price_jun,
            7: self.billing_price_jul, 8: self.billing_price_aug, 9: self.billing_price_sep,
            10: self.billing_price_oct, 11: self.billing_price_nov, 12: self.billing_price_dec,
        }
        return month_map.get(month, self.base_price)

    def get_enrollment_price_for_month(self, month: int):
        """指定月の入会者価格を取得"""
        month_map = {
            1: self.enrollment_price_jan, 2: self.enrollment_price_feb, 3: self.enrollment_price_mar,
            4: self.enrollment_price_apr, 5: self.enrollment_price_may, 6: self.enrollment_price_jun,
            7: self.enrollment_price_jul, 8: self.enrollment_price_aug, 9: self.enrollment_price_sep,
            10: self.enrollment_price_oct, 11: self.enrollment_price_nov, 12: self.enrollment_price_dec,
        }
        return month_map.get(month, self.base_price)


class CourseSeminar(TenantModel):
    """T11b: コースと講習の紐づけ

    コースに対して必須/選択の講習会を定義する。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    course = models.ForeignKey(
        'contracts.Course',
        on_delete=models.CASCADE,
        related_name='course_seminars',
        verbose_name='コース'
    )
    seminar = models.ForeignKey(
        Seminar,
        on_delete=models.CASCADE,
        related_name='course_seminars',
        verbose_name='講習'
    )

    is_required = models.BooleanField('必須', default=False, help_text='このコースで必須の講習会かどうか')
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't11b_course_seminars'
        verbose_name = 'T11b_コース講習紐づけ'
        verbose_name_plural = 'T11b_コース講習紐づけ'
        unique_together = ['tenant_id', 'course', 'seminar']

    def __str__(self):
        return f"{self.course.course_name} - {self.seminar.seminar_name}"


class Certification(TenantModel):
    """T12: 検定マスタ（買い切り）"""

    class CertificationType(models.TextChoices):
        EIKEN = 'eiken', '英検'
        KANKEN = 'kanken', '漢検'
        SUKEN = 'suken', '数検'
        SOROBAN = 'soroban', '珠算検定'
        ANZAN = 'anzan', '暗算検定'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    certification_code = models.CharField('検定コード', max_length=50)
    certification_name = models.CharField('検定名', max_length=200)

    certification_type = models.CharField(
        '検定種別',
        max_length=20,
        choices=CertificationType.choices,
        default=CertificationType.OTHER
    )

    level = models.CharField('級・レベル', max_length=50, blank=True)

    # 関連
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='certifications',
        verbose_name='ブランド'
    )

    # 試験日
    year = models.IntegerField('年度')
    exam_date = models.DateField('試験日', null=True, blank=True)

    # 価格
    exam_fee = models.DecimalField('検定料', max_digits=10, decimal_places=0, default=0)

    # 購入締切（検定開始日の何日前まで購入可能か）
    purchase_deadline_days = models.IntegerField(
        '購入締切日数',
        default=7,
        help_text='検定開始日の何日前まで購入可能か（デフォルト: 7日前）'
    )

    # カレンダーコード（検定期間をカレンダーから取得する場合）
    calendar_code = models.CharField(
        'カレンダーコード',
        max_length=50,
        blank=True,
        help_text='検定期間をカレンダーから取得する場合に指定（例: 1021_SOR）'
    )

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't12_certifications'
        verbose_name = 'T12_検定'
        verbose_name_plural = 'T12_検定'
        ordering = ['year', 'certification_type']
        unique_together = ['tenant_id', 'certification_code']

    def __str__(self):
        return f"{self.certification_name} {self.level} ({self.year})"

    def get_next_exam_period(self, from_date=None):
        """次の検定期間を取得（カレンダーから）

        Returns:
            tuple: (開始日, 終了日) or (None, None)
        """
        from datetime import date, timedelta
        from apps.schools.models import LessonCalendar

        if from_date is None:
            from_date = date.today()

        # カレンダーコードが設定されている場合、カレンダーから検定日を取得
        if self.calendar_code:
            # カレンダーはテナント横断で検索（カレンダーコードでユニーク）
            exam_days = LessonCalendar.objects.filter(
                calendar_code=self.calendar_code,
                display_label='検',
                lesson_date__gte=from_date
            ).order_by('lesson_date').values_list('lesson_date', flat=True)

            if exam_days:
                exam_dates = list(exam_days)
                # 連続する日付をグループ化して最初の検定期間を取得
                start_date = exam_dates[0]
                end_date = start_date
                for i in range(1, len(exam_dates)):
                    if exam_dates[i] == end_date + timedelta(days=1):
                        end_date = exam_dates[i]
                    elif exam_dates[i] > end_date + timedelta(days=2):
                        # 2日以上離れていたら別の検定期間
                        break
                    else:
                        end_date = exam_dates[i]
                return (start_date, end_date)

        # exam_dateが設定されている場合はそれを使用
        if self.exam_date and self.exam_date >= from_date:
            return (self.exam_date, self.exam_date)

        return (None, None)

    def can_purchase(self, purchase_date=None):
        """購入可能かどうかをチェック

        Returns:
            tuple: (購入可能かどうか, エラーメッセージ)
        """
        from datetime import date, timedelta

        if purchase_date is None:
            purchase_date = date.today()

        start_date, end_date = self.get_next_exam_period(from_date=purchase_date)

        if start_date is None:
            # 検定期間が見つからない場合は購入可能
            return (True, None)

        # 購入締切日を計算
        deadline = start_date - timedelta(days=self.purchase_deadline_days)

        if purchase_date > deadline:
            remaining_days = (start_date - purchase_date).days
            return (
                False,
                f'検定開始日（{start_date}）の{self.purchase_deadline_days}日前を過ぎているため購入できません。'
                f'（残り{remaining_days}日）'
            )

        return (True, None)


class CourseRequiredSeminar(TenantModel):
    """T54: コース必須講習"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    course = models.ForeignKey(
        'contracts.Course',
        on_delete=models.CASCADE,
        related_name='required_seminars',
        verbose_name='コース'
    )
    seminar = models.ForeignKey(
        Seminar,
        on_delete=models.CASCADE,
        related_name='required_by_courses',
        verbose_name='必須講習'
    )

    auto_enroll = models.BooleanField('自動申込', default=True)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't54_course_required_seminars'
        verbose_name = 'T54_コース必須講習'
        verbose_name_plural = 'T54_コース必須講習'
        unique_together = ['course', 'seminar']

    def __str__(self):
        return f"{self.course.course_name} → {self.seminar.seminar_name}"
