"""Search agent module for web information retrieval."""
from typing import List
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
    
    async def search(self, query: str) -> List[str]:
        """Perform a web search for the given query.
        
        Args:
            query: The search query
            
        Returns:
            A list of relevant search results
        """
        # Add specific search modifiers for personal searches
        if any(name in query.lower() for name in ["danny ruchtie", "danny", "ruchtie"]):
            # Add specific terms to find personal/professional info
            search_query = f"{query} (linkedin OR github OR profile OR about OR professional OR developer)"
        else:
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
                max_results=5  # Limit to top 5 results
            ):
                if r.get('body'):
                    results.append(r['body'])
            
            if not results:
                # Fallback message if no results found
                return ["No relevant search results found. Please try rephrasing your query."]
            
            return results
            
        except Exception as e:
            # Handle any search errors gracefully
            print(f"Search error: {str(e)}")
            return [
                "I encountered an error while searching. "
                "Please try again or rephrase your query."
            ] 