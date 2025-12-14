# Lessons admin
from django.contrib import admin
from django.db.models import Case, When
from .models import AbsenceTicket

# Note: TimeSlot is now in apps.schools.admin
# LessonCalendar is in apps.schools.admin


@admin.register(AbsenceTicket)
class AbsenceTicketAdmin(admin.ModelAdmin):
    """欠席チケット管理（作業一覧）"""
    list_display = [
        'student',
        'absence_date',
        'consumption_symbol',
        'status',
        'valid_until',
        'created_at',
    ]
    list_filter = ['status', 'consumption_symbol', 'absence_date']
    search_fields = [
        'student__last_name',
        'student__first_name',
        'consumption_symbol',
    ]
    ordering = ['-absence_date']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'absence_date'

    fieldsets = (
        ('基本情報', {
            'fields': ('student', 'absence_date', 'class_schedule')
        }),
        ('チケット情報', {
            'fields': ('original_ticket', 'consumption_symbol', 'status')
        }),
        ('振替使用', {
            'fields': ('used_date', 'used_class_schedule'),
            'classes': ('collapse',)
        }),
        ('その他', {
            'fields': ('valid_until', 'notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """発行済を優先して表示"""
        qs = super().get_queryset(request)
        # status='issued' を先に表示
        return qs.order_by(
            Case(
                When(status='issued', then=0),
                default=1,
            ),
            '-absence_date'
        )
