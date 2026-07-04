"""Datetime helpers for TyPySetup."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC time as a naive ``datetime``.

    Drop-in replacement for the deprecated ``datetime.utcnow()`` (removed in
    future Python versions). Returns a naive datetime in UTC so the existing
    on-disk serialization format (ISO 8601 + ``Z`` suffix) is preserved and no
    offset-aware/naive comparison issues are introduced across stored history.
    """
    return datetime.now(UTC).replace(tzinfo=None)
