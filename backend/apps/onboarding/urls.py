"""
Onboarding URLs - ユースケース単位のAPI
"""
from django.urls import path
from .views import (
    OnboardingRegisterView,
    AddStudentView,
    PurchaseCompleteView,
)

app_name = 'onboarding'

urlpatterns = [
    path('register/', OnboardingRegisterView.as_view(), name='register'),
    path('add-student/', AddStudentView.as_view(), name='add_student'),
    path('purchase/complete/', PurchaseCompleteView.as_view(), name='purchase_complete'),
]
