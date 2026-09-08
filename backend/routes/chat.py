"""Chat routes with Claude API integration"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class ChatMessage(BaseModel):
    message: str
    context: dict = {}

@router.post("/")
async def chat(message: ChatMessage):
    """Send message to ARIA"""
    try:
        return {
            "response": "ARIA response",
            "context": message.context,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_history():
    """Get chat history"""
    return {"messages": []}
