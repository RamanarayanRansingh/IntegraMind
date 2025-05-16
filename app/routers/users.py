from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from Data_Base.db_manager import SessionLocal  # Import SessionLocal instead of get_db
from Data_Base import models
from ..schemas.user import UserCreate, UserResponse
from ..utils.logger import logger

router = APIRouter(tags=["users"])

# Define a new dependency that returns the session directly
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    db: Session = Depends(get_db)  # Now this gets a Session object, not a context manager
):
    """
    Create a new user.
    """
    try:
        user = models.User(
            name=request.name,
            therapist_email=request.therapist_email,
            consent_level=request.consent_level,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Created new user with ID {user.user_id}")
        
        return UserResponse(
            user_id=user.user_id,
            name=user.name,
            therapist_email=user.therapist_email,
            consent_level=user.consent_level,
            risk_level="low"  # Default risk level
        )
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get user details by ID.
    """
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get latest assessment scores if available
    phq9 = db.query(models.Assessment).filter(
        models.Assessment.user_id == user_id,
        models.Assessment.assessment_type == "phq9"
    ).order_by(models.Assessment.timestamp.desc()).first()
    
    gad7 = db.query(models.Assessment).filter(
        models.Assessment.user_id == user_id,
        models.Assessment.assessment_type == "gad7"
    ).order_by(models.Assessment.timestamp.desc()).first()
    
    # Get latest DAST-10 assessment
    dast10 = db.query(models.Assessment).filter(
        models.Assessment.user_id == user_id,
        models.Assessment.assessment_type == "dast10"
    ).order_by(models.Assessment.timestamp.desc()).first()
    
    # Get latest CAGE assessment
    cage = db.query(models.Assessment).filter(
        models.Assessment.user_id == user_id,
        models.Assessment.assessment_type == "cage"
    ).order_by(models.Assessment.timestamp.desc()).first()
    
    # Get risk level from most recent crisis event if any
    crisis = db.query(models.CrisisEvent).filter(
        models.CrisisEvent.user_id == user_id
    ).order_by(models.CrisisEvent.timestamp.desc()).first()
    
    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        therapist_email=user.therapist_email,
        consent_level=user.consent_level,
        phq9_score=phq9.total_score if phq9 else None,
        phq9_date=phq9.timestamp.strftime("%Y-%m-%d") if phq9 else None,
        gad7_score=gad7.total_score if gad7 else None,
        gad7_date=gad7.timestamp.strftime("%Y-%m-%d") if gad7 else None,
        dast10_score=dast10.total_score if dast10 else None,
        dast10_date=dast10.timestamp.strftime("%Y-%m-%d") if dast10 else None,
        cage_score=cage.total_score if cage else None,
        cage_date=cage.timestamp.strftime("%Y-%m-%d") if cage else None,
        risk_level=crisis.risk_level if crisis else "low"
    )

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Update user details.
    """
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    user.name = request.name
    user.therapist_email = request.therapist_email
    user.consent_level = request.consent_level
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Updated user with ID {user_id}")
    
    # Return updated user with any assessment data
    return await get_user(user_id, db)

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all users with pagination.
    """
    users = db.query(models.User).offset(skip).limit(limit).all()
    
    return [await get_user(user.user_id, db) for user in users]