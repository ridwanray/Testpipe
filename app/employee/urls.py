from .views import EmployeeViewSets
from rest_framework.routers import DefaultRouter
from django.urls import path, include

app_name = "employee"

router = DefaultRouter()
router.register("", EmployeeViewSets)


urlpatterns = [
    path("", include(router.urls)),
]
