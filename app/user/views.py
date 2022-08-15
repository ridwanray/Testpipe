import asyncio
from django.conf import settings
from sentry_sdk import capture_exception
from rest_framework.decorators import action
from rest_framework import filters, permissions
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
    IsAuthenticatedOrReadOnly,
)
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.contrib.auth import get_user_model, logout, login
from rest_framework.settings import api_settings
from rest_framework.response import Response
from rest_framework import viewsets, status, generics, views
from django.contrib.auth.forms import AuthenticationForm
from rest_framework.decorators import api_view, permission_classes
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.authtoken.views import ObtainAuthToken
from django.utils.crypto import get_random_string
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from .models import User, Token
from .permissions import IsSuperAdmin, IsHRAdmin
from .serializers import (
    CreateUserSerializer,
    ListUserSerializer,
    AuthTokenSerializer,
    CustomObtainTokenPairSerializer,
    VerifyTokenSerializer,
    InitializePasswordResetSerializer,
    CreatePasswordSerializer,
)
from .tasks import send_registration_email, send_password_reset_email
from employee.models import Employee
from user.filters import VERIFY_TOKEN_PARAMETERS
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    inline_serializer,
    OpenApiResponse,
)

CACHE_TTL = getattr(settings, "CACHE_TTL", DEFAULT_TIMEOUT)


class AuthViewsets(viewsets.ModelViewSet):
    """User viewsets"""

    queryset = get_user_model().objects.all()
    serializer_class = ListUserSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active"]
    search_fields = ["email", "firstname", "lastname", "phone"]
    ordering_fields = [
        "created_at",
        "last_login",
        "email",
        "firstname",
        "lastname",
        "phone",
    ]

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(organisation=user.organisation)

    def get_serializer_class(self):
        if self.action == "create_password":
            return CreatePasswordSerializer
        elif self.action == "initialize_reset":
            return InitializePasswordResetSerializer
        elif self.action == "verify_token":
            return VerifyTokenSerializer
        elif self.action in ["create", "invite_user"]:
            return CreateUserSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in [
            "create_password",
            "initialize_reset",
            "verify_token",
            "retrieve",
            "list",
        ]:
            permission_classes = [AllowAny]
        elif self.action in ["destroy", "partial_update"]:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(
        methods=["POST"],
        detail=False,
        serializer_class=CreateUserSerializer,
        permission_classes=[IsAuthenticated, IsHRAdmin],
        url_path="invite-user",
    )
    def invite_user(self, request, pk=None):
        """This endpoint invites new user by admin"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"success": True}, status=status.HTTP_200_OK)
            return Response(
                {"success": False, "errors": serializer.errors},
                status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            capture_exception(e)
            return Response({"message": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(parameters=VERIFY_TOKEN_PARAMETERS)
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=VerifyTokenSerializer,
        url_path="verify-token",
    )
    def verify_token(self, request, pk=None):
        """This endpoint verifies token"""
        try:
            token = Token.objects.filter(token=request.GET.get("token")).first()
            if token and token.is_valid():
                token.verify_user()
                token.save()
                return Response(
                    {"success": True, "valid": True}, status=status.HTTP_200_OK
                )
            return Response(
                {"success": False, "valid": False},
                status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            capture_exception(e)
            return Response({"message": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(
        methods=["POST"],
        detail=False,
        serializer_class=InitializePasswordResetSerializer,
        url_path="reset-password",
    )
    def initialize_reset(self, request, pk=None):
        """This endpoint initializes password reset by sending password reset email to user"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                email = request.data["email"].lower().strip()
                user = (
                    get_user_model().objects.filter(email=email, is_active=True).first()
                )
                if not user:
                    return Response(
                        {
                            "success": False,
                            "message": "user with this record not found",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                token, created = Token.objects.update_or_create(
                    user=user,
                    defaults={
                        "user": user,
                        "token_type": "PASSWORD_RESET",
                        "token": get_random_string(120),
                    },
                )
                email_data = {
                    "fullname": user.firstname,
                    "email": user.email,
                    "token": token.token,
                }
                send_password_reset_email.delay(email_data)
                return Response(
                    {
                        "success": True,
                        "message": "Email successfully sent to registered email",
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"success": False, "errors": serializer.errors},
                status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            capture_exception(e)
            return Response({"message": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(
        methods=["POST"],
        detail=False,
        serializer_class=CreatePasswordSerializer,
        url_path="create-password",
    )
    def create_password(self, request, pk=None):
        """Create a new password given the reset token"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                token = Token.objects.filter(
                    token=request.data["token"]).first()
                if not token or not token.is_valid():
                    return Response(
                        {"success": False, "errors": "Invalid token specified"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                token.reset_user_password(request.data["password"])
                user = token.user
                if "EMPLOYEE" in user.roles:
                    employee = Employee.objects.get(user=user)
                    employee.invitation_status = "COMPLETED"
                    employee.save()
                if "HR_ADMIN" in user.roles:
                    organisation = user.organisation
                    organisation.status = "ACTIVE"
                    organisation.save()
                token.delete()
                return Response(
                    {"success": True, "message": "Password successfully reset"},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"success": False, "errors": serializer.errors},
                status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            capture_exception(e)
            return Response({"message": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomObtainTokenPairView(TokenObtainPairView):
    """Login with email and password"""

    serializer_class = CustomObtainTokenPairSerializer


class CreateTokenView(ObtainAuthToken):
    """Create a new auth token for user"""

    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        try:
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {"token": token.key, "created": created, "roles": user.roles},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"message": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)
