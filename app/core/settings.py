import os
from pathlib import Path
import redis
from celery.schedules import crontab
import dj_database_url
from decouple import config
from datetime import timedelta
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY","ssdsdsd")
DEBUG = int(os.environ.get("DEBUG", 1))
DEBUG_LOCAL = int(os.environ.get("DEBUG", 1))


ALLOWED_HOSTS = ["127.0.0.1", "0.0.0.0", "localhost", "api", "api.py.hrms.prunedge.org"]
INTERNAL_IPS = ["127.0.0.1"]
if DEBUG:
    import os  # only if you haven't already imported this
    import socket  # only if you haven't already imported this

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[:-1] + "1" for ip in ips] + ["127.0.0.1", "10.0.2.2"]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Application definition

INSTALLED_APPS = [
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'storages',
    'django_filters',
    'import_export',
    'debug_toolbar',
    'drf_spectacular',
    'core.celery.CeleryConfig',
    'user',
    'organisation',
    'leave',
    'claim',
    'employee',
    'announcement',
    'notification'
]

AUTH_USER_MODEL = "user.User"

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.ValidationErrorMiddleware",
    "core.middleware.CaptureExceptionMiddleware",
]

ROOT_URLCONF = "core.urls"
IMPORT_EXPORT_USE_TRANSACTIONS = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"
CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = ["https://*.edgehrms.com", "https://*.prunedge.org"]
LOGIN_URL = "rest_framework:login"
LOGOUT_URL = "rest_framework:logout"

# Database

DATABASES = {"default": dj_database_url.config(default=config("DATABASE_URL"))}

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DATE_INPUT_FORMATS = [
    "%d/%m/%Y",
    "%d/%m/%y",  # '10/02/2020', '10/02/20'
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",  # '2006-10-25', '10/25/2006', '10/25/06'
    "%b %d %Y",
    "%b %d, %Y",  # 'Oct 25 2006', 'Oct 25, 2006'
    "%d %b %Y",
    "%d %b, %Y",  # '25 Oct 2006', '25 Oct, 2006'
    "%B %d %Y",
    "%B %d, %Y",  # 'October 25 2006', 'October 25, 2006'
    "%d %B %Y",
    "%d %B, %Y",  # '25 October 2006', '25 October, 2006'
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.CustomPagination",
    "PAGE_SIZE": 10,
    # 'DATE_INPUT_FORMATS': ["%d/%m/%Y", ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

APP_NAME = os.getenv("APP_NAME")
STATIC_ROOT = os.path.join(BASE_DIR, f"staticfiles/{APP_NAME}")
STATIC_TMP = os.path.join(BASE_DIR, f"static/{APP_NAME}")
os.makedirs(STATIC_TMP, exist_ok=True)
os.makedirs(STATIC_ROOT, exist_ok=True)

# AWS CONFIG
# to make sure all your files gives read only access to the files
STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
DEFAULT_FILE_STORAGE = "core.storage_backends.MediaStorage"
PRIVATE_MEDIA_LOCATION = "private"
PRIVATE_FILE_STORAGE = "core.storage_backends.PrivateMediaStorage"

AWS_DEFAULT_ACL = "public-read"
AWS_QUERYSTRING_AUTH = False
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME")
AWS_ACCESS_KEY_ID = os.environ.get("ACCESS_KEY_AWS")
AWS_SECRET_ACCESS_KEY = os.environ.get("ACCESS_SECRET_AWS")
AWS_STORAGE_BUCKET_NAME = os.environ.get("ACCESS_BUCKET_NAME_AWS")
AWS_S3_ENDPOINT_URL = f"https://{AWS_S3_REGION_NAME}.digitaloceanspaces.com"
AWS_S3_CUSTOM_DOMAIN = os.environ.get("AWS_S3_CUSTOM_DOMAIN")
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}
AWS_LOCATION = f"static/{APP_NAME}"
AWS_S3_SIGNATURE_VERSION = "s3v4"
STATICFILES_DIRS = [
    BASE_DIR / AWS_LOCATION,
]

STATIC_URL = "{}/{}/".format(AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
STATIC_ROOT = "static/"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs/debug.log",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}

# Email Settings
EMAIL_FROM = os.environ.get("SENDER_EMAIL")
EMAIL_HOST = os.environ.get("SMTP_HOST", "smtp.sendgrid.net")
EMAIL_HOST_USER = "apikey"  # this is exactly the value 'apikey'
EMAIL_HOST_PASSWORD = os.environ.get("SENDGRID_API_KEY")
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# SMS Settings
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", None)
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", None)
TWILIO_NUMBER = "OYO-EOC"  # os.environ.get("TWILIO_NUMBER")

CLIENT_URL = os.environ.get("CLIENT_URL")


TOKEN_LIFESPAN = 24 * 7  # hours

REDIS_URL = os.getenv("REDIS_URL", "localhost:6379")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_SERIALIZER = "json"

FLOWER_BASIC_AUTH = os.environ.get("FLOWER_BASIC_AUTH")
# Assumes that the username is swift or simple have the url as redis://swift:jetSwift@localhost:6379/0
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": os.getenv("APP_NAME"),
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

CACHE_TTL = 60 * 1
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
        # 'ROUTING': 'core'
    },
}

CELERY_BEAT_SCHEDULE = {
    # "sample_task": {
    #     "task": "user.tasks.sample_task",
    #     "schedule": crontab(minute="*/1"),
    # },
    # "send_email_report": {
    #     "task": "user.tasks.send_email_report",
    #     "schedule": crontab(hour="*/1"),
    # },
}

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
}

SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "DEFAULT_GENERATOR_CLASS": "drf_spectacular.generators.SchemaGenerator",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "COMPONENT_SPLIT_PATCH": True,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
        "displayRequestDuration": True,
    },
    "UPLOADED_FILES_USE_URL": True,
    "TITLE": "HRPay Application API",
    "DESCRIPTION": "HrPay API Doc",
    "VERSION": "1.0.0",
    "LICENCE": {"name": "BSD License"},
    "CONTACT": {"name": "Daniel Ale", "email": "daniel.ale@prunedge.com"},
    # Oauth2 related settings. used for example by django-oauth2-toolkit.
    # https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.3.md#oauth-flows-object
    "OAUTH2_FLOWS": [],
    "OAUTH2_AUTHORIZATION_URL": None,
    "OAUTH2_TOKEN_URL": None,
    "OAUTH2_REFRESH_URL": None,
    "OAUTH2_SCOPES": None,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

if DEBUG == 0:
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN", None),
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )


# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
