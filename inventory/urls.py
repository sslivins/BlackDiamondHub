from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='inventory'),
    path('item/<int:id>/', views.item_detail, name='item_detail'),
    path('item/<int:id>/edit/', views.edit_item, name='edit_item'),
    path('item/add/', views.add_item, name='add_item'),
]
