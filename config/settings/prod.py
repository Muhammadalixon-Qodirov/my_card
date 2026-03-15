import os
from .base import *
from decouple import config


DEBUG = False

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
    }
}

# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

CORS_ALLOW_ALL_ORIGINS = True
# CORS_ALLOWED_ORIGINS = [
#     "https://example.com",
#     "https://www.example.com",
#     "https://app.example.com",
# ]
CSRF_TRUSTED_ALL_ORIGINS = True
# CSRF_TRUSTED_ORIGINS = [
#     "https://example.com",
#     "https://app.example.com",
# ]

# SECURE_SSL_REDIRECT = True

# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

# X_FRAME_OPTIONS = "DENY"

# SECURE_CONTENT_TYPE_NOSNIFF = True
# SECURE_BROWSER_XSS_FILTER = True
