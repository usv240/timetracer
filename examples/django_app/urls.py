"""
Django URL configuration for Timetracer example.
"""

from django.urls import path
from views import fetch_external, health, users_list

urlpatterns = [
    path('', health),
    path('api/users/', users_list),
    path('api/fetch-external/', fetch_external),
]
