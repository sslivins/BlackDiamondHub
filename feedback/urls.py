# feedback/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
    path('', views.view_feedback, name='view_feedback'),
    path('mark_as_read/<int:feedback_id>/', views.mark_as_read, name='mark_as_read'),
    path('delete/<int:feedback_id>/', views.delete_feedback, name='delete_feedback'),
    path('bulk-action/', views.bulk_feedback_action, name='bulk_feedback_action'),    
]
