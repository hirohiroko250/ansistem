"""
Schools Signals
休校設定時にお知らせを自動作成
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(post_save, sender='schools.SchoolClosure')
def create_announcement_on_closure(sender, instance, created, **kwargs):
    """
    休校設定が作成されたとき、お知らせを自動作成する
    """
    if not created:
        return

    try:
        from apps.communications.models import Announcement

        # 休校日のフォーマット
        closure_date = instance.closure_date
        date_str = f"{closure_date.year}年{closure_date.month}月{closure_date.day}日"

        # タイトルと内容を生成
        school_name = instance.school.school_name if instance.school else "全校舎"
        brand_name = instance.brand.brand_name if instance.brand else ""
        closure_type_display = instance.get_closure_type_display()
        reason = getattr(instance, 'reason', '') or ''

        # タイトル生成
        if brand_name:
            title = f"【{closure_type_display}】{date_str} {brand_name}"
        else:
            title = f"【{closure_type_display}】{date_str} {school_name}"

        # 内容生成
        content_lines = [
            f"{date_str}は{closure_type_display}となります。",
        ]

        if instance.school:
            content_lines.append(f"対象校舎: {school_name}")

        if instance.brand:
            content_lines.append(f"対象ブランド: {brand_name}")

        if instance.schedule:
            # 特定の時間帯のみの休講
            schedule = instance.schedule
            day_names = ['', '月', '火', '水', '木', '金', '土', '日']
            day_name = day_names[schedule.day_of_week] if 1 <= schedule.day_of_week <= 7 else ''
            time_info = ""
            if hasattr(schedule, 'time_slot') and schedule.time_slot:
                try:
                    start = schedule.time_slot.start_time.strftime('%H:%M')
                    end = schedule.time_slot.end_time.strftime('%H:%M')
                    time_info = f"{start}-{end}"
                except Exception:
                    pass
            content_lines.append(f"対象時間帯: {day_name}曜日 {time_info}".strip())
        else:
            content_lines.append("対象: 終日")

        if reason:
            content_lines.append(f"理由: {reason}")

        content_lines.append("")
        content_lines.append("ご不便をおかけいたしますが、ご理解のほどよろしくお願いいたします。")

        content = "\n".join(content_lines)

        # お知らせを作成
        announcement = Announcement.objects.create(
            tenant_id=instance.tenant_id,
            title=title,
            content=content,
            target_type=Announcement.TargetType.GUARDIANS,  # 保護者向け
            status=Announcement.Status.SENT,  # 即時公開
            sent_at=timezone.now(),
        )

        # 対象校舎を設定
        if instance.school:
            announcement.target_schools.add(instance.school)

        logger.info(f"[SchoolClosure] Created announcement: {announcement.id} for closure: {instance.id}")

        # 操作ログを記録
        try:
            from .models import CalendarOperationLog
            CalendarOperationLog.log_closure(
                tenant_id=instance.tenant_id,
                closure=instance,
                user=None,  # シグナルでは操作者不明
            )
            logger.info(f"[SchoolClosure] Created operation log for closure: {instance.id}")
        except Exception as log_error:
            logger.warning(f"[SchoolClosure] Failed to create operation log: {log_error}")

    except Exception as e:
        logger.error(f"[SchoolClosure] Failed to create announcement: {e}", exc_info=True)
