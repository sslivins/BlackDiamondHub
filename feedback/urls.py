# feedback/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
    path('feedback/', views.view_feedback, name='view_feedback'),
    path('feedback/mark_as_read/<int:feedback_id>/', views.mark_as_read, name='mark_as_read'),    
]
