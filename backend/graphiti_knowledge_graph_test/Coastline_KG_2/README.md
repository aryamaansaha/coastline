# Travel Preference Knowledge Graph

> ⚠️ **DISCLAIMER: Work In Progress**
> 
> This module is a **standalone experimental prototype** and is **NOT yet integrated** into the main Coastline application. Integration work is ongoing. This code serves as a proof-of-concept for storing and retrieving user travel preferences using a knowledge graph architecture.

---

A sophisticated knowledge graph system for storing, extracting, and querying user travel preferences using **FalkorDB** (a Redis-compatible graph database) and **Graphiti** (an LLM-powered knowledge graph framework).

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Concepts](#core-concepts)
  - [What is a Knowledge Graph?](#what-is-a-knowledge-graph)
  - [Why FalkorDB + Graphiti?](#why-falkordb--graphiti)
  - [Preference Extraction Pipeline](#preference-extraction-pipeline)
- [Components](#components)
  - [config.py](#configpy)
  - [preference_graph.py](#preference_graphpy)
  - [example.py](#examplepy)
- [Setup](#setup)
  - [Prerequisites](#prerequisites)
  - [1. Start FalkorDB with Docker](#1-start-falkordb-with-docker)
  - [2. Set Environment Variables](#2-set-environment-variables)
  - [3. Install Dependencies](#3-install-dependencies)
- [Usage](#usage)
  - [Basic Usage](#basic-usage)
  - [Processing Multiple Trips](#processing-multiple-trips)
  - [Querying Preferences](#querying-preferences)
- [API Reference](#api-reference)
  - [PreferenceGraph Class](#preferencegraph-class)
- [How It Works](#how-it-works)
  - [Step 1: Preference Summarization](#step-1-preference-summarization)
  - [Step 2: Entity Extraction & Storage](#step-2-entity-extraction--storage)
  - [Step 3: Semantic Search & Retrieval](#step-3-semantic-search--retrieval)
- [Example Workflow](#example-workflow)
- [Troubleshooting](#troubleshooting)
- [Dependencies](#dependencies)

---

## Overview

This module enables the Coastline travel planning application to:

1. **Extract long-term travel preferences** from user conversations (Q&A sessions and chat history)
2. **Filter out transactional noise** (budget changes, flight bookings, hotel details)
3. **Store preferences in a knowledge graph** with automatic entity extraction and relationship discovery
4. **Query preferences using natural language** with semantic search capabilities

The goal is to build a persistent "memory" of what users like across multiple trips, enabling more personalized travel recommendations over time.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Conversation                           │
│  "I love museums, want an intense pace, would like to meet      │
│   locals, budget is $5000, flights look expensive..."           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Preference Summarization                       │
│                      (OpenAI GPT-4o-mini)                        │
│                                                                  │
│  Filters out: budget, flights, hotels, scheduling               │
│  Extracts: attractions, pace, activities, travel style          │
│                                                                  │
│  Output:                                                         │
│  - "User enjoys visiting museums"                                │
│  - "User prefers an intense travel pace"                         │
│  - "User values meeting local people"                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Graphiti Layer                            │
│                                                                  │
│  • Automatic entity extraction from natural language             │
│  • Relationship discovery between entities                       │
│  • Entity resolution (deduplication)                             │
│  • Embedding generation for semantic search                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FalkorDB (Graph Store)                       │
│                                                                  │
│  Nodes: User, Preference, Activity, Pace, etc.                  │
│  Edges: ENJOYS, PREFERS, VALUES, etc.                           │
│                                                                  │
│  Example:                                                        │
│  (User)--[ENJOYS]-->(Museums)                                   │
│  (User)--[PREFERS]-->(Intense Pace)                             │
│  (User)--[VALUES]-->(Meeting Locals)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Concepts

### What is a Knowledge Graph?

A knowledge graph represents information as a network of **entities (nodes)** connected by **relationships (edges)**. Unlike traditional databases that store data in tables, knowledge graphs capture the semantic meaning and connections between concepts.

For travel preferences, this means:
- **Nodes**: "User", "Museums", "Beaches", "Intense Pace", "Local Culture"
- **Edges**: "User ENJOYS Museums", "User PREFERS Intense Pace"

This structure enables powerful queries like "What attractions does the user like?" that traverse the graph to find all connected preferences.

### Why FalkorDB + Graphiti?

| Component | Role |
|-----------|------|
| **FalkorDB** | High-performance, Redis-compatible graph database. Provides the storage layer with native graph querying via Cypher. Runs as a lightweight Docker container. |
| **Graphiti** | LLM-powered knowledge graph framework by Zep AI. Automatically extracts entities and relationships from natural language text, handles entity resolution, and provides semantic search over the graph. |

Together, they eliminate the need to manually define schemas or write complex entity extraction logic—the LLM handles the semantic understanding.

### Preference Extraction Pipeline

The system distinguishes between:

**Long-term Preferences (STORED):**
- Types of attractions enjoyed (museums, beaches, nature)
- Travel pace preferences (relaxed, moderate, intense)
- Activity preferences (shopping, dining, adventure)
- Social preferences (meeting locals, solo travel)
- Travel style (luxury, budget-conscious)

**Transactional Details (IGNORED):**
- Budget amounts or changes
- Flight/hotel bookings
- Scheduling requests
- Price negotiations

This filtering ensures the knowledge graph captures enduring user preferences, not trip-specific logistics.

---

## Components

### config.py

Configuration management module that loads environment variables:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# FalkorDB Configuration
FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", 6379))

# Graph Configuration
GRAPH_NAME = "travel_preferences"
USER_ID = "default_user"
```

**Key Points:**
- Raises `ValueError` if `OPENAI_API_KEY` is not set (required for LLM operations)
- FalkorDB defaults to `localhost:6379` (standard Redis port)
- Uses `python-dotenv` to load variables from a `.env` file

### preference_graph.py

The core module containing the `PreferenceGraph` class. Provides all functionality for:
- Initializing the graph database connection
- Summarizing raw user input into preference statements
- Storing preferences as graph episodes
- Querying preferences with natural language
- Retrieving all stored preferences
- Resetting the graph

See the [API Reference](#api-reference) section for detailed method documentation.

### example.py

A comprehensive demonstration script showing:
1. Processing multiple trip conversations
2. Extracting preferences from each
3. Storing them in the knowledge graph
4. Querying with various natural language questions
5. Retrieving all stored preferences

This script is designed to be run directly to verify the system is working correctly.

---

## Setup

### Prerequisites

- **Python 3.11+** (async/await support required)
- **Docker** (for running FalkorDB)
- **OpenAI API Key** (for GPT-4o-mini access)

### 1. Start FalkorDB with Docker

```bash
docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest
```

This command:
- Exposes **port 6379**: Redis protocol for graph operations (used by the Python client)
- Exposes **port 3000**: FalkorDB Browser UI for visualization (optional but helpful for debugging)
- Runs in interactive mode (`-it`) with auto-cleanup (`--rm`)

**Alternative: Background Mode**
```bash
docker run -d -p 6379:6379 -p 3000:3000 --name falkordb falkordb/falkordb:latest
```

To stop: `docker stop falkordb && docker rm falkordb`

### 2. Set Environment Variables

Create a `.env` file in the `Coastline_KG_2` directory:

```bash
# Required
OPENAI_API_KEY=your-openai-api-key-here

# Optional (defaults shown)
FALKORDB_HOST=localhost
FALKORDB_PORT=6379
```

**Security Note:** Never commit your `.env` file to version control. Add it to `.gitignore`.

### 3. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install packages
pip install -r requirements.txt
```

**Dependencies Installed:**
- `graphiti-core[falkordb]>=0.24.1` - Graphiti with FalkorDB driver
- `openai>=1.0.0` - OpenAI Python SDK for LLM calls
- `python-dotenv>=1.0.0` - Environment variable management

---

## Usage

### Basic Usage

```python
import asyncio
from preference_graph import PreferenceGraph

async def main():
    # Initialize the graph
    pg = PreferenceGraph()
    await pg.initialize()
    
    # Raw user input (from Q/A session or chat)
    raw_input = """
    Q: What would you like to see?
    A: I love art museums and historical sites
    
    Q: Travel pace?
    A: Relaxed, I want to really absorb each place
    """
    
    # Step 1: Summarize to extract preferences
    summary = await pg.summarize_preferences(raw_input)
    print(f"Extracted: {summary}")
    # Output:
    # User enjoys visiting art museums.
    # User enjoys exploring historical sites.
    # User prefers a relaxed travel pace.
    
    # Step 2: Store in knowledge graph
    await pg.store_preferences(summary, trip_name="rome_trip_2024")
    
    # Step 3: Query later
    result = await pg.get_preferences("What attractions does the user like?")
    print(result)
    
    # Cleanup
    await pg.close()

asyncio.run(main())
```

### Processing Multiple Trips

The knowledge graph accumulates preferences across multiple trips, building a richer user profile over time:

```python
async def process_multiple_trips():
    pg = PreferenceGraph()
    await pg.initialize()
    
    trips = [
        ("paris_2024", "User mentioned loving impressionist art and cafe culture"),
        ("tokyo_2024", "User enjoyed street food tours and temple visits"),
        ("barcelona_2024", "User loved the architecture and beach afternoons"),
    ]
    
    for trip_name, conversation in trips:
        summary = await pg.summarize_preferences(conversation)
        await pg.store_preferences(summary, trip_name=trip_name)
    
    # Now queries reflect preferences from ALL trips
    art_prefs = await pg.get_preferences("What art-related interests does the user have?")
    # Might return preferences about impressionist art, temples, architecture
    
    await pg.close()
```

### Querying Preferences

Natural language queries work because Graphiti combines:
- **Semantic search**: Finding relevant nodes based on meaning
- **Graph traversal**: Following relationships to connected entities
- **LLM synthesis**: Generating natural language responses

```python
# Specific queries
await pg.get_preferences("What tourist attractions does the user like?")
await pg.get_preferences("Does the user prefer fast or slow travel?")
await pg.get_preferences("What food experiences interest the user?")
await pg.get_preferences("Does the user like meeting local people?")

# Broad query for all preferences
all_prefs = await pg.get_all_preferences()
for pref in all_prefs:
    print(f"- {pref}")
```

---

## API Reference

### PreferenceGraph Class

#### `__init__()`
Initializes the OpenAI client. Does NOT connect to FalkorDB yet.

```python
pg = PreferenceGraph()
```

---

#### `async initialize()`
Establishes connection to FalkorDB and builds required indices/constraints.

**Must be called before any other async methods.**

```python
await pg.initialize()
```

---

#### `async close()`
Closes the Graphiti/FalkorDB connection. Always call when done.

```python
await pg.close()
```

---

#### `async summarize_preferences(raw_input: str) -> str`
Extracts long-term travel preferences from raw user input using GPT-4o-mini.

**Parameters:**
- `raw_input` (str): Raw text containing Q/A responses and/or chat history

**Returns:**
- `str`: Summarized preference statements, one per line

**Example:**
```python
summary = await pg.summarize_preferences("""
    Q: What would you like to do?
    A: Visit museums and try local food
    
    Chat: The flights are too expensive, find cheaper ones.
""")
# Returns:
# "User enjoys visiting museums.
#  User enjoys trying local food."
# (Note: flight mention is filtered out)
```

---

#### `async store_preferences(summary: str, trip_name: str | None = None)`
Stores preference summary in the knowledge graph as a Graphiti "episode".

**Parameters:**
- `summary` (str): Preference statements to store (typically from `summarize_preferences`)
- `trip_name` (str, optional): Identifier for the trip context. Defaults to timestamp-based name.

**Behavior:**
- Creates nodes for entities mentioned (User, Museums, Local Food, etc.)
- Creates edges representing relationships (ENJOYS, PREFERS, etc.)
- Graphiti handles entity resolution (deduplicates "museums" across trips)

```python
await pg.store_preferences(summary, trip_name="paris_spring_2024")
```

---

#### `async get_preferences(query: str) -> str`
Queries the knowledge graph using natural language.

**Parameters:**
- `query` (str): Natural language question about user preferences

**Returns:**
- `str`: Natural language response synthesized from graph facts

**How it works:**
1. Graphiti performs semantic search over the graph
2. Returns up to 10 relevant "facts" (edge properties)
3. GPT-4o-mini synthesizes a coherent response

```python
result = await pg.get_preferences("What kind of food does the user like?")
# Returns: "The user enjoys trying local food and has shown interest
#           in street food experiences and cooking classes."
```

---

#### `async get_all_preferences() -> list[str]`
Retrieves all stored preferences as a list of fact strings.

**Returns:**
- `list[str]`: All preference facts stored in the graph (up to 50)

```python
all_facts = await pg.get_all_preferences()
for fact in all_facts:
    print(f"- {fact}")
```

---

#### `async reset_graph()`
**⚠️ DESTRUCTIVE**: Deletes all nodes and relationships from the graph.

Use for testing or to start fresh. Data cannot be recovered.

```python
await pg.reset_graph()  # Deletes everything!
```

---

## How It Works

### Step 1: Preference Summarization

The `summarize_preferences` method uses a carefully crafted prompt:

```
You are analyzing a traveler's input to extract their long-term travel preferences.

Examples of what you can extract IF PRESENT IN THE USER INPUT:
- Types of attractions they enjoy (museums, beaches, nature, etc.)
- Preferred travel pace (relaxed, moderate, intense)
- Activity preferences (meeting locals, shopping, dining, adventure)
...

IGNORE completely:
- Budget mentions or changes
- Flight/hotel/booking details
- Scheduling requests
...
```

This prompt ensures:
- Only expressed preferences are extracted (no hallucination)
- Transactional details are filtered out
- Output format is consistent (one preference per line)

### Step 2: Entity Extraction & Storage

When you call `store_preferences`, Graphiti:

1. **Parses the text** using its LLM backbone
2. **Extracts entities**: "User", "museums", "intense travel pace", etc.
3. **Discovers relationships**: "User" → ENJOYS → "museums"
4. **Resolves duplicates**: If "museums" already exists, it links rather than creates
5. **Generates embeddings**: For semantic similarity search later
6. **Stores in FalkorDB**: As nodes and edges in the graph

This happens automatically—no manual schema definition required.

### Step 3: Semantic Search & Retrieval

When you call `get_preferences`:

1. **Query embedding**: Your question is converted to a vector
2. **Semantic search**: Graphiti finds facts with similar embeddings
3. **Graph traversal**: Related facts are also retrieved via graph edges
4. **LLM synthesis**: Results are formatted into a natural response

Example:
```
Query: "What attractions does the user like?"
         ↓
[Semantic Search finds edges with "attractions" in embedding space]
         ↓
Facts found:
- "User enjoys visiting museums"
- "User enjoys exploring beaches"
         ↓
[LLM synthesizes response]
         ↓
Response: "The user enjoys visiting museums and exploring beaches."
```

---

## Example Workflow

Run the complete demo:

```bash
# Make sure FalkorDB is running
docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest

# In another terminal
source venv/bin/activate
python example.py
```

Expected output:

```
============================================================
Travel Preference Knowledge Graph Demo
============================================================

✓ Connected to FalkorDB

----------------------------------------
Processing Trip 1...
----------------------------------------

Extracted preferences:
User enjoys visiting museums.
User enjoys exploring beaches.
User prefers an intense travel pace.
User values meeting local people.

✓ Stored in knowledge graph

----------------------------------------
Processing Trip 2...
----------------------------------------

Extracted preferences:
User enjoys trying local food.
User enjoys exploring street markets.
User is interested in taking cooking classes.
User enjoys visiting art museums.

✓ Stored in knowledge graph

============================================================
Querying Historical Preferences
============================================================

📍 Query: What tourist attractions does the user like?
Response: The user enjoys visiting museums, particularly art museums, 
          and exploring beaches. They also like exploring street markets.

🏃 Query: What pace of travel does the user prefer?
Response: The user prefers an intense travel pace, wanting to visit 
          as many places as possible.

🍜 Query: What are the user's food and dining preferences?
Response: The user enjoys trying local food and exploring street markets. 
          They're also interested in taking cooking classes.

👥 Query: Does the user like meeting locals or social activities?
Response: Yes, the user values meeting local people during their travels.

============================================================
All Stored Preferences
============================================================
  1. User enjoys visiting museums
  2. User enjoys exploring beaches
  3. User prefers an intense travel pace
  4. User values meeting local people
  5. User enjoys trying local food
  6. User enjoys exploring street markets
  7. User is interested in taking cooking classes
  8. User enjoys visiting art museums

✓ Connection closed
```

---

## Troubleshooting

### Connection Refused to FalkorDB

```
Error: Connection refused to localhost:6379
```

**Solution:** Ensure FalkorDB Docker container is running:
```bash
docker ps  # Should show falkordb/falkordb container
docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest
```

### OpenAI API Key Error

```
ValueError: OPENAI_API_KEY environment variable is required
```

**Solution:** Set your API key in `.env` or export it:
```bash
export OPENAI_API_KEY=sk-your-key-here
```

### "PreferenceGraph not initialized" Error

```
RuntimeError: PreferenceGraph not initialized. Call initialize() first.
```

**Solution:** Always call `await pg.initialize()` before using other methods:
```python
pg = PreferenceGraph()
await pg.initialize()  # Don't forget this!
```

### Empty Query Results

If queries return "No preferences found":
1. Verify preferences were stored (check FalkorDB Browser at http://localhost:3000)
2. Try broader queries
3. Ensure the graph wasn't reset

### Viewing the Graph

Open http://localhost:3000 in your browser to access FalkorDB's visualization UI. You can run Cypher queries like:
```cypher
MATCH (n) RETURN n LIMIT 25
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `graphiti-core[falkordb]` | ≥0.24.1 | Knowledge graph framework with FalkorDB driver |
| `openai` | ≥1.0.0 | OpenAI API client for LLM operations |
| `python-dotenv` | ≥1.0.0 | Load environment variables from `.env` files |

**Transitive Dependencies** (installed automatically):
- `falkordb` - Python client for FalkorDB
- `redis` - Redis protocol support
- `httpx` - Async HTTP client
- `pydantic` - Data validation
- `numpy` - Vector operations for embeddings
- `tiktoken` - Token counting for OpenAI

---

## Future Integration

This module is designed to eventually integrate with the main Coastline backend:

1. **Agent Graph Integration**: The preference graph will be queried during trip planning to personalize recommendations
2. **Multi-User Support**: Replace `USER_ID = "default_user"` with actual user session IDs
3. **Persistence**: Configure FalkorDB with persistent volumes for production
4. **Caching**: Add preference caching to reduce graph queries

---

*Last updated: December 2024*
