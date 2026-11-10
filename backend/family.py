"""Deprecated legacy placeholder.

The active, authenticated family-monitoring implementation lives in
``backend.wellness.family`` and its API routes are registered by
``backend.wellness.router`` from ``backend.main``.

This module is intentionally not an API router. Do not mount it; doing so
would bypass the consent and per-category sharing workflow.
"""
