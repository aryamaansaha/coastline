"""
LangGraph Agent v3 for Coastline Travel Planner

Key Features:
1. Web-compatible HITL using LangGraph interrupts
2. MongoDB checkpointing for state persistence across requests
3. SSE-friendly architecture for streaming progress
4. Budget propagation fix
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import Annotated, List, Literal, TypedDict, Generator
from datetime import datetime
from pathlib import Path
import os

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.types import interrupt, Command

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
    
    # User inputs (can be updated by human - e.g., budget increase)
    preferences: dict  # Structured JSON from Preferences schema
    
    # Execution state (mutable)
    current_itinerary: dict | None  # Parsed JSON from LLM
    total_cost: float | None  # Calculated by auditor
    cost_breakdown: dict | None  # By category (flights, hotels, activities)
    budget_status: Literal["unknown", "under", "over"]  # Set by auditor
    is_approved: bool  # Set by human review
    revision_count: int  # Track revisions (both schema and human-requested)
    
    # Status tracking for SSE
    current_step: str | None  # Current step name for progress updates


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
            print(f"📋 Budget: ${budget:.2f}")
            
            # Show NEW tool results since last AI message
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
                        print(f"\n🔧 Tool Results (since last LLM call):")
                        for msg in new_tool_messages:
                            tool_name = getattr(msg, 'name', 'unknown')
                            content = msg.content
                            try:
                                # Parse and pretty print JSON
                                content_json = json.loads(content) if isinstance(content, str) else content
                                # Summarize instead of full dump
                                if isinstance(content_json, dict):
                                    if 'flights' in content_json:
                                        flights = content_json.get('flights', [])
                                        print(f"\n  ✈️  {tool_name}: {len(flights)} flights found")
                                        for f in flights[:3]:
                                            price = f.get('price', {})
                                            print(f"      - {f.get('airline', '?')}: ${price.get('total', '?')} {price.get('currency', '')}")
                                    elif 'hotels' in content_json:
                                        hotels = content_json.get('hotels', [])
                                        print(f"\n  🏨 {tool_name}: {len(hotels)} hotels found")
                                        for h in hotels[:3]:
                                            print(f"      - {h.get('name', '?')}: ${h.get('price_per_night', '?')}/night")
                                    elif 'total_cost' in content_json:
                                        print(f"\n  💰 {tool_name}: ${content_json.get('total_cost', 0):.2f}")
                                    else:
                                        print(f"\n  📦 {tool_name}: {json.dumps(content_json, indent=2)[:300]}")
                                else:
                                    print(f"\n  📦 {tool_name}: {str(content_json)[:300]}")
                            except:
                                print(f"\n  📦 {tool_name}: {str(content)[:300]}")
        
        response = llm_with_tools.invoke(msgs)
        
        if debug:
            # Show tool calls requested
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"\n🔧 Tool Calls Requested: {len(response.tool_calls)}")
                for i, tool_call in enumerate(response.tool_calls, 1):
                    args = tool_call.get('args', {})
                    args_str = json.dumps(args) if len(json.dumps(args)) < 100 else f"{json.dumps(args)[:100]}..."
                    print(f"   {i}. {tool_call['name']}({args_str})")
            
            # Show LLM text response (might contain itinerary JSON)
            if hasattr(response, 'content') and response.content:
                content = response.content
                print(f"\n📝 LLM Response ({len(content)} chars):")
                # Do NOT log full raw response here anymore. Only in auditor if schema fails.
                # Try to parse as JSON for prettier output
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and 'trip_title' in parsed:
                        print(f"   🗺️  Itinerary: {parsed.get('trip_title', 'Untitled')}")
                        days = parsed.get('days', [])
                        print(f"   📅 Days: {len(days)}")
                        for day in days[:2]:
                            print(f"      Day {day.get('day_number', '?')}: {day.get('theme', 'Activities')}")
                            for act in day.get('activities', [])[:2]:
                                cost = act.get('estimated_cost', 0)
                                print(f"         • {act.get('title', '?')} (${cost:.2f})")
                        if len(days) > 2:
                            print(f"      ... and {len(days) - 2} more days")
                    else:
                        print(f"   {content[:300]}...")
                except:
                    print(f"   {content[:300]}...")
        
        return {
            "messages": [response],
            "current_step": "planning"
        }
    
    return planner_node


def create_auditor_node(debug=False):
    """Factory function for auditor node with debug flag"""
    def auditor_node(state: PlanState) -> dict:
        """
        Auditor: Validates structure and calculates costs.
        """
        sys.path.insert(0, str(Path(__file__).parent / "app"))
        from app.services.utils import ResponseParser
        from app.schemas.trip import ItineraryLLMCreate
        from pydantic import ValidationError
        
        messages = state["messages"]
        last_message = messages[-1]
        preferences = state["preferences"]
        budget_limit = preferences.get("budget_limit", 2000.0)
        
        try:
            content = last_message.content
            itinerary_dict = ResponseParser.extract_json(content)
            
            if not itinerary_dict:
                raise ValueError("No valid JSON found in response")
            
            # Validate against Pydantic schema
            try:
                ItineraryLLMCreate(**itinerary_dict)
                if debug:
                    print(f"✅ AUDITOR: Schema validation passed")
            except ValidationError as ve:
                errors = ve.errors()
                error_details = [
                    f"{' → '.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                    for err in errors
                ]
                
                print(f"❌ AUDITOR: Schema validation failed")
                # Save the raw LLM response to logs/ only on schema validation error
                if debug:
                    logs_dir = Path(__file__).parent / "logs"
                    logs_dir.mkdir(exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    log_file = logs_dir / f"llm_response_{timestamp}.json"
                    
                    with open(log_file, 'w') as f:
                        f.write(content)
                    print(f"   💾 Full response saved to: {log_file.name}")
                
                feedback_msg = format_schema_validation_error(error_details)
                
                return {
                    "budget_status": "unknown",
                    "messages": [HumanMessage(content=feedback_msg)],
                    "current_step": "validation_failed"
                }
            
            # Calculate costs
            total_cost = 0.0
            breakdown = {"flights": 0.0, "hotels": 0.0, "activities": 0.0}
            
            for day in itinerary_dict.get("days", []):
                for activity in day.get("activities", []):
                    cost = float(activity.get("estimated_cost", 0))
                    activity_type = activity.get("type", "activity")
                    
                    total_cost += cost
                    if activity_type == "flight":
                        breakdown["flights"] += cost
                    elif activity_type == "hotel":
                        breakdown["hotels"] += cost
                    else:
                        breakdown["activities"] += cost
            
            budget_status = "under" if total_cost <= budget_limit else "over"
            
            # Always show cost summary
            print(f"\n{'='*60}")
            print(f"💰 AUDITOR - Cost Validation")
            print(f"{'='*60}")
            print(f"   Total: ${total_cost:.2f} / ${budget_limit:.2f} budget")
            print(f"   Status: {'✅ UNDER BUDGET' if budget_status == 'under' else '⚠️  OVER BUDGET'}")
            print(f"\n   📊 Cost Breakdown:")
            print(f"      ✈️  Flights:    ${breakdown['flights']:.2f}")
            print(f"      🏨 Hotels:     ${breakdown['hotels']:.2f}")
            print(f"      🎯 Activities: ${breakdown['activities']:.2f}")
            
            return {
                "current_itinerary": itinerary_dict,
                "total_cost": round(total_cost, 2),
                "cost_breakdown": {k: round(v, 2) for k, v in breakdown.items()},
                "budget_status": budget_status,
                "current_step": "audited"
            }
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"\n⚠️ AUDITOR: Failed to parse JSON - {e}")
            
            if debug:
                # Save the problematic response for inspection
                logs_dir = Path(__file__).parent / "logs"
                logs_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                error_log = logs_dir / f"parse_error_{timestamp}.txt"
                
                with open(error_log, 'w') as f:
                    f.write(f"Error: {e}\n\n")
                    f.write("="*60 + "\n")
                    f.write("RAW CONTENT:\n")
                    f.write("="*60 + "\n")
                    f.write(content)
                
                print(f"   💾 Error details saved to: {error_log.name}")
            
            feedback_msg = format_json_parse_error(str(e))
            
            return {
                "current_itinerary": None,
                "total_cost": None,
                "cost_breakdown": None,
                "budget_status": "unknown",
                "messages": [HumanMessage(content=feedback_msg)],
                "current_step": "parse_failed"
            }
    
    return auditor_node


def human_review_node(state: PlanState) -> dict:
    """
    Human-in-the-loop review node using LangGraph interrupts.
    
    For schema validation failures: auto-retry with limit
    For valid itineraries: interrupt and wait for human decision
    """
    budget_status = state.get("budget_status", "unknown")
    revision_count = state.get("revision_count", 0)
    MAX_SCHEMA_REVISIONS = 3
    
    # =========================================================================
    # CASE 1: Schema validation failed - auto-retry with limit
    # =========================================================================
    if budget_status == "unknown":
        if revision_count >= MAX_SCHEMA_REVISIONS:
            print(f"❌ HUMAN REVIEW: Max schema retries ({MAX_SCHEMA_REVISIONS}) reached")
            # Signal failure - don't interrupt, just fail
            return {
                "is_approved": False,
                "current_step": "failed_max_retries"
            }
        
        print(f"🔄 HUMAN REVIEW: Invalid format - Auto-retrying ({revision_count + 1}/{MAX_SCHEMA_REVISIONS})")
        return {
            "is_approved": False,
            "revision_count": revision_count + 1,
            "messages": [HumanMessage(content=AGENT_REQUEST_VALID_JSON)],
            "current_step": "retrying_validation"
        }
    
    # =========================================================================
    # CASE 2: Valid itinerary - INTERRUPT for human decision
    # =========================================================================
    preferences = state.get("preferences", {})
    
    # Prepare preview data to send to frontend
    preview_data = {
        "itinerary": state.get("current_itinerary"),
        "total_cost": state.get("total_cost"),
        "cost_breakdown": state.get("cost_breakdown"),
        "budget_status": budget_status,
        "budget_limit": preferences.get("budget_limit"),
        "revision_count": revision_count
    }
    
    print(f"⏸️  HUMAN REVIEW: Interrupting for human decision")
    print(f"   Preview: ${preview_data['total_cost']:.2f} / ${preview_data['budget_limit']:.2f}")
    
    # INTERRUPT - This pauses execution and returns preview_data to caller
    # When resumed, interrupt() returns the human's decision
    human_decision = interrupt(preview_data)
    
    print(f"▶️  HUMAN REVIEW: Resumed with decision: {human_decision.get('action')}")
    
    # Process the decision
    action = human_decision.get("action", "approve")
    feedback = human_decision.get("feedback")
    new_budget = human_decision.get("new_budget")
    
    if action == "approve":
        print("✅ HUMAN REVIEW: Itinerary APPROVED")
        return {
            "is_approved": True,
            "current_step": "approved"
        }
    
    elif action == "revise":
        result = {
            "is_approved": False,
            "revision_count": revision_count + 1,
            "current_step": "revision_requested"
        }
        
        # Add feedback as message
        if feedback:
            result["messages"] = [HumanMessage(content=feedback)]
        else:
            result["messages"] = [HumanMessage(content="Please revise the itinerary.")]
        
        # Update budget if changed
        if new_budget is not None:
            updated_preferences = preferences.copy()
            updated_preferences["budget_limit"] = new_budget
            result["preferences"] = updated_preferences
            print(f"💰 HUMAN REVIEW: Budget updated to ${new_budget:.2f}")
        
        print(f"🔄 HUMAN REVIEW: Revision requested with feedback")
        return result
    
    else:
        # Unknown action - treat as approve
        print(f"⚠️ HUMAN REVIEW: Unknown action '{action}' - treating as approve")
        return {
            "is_approved": True,
            "current_step": "approved"
        }


# ============================================================================
# ROUTING LOGIC
# ============================================================================

def route_after_planner(state: PlanState) -> Literal["tools", "auditor"]:
    """Route from planner to tools or auditor"""
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return "auditor"


def route_after_review(state: PlanState) -> Literal["planner", "__end__"]:
    """Route from human review based on approval"""
    is_approved = state.get("is_approved", False)
    current_step = state.get("current_step", "")
    
    if is_approved:
        return "__end__"
    
    # Failed max retries - end
    if current_step == "failed_max_retries":
        return "__end__"
    
    # Revision requested or retrying - back to planner
    return "planner"


# ============================================================================
# GRAPH BUILDER
# ============================================================================

def build_agent_graph(checkpointer, langchain_tools, debug=False):
    """
    Build the agent graph with proper HITL support.
    
    Args:
        checkpointer: LangGraph checkpointer (MongoDB or Memory)
        langchain_tools: List of LangChain tools from MCP
        debug: Enable debug output
        
    Returns:
        Compiled StateGraph
    """
    # Setup LLM
    # Get LLM from provider wrapper (configurable via LLM_PROVIDER, LLM_MODEL, LLM_TEMPERATURE env vars)
    from app.services.llm import get_llm, get_llm_config
    
    # Use environment variables - no hardcoded values
    llm = get_llm()
    llm_with_tools = llm.bind_tools(langchain_tools)
    
    # Always print LLM configuration (useful for debugging and monitoring)
    config = get_llm_config()
    print(f"🤖 LLM Configuration: {config['provider']}/{config['model']} (temperature={config['temperature']})")
    
    if debug:
        print(f"🔍 Debug mode enabled")
    
    # Create nodes
    planner_node = create_planner_node(llm_with_tools, debug=debug)
    tools_node = ToolNode(langchain_tools)
    auditor_node = create_auditor_node(debug=debug)
    
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
    builder.add_edge("auditor", "human_review")
    builder.add_conditional_edges("human_review", route_after_review)
    
    # Compile with checkpointer
    graph = builder.compile(checkpointer=checkpointer)
    
    return graph


def get_initial_state(preferences: dict) -> dict:
    """Create initial state for a new trip generation"""
    return {
        "messages": [],
        "preferences": preferences,
        "current_itinerary": None,
        "total_cost": None,
        "cost_breakdown": None,
        "budget_status": "unknown",
        "is_approved": False,
        "revision_count": 0,
        "current_step": "starting"
    }


# ============================================================================
# STREAMING RUNNER (for SSE)
# ============================================================================

async def run_agent_streaming(
    graph,
    session_id: str,
    preferences: dict = None,
    human_decision: dict = None,
    debug: bool = False
) -> Generator:
    """
    Run agent with streaming output for SSE.
    
    Args:
        graph: Compiled LangGraph
        session_id: Unique session ID (used as thread_id)
        preferences: User preferences (for new sessions)
        human_decision: Human decision (for resuming after interrupt)
        debug: Enable debug output
        
    Yields:
        Dict events for SSE streaming
    """
    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 50
    }
    
    # Determine if this is a new session or resuming
    if human_decision is not None:
        # Resuming from interrupt with human decision
        print(f"▶️ Resuming session {session_id} with decision: {human_decision}")
        
        # Use Command.resume() to inject the decision
        input_data = Command(resume=human_decision)
        
    elif preferences is not None:
        # New session
        print(f"🚀 Starting new session {session_id}")
        input_data = get_initial_state(preferences)
        
        yield {
            "event": "status",
            "data": {"step": "starting", "message": "Starting trip generation..."}
        }
    else:
        raise ValueError("Must provide either preferences (new) or human_decision (resume)")
    
    # Stream graph execution
    try:
        async for event in graph.astream(input_data, config, stream_mode="updates"):
            # event is a dict with node name as key
            for node_name, node_output in event.items():
                if debug:
                    print(f"📍 Node: {node_name}")
                
                # Yield progress events
                if node_name == "planner":
                    yield {
                        "event": "status",
                        "data": {"step": "planning", "message": "AI is planning your trip..."}
                    }
                
                elif node_name == "tools":
                    yield {
                        "event": "status",
                        "data": {"step": "searching", "message": "Searching for flights and hotels..."}
                    }
                
                elif node_name == "auditor":
                    yield {
                        "event": "status",
                        "data": {"step": "validating", "message": "Validating itinerary and costs..."}
                    }
                
                elif node_name == "human_review":
                    current_step = node_output.get("current_step", "")
                    
                    if current_step == "approved":
                        # Agent completed successfully
                        pass  # Will be handled by final state
                    
                    elif current_step in ["retrying_validation", "revision_requested"]:
                        yield {
                            "event": "status",
                            "data": {"step": "revising", "message": "Revising the itinerary..."}
                        }
    
    except Exception as e:
        # Check if this is an interrupt (not an error)
        if "interrupt" in str(type(e).__name__).lower():
            raise  # Re-raise interrupt exceptions
        
        import traceback
        error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
        print(f"❌ Agent error: {error_msg}")
        traceback.print_exc()
        yield {
            "event": "error",
            "data": {"message": error_msg, "recoverable": False}
        }
        return
    
    # Get final state
    final_state = await graph.aget_state(config)
    state_values = final_state.values
    
    # Check if we hit an interrupt (HITL checkpoint)
    if final_state.next:
        # Graph is waiting at an interrupt
        # The interrupt value should be in the state
        print(f"⏸️ Agent paused at interrupt, next nodes: {final_state.next}")
        
        # Get the preview data from the interrupt
        # LangGraph stores interrupt value in state.tasks
        preview_data = None
        if hasattr(final_state, 'tasks') and final_state.tasks:
            for task in final_state.tasks:
                if hasattr(task, 'interrupts') and task.interrupts:
                    preview_data = task.interrupts[0].value
                    break
        
        if preview_data is None:
            # Fallback: construct preview from state
            preview_data = {
                "itinerary": state_values.get("current_itinerary"),
                "total_cost": state_values.get("total_cost"),
                "cost_breakdown": state_values.get("cost_breakdown"),
                "budget_status": state_values.get("budget_status"),
                "budget_limit": state_values.get("preferences", {}).get("budget_limit"),
                "revision_count": state_values.get("revision_count", 0)
            }
        
        yield {
            "event": "awaiting_approval",
            "data": {
                "session_id": session_id,
                "preview": preview_data
            }
        }
    
    else:
        # Graph completed
        is_approved = state_values.get("is_approved", False)
        
        if is_approved:
            # Get final budget from potentially updated preferences
            final_preferences = state_values.get("preferences", {})
            
            yield {
                "event": "complete",
                "data": {
                    "session_id": session_id,
                    "itinerary": state_values.get("current_itinerary"),
                    "total_cost": state_values.get("total_cost"),
                    "cost_breakdown": state_values.get("cost_breakdown"),
                    "budget_limit": final_preferences.get("budget_limit"),
                    "budget_status": state_values.get("budget_status")
                }
            }
        else:
            yield {
                "event": "error",
                "data": {
                    "message": "Agent failed to generate valid itinerary",
                    "recoverable": False
                }
            }


# ============================================================================
# SIMPLE RUNNER (for CLI/testing)
# ============================================================================

async def run_agent_simple(
    preferences: dict,
    debug: bool = False,
    auto_approve: bool = True
) -> dict:
    """
    Simple runner for CLI testing (auto-approves or uses CLI input).
    
    This is a convenience wrapper that doesn't require external checkpointer.
    """
    from langgraph.checkpoint.memory import MemorySaver
    
    server_path = str(Path(__file__).parent / "mcp" / "server.py")
    
    mcp_client = MultiServerMCPClient({
        "travel-server": {
            "command": sys.executable,
            "args": [server_path],
            "transport": "stdio"
        }
    })
    
    async with mcp_client.session("travel-server") as session:
        langchain_tools = await load_mcp_tools(session)
        
        if debug:
            print(f"🔧 MCP Tools: {[t.name for t in langchain_tools]}")
        
        checkpointer = MemorySaver()
        graph = build_agent_graph(checkpointer, langchain_tools, debug=debug)
        
        session_id = "cli-test"
        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 50
        }
        
        print(f"\n🚀 Starting agent with preferences:")
        print(json.dumps(preferences, indent=2))
        
        # Run until completion or interrupt
        input_data = get_initial_state(preferences)
        
        while True:
            # Run graph
            result = await graph.ainvoke(input_data, config)
            
            # Check state
            state = await graph.aget_state(config)
            
            if not state.next:
                # Graph completed
                break
            
            # Hit interrupt - need human decision
            print("\n" + "="*60)
            print("👤 HUMAN REVIEW REQUIRED")
            print("="*60)
            
            # Get preview from interrupt
            preview = None
            if hasattr(state, 'tasks') and state.tasks:
                for task in state.tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        preview = task.interrupts[0].value
                        break
            
            if preview:
                print(f"💰 Total Cost: ${preview.get('total_cost', 0):.2f}")
                print(f"🎯 Budget: ${preview.get('budget_limit', 0):.2f}")
                print(f"📊 Status: {preview.get('budget_status', 'unknown')}")
            
            if auto_approve:
                print("✅ [AUTO] Approving...")
                decision = {"action": "approve"}
            else:
                # CLI input
                print("\nOptions:")
                print("  [1] Approve")
                print("  [2] Revise with feedback")
                print("  [3] Increase budget and revise")
                
                choice = input("Choice (1/2/3): ").strip()
                
                if choice == "1":
                    decision = {"action": "approve"}
                elif choice == "2":
                    feedback = input("Feedback: ").strip() or "Please revise."
                    decision = {"action": "revise", "feedback": feedback}
                elif choice == "3":
                    new_budget = float(input("New budget: $").strip())
                    feedback = input("Feedback (optional): ").strip()
                    decision = {
                        "action": "revise",
                        "feedback": feedback or f"Budget increased to ${new_budget}. Please revise.",
                        "new_budget": new_budget
                    }
                else:
                    decision = {"action": "approve"}
            
            # Resume with decision
            input_data = Command(resume=decision)
        
        # Get final state
        final_state = await graph.aget_state(config)
        state_values = final_state.values
        final_preferences = state_values.get("preferences", {})
        
        return {
            "itinerary": state_values.get("current_itinerary"),
            "total_cost": state_values.get("total_cost"),
            "cost_breakdown": state_values.get("cost_breakdown"),
            "budget_status": state_values.get("budget_status"),
            "budget_limit": final_preferences.get("budget_limit"),  # Use updated budget
            "success": state_values.get("is_approved", False)
        }


# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    test_preferences = {
        "destinations": ["London", "Paris"],
        "origin": "New York",
        "start_date": "2026-02-01",
        "end_date": "2026-02-07",
        "budget_limit": 2500.0
    }
    
    result = asyncio.run(run_agent_simple(
        test_preferences,
        debug=True,
        auto_approve=True
    ))
    
    print("\n" + "="*60)
    print("FINAL RESULT")
    print("="*60)
    print(json.dumps(result, indent=2))

