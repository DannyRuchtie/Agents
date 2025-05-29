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
        self.search_engine_id = os.getenv("GOOGLE_CSE_ID") # Corrected to GOOGLE_CSE_ID

        # ---- TEMPORARY HARDCODED DEBUG ----
        # self.google_api_key = "AIzaSyCSxVQZ1Tz0H_f3ufP34__8cimx-sYncik" 
        # self.search_engine_id = "707592731416c4d01"
        # print(f"[SEARCH_AGENT_DEBUG] Using HARDCODED GOOGLE_API_KEY: {self.google_api_key}")
        # print(f"[SEARCH_AGENT_DEBUG] Using HARDCODED GOOGLE_CSE_ID: {self.search_engine_id}")
        # ---- END TEMPORARY HARDCODED DEBUG ----
        
        if not self.google_api_key or not self.search_engine_id:
            # This warning will now trigger if .env isn't loaded properly
            debug_print("SearchAgent: WARNING - Google API key or Search Engine ID not found via os.getenv. Search functionality will be limited or fail.")
    
    async def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Perform a web search using Google Custom Search API.
        
        Args:
            query: The search query
            num_results: Number of results to return (max 10)
            
        Returns:
            List of SearchResult objects
            
        Raises:
            Exception: If the API request fails or returns an error.
        """
        if not self.google_api_key or not self.search_engine_id:
            debug_print("SearchAgent: GOOGLE_API_KEY or GOOGLE_SEARCH_ENGINE_ID is not set.")
            raise Exception("Search agent is not configured. Missing Google API key or Search Engine ID.")

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
            debug_print(f"SearchAgent: Requesting URL: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    debug_print(f"SearchAgent: Response status: {response.status}")
                    if response.status != 200:
                        error_text = await response.text()
                        debug_print(f"SearchAgent: Error response text: {error_text}")
                        try:
                            error_data = await response.json()
                            error_message = error_data.get('error', {}).get('message', f'Unknown API error. Status: {response.status}, Body: {error_text}')
                        except aiohttp.ContentTypeError: # Not JSON
                            error_message = f'API error. Status: {response.status}, Body: {error_text}'
                        raise Exception(f"Search API request failed: {error_message}")
                    
                    data = await response.json()
                    debug_print(f"SearchAgent: Response data: {data}")
                    
                    if "items" not in data or not data["items"]:
                        debug_print("SearchAgent: No 'items' in response or 'items' is empty.")
                        # Check for potential API errors even with 200 OK if items are missing
                        if "error" in data:
                             error_message = data.get('error', {}).get('message', 'Unknown error from API response structure.')
                             raise Exception(f"Search API returned an error: {error_message}")
                        raise Exception("No search results found by Google API for the query.")
                    
                    results = []
                    for item in data["items"]:
                        result = SearchResult(
                            title=item.get("title", ""),
                            link=item.get("link", ""),
                            snippet=item.get("snippet", "")
                        )
                        results.append(result)
                    
                    return results
                    
        except aiohttp.ClientError as e:
            debug_print(f"SearchAgent: Network or HTTP error during search: {str(e)}")
            raise Exception(f"Network error during search: {str(e)}")
        except Exception as e:
            debug_print(f"SearchAgent: General error during search: {str(e)}")
            # Re-raise the exception if it's one of our specific ones, or wrap it
            if isinstance(e, Exception) and e.args and "Search API request failed" in e.args[0]:
                raise
            if isinstance(e, Exception) and e.args and "No search results found" in e.args[0]:
                raise
            if isinstance(e, Exception) and e.args and "Search agent is not configured" in e.args[0]:
                raise
            raise Exception(f"An unexpected error occurred in search: {str(e)}")
    
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
        debug_print(f"SearchAgent: Processing query: '{query}'")
        try:
            # Perform the search
            results = await self.search(query)
            
            # This part is effectively handled by exceptions from self.search now,
            # but keeping it as a fallback or for clarity.
            if not results: 
                return "I tried searching but couldn't find anything specific. Maybe we could try a different search term?"
            
            # Format the results in a friendly way
            formatted_results = self.format_results(results)
            
            # Generate a conversational summary using the language model
            # If we want the summary to be streamed, super().process needs to handle streaming
            # and this method should yield from it or handle chunks.
            # For now, assuming super().process returns a complete string.
            
            # Constructing the prompt for the LLM to summarize the search results
            # This part is where the BaseAgent's LLM is used.
            # The SearchAgent's role is to fetch, format, and then pass to BaseAgent for summarization.
            # The BaseAgent's process method should handle the streaming if stream=True was passed to its client.
            
            # We want to show the raw results first, then the summary.
            # So, we'll return the formatted_results, and let the MasterAgent (or user) decide if a summary is needed.
            # For now, SearchAgent will just return the formatted list.
            # The "summary" part by calling super().process here would make SearchAgent call an LLM,
            # which might be redundant if MasterAgent is already an LLM.

            # Let's simplify: SearchAgent's job is to get and format search results.
            # The summarization can be a higher-level task.
            # So, we'll return formatted_results directly.

            # The prompt and summary generation using super().process can be removed from SearchAgent
            # if the intention is for SearchAgent to *only* fetch and format, not summarize using its own LLM.
            # This simplifies SearchAgent and avoids nested LLM calls if MasterAgent is already summarizing.

            # Based on previous discussions, MasterAgent calls the specialist agent, and the specialist
            # agent (like SearchAgent) processes and returns its findings. MasterAgent then formulates the final response.
            # So, SearchAgent should just return its direct findings.
            
            debug_print(f"SearchAgent: Successfully found and formatted {len(results)} results.")
            return formatted_results # Return directly formatted results

        except Exception as e:
            debug_print(f"SearchAgent: Error processing search query '{query}': {str(e)}")
            # Return a user-friendly message including the specific error
            return f"Sorry, I encountered an issue while searching for '{query}'. Details: {str(e)}" 