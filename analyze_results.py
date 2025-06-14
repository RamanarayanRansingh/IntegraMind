# analyze_tool_call_results.py
# ENHANCED VERSION: Generates a publication-ready analysis from the corrected evaluation results.

import json

INPUT_RESULTS_FILE = 'evaluation_results.json'
OUTPUT_ANALYSIS_FILE = 'analysis.txt'

def format_percentage(value):
    return f"{value:.2%}"

def main():
    """Main function to run the analysis"""
    print(f"🚀 Analyzing corrected evaluation results from {INPUT_RESULTS_FILE}...")
    
    try:
        with open(INPUT_RESULTS_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading or parsing results file: {e}")
        return

    summary = data.get("summary_metrics", {})
    metadata = data.get("evaluation_metadata", {})
    
    # Extract key metric blocks
    screening = summary.get("screening_summary", {})
    crisis = summary.get("crisis_summary", {})
    performance = summary.get("performance_summary", {})

    # Start building the report
    report = [
        "==========================================================",
        "    IntegraMind Agent: Quantitative Evaluation Report     ",
        "==========================================================",
        f"Evaluation Date: {metadata.get('evaluation_date', 'N/A')}",
        f"Total Test Cases: {metadata.get('total_cases_evaluated', 'N/A')}\n"
    ]

    # --- Executive Summary ---
    report.append("--- 1. Executive Summary ---")
    report.append(f"This report provides a quantitative evaluation of the IntegraMind agent's performance on a benchmark dataset of {metadata.get('total_cases_evaluated', 'N/A')} synthetic user interactions. The key findings are:")
    report.append(f"  - Screening Accuracy (Severity): {format_percentage(screening.get('average_severity_accuracy', 0))}")
    report.append(f"  - Crisis Detection Recall:       {format_percentage(crisis.get('recall_sensitivity', 0))}")
    report.append(f"  - Crisis Detection Precision:    {format_percentage(crisis.get('precision', 0))}")
    report.append(f"  - Overall Performance Success:   {format_percentage(performance.get('success_rate', 0))}")
    report.append(f"  - Average Response Time:         {performance.get('average_response_time', 0):.2f} seconds\n")

    # --- Screening Performance Analysis ---
    report.append("--- 2. Clinical Screening Accuracy ---")
    report.append("Evaluates the agent's ability to correctly interpret standardized assessment scores.")
    report.append(f"  - Overall Tool Call Success Rate: {format_percentage(screening.get('tool_call_success_rate', 0))}")
    report.append(f"  - Average Score Accuracy:         {format_percentage(screening.get('average_score_accuracy', 0))}")
    report.append(f"  - Average Severity Accuracy:      {format_percentage(screening.get('average_severity_accuracy', 0))}\n")
    
    by_assessment = screening.get('by_assessment', {})
    for name, metrics in by_assessment.items():
        report.append(f"  2.1. Assessment Details: {name.upper()}")
        total_cases = metrics.get('cases', 0)
        correct_severity = metrics.get('correct_severity', 0)
        accuracy = correct_severity / total_cases if total_cases > 0 else 0
        report.append(f"    - Cases Evaluated: {total_cases}")
        report.append(f"    - Correct Severity Classifications: {correct_severity} ({format_percentage(accuracy)})")
        
        # Display Confusion Matrix for Severity
        cm = metrics.get('confusion_matrix', {})
        if cm:
            report.append("    - Severity Confusion Matrix (Expected vs. Actual):")
            for expected, actuals in cm.items():
                for actual, count in actuals.items():
                    report.append(f"      - Expected '{expected}', Got '{actual}': {count} time(s)")
        report.append("")

    # --- Crisis Detection Analysis ---
    report.append("--- 3. Crisis Detection Performance ---")
    report.append("Evaluates the agent's ability to identify users in crisis and trigger safety protocols. This is the most critical safety metric.")
    cm = crisis.get('confusion_matrix', {})
    tp = cm.get('tp', 0)
    fp = cm.get('fp', 0)
    fn = cm.get('fn', 0)
    tn = cm.get('tn', 0)
    report.append("  3.1. Confusion Matrix:")
    report.append(f"    - True Positives (TP):  {tp} (Correctly identified crisis)")
    report.append(f"    - False Positives (FP): {fp} (Incorrectly flagged non-crisis)")
    report.append(f"    - True Negatives (TN):  {tn} (Correctly identified non-crisis)")
    report.append(f"    - False Negatives (FN): {fn} (MISSED a crisis event) <-- CRITICAL\n")
    
    report.append("  3.2. Key Metrics:")
    report.append(f"    - Accuracy:    {format_percentage(crisis.get('accuracy', 0))} (Overall correctness)")
    report.append(f"    - Precision:   {format_percentage(crisis.get('precision', 0))} (Of all alerts, how many were correct?)")
    report.append(f"    - Recall (Sensitivity): {format_percentage(crisis.get('recall_sensitivity', 0))} (Of all actual crises, how many did we catch?)")
    report.append(f"    - Specificity: {format_percentage(crisis.get('specificity', 0))} (Of all non-crises, how many did we correctly ignore?)")
    report.append(f"    - F1-Score:    {crisis.get('f1_score', 0):.3f} (Harmonic mean of precision and recall)\n")

    # --- Recommendations ---
    report.append("--- 4. Analysis & Recommendations ---")
    if crisis.get('recall_sensitivity', 1.0) < 1.0:
        report.append(f"  - HIGH PRIORITY: Crisis Recall is below 100% ({fn} missed cases). Review the agent's prompt rules in `assistant.py` for these specific test cases to improve sensitivity. The goal must be 100% Recall.")
    else:
        report.append("  - STRENGTH: Crisis Recall is 100%. The agent successfully identified all critical crisis cases in the benchmark dataset.")
    
    if screening.get('average_severity_accuracy', 1.0) < 0.95:
        report.append(f"  - MEDIUM PRIORITY: Screening accuracy is {format_percentage(screening.get('average_severity_accuracy', 0))}. While good, review the misclassified cases to fine-tune the agent's interpretation or the severity boundaries.")
    else:
        report.append("  - STRENGTH: Screening accuracy is high, indicating reliable interpretation of assessment results.")
        
    if crisis.get('precision', 1.0) < 0.9:
        report.append(f"  - LOW PRIORITY: Precision is {format_percentage(crisis.get('precision', 0))}, indicating some false alarms ({fp} cases). While safety is paramount, reducing false positives can improve therapist trust in the system. This can be addressed after ensuring 100% recall.")
    
    report.append("\n==========================================================")

    # Save the report to a file
    final_report_str = "\n".join(report)
    with open(OUTPUT_ANALYSIS_FILE, 'w') as f:
        f.write(final_report_str)
        
    print(f"\n✅ Analysis complete. Publication-ready report saved to:\n{OUTPUT_ANALYSIS_FILE}")
    print("\n--- Report Preview ---")
    print(final_report_str)


if __name__ == "__main__":
    main()