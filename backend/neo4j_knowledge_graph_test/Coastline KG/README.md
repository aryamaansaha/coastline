# Coastline KG - User Preference Knowledge Graph

> ⚠️ **DISCLAIMER: Work In Progress**
> 
> This module is a **standalone experimental prototype** and is **NOT yet integrated** into the main Coastline application. Integration work is ongoing. This code serves as a proof-of-concept for storing and retrieving user travel preferences using a knowledge graph architecture.

---

A knowledge graph system for storing and querying user travel preferences using **Graphiti** (an LLM-powered knowledge graph framework) with **FalkorDB** (a high-performance graph database). This implementation provides a streamlined API with convenience functions and a singleton pattern for easy integration.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Concepts](#core-concepts)
  - [What is Graphiti?](#what-is-graphiti)
  - [What is FalkorDB?](#what-is-falkordb)
  - [The Preference Extraction Problem](#the-preference-extraction-problem)
- [Project Structure](#project-structure)
- [Components](#components)
  - [docker-compose.yml](#docker-composeyml)
  - [preference_graph.py](#preference_graphpy)
  - [test_graph.py](#test_graphpy)
  - [env.example](#envexample)
- [Setup](#setup)
  - [Prerequisites](#prerequisites)
  - [Step 1: Start FalkorDB](#step-1-start-falkordb)
  - [Step 2: Set Up Python Environment](#step-2-set-up-python-environment)
  - [Step 3: Configure Environment Variables](#step-3-configure-environment-variables)
  - [Step 4: Test the Installation](#step-4-test-the-installation)
- [Usage](#usage)
  - [Quick Start (Convenience Functions)](#quick-start-convenience-functions)
  - [Class-Based Usage](#class-based-usage)
  - [Querying Preferences](#querying-preferences)
  - [Getting All Preferences by Category](#getting-all-preferences-by-category)
- [API Reference](#api-reference)
  - [Convenience Functions](#convenience-functions)
  - [PreferenceGraph Class](#preferencegraph-class)
- [How Graphiti Works](#how-graphiti-works)
  - [Episode-Based Knowledge Ingestion](#episode-based-knowledge-ingestion)
  - [Automatic Entity Extraction](#automatic-entity-extraction)
  - [Hybrid Search](#hybrid-search)
- [Data Flow](#data-flow)
- [Test Script Walkthrough](#test-script-walkthrough)
- [FalkorDB Browser UI](#falkordb-browser-ui)
- [Troubleshooting](#troubleshooting)
- [Dependencies](#dependencies)
- [Future Integration Plans](#future-integration-plans)

---

## Overview

The Coastline travel planning application needs to remember user preferences across multiple trips. Traditional databases struggle with this because:

1. Preferences are expressed in natural language ("I love art museums")
2. Preferences are implicit ("Can we squeeze in a museum?" → user likes museums)
3. Queries are also natural language ("What does the user enjoy?")

This module solves these challenges by:

1. **Extracting preferences from conversations** using LLM summarization
2. **Storing them in a knowledge graph** where entities and relationships are automatically discovered
3. **Enabling natural language queries** that leverage semantic search and graph traversal

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        User Conversation                              │
│                                                                       │
│  Initial Q/A:                                                         │
│  Q: What would you like to see more of?                               │
│  A: museums, maybe some beaches                                       │
│                                                                       │
│  Chat History:                                                        │
│  turn 1: the flights are kinda expensive...                           │
│  turn 2: i've increased the budget, allocate more towards shopping   │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    LLM Preference Extraction                          │
│                       (OpenAI GPT-4o-mini)                            │
│                                                                       │
│  ✓ EXTRACTED (Long-term preferences):                                │
│    - User enjoys museums                                              │
│    - User enjoys beaches                                              │
│    - User prefers an intense travel pace                              │
│    - User likes meeting locals                                        │
│                                                                       │
│  ✗ FILTERED (Transactional/temporary):                               │
│    - Budget changes                                                   │
│    - Flight costs                                                     │
│    - Hotel bookings                                                   │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                           Graphiti                                    │
│                   (LLM-Powered Knowledge Graph)                       │
│                                                                       │
│  Automatic Processing:                                                │
│  ┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐   │
│  │ Entity          │ → │ Relationship      │ → │ Embedding       │   │
│  │ Extraction      │   │ Discovery         │   │ Generation      │   │
│  └─────────────────┘   └──────────────────┘   └─────────────────┘   │
│                                                                       │
│  ┌─────────────────┐   ┌──────────────────┐                          │
│  │ Entity          │ → │ Fact             │                          │
│  │ Resolution      │   │ Storage          │                          │
│  └─────────────────┘   └──────────────────┘                          │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          FalkorDB                                     │
│               (Redis-Compatible Graph Database)                       │
│                                                                       │
│  Stored as Graph:                                                     │
│                                                                       │
│     ┌──────┐    ENJOYS     ┌─────────┐                               │
│     │ User │───────────────│ Museums │                               │
│     └──────┘               └─────────┘                               │
│         │                                                             │
│         │ PREFERS          ┌──────────────┐                          │
│         └──────────────────│ Intense Pace │                          │
│         │                  └──────────────┘                          │
│         │ VALUES                                                      │
│         └──────────────────│ Local People │                          │
│                            └──────────────┘                          │
│                                                                       │
│  Ports: 6379 (Redis), 3000 (Browser UI)                              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Core Concepts

### What is Graphiti?

[Graphiti](https://github.com/getzep/graphiti) is an open-source framework by Zep AI that builds knowledge graphs from unstructured text. Unlike traditional graph databases that require you to define schemas and manually extract entities, Graphiti uses LLMs to:

1. **Extract entities** from natural language (e.g., "museums" from "I love art museums")
2. **Discover relationships** (e.g., "User ENJOYS museums")
3. **Resolve entities** (e.g., "art museums" and "museums" are the same thing)
4. **Generate embeddings** for semantic search

This means you can feed it raw text and get a queryable knowledge graph without any manual data modeling.

### What is FalkorDB?

[FalkorDB](https://www.falkordb.com/) is a high-performance graph database that:

- Uses the **Redis protocol** (port 6379), making it familiar and fast
- Supports **Cypher query language** for graph operations
- Provides a **browser-based UI** (port 3000) for visualization
- Is designed for **low-latency, real-time** applications
- Runs as a lightweight **Docker container**

FalkorDB serves as the storage backend for Graphiti, holding all the nodes, edges, and embeddings.

### The Preference Extraction Problem

When users chat with a travel planning AI, they express many things:

| User Says | Type | Should Store? |
|-----------|------|---------------|
| "I love visiting museums" | **Preference** | ✓ Yes |
| "Intense pace, see as much as possible" | **Preference** | ✓ Yes |
| "Would like to meet locals" | **Preference** | ✓ Yes |
| "The flights are too expensive" | **Transactional** | ✗ No |
| "I've increased my budget to $5000" | **Transactional** | ✗ No |
| "Book the Hilton hotel" | **Transactional** | ✗ No |

This module filters out transactional noise and stores only the enduring preferences that should inform future trip recommendations.

---

## Project Structure

```
Coastline KG/
├── docker-compose.yml      # FalkorDB container configuration
├── requirements.txt        # Python dependencies
├── env.example             # Template for .env file
├── preference_graph.py     # Main module with PreferenceGraph class
├── test_graph.py           # Test script demonstrating all features
└── README.md               # This documentation
```

---

## Components

### docker-compose.yml

Defines the FalkorDB service:

```yaml
services:
  falkordb:
    image: falkordb/falkordb:latest
    container_name: coastline-falkordb
    ports:
      - "6379:6379"  # Redis protocol for graph operations
      - "3000:3000"  # FalkorDB Browser UI
    volumes:
      - falkordb_data:/data  # Persistent storage

volumes:
  falkordb_data:  # Named volume for data persistence
```

**Key Points:**
- Container is named `coastline-falkordb` for easy reference
- Data persists in a Docker volume (`falkordb_data`)
- Browser UI accessible at http://localhost:3000

### preference_graph.py

The core module with two usage patterns:

1. **Convenience Functions** (recommended for simple use):
   - `summarize_and_store(conversation, trip_context)` - One-step extraction and storage
   - `get_preferences(query)` - Natural language query
   - `get_all_user_preferences()` - Get all preferences by category
   - `cleanup()` - Close connections

2. **PreferenceGraph Class** (for advanced control):
   - Full control over initialization and lifecycle
   - Access to individual operations
   - Useful for batch processing or custom workflows

**Design Patterns:**
- **Singleton Pattern**: Uses a global `_graph_instance` to reuse connections
- **Lazy Initialization**: Graph is only created when first needed
- **Async/Await**: All database operations are asynchronous

### test_graph.py

A comprehensive test script that demonstrates:
1. Extracting preferences from a sample conversation
2. Storing them in the graph
3. Querying specific preferences
4. Retrieving all categorized preferences

Run it to verify your setup is working correctly.

### env.example

Template for environment variables:

```bash
OPENAI_API_KEY=your_openai_api_key_here
FALKORDB_HOST=localhost
FALKORDB_PORT=6379
```

Copy to `.env` and fill in your values.

---

## Setup

### Prerequisites

- **Python 3.11+** with async/await support
- **Docker** and **Docker Compose** for running FalkorDB
- **OpenAI API Key** for GPT-4o-mini access

### Step 1: Start FalkorDB

Navigate to the project directory and start FalkorDB:

```bash
cd "Coastline KG"
docker compose up -d
```

Verify it's running:

```bash
docker compose ps
# Should show: coastline-falkordb   falkordb/falkordb:latest   ...   Up
```

Check the browser UI: Open http://localhost:3000 in your browser.

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

```bash
# Copy the example file
cp env.example .env

# Edit and add your OpenAI API key
nano .env  # or use any text editor
```

Your `.env` should contain:

```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
FALKORDB_HOST=localhost
FALKORDB_PORT=6379
```

### Step 4: Test the Installation

```bash
python test_graph.py
```

You should see output showing:
1. Preferences being extracted
2. Preferences being stored
3. Query results for different questions
4. All categorized preferences

---

## Usage

### Quick Start (Convenience Functions)

The simplest way to use this module:

```python
import asyncio
from preference_graph import summarize_and_store, get_preferences, cleanup

async def main():
    # Store preferences from a conversation
    conversation = """
    Q: What would you like to see?
    A: I love art museums and historical sites
    
    Q: Travel pace?
    A: Pretty relaxed, I like to take my time
    
    Chat: The hotel looks great, book it. Also, I really enjoy local food.
    """
    
    # Extract and store in one call
    summary = await summarize_and_store(
        conversation=conversation,
        trip_context="rome_2024"
    )
    print(f"Stored preferences:\n{summary}")
    
    # Query with natural language
    attractions = await get_preferences("What attractions does the user enjoy?")
    print(f"\nAttractions: {attractions}")
    
    pace = await get_preferences("What travel pace does the user prefer?")
    print(f"\nPace: {pace}")
    
    # Always cleanup when done
    await cleanup()

asyncio.run(main())
```

### Class-Based Usage

For more control over the lifecycle:

```python
import asyncio
from preference_graph import PreferenceGraph

async def main():
    # Create and initialize
    graph = PreferenceGraph()
    await graph.initialize()
    
    # Manual summarization (synchronous - uses OpenAI directly)
    conversation = "I love street food and exploring local markets"
    summary = graph.summarize_preferences(conversation)
    
    # Store (async - writes to graph)
    await graph.store_preferences(summary, trip_context="bangkok_2024")
    
    # Query (async - searches graph)
    result = await graph.query_preferences(
        query="What food preferences does the user have?",
        num_results=5
    )
    print(result)
    
    # Get all preferences organized by category
    all_prefs = await graph.get_all_preferences()
    for category, prefs in all_prefs.items():
        print(f"\n{category.upper()}:")
        print(prefs)
    
    # Cleanup
    await graph.close()

asyncio.run(main())
```

### Querying Preferences

Natural language queries work by combining semantic search with graph traversal:

```python
# Specific queries
await get_preferences("What tourist attractions does the user like?")
await get_preferences("Does the user prefer fast or relaxed travel?")
await get_preferences("What are the user's food preferences?")
await get_preferences("Does the user enjoy meeting locals?")

# More complex queries
await get_preferences("Would the user enjoy a cooking class?")
await get_preferences("Should I recommend nightlife activities?")
await get_preferences("Is the user interested in cultural experiences?")
```

### Getting All Preferences by Category

The `get_all_preferences()` method queries five predefined categories:

```python
from preference_graph import get_all_user_preferences

prefs = await get_all_user_preferences()

# Returns dict with keys:
# - "attractions": What tourist attractions the user likes
# - "pace": Preferred travel pace
# - "social": Social preferences (solo, groups, meeting locals)
# - "activities": Preferred activities
# - "food": Food and dietary preferences
```

---

## API Reference

### Convenience Functions

#### `summarize_and_store(conversation: str, trip_context: str = "general") -> str`

One-step function to extract and store preferences.

**Parameters:**
- `conversation` (str): Raw Q/A and chat history text
- `trip_context` (str): Label for this trip (e.g., "paris_2024")

**Returns:**
- `str`: The extracted preference summary

**Example:**
```python
summary = await summarize_and_store(
    "I love beaches and want a relaxed pace",
    "maldives_trip"
)
```

---

#### `get_preferences(query: str) -> str`

Query stored preferences using natural language.

**Parameters:**
- `query` (str): Natural language question

**Returns:**
- `str`: Bullet-pointed list of relevant facts, or "No preferences found"

**Example:**
```python
result = await get_preferences("What does the user like?")
# Returns:
# - User enjoys visiting beaches
# - User prefers a relaxed travel pace
```

---

#### `get_all_user_preferences() -> dict`

Get all preferences organized by category.

**Returns:**
- `dict`: Categories as keys, preference strings as values

**Categories:**
- `attractions` - Tourist attraction preferences
- `pace` - Travel pace preferences
- `social` - Social/group preferences
- `activities` - Activity preferences
- `food` - Food/dietary preferences

---

#### `cleanup()`

Close the graph connection. Always call when done.

```python
await cleanup()
```

---

### PreferenceGraph Class

#### `__init__()`

Creates a new instance with OpenAI and FalkorDB clients.

**Note:** Does not connect to database. Call `initialize()` after.

---

#### `async initialize()`

Builds required indices and constraints in FalkorDB.

**Must be called before any storage/query operations.**

---

#### `async close()`

Closes the Graphiti connection.

---

#### `summarize_preferences(conversation: str) -> str`

**Synchronous** method that uses OpenAI to extract preferences.

Filters out budget, flights, hotels, and other transactional details.

---

#### `async store_preferences(summary: str, trip_context: str = "general")`

Stores preference summary in the graph as a Graphiti episode.

**Parameters:**
- `summary` (str): Preference statements to store
- `trip_context` (str): Trip identifier for context

---

#### `async query_preferences(query: str, num_results: int = 5) -> str`

Searches the graph and returns relevant facts.

**Parameters:**
- `query` (str): Natural language question
- `num_results` (int): Maximum facts to return (default: 5)

---

#### `async get_all_preferences() -> dict`

Queries all five preference categories.

---

## How Graphiti Works

### Episode-Based Knowledge Ingestion

Graphiti organizes knowledge into "episodes"—discrete chunks of information from a single source. When you call `store_preferences`:

```python
await self.graphiti.add_episode(
    name="user_preferences_paris_trip",
    episode_body="- User enjoys museums\n- User prefers relaxed pace",
    source=EpisodeType.text,
    source_description="User travel preferences from paris_trip",
    reference_time=datetime.now(timezone.utc),
)
```

Each episode is processed by the LLM to extract entities and relationships.

### Automatic Entity Extraction

Given the text "User enjoys visiting museums", Graphiti automatically:

1. **Extracts entities**: `User`, `museums`
2. **Identifies relationship**: `ENJOYS`
3. **Creates graph structure**: `(User)-[:ENJOYS]->(museums)`
4. **Generates embeddings**: Vector representations for semantic search
5. **Stores fact**: "User enjoys visiting museums" as edge property

### Hybrid Search

When you query, Graphiti uses three strategies:

1. **Semantic Search**: Finds facts with similar embeddings to your query
2. **Keyword Matching**: Looks for exact matches on key terms
3. **Graph Traversal**: Follows relationships to find connected facts

This hybrid approach ensures both precision (exact matches) and recall (semantically similar content).

---

## Data Flow

```
┌────────────────────────────────────────────────────────────────────┐
│ STORING PREFERENCES                                                 │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. User input (conversation) ─────────────────────────────────────▶
│     "I love museums, want intense pace, budget is $5000"           │
│                                                                     │
│  2. LLM Summarization (GPT-4o-mini) ───────────────────────────────▶
│     Filters: budget, flights, hotels                               │
│     Extracts: preferences only                                      │
│     Output: "- User enjoys museums\n- User prefers intense pace"   │
│                                                                     │
│  3. Graphiti Episode Creation ─────────────────────────────────────▶
│     Automatic: entity extraction, relationships, embeddings        │
│                                                                     │
│  4. FalkorDB Storage ──────────────────────────────────────────────▶
│     Nodes: User, Museums, Intense Pace                             │
│     Edges: ENJOYS, PREFERS (with fact properties)                  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ QUERYING PREFERENCES                                                │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Natural language query ────────────────────────────────────────▶
│     "What attractions does the user like?"                         │
│                                                                     │
│  2. Graphiti Search ───────────────────────────────────────────────▶
│     - Semantic: finds "museums" via embedding similarity           │
│     - Keyword: matches "attractions", "like"                        │
│     - Graph: traverses from User to connected attractions          │
│                                                                     │
│  3. Results Returned ──────────────────────────────────────────────▶
│     Facts: ["User enjoys museums"]                                 │
│     Formatted: "- User enjoys museums"                             │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Test Script Walkthrough

The `test_graph.py` script demonstrates the complete workflow:

```python
# Sample conversation (from design doc)
SAMPLE_CONVERSATION = """
Initial Q/A: 

Q: What would you like to see more of?
A: museums, maybe some beaches

Q: What pace would you like this trip?
A: pretty intense, wanna visit as many as possible

Q: Specific requests?
A: Would really like to spend a day meeting locals!

Chat History:

turn 1: the flights are kinda expensive, see if there are cheaper options?
turn 2: i've increased the budget, allocate more towards shopping
"""
```

**Step 1: Extract and Store**
```python
summary = await summarize_and_store(
    conversation=SAMPLE_CONVERSATION,
    trip_context="test_trip_1"
)
# Output:
# - User enjoys museums
# - User enjoys beaches
# - User prefers an intense travel pace
# - User likes meeting locals
# (Note: budget and flight mentions are filtered out)
```

**Step 2: Query Specific Preferences**
```python
queries = [
    "What kind of tourist attractions does the user like?",
    "What level of pace does the user prefer for trips?",
    "Does the user like meeting locals?",
]

for query in queries:
    result = await get_preferences(query)
    print(f"Query: {query}\nResult: {result}\n")
```

**Step 3: Get All Categorized Preferences**
```python
all_prefs = await get_all_user_preferences()

# Output:
# ATTRACTIONS:
# - User enjoys museums
# - User enjoys beaches
#
# PACE:
# - User prefers an intense travel pace
#
# SOCIAL:
# - User likes meeting locals
#
# ACTIVITIES:
# - No preferences found for this query.
#
# FOOD:
# - No preferences found for this query.
```

---

## FalkorDB Browser UI

Access the visual interface at http://localhost:3000

**Useful Cypher Queries:**

```cypher
-- See all nodes
MATCH (n) RETURN n LIMIT 50

-- See all relationships
MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 50

-- Find user preferences
MATCH (u:Entity {name: 'User'})-[r]->(p) RETURN u, r, p

-- Count entities by type
MATCH (n:Entity) RETURN n.entity_type, count(*) as count
```

---

## Troubleshooting

### Docker Issues

**Container won't start:**
```bash
docker compose logs falkordb  # Check logs
docker compose down && docker compose up -d  # Restart
```

**Port already in use:**
```bash
lsof -i :6379  # Find process using port
kill <PID>     # Stop it
```

### Connection Errors

**"Connection refused to localhost:6379":**
```bash
# Verify container is running
docker compose ps

# If not running, start it
docker compose up -d
```

### OpenAI Errors

**"Invalid API key":**
- Check `.env` file has correct key
- Ensure no extra spaces or quotes around key
- Verify key is active at https://platform.openai.com

**Rate limiting:**
- Add delays between calls
- Use GPT-4o-mini (cheaper, less likely to hit limits)

### Graph Errors

**"Indices already exist":**
This is handled gracefully—the code catches this exception and continues.

**Empty results:**
- Verify data was stored (check browser UI)
- Try broader queries
- Check if graph was accidentally cleared

### Stopping FalkorDB

```bash
# Stop container, keep data
docker compose down

# Stop and delete all data
docker compose down -v

# Remove the container manually
docker stop coastline-falkordb
docker rm coastline-falkordb
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `graphiti-core[falkordb]` | ≥0.5.0 | Knowledge graph framework with FalkorDB driver |
| `openai` | ≥1.0.0 | OpenAI API client for LLM operations |
| `python-dotenv` | ≥1.0.0 | Environment variable loading from `.env` |

**Installed Transitively:**
- `falkordb` - Python client for FalkorDB
- `redis` - Redis protocol support
- `pydantic` - Data validation
- `httpx` - Async HTTP client
- `numpy` - Vector operations
- `tiktoken` - Token counting

---

## Future Integration Plans

This experimental module is designed for eventual integration with the main Coastline backend:

### Planned Enhancements

1. **Multi-User Support**
   - Replace global singleton with per-user graph instances
   - Partition preferences by user ID
   - Support concurrent users

2. **Agent Graph Integration**
   - Query preferences during trip planning
   - Use preferences to personalize recommendations
   - Feed historical preferences to the planning agent

3. **Production Deployment**
   - Configure persistent volumes for FalkorDB
   - Add health checks and monitoring
   - Implement caching layer for frequent queries

4. **Enhanced Preference Types**
   - Accommodation preferences
   - Transportation preferences
   - Accessibility requirements
   - Seasonal preferences

5. **Preference Decay**
   - Track when preferences were expressed
   - Weight recent preferences more heavily
   - Allow users to update/remove preferences

---

## References

- [Graphiti Documentation](https://github.com/getzep/graphiti)
- [FalkorDB Documentation](https://docs.falkordb.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)

---

*Last updated: December 2024*
