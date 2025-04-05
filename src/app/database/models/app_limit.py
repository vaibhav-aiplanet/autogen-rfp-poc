import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ApplicationLimit(Base):
    __tablename__ = "application_limit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    userid = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    max_folder = Column(Integer, nullable=False, default=3)
    max_file = Column(Integer, nullable=False, default=3)
    max_agent = Column(Integer, nullable=False, default=3)
    max_tokens = Column(Integer, nullable=False, default=10000)
    tokens_left = Column(Integer, default=10000)  # Default token balance
    last_token_reset = Column(DateTime, default=datetime.utcnow)

    # Relationship with User
    user = relationship("User", back_populates="application_limit")
