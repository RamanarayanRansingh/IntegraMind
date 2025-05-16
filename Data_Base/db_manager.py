from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from datetime import datetime

from Data_Base.models import Base, User, Assessment, CrisisEvent, ConversationHistory

# Database URL should ideally be in an environment variable
DATABASE_URL = "sqlite:///Data_Base/db/mental_health_assistant.db"

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)

# USER FUNCTIONS
def get_user_info(user_id):
    """Retrieve user information from database including assessment scores and risk level"""
    with get_db() as db:
        # Get user
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            # Create default user info if not found
            return {
                "user_id": user_id,
                "name": "User",
                "therapist_email": None,
                "consent_level": "basic",
                "risk_level": "low",
                "phq9_score": None,
                "gad7_score": None,
                "dast10_score": None,
                "cage_score": None,
                "last_assessment": None
            }
            
        # Get latest PHQ-9 assessment
        phq9 = db.query(Assessment).filter(
            Assessment.user_id == user_id,
            Assessment.assessment_type == 'phq9'
        ).order_by(Assessment.timestamp.desc()).first()
        
        # Get latest GAD-7 assessment
        gad7 = db.query(Assessment).filter(
            Assessment.user_id == user_id,
            Assessment.assessment_type == 'gad7'
        ).order_by(Assessment.timestamp.desc()).first()
        
        # Get latest DAST-10 assessment
        dast10 = db.query(Assessment).filter(
            Assessment.user_id == user_id,
            Assessment.assessment_type == 'dast10'
        ).order_by(Assessment.timestamp.desc()).first()
        
        # Get latest CAGE assessment
        cage = db.query(Assessment).filter(
            Assessment.user_id == user_id,
            Assessment.assessment_type == 'cage'
        ).order_by(Assessment.timestamp.desc()).first()
        
        # Get latest crisis event
        crisis = db.query(CrisisEvent).filter(
            CrisisEvent.user_id == user_id
        ).order_by(CrisisEvent.timestamp.desc()).first()
        
        # Find the most recent assessment date
        assessment_dates = [a.timestamp for a in [phq9, gad7, dast10, cage] if a is not None]
        last_assessment = max(assessment_dates).strftime("%Y-%m-%d") if assessment_dates else None
        
        return {
            "user_id": user.user_id,
            "name": user.name,
            "therapist_email": user.therapist_email,
            "consent_level": user.consent_level,
            "risk_level": crisis.risk_level if crisis else "low",
            "phq9_score": phq9.total_score if phq9 else None,
            "phq9_date": phq9.timestamp.strftime("%Y-%m-%d") if phq9 else None,
            "gad7_score": gad7.total_score if gad7 else None,
            "gad7_date": gad7.timestamp.strftime("%Y-%m-%d") if gad7 else None,
            "dast10_score": dast10.total_score if dast10 else None,
            "dast10_date": dast10.timestamp.strftime("%Y-%m-%d") if dast10 else None,
            "cage_score": cage.total_score if cage else None,
            "cage_date": cage.timestamp.strftime("%Y-%m-%d") if cage else None,
            "last_assessment": last_assessment
        }

def create_or_update_user(user_id, name=None, therapist_email=None, consent_level=None):
    """Create a new user or update an existing user's information"""
    with get_db() as db:
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            # Create new user
            user = User(
                user_id=user_id,
                name=name or "User",
                therapist_email=therapist_email,
                consent_level=consent_level or "basic"
            )
            db.add(user)
            return "User created successfully"
        else:
            # Update existing user
            if name:
                user.name = name
            if therapist_email is not None:  # Allow setting to None
                user.therapist_email = therapist_email
            if consent_level:
                user.consent_level = consent_level
            
            return "User updated successfully"

# ASSESSMENT FUNCTIONS
def store_assessment_result(user_id, assessment_type, total_score, item_scores=None, timestamp=None):
    """Store assessment result in the database"""
    with get_db() as db:
        # Create a new user if one doesn't exist
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(
                user_id=user_id,
                name="User",
                consent_level="basic"
            )
            db.add(user)
            db.flush()
        
        # FIX: Ensure timestamp is a datetime object, not a string
        if timestamp is None:
            timestamp = datetime.utcnow()
        elif isinstance(timestamp, str):
            # Convert ISO format string to datetime object
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                timestamp = datetime.utcnow()
            
        assessment = Assessment(
            user_id=user_id,
            assessment_type=assessment_type,
            total_score=total_score,
            item_scores=item_scores,
            timestamp=timestamp
        )
        db.add(assessment)
        return assessment.assessment_id

def get_previous_risk_assessments(user_id, assessment_type=None, limit=3):
    """
    Retrieves previous risk assessments for a user.
    
    Args:
        user_id: The user ID
        assessment_type: Optional type of assessment to filter by
        limit: Maximum number of assessments to return (default: 3)
        
    Returns:
        List of previous risk assessments
    """
    with get_db() as db:
        query = db.query(Assessment).filter(Assessment.user_id == user_id)
        
        # Add assessment_type filter if provided
        if assessment_type:
            query = query.filter(Assessment.assessment_type == assessment_type)
        
        # Order by timestamp descending and limit results
        assessments = query.order_by(Assessment.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "assessment_id": a.assessment_id,
                "assessment_type": a.assessment_type,
                "total_score": a.total_score,
                "item_scores": a.item_scores,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None
            }
            for a in assessments
        ]

# CRISIS EVENT FUNCTIONS
def record_crisis_event(user_id, risk_level, description=None, action_taken=None):
    """Record a crisis event in the database"""
    with get_db() as db:
        # Create a new user if one doesn't exist
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(
                user_id=user_id,
                name="User",
                consent_level="basic"
            )
            db.add(user)
            db.flush()
            
        crisis_event = CrisisEvent(
            user_id=user_id,
            risk_level=risk_level,
            description=description,
            action_taken=action_taken,
            timestamp=datetime.utcnow()
        )
        db.add(crisis_event)
        return crisis_event.event_id

# INTERVENTION FUNCTIONS
def store_intervention(user_id, intervention_type, **kwargs):
    """Store details about an intervention that was provided to the user"""
    description = f"Intervention type: {intervention_type}"
    for key, value in kwargs.items():
        if value:
            description += f", {key}: {value}"
            
    # Store as a crisis event with special action_taken value
    return record_crisis_event(
        user_id=user_id,
        risk_level="low",  # Interventions don't typically represent crisis states
        description=description,
        action_taken=f"intervention_{intervention_type}"
    )

# CONVERSATION FUNCTIONS
def store_conversation_history(user_id, thread_id, messages, summary):
    """Store or update conversation history in the database"""
    with get_db() as db:
        # Create a new user if one doesn't exist
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(
                user_id=user_id,
                name="User",
                consent_level="basic"
            )
            db.add(user)
            db.flush()
            
        # Check if thread exists
        conversation = db.query(ConversationHistory).filter(
            ConversationHistory.thread_id == thread_id
        ).first()
        
        if not conversation:
            # Create new conversation record
            conversation = ConversationHistory(
                thread_id=thread_id,
                user_id=user_id,
                messages=messages,
                summary=summary,
                timestamp=datetime.utcnow()
            )
            db.add(conversation)
        else:
            # Update existing conversation record
            conversation.messages = messages
            conversation.summary = summary
            conversation.timestamp = datetime.utcnow()
            
        return thread_id