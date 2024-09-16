from django.urls import path
from . import views

urlpatterns = [
    path('', views.sonos_control_view, name='sonos_control'),
    path('sonos_play/', views.play_spotify_on_sonos, name='play_spotify_on_sonos'),
    path('toggle_group/', views.toggle_group, name='toggle_group'),
]
