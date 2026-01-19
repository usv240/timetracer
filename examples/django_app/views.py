"""
Django views demonstrating Timetracer integration.
"""

import requests
from django.http import JsonResponse

# Enable plugins at module level
from timetracer.integrations.django import auto_setup

auto_setup(plugins=['requests'])


def health(request):
    """Simple health check."""
    return JsonResponse({'status': 'ok', 'framework': 'django'})


def users_list(request):
    """Return a list of users (mock data)."""
    users = [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'},
        {'id': 3, 'name': 'Charlie'},
    ]
    return JsonResponse({'users': users})


def fetch_external(request):
    """
    Fetch data from external API.

    In record mode: The requests call is captured.
    In replay mode: The call is mocked using the recorded response.
    """
    # This HTTP call will be captured by Timetracer
    response = requests.get('https://httpbin.org/json')
    data = response.json()

    return JsonResponse({
        'status': 'success',
        'external_data': data,
    })
