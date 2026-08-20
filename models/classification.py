import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)

    category = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    sentiment = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)

    prompt_version = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    is_fallback = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="classifications")
    assignment = relationship("Assignment", back_populates="classification", uselist=False)