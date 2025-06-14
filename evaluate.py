# tool_call_evaluator_fixed.py
# Enhanced version with better debugging and tool call extraction

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

# --- Configuration ---
INPUT_DATA_FILE = 'synthetic_test_data.json'
OUTPUT_RESULTS_FILE = 'evaluation_results.json'
DEBUG_OUTPUT_FILE = 'debug_agent_outputs.json'  # New: for debugging
RATE_LIMIT_DELAY = 7
MAX_RETRIES = 2
TIMEOUT_SECONDS = 30

# --- Load Environment Variables ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY_2")

# --- Import Agent Logic ---
try:
    from app.services.assistant import graph
    print("✅ Successfully imported agent graph.")
except ImportError as e:
    print(f"❌ Error importing agent logic: {e}")
    print("Please ensure the agent logic is correctly structured for import.")
    sys.exit(1)

class ToolCallEvaluator:
    """Evaluates agent performance by directly inspecting tool calls and state changes"""
    
    def __init__(self):
        self.reset_metrics()
        self.debug_outputs = []  # Store raw outputs for debugging
    
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
    """Enhanced inspector with better debugging capabilities"""
    
    @staticmethod
    def extract_tool_calls_enhanced(agent_output: Any) -> Tuple[List[Dict], Dict]:
        """
        Enhanced tool call extraction with comprehensive debugging info.
        Returns: (tool_calls, debug_info)
        """
        tool_calls = []
        debug_info = {
            "output_type": str(type(agent_output)),
            "output_keys": [],
            "messages_found": False,
            "messages_count": 0,
            "message_types": [],
            "raw_structure": None
        }
        
        # Debug: Capture the structure
        if hasattr(agent_output, 'keys'):
            debug_info["output_keys"] = list(agent_output.keys())
        
        try:
            # Try multiple ways to access messages
            messages = None
            
            # Method 1: Direct access
            if isinstance(agent_output, dict) and "messages" in agent_output:
                messages = agent_output["messages"]
                debug_info["messages_found"] = True
                debug_info["access_method"] = "direct_dict"
            
            # Method 2: Check if it's a state with messages
            elif hasattr(agent_output, 'get') and agent_output.get("messages"):
                messages = agent_output.get("messages")
                debug_info["messages_found"] = True
                debug_info["access_method"] = "get_method"
                
            # Method 3: Check for different key names
            elif isinstance(agent_output, dict):
                for key in ["message", "outputs", "response", "result"]:
                    if key in agent_output:
                        messages = agent_output[key]
                        debug_info["messages_found"] = True
                        debug_info["access_method"] = f"alternate_key_{key}"
                        break
            
            # Method 4: If agent_output itself is a list of messages
            elif isinstance(agent_output, list):
                messages = agent_output
                debug_info["messages_found"] = True
                debug_info["access_method"] = "direct_list"
            
            if messages:
                debug_info["messages_count"] = len(messages)
                
                for i, message in enumerate(messages):
                    msg_type = str(type(message))
                    debug_info["message_types"].append(msg_type)
                    
                    # Extract tool calls with multiple approaches
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
                    
                    # Check for tool results
                    elif hasattr(message, 'type') and getattr(message, 'type') == "tool":
                        tool_result = {
                            "name": getattr(message, 'name', 'unknown'),
                            "result": getattr(message, 'content', ''),
                            "id": getattr(message, 'tool_call_id', ''),
                            "type": "tool_result",
                            "message_index": i
                        }
                        tool_calls.append(tool_result)
                    
                    # Alternative: Check for tool-related content in regular messages
                    elif hasattr(message, 'content'):
                        content = str(message.content)
                        # Look for assessment patterns in content
                        if "Total Score:" in content or "Interpretation:" in content:
                            tool_result = {
                                "name": "calculate_assessment_score",
                                "result": content,
                                "id": f"inferred_{i}",
                                "type": "tool_result_inferred",
                                "message_index": i
                            }
                            tool_calls.append(tool_result)
                        
                        # Look for crisis-related patterns
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
        
        # Store raw structure (truncated for debugging)
        try:
            debug_info["raw_structure"] = str(agent_output)[:500] + "..." if len(str(agent_output)) > 500 else str(agent_output)
        except:
            debug_info["raw_structure"] = "Could not serialize"
            
        return tool_calls, debug_info
    
    @staticmethod
    def extract_assessment_results_enhanced(tool_calls: List[Dict]) -> Tuple[Dict, List[str]]:
        """
        Enhanced assessment extraction with better pattern matching.
        Returns: (assessment_results, parsing_issues)
        """
        assessment_results = {}
        parsing_issues = []
        tool_args_map = {tc['id']: tc.get('args', {}) for tc in tool_calls if tc.get('type') == 'tool_call'}

        for tool_call in tool_calls:
            if tool_call.get("type") in ["tool_result", "tool_result_inferred"] and \
               ("calculate_assessment_score" in tool_call.get("name", "") or "assessment" in tool_call.get("name", "").lower()):
                
                result_content = tool_call.get("result", "")
                
                # Multiple regex patterns for score extraction
                score_patterns = [
                    r"Total Score:\s*(\d+)",
                    r"Score:\s*(\d+)",
                    r"total_score[\"']?\s*:\s*(\d+)",
                    r"(\d+)\s*out of"
                ]
                
                # Multiple regex patterns for severity extraction
                severity_patterns = [
                    r"Interpretation:\s*([^\n\r]+)",
                    r"Severity:\s*([^\n\r]+)",
                    r"Level:\s*([^\n\r]+)",
                    r"Classification:\s*([^\n\r]+)",
                    r"Result:\s*([^\n\r]+)"
                ]
                
                total_score = None
                severity = None
                
                # Try score patterns
                for pattern in score_patterns:
                    match = re.search(pattern, result_content, re.IGNORECASE)
                    if match:
                        try:
                            total_score = int(match.group(1))
                            break
                        except ValueError:
                            continue
                
                # Try severity patterns
                for pattern in severity_patterns:
                    match = re.search(pattern, result_content, re.IGNORECASE)
                    if match:
                        severity = match.group(1).strip()
                        # Clean up common artifacts
                        severity = re.sub(r'["\']', '', severity)
                        severity = severity.strip('.,;')
                        break
                
                # Try to infer assessment type
                original_args = tool_args_map.get(tool_call.get("id"), {})
                assessment_type = original_args.get("assessment_type")
                
                # If not found in args, try to infer from content
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
        """
        Enhanced crisis detection with multiple detection methods.
        Returns: (crisis_actions, detection_reasons)
        """
        crisis_actions = {"crisis_detected": False, "therapist_notified": False}
        detection_reasons = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "").lower()
            content = tool_call.get("result", "") or str(tool_call.get("args", ""))
            
            # Method 1: Direct tool name matching
            if any(keyword in tool_name for keyword in ["therapist_alert", "crisis_protocol", "emergency"]):
                crisis_actions["crisis_detected"] = True
                if "therapist_alert" in tool_name:
                    crisis_actions["therapist_notified"] = True
                detection_reasons.append(f"Tool name match: {tool_name}")
            
            # Method 2: Content-based detection
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
            
            # Method 3: Inferred crisis actions
            if tool_call.get("type") == "crisis_inferred":
                crisis_actions["crisis_detected"] = True
                detection_reasons.append("Crisis pattern inferred from message content")
        
        return crisis_actions, detection_reasons

def run_agent_with_enhanced_inspection(input_data: Dict, config: Dict) -> Tuple[Any, List[Dict], Dict, Optional[str], float]:
    """Enhanced agent runner with comprehensive debugging"""
    start_time = time.time()
    try:
        result = graph.invoke(input_data, config)
        response_time = time.time() - start_time
        tool_calls, debug_info = AgentStateInspector.extract_tool_calls_enhanced(result)
        return result, tool_calls, debug_info, None, response_time
    except Exception as e:
        response_time = time.time() - start_time
        debug_info = {"error": str(e), "execution_failed": True}
        return None, [], debug_info, f"Agent execution failed: {str(e)}", response_time

def evaluate_single_case_enhanced(case: Dict, evaluator: ToolCallEvaluator) -> Dict:
    """Enhanced evaluation with comprehensive debugging"""
    try:
        input_data = {"messages": [HumanMessage(content=case["user_input"])]}
        config = {"configurable": {"user_id": 1, "thread_id": str(uuid.uuid4())}}
        
        agent_output, tool_calls, debug_info, error_message, response_time = run_agent_with_enhanced_inspection(input_data, config)
        
        # Store debug info
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
        
        # Enhanced screening evaluation
        assessment_type = case.get("assessment_type")
        expected_total_score = case.get("expected_total_score")
        
        if assessment_type and assessment_type != "none" and expected_total_score is not None:
            assessment_results, parsing_issues = AgentStateInspector.extract_assessment_results_enhanced(tool_calls)
            
            if parsing_issues:
                result["parsing_issues"] = parsing_issues
            
            screening_eval = evaluate_screening_case_enhanced(case, assessment_results, evaluator)
            result.update(screening_eval)
        
        # Enhanced crisis evaluation
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
    """Enhanced screening evaluation"""
    assessment_type = case.get("assessment_type")
    expected_total = case.get("expected_total_score")
    expected_severity = safe_get_string(case, "expected_severity", "").lower().strip()
    
    result = {"assessment_type": assessment_type}
    
    evaluator.metrics["screening"]["total_cases"] += 1
    assess_metrics = evaluator.metrics["screening"]["by_assessment"][assessment_type]
    assess_metrics["cases"] += 1

    if assessment_type in assessment_results:
        evaluator.metrics["screening"]["tool_call_success"] += 1
        actual_data = assessment_results[assessment_type]
        actual_total = actual_data.get("total_score")
        actual_severity = str(actual_data.get("severity", "")).lower().strip()
        
        score_accuracy = 1.0 if actual_total == expected_total else 0.0
        severity_accuracy = 1.0 if actual_severity == expected_severity else 0.0
        
        result.update({
            "expected_total": expected_total, "actual_total": actual_total,
            "expected_severity": expected_severity, "actual_severity": actual_severity,
            "score_accuracy": score_accuracy, "severity_accuracy": severity_accuracy,
            "tool_call_success": True,
            "raw_assessment_content": actual_data.get("raw_content", "")
        })
        
        evaluator.metrics["screening"]["score_accuracy"].append(score_accuracy)
        evaluator.metrics["screening"]["severity_accuracy"].append(severity_accuracy)
        if score_accuracy == 1.0: assess_metrics["correct_scores"] += 1
        if severity_accuracy == 1.0: assess_metrics["correct_severity"] += 1
        
        assess_metrics["confusion_matrix"][expected_severity][actual_severity] += 1
    else:
        evaluator.metrics["screening"]["tool_call_failures"] += 1
        result.update({ 
            "tool_call_success": False, 
            "score_accuracy": 0.0, 
            "severity_accuracy": 0.0,
            "missing_assessment": True
        })
        evaluator.metrics["screening"]["score_accuracy"].append(0.0)
        evaluator.metrics["screening"]["severity_accuracy"].append(0.0)
        assess_metrics["confusion_matrix"][expected_severity]["not_detected"] += 1
        
    return result

def evaluate_crisis_case_enhanced(case: Dict, crisis_actions: Dict, evaluator: ToolCallEvaluator) -> Dict:
    """Enhanced crisis evaluation"""
    expected_action = safe_get_string(case, "expected_action", "")
    expected_alert = expected_action == "send_therapist_alert"
    actual_alert = crisis_actions["crisis_detected"]
    
    result = {
        "expected_alert": expected_alert, 
        "actual_alert": actual_alert,
        "therapist_notified": crisis_actions["therapist_notified"],
        "crisis_detection_method": "enhanced"
    }

    if expected_alert and actual_alert: 
        evaluator.metrics["crisis"]["true_positives"] += 1
    elif not expected_alert and actual_alert: 
        evaluator.metrics["crisis"]["false_positives"] += 1
    elif expected_alert and not actual_alert: 
        evaluator.metrics["crisis"]["false_negatives"] += 1
        result["missed_crisis"] = True  # Flag for analysis
    else: 
        evaluator.metrics["crisis"]["true_negatives"] += 1

    if actual_alert: evaluator.metrics["crisis"]["alert_tool_calls"] += 1
    if expected_alert and not actual_alert: evaluator.metrics["crisis"]["missed_alerts"] += 1

    evaluator.metrics["crisis"]["total_cases"] += 1
    return result

def safe_get_string(data: Dict, key: str, default: str = "") -> str:
    """Safely get a string value from a dictionary, handling None values"""
    value = data.get(key, default)
    if value is None:
        return default
    return str(value)

def calculate_final_metrics(evaluator: ToolCallEvaluator) -> Dict:
    """Calculate comprehensive final metrics from the evaluation"""
    metrics = evaluator.metrics
    
    # Screening Metrics
    sm = metrics["screening"]
    screening_summary = {
        "total_cases": sm["total_cases"],
        "tool_call_success_rate": sm["tool_call_success"] / max(1, sm["total_cases"]),
        "average_score_accuracy": np.mean(sm["score_accuracy"]) if sm["score_accuracy"] else 0,
        "average_severity_accuracy": np.mean(sm["severity_accuracy"]) if sm["severity_accuracy"] else 0,
        "by_assessment": {k: dict(v) for k, v in sm["by_assessment"].items()}
    }
    
    # Crisis Metrics
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
    
    # Performance Metrics
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
    """Main function to run the enhanced evaluation"""
    print("🚀 Starting Enhanced Tool Call Based Evaluation with Debugging...")
    try:
        with open(INPUT_DATA_FILE, 'r') as f:
            test_cases = json.load(f).get('test_cases', [])
        print(f"✅ Loaded {len(test_cases)} total test cases from {INPUT_DATA_FILE}")
    except Exception as e:
        print(f"❌ Error loading test data: {e}")
        return
    
    # Run on a small sample first for debugging
    test_cases = test_cases[:20]  # Start with 5 cases for debugging
    print(f"🔬 Running on {len(test_cases)} cases for debugging.")
    
    evaluator = ToolCallEvaluator()
    results = []
    start_time = time.time()
    
    for i, case in enumerate(test_cases):
        print(f"\n[{i+1}/{len(test_cases)}] Evaluating: {case.get('test_id', 'unknown')}...")
        try:
            result = evaluate_single_case_enhanced(case, evaluator)
            results.append(result)
            
            # Show detailed progress
            if result.get("evaluation_status") == "success":
                debug_sum = result.get("debug_summary", {})
                print(f"   ✅ Success - Tool calls: {result.get('tool_calls_count', 0)}")
                print(f"      Messages found: {debug_sum.get('messages_found', False)}")
                print(f"      Messages count: {debug_sum.get('messages_count', 0)}")
                print(f"      Access method: {debug_sum.get('access_method', 'none')}")
                
                if result.get("crisis_detection_reasons"):
                    print(f"      Crisis detected via: {result['crisis_detection_reasons']}")
                    
                if result.get("parsing_issues"):
                    print(f"      ⚠️  Parsing issues: {len(result['parsing_issues'])}")
                    
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Critical error: {str(e)}")
            results.append({
                "test_id": case.get("test_id", "unknown"),
                "error": f"Critical evaluation error: {str(e)}",
                "evaluation_status": "failed"
            })
        
        # Rate limiting
        if i < len(test_cases) - 1:
            time.sleep(RATE_LIMIT_DELAY)
    
    final_metrics = calculate_final_metrics(evaluator)
    output = {
        "evaluation_metadata": {
            "evaluation_type": "enhanced_tool_call_based",
            "total_cases_evaluated": len(results),
            "successful_evaluations": sum(1 for r in results if r.get("evaluation_status") == "success"),
            "failed_evaluations": sum(1 for r in results if r.get("evaluation_status") == "failed"),
            "total_evaluation_time_seconds": time.time() - start_time,
            "evaluation_date": datetime.now().isoformat()
        },
        "summary_metrics": final_metrics,
        "detailed_results": results
    }
    
    # Save main results
    try:
        with open(OUTPUT_RESULTS_FILE, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"\n✅ Enhanced evaluation complete! Results saved to {OUTPUT_RESULTS_FILE}")
        
        # Save debug outputs separately
        with open(DEBUG_OUTPUT_FILE, 'w') as f:
            json.dump(evaluator.debug_outputs, f, indent=2)
        print(f"🔍 Debug information saved to {DEBUG_OUTPUT_FILE}")
        
        # Print summary
        metadata = output["evaluation_metadata"]
        print(f"\n📊 Enhanced Evaluation Summary:")
        print(f"   Total cases: {metadata['total_cases_evaluated']}")
        print(f"   Successful: {metadata['successful_evaluations']}")
        print(f"   Failed: {metadata['failed_evaluations']}")
        print(f"   Total time: {metadata['total_evaluation_time_seconds']:.2f} seconds")
        
        # Print debug insights
        debug_summary = {}
        for debug_entry in evaluator.debug_outputs:
            access_method = debug_entry["debug_info"].get("access_method", "none")
            debug_summary[access_method] = debug_summary.get(access_method, 0) + 1
            
        print(f"\n🔍 Debug Summary:")
        for method, count in debug_summary.items():
            print(f"   {method}: {count} cases")
        
    except Exception as e:
        print(f"❌ Error saving results: {e}")
    
    print(f"\n📋 Next Steps:")
    print(f"1. Check {DEBUG_OUTPUT_FILE} to understand how tool calls are being extracted")
    print(f"2. Look for patterns in access_method to understand your agent's output structure")
    print(f"3. Adjust the extraction logic based on findings")
    print(f"4. Re-run with full dataset once extraction is working correctly")

if __name__ == "__main__":
    main()