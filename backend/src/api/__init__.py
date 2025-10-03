"""
API routes for the voice chatbot application.
"""
from fastapi import APIRouter
from .chat import router as chat_router
from .audio import router as audio_router
from .conversation import router as conversation_router
from .user import router as user_router

router = APIRouter()

# Include all route modules
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(audio_router, prefix="/audio", tags=["audio"])
router.include_router(conversation_router, prefix="/conversations", tags=["conversations"])
router.include_router(user_router, prefix="/users", tags=["users"])
