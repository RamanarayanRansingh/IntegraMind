from pydantic import BaseModel, Field
from typing import Optional

class UserCreate(BaseModel):
    name: str = Field(..., description="User's name")
    therapist_email: Optional[str] = Field(None, description="Email of user's therapist")
    consent_level: str = Field("basic", description="User's consent level")
    
class UserResponse(BaseModel):
    user_id: int = Field(..., description="The ID of the user")
    name: str = Field(..., description="User's name")
    therapist_email: Optional[str] = Field(None, description="Email of user's therapist")
    consent_level: str = Field(..., description="User's consent level")
    phq9_score: Optional[int] = Field(None, description="Most recent PHQ-9 score")
    phq9_date: Optional[str] = Field(None, description="Date of most recent PHQ-9 assessment")
    gad7_score: Optional[int] = Field(None, description="Most recent GAD-7 score")
    gad7_date: Optional[str] = Field(None, description="Date of most recent GAD-7 assessment")
    dast10_score: Optional[int] = Field(None, description="Most recent DAST-10 score")
    dast10_date: Optional[str] = Field(None, description="Date of most recent DAST-10 assessment")
    cage_score: Optional[int] = Field(None, description="Most recent CAGE score")
    cage_date: Optional[str] = Field(None, description="Date of most recent CAGE assessment")
    risk_level: str = Field("low", description="Current risk level")