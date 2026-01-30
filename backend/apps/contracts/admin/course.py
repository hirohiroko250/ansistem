"""
Course Admin - コース管理
CourseAdmin, CourseItemAdmin, CourseRequiredSeminarAdmin
"""
from django.contrib import admin
from django.http import HttpResponseRedirect
from apps.core.admin_csv import CSVImportExportMixin
from ..models import Course, CourseItem, CourseRequiredSeminar


# =============================================================================
# T08: コース
# =============================================================================
class CourseItemInline(admin.TabularInline):
    model = CourseItem
    extra = 1
    can_delete = True
    raw_id_fields = ['product']
    fields = ['product', 'quantity', 'price_override', 'sort_order', 'is_active']
    verbose_name = '商品（T03_契約全部から選択）'
    verbose_name_plural = 'T52_コース商品構成'


# CourseTicketInline will be added dynamically in __init__.py


@admin.register(Course)
class CourseAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'course_code', 'course_name', 'brand', 'grade',
        'get_ticket_codes', 'product_set', 'course_price', 'is_visible', 'is_active'
    ]
    list_filter = ['brand', 'grade', 'is_visible', 'product_set', 'is_active']
    search_fields = ['course_code', 'course_name']
    raw_id_fields = ['brand', 'school', 'grade', 'product_set']
    list_editable = ['is_visible']  # 一覧から直接編集可能
    inlines = [CourseItemInline]  # CourseTicketInline added dynamically in __init__.py
    ordering = ['brand', 'grade', 'course_code']
    actions = ['make_visible', 'make_invisible', 'apply_product_set']
    change_form_template = 'admin/contracts/course/change_form.html'

    def get_queryset(self, request):
        """チケット情報を効率的に取得"""
        return super().get_queryset(request).prefetch_related('course_tickets__ticket')

    @admin.display(description='チケットID')
    def get_ticket_codes(self, obj):
        """紐づくチケットIDを表示"""
        tickets = obj.course_tickets.filter(is_active=True).select_related('ticket')
        if tickets:
            return ', '.join([ct.ticket.ticket_code for ct in tickets if ct.ticket])
        return '-'

    @admin.action(description='選択したコースを表示する')
    def make_visible(self, request, queryset):
        updated = queryset.update(is_visible=True)
        self.message_user(request, f'{updated}件のコースを表示に設定しました。')

    @admin.action(description='選択したコースを非表示にする')
    def make_invisible(self, request, queryset):
        updated = queryset.update(is_visible=False)
        self.message_user(request, f'{updated}件のコースを非表示に設定しました。')

    @admin.action(description='商品セットを適用（CourseItemにコピー）')
    def apply_product_set(self, request, queryset):
        """選択したコースに紐づく商品セットの内容をCourseItemにコピー"""
        total_created = 0
        total_skipped = 0
        for course in queryset:
            if not course.product_set:
                continue
            for set_item in course.product_set.items.filter(is_active=True):
                # 既に同じ商品がCourseItemにあればスキップ
                existing = CourseItem.objects.filter(
                    course=course,
                    product=set_item.product
                ).exists()
                if existing:
                    total_skipped += 1
                    continue
                # CourseItemを作成
                CourseItem.objects.create(
                    course=course,
                    product=set_item.product,
                    quantity=set_item.quantity,
                    price_override=set_item.price_override,
                    sort_order=set_item.sort_order,
                    is_active=True,
                    tenant_id=course.tenant_id,
                    tenant_ref=course.tenant_ref,
                )
                total_created += 1
        self.message_user(
            request,
            f'{total_created}件の商品をコースに追加しました。（{total_skipped}件はスキップ）'
        )

    def response_change(self, request, obj):
        """詳細画面で「商品セット適用」ボタンが押された場合の処理"""
        if "_apply_product_set" in request.POST:
            if obj.product_set:
                created = 0
                skipped = 0
                for set_item in obj.product_set.items.filter(is_active=True):
                    existing = CourseItem.objects.filter(
                        course=obj,
                        product=set_item.product
                    ).exists()
                    if existing:
                        skipped += 1
                        continue
                    CourseItem.objects.create(
                        course=obj,
                        product=set_item.product,
                        quantity=set_item.quantity,
                        price_override=set_item.price_override,
                        sort_order=set_item.sort_order,
                        is_active=True,
                        tenant_id=obj.tenant_id,
                        tenant_ref=obj.tenant_ref,
                    )
                    created += 1
                self.message_user(
                    request,
                    f'商品セット「{obj.product_set.set_name}」から{created}件の商品を追加しました。（{skipped}件はスキップ）'
                )
            else:
                self.message_user(request, '商品セットが設定されていません。', level='warning')
            return HttpResponseRedirect(request.path)
        return super().response_change(request, obj)

    def save_formset(self, request, form, formset, change):
        """インラインのtenant情報を親から引き継ぐ"""
        instances = formset.save(commit=False)
        # 削除対象を処理（物理削除）
        for obj in formset.deleted_objects:
            obj.hard_delete()
        # 新規・更新対象を処理
        for instance in instances:
            if form.instance.tenant_id:
                instance.tenant_id = form.instance.tenant_id
                instance.tenant_ref = form.instance.tenant_ref
            instance.save()
        formset.save_m2m()

    csv_import_fields = {
        'コースコード': 'course_code',
        'コース名': 'course_name',
        'ブランドコード': 'brand__brand_code',
        '教室コード': 'school__school_code',
        '学年コード': 'grade__grade_code',
        'コース料金': 'course_price',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['コースコード', 'コース名']
    csv_unique_fields = ['course_code']
    csv_export_fields = [
        'course_code', 'course_name', 'brand.brand_name', 'school.school_name',
        'grade.grade_name', 'product_set.set_name', 'course_price',
        'promotion_course.course_code', 'promotion_course.course_name',
        'description', 'sort_order', 'is_visible', 'mile', 'is_active'
    ]
    csv_export_headers = {
        'course_code': 'コースコード',
        'course_name': 'コース名',
        'brand.brand_name': 'ブランド名',
        'school.school_name': '校舎名',
        'grade.grade_name': '学年名',
        'product_set.set_name': '商品セット',
        'course_price': 'コース料金',
        'promotion_course.course_code': '昇格先コースコード',
        'promotion_course.course_name': '昇格先コース名',
        'description': '説明',
        'sort_order': '表示順',
        'is_visible': '保護者に表示',
        'mile': 'マイル',
        'is_active': '有効',
    }


# =============================================================================
# T52: コース商品構成
# =============================================================================
@admin.register(CourseItem)
class CourseItemAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['course', 'product', 'quantity', 'price_override', 'is_active']
    list_filter = ['is_active', 'course']
    search_fields = ['course__course_name', 'product__product_name']
    raw_id_fields = ['course', 'product']

    csv_import_fields = {
        'コースコード': 'course__course_code',
        '商品コード': 'product__product_code',
        '数量': 'quantity',
        '単価上書き': 'price_override',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['コースコード', '商品コード']
    csv_unique_fields = []
    csv_export_fields = [
        'course.course_code', 'course.course_name',
        'product.product_code', 'product.product_name',
        'quantity', 'price_override', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'product.product_code': '商品コード',
        'product.product_name': '商品名',
        'quantity': '数量',
        'price_override': '単価上書き',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T54: コース必須講習
# =============================================================================
@admin.register(CourseRequiredSeminar)
class CourseRequiredSeminarAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['course', 'seminar', 'auto_enroll', 'is_active']
    list_filter = ['auto_enroll', 'is_active']
    search_fields = ['course__course_name', 'seminar__seminar_name']
    raw_id_fields = ['course', 'seminar']

    csv_import_fields = {
        'コースコード': 'course__course_code',
        '講習コード': 'seminar__seminar_code',
        '自動登録': 'auto_enroll',
        '有効': 'is_active',
    }
    csv_required_fields = ['コースコード', '講習コード']
    csv_unique_fields = []
    csv_export_fields = [
        'course.course_code', 'course.course_name',
        'seminar.seminar_code', 'seminar.seminar_name',
        'auto_enroll', 'is_active'
    ]
    csv_export_headers = {
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'seminar.seminar_code': '講習コード',
        'seminar.seminar_name': '講習名',
        'auto_enroll': '自動登録',
        'is_active': '有効',
    }
