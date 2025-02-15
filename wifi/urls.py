from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.wifi_qr, name='wifi_qr'),
]