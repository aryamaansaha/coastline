"""
Example usage of the Travel Preference Knowledge Graph.

Make sure FalkorDB is running:
    docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest

And set your OpenAI API key:
    export OPENAI_API_KEY=your-key-here
"""

import asyncio
from preference_graph import PreferenceGraph


# Sample trip data
TRIP_1_INPUT = """
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

TRIP_2_INPUT = """
Initial Q/A:

Q: What activities interest you?
A: I love trying local food and exploring street markets

Q: Accommodation preferences?
A: Something central, doesn't need to be fancy

Q: Any must-dos?
A: I'd love to take a cooking class!

Chat History:

turn 1: Can we squeeze in a museum visit? I really enjoy art museums.
turn 2: The hotel looks fine, just book it.
"""


async def main():
    print("=" * 60)
    print("Travel Preference Knowledge Graph Demo")
    print("=" * 60)

    # Initialize the graph
    pg = PreferenceGraph()
    await pg.initialize()
    print("\n✓ Connected to FalkorDB\n")

    # --- Process Trip 1 ---
    print("-" * 40)
    print("Processing Trip 1...")
    print("-" * 40)

    summary1 = await pg.summarize_preferences(TRIP_1_INPUT)
    print(f"\nExtracted preferences:\n{summary1}\n")

    await pg.store_preferences(summary1, trip_name="trip_1")
    print("✓ Stored in knowledge graph\n")

    # --- Process Trip 2 ---
    print("-" * 40)
    print("Processing Trip 2...")
    print("-" * 40)

    summary2 = await pg.summarize_preferences(TRIP_2_INPUT)
    print(f"\nExtracted preferences:\n{summary2}\n")

    await pg.store_preferences(summary2, trip_name="trip_2")
    print("✓ Stored in knowledge graph\n")

    # --- Query the graph ---
    print("=" * 60)
    print("Querying Historical Preferences")
    print("=" * 60)

    # Query 1: Attractions
    print("\n📍 Query: What tourist attractions does the user like?")
    attractions = await pg.get_preferences("What tourist attractions does the user like?")
    print(f"Response: {attractions}\n")

    # Query 2: Pace
    print("🏃 Query: What pace of travel does the user prefer?")
    pace = await pg.get_preferences("What pace of travel does the user prefer?")
    print(f"Response: {pace}\n")

    # Query 3: Food preferences
    print("🍜 Query: What are the user's food and dining preferences?")
    food = await pg.get_preferences("What are the user's food and dining preferences?")
    print(f"Response: {food}\n")

    # Query 4: Social preferences
    print("👥 Query: Does the user like meeting locals or social activities?")
    social = await pg.get_preferences("Does the user like meeting locals or social activities?")
    print(f"Response: {social}\n")

    # Get all preferences
    print("=" * 60)
    print("All Stored Preferences")
    print("=" * 60)
    all_prefs = await pg.get_all_preferences()
    for i, pref in enumerate(all_prefs, 1):
        print(f"  {i}. {pref}")

    # Cleanup
    await pg.close()
    print("\n✓ Connection closed")


if __name__ == "__main__":
    asyncio.run(main())


