from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import NotificationViewSets

app_name = 'notification'
router = DefaultRouter()
router.register('', NotificationViewSets)

urlpatterns = [
    path('', include(router.urls)),
]
