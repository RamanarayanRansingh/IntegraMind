from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ChatRequest(BaseModel):
    user_id: int = Field(..., description="The ID of the user sending the message")
    message: str = Field(..., description="The message content")
    thread_id: Optional[str] = Field(None, description="Optional thread ID for continuing conversations")
    
class ChatResponse(BaseModel):
    thread_id: str = Field(..., description="The ID of the conversation thread")
    response: str = Field(..., description="The assistant's response")
    requires_approval: bool = Field(False, description="Whether this response requires approval")
    tool_details: Optional[Dict[str, Any]] = Field(None, description="Details about the tool being called")