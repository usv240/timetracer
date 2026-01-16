"""
Cassette naming utilities.

Provides consistent naming for cassette files and directories.
"""

import re
from datetime import datetime, timezone


def sanitize_route(route: str) -> str:
    """
    Convert a route template to a filesystem-safe string.

    Examples:
        /checkout -> checkout
        /users/{id} -> users_id
        /v1/payments/confirm -> v1_payments_confirm
        /api/v2/orders/{order_id}/items -> api_v2_orders_order_id_items
    """
    # Remove leading/trailing slashes
    route = route.strip("/")

    # Replace path parameters like {id} with their name
    route = re.sub(r"\{(\w+)\}", r"\1", route)

    # Replace non-alphanumeric with underscore
    route = re.sub(r"[^a-zA-Z0-9]", "_", route)

    # Collapse multiple underscores
    route = re.sub(r"_+", "_", route)

    # Remove leading/trailing underscores
    route = route.strip("_")

    # Handle empty result
    if not route:
        route = "root"

    return route.lower()


def cassette_filename(
    method: str,
    route_template: str,
    session_id: str,
    extension: str = "json"
) -> str:
    """
    Generate a standardized cassette filename.

    Format: {METHOD}__{sanitized_route}__{short_id}.{extension}

    Example:
        POST /checkout abc123... -> POST__checkout__abc123.json
    """
    sanitized = sanitize_route(route_template or "unknown")
    short_id = session_id[:8] if session_id else "unknown"

    return f"{method.upper()}__{sanitized}__{short_id}.{extension}"


def get_date_directory() -> str:
    """
    Get the date-based subdirectory name for today.

    Format: YYYY-MM-DD
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
