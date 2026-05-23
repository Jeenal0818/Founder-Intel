# app/models.py
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, BigInteger, Enum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .db import Base
import enum


class RunType(str, enum.Enum):
    weekly = "weekly"
    daily_critical = "daily_critical"


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True)  # company_id
    name = Column(String, nullable=False)
    competitors = Column(JSONB, nullable=False)       # list[str]
    founders_emails = Column(JSONB, nullable=False)   # list[str]
    market_keywords = Column(JSONB, nullable=False)   # list[str]
    strategy_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class MonitoringRun(Base):
    __tablename__ = "monitoring_runs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_id = Column(String, ForeignKey("companies.id"), index=True, nullable=False)
    run_type = Column(Enum(RunType), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    brief = Column(Text, nullable=True)
    events = Column(JSONB, nullable=False, default=list)
    critical_events = Column(JSONB, nullable=False, default=list)
    weekly_events = Column(JSONB, nullable=False, default=list)
    recommendations = Column(Text, nullable=True)
