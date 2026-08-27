from datetime import datetime
import uuid
from sqlalchemy import Column, DateTime, String, Boolean, Text
from sqlalchemy.orm import relationship
from database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    # UUID strings are 36 characters long
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel = Column(String(50), nullable=False)
    customer_id = Column(String(255), nullable=True, index=True)
    customer_email = Column(String(255), nullable=True)
    raw_subject = Column(String(255), nullable=True)
    raw_body = Column(Text, nullable=False)
    sanitized_body = Column(Text, nullable=False)
    pii_flagged = Column(Boolean, default=False, nullable=False)
    injection_flagged = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    classifications = relationship("Classification", back_populates="ticket")
    assignments = relationship("Assignment", back_populates="ticket")