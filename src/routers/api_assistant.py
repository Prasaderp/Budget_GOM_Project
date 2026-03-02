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
from src.utils_scheme import get_scheme_from_cookies
from src.utils_auth import get_auth_user, get_user_context, get_fiscal_year
from src.core.registry import scheme_registry

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

_LAST_CLEANUP_AT: float = 0.0
_CLEANUP_INTERVAL_SECONDS: int = 3600

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
        username = get_auth_user(request)
        if not username:
            raise HTTPException(status_code=401, detail="Unauthorized")

        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        global _LAST_CLEANUP_AT
        now = time.time()
        if now - _LAST_CLEANUP_AT >= _CLEANUP_INTERVAL_SECONDS:
            cutoff = datetime.utcnow() - timedelta(days=30)
            deleted_count = (
                db.query(models.AssistantChat)
                .filter(models.AssistantChat.created_at < cutoff)
                .delete(synchronize_session=False)
            )
            if deleted_count > 0:
                db.commit()
            else:
                db.rollback()
            _LAST_CLEANUP_AT = now

        run_async_chatbot_query = _lazy_chatbot()
        if run_async_chatbot_query is None:
            raise HTTPException(status_code=503, detail="Assistant is currently unavailable. Please try again later.")

        scheme_code, sub_scheme_code = get_scheme_from_cookies(request)

        # Validate that the selected sub-scheme is known and implemented.
        scheme_config = scheme_registry.get_scheme(sub_scheme_code)
        if not scheme_config or not scheme_config.implemented:
            raise HTTPException(
                status_code=400,
                detail="Selected sub-scheme is not available for assistant queries.",
            )

        # Build a compact, server-trusted user context for security policies.
        user_ctx = get_user_context(request)
        user_ctx.update(
            {
                "scheme_code": scheme_code,
                "sub_scheme_code": sub_scheme_code,
                "fiscal_year": get_fiscal_year(request),
            }
        )

        # Extra safety: validate user level/unit against scheme configuration
        # before handing control to the chatbot security layer.
        level = (user_ctx.get("level") or "").strip()
        role = (user_ctx.get("role") or "").strip()
        unit = (user_ctx.get("unit") or "").strip()
        if not level or not unit:
            raise HTTPException(
                status_code=400,
                detail="User context is missing required level/unit information for assistant access.",
            )

        # DCO-level users and elevated roles (dco, admin) have division-wide access
        is_elevated = level == "dco" or role in ("dco", "admin")
        
        allowed_districts = scheme_config.districts or []
        if allowed_districts and not is_elevated and unit not in allowed_districts:
            raise HTTPException(
                status_code=403,
                detail="Your unit is not permitted for the selected sub-scheme.",
            )

        response_text = await run_async_chatbot_query(
            question=payload.question,
            top_k=payload.top_k,
            sub_scheme_code=sub_scheme_code,
            user_context=user_ctx,
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
    username = get_auth_user(request)
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
        from src.chatbot.database import is_pool_initialized
        from src.chatbot.llm import _init_llm

        pool_ok = is_pool_initialized()
        llm_ok = False
        try:
            llm = _init_llm()
            llm_ok = llm is not None
        except Exception:
            pass

        if pool_ok and llm_ok:
            return {"status": "available", "message": "Assistant service is running"}

        issues = []
        if not pool_ok:
            issues.append("database pool not initialized")
        if not llm_ok:
            issues.append("LLM not available")
        return {"status": "degraded", "message": f"Issues: {', '.join(issues)}"}

    except Exception as e:
        return {
            "status": "error",
            "message": f"Assistant service error: {str(e)}"
        }