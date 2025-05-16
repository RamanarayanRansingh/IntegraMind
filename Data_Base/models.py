from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    therapist_email = Column(String, nullable=True)
    consent_level = Column(String, default="basic")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    assessments = relationship("Assessment", back_populates="user")
    crisis_events = relationship("CrisisEvent", back_populates="user")
    conversation_histories = relationship("ConversationHistory", back_populates="user")


class Assessment(Base):
    __tablename__ = "assessments"

    assessment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    assessment_type = Column(String, nullable=False)  # e.g., "phq9", "gad7","cage","dast10"
    total_score = Column(Integer, nullable=False)
    item_scores = Column(JSON, nullable=True)  # Store individual question responses as list
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="assessments")


class CrisisEvent(Base):
    __tablename__ = "crisis_events"

    event_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    risk_level = Column(String, nullable=False)  # "low", "moderate", "high", "imminent"
    description = Column(Text, nullable=True)
    action_taken = Column(Text, nullable=True)  # e.g., "therapist_notified", "resources_provided"
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="crisis_events")


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    thread_id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    messages = Column(JSON, nullable=False, default=list)
    summary = Column(Text, nullable=False)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    pending_approval = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="conversation_histories")
