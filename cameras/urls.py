from django.urls import path
from .views import camera_feed_view

urlpatterns = [
    path('', camera_feed_view, name='camera_feeds'),
]