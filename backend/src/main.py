"""
Main FastAPI application for the voice-enabled chatbot.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import websockets
from websockets.server import WebSocketServerProtocol

from .core.config import settings
from .core.database import init_db, close_db
from .services.speechmatics_service import streaming_websocket_handler
from .services.flow_voice_service import FlowVoiceService
from .websocket.flow_websocket_handler import FlowWebSocketHandler
from .services.ai_chatbot_service import ai_chatbot_service
from .services.tts_service import tts_service
from .api import router as api_router
from .websocket.manager import WebSocketManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting voice chatbot application...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize WebSocket manager
    app.state.websocket_manager = WebSocketManager()
    logger.info("WebSocket manager initialized")
    
    # Initialize Flow Voice service
    app.state.flow_voice_service = FlowVoiceService(
        api_key=settings.speechmatics_api_key,
        region=settings.speechmatics_region
    )
    app.state.flow_websocket_handler = FlowWebSocketHandler(app.state.flow_voice_service)
    logger.info("Flow Voice service initialized")
    
    # WebSocket endpoints are handled by FastAPI directly
    logger.info("WebSocket endpoints ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down voice chatbot application...")
    
    # Close database connections
    await close_db()
    logger.info("Database connections closed")
    
    # Close AI service
    await ai_chatbot_service.close()
    logger.info("AI chatbot service closed")


# Create FastAPI application
app = FastAPI(
    title="Voice-Enabled Chatbot API",
    description="A comprehensive voice-enabled chatbot with real-time transcription, AI responses, and text-to-speech",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"]
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Voice-Enabled Chatbot API",
        "version": settings.app_version,
        "status": "running",
        "features": {
            "voice_chat": settings.feature_voice_chat,
            "file_upload": settings.feature_file_upload,
            "conversation_history": settings.feature_conversation_history,
            "multi_language": settings.feature_multi_language,
            "voice_activity_detection": settings.feature_voice_activity_detection,
            "real_time_transcription": settings.feature_real_time_transcription,
            "text_to_speech": settings.feature_text_to_speech,
            "ai_fallback": settings.feature_ai_fallback,
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "version": settings.app_version
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check database connection
        from .core.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        # Check Redis connection
        from .core.database import get_redis
        redis_client = await get_redis()
        await redis_client.ping()
        
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@app.websocket("/ws/transcription/{session_id}")
async def websocket_transcription_endpoint(
    websocket: WebSocket,
    session_id: str,
    language: str = "en"
):
    """WebSocket endpoint for real-time transcription."""
    await websocket.accept()
    
    try:
        await speechmatics_websocket_handler.handle_websocket_connection(
            websocket, session_id, language
        )
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.close(code=1011, reason="Internal server error")


# Removed duplicate WebSocket endpoint - using streaming handler below


async def handle_chat_message(websocket: WebSocket, user_id: str, data: Dict[str, Any]):
    """Handle text chat message."""
    try:
        message = data.get("message", "")
        language = data.get("language", "en")
        
        if not message:
            await websocket.send_json({
                "type": "error",
                "message": "Empty message"
            })
            return
        
        # Generate AI response
        response = await ai_chatbot_service.generate_response(
            message=message,
            conversation_history=[],  # TODO: Load from database
            language=language,
            user_id=int(user_id) if user_id.isdigit() else None
        )
        
        # Send response back to client
        await websocket.send_json({
            "type": "ai_response",
            "content": response["content"],
            "provider": response["provider"],
            "model": response["model"],
            "response_time_ms": response["response_time_ms"]
        })
        
        # Generate TTS if requested
        if data.get("generate_tts", False):
            tts_result = await tts_service.generate_speech(
                text=response["content"],
                language=language
            )
            
            if tts_result.get("audio_data"):
                import base64
                audio_b64 = base64.b64encode(tts_result["audio_data"]).decode()
                
                await websocket.send_json({
                    "type": "tts_audio",
                    "audio_data": audio_b64,
                    "format": tts_result["format"],
                    "sample_rate": tts_result["sample_rate"],
                    "duration": tts_result["duration"]
                })
        
    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Failed to process message"
        })


async def handle_voice_message(websocket: WebSocket, user_id: str, data: Dict[str, Any]):
    """Handle voice message (transcription + AI response)."""
    try:
        # This would integrate with the transcription service
        # For now, we'll just acknowledge the message
        await websocket.send_json({
            "type": "voice_message_received",
            "message": "Voice message processing not yet implemented"
        })
        
    except Exception as e:
        logger.error(f"Error handling voice message: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Failed to process voice message"
        })


@app.websocket("/ws/chat/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time voice conversation with VAD."""
    await websocket.accept()
    await streaming_websocket_handler.handle_streaming_connection(
        websocket, user_id
    )


@app.websocket("/ws/flow/{session_id}")
async def websocket_flow_voice(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for Flow Voice AI agent conversations."""
    await app.state.flow_websocket_handler.handle_flow_connection(websocket, session_id)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
