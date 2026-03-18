from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)        # lesson | worksheet | scheme | slides
    title = Column(String(255), nullable=False)
    subject = Column(String(100), nullable=False)
    key_stage = Column(String(20), nullable=False)
    topic = Column(String(255), nullable=False)
    input_prompt = Column(Text, nullable=False)
    structured_output = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
