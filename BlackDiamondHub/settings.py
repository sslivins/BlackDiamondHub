"""
Django settings for BlackDiamondHub project.

Generated by 'django-admin startproject' using Django 5.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-*-@iek83wyv#jk^*h_wnxj93&hn#%==cqoyfey17r_b6jy43$r'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["192.168.1.162", "homehub-backend.mi"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'daphne',
    'django.contrib.staticfiles',
    'channels',
    'social_django',
    'django_tables2',
    'crispy_forms',
    'crispy_bootstrap5',
    'inventory',
    'sunpeaks_webcams',
    'feedback',
    'sonos_control',
]

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
ASGI_APPLICATION = 'BlackDiamondHub.asgi.application'
WSGI_APPLICATION = 'BlackDiamondHub.wsgi.application'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'BlackDiamondHub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'feedback.context_processors.unread_feedback_count',
                'sonos_control.context_processors.spotify_token',
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = (
    'social_core.backends.spotify.SpotifyOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

# SOCIAL_AUTH_PIPELINE = (
#     'social_core.pipeline.social_auth.social_details',
#     'sonos_control.pipeline.custom_redirect',  # Add this step to handle the next parameter
#     # other pipeline steps...
# )

SOCIAL_AUTH_DISCONNECT_PIPELINE = (
    'sonos_control.pipeline.custom_allowed_to_disconnect',
    'social_core.pipeline.disconnect.get_entries',    
    'social_core.pipeline.disconnect.revoke_tokens',
    'social_core.pipeline.disconnect.disconnect',
    'sonos_control.pipeline.clear_session_and_logout',
)


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'sunpeaks_inventory',
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': '5432',
    }
}



# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

########################
# Social Auth Settings #
########################
SOCIAL_AUTH_AUTHENTICATION_BACKENDS = (
    'social_core.backends.spotify.SpotifyOAuth2',
)

SOCIAL_AUTH_SPOTIFY_EXTRA_DATA = [
    ('access_token', 'access_token'),
    ('refresh_token', 'refresh_token'),
    ('token_type', 'token_type'),
    ('expires_in', 'expires_in'), 
    ('id', 'id'),
    ('email', 'email'),
]

SOCIAL_AUTH_STRATEGY = "social_django.strategy.DjangoStrategy"
SOCIAL_AUTH_STORAGE = "social_django.models.DjangoStorage"

SOCIAL_AUTH_JSONFIELD_ENABLED = True
SOCIAL_AUTH_DEBUG = True
SOCIAL_AUTH_REVOKE_TOKENS_ON_DISCONNECT = True
SOCIAL_AUTH_REFRESH_TOKENS = True
SOCIAL_AUTH_SESSION_EXPIRATION = True

# social auth for spotify settings
SOCIAL_AUTH_SPOTIFY_KEY =  os.getenv('SPOTIFY_CLIENT_ID')
SOCIAL_AUTH_SPOTIFY_SECRET =  os.getenv('SPOTIFY_CLIENT_SECRET')
SOCIAL_AUTH_SPOTIFY_REDIRECT_URI = 'http://192.168.1.162:8080/auth/complete/spotify/'
SOCIAL_AUTH_SPOTIFY_SCOPE = ['user-read-email', 'user-read-private', 'user-read-recently-played', 'user-library-read']

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = 'http://192.168.1.162:8080/sonos_control/spotify/auth/callback/'
SPOTIFY_SCOPE= ['user-read-recently-played', 'user-top-read', 'user-library-read']
