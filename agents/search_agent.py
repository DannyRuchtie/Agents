"""Search agent module for web search functionality."""
import os
from typing import List, Dict, Optional
import aiohttp
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

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
    
    async def _fetch_and_extract_text(self, url: str, session: aiohttp.ClientSession) -> Optional[str]:
        """Fetch HTML content from a URL and extract clean text."""
        try:
            debug_print(f"SearchAgent: Fetching content from URL: {url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    debug_print(f"SearchAgent: Failed to fetch {url}. Status: {response.status}")
                    return None
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, "html.parser")
                
                # Remove script and style elements
                for script_or_style in soup(["script", "style"]):
                    script_or_style.decompose()
                
                # Get text
                text = soup.get_text()
                
                # Break into lines and remove leading/trailing space on each
                lines = (line.strip() for line in text.splitlines())
                # Break multi-headlines into a line each
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                # Drop blank lines
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                if not text:
                    debug_print(f"SearchAgent: No text extracted from {url}")
                    return None
                
                debug_print(f"SearchAgent: Successfully extracted text from {url} (length: {len(text)})")
                # Limit text to avoid overly long prompts (e.g., first 15000 chars)
                # This limit should ideally be based on token count for the LLM
                return text[:15000]
        except aiohttp.ClientError as e:
            debug_print(f"SearchAgent: Network error fetching {url}: {str(e)}")
            return None
        except Exception as e:
            debug_print(f"SearchAgent: Error fetching or parsing {url}: {str(e)}")
            return None

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
        """Process a search query, fetch content from the top result, and provide a summary."""
        debug_print(f"SearchAgent: Processing query: '{query}'")
        try:
            # Perform the initial search
            search_results = await self.search(query)
            
            if not search_results:
                return "I tried searching but couldn't find anything specific online. Maybe try rephrasing?"

            # Format the initial list of results (fallback or for context)
            formatted_initial_results = self.format_results(search_results)

            # Try to fetch and summarize the top result
            top_result = search_results[0]
            debug_print(f"SearchAgent: Attempting to fetch and summarize top result: {top_result.link}")

            async with aiohttp.ClientSession() as session: # Create a session for fetching content
                extracted_text = await self._fetch_and_extract_text(top_result.link, session)

            if extracted_text:
                debug_print(f"SearchAgent: Successfully extracted text from top result. Length: {len(extracted_text)}. Now summarizing.")
                prompt_for_summary = (
                    f"Based on the following text from the webpage titled '{top_result.title}' ({top_result.link}), "
                    f"please answer the user's question: '{query}'.\n\n"
                    f"Extracted Text:\n{extracted_text}\n\n"
                    f"Please provide a concise answer to the question based *only* on this text. "
                    f"If the text doesn't answer the question, say so."
                )
                
                # Use the BaseAgent's LLM to process the summary prompt
                summary_answer = await super().process(prompt_for_summary)
                
                return f"{summary_answer}\n\nSource: {top_result.title} - {top_result.link}"
            else:
                debug_print("SearchAgent: Could not extract text from top result or an error occurred. Falling back to list.")
                return f"I found some search results, but couldn't fully read the top page. Here's a list:\n{formatted_initial_results}"

        except Exception as e:
            debug_print(f"SearchAgent: Error processing search query '{query}': {str(e)}")
            return f"Sorry, I encountered an issue while searching for '{query}'. Details: {str(e)}" 