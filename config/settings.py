import os
import sys

from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    return [value.strip() for value in os.getenv(name, default).split(',') if value.strip()]


DEBUG = env_bool('DEBUG', True)
IS_TESTING = 'test' in sys.argv
DISABLE_AUTH_FOR_LOCAL_DEV = env_bool('DISABLE_AUTH_FOR_LOCAL_DEV', False)
LOCAL_DEV_AUTH_EMAIL = os.getenv('LOCAL_DEV_AUTH_EMAIL', '')
SECRET_KEY = os.getenv('SECRET_KEY')

if not SECRET_KEY and DEBUG:
    SECRET_KEY = 'django-insecure-local-syncora-development-key'
elif not SECRET_KEY:
    raise RuntimeError('SECRET_KEY must be set when DEBUG is False.')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS')
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
elif not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError('ALLOWED_HOSTS must be set when DEBUG is False.')

CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')


# Application definition

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'channels',
    'apps.core.apps.CoreConfig',
    'apps.accounts',
    'apps.organizations',
    'apps.branches',
    'apps.products',
    'apps.inventory',
    'apps.suppliers',
    'apps.purchases',
    'apps.customers',
    'apps.sales',
    'apps.expenses',
    'apps.finance',
    'apps.notifications',
    'apps.reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'apps.core.middleware.RequestLoggingMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'syncora'),
        'USER': os.getenv('DB_USER', 'syncora_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '60' if not DEBUG else '0')),
        'OPTIONS': {
            key: value
            for key, value in {
                'sslmode': os.getenv('DB_SSLMODE', ''),
            }.items()
            if value
        },
    }
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=20),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}

AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.core.authentication.LocalDevAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'auth': '10/minute',
        'reports': '120/minute',
    },
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'apps.core.exceptions.api_exception_handler',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Syncora API',
    'DESCRIPTION': (
        'Real-time multi-tenant business management API for organizations, branches, inventory, '
        'purchasing, sales, payments, expenses, analytics, notifications, and audit logging.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
    },
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': [
        {'name': 'Authentication'},
        {'name': 'Organizations'},
        {'name': 'Branches'},
        {'name': 'Products'},
        {'name': 'Inventory'},
        {'name': 'Suppliers'},
        {'name': 'Purchases'},
        {'name': 'Customers'},
        {'name': 'Sales'},
        {'name': 'Expenses'},
        {'name': 'Finance'},
        {'name': 'Notifications'},
        {'name': 'Reports'},
    ],
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'default': {
        'BACKEND': os.getenv('DEFAULT_FILE_STORAGE', 'django.core.files.storage.FileSystemStorage'),
    },
    'staticfiles': {
        'BACKEND': os.getenv(
            'STATICFILES_STORAGE',
            (
                'django.contrib.staticfiles.storage.StaticFilesStorage'
                if DEBUG or IS_TESTING
                else 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
            ),
        ),
    },
}

SECURE_SSL_REDIRECT = False if IS_TESTING else env_bool('SECURE_SSL_REDIRECT', not DEBUG)
SESSION_COOKIE_SECURE = False if IS_TESTING else env_bool('SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = False if IS_TESTING else env_bool('CSRF_COOKIE_SECURE', not DEBUG)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', not DEBUG)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', False)
SECURE_CONTENT_TYPE_NOSNIFF = env_bool('SECURE_CONTENT_TYPE_NOSNIFF', True)
SECURE_REFERRER_POLICY = os.getenv('SECURE_REFERRER_POLICY', 'same-origin')
X_FRAME_OPTIONS = os.getenv('X_FRAME_OPTIONS', 'DENY')
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')


# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

MAILERS = {
    'default': {
        'BACKEND': os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'),
        'HOST': os.getenv('EMAIL_HOST', ''),
        'PORT': int(os.getenv('EMAIL_PORT', '587')),
        'USERNAME': os.getenv('EMAIL_HOST_USER', ''),
        'PASSWORD': os.getenv('EMAIL_HOST_PASSWORD', ''),
        'USE_TLS': env_bool('EMAIL_USE_TLS', True),
        'USE_SSL': env_bool('EMAIL_USE_SSL', False),
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s request_id=%(request_id)s user_id=%(user_id)s status=%(status_code)s duration_ms=%(duration_ms)s',
        },
        'standard': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'filters': {
        'request_defaults': {
            '()': 'apps.core.logging.RequestLogDefaultsFilter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'request_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
            'filters': ['request_defaults'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'syncora.requests': {
            'handlers': ['request_console'],
            'level': os.getenv('SYNCORA_REQUEST_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'syncora.events': {
            'handlers': ['console'],
            'level': os.getenv('SYNCORA_EVENT_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'syncora.security': {
            'handlers': ['console'],
            'level': os.getenv('SYNCORA_SECURITY_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}
