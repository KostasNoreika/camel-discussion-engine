"""
Database models for CAMEL Discussion API
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Discussion(Base):
    """Discussion session model"""
    __tablename__ = "discussions"

    id = Column(String, primary_key=True)
    topic = Column(Text, nullable=False)
    user_id = Column(String, nullable=False)
    status = Column(String, default="active")  # active, completed, stopped
    roles = Column(JSON, nullable=True)  # List of role definitions
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    consensus_reached = Column(Boolean, default=False)
    consensus_summary = Column(Text, nullable=True)
    consensus_confidence = Column(Float, nullable=True)

    # Relationships
    messages = relationship("Message", back_populates="discussion", cascade="all, delete-orphan")


class Message(Base):
    """Message model for discussion messages"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    discussion_id = Column(String, ForeignKey("discussions.id"), nullable=False)
    role_name = Column(String, nullable=False)  # e.g., "Neurologist", "User"
    model = Column(String, nullable=False)  # e.g., "gpt-4", "user"
    content = Column(Text, nullable=False)
    is_user = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    turn_number = Column(Integer, default=0)
    metadata = Column(JSON, nullable=True)  # Additional data (timestamps, user_id, etc.)

    # Relationships
    discussion = relationship("Discussion", back_populates="messages")


class AgentPerformance(Base):
    """Agent performance metrics for monitoring and optimization"""
    __tablename__ = "agent_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    discussion_id = Column(String, ForeignKey("discussions.id"), nullable=False)
    role_name = Column(String, nullable=False)  # Which agent
    model = Column(String, nullable=False)  # Which LLM model
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    token_count = Column(Integer, nullable=True)  # Tokens used
    cost_usd = Column(String, nullable=True)  # Cost in USD
    created_at = Column(DateTime, default=datetime.utcnow)
