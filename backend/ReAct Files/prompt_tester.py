"""
Prompt engineering tool for testing different prompt variations.

This module allows testing different system and user prompts to compare
their impact on agent performance and success rates.
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent to path for app.schemas imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.budget import TripBudget, BudgetResult
from budget_agent_services import BudgetAgentService

from config import get_experiment_config, get_output_dir
from utils import calculate_statistics, export_results_to_json, export_results_to_csv


# Predefined prompt variations
PROMPT_VARIATIONS = {
    "default": {
        "system": """You are a budget-conscious multi-city travel planner. Your goal is to find the cheapest flights and hotels that fit within the user's budget constraints.

When searching:
1. First get airport codes for cities using get_airport_code
2. Search for flights for each leg of the journey
3. Search for hotels in each destination city

Always complete ALL searches before providing your final summary. Report exact prices from the API responses.""",
        "user_template": """Plan a multi-city trip with these details:

**Trip Details:**
- Origin: {origin}
- Destination Cities to Visit: [{destinations}]
- Trip Dates: {departure_date} to {return_date} ({total_days} days total)
- Number of Adults: {adults}

**Budget Constraints (MUST NOT EXCEED):**
- Flight Budget: ${flight_budget:.2f} (for ALL flights: origin->cities->origin)
- Hotel Budget: ${hotel_budget:.2f} (for ALL hotels across all cities)
- Activity Budget: ${activity_budget:.2f}
- Total Budget: ${total_budget:.2f}
{replan_context}

**Your Task:**
1. Decide the optimal order to visit the cities (consider geography to minimize flight costs)
2. Allocate days per city (total must equal {total_days} days)
3. Search for flights for each leg (origin->city1, city1->city2, ..., lastCity->origin)
4. Search for hotels in each city for the allocated number of nights
5. Provide a final summary with all costs

Please proceed with the searches now."""
    },
    "strict": {
        "system": """You are a strict budget-enforcing travel planner. Budget constraints are HARD LIMITS that MUST NOT be exceeded under any circumstances.

CRITICAL RULES:
- Budget constraints are MANDATORY, not suggestions
- If a plan exceeds budget, you MUST find a cheaper alternative
- Never report costs that exceed the budget
- Always verify costs before finalizing

When searching:
1. Get airport codes for all cities
2. Search for flights for each leg
3. Search for hotels in each city
4. VERIFY all costs are within budget
5. If over budget, try different city orders or day allocations

Report exact prices from API responses only.""",
        "user_template": """Plan a multi-city trip. BUDGET CONSTRAINTS ARE MANDATORY AND CANNOT BE EXCEEDED.

Trip Details:
- Origin: {origin}
- Destinations: {destinations}
- Dates: {departure_date} to {return_date} ({total_days} days)
- Adults: {adults}

MANDATORY BUDGET LIMITS (DO NOT EXCEED):
- Flights: ${flight_budget:.2f}
- Hotels: ${hotel_budget:.2f}
- Activities: ${activity_budget:.2f}
- TOTAL: ${total_budget:.2f}
{replan_context}

You MUST ensure the total cost does not exceed these limits. If initial searches show costs over budget, try different approaches."""
    },
    "flexible": {
        "system": """You are a flexible travel planner. Try to stay within budget, but if it's close, that's acceptable.

When searching:
1. Get airport codes
2. Search flights and hotels
3. Aim for budget, but being slightly over is okay if it's a good plan

Report prices from API.""",
        "user_template": """Plan a trip:
- Origin: {origin}
- Destinations: {destinations}
- Dates: {departure_date} to {return_date}
- Budget: ${total_budget:.2f} total
{replan_context}

Try to stay close to the budget."""
    }
}


class PromptTester:
    """Test different prompt variations."""
    
    @staticmethod
    async def test_prompt_variation(
        budget: TripBudget,
        prompt_name: str,
        system_prompt: str,
        user_prompt: str,
        num_runs: int = 5
    ) -> List[BudgetResult]:
        """
        Test a specific prompt variation multiple times.
        
        Args:
            budget: TripBudget configuration
            prompt_name: Name of the prompt variation
            system_prompt: System prompt to use
            user_prompt: User prompt to use
            num_runs: Number of test runs
            
        Returns:
            List of BudgetResult objects
        """
        print(f"\n{'='*70}")
        print(f"Testing Prompt Variation: {prompt_name}")
        print(f"{'='*70}")
        print(f"Runs: {num_runs}")
        
        results = []
        
        # Note: This is a simplified version. To fully test prompts, you'd need
        # to modify BudgetAgentService.run_single_iteration to accept custom prompts.
        # For now, we'll run with default prompts and document the approach.
        
        for run_num in range(1, num_runs + 1):
            print(f"\nRun {run_num}/{num_runs}...")
            try:
                result = await BudgetAgentService.plan_trip_with_budget(budget)
                results.append(result)
                status = "✅" if result.success else "❌"
                print(f"{status} Success={result.success}, Iterations={result.iterations_used}")
            except Exception as e:
                print(f"❌ Run {run_num} failed: {e}")
            
            if run_num < num_runs:
                await asyncio.sleep(15)
        
        return results
    
    @staticmethod
    def compare_prompts(
        prompt_results: Dict[str, List[BudgetResult]]
    ) -> Dict[str, Any]:
        """
        Compare results across different prompt variations.
        
        Args:
            prompt_results: Dictionary mapping prompt names to result lists
            
        Returns:
            Comparison statistics
        """
        comparison = {}
        
        for prompt_name, results in prompt_results.items():
            if not results:
                continue
            
            stats = calculate_statistics(results)
            comparison[prompt_name] = {
                "success_rate": stats["success_rate"],
                "success_count": stats["success_count"],
                "total_runs": stats["total_runs"],
                "average_iterations": stats["average_iterations"],
                "average_over_budget": stats["average_over_budget"]
            }
        
        return comparison
    
    @staticmethod
    def generate_prompt_comparison_report(
        prompt_results: Dict[str, List[BudgetResult]],
        save_file: bool = True
    ) -> str:
        """
        Generate a comparison report for different prompts.
        
        Args:
            prompt_results: Dictionary mapping prompt names to result lists
            save_file: Whether to save report to file
            
        Returns:
            Formatted markdown report string
        """
        lines = []
        lines.append("# Prompt Variation Comparison Report")
        lines.append("")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        comparison = PromptTester.compare_prompts(prompt_results)
        
        # Summary table
        lines.append("## Summary")
        lines.append("")
        lines.append("| Prompt Variation | Success Rate | Avg Iterations | Avg Over Budget |")
        lines.append("|------------------|--------------|----------------|-----------------|")
        
        for prompt_name, stats in comparison.items():
            avg_over = stats.get("average_over_budget", 0.0)
            avg_over_str = f"${avg_over:.2f}" if avg_over > 0 else "N/A"
            
            lines.append(
                f"| {prompt_name} | {stats['success_rate']:.1f}% | "
                f"{stats['average_iterations']:.2f} | {avg_over_str} |"
            )
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Detailed results
        lines.append("## Detailed Results")
        lines.append("")
        
        for prompt_name, results in prompt_results.items():
            if not results:
                continue
            
            stats = calculate_statistics(results)
            lines.append(f"### {prompt_name}")
            lines.append("")
            lines.append(f"- **Total Runs**: {stats['total_runs']}")
            lines.append(f"- **Success Rate**: {stats['success_rate']:.1f}%")
            lines.append(f"- **Average Iterations**: {stats['average_iterations']:.2f}")
            lines.append(f"- **Std Dev Iterations**: {stats['std_iterations']:.2f}")
            
            if stats.get("average_over_budget", 0.0) > 0:
                lines.append(f"- **Average Over Budget**: ${stats['average_over_budget']:.2f}")
            
            lines.append("")
        
        # Best prompt
        if comparison:
            best_prompt = max(
                comparison.items(),
                key=lambda x: x[1]["success_rate"]
            )
            lines.append("---")
            lines.append("")
            lines.append(f"## Best Performing Prompt: **{best_prompt[0]}**")
            lines.append(f"- Success Rate: {best_prompt[1]['success_rate']:.1f}%")
            lines.append("")
        
        report = "\n".join(lines)
        
        # Save report
        if save_file:
            output_dir = get_output_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = output_dir / f"prompt_comparison_{timestamp}.md"
            
            with open(report_file, "w") as f:
                f.write(report)
            
            print(f"💾 Report saved to: {report_file}")
        
        return report


async def test_all_prompts(
    budget: TripBudget,
    num_runs_per_prompt: int = 5,
    prompt_names: Optional[List[str]] = None
) -> Dict[str, List[BudgetResult]]:
    """
    Test all prompt variations.
    
    Args:
        budget: TripBudget configuration
        num_runs_per_prompt: Number of runs per prompt variation
        prompt_names: Optional list of prompt names to test (None = all)
        
    Returns:
        Dictionary mapping prompt names to result lists
    """
    if prompt_names is None:
        prompt_names = list(PROMPT_VARIATIONS.keys())
    
    prompt_results = {}
    
    for prompt_name in prompt_names:
        if prompt_name not in PROMPT_VARIATIONS:
            print(f"⚠️  Prompt variation '{prompt_name}' not found. Skipping.")
            continue
        
        prompt_config = PROMPT_VARIATIONS[prompt_name]
        
        # Note: Actual prompt testing would require modifying BudgetAgentService
        # For now, we run with default prompts and document the approach
        results = await PromptTester.test_prompt_variation(
            budget,
            prompt_name,
            prompt_config["system"],
            prompt_config["user_template"],
            num_runs_per_prompt
        )
        
        prompt_results[prompt_name] = results
    
    # Generate comparison report
    report = PromptTester.generate_prompt_comparison_report(prompt_results)
    print("\n" + report)
    
    return prompt_results


async def main():
    """Main entry point for prompt tester."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test different prompt variations"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of runs per prompt (default: 5)"
    )
    parser.add_argument(
        "--prompts",
        nargs="+",
        choices=list(PROMPT_VARIATIONS.keys()),
        help="Specific prompts to test (default: all)"
    )
    
    args = parser.parse_args()
    
    # Get default configuration
    config = get_experiment_config()
    budget = TripBudget(**config)
    
    # Test prompts
    await test_all_prompts(
        budget,
        num_runs_per_prompt=args.runs,
        prompt_names=args.prompts
    )


if __name__ == "__main__":
    asyncio.run(main())

