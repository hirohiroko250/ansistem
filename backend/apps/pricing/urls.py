from django.urls import path
from .views import PricingPreviewView, PricingConfirmView

app_name = 'pricing'

urlpatterns = [
    path('preview/', PricingPreviewView.as_view(), name='preview'),
    path('confirm/', PricingConfirmView.as_view(), name='confirm'),
]
