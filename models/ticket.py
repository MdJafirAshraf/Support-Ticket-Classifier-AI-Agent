import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    channel = Column(String, nullable=False)
    raw_subject = Column(String, nullable=True)
    raw_body = Column(Text, nullable=False)
    sanitized_body = Column(Text, nullable=False)
    customer_email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    classifications = relationship("Classification", back_populates="ticket")
    assignments = relationship("Assignment", back_populates="ticket")