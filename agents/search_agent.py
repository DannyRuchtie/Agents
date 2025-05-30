"""Search agent module for web search functionality."""
import os
from typing import List, Dict, Optional
import aiohttp
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import asyncio
import ssl

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
        self.last_source_list_str: Optional[str] = None # Added to store last sources
        
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
        """Fetch HTML content from a URL and extract clean text, with retries."""
        max_retries = 3
        retry_delay_seconds = 1

        for attempt in range(max_retries):
            try:
                debug_print(f"SearchAgent: Fetching content from URL: {url} (Attempt {attempt + 1}/{max_retries})")
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        soup = BeautifulSoup(html_content, "html.parser")
                        
                        for script_or_style in soup(["script", "style"]):
                            script_or_style.decompose()
                        
                        text = soup.get_text()
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                        
                        if not text:
                            debug_print(f"SearchAgent: No text extracted from {url} on attempt {attempt + 1}")
                            return None # No point retrying if page is empty
                        
                        debug_print(f"SearchAgent: Successfully extracted text from {url} (length: {len(text)}) on attempt {attempt+1}")
                        return text[:12000]
                    else:
                        # Don't retry on non-200 status if it's a clear client/server error like 404 or 403
                        if 400 <= response.status < 500:
                            debug_print(f"SearchAgent: Failed to fetch {url} with client error status: {response.status} on attempt {attempt+1}. Not retrying.")
                            return None 
                        # For other non-200 errors (e.g. server errors 5xx), let it fall through to retry logic below
                        debug_print(f"SearchAgent: Failed to fetch {url}. Status: {response.status} on attempt {attempt+1}")
                        # Fall through to retry for non-client errors or if all retries exhausted

            except aiohttp.ClientError as e: # Includes ClientConnectionError, TimeoutError, etc.
                debug_print(f"SearchAgent: Network error fetching {url} on attempt {attempt + 1}: {str(e)}")
                if attempt + 1 == max_retries:
                    debug_print(f"SearchAgent: Max retries reached for {url}. Error: {str(e)}")
                    return None # Return None after last retry fails
            except Exception as e:
                debug_print(f"SearchAgent: General error fetching or parsing {url} on attempt {attempt + 1}: {str(e)}")
                # For unexpected errors, probably best not to retry indefinitely
                return None
            
            # If we haven't returned yet (e.g. non-200 server error or ClientError and not last attempt), wait and retry
            if attempt + 1 < max_retries:
                debug_print(f"SearchAgent: Waiting {retry_delay_seconds}s before retrying {url}...")
                await asyncio.sleep(retry_delay_seconds)
        
        debug_print(f"SearchAgent: All {max_retries} attempts to fetch {url} failed.")
        return None # Should be reached if all retries fail due to non-200 and not client error

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
        """Process a search query, fetch content from up to top 5 results, and provide a summary."""
        debug_print(f"SearchAgent: Processing query: '{query}'")
        NUM_RESULTS_TO_PROCESS = 5
        MAX_TOTAL_TEXT_CHARS = 24000 # Max combined chars from all pages for LLM

        try:
            search_results = await self.search(query) # Fetches based on its default (e.g., 5 results)
            
            if not search_results:
                return "I tried searching but couldn't find anything specific online. Maybe try rephrasing?"

            all_extracted_text = ""
            sources_info = []
            text_processed_count = 0

            # Create a more specific SSL context
            ssl_context = ssl.create_default_context()
            # You might need to adjust properties on ssl_context if specific errors arise,
            # e.g., ssl_context.check_hostname = False (less secure, for debugging)
            # or ssl_context.minimum_version / maximum_version
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2 # Explicitly set minimum TLS version

            connector = aiohttp.TCPConnector(ssl=ssl_context, enable_cleanup_closed=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                for i, result in enumerate(search_results):
                    if i >= NUM_RESULTS_TO_PROCESS:
                        break # Stop after processing the desired number of results
                    
                    if len(all_extracted_text) >= MAX_TOTAL_TEXT_CHARS:
                        debug_print(f"SearchAgent: Reached max total text character limit ({MAX_TOTAL_TEXT_CHARS}). Not fetching more pages.")
                        break

                    debug_print(f"SearchAgent: Attempting to fetch and extract text from result {i+1}: {result.link}")
                    extracted_text_from_page = await self._fetch_and_extract_text(result.link, session)

                    if extracted_text_from_page:
                        remaining_char_budget = MAX_TOTAL_TEXT_CHARS - len(all_extracted_text)
                        text_to_add = extracted_text_from_page[:remaining_char_budget]
                        
                        if text_to_add:
                            all_extracted_text += f"\n\n--- Content from {result.title} ({result.link}) ---\n{text_to_add}"
                            sources_info.append(f"{result.title} - {result.link}")
                            text_processed_count += 1
                            debug_print(f"SearchAgent: Added text from {result.link}. Total accumulated text length: {len(all_extracted_text)}")
                        else:
                            debug_print(f"SearchAgent: No character budget left to add text from {result.link}")
            
            if all_extracted_text and sources_info:
                debug_print(f"SearchAgent: Successfully extracted text from {text_processed_count} source(s). Total length: {len(all_extracted_text)}. Now summarizing.")
                
                source_list_str = "\n".join([f"- {s}" for s in sources_info])
                prompt_for_summary = (
                    f"You have been provided with text extracted from multiple web pages (listed under 'Original Sources' below) to answer the user's question: '{query}'.\n\n"
                    f"Combined Extracted Text:\n{all_extracted_text}\n\n"
                    f"User's Question: {query}\n\n"
                    f"Instructions for your answer:\n"
                    f"1. Directly answer the user's question: '{query}'.\n"
                    f"2. Synthesize the information from all provided text into a single, coherent response. Avoid presenting information as if it's from distinct, separate sources in your main answer. Instead, merge the findings and present a unified summary or list of points.\n"
                    f"3. Ensure your answer is concise and directly addresses the question based *only* on the provided text.\n"
                    f"4. Do NOT begin your answer with phrases like 'Based on the provided text...' or 'According to the sources...'. Start directly with the information.\n"
                    f"5. If the text does not contain an answer, clearly state that the information was not found in the provided content.\n\n"
                    f"Answer a concise response to the user's question '{query}' based on the text above. Your response should be a single, synthesized answer, not a list of points from each source. Start your answer directly without any preamble like 'Based on the text...'. If no information is found, state that clearly.:\n"
                )
                
                summary_answer = await super().process(prompt_for_summary)
                
                # Store the sources before conditional return
                self.last_source_list_str = source_list_str

                # Conditionally append sources
                if "source" in query.lower() or \
                   "sources" in query.lower() or \
                   "where did you find" in query.lower() or \
                   "what are your sources" in query.lower():
                    return f"{summary_answer}\n\nSources:\n{source_list_str}"
                else:
                    return summary_answer
            else:
                # Fallback if no text could be extracted from any of the top N pages
                formatted_initial_results = self.format_results(search_results)
                debug_print("SearchAgent: Could not extract text from top results or an error occurred. Falling back to list.")
                return f"I found some search results, but couldn't fully read the content from the top pages. Here's a list of links I found:\n{formatted_initial_results}"

        except Exception as e:
            debug_print(f"SearchAgent: Error processing search query '{query}': {str(e)}")
            return f"Sorry, I encountered an issue while searching for '{query}'. Details: {str(e)}"

    def get_last_retrieved_sources(self) -> Optional[str]:
        """Returns the string list of sources from the most recent 'process' call."""
        if self.last_source_list_str:
            return f"Sources from the last search:\n{self.last_source_list_str}"
        return "I don't have any specific sources from my last search to share, or I haven't performed a search recently." 