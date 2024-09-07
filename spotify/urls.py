# spotify/urls.py
from django.urls import path
from . import views

app_name = 'spotify'  # This line defines the namespace
urlpatterns = [
    path('', views.spotify_landing, name='landing'),
    path('login/', views.spotify_login, name='login'),
    path('callback/', views.spotify_callback, name='callback'),
    path('qr_callback/', views.spotify_qr_callback, name='qr_callback'),
    path('search/', views.spotify_search, name='spotify_search'),
    path('play/', views.spotify_play, name='spotify_play'),
    path('recently_played/', views.spotify_recently_played, name='spotify_recently_played'),
    path('favorites/', views.spotify_favorites, name='spotify_favorites'),
    path('devices/', views.spotify_devices, name='spotify_devices'),  # Return list of devices
    path('transfer_playback/', views.spotify_transfer_playback, name='spotify_transfer_playback'),  # Transfer playback to a device
    path('callback/', views.spotify_callback, name='spotify_callback'),
    path('get_token/', views.spotify_get_token, name='spotify_get_token'),  # New route to serve the token
    path('webplayer/', views.webplayer_view, name='webplayer'),  # Your web player view    
]
