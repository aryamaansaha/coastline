"""
Quantitative experiment runner for ReAct agent.

This module automates the 10-run quantitative experiment from the project report,
running the exact test case (MAD → ATH, ROM, $1500 budget) and collecting statistics.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.budget import TripBudget, BudgetResult
from app.services.budget_agent import BudgetAgentService

from config import (
    get_experiment_config,
    get_output_dir,
    EXPERIMENT_RUNNER_SETTINGS,
    AGENT_SETTINGS
)
from utils import (
    calculate_statistics,
    export_results_to_json,
    export_results_to_csv,
    format_result_summary,
    validate_result
)


async def run_single_experiment(
    run_number: int,
    total_runs: int,
    config: dict,
    retry_attempts: int = 2
) -> Optional[BudgetResult]:
    """
    Run a single experiment iteration.
    
    Args:
        run_number: Current run number (1-indexed)
        total_runs: Total number of runs
        config: Experiment configuration
        retry_attempts: Number of retry attempts on failure
        
    Returns:
        BudgetResult or None if all retries failed
    """
    print(f"\n{'='*70}")
    print(f"Run {run_number}/{total_runs}")
    print(f"{'='*70}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create TripBudget from config
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
    
    print(f"\n📋 Configuration:")
    print(f"   Origin: {budget.origin}")
    print(f"   Destinations: {budget.destinations}")
    print(f"   Dates: {budget.departure_date} to {budget.return_date}")
    print(f"   Adults: {budget.adults}")
    print(f"   ✈️  Flight Budget: ${budget.flight_budget:.2f}")
    print(f"   🏨 Hotel Budget:  ${budget.hotel_budget:.2f}")
    print(f"   🎯 Activity Budget: ${budget.activity_budget:.2f}")
    print(f"   🔄 Max Iterations: {budget.max_iterations}")
    
    # Retry logic
    for attempt in range(retry_attempts):
        try:
            print(f"\n🔄 Running ReAct agent (attempt {attempt + 1}/{retry_attempts})...")
            result = await BudgetAgentService.plan_trip_with_budget(budget)
            
            # Validate result
            if not validate_result(result):
                print(f"⚠️  Warning: Result validation failed")
            
            # Print summary
            print(f"\n{format_result_summary(result)}")
            
            return result
            
        except Exception as e:
            print(f"\n❌ Error on attempt {attempt + 1}: {str(e)}")
            if attempt < retry_attempts - 1:
                delay = EXPERIMENT_RUNNER_SETTINGS["error_retry_delay"]
                print(f"   Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                print(f"   All retry attempts exhausted")
                import traceback
                traceback.print_exc()
                return None
    
    return None


async def run_quantitative_experiment(
    num_runs: int = 10,
    config_override: Optional[dict] = None
) -> List[BudgetResult]:
    """
    Run the quantitative experiment multiple times.
    
    This runs the exact test case from the project report:
    - Origin: Madrid (MAD)
    - Destinations: Athens (ATH), Rome (ROM)
    - Budget: $1500 total
    - Expected: ReAct 6/10 success, HITL 9/10 success
    
    Args:
        num_runs: Number of runs to execute (default: 10)
        config_override: Optional dictionary to override experiment config
        
    Returns:
        List of BudgetResult objects
    """
    print("\n" + "="*70)
    print("QUANTITATIVE EXPERIMENT RUNNER")
    print("ReAct Agent: Multi-City Budget-Aware Trip Planning")
    print("="*70)
    print(f"\nStarting experiment with {num_runs} runs...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get configuration
    config = get_experiment_config()
    if config_override:
        config.update(config_override)
    
    config["num_runs"] = num_runs
    
    print(f"\n📋 Experiment Configuration:")
    print(f"   Origin: {config['origin']}")
    print(f"   Destinations: {config['destinations']}")
    print(f"   Dates: {config['departure_date']} to {config['return_date']}")
    print(f"   Budget: ${config['flight_budget']:.2f} flights + "
          f"${config['hotel_budget']:.2f} hotels + "
          f"${config['activity_budget']:.2f} activities")
    print(f"   Max Iterations: {config['max_iterations']}")
    print(f"   Number of Runs: {num_runs}")
    
    # Get settings
    runner_settings = EXPERIMENT_RUNNER_SETTINGS
    agent_settings = AGENT_SETTINGS
    
    print(f"\n⚙️  Settings:")
    print(f"   Iteration Delay: {agent_settings['iteration_delay']}s")
    print(f"   Error Retry Attempts: {runner_settings['error_retry_attempts']}")
    print(f"   Save Results: {runner_settings['save_results']}")
    
    # Run experiments
    results: List[BudgetResult] = []
    failed_runs = 0
    
    for run_num in range(1, num_runs + 1):
        result = await run_single_experiment(
            run_number=run_num,
            total_runs=num_runs,
            config=config,
            retry_attempts=runner_settings["error_retry_attempts"]
        )
        
        if result:
            results.append(result)
        else:
            failed_runs += 1
        
        # Progress update
        if run_num % runner_settings["progress_update_interval"] == 0:
            success_count = sum(1 for r in results if r.success)
            print(f"\n📊 Progress: {run_num}/{num_runs} runs complete")
            print(f"   Successful: {success_count}/{len(results)}")
            print(f"   Failed runs: {failed_runs}")
        
        # Delay between runs (rate limit avoidance)
        if run_num < num_runs:
            delay = agent_settings["iteration_delay"]
            print(f"\n⏳ Waiting {delay}s before next run (rate limit avoidance)...")
            await asyncio.sleep(delay)
    
    # Calculate statistics
    print("\n" + "="*70)
    print("EXPERIMENT COMPLETE")
    print("="*70)
    
    if not results:
        print("\n❌ No successful runs completed!")
        return []
    
    stats = calculate_statistics(results)
    
    print(f"\n📊 FINAL STATISTICS:")
    print(f"   Total Runs: {stats['total_runs']}")
    print(f"   Successful: {stats['success_count']} ({stats['success_rate']:.1f}%)")
    print(f"   Failed: {stats['total_runs'] - stats['success_count']}")
    print(f"   Average Iterations: {stats['average_iterations']:.2f}")
    print(f"   Std Dev Iterations: {stats['std_iterations']:.2f}")
    print(f"   Median Iterations: {stats['median_iterations']}")
    print(f"   Min Iterations: {stats['min_iterations']}")
    print(f"   Max Iterations: {stats['max_iterations']}")
    
    if stats['average_over_budget'] > 0:
        print(f"   Average Over Budget: ${stats['average_over_budget']:.2f}")
    
    if failed_runs > 0:
        print(f"\n⚠️  Warning: {failed_runs} runs failed completely")
    
    # Save results
    if runner_settings["save_results"]:
        timestamp = datetime.now().strftime(runner_settings["timestamp_format"])
        
        if runner_settings["save_json"]:
            json_file = f"experiment_results_{timestamp}.json"
            json_path = export_results_to_json(results, json_file)
            print(f"\n💾 Results saved to JSON: {json_path}")
        
        if runner_settings["save_csv"]:
            csv_file = f"experiment_results_{timestamp}.csv"
            csv_path = export_results_to_csv(results, csv_file)
            print(f"💾 Results saved to CSV: {csv_path}")
    
    print("\n" + "="*70)
    
    return results


async def main():
    """Main entry point for running the experiment."""
    import os
    from dotenv import load_dotenv
    
    # Check environment
    load_dotenv()
    
    openai_key = os.getenv("OPENAI_API_KEY")
    amadeus_id = os.getenv("AMADEUS_CLIENT_ID")
    amadeus_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    
    if not openai_key:
        print("❌ OPENAI_API_KEY not set in .env")
        return
    
    if not amadeus_id or not amadeus_secret:
        print("❌ AMADEUS_CLIENT_ID or AMADEUS_CLIENT_SECRET not set in .env")
        return
    
    print("✅ Environment variables configured")
    
    # Run experiment
    results = await run_quantitative_experiment(num_runs=10)
    
    if results:
        print(f"\n✅ Experiment completed with {len(results)} results")
    else:
        print("\n❌ Experiment failed - no results collected")


if __name__ == "__main__":
    asyncio.run(main())

