"""Basic HTTP authentication for the dashboard."""

import os
from functools import wraps
from typing import Callable

from flask import Response, request


def check_auth(username: str, password: str) -> bool:
    """Check credentials against env vars."""
    expected_user = os.getenv("DASHBOARD_USERNAME", "admin")
    expected_pass = os.getenv("DASHBOARD_PASSWORD", "changeme")
    return username == expected_user and password == expected_pass


def authenticate() -> Response:
    """Send 401 Basic Auth challenge."""
    return Response(
        "Authentication required",
        401,
        {"WWW-Authenticate": 'Basic realm="Clipper Agency"'},
    )


def requires_auth(f: Callable) -> Callable:
    """Decorator to require basic auth."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated
