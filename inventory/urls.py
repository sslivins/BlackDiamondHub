from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='inventory'),
    path('item/<int:id>/', views.item_detail, name='item_detail'),
    path('item/<int:id>/edit/', views.edit_item, name='edit_item'),
    path('item/add/', views.add_item, name='add_item'),
    path('accounts/profile/', views.profile, name='profile'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)