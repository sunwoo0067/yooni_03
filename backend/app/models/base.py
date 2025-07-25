"""
Base model with common fields and functionality
"""
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, Column, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

Base = declarative_base()


class TimestampMixin:
    """Mixin for adding timestamp fields"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    
    def soft_delete(self):
        """Mark record as deleted"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """Restore soft deleted record"""
        self.is_deleted = False
        self.deleted_at = None


class UUIDMixin:
    """Mixin for UUID primary key"""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)


class MetadataMixin:
    """Mixin for flexible metadata storage"""
    metadata = Column(JSONB, nullable=True)
    
    def set_metadata(self, key: str, value: Any):
        """Set a metadata field"""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None):
        """Get a metadata field"""
        if self.metadata is None:
            return default
        return self.metadata.get(key, default)


class BaseModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, MetadataMixin):
    """Base model with all common functionality"""
    __abstract__ = True
    
    notes = Column(Text, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"