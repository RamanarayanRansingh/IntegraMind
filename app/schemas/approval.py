# schemas/approval.py
from pydantic import BaseModel, Field

class ApprovalRequest(BaseModel):
    thread_id: str = Field(..., description="The ID of the conversation thread")
    approved: bool = Field(False, description="Whether the action is approved")