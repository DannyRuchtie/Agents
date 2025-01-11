"""Writer agent module for text generation and editing."""
from typing import List

from .base_agent import BaseAgent

WRITER_SYSTEM_PROMPT = """You are an expert writer and editor. Your role is to take 
input content and create well-written, concise summaries or detailed 
explanations as needed. Focus on clarity, coherence, and factual accuracy. 
Always maintain a professional tone."""

class WriterAgent(BaseAgent):
    """Agent responsible for writing and editing text."""
    
    def __init__(self):
        super().__init__(
            agent_type="writer",
            system_prompt=WRITER_SYSTEM_PROMPT,
        )
    
    async def summarize(self, texts: List[str]) -> str:
        """Summarize a list of texts into a coherent paragraph.
        
        Args:
            texts: List of text snippets to summarize
            
        Returns:
            A coherent summary
        """
        combined_text = "\n".join(texts)
        response = await self.process(
            f"Please summarize the following information into a coherent, "
            f"well-written paragraph:\n\n{combined_text}"
        )
        return response
    
    async def expand(self, topic: str, context: str = "") -> str:
        """Expand on a topic with optional context.
        
        Args:
            topic: The main topic to write about
            context: Optional additional context
            
        Returns:
            Detailed explanation of the topic
        """
        prompt = f"Please write a detailed explanation about: {topic}"
        if context:
            prompt += f"\nConsider this context: {context}"
            
        response = await self.process(prompt)
        return response 