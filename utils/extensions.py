"""
utils/extensions.py
====================
Holds every Flask extension instance as a module-level singleton.

Why this file exists:
    Flask extensions (SQLAlchemy, Mail, etc.) need to be instantiated
    *before* the application factory runs, but the actual binding to the
    Flask ``app`` object happens later via ``extension.init_app(app)``.
    Keeping the instances here (instead of inside app.py or models/) avoids
    circular imports between app.py, models/*, and routes/*.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate

# Single shared SQLAlchemy instance used by every model in models/
db = SQLAlchemy()

# Handles schema migrations (flask db init / migrate / upgrade)
migrate = Migrate()

# Optional email notifications (attendance summaries, alerts, etc.)
mail = Mail()
