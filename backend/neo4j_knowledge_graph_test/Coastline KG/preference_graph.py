"""
User Preference Knowledge Graph

Uses Graphiti with FalkorDB for LLM-powered entity extraction
and natural language queries over user travel preferences.
"""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI
from graphiti_core import Graphiti
from graphiti_core.driver.falkordb_driver import FalkorDriver
from graphiti_core.nodes import EpisodeType

load_dotenv()


# Configuration
FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", "6379"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class PreferenceGraph:
    """Manages user travel preferences using Graphiti + FalkorDB."""

    def __init__(self):
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Create FalkorDB driver
        self.falkor_driver = FalkorDriver(
            host=FALKORDB_HOST,
            port=FALKORDB_PORT,
            database="preferences"
        )
        
        # Initialize Graphiti with FalkorDB driver
        self.graphiti = Graphiti(graph_driver=self.falkor_driver)

    async def initialize(self):
        """Initialize the graph database with required indices."""
        try:
            await self.graphiti.build_indices_and_constraints()
        except Exception as e:
            # Ignore if indices already exist
            error_str = str(e).lower()
            if "already exists" in error_str or "equivalent" in error_str:
                print("Indices already exist, continuing...")
            else:
                raise

    async def close(self):
        """Close the connection to the graph database."""
        await self.graphiti.close()

    def summarize_preferences(self, conversation: str) -> str:
        """
        Extract long-term user preferences from conversation.
        
        Filters out transient details (budget, flights, hotels) and
        focuses on lasting travel preferences.
        """
        prompt = f"""Extract ONLY long-term travel preferences from this conversation.

IGNORE mentions of:
- Budget changes or increases
- Flight bookings or changes  
- Hotel preferences
- Any temporary/transactional requests

FOCUS ON:
- Types of attractions the user enjoys
- Travel pace preferences
- Social preferences (meeting locals, solo, groups)
- Activity preferences
- Food/dietary preferences
- Any recurring interests

Conversation:
{conversation}

Return a list of clear preference statements, one per line. Example format:
- User enjoys museums
- User prefers an intense travel pace
- User likes meeting locals
- User is vegetarian

Preferences:"""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        
        return response.choices[0].message.content.strip()

    async def store_preferences(self, summary: str, trip_context: str = "general"):
        """
        Store extracted preferences in the knowledge graph using Graphiti.
        
        Graphiti automatically:
        - Extracts entities from the text
        - Discovers relationships
        - Resolves duplicates
        - Creates embeddings for semantic search
        """
        await self.graphiti.add_episode(
            name=f"user_preferences_{trip_context}",
            episode_body=summary,
            source=EpisodeType.text,
            source_description=f"User travel preferences from {trip_context}",
            reference_time=datetime.now(timezone.utc),
        )

    async def query_preferences(self, query: str, num_results: int = 5) -> str:
        """
        Query the knowledge graph using natural language.
        
        Graphiti uses semantic search + graph traversal to find relevant facts.
        Returns natural language response suitable for feeding to an agent.
        """
        results = await self.graphiti.search(query, num_results=num_results)
        
        if not results:
            return "No preferences found for this query."
        
        # Format results as natural language
        facts = [edge.fact for edge in results]
        return "\n".join(f"- {fact}" for fact in facts)

    async def get_all_preferences(self) -> dict:
        """
        Get preferences by category using natural language queries.
        """
        queries = {
            "attractions": "What kind of tourist attractions does the user like?",
            "pace": "What travel pace does the user prefer?",
            "social": "What are the user's social preferences when traveling?",
            "activities": "What activities does the user enjoy?",
            "food": "What are the user's food or dietary preferences?",
        }
        
        preferences = {}
        for category, query in queries.items():
            result = await self.query_preferences(query, num_results=3)
            preferences[category] = result
        
        return preferences


# Convenience functions for simpler usage
_graph_instance = None


async def get_graph() -> PreferenceGraph:
    """Get or create the singleton graph instance."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = PreferenceGraph()
        await _graph_instance.initialize()
    return _graph_instance


async def summarize_and_store(conversation: str, trip_context: str = "general") -> str:
    """
    One-step function to extract and store preferences.
    
    Args:
        conversation: The Q/A and chat history string
        trip_context: Optional label for the trip (e.g., "paris_2024")
    
    Returns:
        The extracted preference summary
    """
    graph = await get_graph()
    summary = graph.summarize_preferences(conversation)
    await graph.store_preferences(summary, trip_context)
    return summary


async def get_preferences(query: str) -> str:
    """
    Query stored preferences using natural language.
    
    Args:
        query: Natural language question about preferences
    
    Returns:
        Natural language response with relevant preferences
    """
    graph = await get_graph()
    return await graph.query_preferences(query)


async def get_all_user_preferences() -> dict:
    """Get all categorized user preferences."""
    graph = await get_graph()
    return await graph.get_all_preferences()


async def cleanup():
    """Close the graph connection."""
    global _graph_instance
    if _graph_instance:
        await _graph_instance.close()
        _graph_instance = None
