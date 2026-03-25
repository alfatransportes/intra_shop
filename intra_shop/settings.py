import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

from dotenv import load_dotenv

load_dotenv()
DEBUG = os.environ.get("DEBUG") == "1"

SECRET_KEY = 'django-insecure-kuvw5sv-%fmdj9l(z1zhh$z5cg*3ii&_cm17ns*3%erl@cf)f2'
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-do-not-use-in-prod"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY não definido em produção.")
DEBUG = True

ALLOWED_HOSTS = ["api.alfatransportes.com.br", "intrashop.swem.com.br", "alfatransportes.com.br", "127.0.0.1", "localhost", "[::1]", "192.168.1.27", "192.168.1.210", "10.0.0.42"]

CSRF_TRUSTED_ORIGINS = [
    "https://api.alfatransportes.com.br",
    "https://alfatransportes.com.br",
    "https://intrashop.swem.com.br",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://192.168.1.27",
]

INSTALLED_APPS = [
    'accounts',
    'django.contrib.humanize',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'website.apps.WebsiteConfig',
    'dashboard',
    # 'website',
]


AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "index"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'intra_shop.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'website.context_processors.config_website_global',
            ],
        },
    },
]

WSGI_APPLICATION = 'intra_shop.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DATABASE_ENGINE'),
        'NAME': os.environ.get('DATABASE_NAME'),
        'USER': os.environ.get('DATABASE_USER'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD'),
        'HOST': os.environ.get('DATABASE_HOST'),
        'PORT': os.environ.get('DATABASE_PORT'),
        'CONN_MAX_AGE': int(os.environ.get("DATABASE_CONN_MAX_AGE", "0")),
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Logs
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"verbose": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "app.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "error.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["file", "error_file"], "level": "INFO"},
}

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Arquivos Staticos
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "static")

# Arquivos de Media/upload
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Email settings
SITE_URL = os.getenv("BASE_URL")
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
SERVER_EMAIL = os.getenv("SERVER_EMAIL")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_HOST_PORT = os.getenv("EMAIL_HOST_PORT")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS")
LEADS_TO_EMAIL = os.getenv("LEADS_TO_EMAIL")