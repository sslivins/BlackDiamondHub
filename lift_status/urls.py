from django.urls import path
from . import views

urlpatterns = [
    path('', views.lift_status_view, name='lift_status'),
]
