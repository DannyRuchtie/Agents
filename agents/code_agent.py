"""Code agent module for programming assistance."""
from typing import Optional

from .base_agent import BaseAgent

CODE_SYSTEM_PROMPT = """You are an expert programmer. Your role is to generate 
clean, well-documented code snippets and explain programming concepts. 
Focus on best practices, security, and maintainability. Ensure all code
is production-ready and follows modern development standards."""

class CodeAgent(BaseAgent):
    """Agent responsible for code generation and explanation."""
    
    def __init__(self):
        super().__init__(
            agent_type="code",
            system_prompt=CODE_SYSTEM_PROMPT,
        )
    
    async def generate_code(
        self,
        task: str,
        language: str = "python",
        context: Optional[str] = None
    ) -> str:
        """Generate code for a given task.
        
        Args:
            task: Description of what the code should do
            language: Programming language to use
            context: Optional additional context or requirements
            
        Returns:
            Generated code snippet with explanatory comments
        """
        prompt = (
            f"Generate {language} code for the following task:\n{task}\n\n"
            "Include clear comments and follow best practices. "
            "The code should be production-ready and well-documented."
        )
        
        if context:
            prompt += f"\nAdditional context: {context}"
            
        response = await self.process(prompt)
        return response
    
    async def explain_code(self, code: str) -> str:
        """Explain a code snippet in plain English.
        
        Args:
            code: The code snippet to explain
            
        Returns:
            Detailed explanation of the code
        """
        prompt = (
            "Please explain the following code in detail, "
            "breaking down its functionality and purpose:\n\n"
            f"```\n{code}\n```"
        )
        
        response = await self.process(prompt)
        return response 