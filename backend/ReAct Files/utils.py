"""
Utility and helper functions for ReAct agent experiments.

This module provides common functions for formatting, parsing, statistics,
and data export operations.
"""

import json
import csv
import statistics
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.schemas.budget import BudgetResult, BudgetBreakdown

# Import config at module level to avoid circular imports
try:
    from config import get_output_dir
except ImportError:
    # Fallback if config not available
    def get_output_dir():
        return Path(__file__).parent / "experiment_results"


def format_result_summary(result: BudgetResult) -> str:
    """
    Pretty-print a single BudgetResult.
    
    Args:
        result: The BudgetResult to format
        
    Returns:
        Formatted string representation
    """
    lines = []
    lines.append("=" * 70)
    
    status_icon = "✅" if result.success else "❌"
    lines.append(f"{status_icon} Success: {result.success}")
    lines.append(f"📝 Message: {result.message}")
    lines.append(f"🔄 Iterations Used: {result.iterations_used}")
    
    if result.best_plan_over_budget:
        lines.append(f"💸 Over Budget By: ${result.best_plan_over_budget:.2f}")
    
    if result.breakdown:
        lines.append("\n📍 TRIP PLAN:")
        lines.append("-" * 50)
        if result.breakdown.city_order:
            lines.append(f"   Route: {' → '.join(result.breakdown.city_order)}")
        if result.breakdown.days_per_city:
            days_str = ", ".join([
                f"{city}: {days} days" 
                for city, days in result.breakdown.days_per_city.items()
            ])
            lines.append(f"   Days: {days_str}")
        
        lines.append("\n✈️  FLIGHT SEGMENTS:")
        lines.append("-" * 50)
        if result.breakdown.flight_segments:
            for seg in result.breakdown.flight_segments:
                estimate_tag = " (estimate)" if seg.is_estimate else ""
                airline_str = f" [{seg.airline}]" if seg.airline else ""
                lines.append(
                    f"   {seg.from_city} → {seg.to_city}: "
                    f"${seg.cost:.2f}{airline_str}{estimate_tag}"
                )
        else:
            lines.append("   No flight segments found")
        
        lines.append("\n🏨 HOTEL STAYS:")
        lines.append("-" * 50)
        if result.breakdown.hotel_stays:
            for stay in result.breakdown.hotel_stays:
                hotel_name = f" - {stay.hotel_name}" if stay.hotel_name else ""
                ppn = (
                    f" (${stay.price_per_night:.2f}/night)" 
                    if stay.price_per_night else ""
                )
                lines.append(
                    f"   {stay.city}: {stay.nights} nights = "
                    f"${stay.cost:.2f}{ppn}{hotel_name}"
                )
        else:
            lines.append("   No hotel stays found")
        
        lines.append("\n💰 BUDGET BREAKDOWN:")
        lines.append("-" * 50)
        
        # Flight
        flight_icon = "✅" if result.breakdown.flight_within_budget else "❌"
        if result.breakdown.flight_cost is not None:
            lines.append(
                f"   ✈️  Flights: ${result.breakdown.flight_cost:.2f} / "
                f"${result.breakdown.flight_budget:.2f} {flight_icon}"
            )
        else:
            lines.append(
                f"   ✈️  Flights: Unknown / "
                f"${result.breakdown.flight_budget:.2f} {flight_icon}"
            )
        
        # Hotel
        hotel_icon = "✅" if result.breakdown.hotel_within_budget else "❌"
        if result.breakdown.hotel_cost is not None:
            lines.append(
                f"   🏨 Hotels:  ${result.breakdown.hotel_cost:.2f} / "
                f"${result.breakdown.hotel_budget:.2f} {hotel_icon}"
            )
        else:
            lines.append(
                f"   🏨 Hotels:  Unknown / "
                f"${result.breakdown.hotel_budget:.2f} {hotel_icon}"
            )
        
        # Activity
        activity_icon = "✅" if result.breakdown.activity_within_budget else "❌"
        lines.append(
            f"   🎯 Activities: ${result.breakdown.activity_cost:.2f} / "
            f"${result.breakdown.activity_budget:.2f} {activity_icon}"
        )
        
        lines.append("-" * 50)
        lines.append(
            f"   💵 TOTAL: ${result.breakdown.total_cost:.2f} / "
            f"${result.breakdown.total_budget:.2f}"
        )
    
    if result.budget_errors:
        lines.append("\n⚠️  BUDGET ERRORS:")
        for error in result.budget_errors:
            lines.append(f"   • {error}")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)


def calculate_statistics(results: List[BudgetResult]) -> Dict[str, Any]:
    """
    Compute comprehensive statistics from a list of results.
    
    Args:
        results: List of BudgetResult objects
        
    Returns:
        Dictionary with statistics including:
        - success_rate: Percentage of successful runs
        - success_count: Number of successful runs
        - total_runs: Total number of runs
        - average_iterations: Average iterations used
        - std_iterations: Standard deviation of iterations
        - average_over_budget: Average over-budget amount (for failures)
        - median_iterations: Median iterations used
        - min_iterations: Minimum iterations
        - max_iterations: Maximum iterations
        - cost_statistics: Statistics about costs
    """
    if not results:
        return {
            "success_rate": 0.0,
            "success_count": 0,
            "total_runs": 0,
            "average_iterations": 0.0,
            "std_iterations": 0.0,
            "average_over_budget": 0.0,
            "median_iterations": 0,
            "min_iterations": 0,
            "max_iterations": 0,
            "cost_statistics": {}
        }
    
    total_runs = len(results)
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    success_count = len(successful)
    success_rate = (success_count / total_runs) * 100 if total_runs > 0 else 0.0
    
    # Iteration statistics
    iterations = [r.iterations_used for r in results]
    average_iterations = statistics.mean(iterations) if iterations else 0.0
    std_iterations = statistics.stdev(iterations) if len(iterations) > 1 else 0.0
    median_iterations = statistics.median(iterations) if iterations else 0
    min_iterations = min(iterations) if iterations else 0
    max_iterations = max(iterations) if iterations else 0
    
    # Over-budget statistics (for failures only)
    over_budget_amounts = [
        r.best_plan_over_budget 
        for r in failed 
        if r.best_plan_over_budget is not None
    ]
    average_over_budget = (
        statistics.mean(over_budget_amounts) 
        if over_budget_amounts else 0.0
    )
    
    # Cost statistics
    cost_stats = {}
    if results and results[0].breakdown:
        total_costs = [
            r.breakdown.total_cost 
            for r in results 
            if r.breakdown and r.breakdown.total_cost is not None
        ]
        flight_costs = [
            r.breakdown.flight_cost 
            for r in results 
            if r.breakdown and r.breakdown.flight_cost is not None
        ]
        hotel_costs = [
            r.breakdown.hotel_cost 
            for r in results 
            if r.breakdown and r.breakdown.hotel_cost is not None
        ]
        
        if total_costs:
            cost_stats["total_cost"] = {
                "mean": statistics.mean(total_costs),
                "median": statistics.median(total_costs),
                "min": min(total_costs),
                "max": max(total_costs),
                "std": statistics.stdev(total_costs) if len(total_costs) > 1 else 0.0
            }
        
        if flight_costs:
            cost_stats["flight_cost"] = {
                "mean": statistics.mean(flight_costs),
                "median": statistics.median(flight_costs),
                "min": min(flight_costs),
                "max": max(flight_costs),
                "std": statistics.stdev(flight_costs) if len(flight_costs) > 1 else 0.0
            }
        
        if hotel_costs:
            cost_stats["hotel_cost"] = {
                "mean": statistics.mean(hotel_costs),
                "median": statistics.median(hotel_costs),
                "min": min(hotel_costs),
                "max": max(hotel_costs),
                "std": statistics.stdev(hotel_costs) if len(hotel_costs) > 1 else 0.0
            }
    
    return {
        "success_rate": success_rate,
        "success_count": success_count,
        "total_runs": total_runs,
        "average_iterations": average_iterations,
        "std_iterations": std_iterations,
        "average_over_budget": average_over_budget,
        "median_iterations": median_iterations,
        "min_iterations": min_iterations,
        "max_iterations": max_iterations,
        "cost_statistics": cost_stats
    }


def export_results_to_json(
    results: List[BudgetResult], 
    filename: str
) -> Path:
    """
    Export results to JSON file.
    
    Args:
        results: List of BudgetResult objects
        filename: Output filename (will be saved in OUTPUT_DIR)
        
    Returns:
        Path to the created file
    """
    output_dir = get_output_dir()
    filepath = output_dir / filename
    
    # Convert Pydantic models to dicts
    results_dict = [result.model_dump() for result in results]
    
    export_data = {
        "timestamp": datetime.now().isoformat(),
        "total_results": len(results),
        "results": results_dict
    }
    
    with open(filepath, "w") as f:
        json.dump(export_data, f, indent=2, default=str)
    
    return filepath


def export_results_to_csv(
    results: List[BudgetResult], 
    filename: str
) -> Path:
    """
    Export results to CSV file.
    
    Args:
        results: List of BudgetResult objects
        filename: Output filename (will be saved in OUTPUT_DIR)
        
    Returns:
        Path to the created file
    """
    output_dir = get_output_dir()
    filepath = output_dir / filename
    
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            "run_number",
            "success",
            "iterations_used",
            "over_budget",
            "total_cost",
            "flight_cost",
            "hotel_cost",
            "activity_cost",
            "flight_budget",
            "hotel_budget",
            "activity_budget",
            "flight_within_budget",
            "hotel_within_budget",
            "activity_within_budget",
            "city_order",
            "days_per_city",
            "num_flight_segments",
            "num_hotel_stays"
        ])
        
        # Data rows
        for i, result in enumerate(results, 1):
            breakdown = result.breakdown
            
            city_order_str = ",".join(breakdown.city_order) if breakdown and breakdown.city_order else ""
            days_per_city_str = (
                json.dumps(breakdown.days_per_city) 
                if breakdown and breakdown.days_per_city else ""
            )
            
            writer.writerow([
                i,
                result.success,
                result.iterations_used,
                result.best_plan_over_budget or 0.0,
                breakdown.total_cost if breakdown else None,
                breakdown.flight_cost if breakdown else None,
                breakdown.hotel_cost if breakdown else None,
                breakdown.activity_cost if breakdown else None,
                breakdown.flight_budget if breakdown else None,
                breakdown.hotel_budget if breakdown else None,
                breakdown.activity_budget if breakdown else None,
                breakdown.flight_within_budget if breakdown else None,
                breakdown.hotel_within_budget if breakdown else None,
                breakdown.activity_within_budget if breakdown else None,
                city_order_str,
                days_per_city_str,
                len(breakdown.flight_segments) if breakdown else 0,
                len(breakdown.hotel_stays) if breakdown else 0
            ])
    
    return filepath


def parse_agent_reasoning(reasoning: Optional[str]) -> Dict[str, Any]:
    """
    Extract structured data from agent reasoning text.
    
    Args:
        reasoning: Agent's reasoning text
        
    Returns:
        Dictionary with extracted information
    """
    if not reasoning:
        return {}
    
    extracted = {
        "text": reasoning,
        "length": len(reasoning),
        "mentions_budget": "budget" in reasoning.lower(),
        "mentions_cost": "cost" in reasoning.lower() or "$" in reasoning,
        "mentions_iteration": "iteration" in reasoning.lower() or "attempt" in reasoning.lower()
    }
    
    return extracted


def format_comparison_table(
    react_stats: Dict[str, Any], 
    hitl_stats: Dict[str, Any]
) -> str:
    """
    Format a side-by-side comparison table.
    
    Args:
        react_stats: Statistics from ReAct agent
        hitl_stats: Statistics from HITL workflow
        
    Returns:
        Formatted string table
    """
    lines = []
    lines.append("=" * 80)
    lines.append("COMPARISON: ReAct Agent vs HITL Workflow")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"{'Metric':<40} {'ReAct':<20} {'HITL':<20}")
    lines.append("-" * 80)
    
    # Success rate
    react_sr = react_stats.get("success_rate", 0.0)
    hitl_sr = hitl_stats.get("success_rate", 0.0)
    lines.append(
        f"{'Success Rate (%)':<40} "
        f"{react_sr:.1f}%{'':<15} "
        f"{hitl_sr:.1f}%{'':<15}"
    )
    
    # Success count
    react_sc = react_stats.get("success_count", 0)
    react_tr = react_stats.get("total_runs", 0)
    hitl_sc = hitl_stats.get("success_count", 0)
    hitl_tr = hitl_stats.get("total_runs", 0)
    lines.append(
        f"{'Success Count':<40} "
        f"{react_sc}/{react_tr}{'':<15} "
        f"{hitl_sc}/{hitl_tr}{'':<15}"
    )
    
    # Average iterations
    react_ai = react_stats.get("average_iterations", 0.0)
    hitl_ai = hitl_stats.get("average_iterations", 0.0)
    lines.append(
        f"{'Average Iterations':<40} "
        f"{react_ai:.2f}{'':<15} "
        f"{hitl_ai:.2f}{'':<15}"
    )
    
    # Average over budget
    react_aob = react_stats.get("average_over_budget", 0.0)
    hitl_aob = hitl_stats.get("average_over_budget", 0.0)
    lines.append(
        f"{'Avg Over Budget ($)':<40} "
        f"${react_aob:.2f}{'':<12} "
        f"${hitl_aob:.2f}{'':<12}"
    )
    
    lines.append("=" * 80)
    
    return "\n".join(lines)


def validate_result(result: BudgetResult) -> bool:
    """
    Validate that a result has the expected structure.
    
    Args:
        result: BudgetResult to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(result, BudgetResult):
        return False
    
    if result.breakdown:
        breakdown = result.breakdown
        if breakdown.total_cost is not None and breakdown.total_cost < 0:
            return False
        if breakdown.flight_cost is not None and breakdown.flight_cost < 0:
            return False
        if breakdown.hotel_cost is not None and breakdown.hotel_cost < 0:
            return False
    
    if result.iterations_used < 1:
        return False
    
    if result.best_plan_over_budget is not None and result.best_plan_over_budget < 0:
        return False
    
    return True


def get_cost_accuracy(breakdown: Optional[BudgetBreakdown]) -> float:
    """
    Calculate how close costs are to budget (as a percentage).
    
    Args:
        breakdown: BudgetBreakdown to analyze
        
    Returns:
        Accuracy percentage (0-100), where 100 means exactly at budget
    """
    if not breakdown:
        return 0.0
    
    if breakdown.total_budget == 0:
        return 0.0
    
    if breakdown.total_cost is None:
        return 0.0
    
    # Calculate how close we are to budget
    # If under budget, accuracy is (cost / budget) * 100
    # If over budget, accuracy decreases
    if breakdown.total_cost <= breakdown.total_budget:
        accuracy = (breakdown.total_cost / breakdown.total_budget) * 100
    else:
        # Over budget: accuracy decreases
        over_by = breakdown.total_cost - breakdown.total_budget
        accuracy = max(0.0, 100.0 - (over_by / breakdown.total_budget) * 100)
    
    return accuracy

