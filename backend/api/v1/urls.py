"""
API v1 URL Configuration
"""
from django.urls import path, include

app_name = 'api_v1'

urlpatterns = [
    # 認証
    path('auth/', include('apps.authentication.urls', namespace='auth')),

    # 校舎・ブランド・学年・教科
    path('schools/', include('apps.schools.urls', namespace='schools')),

    # 生徒・保護者
    path('students/', include('apps.students.urls', namespace='students')),

    # 契約・商品・割引
    path('contracts/', include('apps.contracts.urls', namespace='contracts')),

    # 授業・スケジュール
    path('lessons/', include('apps.lessons.urls', namespace='lessons')),

    # 人事・勤怠・給与
    path('hr/', include('apps.hr.urls', namespace='hr')),

    # コミュニケーション（チャット・対応履歴・ボット・通知）
    path('communications/', include('apps.communications.urls', namespace='communications')),

    # ユーザー管理
    path('users/', include('apps.users.urls', namespace='users')),

    # テナント管理
    path('tenants/', include('apps.tenants.urls', namespace='tenants')),

    # 料金計算
    path('pricing/', include('apps.pricing.urls', namespace='pricing')),
]
