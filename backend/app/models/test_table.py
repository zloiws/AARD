"""
Test table used for verifying Alembic migrations.
"""
from app.core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, func


class TestTable(Base):
    """A small test table to validate migrations."""

    __tablename__ = "test_table"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


