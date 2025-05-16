from typing import List, Optional, Dict, Any
from datetime import datetime
from langchain.tools import tool
from Data_Base.db_manager import store_assessment_result, get_previous_risk_assessments

# Define assessment questions
PHQ9_QUESTIONS = [
    "Little interest or pleasure in doing things?",
    "Feeling down, depressed, or hopeless?",
    "Trouble falling or staying asleep, or sleeping too much?",
    "Feeling tired or having little energy?",
    "Poor appetite or overeating?",
    "Feeling bad about yourself - or that you are a failure or have let yourself or your family down?",
    "Trouble concentrating on things, such as reading the newspaper or watching television?",
    "Moving or speaking so slowly that other people could have noticed? Or the opposite - being so fidgety or restless that you have been moving around a lot more than usual?",
    "Thoughts that you would be better off dead, or of hurting yourself in some way?"
]

GAD7_QUESTIONS = [
    "Feeling nervous, anxious, or on edge?",
    "Not being able to stop or control worrying?",
    "Worrying too much about different things?",
    "Trouble relaxing?", 
    "Being so restless that it's hard to sit still?",
    "Becoming easily annoyed or irritable?",
    "Feeling afraid as if something awful might happen?"
]

# New assessment questions for addiction
DAST10_QUESTIONS = [
    "Have you used drugs other than those required for medical reasons?",
    "Do you abuse more than one drug at a time?",
    "Are you always able to stop using drugs when you want to?",
    "Have you had 'blackouts' or 'flashbacks' as a result of drug use?",
    "Do you ever feel bad or guilty about your drug use?",
    "Does your spouse (or parents) ever complain about your involvement with drugs?",
    "Have you neglected your family because of your use of drugs?",
    "Have you engaged in illegal activities in order to obtain drugs?",
    "Have you ever experienced withdrawal symptoms (felt sick) when you stopped taking drugs?",
    "Have you had medical problems as a result of your drug use (e.g., memory loss, hepatitis, convulsions, bleeding, etc.)?"
]

CAGE_QUESTIONS = [
    "Have you ever felt you should Cut down on your drinking?",
    "Have people Annoyed you by criticizing your drinking?",
    "Have you ever felt bad or Guilty about your drinking?",
    "Have you ever had a drink first thing in the morning to steady your nerves or get rid of a hangover (Eye-opener)?"
]

PHQ9_SEVERITY = {
    (0, 4): "Minimal or no depression",
    (5, 9): "Mild depression",
    (10, 14): "Moderate depression",
    (15, 19): "Moderately severe depression",
    (20, 27): "Severe depression"
}

GAD7_SEVERITY = {
    (0, 4): "Minimal anxiety",
    (5, 9): "Mild anxiety",
    (10, 14): "Moderate anxiety", 
    (15, 21): "Severe anxiety"
}

DAST10_SEVERITY = {
    (0, 2): "Low level of problems related to drug use",
    (3, 5): "Moderate level of problems related to drug use",
    (6, 8): "Substantial level of problems related to drug use",
    (9, 10): "Severe level of problems related to drug use"
}

CAGE_SEVERITY = {
    (0, 1): "Low risk of alcohol dependence",
    (2, 4): "High risk of alcohol dependence"
}

# Assessment configuration metadata
ASSESSMENT_CONFIG = {
    "phq9": {
        "title": "PHQ-9 Depression Screening",
        "instructions": "Over the last 2 weeks, how often have you been bothered by any of the following problems?",
        "questions": PHQ9_QUESTIONS,
        "severity": PHQ9_SEVERITY,
        "max_score": 27,
        "required_scores": 9
    },
    "gad7": {
        "title": "GAD-7 Anxiety Screening",
        "instructions": "Over the last 2 weeks, how often have you been bothered by the following problems?",
        "questions": GAD7_QUESTIONS,
        "severity": GAD7_SEVERITY,
        "max_score": 21,
        "required_scores": 7
    },
    "dast10": {
        "title": "DAST-10 Drug Use Screening",
        "instructions": "The following questions concern information about your potential involvement with drugs excluding alcohol and tobacco during the past 12 months. When the words 'drug use' are used, they mean the use of prescribed or over‐the‐counter medications used in excess of directions and any non‐medical use of drugs.",
        "questions": DAST10_QUESTIONS,
        "severity": DAST10_SEVERITY,
        "max_score": 10,
        "required_scores": 10,
        "scoring_note": "For question 3, a 'No' answer is scored as 1 point. For all other questions, 'Yes' is scored as 1 point."
    },
    "cage": {
        "title": "CAGE Alcohol Screening",
        "instructions": "Please answer the following questions about your alcohol use:",
        "questions": CAGE_QUESTIONS,
        "severity": CAGE_SEVERITY,
        "max_score": 4,
        "required_scores": 4
    }
}

@tool
def administer_assessment(
    assessment_type: str,
    user_id: Optional[int] = None,
    context: Optional[str] = None
) -> str:
    """
    Administers a standardized mental health or substance use assessment to the user.
    
    Args:
        assessment_type: Type of assessment to administer (phq9, gad7, dast10, cage)
        user_id: Optional user ID for tracking
        context: Optional context about how to administer (embedded, full, follow-up)
        
    Returns:
        Formatted assessment with instructions
    """
    assessment_type = assessment_type.lower()
    
    # Validate assessment type
    if assessment_type not in ASSESSMENT_CONFIG:
        return f"Unknown assessment type: {assessment_type}. Available assessments: phq9, gad7, dast10, cage"
    
    # Get assessment configuration
    config = ASSESSMENT_CONFIG[assessment_type]
    questions = config["questions"]
    title = config["title"]
    instructions = config["instructions"]
    
    # Set appropriate scale based on assessment type
    if assessment_type in ["phq9", "gad7"]:
        scale = "0 = Not at all, 1 = Several days, 2 = More than half the days, 3 = Nearly every day"
    elif assessment_type in ["dast10", "cage"]:
        scale = "Please answer Yes (1) or No (0) to each question"
    
    # Check context and format accordingly
    if context == "embedded":
        # For embedding a single question naturally in conversation
        import random
        question_index = random.randint(0, len(questions) - 1)
        
        if assessment_type in ["phq9", "gad7"]:
            return f"I'd like to check in on something specific: {questions[question_index]}\n\nYou can respond with a rating from 0 to 3, where {scale}"
        else:
            return f"I'd like to ask you about something specific: {questions[question_index]}\n\nYou can respond with Yes or No."
    
    elif context == "follow-up":
        # When continuing a partially completed assessment
        # In a real implementation, we'd retrieve the missing questions
        if assessment_type in ["phq9", "gad7"]:
            return f"Let's continue with the assessment. For each of the remaining questions, please rate on a scale where {scale}"
        else:
            return f"Let's continue with the assessment. For each of the remaining questions, please answer Yes or No."
    
    else:
        # Default: full assessment
        return format_assessment_for_display(assessment_type, questions, instructions, title, scale)

@tool
def calculate_assessment_score(
    assessment_type: str,
    scores: List[int],
    user_id: Optional[int] = 1,
    store_result: bool = True
) -> str:
    """
    Calculates and interprets assessment scores.
    
    Args:
        assessment_type: Type of assessment (phq9, gad7, dast10, cage)
        scores: List of numeric scores (0-3 for PHQ-9/GAD-7, 0-1 for DAST-10/CAGE)
        user_id: User ID for tracking scores over time
        store_result: Whether to store the result in the database
        
    Returns:
        Interpretation of assessment scores with comparison to previous results if available
    """
    assessment_type = assessment_type.lower()
    
    # Validate assessment type
    if assessment_type not in ASSESSMENT_CONFIG:
        return f"Unknown assessment type: {assessment_type}. Available assessments: phq9, gad7, dast10, cage"
    
    # Get assessment configuration
    config = ASSESSMENT_CONFIG[assessment_type]
    required_scores = config["required_scores"]
    assessment_name = config["title"]
    max_score = config["max_score"]
    severity_ranges = config["severity"]
    
    # Validate scores based on assessment type
    if assessment_type in ["phq9", "gad7"]:
        for score in scores:
            if not (0 <= score <= 3):
                return f"Invalid score detected: {score}. For {assessment_name}, all scores must be between 0 and 3."
    elif assessment_type in ["dast10", "cage"]:
        for score in scores:
            if not (0 <= score <= 1):
                return f"Invalid score detected: {score}. For {assessment_name}, all scores must be either 0 (No) or 1 (Yes)."
    
    if len(scores) != required_scores:
        return f"Error: {assessment_name} requires exactly {required_scores} scores, but {len(scores)} were provided."
    
    # Calculate total score with special handling for DAST-10 question 3
    if assessment_type == "dast10":
        # For DAST-10, question 3 is reverse scored
        total_score = sum(scores)
        if scores[2] == 0:  # If question 3 is answered "No"
            total_score += 1
            scores[2] = 1  # Update the score for storage
        else:
            scores[2] = 0  # If "Yes", score is 0
    else:
        total_score = sum(scores)
    
    # Special case for PHQ-9 item 9 (suicidal ideation)
    suicide_risk = scores[8] if assessment_type == "phq9" and len(scores) > 8 else 0
    
    # Determine severity
    severity = "Unknown"
    for score_range, severity_label in severity_ranges.items():
        if score_range[0] <= total_score <= score_range[1]:
            severity = severity_label
            break
    
    # Get previous assessment for comparison if available
    previous_assessment = None
    if user_id is not None:
        try:
            previous_assessments = get_previous_risk_assessments(
                user_id=user_id, 
                assessment_type=assessment_type, 
                limit=1
            )
            previous_assessment = previous_assessments[0] if previous_assessments else None
        except Exception as e:
            print(f"Error retrieving previous assessments: {str(e)}")
    
    # Store current assessment if requested
    if store_result and user_id is not None:
        # FIX: Convert ISO format string to datetime object if it's a string
        timestamp = datetime.now()
        try:
            store_assessment_result(
                user_id=user_id,
                assessment_type=assessment_type,
                total_score=total_score,
                item_scores=scores,
                timestamp=timestamp
            )
        except Exception as e:
            print(f"Error storing assessment result: {str(e)}")
    
    # Format the response
    return format_assessment_result(
        assessment_type=assessment_type,
        assessment_name=assessment_name,
        total_score=total_score,
        max_score=max_score,
        severity=severity,
        suicide_risk=suicide_risk,
        previous_assessment=previous_assessment
    )

def format_assessment_for_display(
    assessment_type: str, 
    questions: List[str], 
    instructions: str,
    title: str,
    scale: str
) -> str:
    """
    Helper function to format assessment questions for display
    
    Args:
        assessment_type: Type of assessment (phq9, gad7, dast10, cage)
        questions: List of questions to display
        instructions: Instructions for the assessment
        title: Title of the assessment
        scale: Scale description
        
    Returns:
        Formatted assessment ready for display
    """
    formatted_assessment = [
        f"# {title}",
        f"{instructions}",
        f"{scale}",
        ""
    ]
    
    # Add special note for DAST-10
    if assessment_type == "dast10":
        formatted_assessment.append("Different drugs include: cannabis, cocaine, prescription stimulants, methamphetamine, inhalants, sedatives, hallucinogens, opioids, or others.")
        formatted_assessment.append("")
    
    for i, question in enumerate(questions, 1):
        formatted_assessment.append(f"{i}. {question}")
    
    formatted_assessment.append("")
    
    if assessment_type in ["phq9", "gad7"]:
        formatted_assessment.append("Please respond with your rating (0-3) for each question, either in a list format or one by one.")
    else:
        formatted_assessment.append("Please respond with Yes or No for each question, either in a list format or one by one.")
    
    return "\n".join(formatted_assessment)

def format_assessment_result(
    assessment_type: str,
    assessment_name: str,
    total_score: int,
    max_score: int,
    severity: str,
    suicide_risk: int,
    previous_assessment: Optional[Dict[str, Any]] = None
) -> str:
    """
    Helper function to format assessment results for display
    
    Args:
        assessment_type: Type of assessment (phq9, gad7, dast10, cage)
        assessment_name: Name of the assessment
        total_score: Total assessment score
        max_score: Maximum possible score
        severity: Severity level description
        suicide_risk: Score on suicide risk question (PHQ-9 item 9)
        previous_assessment: Previous assessment data for comparison
        
    Returns:
        Formatted assessment results ready for display
    """
    result = [
        f"# {assessment_name} Results",
        f"Total Score: {total_score}/{max_score}",
        f"Interpretation: {severity}",
        ""
    ]
    
    # Add score change if previous assessment exists
    if previous_assessment:
        prev_score = previous_assessment.get('total_score', 0)
        prev_date = previous_assessment.get('timestamp', 'unknown date')
        
        # Parse previous date if it's an ISO format string
        if isinstance(prev_date, str):
            try:
                prev_date = datetime.fromisoformat(prev_date).strftime("%Y-%m-%d")
            except ValueError:
                prev_date = "unknown date"
        
        # Calculate change
        change = total_score - prev_score
        if change > 0:
            change_text = f"increased by {change}"
        elif change < 0:
            change_text = f"decreased by {abs(change)}"
        else:
            change_text = "remained the same"
        
        result.append(f"Change: Your score has {change_text} since your last assessment ({prev_date}).")
        result.append("")
    
    # Add recommendations based on severity and assessment type
    result.append("## Recommendations:")
    
    if assessment_type == "phq9":
        if suicide_risk > 0:
            result.append("⚠️ **Important Safety Note**: Your response indicates thoughts about self-harm or suicide. " 
                        "This is important to address right away. Please consider talking to a mental health professional "
                        "as soon as possible. If you're in immediate danger, please call emergency services or a crisis line.")
            result.append("")
        
        if total_score < 5:
            result.append("Your symptoms suggest minimal or no depression. Continue with self-care practices.")
        elif total_score < 10:
            result.append("Your symptoms suggest mild depression. Consider watchful waiting, self-help resources, or support groups.")
        elif total_score < 15:
            result.append("Your symptoms suggest moderate depression. Consider psychotherapy, counseling, or speaking with your doctor.")
        elif total_score < 20:
            result.append("Your symptoms suggest moderately severe depression. Active treatment with psychotherapy and/or medication is recommended.")
        else:
            result.append("Your symptoms suggest severe depression. Immediate initiation of treatment is recommended, combining psychotherapy and medication.")
    
    elif assessment_type == "gad7":
        if total_score < 5:
            result.append("Your symptoms suggest minimal anxiety. Continue with self-care practices.")
        elif total_score < 10:
            result.append("Your symptoms suggest mild anxiety. Consider self-help resources or monitoring symptoms.")
        elif total_score < 15:
            result.append("Your symptoms suggest moderate anxiety. Consider speaking with a healthcare provider about treatment options.")
        else:
            result.append("Your symptoms suggest severe anxiety. Active treatment with a healthcare provider is recommended.")
    
    elif assessment_type == "dast10":
        if total_score < 3:
            result.append("Your responses suggest a low level of problems related to drug use. Monitor your use and consider preventative education.")
        elif total_score < 6:
            result.append("Your responses suggest a moderate level of problems related to drug use. Consider a brief intervention or counseling.")
        elif total_score < 9:
            result.append("Your responses suggest a substantial level of problems related to drug use. A more thorough assessment by a healthcare professional is recommended.")
        else:
            result.append("Your responses suggest a severe level of problems related to drug use. Intensive assessment and treatment is strongly recommended.")
        
        # Add information about resources
        result.append("")
        result.append("The SAMHSA National Helpline offers free, confidential, 24/7/365 treatment referral and information services for individuals facing substance use disorders: 1-800-662-HELP (4357)")
    
    elif assessment_type == "cage":
        if total_score < 2:
            result.append("Your responses suggest a low risk of alcohol dependence. Continue to monitor your drinking habits.")
        else:
            result.append("Your responses suggest a high risk of alcohol dependence. A more thorough assessment by a healthcare professional is recommended.")
            
        # Add information about resources
        result.append("")
        result.append("If you have concerns about your alcohol use, consider speaking with a healthcare provider or contacting the SAMHSA National Helpline: 1-800-662-HELP (4357)")
    
    result.append("")
    result.append("I'm here to support you. Would you like to talk more about these results or explore coping strategies?")
    
    return "\n".join(result)