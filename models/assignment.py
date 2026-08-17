import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False)
    classification_id = Column(String, ForeignKey("classifications.id"), nullable=False)

    assigned_team = Column(String, nullable=False)
    status = Column(String, default="pending")          # pending | in_progress | resolved
    assigned_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="assignments")
    classification = relationship("Classification", back_populates="assignment")