from django.urls import path
from .views import sonos_control_view

urlpatterns = [
    path('', sonos_control_view, name='sonos_control'),
]
