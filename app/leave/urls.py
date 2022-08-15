from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    LeavePolicyViewSets,
    EmployeeLeaveRequestViewSets,
    EmployeeLeaveViewSets,
)

app_name = "leave"
router = DefaultRouter()

router.register("requests", EmployeeLeaveRequestViewSets)

router.register("policy", LeavePolicyViewSets)
router.register("", EmployeeLeaveViewSets)


urlpatterns = [
    path("", include(router.urls)),
]
