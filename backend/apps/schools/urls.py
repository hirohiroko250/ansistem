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
    PublicTrialAvailabilityView, PublicTrialBookingView,
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
    # 認証必要API
    path('', include(router.urls)),
]
