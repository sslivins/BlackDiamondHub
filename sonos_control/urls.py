from django.urls import path
from . import views

urlpatterns = [
    path('', views.sonos_control_view, name='sonos_control'),
    #path('sonos_play/', views.play_spotify_on_sonos, name='play_spotify_on_sonos'),
    path('get_sonos_status_partial/', views.get_sonos_status_partial, name='get_sonos_status_partial'),
    path('toggle_group/', views.toggle_group, name='toggle_group'),
    path('adjust-volume/', views.adjust_volume, name='adjust_volume'),
    path('toggle-play-pause/', views.toggle_play_pause, name='toggle_play_pause'),
]
