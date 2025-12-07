"""
Test script for agent_graph_v2.py

Tests various scenarios:
1. Single-city trip (round-trip)
2. Multi-city trip (one-way flights between cities)
3. Budget-constrained trip
4. Weekend getaway (short trip)

Usage:
    python test_agent_v2.py                    # Run all tests (auto-approve mode)
    python test_agent_v2.py --test single      # Run single test
    python test_agent_v2.py --test multi       # Run multi-city test
    python test_agent_v2.py --test budget      # Run budget test
    python test_agent_v2.py --test weekend     # Run weekend test
    python test_agent_v2.py -i                 # Interactive mode (human review)
    python test_agent_v2.py --test single -i   # Single test with interactive mode
"""

import asyncio
import json
from datetime import datetime, timedelta
from agent_graph_v2 import run_agent_with_preferences
from dotenv import load_dotenv
import sys

load_dotenv()

# Global flag for interactive mode (set via CLI)
INTERACTIVE_MODE = False


def print_separator(title=""):
    """Print a nice separator"""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'='*80}\n")


def print_result_summary(result: dict):
    """Print a clean summary of the agent result"""
    print_separator("📊 FINAL RESULT SUMMARY")
    
    if not result.get("success"):
        print("❌ Agent failed to generate a valid itinerary")
        return
    
    print(f"✅ Status: {'APPROVED' if result['success'] else 'FAILED'}")
    print(f"💰 Total Cost: ${result['total_cost']:.2f}")
    print(f"🎯 Budget Limit: ${result['budget_limit']:.2f}")
    print(f"📊 Budget Status: {result['budget_status'].upper()}")
    
    if result.get("cost_breakdown"):
        print(f"\n💵 Cost Breakdown:")
        for category, amount in result["cost_breakdown"].items():
            print(f"   - {category.capitalize()}: ${amount:.2f}")
    
    itinerary = result.get("itinerary")
    if itinerary:
        print(f"\n📅 Trip: {itinerary.get('trip_title', 'N/A')}")
        print(f"🗓️  Days: {len(itinerary.get('days', []))}")
        
        # Show day-by-day breakdown
        for day in itinerary.get("days", []):
            day_num = day.get("day_number", "?")
            theme = day.get("theme", "N/A")
            city = day.get("city", "N/A")
            activity_count = len(day.get("activities", []))
            print(f"   Day {day_num} ({city}): {theme} - {activity_count} activities")


async def test_single_city():
    """Test 1: Single-city round-trip (NYC to London)"""
    print_separator("🧪 TEST 1: Single-City Round-Trip")
    
    # Use dates 2 months in the future
    start_date = datetime.now() + timedelta(days=60)
    end_date = start_date + timedelta(days=5)
    
    preferences = {
        "destinations": ["London"],
        "origin": "New York",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "budget_limit": 2500.0
    }
    
    print(f"📍 Destination: {preferences['destinations'][0]}")
    print(f"🛫 Origin: {preferences['origin']}")
    print(f"📅 Dates: {preferences['start_date']} to {preferences['end_date']}")
    print(f"💰 Budget: ${preferences['budget_limit']:.2f}")
    
    result = await run_agent_with_preferences(preferences, debug=True, interactive=INTERACTIVE_MODE)
    print_result_summary(result)
    
    return result


async def test_multi_city():
    """Test 2: Multi-city trip (NYC → London → Paris → Copenhagen → NYC)"""
    print_separator("🧪 TEST 2: Multi-City European Tour")
    
    # Use dates 3 months in the future for longer trip
    start_date = datetime.now() + timedelta(days=90)
    end_date = start_date + timedelta(days=10)
    
    preferences = {
        "destinations": ["London", "Paris", "Copenhagen"],
        "origin": "New York",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "budget_limit": 5000.0
    }
    
    print(f"📍 Destinations: {', '.join(preferences['destinations'])}")
    print(f"🛫 Origin: {preferences['origin']}")
    print(f"📅 Dates: {preferences['start_date']} to {preferences['end_date']}")
    print(f"💰 Budget: ${preferences['budget_limit']:.2f}")
    
    result = await run_agent_with_preferences(preferences, debug=True, interactive=INTERACTIVE_MODE)
    print_result_summary(result)
    
    return result


async def test_budget_constrained():
    """Test 3: Tight budget to test revision loop"""
    print_separator("🧪 TEST 3: Budget-Constrained Trip")
    
    start_date = datetime.now() + timedelta(days=45)
    end_date = start_date + timedelta(days=4)
    
    preferences = {
        "destinations": ["Miami"],
        "origin": "New York",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "budget_limit": 800.0  # Intentionally tight
    }
    
    print(f"📍 Destination: {preferences['destinations'][0]}")
    print(f"🛫 Origin: {preferences['origin']}")
    print(f"📅 Dates: {preferences['start_date']} to {preferences['end_date']}")
    print(f"💰 Budget: ${preferences['budget_limit']:.2f} (TIGHT!)")
    print(f"⚠️  This should trigger budget revision...")
    
    result = await run_agent_with_preferences(preferences, debug=True, interactive=INTERACTIVE_MODE)
    print_result_summary(result)
    
    return result


async def test_weekend_getaway():
    """Test 4: Quick weekend trip"""
    print_separator("🧪 TEST 4: Weekend Getaway")
    
    # Next weekend (roughly)
    start_date = datetime.now() + timedelta(days=14)
    end_date = start_date + timedelta(days=2)
    
    preferences = {
        "destinations": ["Boston"],
        "origin": "New York",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "budget_limit": 600.0
    }
    
    print(f"📍 Destination: {preferences['destinations'][0]}")
    print(f"🛫 Origin: {preferences['origin']}")
    print(f"📅 Dates: {preferences['start_date']} to {preferences['end_date']} (weekend)")
    print(f"💰 Budget: ${preferences['budget_limit']:.2f}")
    
    result = await run_agent_with_preferences(preferences, debug=True, interactive=INTERACTIVE_MODE)
    print_result_summary(result)
    
    return result


async def run_all_tests():
    """Run all test scenarios"""
    print_separator("🚀 RUNNING ALL TEST SCENARIOS")
    
    tests = [
        ("Single City", test_single_city),
        ("Multi City", test_multi_city),
        ("Budget Constrained", test_budget_constrained),
        ("Weekend Getaway", test_weekend_getaway)
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            print(f"\n\n🔄 Starting: {name}")
            result = await test_func()
            results[name] = {
                "success": result.get("success", False),
                "cost": result.get("total_cost"),
                "budget": result.get("budget_limit")
            }
        except Exception as e:
            print(f"\n❌ Test '{name}' failed with error: {e}")
            results[name] = {"success": False, "error": str(e)}
    
    # Final summary
    print_separator("📊 ALL TESTS COMPLETE")
    for name, result in results.items():
        status = "✅" if result.get("success") else "❌"
        if "error" in result:
            print(f"{status} {name}: ERROR - {result['error']}")
        else:
            cost = result.get("cost", 0)
            budget = result.get("budget", 0)
            print(f"{status} {name}: ${cost:.2f} / ${budget:.2f}")


def main():
    """Main entry point"""
    global INTERACTIVE_MODE
    
    # Parse command line args
    test_name = None
    args = sys.argv[1:]
    
    # Check for interactive mode flag
    if "-i" in args or "--interactive" in args:
        INTERACTIVE_MODE = True
        args = [a for a in args if a not in ["-i", "--interactive"]]
        print("🖐️  Interactive mode enabled - you will review each itinerary")
    
    # Parse test name
    if "--test" in args:
        idx = args.index("--test")
        if idx + 1 < len(args):
            test_name = args[idx + 1]
    
    # Map test names to functions
    tests = {
        "single": test_single_city,
        "multi": test_multi_city,
        "budget": test_budget_constrained,
        "weekend": test_weekend_getaway,
        "all": run_all_tests
    }
    
    if test_name:
        if test_name not in tests:
            print(f"❌ Unknown test: {test_name}")
            print(f"Available tests: {', '.join(tests.keys())}")
            sys.exit(1)
        
        asyncio.run(tests[test_name]())
    else:
        # Default: run single test (easier for interactive mode)
        if INTERACTIVE_MODE:
            print("Running single city test (default for interactive mode)")
            asyncio.run(test_single_city())
        else:
            asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()

