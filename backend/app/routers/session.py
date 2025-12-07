"""
Session router for HITL trip generation.

Endpoints:
- POST /api/trip/generate/stream - Start generation with SSE streaming
- POST /api/trip/session/{id}/decide - Submit human decision
- GET /api/trip/session/{id}/status - Get session status
- DELETE /api/trip/session/{id} - Cancel/delete session
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

from app.schemas.trip import Preferences, Itinerary, CostBreakdown
from app.schemas.session import (
    TripSession,
    SessionStatus,
    SessionPreview,
    HumanDecision,
    SSEEventType
)
from app.services.session import SessionService, MongoDBCheckpointer
from app.services.trip import TripService
from app.services.geocode import LocalizeService
from app.database import get_db

# Add backend dir to path for agent import
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

router = APIRouter()


# ============================================================================
# MCP CLIENT SINGLETON (reused across requests)
# ============================================================================

_langchain_tools = None
_mcp_client = None


async def get_mcp_tools():
    """Get or create MCP tools (singleton pattern)"""
    global _langchain_tools, _mcp_client
    
    if _langchain_tools is not None:
        return _langchain_tools
    
    from langchain_mcp_adapters.client import MultiServerMCPClient
    
    server_path = str(backend_dir / "mcp" / "server.py")
    
    _mcp_client = MultiServerMCPClient({
        "travel-server": {
            "command": sys.executable,
            "args": [server_path],
            "transport": "stdio"
        }
    })
    
    # Use get_tools() method instead of context manager
    _langchain_tools = await _mcp_client.get_tools()
    
    print(f"🔧 MCP Tools loaded: {[t.name for t in _langchain_tools]}")
    return _langchain_tools


# ============================================================================
# SSE STREAMING ENDPOINT
# ============================================================================

@router.post("/api/trip/generate/stream")
async def generate_trip_stream(
    preferences: Preferences,
    request: Request,
    db = Depends(get_db)
):
    """
    Start trip generation with SSE streaming.
    
    Returns an SSE stream with events:
    - status: Progress updates
    - awaiting_approval: HITL checkpoint reached (includes preview)
    - complete: Generation finished successfully
    - error: Something went wrong
    
    Frontend should:
    1. Open SSE connection
    2. Listen for events
    3. On "awaiting_approval": Show preview, get user decision
    4. Call POST /api/trip/session/{id}/decide with decision
    5. Open new SSE connection to continue (or poll status)
    """
    from agent_graph_v3 import build_agent_graph, run_agent_streaming
    
    # Create session
    preferences_dict = {
        "destinations": preferences.destinations,
        "start_date": preferences.start_date.strftime("%Y-%m-%d"),
        "end_date": preferences.end_date.strftime("%Y-%m-%d"),
        "budget_limit": preferences.budget_limit,
        "origin": preferences.origin
    }
    
    session = SessionService.create_session(db, preferences_dict)
    
    async def event_generator():
        """Generate SSE events from agent execution"""
        try:
            # Get MCP tools
            langchain_tools = await get_mcp_tools()
            
            # Build graph with MongoDB checkpointer
            checkpointer = MongoDBCheckpointer(db)
            graph = build_agent_graph(checkpointer, langchain_tools, debug=True)
            
            # Run agent with streaming
            async for event in run_agent_streaming(
                graph,
                session_id=session.session_id,
                preferences=preferences_dict,
                debug=True
            ):
                event_type = event.get("event", "status")
                event_data = event.get("data", {})
                
                # Update session status based on event
                if event_type == "awaiting_approval":
                    preview_data = event_data.get("preview", {})
                    preview = SessionPreview(
                        itinerary=_dict_to_itinerary(preview_data.get("itinerary"), preferences.budget_limit),
                        total_cost=preview_data.get("total_cost", 0),
                        cost_breakdown=CostBreakdown(**preview_data.get("cost_breakdown", {})),
                        budget_limit=preview_data.get("budget_limit", preferences.budget_limit),
                        budget_status=preview_data.get("budget_status", "unknown"),
                        revision_count=preview_data.get("revision_count", 0)
                    )
                    SessionService.update_session_status(
                        db, session.session_id, 
                        SessionStatus.AWAITING_APPROVAL,
                        preview=preview
                    )
                
                elif event_type == "complete":
                    # Geocode and save final itinerary
                    itinerary_dict = event_data.get("itinerary")
                    final_budget = event_data.get("budget_limit", preferences.budget_limit)
                    
                    if itinerary_dict:
                        itinerary = await _process_final_itinerary(
                            itinerary_dict, 
                            final_budget,
                            db
                        )
                        
                        SessionService.complete_session(
                            db,
                            session.session_id,
                            itinerary,
                            event_data.get("total_cost", 0),
                            CostBreakdown(**event_data.get("cost_breakdown", {}))
                        )
                        
                        # Update event data with processed itinerary
                        event_data["itinerary"] = itinerary.model_dump()
                
                elif event_type == "error":
                    SessionService.update_session_status(
                        db, session.session_id,
                        SessionStatus.FAILED,
                        error_message=event_data.get("message", "Unknown error")
                    )
                
                # Yield SSE event
                yield {
                    "event": event_type,
                    "data": json.dumps(event_data, default=json_serial)
                }
                
                # Check if client disconnected
                if await request.is_disconnected():
                    print(f"Client disconnected from session {session.session_id}")
                    break
        
        except Exception as e:
            print(f"❌ SSE Error: {e}")
            import traceback
            traceback.print_exc()
            
            SessionService.update_session_status(
                db, session.session_id,
                SessionStatus.FAILED,
                error_message=str(e)
            )
            
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e), "recoverable": False})
            }
    
    return EventSourceResponse(event_generator())


# ============================================================================
# DECISION ENDPOINT
# ============================================================================

@router.post("/api/trip/session/{session_id}/decide")
async def submit_decision(
    session_id: str,
    decision: HumanDecision,
    request: Request,
    db = Depends(get_db)
):
    """
    Submit human decision for HITL checkpoint.
    
    Returns an SSE stream continuing from where we left off.
    
    Decision options:
    - action: "approve" - Accept current itinerary
    - action: "revise" - Request revision with feedback
      - feedback: Required text feedback for the agent
      - new_budget: Optional budget increase
    """
    from agent_graph_v3 import build_agent_graph, run_agent_streaming
    
    # Validate session exists and is awaiting approval
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != SessionStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=400, 
            detail=f"Session is not awaiting approval (status: {session.status})"
        )
    
    # Validate decision
    if decision.action == "revise" and not decision.feedback:
        raise HTTPException(
            status_code=400,
            detail="Feedback is required when requesting revision"
        )
    
    # Update budget in session if changed
    if decision.new_budget is not None:
        SessionService.update_session_preferences(db, session_id, decision.new_budget)
    
    # Update session status
    SessionService.update_session_status(db, session_id, SessionStatus.PROCESSING)
    
    async def event_generator():
        """Generate SSE events from resumed agent execution"""
        try:
            langchain_tools = await get_mcp_tools()
            checkpointer = MongoDBCheckpointer(db)
            graph = build_agent_graph(checkpointer, langchain_tools, debug=True)
            
            # Prepare decision dict
            decision_dict = {
                "action": decision.action,
                "feedback": decision.feedback,
                "new_budget": decision.new_budget
            }
            
            # Resume agent with decision
            async for event in run_agent_streaming(
                graph,
                session_id=session_id,
                human_decision=decision_dict,
                debug=True
            ):
                event_type = event.get("event", "status")
                event_data = event.get("data", {})
                
                # Update session status based on event
                if event_type == "awaiting_approval":
                    preview_data = event_data.get("preview", {})
                    
                    # Get current budget (may have been updated)
                    current_session = SessionService.get_session(db, session_id)
                    current_budget = current_session.preferences.get("budget_limit", 0)
                    
                    preview = SessionPreview(
                        itinerary=_dict_to_itinerary(preview_data.get("itinerary"), current_budget),
                        total_cost=preview_data.get("total_cost", 0),
                        cost_breakdown=CostBreakdown(**preview_data.get("cost_breakdown", {})),
                        budget_limit=preview_data.get("budget_limit", current_budget),
                        budget_status=preview_data.get("budget_status", "unknown"),
                        revision_count=preview_data.get("revision_count", 0)
                    )
                    SessionService.update_session_status(
                        db, session_id,
                        SessionStatus.AWAITING_APPROVAL,
                        preview=preview
                    )
                
                elif event_type == "complete":
                    itinerary_dict = event_data.get("itinerary")
                    final_budget = event_data.get("budget_limit")
                    
                    # Get updated budget from session
                    current_session = SessionService.get_session(db, session_id)
                    if final_budget is None:
                        final_budget = current_session.preferences.get("budget_limit", 0)
                    
                    if itinerary_dict:
                        itinerary = await _process_final_itinerary(
                            itinerary_dict,
                            final_budget,
                            db
                        )
                        
                        SessionService.complete_session(
                            db,
                            session_id,
                            itinerary,
                            event_data.get("total_cost", 0),
                            CostBreakdown(**event_data.get("cost_breakdown", {}))
                        )
                        
                        event_data["itinerary"] = itinerary.model_dump()
                
                elif event_type == "error":
                    SessionService.update_session_status(
                        db, session_id,
                        SessionStatus.FAILED,
                        error_message=event_data.get("message", "Unknown error")
                    )
                
                yield {
                    "event": event_type,
                    "data": json.dumps(event_data, default=json_serial)
                }
                
                if await request.is_disconnected():
                    break
        
        except Exception as e:
            print(f"❌ SSE Error in decide: {e}")
            import traceback
            traceback.print_exc()
            
            SessionService.update_session_status(
                db, session_id,
                SessionStatus.FAILED,
                error_message=str(e)
            )
            
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e), "recoverable": False})
            }
    
    return EventSourceResponse(event_generator())


# ============================================================================
# STATUS & MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/api/trip/session/{session_id}/status")
def get_session_status(session_id: str, db = Depends(get_db)):
    """Get current session status (for polling fallback)"""
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session.session_id,
        "status": session.status,
        "preview": session.preview,
        "final_itinerary": session.final_itinerary,
        "final_cost": session.final_cost,
        "error_message": session.error_message,
        "created_at": session.created_at,
        "updated_at": session.updated_at
    }


@router.delete("/api/trip/session/{session_id}")
def delete_session(session_id: str, db = Depends(get_db)):
    """Delete/cancel a session"""
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete session
    db.sessions.delete_one({"session_id": session_id})
    
    # Delete checkpoints
    checkpointer = MongoDBCheckpointer(db)
    checkpointer.delete_thread(session_id)
    
    return {"success": True, "message": "Session deleted"}


@router.post("/api/trip/sessions/cleanup")
def cleanup_expired_sessions(db = Depends(get_db)):
    """
    Manually trigger cleanup of expired sessions.
    
    In production, this would be called by a scheduled job.
    """
    deleted_count = SessionService.cleanup_expired_sessions(db)
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Cleaned up {deleted_count} expired sessions"
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _dict_to_itinerary(itinerary_dict: dict | None, budget_limit: float) -> Itinerary | None:
    """Convert raw itinerary dict to Pydantic Itinerary (without geocoding)"""
    if not itinerary_dict:
        return None
    
    from app.schemas.trip import Itinerary, Day, Activity, Location
    import uuid
    
    days = []
    for day_data in itinerary_dict.get("days", []):
        activities = []
        for act_data in day_data.get("activities", []):
            loc_data = act_data.get("location", {})
            location = Location(
                name=loc_data.get("name", ""),
                address=loc_data.get("address", ""),
                lat=None,
                lng=None
            )
            
            # Keep time_slot as string (e.g., "08:31 AM")
            time_slot = act_data.get("time_slot", "09:00 AM")
            
            activities.append(Activity(
                id=str(uuid.uuid4()),
                type=act_data.get("type", "activity"),
                time_slot=time_slot,
                title=act_data.get("title", ""),
                description=act_data.get("description", ""),
                activity_suggestion=act_data.get("activity_suggestion", ""),
                location=location,
                estimated_cost=act_data.get("estimated_cost", 0.0),
                price_suggestion=act_data.get("price_suggestion", ""),
                currency=act_data.get("currency", "USD")
            ))
        
        days.append(Day(
            id=str(uuid.uuid4()),
            day_number=day_data.get("day_number", 1),
            theme=day_data.get("theme", ""),
            city=day_data.get("city", ""),
            activities=activities
        ))
    
    return Itinerary(
        trip_id=str(uuid.uuid4()),
        trip_title=itinerary_dict.get("trip_title", "Your Trip"),
        days=days,
        budget_limit=budget_limit
    )


async def _process_final_itinerary(
    itinerary_dict: dict,
    budget_limit: float,
    db
) -> Itinerary:
    """
    Process final itinerary: geocode locations and save to DB.
    """
    from app.schemas.trip import Itinerary, Day, Activity, Location
    import uuid
    
    days = []
    for day_data in itinerary_dict.get("days", []):
        city = day_data.get("city", "")
        activities = []
        
        for act_data in day_data.get("activities", []):
            loc_data = act_data.get("location", {})
            loc_name = loc_data.get("name", "")
            loc_address = loc_data.get("address", "")
            
            # Geocode
            lat, lng = None, None
            result = LocalizeService.geocode_nominatim(loc_address)
            if result:
                lat, lng = result
            else:
                # Fallback: try name + city
                fallback = f"{loc_name}, {city}" if loc_name and city else None
                if fallback:
                    result = LocalizeService.geocode_nominatim(fallback)
                    if result:
                        lat, lng = result
            
            location = Location(
                name=loc_name,
                address=loc_address,
                lat=lat,
                lng=lng
            )
            
            # Keep time_slot as string (e.g., "08:31 AM")
            time_slot = act_data.get("time_slot", "09:00 AM")
            
            activities.append(Activity(
                id=str(uuid.uuid4()),
                type=act_data.get("type", "activity"),
                time_slot=time_slot,
                title=act_data.get("title", ""),
                description=act_data.get("description", ""),
                activity_suggestion=act_data.get("activity_suggestion", ""),
                location=location,
                estimated_cost=act_data.get("estimated_cost", 0.0),
                price_suggestion=act_data.get("price_suggestion", ""),
                currency=act_data.get("currency", "USD")
            ))
        
        days.append(Day(
            id=str(uuid.uuid4()),
            day_number=day_data.get("day_number", 1),
            theme=day_data.get("theme", ""),
            city=city,
            activities=activities
        ))
    
    itinerary = Itinerary(
        trip_id=str(uuid.uuid4()),
        trip_title=itinerary_dict.get("trip_title", "Your Trip"),
        days=days,
        budget_limit=budget_limit
    )
    
    # Save to MongoDB
    TripService.save_itinerary(db, itinerary)
    
    return itinerary

