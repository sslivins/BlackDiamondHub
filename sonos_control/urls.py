from django.urls import path
from . import views

urlpatterns = [
    path('', views.sonos_control_view, name='sonos_control'),
    #path('sonos_play/', views.play_spotify_on_sonos, name='play_spotify_on_sonos'),
    path('get_sonos_status_partial/', views.get_sonos_status_partial, name='get_sonos_status_partial'),
    path('toggle_group/', views.toggle_group, name='toggle_group'),
    path('adjust-volume/', views.adjust_volume, name='adjust_volume'),
    path('toggle-play-pause/', views.toggle_play_pause, name='toggle_play_pause'),
    path('play-track/', views.play_track, name='play_track'),
    path('play-uri/', views.play_uri, name='play_uri'),
    path('queue-track/', views.queue_track, name='queue_track'),
    path('search/', views.spotify_search, name='spotify_search'),
    path('spotify/data/', views.fetch_spotify_data, name='fetch_spotify_data'),
]
