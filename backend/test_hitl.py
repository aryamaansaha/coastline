"""
Test script for HITL SSE streaming endpoints.

Tests the new session-based flow:
1. POST /api/trip/generate/stream → SSE events
2. POST /api/trip/session/{id}/decide → Continue with decision
"""

import httpx
import json
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get backend port from environment variable, default to 8008
BACKEND_PORT = os.getenv("BACKEND_PORT", "8008")
BASE_URL = f"http://127.0.0.1:{BACKEND_PORT}"


def parse_sse_events(text: str):
    """Parse SSE events from response text"""
    events = []
    lines = text.split('\n')
    current_event = {}
    
    for line in lines:
        if line.startswith('event: '):
            current_event['event'] = line[7:].strip()
        elif line.startswith('data: '):
            try:
                current_event['data'] = json.loads(line[6:])
            except json.JSONDecodeError:
                current_event['data'] = line[6:]
        elif line == '' and current_event:
            if 'event' in current_event:
                events.append(current_event)
            current_event = {}
    
    # Don't forget last event
    if current_event and 'event' in current_event:
        events.append(current_event)
    
    return events


async def test_hitl_flow():
    """Test the full HITL flow"""
    
    # Test preferences - small trip to reduce API calls
    # Use dates ~1 month from now (dynamic)
    start = datetime.now() + timedelta(days=35)
    end = datetime.now() + timedelta(days=38)
    
    preferences = {
        "destinations": ["Paris"],
        "start_date": start.strftime("%Y-%m-%dT00:00:00Z"),
        "end_date": end.strftime("%Y-%m-%dT00:00:00Z"),
        "budget_limit": 1500.0,
        "origin": "New York"
    }
    
    print(f"📅 Trip dates: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    
    print("="*60)
    print("🧪 TESTING HITL SSE FLOW")
    print("="*60)
    print(f"\n📋 Preferences: {json.dumps(preferences, indent=2)}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Step 1: Start generation with SSE streaming
        print("\n" + "-"*40)
        print("📡 Step 1: Starting SSE stream...")
        print("-"*40)
        
        session_id = None
        preview = None
        final_result = None
        
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/trip/generate/stream",
            json=preferences,
            headers={"Accept": "text/event-stream"}
        ) as response:
            print(f"Response status: {response.status_code}")
            
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                events = parse_sse_events(buffer)
                
                for event in events:
                    event_type = event.get('event')
                    data = event.get('data', {})
                    
                    print(f"\n📨 Event: {event_type}")
                    
                    if event_type == 'status':
                        print(f"   Step: {data.get('step')}")
                        print(f"   Message: {data.get('message')}")
                    
                    elif event_type == 'awaiting_approval':
                        session_id = data.get('session_id')
                        preview = data.get('preview', {})
                        print(f"   Session ID: {session_id}")
                        print(f"   Total Cost: ${preview.get('total_cost', 0):.2f}")
                        print(f"   Budget: ${preview.get('budget_limit', 0):.2f}")
                        print(f"   Status: {preview.get('budget_status')}")
                        print(f"   Revision Count: {preview.get('revision_count', 0)}")
                        # Break out to submit decision
                        break
                    
                    elif event_type == 'complete':
                        final_result = data
                        print(f"   ✅ Generation complete!")
                        print(f"   Trip: {data.get('itinerary', {}).get('trip_title')}")
                        print(f"   Total Cost: ${data.get('total_cost', 0):.2f}")
                        break
                    
                    elif event_type == 'error':
                        print(f"   ❌ Error: {data.get('message')}")
                        return
                
                # Check if we got what we need
                if session_id or final_result:
                    break
        
        # If we got a complete event immediately (auto-approved due to budget), we're done
        if final_result:
            print("\n" + "="*60)
            print("✅ TEST COMPLETE (auto-approved)")
            print("="*60)
            return
        
        if not session_id:
            print("\n❌ No session_id received!")
            return
        
        # Step 2: Submit approval decision
        print("\n" + "-"*40)
        print("📤 Step 2: Submitting APPROVE decision...")
        print("-"*40)
        
        decision = {
            "action": "approve"
        }
        
        print(f"Decision: {json.dumps(decision)}")
        
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/trip/session/{session_id}/decide",
            json=decision,
            headers={"Accept": "text/event-stream"}
        ) as response:
            print(f"Response status: {response.status_code}")
            
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                events = parse_sse_events(buffer)
                
                for event in events:
                    event_type = event.get('event')
                    data = event.get('data', {})
                    
                    print(f"\n📨 Event: {event_type}")
                    
                    if event_type == 'status':
                        print(f"   Step: {data.get('step')}")
                        print(f"   Message: {data.get('message')}")
                    
                    elif event_type == 'complete':
                        final_result = data
                        print(f"   ✅ Generation complete!")
                        itinerary = data.get('itinerary', {})
                        print(f"   Trip: {itinerary.get('trip_title')}")
                        print(f"   Total Cost: ${data.get('total_cost', 0):.2f}")
                        print(f"   Days: {len(itinerary.get('days', []))}")
                        break
                    
                    elif event_type == 'awaiting_approval':
                        # Another HITL round
                        session_id = data.get('session_id')
                        preview = data.get('preview', {})
                        print(f"   Another approval needed!")
                        print(f"   Total Cost: ${preview.get('total_cost', 0):.2f}")
                        break
                    
                    elif event_type == 'error':
                        print(f"   ❌ Error: {data.get('message')}")
                        break
                
                if final_result:
                    break
        
        # Step 3: Verify session status
        print("\n" + "-"*40)
        print("🔍 Step 3: Checking session status...")
        print("-"*40)
        
        status_response = await client.get(f"{BASE_URL}/api/trip/session/{session_id}/status")
        status = status_response.json()
        
        print(f"Session Status: {status.get('status')}")
        print(f"Created: {status.get('created_at')}")
        if status.get('final_cost'):
            print(f"Final Cost: ${status.get('final_cost'):.2f}")
        
        print("\n" + "="*60)
        print("✅ TEST COMPLETE")
        print("="*60)


async def test_revise_flow():
    """Test the revise flow with feedback"""
    
    # Use dates ~1 month from now (dynamic)
    start = datetime.now() + timedelta(days=35)
    end = datetime.now() + timedelta(days=37)
    
    preferences = {
        "destinations": ["London"],
        "start_date": start.strftime("%Y-%m-%dT00:00:00Z"),
        "end_date": end.strftime("%Y-%m-%dT00:00:00Z"),
        "budget_limit": 800.0,  # Low budget to force over-budget
        "origin": "New York"
    }
    
    print(f"📅 Trip dates: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    
    print("="*60)
    print("🧪 TESTING REVISE FLOW")
    print("="*60)
    print(f"\n📋 Preferences (low budget to test revision):")
    print(json.dumps(preferences, indent=2))
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Start generation
        print("\n📡 Starting SSE stream...")
        
        session_id = None
        
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/trip/generate/stream",
            json=preferences,
            headers={"Accept": "text/event-stream"}
        ) as response:
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                events = parse_sse_events(buffer)
                
                for event in events:
                    if event.get('event') == 'awaiting_approval':
                        session_id = event['data'].get('session_id')
                        preview = event['data'].get('preview', {})
                        print(f"\n⏸️  HITL Checkpoint:")
                        print(f"   Cost: ${preview.get('total_cost', 0):.2f} / ${preview.get('budget_limit', 0):.2f}")
                        print(f"   Status: {preview.get('budget_status')}")
                        break
                
                if session_id:
                    break
        
        if not session_id:
            print("❌ No session_id - agent may have auto-completed")
            return
        
        # Submit REVISE with feedback and budget increase
        print("\n📤 Submitting REVISE decision with feedback + budget increase...")
        
        decision = {
            "action": "revise",
            "feedback": "Please find cheaper accommodation options. I prefer hostels or budget hotels.",
            "new_budget": 1200.0
        }
        
        print(f"Decision: {json.dumps(decision, indent=2)}")
        
        # Reset to wait for NEW awaiting_approval event
        got_new_checkpoint = False
        
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/trip/session/{session_id}/decide",
            json=decision,
            headers={"Accept": "text/event-stream"}
        ) as response:
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                events = parse_sse_events(buffer)
                
                for event in events:
                    event_type = event.get('event')
                    data = event.get('data', {})
                    
                    print(f"\n📨 Event: {event_type}")
                    
                    if event_type == 'status':
                        print(f"   {data.get('message', '')}")
                    
                    elif event_type == 'awaiting_approval':
                        preview = data.get('preview', {})
                        print(f"   New preview after revision:")
                        print(f"   Cost: ${preview.get('total_cost', 0):.2f}")
                        print(f"   Budget: ${preview.get('budget_limit', 0):.2f}")
                        print(f"   Revision #: {preview.get('revision_count', 0)}")
                        
                        # Update session_id for next approve
                        session_id = data.get('session_id')
                        got_new_checkpoint = True
                        break
                    
                    elif event_type == 'complete':
                        print(f"   ✅ Complete after revision!")
                        print(f"   Cost: ${data.get('total_cost', 0):.2f}")
                        return
                    
                    elif event_type == 'error':
                        print(f"   ❌ Error: {data.get('message', '')}")
                        return
                
                if got_new_checkpoint:
                    break
        
        # Approve the revised itinerary
        print("\n📤 Approving revised itinerary...")
        
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/trip/session/{session_id}/decide",
            json={"action": "approve"},
            headers={"Accept": "text/event-stream"}
        ) as response:
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                events = parse_sse_events(buffer)
                
                for event in events:
                    if event.get('event') == 'complete':
                        data = event['data']
                        print(f"\n✅ Final result:")
                        print(f"   Trip: {data.get('itinerary', {}).get('trip_title')}")
                        print(f"   Cost: ${data.get('total_cost', 0):.2f}")
                        return
        
        print("\n" + "="*60)
        print("✅ REVISE TEST COMPLETE")
        print("="*60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "revise":
        asyncio.run(test_revise_flow())
    else:
        asyncio.run(test_hitl_flow())

