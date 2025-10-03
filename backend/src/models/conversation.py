"""
Conversation and Message models for chat history.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class Conversation(Base):
    """Conversation model for chat sessions."""
    
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=True)
    language = Column(String(10), default="en")
    is_active = Column(Boolean, default=True)
    conversation_metadata = Column(JSON, nullable=True)  # Store additional conversation metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title='{self.title}')>"


class Message(Base):
    """Message model for individual chat messages."""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    content_type = Column(String(20), default="text")  # 'text', 'audio', 'image'
    
    # Audio-specific fields
    audio_file_id = Column(Integer, ForeignKey("audio_files.id"), nullable=True)
    audio_duration = Column(Integer, nullable=True)  # Duration in milliseconds
    transcription = Column(Text, nullable=True)  # Transcribed text from audio
    transcription_confidence = Column(Integer, nullable=True)  # Confidence score 0-100
    
    # AI response fields
    ai_model_used = Column(String(50), nullable=True)  # Which AI model generated the response
    ai_provider = Column(String(20), nullable=True)  # 'kong', 'ollama', 'openai'
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    
    # Metadata
    message_metadata = Column(JSON, nullable=True)  # Store additional message metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    audio_file = relationship("AudioFile", back_populates="messages")
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, role='{self.role}')>"
