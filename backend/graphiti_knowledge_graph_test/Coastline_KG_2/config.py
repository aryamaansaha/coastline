import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY environment variable is required. "
        "Set it in your .env file or export it: export OPENAI_API_KEY=your-key"
    )

# FalkorDB Configuration
FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", 6379))

# Graph Configuration
GRAPH_NAME = "travel_preferences"
USER_ID = "default_user"  # Single user app

