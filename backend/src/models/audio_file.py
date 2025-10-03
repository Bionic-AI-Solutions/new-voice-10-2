"""
Audio file model for storing uploaded and generated audio files.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class AudioFile(Base):
    """Audio file model for storing uploaded and generated audio files."""
    
    __tablename__ = "audio_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # File size in bytes
    mime_type = Column(String(100), nullable=False)
    duration = Column(Integer, nullable=True)  # Duration in milliseconds
    sample_rate = Column(Integer, nullable=True)
    channels = Column(Integer, nullable=True)
    bit_depth = Column(Integer, nullable=True)
    
    # File type and purpose
    file_type = Column(String(20), nullable=False)  # 'upload', 'tts_response', 'transcription'
    purpose = Column(String(50), nullable=True)  # 'user_input', 'bot_response', 'transcription'
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(20), default="pending")  # 'pending', 'processing', 'completed', 'failed'
    processing_error = Column(Text, nullable=True)
    
    # Transcription fields (if applicable)
    transcription = Column(Text, nullable=True)
    transcription_confidence = Column(Integer, nullable=True)  # Confidence score 0-100
    language_detected = Column(String(10), nullable=True)
    
    # TTS fields (if applicable)
    tts_provider = Column(String(20), nullable=True)  # 'speechmatics', 'local', 'elevenlabs'
    tts_voice = Column(String(50), nullable=True)
    tts_text = Column(Text, nullable=True)  # Original text that was converted to speech
    
    # Metadata
    file_metadata = Column(Text, nullable=True)  # JSON string for additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # For temporary files
    
    # Relationships
    messages = relationship("Message", back_populates="audio_file")
    
    def __repr__(self) -> str:
        return f"<AudioFile(id={self.id}, filename='{self.filename}', file_type='{self.file_type}')>"
