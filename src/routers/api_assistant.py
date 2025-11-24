from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional
import time
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from src import models
from src import schemas
from src.database import get_db

def _lazy_chatbot():
    try:
        from src.chatbot import async_chatbot as run_async_chatbot_query
        return run_async_chatbot_query
    except Exception as e:
        print(f"Error loading chatbot: {e}")
        return None

router = APIRouter(
    prefix="/api/assistant",
    tags=["API - Assistant"],
    responses={
        400: {"description": "Invalid input"},
        500: {"description": "Internal server error"},
        503: {"description": "Assistant unavailable"}
    }
)

class ChatQuestion(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="The question to ask the assistant")
    top_k: Optional[int] = Field(10, ge=1, le=100, description="Maximum number of results to return")

class ChatResponse(BaseModel):
    answer: str
    processing_time: float
    timestamp: str

@router.post("/ask", response_model=ChatResponse)
async def ask_assistant_api(payload: ChatQuestion, request: Request, db: Session = Depends(get_db)):
    if not payload.question or payload.question.isspace():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if len(payload.question) > 2000:
        raise HTTPException(status_code=400, detail="Question is too long (max 2000 characters).")

    start_time = time.time()

    try:
        username = request.cookies.get('auth_user') or ''
        if not username:
            raise HTTPException(status_code=401, detail="Unauthorized")
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        cutoff = datetime.utcnow() - timedelta(days=30)
        deleted_count = db.query(models.AssistantChat).filter(models.AssistantChat.created_at < cutoff).delete(synchronize_session=False)
        if deleted_count > 0:
            db.commit()
        else:
            db.rollback()

        run_async_chatbot_query = _lazy_chatbot()
        if run_async_chatbot_query is None:
            raise HTTPException(status_code=503, detail="Assistant is currently unavailable. Please try again later.")

        response_text = await run_async_chatbot_query(
            question=payload.question,
            top_k=payload.top_k
        )

        processing_time = time.time() - start_time

        chat_entries = [
            models.AssistantChat(
                username=user.username,
                level=user.level,
                unit=user.unit,
                role=user.role,
                message_role='user',
                content=payload.question
            ),
            models.AssistantChat(
                username=user.username,
                level=user.level,
                unit=user.unit,
                role=user.role,
                message_role='assistant',
                content=response_text
            )
        ]
        db.add_all(chat_entries)
        db.commit()

        return ChatResponse(
            answer=response_text,
            processing_time=processing_time,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

    except HTTPException:
        raise
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out. Please try again.")
    except Exception as e:
        print(f"Chatbot error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question. Please try again."
        )


@router.get("/history", response_model=schemas.AssistantChatHistoryResponse)
async def get_assistant_history(request: Request, db: Session = Depends(get_db)):
    username = request.cookies.get('auth_user') or ''
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    items = (
        db.query(models.AssistantChat)
        .filter(
            and_(
                models.AssistantChat.username == user.username,
                models.AssistantChat.level == user.level,
                models.AssistantChat.unit == user.unit,
            )
        )
        .order_by(models.AssistantChat.created_at.asc())
        .all()
    )

    return schemas.AssistantChatHistoryResponse(
        items=[schemas.AssistantChatItem(message_role=i.message_role, content=i.content, created_at=i.created_at) for i in items]
    )

@router.get("/health")
async def assistant_health_check():
    try:
        run_async_chatbot_query = _lazy_chatbot()
        if run_async_chatbot_query is None:
            return {
                "status": "unavailable",
                "message": "Assistant service is not loaded"
            }

        test_response = await run_async_chatbot_query("test", top_k=1)
        return {
            "status": "available",
            "message": "Assistant service is running",
            "test_response_length": len(test_response)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Assistant service error: {str(e)}"
        }