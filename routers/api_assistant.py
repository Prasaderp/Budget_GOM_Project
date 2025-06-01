from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from typing import Optional

try:
    from chatbot import chatbot as run_chatbot_query
except ImportError:
    print("ERROR: Could not import 'chatbot' function from chatbot.py.")
    async def run_chatbot_query(question: str):
        return "Error: Chatbot script could not be loaded."

router = APIRouter(
    prefix="/api/assistant",
    tags=["API - Assistant"],
)

class ChatQuestion(BaseModel):
    question: str

@router.post("/ask")
async def ask_assistant_api(payload: ChatQuestion):
    if not payload.question or payload.question.isspace():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        response_text = await run_in_threadpool(run_chatbot_query, question=payload.question)
        return {"answer": response_text}
    except Exception as e:
        print(f"Chatbot error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your question with the assistant.")