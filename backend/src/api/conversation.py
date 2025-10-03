"""
Conversation management API endpoints.
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..core.database import get_db
from ..models.conversation import Conversation, Message

logger = logging.getLogger(__name__)

router = APIRouter()


class ConversationResponse(BaseModel):
    """Conversation response model."""
    id: int
    title: str
    language: str
    is_active: bool
    created_at: str
    updated_at: Optional[str]
    ended_at: Optional[str]
    message_count: int


class MessageResponse(BaseModel):
    """Message response model."""
    id: int
    role: str
    content: str
    content_type: str
    created_at: str
    transcription: Optional[str] = None
    ai_model_used: Optional[str] = None
    ai_provider: Optional[str] = None
    response_time_ms: Optional[int] = None


class CreateConversationRequest(BaseModel):
    """Create conversation request model."""
    title: Optional[str] = None
    language: str = "en"


@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    user_id: int = Query(..., description="User ID"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of conversations to return"),
    offset: int = Query(default=0, ge=0, description="Number of conversations to skip"),
    db: Session = Depends(get_db)
):
    """Get user's conversations."""
    try:
        # TODO: Implement user authentication and get user_id from token
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()
        
        result = []
        for conv in conversations:
            message_count = db.query(Message).filter(
                Message.conversation_id == conv.id
            ).count()
            
            result.append(ConversationResponse(
                id=conv.id,
                title=conv.title or f"Conversation {conv.id}",
                language=conv.language,
                is_active=conv.is_active,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat() if conv.updated_at else None,
                ended_at=conv.ended_at.isoformat() if conv.ended_at else None,
                message_count=message_count
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversations")


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Create a new conversation."""
    try:
        # TODO: Implement user authentication and get user_id from token
        conversation = Conversation(
            user_id=user_id,
            title=request.title,
            language=request.language,
            is_active=True
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title or f"Conversation {conversation.id}",
            language=conversation.language,
            is_active=conversation.is_active,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat() if conversation.updated_at else None,
            ended_at=conversation.ended_at.isoformat() if conversation.ended_at else None,
            message_count=0
        )
        
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get a specific conversation."""
    try:
        # TODO: Implement user authentication and get user_id from token
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        message_count = db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).count()
        
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title or f"Conversation {conversation.id}",
            language=conversation.language,
            is_active=conversation.is_active,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat() if conversation.updated_at else None,
            ended_at=conversation.ended_at.isoformat() if conversation.ended_at else None,
            message_count=message_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation")


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    user_id: int = Query(..., description="User ID"),
    limit: int = Query(default=50, ge=1, le=200, description="Number of messages to return"),
    offset: int = Query(default=0, ge=0, description="Number of messages to skip"),
    db: Session = Depends(get_db)
):
    """Get messages from a conversation."""
    try:
        # TODO: Implement user authentication and get user_id from token
        # Verify conversation belongs to user
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).offset(offset).limit(limit).all()
        
        result = []
        for msg in messages:
            result.append(MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                content_type=msg.content_type,
                created_at=msg.created_at.isoformat(),
                transcription=msg.transcription,
                ai_model_used=msg.ai_model_used,
                ai_provider=msg.ai_provider,
                response_time_ms=msg.response_time_ms
            ))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation messages")


@router.put("/{conversation_id}")
async def update_conversation(
    conversation_id: int,
    title: Optional[str] = None,
    language: Optional[str] = None,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Update a conversation."""
    try:
        # TODO: Implement user authentication and get user_id from token
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if title is not None:
            conversation.title = title
        if language is not None:
            conversation.language = language
        
        db.commit()
        
        return {
            "id": conversation.id,
            "title": conversation.title,
            "language": conversation.language,
            "message": "Conversation updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to update conversation")


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Delete a conversation."""
    try:
        # TODO: Implement user authentication and get user_id from token
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        db.delete(conversation)
        db.commit()
        
        return {
            "id": conversation_id,
            "message": "Conversation deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


@router.post("/{conversation_id}/end")
async def end_conversation(
    conversation_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """End a conversation."""
    try:
        # TODO: Implement user authentication and get user_id from token
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation.is_active = False
        # TODO: Set ended_at timestamp
        
        db.commit()
        
        return {
            "id": conversation_id,
            "message": "Conversation ended successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to end conversation")
