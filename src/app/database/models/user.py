import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class PremiumPlanType(str, enum.Enum):
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"
    PROFESSIONAL = "PROFESSIONAL"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    password = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)
    profile_image = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    premium_plan = Column(
        Enum(PremiumPlanType), default=PremiumPlanType.BASIC, nullable=False
    )

    # Add Stripe-related fields
    stripe_customer_id = Column(String, unique=True, nullable=True)
    stripe_subscription_id = Column(String, unique=True, nullable=True)
    subscription_status = Column(String, nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)
    stripe_session_id = Column(String, unique=True, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=True)
    # The "folder" relationship
    folders = relationship("Folder", back_populates="user")

    # The "agent" relationship
    # agents = relationship("Agent", back_populates="user")

    web_search_history = relationship("UserWebSearchHistory", back_populates="user")

    # The "application_limit" relationship
    application_limit = relationship(
        "ApplicationLimit",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
