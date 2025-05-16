from app.tools.knowledge_tool import get_cbt_exercise, get_psychoeducation, retrieve_relevant_information, get_crisis_protocol
from app.tools.assessment_tool import administer_assessment, calculate_assessment_score
from app.tools.safety_tool import send_therapist_alert

def test_knowledge_tools():
    print("Testing Knowledge Tools...")
    
    # Test retrieving relevant information
    relevant_info = retrieve_relevant_information.invoke({
        'query': 'how to manage panic attacks',
        'category': 'psychoeducation',
        'num_results': 2
    })
    print(f"Relevant Information Result:\n{relevant_info}\n")
    
    # Test getting CBT exercise from knowledge base
    cbt_exercise = get_cbt_exercise.invoke({
        'issue': 'depression',
        'exercise_type': 'thought_record'
    })
    print(f"CBT Exercise From Knowledge Base:\n{cbt_exercise}\n")
    
    # Test getting psychoeducation from knowledge base
    psycho_info = get_psychoeducation.invoke({
        'topic': 'mindfulness'
    })
    print(f"Psychoeducation From Knowledge Base:\n{psycho_info}\n")
    
    # Test getting crisis protocol
    crisis_info = get_crisis_protocol.invoke({
        'risk_level': 'moderate'
    })
    print(f"Crisis Protocol Result:\n{crisis_info}\n")

def test_assessment_tools():
    print("Testing Assessment Tools...")
    
    # Test administering assessment
    assessment = administer_assessment.invoke({
        'assessment_type': 'phq9',
        'user_id': 1,
        'context': 'full'
    })
    print(f"Assessment Administration Result:\n{assessment}\n")
    
    # Test calculating assessment score
    # Simulate PHQ-9 scores: 2,2,1,2,1,1,0,1,0 (moderate depression)
    score_result = calculate_assessment_score.invoke({
        'assessment_type': 'phq9',
        'scores': [2, 2, 1, 2, 1, 1, 0, 1, 0],
        'user_id': 1,
        'store_result': True
    })
    print(f"Assessment Score Calculation Result:\n{score_result}\n")

def test_safety_tools():
    print("Testing Safety Tools...")
    
    # Test sending therapist alert
    alert_result = send_therapist_alert.invoke({
        'risk_level': 'moderate',
        'situation_summary': 'User has expressed feelings of hopelessness and passive suicidal ideation. No immediate plan or intent reported.',
        'user_id': 1,
        'additional_notes': 'User has agreed to contact their therapist and will attend their scheduled appointment tomorrow.'
    })
    print(f"Therapist Alert Result:\n{alert_result}\n")

def test_all_tools():
    print("===== MENTAL HEALTH TOOLS TEST =====\n")
    
    # test_knowledge_tools()
    # test_assessment_tools()
    test_safety_tools()
    
    print("===== TEST COMPLETE =====")

if __name__ == "__main__":
    test_all_tools()