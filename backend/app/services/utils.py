import re
import json
import time
from typing import Callable
from functools import wraps
from amadeus import ResponseError
import logging

logger = logging.getLogger(__name__)

class ResponseParser:
    """Robust parser to handle LLM responses wrapped in various markdown formats, including HTML, JSON, and CSS."""

    @staticmethod
    def clean_response(content) -> str:
        """
        Removes markdown code blocks and cleans up LLM response content.
        Handles various formats like ```json, ```html, ```xml, ```css, etc.
        """
        if not content:
            return ""

        # Extract content from AIMessage object if needed
        if hasattr(content, 'content'):
            content = content.content
        elif hasattr(content, 'text'):
            content = content.text
        
        # Ensure it's a string
        if not isinstance(content, str):
            content = str(content)

        content = content.strip()

        # Pattern to match various code block formats, now including css
        # Matches: ```json, ```html, ```xml, ```text, ```css, ``` (plain), etc.
        code_block_patterns = [
            r'^```(?:json|html|xml|text|markdown|md|css)?\s*\n?(.*?)\n?```$',  # Standard code blocks
            r'^`{3,}\s*(?:json|html|xml|text|markdown|md|css)?\s*\n?(.*?)\n?`{3,}$',  # Variable length backticks
            r'^```\s*(.*?)\s*```$',  # Simple triple backticks
            r'^`([^`]*)`$',  # Single backticks
        ]

        # Try each pattern to extract content
        for pattern in code_block_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                break

        return content

    @staticmethod
    def extract_json(content: str) -> dict:
        """
        Extracts JSON from LLM response, handling various formatting issues.
        """
        content = ResponseParser.clean_response(content)

        # Try to find JSON object boundaries
        json_patterns = [
            r'\{.*\}',  # Find any JSON-like object
            r'\[.*\]',  # Or JSON array
        ]

        for pattern in json_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                json_str = match.group(0)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue

        # If no pattern matches, try to parse the entire cleaned content
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            print(f"Content: {content[:200]}...")
            return {}

    @staticmethod
    def extract_html(content: str) -> str:
        """
        Extracts HTML from LLM response, handling markdown formatting.
        """
        content = ResponseParser.clean_response(content)

        # Remove any remaining markdown artifacts
        content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)  # Remove markdown headers
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Remove bold markdown
        content = re.sub(r'\*(.*?)\*', r'\1', content)  # Remove italic markdown

        return content.strip()

    @staticmethod
    def extract_css(content: str) -> str:
        """
        Extracts CSS from LLM response, handling markdown formatting and <style> tags.
        Handles:
        - ```css ... ```
        - <style> ... </style>
        - plain CSS output
        """
        content = ResponseParser.clean_response(content)

        # First, try to extract from <style>...</style> if present
        style_tag_pattern = r'<style[^>]*>(.*?)<\/style>'
        match = re.search(style_tag_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            css_content = match.group(1).strip()
            return css_content

        # Remove any markdown headers or formatting
        content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)  # Remove markdown headers
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Remove bold markdown
        content = re.sub(r'\*(.*?)\*', r'\1', content)  # Remove italic markdown

        # Remove any stray <style> or </style> tags if present
        content = re.sub(r'</?style[^>]*>', '', content, flags=re.IGNORECASE)

        return content.strip()


# ============================================================================
# RETRY HELPER WITH EXPONENTIAL BACKOFF
# ============================================================================

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for retrying functions with exponential backoff.
    Useful for handling rate limiting (429) and transient errors.
    
    Args:
        max_retries: Maximum number of retry attempts (total tries = max_retries + 1)
        base_delay: Base delay in seconds (doubles each retry)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except ResponseError as e:
                    last_exception = e
                    error_str = str(e)
                    
                    # Check if it's a rate limit error (429)
                    if "[429]" in error_str or "rate" in error_str.lower():
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"Rate limited (429), retrying in {delay}s... (attempt {attempt + 1}/{max_retries + 1})")
                            time.sleep(delay)
                            continue
                    
                    # For other errors, don't retry
                    raise
                except Exception as e:
                    # For non-Amadeus errors, don't retry
                    raise
            
            # If we exhausted all retries, raise the last exception
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator