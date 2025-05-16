from langchain_core.runnables import RunnableLambda

from langgraph.prebuilt import ToolNode

from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import uuid
from langchain_core.messages import ToolMessage
from Data_Base import models


def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }

def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )


def get_or_create_conversation(db: Session, user_id: Optional[int], thread_id: Optional[str]) -> models.ConversationHistory:
    """Get existing conversation or create a new one with user validation"""

    if thread_id:
        conversation = db.query(models.ConversationHistory).filter(
            models.ConversationHistory.thread_id == thread_id
        ).first()
        
        if conversation:
            # Ensure the thread belongs to the same user
            if conversation.user_id != user_id:
                raise HTTPException(status_code=403, detail="Thread ID does not belong to this user")
            return conversation

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required for new conversations")

    # Verify if the user exists
    user = db.query(models.User).filter(
        models.User.user_id == user_id
    ).first()
    
    # Create user if doesn't exist
    if not user:
        user = models.User(
            user_id=user_id,
            name="User",
            consent_level="basic",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(user)
        db.flush()

    # Create a new conversation with a unique thread_id
    new_thread_id = str(uuid.uuid4())
    conversation = models.ConversationHistory(
        thread_id=new_thread_id,
        user_id=user_id,
        messages=[],
        summary=f"Conversation started on {datetime.utcnow().strftime('%Y-%m-%d')}",
        timestamp=datetime.utcnow()
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation