"""
Coastline Agent Test - LangGraph + GPT-4 + MCP
===============================================
This script creates an AI agent that uses MCP to search for flights and hotels.

Architecture:
    User Request → LangGraph Agent (GPT-4) → MCP Client → MCP Server → Amadeus API
                                           ↑
                                    Tools discovered via MCP

The agent:
1. Connects to the MCP server as a client
2. Discovers available tools (search_flights, search_hotels)
3. Uses GPT-4 to reason about which tools to call
4. Executes tools via MCP protocol
5. Generates a complete travel itinerary

Usage:
    python agent_test.py

Requirements:
    pip install langchain-mcp-adapters langgraph langchain-openai
    
    Environment variables:
    - OPENAI_API_KEY: Your OpenAI API key
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# THE AGENT - Uses LangGraph + GPT-4 + MCP
# ============================================================================

async def run_travel_agent(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    adults: int
):
    """
    Run the travel agent to plan a trip.
    
    This agent:
    1. Connects to MCP server
    2. Uses GPT-4 to decide which tools to call
    3. Calls search_flights and search_hotels via MCP
    4. Returns a complete itinerary
    """
    
    # Import here to fail fast if packages missing
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    from langgraph.prebuilt import create_react_agent
    from langchain_openai import ChatOpenAI
    
    print("\n" + "="*60)
    print("🌴 COASTLINE TRAVEL AGENT")
    print("    LangGraph + GPT-4 + MCP")
    print("="*60)
    
    # Path to the MCP server
    server_path = Path(__file__).parent / "mcp" / "server.py"
    
    print(f"\n📡 Connecting to MCP server: {server_path}")
    
    # Create MCP client (new API - not a context manager)
    mcp_client = MultiServerMCPClient(
        {
            "coastline-travel": {
                "command": sys.executable,  # Use current Python interpreter
                "args": [str(server_path)],
                "transport": "stdio",
            }
        }
    )
    
    # Connect to the server and get tools using session
    async with mcp_client.session("coastline-travel") as session:
        
        # Get tools from MCP server via the session
        tools = await load_mcp_tools(session)
        
        print(f"✅ Connected! Discovered {len(tools)} tools:")
        for tool in tools:
            print(f"   • {tool.name}")
        
        # Create the LLM
        llm = ChatOpenAI(
            model="gpt-4-turbo",
            temperature=0  # Deterministic for testing
        )
        
        # Create the ReAct agent
        # ReAct = Reasoning + Acting: the agent thinks, acts, observes, repeats
        agent = create_react_agent(llm, tools)
        
        # Build the prompt for the agent
        user_message = f"""You are a travel planning assistant. Plan a trip with these details:

**Trip Details:**
- Origin: {origin}
- Destination: {destination}
- Departure Date: {departure_date}
- Return Date: {return_date}
- Number of Adults: {adults}

**Your Task:**
1. Use the search_flights tool to find flights from {origin} to {destination}
2. Use the search_hotels tool to find hotels in {destination}
3. Select the CHEAPEST flight and hotel options
4. Present a complete itinerary with:
   - Flight details (airline, times, price)
   - Hotel details (name, price per night, total price)
   - Total trip cost (flights + hotel)

Be concise but include all important booking details."""

        print(f"\n🧠 Agent is thinking...")
        print(f"   Trip: {origin} → {destination}")
        print(f"   Dates: {departure_date} to {return_date}")
        print(f"   Adults: {adults}")
        
        # Run the agent
        result = await agent.ainvoke({
            "messages": [
                {"role": "user", "content": user_message}
            ]
        })
        
        # Extract the final response
        final_message = result["messages"][-1]
        
        # Show the tool calls and their results
        print("\n" + "="*60)
        print("🔧 TOOL CALLS & RESULTS")
        print("="*60)
        
        from langchain_core.messages import ToolMessage, AIMessage
        import json
        
        for msg in result["messages"]:
            # Show tool calls made by the agent
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"\n📤 TOOL CALL: {tc['name']}")
                    print(f"   Args: {json.dumps(tc['args'], indent=2)}")
            
            # Show tool results
            if isinstance(msg, ToolMessage):
                print(f"\n📥 TOOL RESULT: {msg.name}")
                print("-" * 40)
                
                # Parse and pretty-print the result
                try:
                    result_data = json.loads(msg.content)
                    
                    # For flights, show summary
                    if msg.name == "search_flights":
                        if result_data.get("success"):
                            print(f"   ✅ Found {result_data.get('total_results', 0)} flights")
                            cheapest = result_data.get("cheapest_flight")
                            if cheapest:
                                print(f"   💰 Cheapest: ${cheapest['total_price']} {cheapest['currency']}")
                                print(f"   ✈️  Airline: {cheapest['validating_airline']}")
                                print(f"   🎫 Class: {cheapest['cabin_class']}")
                                if cheapest.get("itineraries"):
                                    for i, itin in enumerate(cheapest["itineraries"]):
                                        direction = "Outbound" if i == 0 else "Return"
                                        if itin.get("segments"):
                                            seg = itin["segments"][0]
                                            print(f"   {direction}: {seg['departure_airport']} → {seg['arrival_airport']}")
                                            print(f"            {seg['departure_time']} | {itin['duration']}")
                        else:
                            print(f"   ❌ Error: {result_data.get('error', 'Unknown')}")
                    
                    # For hotels, show summary
                    elif msg.name == "search_hotels":
                        if result_data.get("success"):
                            print(f"   ✅ Found {result_data.get('total_results', 0)} hotels")
                            cheapest = result_data.get("cheapest_hotel")
                            if cheapest:
                                print(f"   🏨 Hotel: {cheapest['hotel_name']}")
                                print(f"   💰 Total: ${cheapest['total_price']} ({cheapest['price_per_night']}/night)")
                                print(f"   🛏️  Room: {cheapest['room_type']}")
                                print(f"   🍳 Board: {cheapest['board_type']}")
                            else:
                                print(f"   ⚠️  No hotels with availability found")
                                print(f"   (Searched {result_data.get('hotels_searched', 0)} hotels)")
                        else:
                            print(f"   ❌ Error: {result_data.get('error', 'Unknown')}")
                    
                    else:
                        # Generic output for other tools
                        print(f"   {json.dumps(result_data, indent=2)[:500]}")
                        
                except json.JSONDecodeError:
                    print(f"   {msg.content[:500]}")
        
        print("\n" + "="*60)
        print("📋 AGENT FINAL RESPONSE")
        print("="*60)
        print(final_message.content)
        
        return result


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run a test trip planning request."""
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set!")
        print("   Please set it in your .env file or environment:")
        print("   export OPENAI_API_KEY='your-key-here'")
        return
    
    print("\n" + "="*60)
    print("🧪 MCP INTEGRATION TEST")
    print("="*60)
    print("\nThis test will:")
    print("  1. Start the MCP server (mcp/server.py)")
    print("  2. Connect LangGraph agent to it via MCP protocol")
    print("  3. Agent uses GPT-4 to call search_flights and search_hotels")
    print("  4. Agent generates a travel itinerary")
    
    # Test trip: Madrid to Athens
    result = asyncio.run(run_travel_agent(
        origin="NYC",           # Madrid
        destination="LON",      # Athens  
        departure_date="2026-01-01",
        return_date="2026-01-08",
        adults=2
    ))
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
