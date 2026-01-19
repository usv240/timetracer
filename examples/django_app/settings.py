"""
Simple Django settings for Timetracer example.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = 'django-insecure-timetracer-example-key'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
]

MIDDLEWARE = [
    'timetracer.integrations.django.TimeTracerMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Timetracer configuration
TIMETRACER = {
    'MODE': os.environ.get('TIMETRACER_MODE', 'off'),
    'CASSETTE_DIR': os.environ.get('TIMETRACER_DIR', './cassettes'),
    'CASSETTE_PATH': os.environ.get('TIMETRACER_CASSETTE'),
    'EXCLUDE_PATHS': ['/admin/', '/static/'],
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
