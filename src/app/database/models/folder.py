import uuid

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, String,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.utils import utc_now
from app.database import Base


class Folder(Base):
    __tablename__ = "folder"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True, nullable=False, unique=True)
    userid = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    is_deleted = Column(Boolean, default=False)

    # Relationship with User
    user = relationship("User", back_populates="folders")

    # Relationship with other tables
    files = relationship("File", back_populates="folder")
    agents = relationship("Agent", back_populates="folder")
    __table_args__ = (
        UniqueConstraint("name", "userid", "is_deleted", name="uq_folder_name_user"),
    )
