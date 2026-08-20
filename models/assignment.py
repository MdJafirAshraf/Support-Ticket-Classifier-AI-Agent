import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)
    classification_id = Column(String(36), ForeignKey("classifications.id"), nullable=False)

    assigned_team = Column(String(100), nullable=False)
    status = Column(String(20), default="pending")          # pending | in_progress | resolved
    assigned_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="assignments")
    classification = relationship("Classification", back_populates="assignment")