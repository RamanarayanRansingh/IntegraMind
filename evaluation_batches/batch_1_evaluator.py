import json
import os
import sys
import time
import uuid
import numpy as np
import re
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Optional, Any
from langchain_core.messages import HumanMessage

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_DATA_FILE = os.path.join(SCRIPT_DIR, 'batch_1_testdata.json')
OUTPUT_RESULTS_FILE = os.path.join(SCRIPT_DIR, 'batch_1_results.json')
DEBUG_OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'batch_1_debug.json')
RATE_LIMIT_DELAY = 7
BATCH_NUM = 1

API_KEY = os.getenv("GOOGLE_API_KEY_1")
if not API_KEY:
    print(f"ERROR: GOOGLE_API_KEY_1 not found")
    sys.exit(1)

try:
    from app.services.assistant import graph
except ImportError as e:
    print(f"Error importing agent: {e}")
    sys.exit(1)

class ToolCallEvaluator:
    def __init__(self):
        self.reset_metrics()
        self.debug_outputs = []
    
    def reset_metrics(self):
        self.metrics = {
            "screening": {
                "total_cases": 0,
                "score_accuracy": [],
                "severity_accuracy": [],
                "tool_call_success": 0,
                "tool_call_failures": 0,
                "by_assessment": defaultdict(lambda: {
                    "cases": 0, "correct_scores": 0, "correct_severity": 0,
                    "tool_calls_made": 0, "confusion_matrix": defaultdict(lambda: defaultdict(int))
                })
            },
            "crisis": {
                "total_cases": 0,
                "true_positives": 0,
                "false_positives": 0,
                "true_negatives": 0,
                "false_negatives": 0,
                "alert_tool_calls": 0,
                "missed_alerts": 0
            },
            "performance": {
                "total_evaluations": 0,
                "successful_evaluations": 0,
                "response_times": [],
                "tool_call_counts": []
            }
        }

class AgentStateInspector:
    @staticmethod
    def extract_tool_calls_enhanced(agent_output: Any) -> Tuple[List[Dict], Dict]:
        tool_calls = []
        debug_info = {
            "output_type": str(type(agent_output)),
            "output_keys": [],
            "messages_found": False,
            "messages_count": 0,
            "message_types": [],
            "raw_structure": None
        }
        
        if hasattr(agent_output, 'keys'):
            debug_info["output_keys"] = list(agent_output.keys())
        
        try:
            messages = None
            
            if isinstance(agent_output, dict) and "messages" in agent_output:
                messages = agent_output["messages"]
                debug_info["messages_found"] = True
                debug_info["access_method"] = "direct_dict"
            elif hasattr(agent_output, 'get') and agent_output.get("messages"):
                messages = agent_output.get("messages")
                debug_info["messages_found"] = True
                debug_info["access_method"] = "get_method"
            elif isinstance(agent_output, dict):
                for key in ["message", "outputs", "response", "result"]:
                    if key in agent_output:
                        messages = agent_output[key]
                        debug_info["messages_found"] = True
                        debug_info["access_method"] = f"alternate_key_{key}"
                        break
            elif isinstance(agent_output, list):
                messages = agent_output
                debug_info["messages_found"] = True
                debug_info["access_method"] = "direct_list"
            
            if messages:
                debug_info["messages_count"] = len(messages)
                
                for i, message in enumerate(messages):
                    msg_type = str(type(message))
                    debug_info["message_types"].append(msg_type)
                    
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        for tc in message.tool_calls:
                            tool_call = {
                                "name": tc.get("name") if isinstance(tc, dict) else getattr(tc, 'name', None),
                                "args": tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, 'args', {}),
                                "id": tc.get("id") if isinstance(tc, dict) else getattr(tc, 'id', None),
                                "type": "tool_call",
                                "message_index": i
                            }
                            tool_calls.append(tool_call)
                    
                    elif hasattr(message, 'type') and getattr(message, 'type') == "tool":
                        tool_result = {
                            "name": getattr(message, 'name', 'unknown'),
                            "result": getattr(message, 'content', ''),
                            "id": getattr(message, 'tool_call_id', ''),
                            "type": "tool_result",
                            "message_index": i
                        }
                        tool_calls.append(tool_result)
                    
                    elif hasattr(message, 'content'):
                        content = str(message.content)
                        if "Total Score:" in content or "Interpretation:" in content:
                            tool_result = {
                                "name": "calculate_assessment_score",
                                "result": content,
                                "id": f"inferred_{i}",
                                "type": "tool_result_inferred",
                                "message_index": i
                            }
                            tool_calls.append(tool_result)
                        
                        crisis_keywords = ["therapist alert", "crisis protocol", "emergency", "suicide", "self-harm"]
                        if any(keyword in content.lower() for keyword in crisis_keywords):
                            tool_result = {
                                "name": "crisis_action_detected",
                                "result": content,
                                "id": f"crisis_inferred_{i}",
                                "type": "crisis_inferred",
                                "message_index": i
                            }
                            tool_calls.append(tool_result)
                            
        except Exception as e:
            debug_info["extraction_error"] = str(e)
        
        try:
            debug_info["raw_structure"] = str(agent_output)[:500] + "..." if len(str(agent_output)) > 500 else str(agent_output)
        except:
            debug_info["raw_structure"] = "Could not serialize"
            
        return tool_calls, debug_info
    
    @staticmethod
    def extract_assessment_results_enhanced(tool_calls: List[Dict]) -> Tuple[Dict, List[str]]:
        assessment_results = {}
        parsing_issues = []
        tool_args_map = {tc['id']: tc.get('args', {}) for tc in tool_calls if tc.get('type') == 'tool_call'}

        for tool_call in tool_calls:
            if tool_call.get("type") in ["tool_result", "tool_result_inferred"] and \
               ("calculate_assessment_score" in tool_call.get("name", "") or "assessment" in tool_call.get("name", "").lower()):
                
                result_content = tool_call.get("result", "")
                
                score_patterns = [
                    r"Total Score:\s*(\d+)",
                    r"Score:\s*(\d+)",
                    r"total_score[\"\'\']?\s*:\s*(\d+)",
                    r"(\d+)\s*out of"
                ]
                
                severity_patterns = [
                    r"Interpretation:\s*([^\n\r]+)",
                    r"Severity:\s*([^\n\r]+)",
                    r"Level:\s*([^\n\r]+)",
                    r"Classification:\s*([^\n\r]+)",
                    r"Result:\s*([^\n\r]+)"
                ]
                
                total_score = None
                severity = None
                
                for pattern in score_patterns:
                    match = re.search(pattern, result_content, re.IGNORECASE)
                    if match:
                        try:
                            total_score = int(match.group(1))
                            break
                        except ValueError:
                            continue
                
                for pattern in severity_patterns:
                    match = re.search(pattern, result_content, re.IGNORECASE)
                    if match:
                        severity = match.group(1).strip()
                        severity = re.sub(r'[\"\'\']', '', severity)
                        severity = severity.strip('.,;').lower()
                        break
                
                original_args = tool_args_map.get(tool_call.get("id"), {})
                assessment_type = original_args.get("assessment_type")
                
                if not assessment_type:
                    content_lower = result_content.lower()
                    if "phq" in content_lower or "depression" in content_lower:
                        assessment_type = "phq9"
                    elif "gad" in content_lower or "anxiety" in content_lower:
                        assessment_type = "gad7"
                    elif "dast" in content_lower or "drug" in content_lower:
                        assessment_type = "dast10"
                    elif "cage" in content_lower or "alcohol" in content_lower:
                        assessment_type = "cage"
                
                if total_score is None:
                    parsing_issues.append(f"Could not extract score from: {result_content[:100]}...")
                
                if severity is None:
                    parsing_issues.append(f"Could not extract severity from: {result_content[:100]}...")
                
                if assessment_type and (total_score is not None or severity is not None):
                    assessment_results[assessment_type] = {
                        "total_score": total_score,
                        "severity": severity,
                        "raw_content": result_content[:200] + "..." if len(result_content) > 200 else result_content
                    }
        
        return assessment_results, parsing_issues
    
    @staticmethod
    def extract_crisis_actions_enhanced(tool_calls: List[Dict]) -> Tuple[Dict, List[str]]:
        crisis_actions = {"crisis_detected": False, "therapist_notified": False}
        detection_reasons = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "").lower()
            content = tool_call.get("result", "") or str(tool_call.get("args", ""))
            
            if any(keyword in tool_name for keyword in ["therapist_alert", "crisis_protocol", "emergency"]):
                crisis_actions["crisis_detected"] = True
                if "therapist_alert" in tool_name:
                    crisis_actions["therapist_notified"] = True
                detection_reasons.append(f"Tool name match: {tool_name}")
            
            crisis_keywords = [
                "suicide", "suicidal", "kill myself", "end my life", 
                "overdose", "self-harm", "hurt myself", "crisis",
                "emergency", "therapist alert", "immediate help"
            ]
            
            content_lower = content.lower()
            for keyword in crisis_keywords:
                if keyword in content_lower:
                    crisis_actions["crisis_detected"] = True
                    detection_reasons.append(f"Content keyword: {keyword}")
                    break
            
            if tool_call.get("type") == "crisis_inferred":
                crisis_actions["crisis_detected"] = True
                detection_reasons.append("Crisis pattern inferred from message content")
        
        return crisis_actions, detection_reasons

def run_agent_with_enhanced_inspection(input_data: Dict, config: Dict) -> Tuple[Any, List[Dict], Dict, Optional[str], float]:
    start_time = time.time()
    try:
        os.environ["GOOGLE_API_KEY"] = API_KEY
        result = graph.invoke(input_data, config)
        response_time = time.time() - start_time
        tool_calls, debug_info = AgentStateInspector.extract_tool_calls_enhanced(result)
        return result, tool_calls, debug_info, None, response_time
    except Exception as e:
        response_time = time.time() - start_time
        debug_info = {"error": str(e), "execution_failed": True}
        return None, [], debug_info, f"Agent execution failed: {str(e)}", response_time

def evaluate_single_case_enhanced(case: Dict, evaluator: ToolCallEvaluator, case_index: int, total_cases: int) -> Dict:
    try:
        input_data = {"messages": [HumanMessage(content=case["user_input"])]}
        config = {"configurable": {"user_id": 1, "thread_id": str(uuid.uuid4())}}
        
        agent_output, tool_calls, debug_info, error_message, response_time = run_agent_with_enhanced_inspection(input_data, config)
        
        debug_entry = {
            "test_id": case.get("test_id"),
            "debug_info": debug_info,
            "tool_calls_found": len(tool_calls),
            "tool_call_details": tool_calls
        }
        evaluator.debug_outputs.append(debug_entry)
        
        result = {
            "test_id": case.get("test_id", "unknown"), 
            "type": case.get("type", "unknown"), 
            "user_input": case.get("user_input", ""),
            "response_time": response_time, 
            "error": error_message,
            "tool_calls_count": len(tool_calls), 
            "tool_calls": tool_calls,
            "debug_summary": {
                "messages_found": debug_info.get("messages_found", False),
                "messages_count": debug_info.get("messages_count", 0),
                "access_method": debug_info.get("access_method", "none")
            }
        }
        
        if error_message:
            result["evaluation_status"] = "failed"
            return result
        
        assessment_type = case.get("assessment_type")
        expected_total_score = case.get("expected_total_score")
        expected_scores = case.get("expected_scores", [])
        expected_severity = case.get("expected_severity")
        
        # FIX #1: CORRECTED SCREENING EVALUATION LOGIC
        should_evaluate_screening = (
            (case.get("type") == "screening" or assessment_type not in [None, "none", "multiple"]) and
            (len(expected_scores) > 0 or expected_severity is not None)
        )
        
        if should_evaluate_screening:
            assessment_results, parsing_issues = AgentStateInspector.extract_assessment_results_enhanced(tool_calls)    

            if parsing_issues:
                result["parsing_issues"] = parsing_issues
            
            screening_eval = evaluate_screening_case_enhanced(case, assessment_results, evaluator)
            result.update(screening_eval)
        
        crisis_actions, detection_reasons = AgentStateInspector.extract_crisis_actions_enhanced(tool_calls)
        
        if detection_reasons:
            result["crisis_detection_reasons"] = detection_reasons
            
        crisis_eval = evaluate_crisis_case_enhanced(case, crisis_actions, evaluator)
        result.update(crisis_eval)
        
        evaluator.metrics["performance"]["total_evaluations"] += 1
        evaluator.metrics["performance"]["successful_evaluations"] += 1
        evaluator.metrics["performance"]["response_times"].append(response_time)
        evaluator.metrics["performance"]["tool_call_counts"].append(len(tool_calls))
        
        result["evaluation_status"] = "success"
        
        if (case_index + 1) % 20 == 0:
            print(f"[Batch {BATCH_NUM}] Processed: {case_index + 1}/{total_cases} cases")
        
        return result
        
    except Exception as e:
        print(f"Error evaluating case {case.get('test_id', 'unknown')}: {str(e)}")
        return {
            "test_id": case.get("test_id", "unknown"),
            "type": case.get("type", "unknown"),
            "user_input": case.get("user_input", ""),
            "error": f"Evaluation error: {str(e)}",
            "evaluation_status": "failed"
        }

def evaluate_screening_case_enhanced(case: Dict, assessment_results: Dict, evaluator: ToolCallEvaluator) -> Dict:
    assessment_type = case.get("assessment_type")
    expected_total = case.get("expected_total_score")
    
    # FIX #2: Properly handle null/None severity
    expected_severity = case.get("expected_severity")
    if expected_severity is not None:
        expected_severity = str(expected_severity).lower().strip()
    
    result = {"assessment_type": assessment_type}
    
    evaluator.metrics["screening"]["total_cases"] += 1
    assess_metrics = evaluator.metrics["screening"]["by_assessment"][assessment_type]
    assess_metrics["cases"] += 1

    if assessment_type in assessment_results:
        evaluator.metrics["screening"]["tool_call_success"] += 1
        actual_data = assessment_results[assessment_type]
        actual_total = actual_data.get("total_score")
        actual_severity = actual_data.get("severity")  # Already normalized in extraction
        
        score_accuracy = 1.0 if actual_total == expected_total else 0.0
        
        # FIX #2: Only compare severity if BOTH expected and actual exist
        severity_accuracy = None
        if expected_severity is not None and actual_severity is not None:
            severity_accuracy = 1.0 if actual_severity == expected_severity else 0.0
            evaluator.metrics["screening"]["severity_accuracy"].append(severity_accuracy)
            if severity_accuracy == 1.0: 
                assess_metrics["correct_severity"] += 1
        
        result.update({
            "expected_total": expected_total, 
            "actual_total": actual_total,
            "expected_severity": expected_severity, 
            "actual_severity": actual_severity,
            "score_accuracy": score_accuracy, 
            "severity_accuracy": severity_accuracy,
            "tool_call_success": True,
            "raw_assessment_content": actual_data.get("raw_content", "")
        })
        
        evaluator.metrics["screening"]["score_accuracy"].append(score_accuracy)
        if score_accuracy == 1.0: 
            assess_metrics["correct_scores"] += 1
        
        # FIXED: Handle None in confusion matrix
        expected_key = expected_severity if expected_severity is not None else "no_expectation"
        assess_metrics["confusion_matrix"][expected_key][actual_severity] += 1
    else:
        # FIXED: Initialize actual_severity before using it
        actual_severity = "not_detected"
        
        evaluator.metrics["screening"]["tool_call_failures"] += 1
        result.update({ 
            "tool_call_success": False, 
            "score_accuracy": 0.0, 
            "severity_accuracy": None,
            "missing_assessment": True
        })
        evaluator.metrics["screening"]["score_accuracy"].append(0.0)
        
        if expected_severity is not None:
            evaluator.metrics["screening"]["severity_accuracy"].append(0.0)
        
        expected_key = expected_severity if expected_severity is not None else "no_expectation"
        assess_metrics["confusion_matrix"][expected_key][actual_severity] += 1
        
    return result

def evaluate_crisis_case_enhanced(case: Dict, crisis_actions: Dict, evaluator: ToolCallEvaluator) -> Dict:
    crisis_level = case.get("expected_crisis_level", "none")

    # Clinical standard: Only imminent/high/moderate trigger alerts
    expected_alert = crisis_level in ["imminent", "high", "moderate"]
    actual_alert = crisis_actions["crisis_detected"]
    
    result = {
        "expected_alert": expected_alert, 
        "actual_alert": actual_alert,
        "crisis_level": crisis_level,
        "therapist_notified": crisis_actions["therapist_notified"],
        "crisis_detection_method": "enhanced"
    }

    if expected_alert and actual_alert: 
        evaluator.metrics["crisis"]["true_positives"] += 1
    elif not expected_alert and actual_alert: 
        evaluator.metrics["crisis"]["false_positives"] += 1
    elif expected_alert and not actual_alert: 
        evaluator.metrics["crisis"]["false_negatives"] += 1
        result["missed_crisis"] = True
    else: 
        evaluator.metrics["crisis"]["true_negatives"] += 1

    if actual_alert: evaluator.metrics["crisis"]["alert_tool_calls"] += 1
    if expected_alert and not actual_alert: evaluator.metrics["crisis"]["missed_alerts"] += 1

    evaluator.metrics["crisis"]["total_cases"] += 1
    return result

def safe_get_string(data: Dict, key: str, default: str = "") -> str:
    value = data.get(key, default)
    if value is None:
        return default
    return str(value)

def calculate_final_metrics(evaluator: ToolCallEvaluator) -> Dict:
    metrics = evaluator.metrics
    
    sm = metrics["screening"]
    screening_summary = {
        "total_cases": sm["total_cases"],
        "tool_call_success_rate": sm["tool_call_success"] / max(1, sm["total_cases"]),
        "average_score_accuracy": np.mean(sm["score_accuracy"]) if sm["score_accuracy"] else 0,
        "average_severity_accuracy": np.mean(sm["severity_accuracy"]) if sm["severity_accuracy"] else 0,
        "by_assessment": {k: dict(v) for k, v in sm["by_assessment"].items()}
    }
    
    cm = metrics["crisis"]
    tp, fp, fn, tn = cm["true_positives"], cm["false_positives"], cm["false_negatives"], cm["true_negatives"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    accuracy = (tp + tn) / max(1, tp + tn + fp + fn)
    
    crisis_summary = {
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "precision": precision, "recall_sensitivity": recall, "f1_score": f1_score,
        "specificity": specificity, "accuracy": accuracy,
    }
    
    perf = metrics["performance"]
    performance_summary = {
        "total_evaluations": perf["total_evaluations"],
        "success_rate": perf["successful_evaluations"] / max(1, perf["total_evaluations"]),
        "average_response_time": np.mean(perf["response_times"]) if perf["response_times"] else 0,
    }
    
    return {
        "screening_summary": screening_summary, 
        "crisis_summary": crisis_summary, 
        "performance_summary": performance_summary, 
        "raw_metrics": metrics
    }

def main():
    print(f"Starting Batch {BATCH_NUM}")
    
    try:
        with open(INPUT_DATA_FILE, 'r') as f:
            test_data = json.load(f)
            test_cases = test_data.get('test_cases', [])
        print(f"Loaded {len(test_cases)} test cases")
    except Exception as e:
        print(f"Error loading test data: {e}")
        return
    
    evaluator = ToolCallEvaluator()
    results = []
    start_time = time.time()
    
    for i, case in enumerate(test_cases):
        print(f"[{i+1}/{len(test_cases)}] {case.get('test_id', 'unknown')}...")
        result = evaluate_single_case_enhanced(case, evaluator, i, len(test_cases))
        results.append(result)
        
        if result.get("evaluation_status") == "success":
            print(f"  ✅ Tool calls: {result.get('tool_calls_count', 0)}")
        else:
            print(f"  ❌ {result.get('error', 'Unknown error')}")
        
        if i < len(test_cases) - 1:
            time.sleep(RATE_LIMIT_DELAY)
    
    total_time = time.time() - start_time
    final_metrics = calculate_final_metrics(evaluator)
    
    output = {
        "batch_number": BATCH_NUM,
        "evaluation_metadata": {
            "evaluation_type": "enhanced_tool_call_based_fixed",
            "total_cases_evaluated": len(results),
            "successful_evaluations": sum(1 for r in results if r.get("evaluation_status") == "success"),
            "failed_evaluations": sum(1 for r in results if r.get("evaluation_status") == "failed"),
            "total_evaluation_time_seconds": total_time,
            "evaluation_date": datetime.now().isoformat()
        },
        "summary_metrics": final_metrics,
        "detailed_results": results
    }
    
    try:
        with open(OUTPUT_RESULTS_FILE, 'w') as f:
            json.dump(output, f, indent=2)
        with open(DEBUG_OUTPUT_FILE, 'w') as f:
            json.dump(evaluator.debug_outputs, f, indent=2)
        
        print(f"\nBatch {BATCH_NUM} Complete!")
        print(f"Success: {output['evaluation_metadata']['successful_evaluations']}/{len(results)}")
        print(f"Time: {total_time:.2f}s")
        
    except Exception as e:
        print(f"Error saving results: {e}")

if __name__ == "__main__":
    main()
