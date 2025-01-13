"""Search agent module for web information retrieval."""
from typing import List
import asyncio
import time
from duckduckgo_search import DDGS

from .base_agent import BaseAgent

SEARCH_SYSTEM_PROMPT = """You are a search expert. Your role is to analyze queries 
and extract key search terms to find the most relevant information from 
the web. Focus on extracting precise, factual search terms."""

class SearchAgent(BaseAgent):
    """Agent responsible for searching and retrieving information from the web."""
    
    def __init__(self):
        super().__init__(
            agent_type="search",
            system_prompt=SEARCH_SYSTEM_PROMPT,
        )
        self.search_client = DDGS()
        self.last_search_time = 0
        self.min_delay = 2  # Minimum delay between searches in seconds
    
    async def search(self, query: str) -> List[str]:
        """Perform a web search for the given query.
        
        Args:
            query: The search query
            
        Returns:
            A list of relevant search results
        """
        # Add delay between searches to avoid rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_search_time
        if time_since_last < self.min_delay:
            await asyncio.sleep(self.min_delay - time_since_last)
        
        # For non-personal searches, optimize the query
        response = await self.process(
            f"Optimize this search query for web search by extracting and reformulating "
            f"the key concepts. Make it concise and focused:\n{query}"
        )
        search_query = response
        
        try:
            # Perform the web search
            results = []
            for r in self.search_client.text(
                search_query,
                max_results=3  # Reduced to 3 results to help with rate limiting
            ):
                if r.get('body'):
                    results.append(r['body'])
            
            # Update last search time
            self.last_search_time = time.time()
            
            if not results:
                # Fallback message if no results found
                return ["No relevant search results found. Please try rephrasing your query."]
            
            return results
            
        except Exception as e:
            # Handle rate limiting errors more gracefully
            error_str = str(e)
            if "202" in error_str or "429" in error_str or "rate" in error_str.lower():
                await asyncio.sleep(self.min_delay * 2)  # Wait longer on rate limit
                return [
                    "I'm currently being rate limited by the search service. "
                    "Please wait a moment and try your search again."
                ]
            
            print(f"Search error: {error_str}")
            return [
                "I encountered an error while searching. "
                "Please try again or rephrase your query."
            ] 