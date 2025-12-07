"""
Service layer for agent integration with FastAPI.

Wraps the LangGraph agent and converts between FastAPI schemas and agent format.
"""

import asyncio
from app.schemas.trip import Preferences, Itinerary, Day, Activity, Location
from app.services.geocode import LocalizeService
from datetime import datetime
import uuid


class AgentService:
    """Service for running the travel planning agent"""
    
    @staticmethod
    def _geocode_location(address: str, fallback_query: str = None) -> tuple[float | None, float | None]:
        """
        Geocode an address using Nominatim.
        
        Args:
            address: Primary address to geocode
            fallback_query: Fallback query if address fails (e.g., location name + city)
            
        Returns:
            Tuple of (lat, lng) or (None, None) if geocoding fails
        """
        # Try primary address
        result = LocalizeService.geocode_nominatim(address)
        if result:
            return result
        
        # Try fallback query
        if fallback_query:
            result = LocalizeService.geocode_nominatim(fallback_query)
            if result:
                return result
        
        return None, None
    
    @staticmethod
    async def generate_itinerary_from_agent(preferences: Preferences) -> tuple[Itinerary, dict]:
        """
        Run the agent and convert output to Pydantic Itinerary object.
        
        Args:
            preferences: Pydantic Preferences object from API request
            
        Returns:
            tuple of (Itinerary object, metadata dict with cost info)
        """
        # Import here to avoid circular dependencies
        import sys
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(backend_dir))
        
        from agent_graph_v2 import run_agent_with_preferences
        
        # Convert Pydantic model to dict for agent
        preferences_dict = {
            "destinations": preferences.destinations,
            "start_date": preferences.start_date.strftime("%Y-%m-%d"),
            "end_date": preferences.end_date.strftime("%Y-%m-%d"),
            "budget_limit": preferences.budget_limit,
            "origin": getattr(preferences, "origin", None)  # Optional field
        }
        
        # Run agent
        result = await run_agent_with_preferences(preferences_dict)
        
        if not result.get("success") or not result.get("itinerary"):
            raise ValueError("Agent failed to generate valid itinerary")
        
        # Convert agent output to Pydantic models
        itinerary_data = result["itinerary"]
        
        # Parse days
        days = []
        for day_data in itinerary_data.get("days", []):
            city = day_data.get("city", "")
            
            # Parse activities
            activities = []
            for activity_data in day_data.get("activities", []):
                # Create Location with geocoding
                loc_data = activity_data.get("location", {})
                loc_name = loc_data.get("name", "")
                loc_address = loc_data.get("address", "")
                
                # Geocode the address
                # Fallback: use location name + city if address fails
                fallback_query = f"{loc_name}, {city}" if loc_name and city else None
                lat, lng = AgentService._geocode_location(loc_address, fallback_query)
                
                if lat and lng:
                    print(f"📍 Geocoded '{loc_name}': ({lat:.4f}, {lng:.4f})")
                else:
                    print(f"⚠️  Failed to geocode '{loc_name}' at '{loc_address}'")
                
                location = Location(
                    name=loc_name,
                    address=loc_address,
                    lat=lat,
                    lng=lng
                )
                
                # Parse time_slot
                time_slot_str = activity_data.get("time_slot", "09:00 AM")
                try:
                    time_slot = datetime.strptime(time_slot_str, "%I:%M %p")
                except:
                    time_slot = datetime.strptime("09:00 AM", "%I:%M %p")
                
                # Create Activity
                activity = Activity(
                    id=str(uuid.uuid4()),
                    type=activity_data.get("type", "activity"),
                    time_slot=time_slot,
                    title=activity_data.get("title", ""),
                    description=activity_data.get("description", ""),
                    activity_suggestion=activity_data.get("activity_suggestion", ""),
                    location=location,
                    estimated_cost=activity_data.get("estimated_cost", 0.0),
                    price_suggestion=activity_data.get("price_suggestion", ""),
                    currency=activity_data.get("currency", "USD")
                )
                activities.append(activity)
            
            # Create Day
            day = Day(
                id=str(uuid.uuid4()),
                day_number=day_data.get("day_number", 1),
                theme=day_data.get("theme", ""),
                city=city,
                activities=activities
            )
            days.append(day)
        
        # Create Itinerary
        itinerary = Itinerary(
            trip_id=str(uuid.uuid4()),
            trip_title=itinerary_data.get("trip_title", "Your Trip"),
            days=days,
            budget_limit=preferences.budget_limit
        )
        
        # Metadata for frontend
        metadata = {
            "total_cost": result.get("total_cost"),
            "cost_breakdown": result.get("cost_breakdown"),
            "budget_status": result.get("budget_status"),
            "over_budget": result.get("total_cost", 0) > preferences.budget_limit
        }
        
        return itinerary, metadata

