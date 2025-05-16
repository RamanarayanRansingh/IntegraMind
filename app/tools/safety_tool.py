import os
import logging
from typing import Optional
from datetime import datetime
from langchain.tools import tool
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import smtplib
import re

from Data_Base.db_manager import record_crisis_event, get_user_info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("safety_tool.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# SMTP configuration from environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
DEFAULT_ALERT_EMAIL = os.getenv("DEFAULT_ALERT_EMAIL", "")


def send_email_smtp(to_email, subject, body, is_html=False):
    """Send email via SMTP."""
    try:
        if not SMTP_USER or not SMTP_PASSWORD:
            logger.error("SMTP credentials not configured")
            return False, "SMTP credentials not configured"
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # Add text part
        plain_text = body
        if is_html:
            # Simple HTML tag removal
            plain_text = re.sub(r'<.*?>', '', body)
            plain_text = plain_text.replace('&nbsp;', ' ')
        msg.attach(MIMEText(plain_text, "plain"))
        
        # Add HTML part if needed
        if is_html:
            msg.attach(MIMEText(body, "html"))
        
        # Send email
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent successfully via SMTP to {to_email}")
        return True, "Email sent successfully via SMTP"
    
    except Exception as e:
        error_msg = f"Failed to send email via SMTP: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def format_alert_html(risk_level, user_id, user_name, situation_summary, additional_notes=None):
    """Format an HTML alert email with better styling."""
    alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Determine risk color
    risk_color = {
        "low": "#4CAF50",      # Green
        "moderate": "#FF9800", # Orange
        "high": "#F44336",     # Red
        "imminent": "#B71C1C"  # Dark Red
    }.get(risk_level.lower(), "#757575")  # Default gray
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #1976D2; color: white; padding: 10px 15px; }}
            .risk-badge {{ background-color: {risk_color}; color: white; padding: 5px 10px; 
                        border-radius: 4px; font-weight: bold; display: inline-block; }}
            .section {{ margin: 15px 0; padding: 15px; background-color: #f5f5f5; border-radius: 4px; }}
            .footer {{ font-size: 12px; color: #757575; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Mental Health Assistant Alert</h2>
            </div>
            
            <div class="section">
                <h3>Alert Details</h3>
                <p><strong>Risk Level:</strong> <span class="risk-badge">{risk_level.upper()}</span></p>
                <p><strong>User ID:</strong> {user_id}</p>
                <p><strong>User Name:</strong> {user_name}</p>
                <p><strong>Time:</strong> {alert_time}</p>
            </div>
            
            <div class="section">
                <h3>Situation Summary</h3>
                <p>{situation_summary.replace('\n', '<br>')}</p>
            </div>
    """
    
    if additional_notes:
        html += f"""
            <div class="section">
                <h3>Additional Notes</h3>
                <p>{additional_notes.replace('\n', '<br>')}</p>
            </div>
        """
        
    html += f"""
            <div class="footer">
                <p>This is an automated alert from the Mental Health Assistant. 
                Please respond according to your crisis protocol.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


@tool
def send_therapist_alert(
    risk_level: str,
    situation_summary: str,
    user_id: Optional[int] = 1,
    additional_notes: Optional[str] = None
) -> str:
    """
    Send an alert to the user's therapist or a designated responder in case of crisis.
    
    Args:
        risk_level: The assessed risk level (low, moderate, high, imminent)
        situation_summary: Brief summary of the situation
        user_id: User ID to retrieve therapist contact info
        additional_notes: Any additional context or information
        
    Returns:
        String confirming alert was sent or error message
    """
    try:
        # Validate risk level
        valid_risk_levels = ["low", "moderate", "high", "imminent"]
        risk_level = risk_level.lower()
        if risk_level not in valid_risk_levels:
            logger.warning(f"Invalid risk level: {risk_level}, defaulting to 'moderate'")
            risk_level = "moderate"
        
        # Get user information to find therapist email
        try:
            user_info = get_user_info(user_id)
            therapist_email = user_info.get("therapist_email") or DEFAULT_ALERT_EMAIL
            user_name = user_info.get("name", "Unknown User")
        except Exception as e:
            logger.error(f"Error retrieving user info: {str(e)}, using defaults")
            therapist_email = DEFAULT_ALERT_EMAIL
            user_name = f"User {user_id}"
        
        # Log the alert attempt
        logger.info(f"Sending therapist alert for User {user_id}, Risk Level: {risk_level}")
        
        # Format the alert subject
        alert_subject = f"ALERT: {risk_level.upper()} Risk - User {user_name} (ID: {user_id})"
        
        # Format HTML email
        html_body = format_alert_html(
            risk_level=risk_level,
            user_id=user_id,
            user_name=user_name,
            situation_summary=situation_summary,
            additional_notes=additional_notes
        )
        
        # Record this alert in the database first (ensure logging even if email fails)
        try:
            event_id = record_crisis_event(
                user_id=user_id,
                risk_level=risk_level,
                description=situation_summary,
                action_taken="therapist_alert_sent"
            )
            logger.info(f"Recorded crisis event in database with ID: {event_id}")
        except Exception as db_error:
            logger.error(f"Failed to record crisis event in database: {str(db_error)}")
            # Continue with email sending even if DB logging fails
        
        # Send email via SMTP
        success, message = send_email_smtp(
            to_email=therapist_email,
            subject=alert_subject,
            body=html_body,
            is_html=True
        )
        
        if success:
            # Update the crisis event to indicate successful email delivery
            try:
                record_crisis_event(
                    user_id=user_id,
                    risk_level=risk_level,
                    description=f"Email alert successfully sent to {therapist_email}",
                    action_taken="therapist_alert_email_sent"
                )
            except Exception as db_error:
                logger.error(f"Failed to record email success in database: {str(db_error)}")
            
            return f"Alert successfully sent to therapist at {therapist_email}. This situation has been logged."
        else:
            logger.error(f"Failed to send email: {message}")
            return f"Alert has been logged in the system, but there was an issue sending the email: {message}. Please continue supporting the user."
        
    except Exception as e:
        # Log the full error for debugging but return a sanitized message
        logger.error(f"Error in send_therapist_alert: {str(e)}", exc_info=True)
        return "There was an issue sending the alert, but this situation has been logged in the system. Please continue providing support to the user."