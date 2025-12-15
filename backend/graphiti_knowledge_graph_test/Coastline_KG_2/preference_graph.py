"""
Travel Preference Knowledge Graph

Stores and retrieves user travel preferences using FalkorDB + Graphiti.
"""

import os
from datetime import datetime, timezone
from openai import AsyncOpenAI
from graphiti_core import Graphiti
from graphiti_core.driver.falkordb_driver import FalkorDriver

import config

# Set OpenAI API key in environment for Graphiti
os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY


class PreferenceGraph:
    """Knowledge graph for storing user travel preferences."""

    def __init__(self):
        self.openai = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.graphiti: Graphiti | None = None
        self.driver: FalkorDriver | None = None

    async def initialize(self):
        """Initialize the Graphiti client with FalkorDB backend."""
        # Create FalkorDB driver
        self.driver = FalkorDriver(
            host=config.FALKORDB_HOST,
            port=config.FALKORDB_PORT,
        )

        # Initialize Graphiti with the FalkorDB driver
        # OpenAI clients are auto-configured via OPENAI_API_KEY env var
        self.graphiti = Graphiti(graph_driver=self.driver)

        # Build indices and constraints for efficient querying
        await self.graphiti.build_indices_and_constraints()

    async def close(self):
        """Close the Graphiti connection."""
        if self.graphiti:
            await self.graphiti.close()

    async def summarize_preferences(self, raw_input: str) -> str:
        """
        Extract long-term travel preferences from user input.
        
        Filters out transactional details (budget, flights, hotels) and
        focuses on enduring preferences like attractions, pace, activities.
        
        Args:
            raw_input: Raw text containing Q/A and chat history
            
        Returns:
            Summarized preferences as natural language statements
        """
        prompt = """You are analyzing a traveler's input to extract their long-term travel preferences.

Examples of what you can extract IF PRESENT IN THE USER INPUT:
- Types of attractions they enjoy (museums, beaches, nature, etc.)
- Preferred travel pace  (relaxed, moderate, intense)
- Activity preferences (meeting locals, shopping, dining, adventure)
- Travel style (luxury, budget, authentic experiences)
- Social preferences (meeting locals, solo, groups)
- Any recurring interests

IGNORE completely:
- Budget mentions or changes
- Flight/hotel/booking details
- Scheduling requests
- Price negotiations
- Any transactional or logistical details

Only extract preferences that are actually expressed in the input. Do not invent or assume preferences.

Format your response as simple preference statements, one per line.
Example format:
User enjoys visiting museums.
User prefers an intense travel pace.
User values meeting local people.

---
USER INPUT:
{input}
---

Extract the long-term travel preferences:"""

        response = await self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract travel preferences from user conversations."},
                {"role": "user", "content": prompt.format(input=raw_input)}
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    async def store_preferences(self, summary: str, trip_name: str | None = None):
        """
        Store preference summary in the knowledge graph.
        
        Each call creates an "episode" in Graphiti, allowing the system to
        track how often preferences are mentioned across trips.
        
        Args:
            summary: Summarized preference statements
            trip_name: Optional trip identifier for context
        """
        if not self.graphiti:
            raise RuntimeError("PreferenceGraph not initialized. Call initialize() first.")

        # Add context about this being a user preference
        episode_content = f"Travel preferences for user: {summary}"
        
        # Create a unique episode name
        timestamp = datetime.now(timezone.utc)
        episode_name = trip_name or f"trip_{timestamp.isoformat()}"

        # Add episode to graph - Graphiti will extract entities and relationships
        await self.graphiti.add_episode(
            name=episode_name,
            episode_body=episode_content,
            source_description="User travel preference extraction",
            reference_time=timestamp,
        )

    async def get_preferences(self, query: str) -> str:
        """
        Query the knowledge graph for user preferences.
        
        Uses semantic search to find relevant preference information.
        
        Args:
            query: Natural language question about preferences
            
        Returns:
            Natural language response with relevant preferences
        """
        if not self.graphiti:
            raise RuntimeError("PreferenceGraph not initialized. Call initialize() first.")

        # Search the graph using Graphiti's search
        results = await self.graphiti.search(query=query, num_results=10)

        if not results:
            return "No preferences found for this query."

        # Compile results into a response - extract facts from edges
        facts = []
        for result in results:
            # Graphiti returns edges with 'fact' attribute
            if hasattr(result, 'fact') and result.fact:
                facts.append(result.fact)
            elif hasattr(result, 'name') and result.name:
                facts.append(f"User preference: {result.name}")

        if not facts:
            return "No specific preferences found for this query."

        # Use LLM to synthesize a coherent response
        synthesis_prompt = f"""Based on these facts from the user's preference history:
{chr(10).join(f'- {fact}' for fact in facts)}

Answer this question naturally: {query}

Provide a concise, helpful response."""

        response = await self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You synthesize user preferences into helpful responses."},
                {"role": "user", "content": synthesis_prompt}
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    async def get_all_preferences(self) -> list[str]:
        """
        Retrieve all stored preferences for the user.
        
        Returns:
            List of all preference facts in the graph
        """
        if not self.graphiti:
            raise RuntimeError("PreferenceGraph not initialized. Call initialize() first.")

        # Broad search to get all preferences
        results = await self.graphiti.search(
            query="What are all the user's travel preferences?",
            num_results=50
        )

        facts = []
        for result in results:
            if hasattr(result, 'fact') and result.fact:
                facts.append(result.fact)

        return facts

    async def reset_graph(self):
        """
        Clear all data from the graph. Use with caution!
        """
        if not self.driver:
            raise RuntimeError("PreferenceGraph not initialized. Call initialize() first.")

        # Delete all nodes and relationships
        await self.driver.execute_query("MATCH (n) DETACH DELETE n")
        print("Graph has been reset.")
