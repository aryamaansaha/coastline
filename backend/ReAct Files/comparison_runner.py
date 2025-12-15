"""
Side-by-side comparison runner for ReAct Agent vs HITL Workflow.

This module runs both the ReAct agent and HITL workflow with identical inputs
and generates comprehensive side-by-side comparison reports.
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add parent to path for app.schemas imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.budget import TripBudget, BudgetResult
from budget_agent_services import BudgetAgentService

from config import get_experiment_config, get_hitl_baseline, get_output_dir
from utils import format_result_summary, calculate_statistics, format_comparison_table
from results_analyzer import analyze_react_results, compare_with_hitl


async def run_react_agent(budget: TripBudget) -> BudgetResult:
    """
    Run the ReAct agent with the given budget configuration.
    
    Args:
        budget: TripBudget configuration
        
    Returns:
        BudgetResult from ReAct agent
    """
    print("\n" + "="*70)
    print("Running ReAct Agent...")
    print("="*70)
    
    result = await BudgetAgentService.plan_trip_with_budget(budget)
    
    print(format_result_summary(result))
    
    return result


async def run_hitl_via_api(
    budget: TripBudget,
    base_url: str = "http://localhost:8000"
) -> Optional[BudgetResult]:
    """
    Run HITL workflow via HTTP API call to backend.
    
    Args:
        budget: TripBudget configuration
        base_url: Base URL of the backend API
        
    Returns:
        BudgetResult from HITL workflow, or None if API call fails
    """
    try:
        import httpx
        
        print("\n" + "="*70)
        print("Running HITL Workflow via API...")
        print("="*70)
        
        # Convert TripBudget to HITL Preferences format
        preferences = {
            "origin": budget.origin,
            "destinations": budget.destinations,
            "start_date": budget.departure_date,
            "end_date": budget.return_date,
            "budget_limit": budget.flight_budget + budget.hotel_budget + budget.activity_budget
        }
        
        # Call HITL API endpoint
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Start generation
            response = await client.post(
                f"{base_url}/api/trip/generate/stream",
                json=preferences
            )
            
            if response.status_code != 200:
                print(f"❌ HITL API call failed: {response.status_code}")
                return None
            
            # Parse SSE stream (simplified - would need full SSE parsing in production)
            # For now, return None and suggest using JSON file method
            print("⚠️  HITL API streaming not fully implemented. Use --hitl-json option instead.")
            return None
            
    except ImportError:
        print("⚠️  httpx not available. Install with: pip install httpx")
        return None
    except Exception as e:
        print(f"❌ Error calling HITL API: {e}")
        return None


def load_hitl_from_json(filename: str) -> Optional[BudgetResult]:
    """
    Load HITL result from JSON file.
    
    Args:
        filename: JSON filename (in output directory or full path)
        
    Returns:
        BudgetResult from HITL, or None if file not found
    """
    output_dir = get_output_dir()
    filepath = output_dir / filename
    
    if not filepath.exists():
        # Try as absolute path
        filepath = Path(filename)
        if not filepath.exists():
            print(f"❌ HITL result file not found: {filename}")
            return None
    
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        elif "result" in data:
            data = data["result"]
        elif "results" in data and len(data["results"]) > 0:
            data = data["results"][0]
        
        result = BudgetResult(**data)
        print(f"✅ Loaded HITL result from: {filepath}")
        return result
        
    except Exception as e:
        print(f"❌ Error loading HITL result: {e}")
        return None


def create_comparison_report(
    react_result: BudgetResult,
    hitl_result: Optional[BudgetResult],
    react_stats: Optional[Dict[str, Any]] = None,
    hitl_stats: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a detailed side-by-side comparison report.
    
    Args:
        react_result: ReAct agent result
        hitl_result: HITL workflow result (optional)
        react_stats: ReAct statistics (optional)
        hitl_stats: HITL statistics (optional)
        
    Returns:
        Formatted markdown report string
    """
    lines = []
    lines.append("# Side-by-Side Comparison: ReAct Agent vs HITL Workflow")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # ReAct Results
    lines.append("## ReAct Agent Results")
    lines.append("")
    lines.append(f"**Success**: {'✅ Yes' if react_result.success else '❌ No'}")
    lines.append(f"**Iterations Used**: {react_result.iterations_used}")
    lines.append(f"**Message**: {react_result.message}")
    
    if react_result.breakdown:
        bd = react_result.breakdown
        lines.append("")
        lines.append("### Cost Breakdown")
        lines.append("")
        lines.append("| Category | Cost | Budget | Within Budget |")
        lines.append("|----------|------|--------|---------------|")
        
        flight_icon = "✅" if bd.flight_within_budget else "❌"
        lines.append(
            f"| Flights | ${bd.flight_cost:.2f} | ${bd.flight_budget:.2f} | {flight_icon} |"
        )
        
        hotel_icon = "✅" if bd.hotel_within_budget else "❌"
        lines.append(
            f"| Hotels | ${bd.hotel_cost:.2f} | ${bd.hotel_budget:.2f} | {hotel_icon} |"
        )
        
        activity_icon = "✅" if bd.activity_within_budget else "❌"
        lines.append(
            f"| Activities | ${bd.activity_cost:.2f} | ${bd.activity_budget:.2f} | {activity_icon} |"
        )
        
        lines.append("")
        lines.append(f"**Total Cost**: ${bd.total_cost:.2f} / ${bd.total_budget:.2f}")
        
        if bd.city_order:
            lines.append(f"**City Order**: {' → '.join(bd.city_order)}")
    
    if react_result.best_plan_over_budget:
        lines.append(f"**Over Budget By**: ${react_result.best_plan_over_budget:.2f}")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # HITL Results
    if hitl_result:
        lines.append("## HITL Workflow Results")
        lines.append("")
        lines.append(f"**Success**: {'✅ Yes' if hitl_result.success else '❌ No'}")
        lines.append(f"**Iterations Used**: {hitl_result.iterations_used}")
        lines.append(f"**Message**: {hitl_result.message}")
        
        if hitl_result.breakdown:
            bd = hitl_result.breakdown
            lines.append("")
            lines.append("### Cost Breakdown")
            lines.append("")
            lines.append("| Category | Cost | Budget | Within Budget |")
            lines.append("|----------|------|--------|---------------|")
            
            flight_icon = "✅" if bd.flight_within_budget else "❌"
            lines.append(
                f"| Flights | ${bd.flight_cost:.2f} | ${bd.flight_budget:.2f} | {flight_icon} |"
            )
            
            hotel_icon = "✅" if bd.hotel_within_budget else "❌"
            lines.append(
                f"| Hotels | ${bd.hotel_cost:.2f} | ${bd.hotel_budget:.2f} | {hotel_icon} |"
            )
            
            activity_icon = "✅" if bd.activity_within_budget else "❌"
            lines.append(
                f"| Activities | ${bd.activity_cost:.2f} | ${bd.activity_budget:.2f} | {activity_icon} |"
            )
            
            lines.append("")
            lines.append(f"**Total Cost**: ${bd.total_cost:.2f} / ${bd.total_budget:.2f}")
            
            if bd.city_order:
                lines.append(f"**City Order**: {' → '.join(bd.city_order)}")
        
        if hitl_result.best_plan_over_budget:
            lines.append(f"**Over Budget By**: ${hitl_result.best_plan_over_budget:.2f}")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Direct Comparison
        lines.append("## Direct Comparison")
        lines.append("")
        lines.append("| Metric | ReAct | HITL | Winner |")
        lines.append("|--------|-------|------|--------|")
        
        # Success
        react_success = "✅" if react_result.success else "❌"
        hitl_success = "✅" if hitl_result.success else "❌"
        winner = "HITL" if hitl_result.success and not react_result.success else (
            "ReAct" if react_result.success and not hitl_result.success else "Tie"
        )
        lines.append(f"| Success | {react_success} | {hitl_success} | {winner} |")
        
        # Iterations
        winner = "HITL" if hitl_result.iterations_used < react_result.iterations_used else (
            "ReAct" if react_result.iterations_used < hitl_result.iterations_used else "Tie"
        )
        lines.append(
            f"| Iterations | {react_result.iterations_used} | {hitl_result.iterations_used} | {winner} |"
        )
        
        # Total Cost (if both have breakdowns)
        if react_result.breakdown and hitl_result.breakdown:
            react_cost = react_result.breakdown.total_cost
            hitl_cost = hitl_result.breakdown.total_cost
            winner = "HITL" if hitl_cost < react_cost else (
                "ReAct" if react_cost < hitl_cost else "Tie"
            )
            lines.append(
                f"| Total Cost | ${react_cost:.2f} | ${hitl_cost:.2f} | {winner} |"
            )
    
    # Statistics Comparison (if provided)
    if react_stats and hitl_stats:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Statistical Comparison")
        lines.append("")
        lines.append(format_comparison_table(react_stats, hitl_stats))
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    
    if hitl_result:
        if hitl_result.success and not react_result.success:
            lines.append("✅ **HITL workflow succeeded where ReAct agent failed.**")
        elif react_result.success and not hitl_result.success:
            lines.append("✅ **ReAct agent succeeded where HITL workflow failed.**")
        elif hitl_result.success and react_result.success:
            lines.append("✅ **Both approaches succeeded.**")
        else:
            lines.append("❌ **Both approaches failed to meet budget constraints.**")
    else:
        lines.append("⚠️  **HITL results not available for comparison.**")
    
    return "\n".join(lines)


async def run_comparison(
    budget: TripBudget,
    hitl_result_file: Optional[str] = None,
    hitl_api_url: Optional[str] = None,
    save_report: bool = True
) -> Dict[str, Any]:
    """
    Run side-by-side comparison of ReAct agent and HITL workflow.
    
    Args:
        budget: TripBudget configuration for both approaches
        hitl_result_file: Optional JSON file with HITL result
        hitl_api_url: Optional API URL for HITL (default: http://localhost:8000)
        save_report: Whether to save comparison report to file
        
    Returns:
        Dictionary with comparison results
    """
    print("\n" + "="*70)
    print("SIDE-BY-SIDE COMPARISON: ReAct Agent vs HITL Workflow")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Origin: {budget.origin}")
    print(f"  Destinations: {budget.destinations}")
    print(f"  Dates: {budget.departure_date} to {budget.return_date}")
    print(f"  Budget: ${budget.flight_budget:.2f} flights + ${budget.hotel_budget:.2f} hotels")
    
    # Run ReAct agent
    react_result = await run_react_agent(budget)
    
    # Get HITL result
    hitl_result = None
    if hitl_result_file:
        hitl_result = load_hitl_from_json(hitl_result_file)
    elif hitl_api_url:
        hitl_result = await run_hitl_via_api(budget, hitl_api_url)
    else:
        print("\n⚠️  No HITL result provided. Use --hitl-json or --hitl-api option.")
    
    # Generate report
    report = create_comparison_report(react_result, hitl_result)
    
    print("\n" + "="*70)
    print("COMPARISON REPORT")
    print("="*70)
    print(report)
    
    # Save report
    if save_report:
        output_dir = get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_dir / f"comparison_report_{timestamp}.md"
        
        with open(report_file, "w") as f:
            f.write(report)
        
        print(f"\n💾 Report saved to: {report_file}")
    
    return {
        "react_result": react_result,
        "hitl_result": hitl_result,
        "report": report
    }


async def main():
    """Main entry point for comparison runner."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run side-by-side comparison of ReAct agent and HITL workflow"
    )
    parser.add_argument(
        "--config",
        type=str,
        choices=["experiment", "tight", "generous", "long"],
        default="experiment",
        help="Use predefined configuration (default: experiment)"
    )
    parser.add_argument(
        "--hitl-json",
        type=str,
        help="JSON file with HITL result to compare"
    )
    parser.add_argument(
        "--hitl-api",
        type=str,
        default="http://localhost:8000",
        help="API URL for HITL workflow (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save report to file"
    )
    
    args = parser.parse_args()
    
    # Get configuration
    if args.config == "experiment":
        config = get_experiment_config()
    else:
        from config import get_test_scenario
        scenario_map = {
            "tight": "Tight Budget Multi-City",
            "generous": "Generous Budget Multi-City",
            "long": "Long Trip Many Cities"
        }
        config = get_test_scenario(scenario_map[args.config])
        if not config:
            print(f"❌ Scenario not found: {args.config}")
            return
    
    # Create TripBudget
    budget = TripBudget(
        origin=config["origin"],
        destinations=config["destinations"],
        departure_date=config["departure_date"],
        return_date=config["return_date"],
        adults=config["adults"],
        flight_budget=config["flight_budget"],
        hotel_budget=config["hotel_budget"],
        activity_budget=config["activity_budget"],
        max_iterations=config["max_iterations"]
    )
    
    # Run comparison
    await run_comparison(
        budget,
        hitl_result_file=args.hitl_json,
        hitl_api_url=args.hitl_api if args.hitl_api else None,
        save_report=not args.no_save
    )


if __name__ == "__main__":
    asyncio.run(main())

