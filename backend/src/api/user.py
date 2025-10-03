"""
User management API endpoints.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    preferred_language: str
    timezone: str
    created_at: str
    last_login: Optional[str]


class UpdateUserRequest(BaseModel):
    """Update user request model."""
    full_name: Optional[str] = None
    preferred_language: Optional[str] = None
    timezone: Optional[str] = None


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get current user information."""
    try:
        # TODO: Implement user authentication and get user_id from token
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            preferred_language=user.preferred_language,
            timezone=user.timezone,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user information")


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    request: UpdateUserRequest,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Update current user information."""
    try:
        # TODO: Implement user authentication and get user_id from token
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if request.full_name is not None:
            user.full_name = request.full_name
        if request.preferred_language is not None:
            user.preferred_language = request.preferred_language
        if request.timezone is not None:
            user.timezone = request.timezone
        
        db.commit()
        db.refresh(user)
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            preferred_language=user.preferred_language,
            timezone=user.timezone,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating current user: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user information")


@router.get("/stats")
async def get_user_stats(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get user statistics."""
    try:
        # TODO: Implement user authentication and get user_id from token
        from ..models.conversation import Conversation, Message
        
        # Get conversation count
        conversation_count = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).count()
        
        # Get message count
        message_count = db.query(Message).join(Conversation).filter(
            Conversation.user_id == user_id
        ).count()
        
        # Get active conversations
        active_conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.is_active == True
        ).count()
        
        return {
            "user_id": user_id,
            "conversation_count": conversation_count,
            "message_count": message_count,
            "active_conversations": active_conversations
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user statistics")


@router.delete("/me")
async def delete_current_user(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Delete current user account."""
    try:
        # TODO: Implement user authentication and get user_id from token
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # TODO: Implement soft delete or hard delete based on requirements
        user.is_active = False
        db.commit()
        
        return {
            "user_id": user_id,
            "message": "User account deactivated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting current user: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user account")
