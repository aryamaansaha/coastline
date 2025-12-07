from app.schemas.trip import Preferences, Itinerary, Day, Activity, Location, TripSummary
from datetime import datetime
import uuid

class TripService:
    @staticmethod
    def generate_trip(preferences: Preferences) -> Itinerary:
        """Generate a mock itinerary for testing (will be replaced by agent later)"""
        
        # Mock activities for Day 1
        day1_activities = [
            Activity(
                id=str(uuid.uuid4()),
                type="activity",
                time_slot=datetime.strptime("09:00 AM", "%I:%M %p"),
                title="Eiffel Tower Visit",
                description="Iconic iron lattice tower offering panoramic city views from observation decks.",
                activity_suggestion="Arrive early to avoid crowds. Take the stairs to the second floor for a unique experience. Spend 1-2 hours exploring and taking photos.",
                location=Location(
                    name="Eiffel Tower",
                    address="Champ de Mars, 5 Avenue Anatole France, 75007 Paris",
                    lat=48.8584,
                    lng=2.2945
                ),
                estimated_cost=28.00,
                price_suggestion="Book tickets online in advance to save time and get slight discounts",
                currency="USD"
            ),
            Activity(
                id=str(uuid.uuid4()),
                type="activity",
                time_slot=datetime.strptime("12:30 PM", "%I:%M %p"),
                title="Lunch at Le Petit Cler",
                description="Charming traditional French bistro near the Eiffel Tower with authentic cuisine.",
                activity_suggestion="Try their daily specials. The croque monsieur is excellent. Reservations recommended during peak hours.",
                location=Location(
                    name="Le Petit Cler",
                    address="29 Rue Cler, 75007 Paris",
                    lat=48.8572,
                    lng=2.3059
                ),
                estimated_cost=35.00,
                price_suggestion="Set menus offer better value than à la carte",
                currency="USD"
            ),
            Activity(
                id=str(uuid.uuid4()),
                type="activity",
                time_slot=datetime.strptime("03:00 PM", "%I:%M %p"),
                title="Louvre Museum",
                description="World's largest art museum featuring the Mona Lisa and thousands of masterpieces.",
                activity_suggestion="Focus on specific wings to avoid overwhelm. Don't miss the Egyptian antiquities and Italian Renaissance sections. Allow 3-4 hours minimum.",
                location=Location(
                    name="Musée du Louvre",
                    address="Rue de Rivoli, 75001 Paris",
                    lat=48.8606,
                    lng=2.3376
                ),
                estimated_cost=20.00,
                price_suggestion="Free entry first Sunday of each month. Buy skip-the-line tickets online",
                currency="USD"
            )
        ]
        
        # Mock activities for Day 2
        day2_activities = [
            Activity(
                id=str(uuid.uuid4()),
                type="activity",
                time_slot=datetime.strptime("10:00 AM", "%I:%M %p"),
                title="Sacré-Cœur Basilica",
                description="Stunning white-domed basilica atop Montmartre hill with breathtaking city views.",
                activity_suggestion="Walk up the steps or take the funicular. Explore the charming Montmartre neighborhood afterwards. Entry is free.",
                location=Location(
                    name="Sacré-Cœur",
                    address="35 Rue du Chevalier de la Barre, 75018 Paris",
                    lat=48.8867,
                    lng=2.3431
                ),
                estimated_cost=0.00,
                price_suggestion="Free to enter the basilica. Dome access is €6 if interested",
                currency="USD"
            ),
            Activity(
                id=str(uuid.uuid4()),
                type="activity",
                time_slot=datetime.strptime("01:00 PM", "%I:%M %p"),
                title="Lunch at L'As du Fallafel",
                description="Famous spot in Le Marais for the best falafel sandwiches in Paris.",
                activity_suggestion="Expect a line but it moves quickly. Get the special with everything. Great casual lunch option.",
                location=Location(
                    name="L'As du Fallafel",
                    address="34 Rue des Rosiers, 75004 Paris",
                    lat=48.8575,
                    lng=2.3594
                ),
                estimated_cost=12.00,
                price_suggestion="Very affordable. Cash preferred to avoid credit card fees",
                currency="USD"
            ),
            Activity(
                id=str(uuid.uuid4()),
                type="activity",
                time_slot=datetime.strptime("03:30 PM", "%I:%M %p"),
                title="Seine River Cruise",
                description="Relaxing boat tour along the Seine with commentary and views of Paris landmarks.",
                activity_suggestion="Choose a late afternoon cruise for golden hour lighting. Most cruises last about 1 hour. Audio guides available in multiple languages.",
                location=Location(
                    name="Bateaux Parisiens",
                    address="Port de la Bourdonnais, 75007 Paris",
                    lat=48.8606,
                    lng=2.2930
                ),
                estimated_cost=18.00,
                price_suggestion="Book online for 10-15% discount. Sunset cruises slightly more expensive",
                currency="USD"
            )
        ]
        
        # Create days
        day1 = Day(
            id=str(uuid.uuid4()),
            day_number=1,
            theme="Iconic Landmarks & Art",
            city="Paris",
            activities=day1_activities
        )
        
        day2 = Day(
            id=str(uuid.uuid4()),
            day_number=2,
            theme="Culture & Local Vibes",
            city="Paris",
            activities=day2_activities
        )
        
        # Create itinerary
        itinerary = Itinerary(
            trip_id=str(uuid.uuid4()),
            trip_title="2 Days in Paris",
            days=[day1, day2],
            budget_limit=preferences.budget_limit
        )
        
        return itinerary
    
    @staticmethod
    def save_itinerary(db, itinerary: Itinerary) -> str:
        """Save itinerary to MongoDB"""
        doc = itinerary.model_dump()
        doc["created_at"] = datetime.now()
        doc["updated_at"] = datetime.now()
        
        # Upsert to handle both create and update
        db.itineraries.update_one(
            {"trip_id": itinerary.trip_id},
            {"$set": doc},
            upsert=True
        )
        return itinerary.trip_id
    
    @staticmethod
    def get_itinerary(db, trip_id: str) -> Itinerary | None:
        """Retrieve itinerary from MongoDB"""
        doc = db.itineraries.find_one({"trip_id": trip_id})
        if not doc:
            return None
        
        # Remove MongoDB's _id field for Pydantic parsing
        doc.pop("_id", None)
        doc.pop("created_at", None)
        doc.pop("updated_at", None)
        
        return Itinerary(**doc)
    
    @staticmethod
    def get_activity(db, trip_id: str, activity_id: str) -> Activity | None:
        """Get a specific activity from an itinerary"""
        itinerary = TripService.get_itinerary(db, trip_id)
        if not itinerary:
            return None
        
        for day in itinerary.days:
            for activity in day.activities:
                if activity.id == activity_id:
                    return activity
        return None
    
    @staticmethod
    def update_itinerary(db, trip_id: str, itinerary: Itinerary) -> bool:
        """Update an existing itinerary"""
        existing = TripService.get_itinerary(db, trip_id)
        if not existing:
            return False
        
        doc = itinerary.model_dump()
        doc["updated_at"] = datetime.now()
        
        db.itineraries.update_one(
            {"trip_id": trip_id},
            {"$set": doc}
        )
        return True
    
    @staticmethod
    def delete_itinerary(db, trip_id: str) -> bool:
        """Delete an itinerary and all associated discoveries"""
        # Delete itinerary
        result = db.itineraries.delete_one({"trip_id": trip_id})
        
        # Delete all associated discoveries
        db.discoveries.delete_many({"trip_id": trip_id})
        
        return result.deleted_count > 0
    
    @staticmethod
    def list_trips(db) -> list[TripSummary]:
        """
        List all trips with summary information.
        
        Returns list of TripSummary objects (not full itineraries).
        """
        # Get all itineraries, sorted by most recent first
        docs = db.itineraries.find().sort("created_at", -1)
        
        summaries = []
        for doc in docs:
            # Extract unique cities from days
            destinations = []
            days = doc.get("days", [])
            for day in days:
                city = day.get("city", "")
                if city and city not in destinations:
                    destinations.append(city)
            
            summaries.append(TripSummary(
                trip_id=doc.get("trip_id", ""),
                trip_title=doc.get("trip_title", "Untitled Trip"),
                budget_limit=doc.get("budget_limit", 0.0),
                destinations=destinations,
                num_days=len(days),
                created_at=doc.get("created_at"),
                updated_at=doc.get("updated_at")
            ))
        
        return summaries