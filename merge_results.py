import json
import glob
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import defaultdict

def merge_batch_results():
    """
    Merge all batch results into a single, comprehensive insights file.
    This script is enhanced to provide detailed, publication-ready analytics.
    """
    print("\n" + "="*80)
    print("MENTAL HEALTH CHATBOT EVALUATION - COMPREHENSIVE RESULTS MERGER")
    print("="*80)

    # Path set to your required directory structure
    path = "evaluation_batches/batch_*_results.json"
    batch_files = sorted(glob.glob(path))

    if not batch_files:
        print(f"\n❌ ERROR: No batch result files found matching the path: '{path}'")
        print("   Please ensure your batch files are in the 'evaluation_batches' directory.")
        return

    print(f"\nFound {len(batch_files)} batch file(s): {', '.join(Path(f).name for f in batch_files)}")

    all_results = []
    batch_metadata = []

    for batch_file in batch_files:
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)

            results = batch_data.get("detailed_results", [])
            metadata = batch_data.get("evaluation_metadata", {})

            all_results.extend(results)
            batch_metadata.append({
                "batch_number": batch_data.get("batch_number"),
                "file_name": Path(batch_file).name,
                "cases": len(results),
                "time_seconds": metadata.get("total_evaluation_time_seconds", 0)
            })
        except Exception as e:
            print(f"  -> ❌ Error loading {batch_file}: {e}")

    if not all_results:
        print("\n❌ ERROR: No detailed results could be loaded from the batch files.")
        return

    insights = calculate_comprehensive_insights(all_results)
    compact_results = create_compact_results(all_results)

    save_comprehensive_json(insights, compact_results, batch_metadata)
    print_console_summary(insights)

    print("\n✅ Results merged and insights generated successfully!")
    print("\nGenerated file:")
    print("   - evaluation_insights.json (Comprehensive insights and detailed results)")


def calculate_comprehensive_insights(results):
    """Calculate a wide range of metrics for deep analysis."""
    total_cases = len(results)
    
    screening_results = [r for r in results if r.get("type") == "screening"]
    
    response_times = [r["response_time"] for r in results if r.get("response_time") is not None]
    tool_calls = [r["tool_calls_count"] for r in results if r.get("tool_calls_count") is not None]

    performance = {
        "avg_response_time": np.mean(response_times) if response_times else 0,
        "median_response_time": np.median(response_times) if response_times else 0,
        "p95_response_time": np.percentile(response_times, 95) if response_times else 0,
        "avg_tool_calls": np.mean(tool_calls) if tool_calls else 0
    }

    screening_by_assessment = defaultdict(list)
    for r in screening_results:
        assessment_type = r.get("assessment_type", "unknown")
        screening_by_assessment[assessment_type].append(r)
    
    screening_analysis = {}
    for assessment, assessment_results in screening_by_assessment.items():
        screening_analysis[assessment] = analyze_screening_assessment(assessment_results)

    crisis_analysis = analyze_crisis_detection(results)
    tool_analysis = analyze_tool_calls(results)
    error_analysis = analyze_errors(results)

    return {
        "overview": {
            "total_cases": total_cases,
            "successful_evaluations": sum(1 for r in results if r.get("evaluation_status") == "success"),
            "failed_evaluations": error_analysis['total_failures'],
        },
        "performance": performance,
        "screening_analysis": screening_analysis,
        "crisis_detection": crisis_analysis,
        "tool_call_analysis": tool_analysis,
        "error_analysis": error_analysis
    }

def analyze_screening_assessment(assessment_results):
    """Analyzes a specific set of screening results with a simplified output."""
    total = len(assessment_results)
    if not total:
        return {}

    correct_severity = sum(1 for r in assessment_results if r.get("severity_accuracy") == 1.0)
    
    return {
        "total_cases": total,
        "correctly_identified": correct_severity,
        "overall_severity_accuracy": correct_severity / total if total > 0 else 0,
    }

def analyze_crisis_detection(results):
    """Calculates comprehensive crisis detection metrics including specificity."""
    tp, fp, fn, tn = 0, 0, 0, 0
    by_level = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})

    for r in results:
        expected = r.get("expected_alert", False)
        actual = r.get("actual_alert", False)
        level = r.get("crisis_level", "none")

        if expected and actual:
            tp += 1; by_level[level]["tp"] += 1
        elif not expected and actual:
            fp += 1; by_level[level]["fp"] += 1
        elif expected and not actual:
            fn += 1; by_level[level]["fn"] += 1
        else:
            tn += 1; by_level[level]["tn"] += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

    metrics_by_level = {}
    for level, counts in by_level.items():
        l_tp, l_fp, l_fn, l_tn = counts['tp'], counts['fp'], counts['fn'], counts['tn']
        l_prec = l_tp / (l_tp + l_fp) if (l_tp + l_fp) > 0 else 0
        l_rec = l_tp / (l_tp + l_fn) if (l_tp + l_fn) > 0 else 0
        l_f1 = 2 * (l_prec * l_rec) / (l_prec + l_rec) if (l_prec + l_rec) > 0 else 0
        l_spec = l_tn / (l_tn + l_fp) if (l_tn + l_fp) > 0 else 0
        metrics_by_level[level] = {
            "cases": l_tp + l_fp + l_fn + l_tn,
            "confusion_matrix": {"tp": l_tp, "fp": l_fp, "fn": l_fn, "tn": l_tn},
            "precision": l_prec, "recall": l_rec, "f1_score": l_f1, "specificity": l_spec
        }

    return {
        "overall": {"precision": precision, "recall": recall, "f1_score": f1, "specificity": specificity,
                    "tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "by_risk_level": metrics_by_level,
    }

def analyze_tool_calls(results):
    """Analyzes usage, success, and failures of tool calls."""
    stats = defaultdict(lambda: {"calls": 0, "errors": 0, "error_messages": defaultdict(int)})
    for r in results:
        tool_calls_in_result = r.get("tool_calls")
        if not isinstance(tool_calls_in_result, list):
            continue
        
        for tool_call in tool_calls_in_result:
            if tool_call.get("type") == "tool_call":
                tool_name = tool_call.get("name")
                if tool_name: stats[tool_name]["calls"] += 1
            elif tool_call.get("type") == "tool_result":
                result = tool_call.get("result", "")
                if isinstance(result, str) and "Error:" in result:
                    call_id = tool_call.get("id")
                    original_call = next((c for c in tool_calls_in_result if c.get("id") == call_id and c.get("type") == "tool_call"), None)
                    if original_call:
                        tool_name = original_call.get("name")
                        if tool_name:
                            stats[tool_name]["errors"] += 1
                            stats[tool_name]["error_messages"][result] += 1
    
    for tool, data in stats.items():
        data["error_rate"] = data["errors"] / data["calls"] if data["calls"] > 0 else 0

    return {k: dict(v) for k, v in sorted(stats.items())}

def analyze_errors(results):
    """Analyzes and categorizes evaluation failures."""
    failures = [r for r in results if r.get("evaluation_status") != "success"]
    error_counts = defaultdict(int)
    for f in failures:
        error_counts[f.get("error", "Unknown evaluation error")] += 1
    return {"total_failures": len(failures), "error_breakdown": dict(error_counts)}

def create_compact_results(results):
    """Creates a compact, categorized version of detailed results."""
    compact = {
        "by_assessment": defaultdict(lambda: defaultdict(list)),
        "missed_crises": [],
        "false_alarms": [],
        "failed_cases": []
    }
    
    for r in results:
        if r.get("evaluation_status") != "success":
            compact["failed_cases"].append({"test_id": r.get("test_id"), "error": r.get("error")})
            continue

        compact_result = {
            "test_id": r.get("test_id"),
            "response_time": r.get("response_time"),
            "tool_calls": r.get("tool_calls_count"),
        }

        if r.get("type") == "screening":
            assessment = r.get("assessment_type", "unknown")
            severity = r.get("expected_severity", "unknown")
            compact_result.update({
                "expected_score": r.get("expected_total"),
                "actual_score": r.get("actual_total"),
                "severity_correct": r.get("severity_accuracy") == 1.0,
            })
            compact["by_assessment"][assessment][severity].append(compact_result)

        if r.get("expected_alert", False) and not r.get("actual_alert", False):
            compact["missed_crises"].append({"test_id": r.get("test_id"), "crisis_level": r.get("crisis_level")})
        
        if not r.get("expected_alert", False) and r.get("actual_alert", False):
            compact["false_alarms"].append({"test_id": r.get("test_id")})
            
    return dict(compact)


def save_comprehensive_json(insights, compact_results, batch_metadata):
    """Save all generated insights and compact results to a single JSON file."""
    output = {
        "evaluation_summary": {
            "generated_at": datetime.now().isoformat(),
            "total_batches": len(batch_metadata),
            "total_cases": insights["overview"]["total_cases"],
            "total_processing_time_seconds": round(sum(b["time_seconds"] for b in batch_metadata), 2),
        },
        "overall_performance": {
            "success_rate_percent": round((insights["overview"]["successful_evaluations"] / insights["overview"]["total_cases"] * 100) if insights["overview"]["total_cases"] > 0 else 0, 1),
            "response_time_seconds": {
                "average": round(insights["performance"]["avg_response_time"], 2),
                "median": round(insights["performance"]["median_response_time"], 2),
                "p95": round(insights["performance"]["p95_response_time"], 2),
            },
            "average_tool_calls_per_case": round(insights["performance"]["avg_tool_calls"], 1),
        },
        "screening_analysis": {
            assessment: {
                "total_cases": data["total_cases"],
                "correctly_identified": data["correctly_identified"],
                "overall_severity_accuracy_percent": round(data["overall_severity_accuracy"] * 100, 1),
            } for assessment, data in insights["screening_analysis"].items()
        },
        "crisis_detection_analysis": insights["crisis_detection"],
        "tool_call_analysis": insights["tool_call_analysis"],
        "failure_analysis": insights["error_analysis"],
        "detailed_categorized_results": compact_results,
        "batch_metadata": batch_metadata
    }

    output_filename = "evaluation_insights.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

def print_console_summary(insights):
    """Print a clear and concise summary of the key insights to the console."""
    print("\n" + "="*80)
    print("EVALUATION INSIGHTS SUMMARY")
    print("="*80)

    overview = insights['overview']
    print(f"\n📊 OVERVIEW")
    print(f"   Total Cases Analyzed: {overview['total_cases']}")
    success_rate = (overview['successful_evaluations'] / overview['total_cases'] * 100) if overview['total_cases'] > 0 else 0
    print(f"   Successful Evaluations: {overview['successful_evaluations']} ({success_rate:.1f}%)")
    if overview['failed_evaluations'] > 0:
        print(f"   Failed Evaluations: {overview['failed_evaluations']} ❌")

    perf = insights['performance']
    print(f"\n⏱️ PERFORMANCE")
    print(f"   Avg Response Time: {perf['avg_response_time']:.2f}s (p95: {perf['p95_response_time']:.2f}s)")
    print(f"   Avg Tool Calls per Case: {perf['avg_tool_calls']:.1f}")
    
    print(f"\n🎯 SCREENING ACCURACY (SEVERITY)")
    if not insights['screening_analysis']:
        print("   No screening results found.")
    else:
        for assessment, data in sorted(insights['screening_analysis'].items()):
            acc = data.get('overall_severity_accuracy', 0) * 100
            total = data.get('total_cases', 0)
            correct = data.get('correctly_identified', 0)
            status = "✅" if acc >= 90 else "⚠️" if acc >= 80 else "❌"
            print(f"   {status} {assessment.upper():<10}: {acc:.1f}% accuracy ({correct}/{total} correct)")

    print(f"\n🚨 CRISIS DETECTION")
    crisis = insights["crisis_detection"]["overall"]
    fn_status = '✅' if crisis['fn'] == 0 else f'❌ ({crisis["fn"]} missed)'
    print(f"   OVERALL METRICS:")
    print(f"     Precision: {crisis['precision']:.3f} | Recall (Sensitivity): {crisis['recall']:.3f} | F1-Score: {crisis['f1_score']:.3f}")
    print(f"     False Negatives (Missed Crises): {fn_status}")
    print(f"     False Positives (False Alarms):  {crisis['fp']}")

    print(f"\n   BY RISK LEVEL:")
    risk_order = ["imminent", "high", "moderate", "low", "none", "unknown"]
    for level in risk_order:
        if level in insights["crisis_detection"]["by_risk_level"]:
            m = insights["crisis_detection"]["by_risk_level"][level]
            cm = m['confusion_matrix']
            if level in ["imminent", "high", "moderate"]:
                print(f"     - {level.upper():<10} ({m['cases']} cases): Recall={m['recall']:.3f} (TP:{cm['tp']}, FN:{cm['fn']})")
            else:
                print(f"     - {level.upper():<10} ({m['cases']} cases): Specificity={m['specificity']:.3f} (TN:{cm['tn']}, FP:{cm['fp']})")

    print("\n🛠️ TOOL CALLS ANALYSIS")
    if not insights['tool_call_analysis']:
        print("   No tool calls were made.")
    else:
        for tool, data in insights['tool_call_analysis'].items():
            error_rate = data['error_rate'] * 100
            status = "✅" if error_rate < 1 else "⚠️" if error_rate < 10 else "❌"
            print(f"   {status} {tool:<30s}: {data['calls']:>4} calls, {error_rate:5.1f}% error rate")

    print("\n" + "="*80)


if __name__ == "__main__":
    merge_batch_results()