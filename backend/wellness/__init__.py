"""Week 5-6 (Track A, Option A2): Medication & Wellness Tracker.

This package is purely additive.  It reuses the existing SQLite database and
tables (medications, dose_log, health_metrics, fitness_activities) and adds
its own tables.  The service modules here do not import FastAPI, so they can
be tested on their own; ``backend.wellness.router`` is the thin HTTP layer.
"""
