from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, exceptions
from django.utils.crypto import get_random_string
from django.db import IntegrityError
from django.db.models import Q
from django.conf import settings
from django.core.exceptions import PermissionDenied
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from email_validator import validate_email, EmailNotValidError
from .models import Token, User
from .tasks import send_new_user_email, send_password_reset_email
from .utils import create_token_and_send_user_email
from django.contrib.auth.hashers import make_password


class ListUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "firstname",
            "lastname",
            "email",
            "roles",
            "image",
            "verified",
            "last_login",
            "created_at",
        ]


class CreateUserSerializer(serializers.ModelSerializer):
    """Serializer for user object"""

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "email",
            "password",
            "firstname",
            "lastname",
            "verified",
            "phone",
            "image",
            "roles",
            "last_login",
            "created_at",
        )
        extra_kwargs = {
            "password": {"write_only": True, "min_length": 8},
            "last_login": {"read_only": True},
            "roles": {"read_only": True},
        }

    def validate(self, attrs):
        email = attrs.get("email", None)
        if email:
            email = attrs["email"].lower().strip()
            if get_user_model().objects.filter(email=email).exists():
                raise serializers.ValidationError("Email already exists")
            try:
                #Todos:Email validator errors:Domain not register
                # valid = validate_email(attrs["email"])
                # attrs["email"] = valid.email
                return super().validate(attrs)
            except EmailNotValidError as e:
                raise serializers.ValidationError(e)
        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        user = User.objects.create_admin_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        # user = self.context['request'].user
        instance = super().update(instance, validated_data)
        if validated_data.get("password", False):
            instance.set_password(validated_data.get("password"))
            instance.save()
        return instance


class CustomObtainTokenPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        if not user.verified:
            raise exceptions.AuthenticationFailed(
                _("Account not yet verified."), code="authentication"
            )
        if user.organisation and not user.organisation.status == "ACTIVE":
            raise exceptions.AuthenticationFailed(
                _("Organisation not Active."), code="authentication"
            )
        token = super().get_token(user)
        # Add custom claims
        token.id = user.id
        token["email"] = user.email
        token["roles"] = user.roles
        if user.firstname and user.lastname:
            token["firstname"] = user.firstname
            token["lastname"] = user.lastname
        if user.organisation:
            token["organisation"] = str(user.organisation.id)
        if user.image:
            token["image"] = user.image.url
        token["phone"] = user.phone
        user.save_last_login()
        return token


class AuthTokenSerializer(serializers.Serializer):
    """Serializer for user authentication object"""

    email = serializers.CharField()
    password = serializers.CharField(
        style={"input_type": "password"}, trim_whitespace=False
    )

    def validate(self, attrs):
        """Validate and authenticate the user"""
        email = attrs.get("email")
        password = attrs.get("password")

        if email:
            user = authenticate(
                request=self.context.get("request"),
                username=email.lower().strip(),
                password=password,
            )

        if not user:
            msg = _("Unable to authenticate with provided credentials")
            raise serializers.ValidationError(msg, code="authentication")
        attrs["user"] = user
        return attrs


class VerifyTokenSerializer(serializers.Serializer):
    """Serializer for token verification"""

    token = serializers.CharField(required=True)


class InitializePasswordResetSerializer(serializers.Serializer):
    """Serializer for sending password reset email to the user"""

    email = serializers.CharField(required=True)
    subdomain = serializers.CharField(required=True)

    def validate(self, attrs):
        try:
            user = User.objects.get(email=attrs.get("email").lower().strip())
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"user": "User with this email does not exist"}
            )

        if attrs.get("subdomain").lower().strip() != user.organisation.subdomain:
            raise serializers.ValidationError(
                {"subdomain": "User not found on this subdomain"}
            )

        return attrs


class CreatePasswordSerializer(serializers.Serializer):
    """Serializer for password change on reset"""

    token = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
