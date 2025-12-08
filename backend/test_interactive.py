#!/usr/bin/env python3
"""
Interactive HITL Test - YOU control the decisions!
"""

import asyncio
import httpx
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get backend port from environment variable, default to 8008
BACKEND_PORT = os.getenv("BACKEND_PORT", "8008")
BASE_URL = f"http://127.0.0.1:{BACKEND_PORT}"


def parse_sse_events(buffer: str) -> list:
    """Parse SSE events from buffer"""
    events = []
    lines = buffer.split("\n")
    
    current_event = {}
    for line in lines:
        if line.startswith("event:"):
            current_event["event"] = line[6:].strip()
        elif line.startswith("data:"):
            try:
                current_event["data"] = json.loads(line[5:].strip())
            except:
                current_event["data"] = {"raw": line[5:].strip()}
        elif line == "" and current_event:
            if "event" in current_event:
                events.append(current_event)
            current_event = {}
    
    return events


def print_full_itinerary(itinerary):
    if not itinerary:
        print("(No itinerary available)\n")
        return
    print("\n------ FULL ITINERARY ------")
    print(json.dumps(itinerary, indent=2, ensure_ascii=False))
    print("----------------------------\n")


async def interactive_test():
    """Interactive HITL test - you make the decisions!"""
    
    # Dynamic dates - 1 month from now
    start = datetime.now() + timedelta(days=35)
    end = datetime.now() + timedelta(days=38)
    
    print("\n" + "="*60)
    print("🎮 INTERACTIVE HITL TEST")
    print("="*60)
    
    # Get user preferences
    print("\n📋 Enter your trip preferences:\n")
    
    destinations = input("   Destinations (default: Paris): ").strip() or "Paris"
    origin = input("   Origin city (default: New York): ").strip() or "New York"
    
    days_input = input("   Trip length in days (default: 3): ").strip()
    days = int(days_input) if days_input else 3
    end = start + timedelta(days=days)
    
    budget_input = input("   Budget in USD (default: 1500): ").strip()
    budget = float(budget_input) if budget_input else 1500.0
    
    preferences = {
        "destinations": destinations.split(","),
        "origin": origin,
        "start_date": start.strftime("%Y-%m-%dT00:00:00Z"),
        "end_date": end.strftime("%Y-%m-%dT00:00:00Z"),
        "budget_limit": budget
    }
    
    print(f"\n📅 Trip: {destinations} from {origin}")
    print(f"📆 Dates: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} ({days} days)")
    print(f"💰 Budget: ${budget:.2f}")
    
    input("\n⏎ Press Enter to start generation...")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        session_id = None
        revision_count = 0
        
        first_run = True
        
        while True:
            # Only show this header on first run
            if first_run:
                print("\n" + "-"*60)
                print("🚀 Starting trip generation...")
                print("-"*60)
                first_run = False
            
            # Start or resume
            if session_id:
                # We already have a session, skip to decision prompt
                pass
            else:
                # Start new generation
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
                            event_type = event.get('event')
                            data = event.get('data', {})
                            
                            if event_type == 'status':
                                print(f"   📍 {data.get('message', '')}")
                            
                            elif event_type == 'awaiting_approval':
                                session_id = data.get('session_id')
                                preview = data.get('preview', {})
                                
                                print("\n" + "="*60)
                                print("⏸️  HUMAN REVIEW REQUIRED")
                                print("="*60)
                                
                                itinerary = preview.get('itinerary', {})
                                print(f"\n📍 Trip: {itinerary.get('trip_title', 'Your Trip')}")
                                print(f"💰 Total Cost: ${preview.get('total_cost', 0):.2f}")
                                print(f"🎯 Your Budget: ${preview.get('budget_limit', 0):.2f}")
                                
                                status = preview.get('budget_status', 'unknown')
                                if status == 'over':
                                    print(f"⚠️  Status: OVER BUDGET!")
                                elif status == 'under':
                                    print(f"✅ Status: Under budget")
                                
                                if revision_count > 0:
                                    print(f"🔄 Revision #: {revision_count}")
                                
                                # Show itinerary summary
                                days_list = itinerary.get('days', [])
                                print(f"\n📅 {len(days_list)} day(s) planned:")
                                for day in days_list[:3]:  # Show first 3 days
                                    print(f"   Day {day.get('day_number')}: {day.get('theme', 'Activities')}")
                                    activities = day.get('activities', [])
                                    for act in activities[:2]:  # Show first 2 activities per day
                                        print(f"      • {act.get('title', 'Activity')}")
                                if len(days_list) > 3:
                                    print(f"   ... and {len(days_list) - 3} more day(s)")

                                # Print full itinerary
                                print_full_itinerary(itinerary)
                                
                                break
                            
                            elif event_type == 'complete':
                                print("\n✅ Trip auto-completed (was under budget)")
                                final = data.get('itinerary', {})
                                print(f"   Trip: {final.get('trip_title')}")
                                print(f"   Cost: ${data.get('total_cost', 0):.2f}")
                                print_full_itinerary(final)
                                return
                            
                            elif event_type == 'error':
                                print(f"\n❌ Error: {data.get('message', 'Unknown error')}")
                                return
                        
                        if session_id:
                            break
            
            if not session_id:
                print("\n❌ No checkpoint reached")
                return
            
            # Get user decision
            print("\n" + "-"*60)
            print("🤔 What would you like to do?")
            print("-"*60)
            print("   [1] ✅ APPROVE - Accept this itinerary")
            print("   [2] 📝 REVISE - Give feedback for changes")
            print("   [3] 💰 REVISE + BUDGET - Give feedback AND increase budget")
            print("   [4] ❌ CANCEL - Abort this trip")
            
            choice = input("\n   Your choice (1-4): ").strip()
            
            if choice == "1":
                # Approve
                decision = {"action": "approve"}
                print("\n✅ Approving itinerary...")
                
            elif choice == "2":
                # Revise with feedback
                print("\n📝 Enter your feedback:")
                feedback = input("   > ").strip()
                if not feedback:
                    feedback = "Please improve the itinerary"
                decision = {"action": "revise", "feedback": feedback}
                revision_count += 1
                
            elif choice == "3":
                # Revise with feedback and budget
                print("\n📝 Enter your feedback:")
                feedback = input("   > ").strip()
                if not feedback:
                    feedback = "Please adjust the itinerary"
                
                print(f"\n💰 Current budget: ${preferences['budget_limit']:.2f}")
                new_budget_str = input("   New budget: $").strip()
                try:
                    new_budget = float(new_budget_str)
                except:
                    new_budget = preferences['budget_limit'] * 1.5
                    print(f"   Using ${new_budget:.2f}")
                
                decision = {
                    "action": "revise",
                    "feedback": feedback,
                    "new_budget": new_budget
                }
                preferences['budget_limit'] = new_budget
                revision_count += 1
                
            elif choice == "4":
                print("\n❌ Cancelled by user")
                return
            else:
                print("\n⚠️ Invalid choice, defaulting to approve")
                decision = {"action": "approve"}
            
            # Submit decision
            print(f"\n📤 Submitting: {decision['action']}")
            
            got_result = False
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
                        
                        if event_type == 'status':
                            print(f"   📍 {data.get('message', '')}")
                        
                        elif event_type == 'awaiting_approval':
                            # New checkpoint after revision
                            session_id = data.get('session_id')
                            preview = data.get('preview', {})
                            
                            print("\n" + "="*60)
                            print("⏸️  NEW PREVIEW AFTER REVISION")
                            print("="*60)
                            
                            itinerary = preview.get('itinerary', {})
                            print(f"\n📍 Trip: {itinerary.get('trip_title', 'Your Trip')}")
                            print(f"💰 Total Cost: ${preview.get('total_cost', 0):.2f}")
                            print(f"🎯 Your Budget: ${preview.get('budget_limit', 0):.2f}")
                            
                            status = preview.get('budget_status', 'unknown')
                            if status == 'over':
                                print(f"⚠️  Status: OVER BUDGET!")
                            else:
                                print(f"✅ Status: Under budget")
                            
                            print(f"🔄 Revision #: {preview.get('revision_count', revision_count)}")
                            
                            # Show itinerary summary with activities
                            days_list = itinerary.get('days', [])
                            print(f"\n📅 {len(days_list)} day(s) planned:")
                            for day in days_list[:3]:
                                print(f"   Day {day.get('day_number')}: {day.get('theme', 'Activities')}")
                                activities = day.get('activities', [])
                                for act in activities[:2]:
                                    print(f"      • {act.get('title', 'Activity')}")
                            if len(days_list) > 3:
                                print(f"   ... and {len(days_list) - 3} more day(s)")
                            
                            # Print full itinerary after revision
                            print_full_itinerary(itinerary)
                            
                            got_result = True
                            break
                        
                        elif event_type == 'complete':
                            print("\n" + "="*60)
                            print("🎉 TRIP COMPLETE!")
                            print("="*60)
                            
                            itinerary = data.get('itinerary', {})
                            print(f"\n📍 {itinerary.get('trip_title', 'Your Trip')}")
                            print(f"💰 Final Cost: ${data.get('total_cost', 0):.2f}")
                            print(f"📅 Days: {len(itinerary.get('days', []))}")
                            print_full_itinerary(itinerary)
                            
                            print("\n✅ Trip saved to database!")
                            return
                        
                        elif event_type == 'error':
                            print(f"\n❌ Error: {data.get('message', 'Unknown error')}")
                            return
                    
                    if got_result:
                        break
            
            if not got_result:
                print("\n⚠️ No response from server")
                return


if __name__ == "__main__":
    print("\n🌊 COASTLINE - Interactive HITL Test\n")
    asyncio.run(interactive_test())

