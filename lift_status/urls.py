from django.urls import path
from . import views

urlpatterns = [
    path('', views.lift_status_view, name='lift_status'),
    path('data/', views.lift_status_data_view, name='lift_status_data'),
]
