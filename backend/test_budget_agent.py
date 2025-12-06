"""
Test script for Multi-City Budget-Aware ReAct Agent.
Tests the agent with different multi-city budget scenarios using real MCP calls.

Usage:
    cd backend
    python test_budget_agent.py

Requirements:
    - OPENAI_API_KEY set in .env
    - AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET set in .env
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the app directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from app.schemas.budget import TripBudget
from app.services.budget_agent import BudgetAgentService


def print_result(result, test_name: str):
    """Pretty print the multi-city budget result."""
    print(f"\n{'='*70}")
    print(f"RESULT: {test_name}")
    print('='*70)
    
    status_icon = "✅" if result.success else "❌"
    print(f"\n{status_icon} Success: {result.success}")
    print(f"📝 Message: {result.message}")
    print(f"🔄 Iterations Used: {result.iterations_used}")
    
    if result.best_plan_over_budget:
        print(f"💸 Over Budget By: ${result.best_plan_over_budget:.2f}")
    
    if result.breakdown:
        print(f"\n📍 TRIP PLAN:")
        print("-" * 50)
        if result.breakdown.city_order:
            print(f"   Route: {' → '.join(result.breakdown.city_order)}")
        if result.breakdown.days_per_city:
            days_str = ", ".join([f"{city}: {days} days" for city, days in result.breakdown.days_per_city.items()])
            print(f"   Days: {days_str}")
        
        print(f"\n✈️  FLIGHT SEGMENTS:")
        print("-" * 50)
        if result.breakdown.flight_segments:
            for seg in result.breakdown.flight_segments:
                estimate_tag = " (estimate)" if seg.is_estimate else ""
                airline_str = f" [{seg.airline}]" if seg.airline else ""
                print(f"   {seg.from_city} → {seg.to_city}: ${seg.cost:.2f}{airline_str}{estimate_tag}")
        else:
            print("   No flight segments found")
        
        if result.breakdown.transport_estimates:
            print(f"\n🚆 PUBLIC TRANSPORT ESTIMATES:")
            print("-" * 50)
            for est in result.breakdown.transport_estimates:
                print(f"   {est.from_city} → {est.to_city}: ~${est.estimated_cost:.2f} ({est.transport_type})")
        
        print(f"\n🏨 HOTEL STAYS:")
        print("-" * 50)
        if result.breakdown.hotel_stays:
            for stay in result.breakdown.hotel_stays:
                hotel_name = f" - {stay.hotel_name}" if stay.hotel_name else ""
                ppn = f" (${stay.price_per_night:.2f}/night)" if stay.price_per_night else ""
                print(f"   {stay.city}: {stay.nights} nights = ${stay.cost:.2f}{ppn}{hotel_name}")
        else:
            print("   No hotel stays found")
        
        print(f"\n💰 BUDGET BREAKDOWN:")
        print("-" * 50)
        
        # Flight
        flight_icon = "✅" if result.breakdown.flight_within_budget else "❌"
        if result.breakdown.flight_cost is not None:
            print(f"   ✈️  Flights: ${result.breakdown.flight_cost:.2f} / ${result.breakdown.flight_budget:.2f} {flight_icon}")
        else:
            print(f"   ✈️  Flights: Unknown / ${result.breakdown.flight_budget:.2f} {flight_icon}")
        
        # Hotel
        hotel_icon = "✅" if result.breakdown.hotel_within_budget else "❌"
        if result.breakdown.hotel_cost is not None:
            print(f"   🏨 Hotels:  ${result.breakdown.hotel_cost:.2f} / ${result.breakdown.hotel_budget:.2f} {hotel_icon}")
        else:
            print(f"   🏨 Hotels:  Unknown / ${result.breakdown.hotel_budget:.2f} {hotel_icon}")
        
        # Activity
        activity_icon = "✅" if result.breakdown.activity_within_budget else "❌"
        print(f"   🎯 Activities: ${result.breakdown.activity_cost:.2f} / ${result.breakdown.activity_budget:.2f} {activity_icon}")
        
        print("-" * 50)
        print(f"   💵 TOTAL: ${result.breakdown.total_cost:.2f} / ${result.breakdown.total_budget:.2f}")
    
    if result.budget_errors:
        print(f"\n⚠️  BUDGET ERRORS:")
        for error in result.budget_errors:
            print(f"   • {error}")
    
    if result.agent_reasoning:
        print(f"\n🤖 AGENT REASONING:")
        print("-" * 50)
        reasoning = result.agent_reasoning
        if len(reasoning) > 1500:
            reasoning = reasoning[:1500] + "\n... [truncated]"
        print(reasoning)


async def test_tight_budget_multi_city():
    """Test with a tight budget for 3 cities (should fail/replan multiple times)."""
    print("\n" + "="*70)
    print("TEST CASE 1: Tight Budget Multi-City (MAD → ATH, ROM, PAR)")
    print("Expected: Will need multiple iterations, may not meet budget")
    print("="*70)
    
    budget = TripBudget(
        origin="MAD",
        destinations=["ATH", "ROM", "PAR"],  # Athens, Rome, Paris
        departure_date="2026-01-01",
        return_date="2026-01-10",  # 9 days
        adults=2,
        flight_budget=800.00,     # Tight for 4 flight legs
        hotel_budget=600.00,      # Tight for 9 nights across 3 cities
        activity_budget=200.00,
        max_iterations=5
    )
    
    print(f"\n📋 Input:")
    print(f"   Origin: {budget.origin}")
    print(f"   Destinations: {budget.destinations}")
    print(f"   Dates: {budget.departure_date} to {budget.return_date}")
    print(f"   Adults: {budget.adults}")
    print(f"   ✈️  Flight Budget: ${budget.flight_budget:.2f}")
    print(f"   🏨 Hotel Budget:  ${budget.hotel_budget:.2f}")
    print(f"   🎯 Activity Budget: ${budget.activity_budget:.2f}")
    print(f"   🔄 Max Iterations: {budget.max_iterations}")
    
    print("\n🔄 Running ReAct agent (this may take 2-5 minutes for multi-city)...")
    result = await BudgetAgentService.plan_trip_with_budget(budget)
    
    print_result(result, "Tight Budget Multi-City Test")
    
    return result


async def test_generous_budget_multi_city():
    """Test with a generous budget for 2 cities (should pass easily)."""
    print("\n" + "="*70)
    print("TEST CASE 2: Generous Budget Multi-City (MAD → ATH, ROM)")
    print("Expected: Should pass in 1-2 iterations")
    print("="*70)
    
    budget = TripBudget(
        origin="MAD",
        destinations=["ATH", "ROM"],  # Athens, Rome
        departure_date="2026-01-01",
        return_date="2026-01-08",  # 7 days
        adults=2,
        flight_budget=1500.00,    # Generous for 3 flight legs
        hotel_budget=1500.00,     # Generous for 7 nights
        activity_budget=400.00,
        max_iterations=5
    )
    
    print(f"\n📋 Input:")
    print(f"   Origin: {budget.origin}")
    print(f"   Destinations: {budget.destinations}")
    print(f"   Dates: {budget.departure_date} to {budget.return_date}")
    print(f"   Adults: {budget.adults}")
    print(f"   ✈️  Flight Budget: ${budget.flight_budget:.2f}")
    print(f"   🏨 Hotel Budget:  ${budget.hotel_budget:.2f}")
    print(f"   🎯 Activity Budget: ${budget.activity_budget:.2f}")
    print(f"   🔄 Max Iterations: {budget.max_iterations}")
    
    print("\n🔄 Running ReAct agent (this may take 1-3 minutes)...")
    result = await BudgetAgentService.plan_trip_with_budget(budget)
    
    print_result(result, "Generous Budget Multi-City Test")
    
    return result


async def test_long_trip_many_cities():
    """Test with many cities over a longer trip."""
    print("\n" + "="*70)
    print("TEST CASE 3: Long Trip - NYC → LON, PAR, ROM, ATH")
    print("Expected: Complex planning, may need several iterations")
    print("="*70)
    
    budget = TripBudget(
        origin="NYC",
        destinations=["LON", "PAR", "ROM", "ATH"],  # London, Paris, Rome, Athens
        departure_date="2026-01-01",
        return_date="2026-01-15",  # 14 days
        adults=2,
        flight_budget=3000.00,    # Transatlantic + European flights
        hotel_budget=2500.00,     # 14 nights across 4 cities
        activity_budget=800.00,
        max_iterations=5
    )
    
    print(f"\n📋 Input:")
    print(f"   Origin: {budget.origin}")
    print(f"   Destinations: {budget.destinations}")
    print(f"   Dates: {budget.departure_date} to {budget.return_date}")
    print(f"   Adults: {budget.adults}")
    print(f"   ✈️  Flight Budget: ${budget.flight_budget:.2f}")
    print(f"   🏨 Hotel Budget:  ${budget.hotel_budget:.2f}")
    print(f"   🎯 Activity Budget: ${budget.activity_budget:.2f}")
    print(f"   🔄 Max Iterations: {budget.max_iterations}")
    
    print("\n🔄 Running ReAct agent (this may take 3-6 minutes for 4 cities)...")
    result = await BudgetAgentService.plan_trip_with_budget(budget)
    
    print_result(result, "Long Trip Many Cities Test")
    
    return result


def check_env():
    """Check if required environment variables are set."""
    print("\n" + "="*70)
    print("🔑 ENVIRONMENT CHECK")
    print("="*70)
    
    openai_key = os.getenv("OPENAI_API_KEY")
    amadeus_id = os.getenv("AMADEUS_CLIENT_ID")
    amadeus_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    
    all_set = True
    
    if openai_key:
        print(f"✅ OPENAI_API_KEY: {openai_key[:20]}...")
    else:
        print("❌ OPENAI_API_KEY: NOT SET")
        all_set = False
    
    if amadeus_id:
        print(f"✅ AMADEUS_CLIENT_ID: {amadeus_id[:10]}...")
    else:
        print("❌ AMADEUS_CLIENT_ID: NOT SET")
        all_set = False
    
    if amadeus_secret:
        print(f"✅ AMADEUS_CLIENT_SECRET: {amadeus_secret[:10]}...")
    else:
        print("❌ AMADEUS_CLIENT_SECRET: NOT SET")
        all_set = False
    
    return all_set


async def main():
    """Run all test cases."""
    print("\n" + "="*70)
    print("🧪 MULTI-CITY BUDGET-AWARE REACT AGENT TEST SUITE")
    print("    Using LangGraph + GPT-4 + MCP (Amadeus API)")
    print("    With Iterative Replanning (max 5 iterations)")
    print("="*70)
    
    # Check environment
    if not check_env():
        print("\n❌ Missing API keys! Please set them in backend/.env")
        print("\nRequired keys:")
        print("  OPENAI_API_KEY=sk-...")
        print("  AMADEUS_CLIENT_ID=...")
        print("  AMADEUS_CLIENT_SECRET=...")
        return
    
    print("\n✅ All API keys configured!")
    print("\n🚀 Starting tests...")
    print("   Note: Multi-city tests make multiple API calls and may take several minutes.\n")
    
    # Run tests
    results = []
    
    # Test 1: Tight budget (likely to fail or need many iterations)
    try:
        result1 = await test_tight_budget_multi_city()
        results.append(("Tight Budget (3 cities)", result1))
    except Exception as e:
        print(f"\n❌ Test 1 failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Generous budget (should pass easily)
    try:
        result2 = await test_generous_budget_multi_city()
        results.append(("Generous Budget (2 cities)", result2))
    except Exception as e:
        print(f"\n❌ Test 2 failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    # Uncomment to run the long trip test (takes longer)
    # try:
    #     result3 = await test_long_trip_many_cities()
    #     results.append(("Long Trip (4 cities)", result3))
    # except Exception as e:
    #     print(f"\n❌ Test 3 failed with error: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    for name, result in results:
        if result.success:
            status = f"✅ PASS (in {result.iterations_used} iteration(s))"
        else:
            if result.best_plan_over_budget:
                status = f"❌ OVER BUDGET by ${result.best_plan_over_budget:.2f} (after {result.iterations_used} iterations)"
            else:
                status = f"❌ FAIL (after {result.iterations_used} iterations)"
        print(f"   {name}: {status}")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
