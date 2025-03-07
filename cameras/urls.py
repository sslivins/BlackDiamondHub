from django.urls import path
from . import views

urlpatterns = [
    path('', views.camera_feed_view, name='cameras'),
]