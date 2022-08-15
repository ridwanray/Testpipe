from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ExpenseViewSets

app_name = "claims"
router = DefaultRouter()
router.register("expense", ExpenseViewSets)

urlpatterns = [
    path("", include(router.urls)),
]
