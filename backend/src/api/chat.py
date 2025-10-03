"""
Chat API endpoints for text and voice interactions.
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel

from ..services.ai_chatbot_service import ai_chatbot_service
from ..services.tts_service import tts_service
from ..core.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model."""
    message: str
    language: str = "en"
    conversation_id: Optional[int] = None
    generate_tts: bool = False


class ChatResponse(BaseModel):
    """Chat response model."""
    content: str
    provider: str
    model: str
    response_time_ms: int
    tokens_used: int
    metadata: Dict[str, Any]


class TTSRequest(BaseModel):
    """Text-to-speech request model."""
    text: str
    language: str = "en"
    voice: Optional[str] = None
    speed: Optional[float] = None
    pitch: Optional[float] = None


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    chat_message: ChatMessage,
    db: Session = Depends(get_db)
):
    """Send a text message and get AI response."""
    try:
        # TODO: Load conversation history from database
        conversation_history = []
        
        # Generate AI response
        response = await ai_chatbot_service.generate_response(
            message=chat_message.message,
            conversation_history=conversation_history,
            language=chat_message.language,
            user_id=None  # TODO: Get from authentication
        )
        
        # TODO: Save message and response to database
        
        return ChatResponse(
            content=response["content"],
            provider=response["provider"],
            model=response["model"],
            response_time_ms=response["response_time_ms"],
            tokens_used=response["tokens_used"],
            metadata=response["metadata"]
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")


@router.post("/tts")
async def generate_speech(tts_request: TTSRequest):
    """Generate speech from text."""
    try:
        result = await tts_service.generate_speech(
            text=tts_request.text,
            language=tts_request.language,
            voice=tts_request.voice,
            speed=tts_request.speed,
            pitch=tts_request.pitch
        )
        
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Convert audio data to base64 for JSON response
        import base64
        audio_b64 = base64.b64encode(result["audio_data"]).decode()
        
        return {
            "audio_data": audio_b64,
            "format": result["format"],
            "sample_rate": result["sample_rate"],
            "channels": result["channels"],
            "duration": result["duration"],
            "provider": result["provider"]
        }
        
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate speech")


@router.get("/models")
async def get_available_models():
    """Get available AI models from all providers."""
    try:
        models = await ai_chatbot_service.get_available_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available models")


@router.get("/voices")
async def get_available_voices(language: str = "en"):
    """Get available TTS voices."""
    try:
        voices = await tts_service.get_available_voices(language)
        return {"voices": voices}
    except Exception as e:
        logger.error(f"Error getting available voices: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available voices")


@router.get("/languages")
async def get_supported_languages():
    """Get supported languages for TTS."""
    try:
        languages = await tts_service.get_supported_languages()
        return {"languages": languages}
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supported languages")


@router.post("/upload-audio")
async def upload_audio_file(
    file: UploadFile = File(...),
    language: str = "en"
):
    """Upload audio file for transcription."""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # TODO: Save file and process with Speechmatics
        # For now, just return a placeholder response
        return {
            "message": "Audio file uploaded successfully",
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file.size,
            "language": language
        }
        
    except Exception as e:
        logger.error(f"Error uploading audio file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload audio file")
