from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    school = Column(String(255), nullable=False)
    key_stages = Column(Text, nullable=False, default="[]")  # JSON array
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="teacher")  # admin | teacher
    is_school_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type = Column(String(50), nullable=False)        # lesson | worksheet | scheme | slides
    title = Column(String(255), nullable=False)
    subject = Column(String(100), nullable=False)
    key_stage = Column(String(20), nullable=False)
    topic = Column(String(255), nullable=False)
    input_prompt = Column(Text, nullable=False)
    structured_output = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    versions = relationship(
        "ResourceVersion",
        back_populates="resource",
        cascade="all, delete-orphan",
        order_by="ResourceVersion.created_at.desc()",
    )


class ResourceVersion(Base):
    __tablename__ = "resource_versions"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    structured_output = Column(Text, nullable=False)
    title = Column(String(255), nullable=True)
    label = Column(String(100), nullable=False, default="Auto-save")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resource = relationship("Resource", back_populates="versions")
