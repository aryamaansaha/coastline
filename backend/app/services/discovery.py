from app.schemas.discovery import Discovery, DiscoveredPlace, DiscoveryType
from app.services.geocode import LocalizeService
from datetime import datetime
import uuid

class DiscoveryService:
    """Generic service for discovering places (restaurants, bars, cafes, etc.)"""
    
    @staticmethod
    def get_discovery(db, trip_id: str, activity_id: str, place_type: DiscoveryType) -> Discovery | None:
        """Get existing discovery for a specific place type"""
        doc = db.discoveries.find_one({
            "trip_id": trip_id,
            "activity_id": activity_id,
            "discovery_type": place_type.value
        })
        if not doc:
            return None
        return Discovery(**doc)
    
    @staticmethod
    def discover_places(
        db, 
        trip_id: str, 
        activity_id: str, 
        place_type: DiscoveryType,
        lat: float, 
        lng: float
    ) -> list[DiscoveredPlace]:
        """
        Discover places using Gemini + Google Maps.
        Places are validated against PlaceLLMCreate schema in LocalizeService.
        """
        
        # Call Gemini API with validation and retry
        validated_places, _ = LocalizeService.discover_places(
            lat, lng, place_type.value, return_grounding_info=False
        )
        
        # Handle empty results (validation failed or no places found)
        if not validated_places:
            print(f"[DiscoveryService] ⚠️ No valid {place_type.value} found near ({lat}, {lng})")
            return []
        
        # Convert validated dicts to DiscoveredPlace objects with IDs and coordinates
        places = []
        for p in validated_places:
            # Geocode place address to get lat/lng
            geocode_result = LocalizeService.geocode_nominatim(p.get('address', ''))
            if geocode_result:
                place_lat, place_lng = geocode_result
            else:
                # Use activity coordinates as fallback
                place_lat, place_lng = lat, lng
            
            # Handle None rating gracefully
            rating = p.get('rating')
            if rating is None:
                rating = None  # Keep as None in DB
            else:
                try:
                    rating = float(rating)
                except (ValueError, TypeError):
                    rating = None
            
            places.append(DiscoveredPlace(
                id=str(uuid.uuid4()),
                place_type=place_type,
                name=p.get('name', ''),
                address=p.get('address', ''),
                rating=rating,
                price_range=p.get('price_range') or 'N/A',
                google_maps_url=p.get('google_maps_url', ''),
                lat=place_lat,
                lng=place_lng,
                starred=False,
                extra_data={}
            ))
        
        print(f"[DiscoveryService] ✅ Discovered {len(places)} {place_type.value}(s)")
        return places
    
    @staticmethod
    def regenerate_places(
        db,
        trip_id: str,
        activity_id: str,
        place_type: DiscoveryType,
        lat: float,
        lng: float
    ) -> list[DiscoveredPlace]:
        """Regenerate places, keeping starred ones"""
        
        # Get existing discovery
        existing = DiscoveryService.get_discovery(db, trip_id, activity_id, place_type)
        
        # Keep starred places
        starred = []
        if existing:
            starred = [p for p in existing.places if p.starred]
        
        # Get new places from Gemini
        new_places = DiscoveryService.discover_places(
            db, trip_id, activity_id, place_type, lat, lng
        )
        
        # Merge: starred + new
        # TODO: Could implement deduplication by name/location if needed
        return starred + new_places
    
    @staticmethod
    def save_discovery(db, discovery: Discovery):
        """Save or update discovery in MongoDB"""
        db.discoveries.update_one(
            {
                "trip_id": discovery.trip_id,
                "activity_id": discovery.activity_id,
                "discovery_type": discovery.discovery_type.value
            },
            {"$set": discovery.model_dump()},
            upsert=True
        )
    
    @staticmethod
    def star_place(
        db, 
        trip_id: str, 
        activity_id: str, 
        place_type: DiscoveryType, 
        place_id: str, 
        starred: bool
    ):
        """Star or unstar a place"""
        db.discoveries.update_one(
            {
                "trip_id": trip_id,
                "activity_id": activity_id,
                "discovery_type": place_type.value,
                "places.id": place_id
            },
            {"$set": {"places.$.starred": starred}}
        )
    
    @staticmethod
    def get_all_discoveries_for_trip(db, trip_id: str) -> list[Discovery]:
        """Get all discoveries (all place types) for a trip"""
        docs = db.discoveries.find({"trip_id": trip_id})
        return [Discovery(**doc) for doc in docs]
    
    @staticmethod
    def get_discoveries_by_type(db, trip_id: str, place_type: DiscoveryType) -> list[Discovery]:
        """Get all discoveries of a specific type for a trip"""
        docs = db.discoveries.find({
            "trip_id": trip_id,
            "discovery_type": place_type.value
        })
        return [Discovery(**doc) for doc in docs]

