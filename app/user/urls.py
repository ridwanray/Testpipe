from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewsets, CustomObtainTokenPairView, CreateTokenView
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView


app_name = "user"

router = DefaultRouter()
router.register("users", AuthViewsets)

urlpatterns = [
    path("", include(router.urls)),
    path("login/", CustomObtainTokenPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="refresh-token"),
    path("token/verify/", TokenVerifyView.as_view(), name="verify-token"),
    path("token/", CreateTokenView.as_view(), name="tokens"),
]
