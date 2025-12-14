"""
Schools URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BrandViewSet, SchoolViewSet, GradeViewSet, SubjectViewSet, ClassroomViewSet,
    PublicSchoolListView, PublicPrefectureListView, PublicAreaListView, PublicSchoolsByAreaView,
    TimeSlotViewSet, SchoolScheduleViewSet, SchoolCourseViewSet, SchoolClosureViewSet,
    PublicBrandCategoriesView, PublicBrandSchoolsView, PublicLessonCalendarView, PublicTrialScheduleView,
    PublicTrialAvailabilityView, PublicTrialBookingView, PublicClassScheduleView, PublicSchoolsByTicketView,
    PublicTicketsBySchoolView, PublicTrialMonthlyAvailabilityView, PublicCalendarSeatsView,
    PublicTrialStatsView,
    PublicBankTypesView, PublicBanksView, PublicBankDetailView, PublicBankBranchesView,
    AdminCalendarView, AdminCalendarEventDetailView,
    GoogleCalendarEventsView, GoogleCalendarListView,
)

app_name = 'schools'

router = DefaultRouter()
router.register('brands', BrandViewSet, basename='brand')
router.register('schools', SchoolViewSet, basename='school')
router.register('grades', GradeViewSet, basename='grade')
router.register('subjects', SubjectViewSet, basename='subject')
router.register('classrooms', ClassroomViewSet, basename='classroom')
router.register('time-slots', TimeSlotViewSet, basename='time-slot')
router.register('schedules', SchoolScheduleViewSet, basename='schedule')
router.register('school-courses', SchoolCourseViewSet, basename='school-course')
router.register('closures', SchoolClosureViewSet, basename='closure')

urlpatterns = [
    # 公開API（認証不要）
    path('public/schools/', PublicSchoolListView.as_view(), name='public-school-list'),
    path('public/prefectures/', PublicPrefectureListView.as_view(), name='public-prefecture-list'),
    path('public/areas/', PublicAreaListView.as_view(), name='public-area-list'),
    path('public/schools-by-area/', PublicSchoolsByAreaView.as_view(), name='public-schools-by-area'),
    path('public/brand-categories/', PublicBrandCategoriesView.as_view(), name='public-brand-categories'),
    path('public/brands/<str:brand_id>/schools/', PublicBrandSchoolsView.as_view(), name='public-brand-schools'),
    path('public/lesson-calendar/', PublicLessonCalendarView.as_view(), name='public-lesson-calendar'),
    path('public/trial-schedule/', PublicTrialScheduleView.as_view(), name='public-trial-schedule'),
    path('public/trial-availability/', PublicTrialAvailabilityView.as_view(), name='public-trial-availability'),
    path('public/trial-booking/', PublicTrialBookingView.as_view(), name='public-trial-booking'),
    path('public/class-schedules/', PublicClassScheduleView.as_view(), name='public-class-schedules'),
    path('public/schools-by-ticket/', PublicSchoolsByTicketView.as_view(), name='public-schools-by-ticket'),
    path('public/tickets-by-school/', PublicTicketsBySchoolView.as_view(), name='public-tickets-by-school'),
    path('public/trial-monthly-availability/', PublicTrialMonthlyAvailabilityView.as_view(), name='public-trial-monthly-availability'),
    path('public/calendar-seats/', PublicCalendarSeatsView.as_view(), name='public-calendar-seats'),
    path('public/trial-stats/', PublicTrialStatsView.as_view(), name='public-trial-stats'),
    # 金融機関API（認証不要）
    path('public/bank-types/', PublicBankTypesView.as_view(), name='public-bank-types'),
    path('public/banks/', PublicBanksView.as_view(), name='public-banks'),
    path('public/banks/<uuid:bank_id>/', PublicBankDetailView.as_view(), name='public-bank-detail'),
    path('public/banks/<uuid:bank_id>/branches/', PublicBankBranchesView.as_view(), name='public-bank-branches'),
    # 管理者用カレンダーAPI
    path('admin/calendar/', AdminCalendarView.as_view(), name='admin-calendar'),
    path('admin/calendar/event/', AdminCalendarEventDetailView.as_view(), name='admin-calendar-event'),
    # 認証必要API
    path('', include(router.urls)),
]
