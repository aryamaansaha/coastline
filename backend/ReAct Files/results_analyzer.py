"""
Results analyzer and comparison tool for ReAct agent experiments.

This module provides functions to analyze ReAct results, compute metrics,
and compare with HITL baseline results.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.budget import BudgetResult

from config import (
    get_hitl_baseline,
    get_output_dir,
    RESULTS_ANALYZER_SETTINGS
)
from utils import (
    calculate_statistics,
    format_comparison_table,
    get_cost_accuracy
)


def load_results_from_json(filename: str) -> List[BudgetResult]:
    """
    Load results from a JSON file.
    
    Args:
        filename: JSON filename (will look in OUTPUT_DIR)
        
    Returns:
        List of BudgetResult objects
    """
    output_dir = get_output_dir()
    filepath = output_dir / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Results file not found: {filepath}")
    
    with open(filepath, "r") as f:
        data = json.load(f)
    
    # Extract results list
    if "results" in data:
        results_data = data["results"]
    else:
        results_data = data
    
    # Convert dicts to BudgetResult objects
    results = [BudgetResult(**result) for result in results_data]
    
    return results


def analyze_react_results(results: List[BudgetResult]) -> Dict[str, Any]:
    """
    Compute comprehensive statistics from ReAct results.
    
    Args:
        results: List of BudgetResult objects
        
    Returns:
        Dictionary with detailed statistics including:
        - Basic statistics (success rate, iterations, etc.)
        - Success rate by iteration count
        - Cost breakdown statistics
        - Budget constraint violation patterns
        - Cost accuracy metrics
    """
    if not results:
        return {
            "error": "No results provided",
            "basic_stats": {},
            "detailed_stats": {}
        }
    
    # Basic statistics
    basic_stats = calculate_statistics(results)
    
    # Success rate by iteration count
    iterations_success = {}
    for result in results:
        iters = result.iterations_used
        if iters not in iterations_success:
            iterations_success[iters] = {"total": 0, "success": 0}
        iterations_success[iters]["total"] += 1
        if result.success:
            iterations_success[iters]["success"] += 1
    
    # Calculate success rate per iteration count
    for iters in iterations_success:
        total = iterations_success[iters]["total"]
        success = iterations_success[iters]["success"]
        iterations_success[iters]["success_rate"] = (
            (success / total) * 100 if total > 0 else 0.0
        )
    
    # Budget constraint violation patterns
    violation_patterns = {
        "flight_only": 0,
        "hotel_only": 0,
        "activity_only": 0,
        "flight_and_hotel": 0,
        "all_three": 0,
        "none": 0
    }
    
    for result in results:
        if not result.success and result.breakdown:
            breakdown = result.breakdown
            flight_violated = not breakdown.flight_within_budget
            hotel_violated = not breakdown.hotel_within_budget
            activity_violated = not breakdown.activity_within_budget
            
            if flight_violated and hotel_violated and activity_violated:
                violation_patterns["all_three"] += 1
            elif flight_violated and hotel_violated:
                violation_patterns["flight_and_hotel"] += 1
            elif flight_violated:
                violation_patterns["flight_only"] += 1
            elif hotel_violated:
                violation_patterns["hotel_only"] += 1
            elif activity_violated:
                violation_patterns["activity_only"] += 1
            else:
                violation_patterns["none"] += 1
        elif result.success:
            violation_patterns["none"] += 1
    
    # Cost accuracy metrics
    accuracies = [
        get_cost_accuracy(result.breakdown) 
        for result in results 
        if result.breakdown
    ]
    
    accuracy_stats = {}
    if accuracies:
        import statistics
        accuracy_stats = {
            "mean": statistics.mean(accuracies),
            "median": statistics.median(accuracies),
            "min": min(accuracies),
            "max": max(accuracies),
            "std": statistics.stdev(accuracies) if len(accuracies) > 1 else 0.0
        }
    
    # Detailed breakdown
    detailed_stats = {
        "success_by_iterations": iterations_success,
        "violation_patterns": violation_patterns,
        "cost_accuracy": accuracy_stats
    }
    
    return {
        "basic_stats": basic_stats,
        "detailed_stats": detailed_stats
    }


def compare_with_hitl(
    react_stats: Dict[str, Any], 
    hitl_stats: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compare ReAct statistics with HITL baseline.
    
    Args:
        react_stats: Statistics from ReAct agent (from analyze_react_results)
        hitl_stats: Statistics from HITL workflow (defaults to baseline from config)
        
    Returns:
        Dictionary with comparison metrics
    """
    if hitl_stats is None:
        hitl_stats = get_hitl_baseline()
    
    react_basic = react_stats.get("basic_stats", {})
    
    comparison = {
        "success_rate": {
            "react": react_basic.get("success_rate", 0.0),
            "hitl": hitl_stats.get("success_rate", 0.0) * 100,  # Convert to percentage
            "difference": (
                react_basic.get("success_rate", 0.0) - 
                (hitl_stats.get("success_rate", 0.0) * 100)
            ),
            "react_better": (
                react_basic.get("success_rate", 0.0) > 
                (hitl_stats.get("success_rate", 0.0) * 100)
            )
        },
        "average_iterations": {
            "react": react_basic.get("average_iterations", 0.0),
            "hitl": hitl_stats.get("average_iterations", 0.0),
            "difference": (
                react_basic.get("average_iterations", 0.0) - 
                hitl_stats.get("average_iterations", 0.0)
            ),
            "react_better": (
                react_basic.get("average_iterations", 0.0) < 
                hitl_stats.get("average_iterations", 0.0)
            )
        },
        "average_over_budget": {
            "react": react_basic.get("average_over_budget", 0.0),
            "hitl": hitl_stats.get("average_over_budget", 0.0),
            "difference": (
                react_basic.get("average_over_budget", 0.0) - 
                hitl_stats.get("average_over_budget", 0.0)
            ),
            "react_better": (
                react_basic.get("average_over_budget", 0.0) < 
                hitl_stats.get("average_over_budget", 0.0)
            )
        },
        "consistency": {
            "react_std_iterations": react_basic.get("std_iterations", 0.0),
            "hitl_std_iterations": hitl_stats.get("std_iterations", 0.0),
            "react_more_consistent": (
                react_basic.get("std_iterations", 0.0) < 
                hitl_stats.get("std_iterations", 0.0)
            )
        }
    }
    
    # Overall assessment
    react_wins = sum([
        comparison["success_rate"]["react_better"],
        comparison["average_iterations"]["react_better"],
        comparison["average_over_budget"]["react_better"],
        comparison["consistency"]["react_more_consistent"]
    ])
    
    comparison["overall"] = {
        "react_wins": react_wins,
        "hitl_wins": 4 - react_wins,
        "react_better_overall": react_wins >= 2
    }
    
    return comparison


def generate_comparison_report(
    react_stats: Dict[str, Any], 
    hitl_stats: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a formatted comparison report.
    
    Args:
        react_stats: Statistics from ReAct agent
        hitl_stats: Statistics from HITL workflow (optional)
        
    Returns:
        Formatted markdown report string
    """
    if hitl_stats is None:
        hitl_stats = get_hitl_baseline()
    
    comparison = compare_with_hitl(react_stats, hitl_stats)
    react_basic = react_stats.get("basic_stats", {})
    react_detailed = react_stats.get("detailed_stats", {})
    
    lines = []
    lines.append("# ReAct Agent vs HITL Workflow Comparison Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    react_sr = react_basic.get("success_rate", 0.0)
    hitl_sr = hitl_stats.get("success_rate", 0.0) * 100
    
    lines.append(f"- **ReAct Success Rate**: {react_sr:.1f}%")
    lines.append(f"- **HITL Success Rate**: {hitl_sr:.1f}%")
    lines.append(f"- **Difference**: {react_sr - hitl_sr:+.1f} percentage points")
    lines.append("")
    
    if comparison["overall"]["react_better_overall"]:
        lines.append("⚠️ **Note**: ReAct shows better performance in this comparison, but this may vary by test case.")
    else:
        lines.append("✅ **HITL workflow demonstrates superior performance** in constraint satisfaction.")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Detailed Comparison
    lines.append("## Detailed Comparison")
    lines.append("")
    lines.append("### Success Rate")
    lines.append("")
    lines.append("| Metric | ReAct | HITL | Difference |")
    lines.append("|--------|-------|------|------------|")
    sr_comp = comparison["success_rate"]
    lines.append(
        f"| Success Rate (%) | {sr_comp['react']:.1f}% | "
        f"{sr_comp['hitl']:.1f}% | {sr_comp['difference']:+.1f}% |"
    )
    lines.append("")
    
    lines.append("### Iterations")
    lines.append("")
    lines.append("| Metric | ReAct | HITL | Difference |")
    lines.append("|--------|-------|------|------------|")
    iter_comp = comparison["average_iterations"]
    lines.append(
        f"| Average Iterations | {iter_comp['react']:.2f} | "
        f"{iter_comp['hitl']:.2f} | {iter_comp['difference']:+.2f} |"
    )
    lines.append("")
    
    lines.append("### Over-Budget Amount")
    lines.append("")
    lines.append("| Metric | ReAct | HITL | Difference |")
    lines.append("|--------|-------|------|------------|")
    ob_comp = comparison["average_over_budget"]
    lines.append(
        f"| Avg Over Budget ($) | ${ob_comp['react']:.2f} | "
        f"${ob_comp['hitl']:.2f} | ${ob_comp['difference']:+.2f} |"
    )
    lines.append("")
    
    # ReAct Detailed Statistics
    lines.append("## ReAct Agent Detailed Statistics")
    lines.append("")
    lines.append("### Basic Statistics")
    lines.append("")
    lines.append(f"- Total Runs: {react_basic.get('total_runs', 0)}")
    lines.append(f"- Successful: {react_basic.get('success_count', 0)}")
    lines.append(f"- Failed: {react_basic.get('total_runs', 0) - react_basic.get('success_count', 0)}")
    lines.append(f"- Success Rate: {react_basic.get('success_rate', 0.0):.1f}%")
    lines.append(f"- Average Iterations: {react_basic.get('average_iterations', 0.0):.2f}")
    lines.append(f"- Std Dev Iterations: {react_basic.get('std_iterations', 0.0):.2f}")
    lines.append(f"- Median Iterations: {react_basic.get('median_iterations', 0)}")
    lines.append("")
    
    # Success by iterations
    if react_detailed.get("success_by_iterations"):
        lines.append("### Success Rate by Iteration Count")
        lines.append("")
        lines.append("| Iterations | Total Runs | Successful | Success Rate (%) |")
        lines.append("|------------|------------|------------|------------------|")
        for iters, data in sorted(react_detailed["success_by_iterations"].items()):
            lines.append(
                f"| {iters} | {data['total']} | {data['success']} | "
                f"{data.get('success_rate', 0.0):.1f}% |"
            )
        lines.append("")
    
    # Violation patterns
    if react_detailed.get("violation_patterns"):
        lines.append("### Budget Constraint Violation Patterns")
        lines.append("")
        lines.append("| Pattern | Count |")
        lines.append("|---------|-------|")
        for pattern, count in react_detailed["violation_patterns"].items():
            lines.append(f"| {pattern.replace('_', ' ').title()} | {count} |")
        lines.append("")
    
    # Cost accuracy
    if react_detailed.get("cost_accuracy"):
        acc = react_detailed["cost_accuracy"]
        lines.append("### Cost Accuracy Metrics")
        lines.append("")
        lines.append(f"- Mean Accuracy: {acc.get('mean', 0.0):.1f}%")
        lines.append(f"- Median Accuracy: {acc.get('median', 0.0):.1f}%")
        lines.append(f"- Min Accuracy: {acc.get('min', 0.0):.1f}%")
        lines.append(f"- Max Accuracy: {acc.get('max', 0.0):.1f}%")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.append(
        "This comparison demonstrates the trade-offs between a pure ReAct agent "
        "and a Human-in-the-Loop workflow with explicit validation nodes. "
        "The HITL approach provides more reliable constraint satisfaction through "
        "explicit state control and dedicated validation nodes."
    )
    lines.append("")
    
    return "\n".join(lines)


def save_comparison_report(
    react_stats: Dict[str, Any],
    hitl_stats: Optional[Dict[str, Any]] = None,
    filename: Optional[str] = None
) -> Path:
    """
    Generate and save a comparison report to file.
    
    Args:
        react_stats: Statistics from ReAct agent
        hitl_stats: Statistics from HITL workflow (optional)
        filename: Output filename (optional, will auto-generate if not provided)
        
    Returns:
        Path to the saved report file
    """
    report = generate_comparison_report(react_stats, hitl_stats)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comparison_report_{timestamp}.md"
    
    output_dir = get_output_dir()
    filepath = output_dir / filename
    
    with open(filepath, "w") as f:
        f.write(report)
    
    return filepath


def visualize_results(results: List[BudgetResult]) -> None:
    """
    Optional visualization of results (requires matplotlib).
    
    Args:
        results: List of BudgetResult objects
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("⚠️  matplotlib not available - skipping visualization")
        return
    
    if not RESULTS_ANALYZER_SETTINGS.get("include_visualizations", False):
        print("⚠️  Visualizations disabled in settings")
        return
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle("ReAct Agent Experiment Results", fontsize=16)
    
    # 1. Success rate
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count
    axes[0, 0].pie(
        [success_count, fail_count],
        labels=["Success", "Failed"],
        autopct="%1.1f%%",
        startangle=90
    )
    axes[0, 0].set_title("Success Rate")
    
    # 2. Iterations distribution
    iterations = [r.iterations_used for r in results]
    axes[0, 1].hist(iterations, bins=range(1, max(iterations) + 2), edgecolor="black")
    axes[0, 1].set_xlabel("Iterations")
    axes[0, 1].set_ylabel("Count")
    axes[0, 1].set_title("Iterations Distribution")
    
    # 3. Over-budget amounts (for failures)
    over_budget = [
        r.best_plan_over_budget 
        for r in results 
        if not r.success and r.best_plan_over_budget is not None
    ]
    if over_budget:
        axes[1, 0].hist(over_budget, bins=20, edgecolor="black")
        axes[1, 0].set_xlabel("Over Budget ($)")
        axes[1, 0].set_ylabel("Count")
        axes[1, 0].set_title("Over-Budget Distribution")
    
    # 4. Total cost distribution
    total_costs = [
        r.breakdown.total_cost 
        for r in results 
        if r.breakdown and r.breakdown.total_cost is not None
    ]
    if total_costs:
        axes[1, 1].hist(total_costs, bins=20, edgecolor="black")
        axes[1, 1].set_xlabel("Total Cost ($)")
        axes[1, 1].set_ylabel("Count")
        axes[1, 1].set_title("Total Cost Distribution")
    
    plt.tight_layout()
    
    # Save figure
    output_dir = get_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"visualization_{timestamp}.png"
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    print(f"📊 Visualization saved to: {filepath}")
    
    plt.close()


async def main():
    """Main entry point for analyzing results."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze ReAct agent experiment results"
    )
    parser.add_argument(
        "--json-file",
        type=str,
        help="JSON file with results to analyze"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare with HITL baseline"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate comparison report"
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate visualizations (requires matplotlib)"
    )
    
    args = parser.parse_args()
    
    # Load results
    if args.json_file:
        results = load_results_from_json(args.json_file)
    else:
        print("❌ Please provide --json-file with results to analyze")
        return
    
    print(f"\n📊 Analyzing {len(results)} results...")
    
    # Analyze
    react_stats = analyze_react_results(results)
    
    # Print basic stats
    basic = react_stats["basic_stats"]
    print(f"\n✅ Success Rate: {basic['success_rate']:.1f}%")
    print(f"🔄 Average Iterations: {basic['average_iterations']:.2f}")
    
    # Compare
    if args.compare:
        comparison = compare_with_hitl(react_stats)
        print("\n" + format_comparison_table(react_stats, get_hitl_baseline()))
    
    # Generate report
    if args.report:
        report_path = save_comparison_report(react_stats)
        print(f"\n📄 Report saved to: {report_path}")
    
    # Visualize
    if args.visualize:
        visualize_results(results)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

