"""
Refactored LangGraph Agent for Coastline Travel Planner

Key Improvements:
1. Auditor node for deterministic cost calculations
2. Structured preferences passed as JSON (not f-strings)
3. JSON output format from LLM
4. Multi-city trip support
5. Programmatic human review (easy to swap for web UI)
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import Annotated, List, Literal, TypedDict
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.memory import MemorySaver

# Import prompts from centralized location
sys.path.insert(0, str(Path(__file__).parent / "app"))
from app.prompts import (
    AGENT_PLANNER_SYSTEM_PROMPT,
    format_preferences_request,
    format_budget_alert,
    format_schema_validation_error,
    format_json_parse_error,
    AGENT_REQUEST_VALID_JSON
)


# ============================================================================
# STATE DEFINITION
# ============================================================================

class PlanState(TypedDict):
    """State that flows through the agent graph"""
    # Conversation history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User inputs (immutable after initial setup)
    preferences: dict  # Structured JSON from Preferences schema
    
    # Execution state (mutable)
    current_itinerary: dict | None  # Parsed JSON from LLM
    total_cost: float | None  # Calculated by auditor
    cost_breakdown: dict | None  # By category (flights, hotels, activities)
    budget_status: Literal["unknown", "under", "over"]  # Set by auditor
    is_approved: bool  # Set by human review
    revision_count: int  # Track how many times we've asked LLM to revise


# ============================================================================
# NODE FACTORY - Creates nodes with LLM in closure
# ============================================================================

def create_planner_node(llm_with_tools, debug=False):
    """Factory function that creates planner node with LLM in closure"""
    def planner_node(state: PlanState) -> dict:
        """
        The core planning agent. Generates itinerary or revises based on feedback.
        """
        preferences = state["preferences"]
        budget = preferences.get("budget_limit", 2000.0)
        revision_count = state.get("revision_count", 0)
        
        # Build system message with current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        sys_content = AGENT_PLANNER_SYSTEM_PROMPT.format(current_date=current_date)
        
        # Add preferences as structured context
        preferences_msg = format_preferences_request(preferences)
        
        # If this is a revision, add context about budget issue
        if state.get("budget_status") == "over":
            total_cost = state.get("total_cost", 0)
            preferences_msg += format_budget_alert(total_cost, budget)
        
        # Build message history
        msgs = [
            SystemMessage(content=sys_content),
            HumanMessage(content=preferences_msg)
        ] + state["messages"]
        
        if debug:
            print(f"\n{'='*60}")
            print(f"🧠 PLANNER NODE (Revision {revision_count})")
            print(f"{'='*60}")
            
            # Show ONLY NEW tool results since last AI message
            messages = state.get("messages", [])
            if messages:
                # Find the last AI message index
                last_ai_idx = -1
                for i in range(len(messages) - 1, -1, -1):
                    if hasattr(messages[i], 'type') and messages[i].type in ['ai', 'AIMessage']:
                        last_ai_idx = i
                        break
                
                # Get tool messages AFTER the last AI message
                if last_ai_idx >= 0:
                    new_tool_messages = [
                        m for m in messages[last_ai_idx + 1:]
                        if hasattr(m, 'type') and m.type == 'tool'
                    ]
                    
                    if new_tool_messages:
                        print(f"\n🔧 NEW Tool Results (since last call):")
                        for msg in new_tool_messages:
                            tool_name = getattr(msg, 'name', 'unknown')
                            content = msg.content
                            try:
                                # Try to parse and pretty print JSON
                                content_json = json.loads(content) if isinstance(content, str) else content
                                print(f"\n  {tool_name}:")
                                print(f"  {json.dumps(content_json, indent=4)}")
                            except:
                                # Not JSON, just show as string
                                content_str = str(content)[:300]
                                print(f"\n  {tool_name}: {content_str}")
        
        response = llm_with_tools.invoke(msgs)
        
        if debug:
            # Show tool calls if any
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"\n🔧 Tool Calls Requested: {len(response.tool_calls)}")
                for i, tool_call in enumerate(response.tool_calls, 1):
                    args_str = json.dumps(tool_call['args'])
                    print(f"  {i}. {tool_call['name']}({args_str})")
            
            # Show text response (might contain itinerary JSON)
            if hasattr(response, 'content') and response.content:
                content = response.content[:500]  # First 500 chars
                print(f"\n📝 LLM Response Preview:")
                print(f"  {content}...")
        
        return {"messages": [response]}
    
    return planner_node


def create_auditor_node(debug=False):
    """Factory function for auditor node with debug flag"""
    def auditor_node(state: PlanState) -> dict:
        """
        Auditor: Validates structure and calculates costs.
        1. Parse JSON from LLM output (using ResponseParser)
        2. Validate against ItineraryLLMCreate schema
        3. Calculate costs deterministically
        4. Check budget
        """
        # Import here to avoid circular dependencies
        sys.path.insert(0, str(Path(__file__).parent / "app"))
        from app.services.utils import ResponseParser
        from app.schemas.trip import ItineraryLLMCreate
        from pydantic import ValidationError
        
        messages = state["messages"]
        last_message = messages[-1]
        preferences = state["preferences"]
        budget_limit = preferences.get("budget_limit", 2000.0)
        
        # Try to parse and validate JSON
        try:
            content = last_message.content
            
            # Step 1: Extract JSON using ResponseParser
            itinerary_dict = ResponseParser.extract_json(content)
            
            if not itinerary_dict:
                raise ValueError("No valid JSON found in response")
            
            # Step 2: Validate against Pydantic schema
            try:
                itinerary_llm = ItineraryLLMCreate(**itinerary_dict)
                if debug:
                    print(f"\n✅ AUDITOR: Schema validation passed")
            except ValidationError as ve:
                # Format validation errors for LLM
                errors = ve.errors()
                error_details = []
                for err in errors:
                    location = " → ".join(str(loc) for loc in err['loc'])
                    error_details.append(f"{location}: {err['msg']}")
                
                print(f"\n❌ AUDITOR: Schema validation failed")
                print(f"   Errors:\n" + "\n   ".join(error_details))
                
                feedback_msg = format_schema_validation_error(error_details)
                
                return {
                    "budget_status": "unknown",
                    "messages": [HumanMessage(content=feedback_msg)]
                }
            
            # Use the raw dict for further processing (not the validated object)
            itinerary = itinerary_dict
            
            if debug:
                print(f"\n{'='*60}")
                print(f"📊 AUDITOR NODE - Parsing Itinerary")
                print(f"{'='*60}")
                print(json.dumps(itinerary, indent=2))
                print(f"\n{'='*60}")
            
            # Extract all costs
            total_cost = 0.0
            breakdown = {
                "flights": 0.0,
                "hotels": 0.0,
                "activities": 0.0,
                "food": 0.0
            }
            
            cost_details = []  # For debug output
            
            for day in itinerary.get("days", []):
                for activity in day.get("activities", []):
                    cost = float(activity.get("estimated_cost", 0))
                    activity_type = activity.get("type", "activity")
                    title = activity.get("title", "Unknown")
                    
                    total_cost += cost
                    
                    # Categorize
                    if activity_type == "flight":
                        breakdown["flights"] += cost
                    elif activity_type == "hotel":
                        breakdown["hotels"] += cost
                    elif activity_type == "food":
                        breakdown["food"] += cost
                    else:
                        breakdown["activities"] += cost
                    
                    if debug and cost > 0:
                        cost_details.append(f"  - {title} ({activity_type}): ${cost:.2f}")
            
            # Determine budget status
            if total_cost <= budget_limit:
                budget_status = "under"
                status_message = f"✅ Budget OK: ${total_cost:.2f} / ${budget_limit:.2f}"
            else:
                budget_status = "over"
                status_message = f"❌ Over Budget: ${total_cost:.2f} / ${budget_limit:.2f} (${total_cost - budget_limit:.2f} over)"
            
            print(f"\n💰 AUDITOR REPORT:")
            print(f"   {status_message}")
            print(f"   Breakdown: {breakdown}")
            
            if debug and cost_details:
                print(f"\n   Cost Details:")
                for detail in cost_details:
                    print(detail)
            
            return {
                "current_itinerary": itinerary,
                "total_cost": round(total_cost, 2),
                "cost_breakdown": {k: round(v, 2) for k, v in breakdown.items()},
                "budget_status": budget_status
            }
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"\n⚠️  AUDITOR: Failed to parse JSON - {e}")
            if debug:
                print(f"   Content preview: {content[:500]}...")
            
            feedback_msg = format_json_parse_error(str(e))
            
            return {
                "current_itinerary": None,
                "total_cost": None,
                "cost_breakdown": None,
                "budget_status": "unknown",
                "messages": [HumanMessage(content=feedback_msg)]
            }
    
    return auditor_node


def human_review_node(state: PlanState) -> dict:
    """
    Simulates human approval/feedback.
    In production, this would be replaced with a web UI interaction.
    
    For now: Auto-approve if budget is OK, otherwise ask for revision.
    """
    budget_status = state.get("budget_status", "unknown")
    is_approved = state.get("is_approved", False)
    
    # Programmatic decision (can be replaced with web UI input)
    if budget_status == "under":
        print("\n✅ HUMAN REVIEW: Budget satisfied - Auto-approving")
        return {"is_approved": True}
    elif budget_status == "over":
        revision_count = state.get("revision_count", 0)
        if revision_count < 2:  # Max 2 revisions
            print(f"\n🔄 HUMAN REVIEW: Over budget - Requesting revision (attempt {revision_count + 1}/2)")
            return {
                "is_approved": False,
                "revision_count": revision_count + 1,
                "messages": [HumanMessage(content="Please revise the plan to fit within budget.")]
            }
        else:
            print("\n⚠️  HUMAN REVIEW: Max revisions reached - Suggesting budget increase")
            return {"is_approved": True}  # Accept but flag for user
    else:
        print("\n❌ HUMAN REVIEW: Invalid itinerary format - Requesting correction")
        return {
            "is_approved": False,
            "messages": [HumanMessage(content=AGENT_REQUEST_VALID_JSON)]
        }


# ============================================================================
# ROUTING LOGIC
# ============================================================================

def route_after_planner(state: PlanState) -> Literal["tools", "auditor"]:
    """Route from planner to tools or auditor"""
    last_message = state["messages"][-1]
    
    # If LLM wants to call tools, go to tools
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Otherwise, go to auditor for cost validation
    return "auditor"


def route_after_auditor(state: PlanState) -> Literal["human_review", "planner"]:
    """Route from auditor based on budget status"""
    budget_status = state.get("budget_status", "unknown")
    
    if budget_status == "unknown":
        # Invalid output, send back to planner
        return "planner"
    
    # Valid output, go to human review
    return "human_review"


def route_after_review(state: PlanState) -> Literal["planner", "__end__"]:
    """Route from human review based on approval"""
    is_approved = state.get("is_approved", False)
    
    if is_approved:
        return "__end__"
    else:
        return "planner"


# ============================================================================
# HELPER: Run Agent with Preferences
# ============================================================================

async def run_agent_with_preferences(preferences: dict, debug: bool = False) -> dict:
    """
    Run the agent with structured preferences.
    
    Args:
        preferences: Dict matching Preferences schema from FastAPI
        debug: If True, print detailed debug output
        
    Returns:
        Dict with itinerary, cost info, and status
    """
    server_path = str(Path(__file__).parent / "mcp" / "server.py")
    
    # Setup MCP Client
    mcp_client = MultiServerMCPClient({
        "travel-server": {
            "command": sys.executable,
            "args": [server_path],
            "transport": "stdio"
        }
    })
    
    # Keep session alive for entire execution
    async with mcp_client.session("travel-server") as session:
        # Load tools
        langchain_tools = await load_mcp_tools(session)
        
        # Setup LLM
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        llm_with_tools = llm.bind_tools(langchain_tools)
        
        # Create nodes with debug flag
        planner_node = create_planner_node(llm_with_tools, debug=debug)
        tools_node = ToolNode(langchain_tools)
        auditor_node = create_auditor_node(debug=debug)
        
        # Add debug wrapper for tools if needed
        if debug:
            print(f"\n🔧 MCP Tools Available: {[t.name for t in langchain_tools]}")
        
        # Build graph
        builder = StateGraph(PlanState)
        
        # Add nodes
        builder.add_node("planner", planner_node)
        builder.add_node("tools", tools_node)
        builder.add_node("auditor", auditor_node)
        builder.add_node("human_review", human_review_node)
        
        # Add edges
        builder.add_edge(START, "planner")
        builder.add_conditional_edges("planner", route_after_planner)
        builder.add_edge("tools", "planner")
        builder.add_conditional_edges("auditor", route_after_auditor)
        builder.add_conditional_edges("human_review", route_after_review)
        
        # Compile
        checkpointer = MemorySaver()
        graph = builder.compile(checkpointer=checkpointer)
        
        # Initial state
        initial_state = {
            "messages": [],
            "preferences": preferences,
            "current_itinerary": None,
            "total_cost": None,
            "cost_breakdown": None,
            "budget_status": "unknown",
            "is_approved": False,
            "revision_count": 0
        }
        
        # Run graph
        config = {"configurable": {"thread_id": "trip-generation"}}
        
        print(f"\n🚀 Starting agent with preferences:")
        print(json.dumps(preferences, indent=2))
        
        final_state = await graph.ainvoke(initial_state, config)
        
        return {
            "itinerary": final_state.get("current_itinerary"),
            "total_cost": final_state.get("total_cost"),
            "cost_breakdown": final_state.get("cost_breakdown"),
            "budget_status": final_state.get("budget_status"),
            "budget_limit": preferences.get("budget_limit"),
            "success": final_state.get("is_approved", False)
        }


# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test with multi-city preferences
    test_preferences = {
        "destinations": ["London", "Paris", "Amsterdam"],
        "origin": "New York",
        "start_date": "2025-06-01",
        "end_date": "2025-06-10",
        "budget_limit": 3000.0
    }
    
    result = asyncio.run(run_agent_with_preferences(test_preferences))
    
    print("\n" + "="*60)
    print("FINAL RESULT")
    print("="*60)
    print(json.dumps(result, indent=2))

