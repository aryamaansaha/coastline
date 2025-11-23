from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="coastline-mcp")


# Example Tool: Get flight options
@mcp.tool()
def get_flight_options(origin: str, destination: str, date: str) -> list[dict]:
    """Get flight options for a given origin, destination, and date."""
    return []