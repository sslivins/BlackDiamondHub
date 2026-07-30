"""
Test-only settings override: run the Django test suite against an in-memory
SQLite database so tests don't require a live PostgreSQL server.

Usage:
    python manage.py test vacation_mode --settings=BlackDiamondHub.settings_test
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
