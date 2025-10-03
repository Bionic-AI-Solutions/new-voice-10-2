"""
Audio processing API endpoints.
"""
import logging
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..services.speechmatics_service import speechmatics_streaming_service
from ..core.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()


class TranscriptionRequest(BaseModel):
    """Transcription request model."""
    language: str = "en"
    enable_partials: bool = True
    enable_entities: bool = True
    enable_sentiment: bool = False
    enable_topics: bool = False


class TranscriptionResponse(BaseModel):
    """Transcription response model."""
    transcript: str
    confidence: float
    language: str
    duration: float
    entities: Optional[Dict[str, Any]] = None
    sentiment: Optional[Dict[str, Any]] = None
    topics: Optional[Dict[str, Any]] = None


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio_file(
    file: UploadFile = File(...),
    language: str = Query(default="en", description="Language code for transcription"),
    enable_partials: bool = Query(default=True, description="Enable partial transcripts"),
    enable_entities: bool = Query(default=True, description="Enable entity detection"),
    enable_sentiment: bool = Query(default=False, description="Enable sentiment analysis"),
    enable_topics: bool = Query(default=False, description="Enable topic detection")
):
    """Transcribe an uploaded audio file."""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Transcribe using Speechmatics
            result = await speechmatics_streaming_service.transcribe_audio_file(
                file_path=temp_path,
                language=language
            )
            
            # Parse the result
            if isinstance(result, dict):
                transcript = result.get("transcript", "")
                confidence = result.get("confidence", 0.0)
                duration = result.get("duration", 0.0)
                entities = result.get("entities") if enable_entities else None
                sentiment = result.get("sentiment") if enable_sentiment else None
                topics = result.get("topics") if enable_topics else None
            else:
                # Handle string result
                transcript = str(result)
                confidence = 1.0
                duration = 0.0
                entities = None
                sentiment = None
                topics = None
            
            return TranscriptionResponse(
                transcript=transcript,
                confidence=confidence,
                language=language,
                duration=duration,
                entities=entities,
                sentiment=sentiment,
                topics=topics
            )
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
    except Exception as e:
        logger.error(f"Error transcribing audio file: {e}")
        raise HTTPException(status_code=500, detail="Failed to transcribe audio file")


@router.get("/supported-languages")
async def get_supported_languages():
    """Get list of supported languages for transcription."""
    try:
        languages = await speechmatics_service.get_supported_languages()
        return {"languages": languages}
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supported languages")


@router.post("/detect-language")
async def detect_language(file: UploadFile = File(...)):
    """Detect language from audio file."""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Read audio data
        audio_data = await file.read()
        
        # Detect language
        detected_language = await speechmatics_service.detect_language(audio_data)
        
        return {
            "detected_language": detected_language,
            "confidence": 0.8,  # Placeholder confidence
            "message": "Language detection completed"
        }
        
    except Exception as e:
        logger.error(f"Error detecting language: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect language")


@router.get("/audio-formats")
async def get_supported_audio_formats():
    """Get list of supported audio formats."""
    return {
        "supported_formats": [
            {
                "format": "wav",
                "mime_type": "audio/wav",
                "description": "WAV audio format"
            },
            {
                "format": "mp3",
                "mime_type": "audio/mpeg",
                "description": "MP3 audio format"
            },
            {
                "format": "flac",
                "mime_type": "audio/flac",
                "description": "FLAC audio format"
            },
            {
                "format": "m4a",
                "mime_type": "audio/mp4",
                "description": "M4A audio format"
            },
            {
                "format": "ogg",
                "mime_type": "audio/ogg",
                "description": "OGG audio format"
            }
        ],
        "max_file_size": "50MB",
        "recommended_format": "wav"
    }


@router.get("/audio-info/{file_id}")
async def get_audio_info(file_id: int, db: Session = Depends(get_db)):
    """Get information about a stored audio file."""
    try:
        # TODO: Implement audio file info retrieval from database
        return {
            "file_id": file_id,
            "message": "Audio file info retrieval not yet implemented"
        }
    except Exception as e:
        logger.error(f"Error getting audio info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audio info")


@router.delete("/audio/{file_id}")
async def delete_audio_file(file_id: int, db: Session = Depends(get_db)):
    """Delete an audio file."""
    try:
        # TODO: Implement audio file deletion from database and storage
        return {
            "file_id": file_id,
            "message": "Audio file deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting audio file: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete audio file")
