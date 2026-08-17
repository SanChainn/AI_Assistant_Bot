"""
SQLAlchemy models package.

All models must be imported here so that Base.metadata and Alembic
can discover them for migrations.
"""

from app.models.base import Base
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message

__all__ = ["Base", "User", "Chat", "Message"]