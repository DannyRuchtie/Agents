"""Writer agent module for composing and summarizing text."""
import os
from pathlib import Path
from datetime import datetime
import re
from typing import Optional

from .base_agent import BaseAgent

WRITER_SYSTEM_PROMPT = """You are a skilled writer. Your role is to:
1. Compose clear, engaging, and well-structured text
2. Adapt your writing style based on the request
3. Create documents in markdown format when asked, always starting with a # Title
4. When asked to write in Dieter Bohn's style (The Verge):
   - Use a conversational yet authoritative tone
   - Include witty observations and clever analogies
   - Focus on the human impact of technology
   - Balance technical details with broader context
   - Add personal touches and relatable experiences
   - Maintain a healthy skepticism while staying optimistic
5. Pay attention to formatting and structure

Focus on quality, clarity, and user requirements."""

class WriterAgent(BaseAgent):
    """Agent responsible for composing and summarizing text."""
    
    def __init__(self):
        super().__init__(
            agent_type="writer",
            system_prompt=WRITER_SYSTEM_PROMPT,
        )
    
    async def expand(self, query: str, context: Optional[str] = None) -> str:
        """Expand on a topic or create a document based on the query.
        
        Args:
            query: The writing request
            context: Optional additional context
            
        Returns:
            Generated text or document
        """
        # Check if this is a document creation request
        should_save = "@Desktop" in query
        
        # Prepare the prompt
        prompt = (
            "Write a response to this request. If '@Desktop' is included, format the response "
            "in clean markdown, starting with a # Title that summarizes the content.\n\n"
        )
        if context:
            prompt += f"Context:\n{context}\n\n"
        prompt += f"Request: {query}"
        
        # Generate the content
        content = await self.process(prompt)
        
        # If requested to save to desktop, write to a markdown file
        if should_save:
            await self._save_to_desktop(content, query)
            return f"I've written your document and saved it to your desktop. Here's what I created:\n\n{content}"
        
        return content
    
    async def _save_to_desktop(self, content: str, query: str) -> None:
        """Save the content to a markdown file on the desktop.
        
        Args:
            content: The content to save
            query: The original query (used for filename)
        """
        # Use exact desktop path
        desktop_path = "/Users/danny/Desktop"
        
        # Try to extract title from the content (looking for # Title format)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            # Use the title as filename
            filename = title_match.group(1).strip()
            # Clean up the filename
            filename = "".join(c if c.isalnum() or c == "_" else "_" for c in filename.lower())
            filename = re.sub(r'_+', '_', filename)  # Replace multiple underscores with single
            filename = filename.strip('_')  # Remove leading/trailing underscores
        else:
            # Fallback to using the query if no title found
            clean_query = query.replace("@Desktop", "").strip()
            words = clean_query.split()[:5]  # Take first 5 words
            filename = "_".join(words).lower()  # Join with underscores
            filename = "".join(c if c.isalnum() or c == "_" else "" for c in filename)
        
        # Add timestamp and extension
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_filename = f"{filename}_{timestamp}.md"
        
        # Create the full path
        file_path = os.path.join(desktop_path, full_filename)
        
        # Write the content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content) 