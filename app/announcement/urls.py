from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import AnnouncementViewSets

app_name = "announcement"

router = DefaultRouter()

router.register("", AnnouncementViewSets)

urlpatterns = [
    path("", include(router.urls)),
]
