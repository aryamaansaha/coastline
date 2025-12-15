"""
Configuration and constants for ReAct agent experiments.

This module centralizes all experiment parameters, test scenarios, and agent settings
for the ReAct agent implementation used in comparative studies.
"""

from pathlib import Path
from typing import Dict, List, Any

# Base directory for ReAct Files
REACT_FILES_DIR = Path(__file__).parent

# Output directory for experiment results
OUTPUT_DIR = REACT_FILES_DIR / "experiment_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================================
# QUANTITATIVE EXPERIMENT CONFIGURATION
# ============================================================================
# This is the exact test case from the project report:
# - Origin: Madrid (MAD)
# - Destinations: Athens (ATH), Rome (ROM)
# - Budget: $1500 total
# - Expected: ReAct 6/10 success, HITL 9/10 success

EXPERIMENT_CONFIG: Dict[str, Any] = {
    "origin": "MAD",
    "destinations": ["ATH", "ROM"],
    "departure_date": "2026-01-01",
    "return_date": "2026-01-10",
    "adults": 2,
    "flight_budget": 1500.0,
    "hotel_budget": 1200.0,
    "activity_budget": 400.0,
    "max_iterations": 5,
    "num_runs": 10
}

# ============================================================================
# TEST SCENARIOS
# ============================================================================
# Predefined test scenarios for various budget conditions

TEST_SCENARIOS: List[Dict[str, Any]] = [
    {
        "name": "Tight Budget Multi-City",
        "description": "3 cities with tight budget (likely to need replanning)",
        "origin": "MAD",
        "destinations": ["ATH", "ROM", "PAR"],
        "departure_date": "2026-01-01",
        "return_date": "2026-01-10",
        "adults": 2,
        "flight_budget": 800.0,
        "hotel_budget": 600.0,
        "activity_budget": 200.0,
        "max_iterations": 5
    },
    {
        "name": "Generous Budget Multi-City",
        "description": "2 cities with generous budget (should pass easily)",
        "origin": "MAD",
        "destinations": ["ATH", "ROM"],
        "departure_date": "2026-01-01",
        "return_date": "2026-01-08",
        "adults": 2,
        "flight_budget": 1500.0,
        "hotel_budget": 1500.0,
        "activity_budget": 400.0,
        "max_iterations": 5
    },
    {
        "name": "Long Trip Many Cities",
        "description": "4 cities over 14 days (complex planning)",
        "origin": "NYC",
        "destinations": ["LON", "PAR", "ROM", "ATH"],
        "departure_date": "2026-01-01",
        "return_date": "2026-01-15",
        "adults": 2,
        "flight_budget": 3000.0,
        "hotel_budget": 2500.0,
        "activity_budget": 800.0,
        "max_iterations": 5
    },
    {
        "name": "Quantitative Experiment",
        "description": "Exact test case from project report (MAD → ATH, ROM, $1500)",
        "origin": "MAD",
        "destinations": ["ATH", "ROM"],
        "departure_date": "2026-01-01",
        "return_date": "2026-01-10",
        "adults": 2,
        "flight_budget": 1500.0,
        "hotel_budget": 1200.0,
        "activity_budget": 400.0,
        "max_iterations": 5
    }
]

# ============================================================================
# AGENT SETTINGS
# ============================================================================
# Default configuration for the ReAct agent

AGENT_SETTINGS: Dict[str, Any] = {
    "model": "gpt-4o",  # OpenAI model to use
    "temperature": 0.2,  # Lower temperature for more consistent results
    "max_turns": 20,  # Maximum tool calling turns per iteration
    "max_retries": 3,  # Retry attempts for rate limits
    "retry_delay": 10,  # Seconds to wait between retries
    "iteration_delay": 15,  # Seconds to wait between planning iterations (rate limit avoidance)
    "early_stop_threshold": 50.0,  # Stop iterations if within $50 of budget
}

# ============================================================================
# HITL BASELINE RESULTS
# ============================================================================
# Expected results from HITL workflow for comparison
# Based on project report: 9/10 success rate

HITL_BASELINE_RESULTS: Dict[str, Any] = {
    "success_rate": 0.90,  # 9 out of 10
    "success_count": 9,
    "total_runs": 10,
    "average_iterations": 1.5,  # Estimated (HITL typically needs fewer iterations)
    "average_over_budget": 0.0,  # HITL enforces hard constraints
    "description": "HITL workflow results from quantitative experiment"
}

# ============================================================================
# EXPERIMENT RUNNER SETTINGS
# ============================================================================

EXPERIMENT_RUNNER_SETTINGS: Dict[str, Any] = {
    "save_results": True,  # Whether to save results to files
    "save_json": True,  # Save JSON format
    "save_csv": True,  # Save CSV format
    "save_markdown": True,  # Save markdown report
    "timestamp_format": "%Y%m%d_%H%M%S",  # Timestamp format for filenames
    "progress_update_interval": 1,  # Print progress every N runs
    "error_retry_attempts": 2,  # Retry failed runs
    "error_retry_delay": 30,  # Seconds to wait before retrying failed run
}

# ============================================================================
# RESULTS ANALYZER SETTINGS
# ============================================================================

RESULTS_ANALYZER_SETTINGS: Dict[str, Any] = {
    "include_visualizations": False,  # Generate plots (requires matplotlib)
    "detailed_breakdown": True,  # Include detailed cost breakdowns
    "compare_with_hitl": True,  # Compare with HITL baseline
    "export_formats": ["json", "markdown"],  # Export formats
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_experiment_config() -> Dict[str, Any]:
    """Get the quantitative experiment configuration."""
    return EXPERIMENT_CONFIG.copy()

def get_test_scenario(name: str) -> Dict[str, Any] | None:
    """Get a test scenario by name."""
    for scenario in TEST_SCENARIOS:
        if scenario["name"] == name:
            return scenario.copy()
    return None

def get_agent_settings() -> Dict[str, Any]:
    """Get agent settings."""
    return AGENT_SETTINGS.copy()

def get_hitl_baseline() -> Dict[str, Any]:
    """Get HITL baseline results for comparison."""
    return HITL_BASELINE_RESULTS.copy()

def get_output_dir() -> Path:
    """Get the output directory for experiment results."""
    return OUTPUT_DIR

