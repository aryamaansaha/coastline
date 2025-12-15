"""
Test script to verify the preference knowledge graph is working.
"""

import asyncio
from preference_graph import (
    summarize_and_store,
    get_preferences,
    get_all_user_preferences,
    cleanup,
)


# Example conversation from your design doc
SAMPLE_CONVERSATION = """
Initial Q/A: 

Q: What would you like to see more of?
A: museums, maybe some beaches

Q: What pace would you like this trip?
A: pretty intense, wanna visit as many as possible

Q: Specific requests?
A: Would really like to spend a day meeting locals!

Chat History:

turn 1: the flights are kinda expensive, see if there are cheaper options? Also, include museums in the plan possible
turn 2: i've increased the budget, allocate more towards shopping at the luxury market.
"""


async def test_store_preferences():
    """Test extracting and storing preferences."""
    print("=" * 60)
    print("STEP 1: Extracting and storing preferences")
    print("=" * 60)
    
    summary = await summarize_and_store(
        conversation=SAMPLE_CONVERSATION,
        trip_context="test_trip_1"
    )
    
    print("\nExtracted preferences:")
    print(summary)
    print()


async def test_query_preferences():
    """Test querying specific preferences."""
    print("=" * 60)
    print("STEP 2: Querying specific preferences")
    print("=" * 60)
    
    queries = [
        "What kind of tourist attractions does the user like?",
        "What level of pace does the user prefer for trips?",
        "Does the user like meeting locals?",
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        result = await get_preferences(query)
        print(f"Result: {result}")
    print()


async def test_get_all_preferences():
    """Test getting all categorized preferences."""
    print("=" * 60)
    print("STEP 3: Getting all categorized preferences")
    print("=" * 60)
    
    all_prefs = await get_all_user_preferences()
    
    for category, prefs in all_prefs.items():
        print(f"\n{category.upper()}:")
        print(prefs)
    print()


async def main():
    """Run all tests."""
    try:
        await test_store_preferences()
        await test_query_preferences()
        await test_get_all_preferences()
        
        print("=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
        
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())

