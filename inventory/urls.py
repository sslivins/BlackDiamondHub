from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='inventory'),
    path('item/<int:id>/', views.item_detail, name='item_detail'),
    path('item/<int:id>/json/', views.item_detail_json, name='item_detail_json'),
    path('item/<int:id>/edit/', views.edit_item, name='edit_item'),
    path('item/add/', views.add_item, name='add_item'),
    path('item/<int:id>/update/', views.update_item, name='update_item'),
]
