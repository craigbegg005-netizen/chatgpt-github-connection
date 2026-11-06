"""Cognitive capability measurement for Oddfellow.

See `profile.py` for the instrument and the reasoning behind it. The short
version: this package measures computational behaviour -- whether state survives
a restart, whether claims match reality, whether a contradiction is detected --
and never claims consciousness, sentience, or self-awareness.
"""

from .profile import (  # noqa: F401
    Confidence,
    Context,
    Measurement,
    build_profile,
    render,
    summarise,
)
from .memory import Memory, MemoryStore  # noqa: F401

__all__ = [
    "Confidence",
    "Context",
    "Measurement",
    "build_profile",
    "render",
    "summarise",
    "Memory",
    "MemoryStore",
]
