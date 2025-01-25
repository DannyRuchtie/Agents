"""Search agent module for web search functionality."""
import os
from typing import List, Dict, Optional
import aiohttp
from urllib.parse import quote_plus

from .base_agent import BaseAgent
from config.settings import debug_print

SEARCH_SYSTEM_PROMPT = """You are a search expert that helps find and summarize information from the web.
Focus on providing accurate, relevant, and well-organized information from reliable sources."""

class SearchResult:
    """Class to represent a search result."""
    def __init__(self, title: str, link: str, snippet: str):
        self.title = title
        self.link = link
        self.snippet = snippet

    def __str__(self) -> str:
        return f"Title: {self.title}\nSnippet: {self.snippet}\nLink: {self.link}\n"

class SearchAgent(BaseAgent):
    """Agent for web search functionality using Google Custom Search."""
    
    def __init__(self):
        """Initialize the Search Agent."""
        super().__init__(
            agent_type="search",
            system_prompt=SEARCH_SYSTEM_PROMPT,
        )
        
        # Get Google API credentials
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        
        if not self.google_api_key or not self.search_engine_id:
            debug_print("Warning: Google API key or Search Engine ID not found. Search functionality will be limited.")
    
    async def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Perform a web search using Google Custom Search API.
        
        Args:
            query: The search query
            num_results: Number of results to return (max 10)
            
        Returns:
            List of SearchResult objects
        """
        try:
            # Ensure num_results is within bounds
            num_results = min(max(1, num_results), 10)
            
            # Build the search URL
            encoded_query = quote_plus(query)
            url = (
                f"https://www.googleapis.com/customsearch/v1"
                f"?key={self.google_api_key}"
                f"&cx={self.search_engine_id}"
                f"&q={encoded_query}"
                f"&num={num_results}"
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        raise Exception(f"Search request failed: {error_data.get('error', {}).get('message', 'Unknown error')}")
                    
                    data = await response.json()
                    
                    if "items" not in data:
                        return []
                    
                    results = []
                    for item in data["items"]:
                        result = SearchResult(
                            title=item.get("title", ""),
                            link=item.get("link", ""),
                            snippet=item.get("snippet", "")
                        )
                        results.append(result)
                    
                    return results
                    
        except Exception as e:
            debug_print(f"Search error: {str(e)}")
            return []
    
    def format_results(self, results: List[SearchResult]) -> str:
        """Format search results into a conversational, friendly response.
        
        Args:
            results: List of SearchResult objects
            
        Returns:
            Formatted string of results in a friendly tone
        """
        if not results:
            return "I looked around but couldn't find anything relevant. Would you like to try rephrasing your search?"
            
        # Start with a friendly intro
        formatted = ["Hey! I found some interesting information for you:"]
        
        for i, result in enumerate(results, 1):
            # Format each result in a more conversational way
            formatted.append(f"\n• {result.title}")
            if result.snippet:
                formatted.append(f"  {result.snippet}")
            formatted.append(f"  You can read more here: {result.link}")
        
        return "\n".join(formatted)
    
    async def process(self, query: str) -> str:
        """Process a search query and return formatted results in a friendly manner.
        
        Args:
            query: The search query
            
        Returns:
            Conversational response with search results
        """
        try:
            # Perform the search
            results = await self.search(query)
            
            if not results:
                return "I tried searching but couldn't find anything specific. Maybe we could try a different search term?"
            
            # Format the results in a friendly way
            formatted_results = self.format_results(results)
            
            # Generate a conversational summary using the language model
            prompt = (
                f"You are a friendly AI assistant helping with a search. Based on these search results for '{query}':\n\n"
                f"{formatted_results}\n\n"
                "Please provide a brief, friendly summary of the key points in a conversational tone, "
                "as if you're chatting with a friend. Keep it natural and engaging."
            )
            
            summary = await super().process(prompt)
            
            # Combine summary and results in a conversational format
            return (
                f"{summary}\n\n"
                f"Here's what I found in detail:\n{formatted_results}\n\n"
                f"Is there anything specific from these results you'd like me to explain further?"
            )
            
        except Exception as e:
            debug_print(f"Error processing search query: {str(e)}")
            return "Sorry, I ran into a problem while searching. Would you mind trying again? Sometimes rephrasing the question helps!" 