"""Code agent module for programming assistance."""
from typing import Optional
import json # Added for parsing LLM response in process method

from .base_agent import BaseAgent
from config.settings import debug_print # Added for debug_print

CODE_SYSTEM_PROMPT = """You are an expert programmer. Your primary role is to assist with programming tasks by generating code or explaining existing code.
When generating code:
- Produce clean, efficient, and well-documented code snippets.
- Adhere to best practices for the specified language, focusing on security and maintainability.
- Ensure generated code is production-ready and follows modern development standards.
- Clearly indicate the language of the generated code if not Python (e.g., using markdown ```language ... ```).
When explaining code:
- Provide a clear, detailed, and easy-to-understand explanation of the code's functionality, logic, and purpose.
- Break down complex parts into simpler concepts.
When asked to perform a task, first determine if the user is asking you to GENERATE new code based on a description, or to EXPLAIN an existing piece of code.
"""

class CodeAgent(BaseAgent):
    """
    Agent responsible for code generation and explanation.

    Core Functionality:
    This agent assists with programming-related queries. It can generate new code
    based on a task description and specified language, or it can explain
    an existing piece of code.

    Tools (exposed via the process method):
        - generate_code(task: str, language: str, context: Optional[str]) -> str:
            Generates a code snippet.
        - explain_code(code: str) -> str:
            Explains an existing code snippet.

    Interaction via MasterAgent:
    MasterAgent will call this agent's `process(query: str)` method.
    This `process` method should:
    1. Use an LLM to determine if the query is a request for code GENERATION
       (e.g., "write a python function to...", "how do I do X in javascript?")
       or code EXPLANATION (e.g., "what does this code do?", "explain this function...").
    2. Extract necessary parameters (e.g., task description, language for generation; code snippet for explanation).
    3. Call the internal `generate_code` or `explain_code` method.
    """
    
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
            "The code should be production-ready and well-documented. "
            f"Ensure the response contains ONLY the {language} code, appropriately formatted (e.g., in a markdown block like ```{language}\n# code here\n```), and its explanation if necessary for clarity."
        )
        
        if context:
            prompt += f"\nAdditional context: {context}"
            
        return await super().process(prompt)
    
    async def explain_code(self, code: str, language: Optional[str] = None) -> str:
        """Explain a code snippet in plain English.
        
        Args:
            code: The code snippet to explain
            language: Optional language hint for the code.
            
        Returns:
            Detailed explanation of the code
        """
        lang_hint = f" (likely {language})" if language else ""
        prompt = (
            f"Please explain the following code snippet{lang_hint} in detail, "
            "breaking down its functionality and purpose:\n\n"
            f"```\n{code}\n```"
        )
        
        return await super().process(prompt)

    async def process(self, query: str) -> str:
        """
        Processes a query to determine if it's for code generation or explanation,
        then calls the appropriate internal method.
        """
        debug_print(f"CodeAgent received query: {query}")

        # Prepare the user's query for safe embedding in the prompt & as a JSON string value
        # For displaying in the prompt directly (less aggressive escaping)
        query_display_in_prompt = query.replace("`", "\\`") # Escape backticks for markdown/f-string safety
        # For embedding as a value within a JSON string (robust escaping)
        query_as_json_string_value = json.dumps(query)

        # Define the JSON example strings
        # The clarify_response_example needs to embed the user's query (as a JSON string)
        clarify_response_example_str = f'''{{"action": "clarify", "parameters": {{"original_query": {query_as_json_string_value}}}}}'''
        generate_response_example_str = '''{{"action": "generate_code", "parameters": {{"task": "list files in a directory", "language": "python"}}}}'''
        explain_response_example_str = '''{{"action": "explain_code", "parameters": {{"code_to_explain": "def hello(): print(\'world\')", "language": "python"}}}}'''

        classifier_prompt = f'''You are an internal request classifier for a CodeAgent.
User query: {query_display_in_prompt}

Determine if the user wants to \'generate_code\' or \'explain_code\'.
- \'generate_code\' is for requests like "write a function to...", "how do I...", "create a script for...".
  If \'generate_code\', extract:
    - \'task\': The description of what the code should do.
    - \'language\' (optional, default \'python\'): The programming language.
    - \'context\' (optional): Any additional details or existing code.
- \'explain_code\' is for requests like "what does this code do?", "explain this function...", often followed by a code block.
  If \'explain_code\', extract:
    - \'code_to_explain\': The code snippet to be explained.
    - \'language\' (optional): The language of the code being explained, if discernible.

Respond with a JSON object with \'action\' (\'generate_code\' or \'explain_code\') and \'parameters\' (an object with extracted fields).
If the query is too vague or not clearly a code generation or explanation task, respond with {clarify_response_example_str}

Example for generation:
Query: "write a python script to list files in a directory"
Response: {generate_response_example_str}

Example for explanation:
Query: "explain this: def hello(): print(\'world\')"
Response: {explain_response_example_str}
'''
        
        raw_classification = await super().process(classifier_prompt)
        debug_print(f"CodeAgent classification response: {raw_classification}")

        try:
            classification = json.loads(raw_classification)
            action = classification.get("action")
            params = classification.get("parameters", {})

            if action == "generate_code":
                task = params.get("task")
                if not task:
                    return "I can try to generate some code for you, but I need a bit more information. What exactly should the code do?"
                language = params.get("language", "python")
                context = params.get("context")
                return await self.generate_code(task=task, language=language, context=context)
            elif action == "explain_code":
                code_to_explain = params.get("code_to_explain")
                if not code_to_explain:
                    return "I'd be happy to explain some code! Could you please provide the code snippet you're curious about?"
                language = params.get("language")
                return await self.explain_code(code=code_to_explain, language=language)
            elif action == "clarify":
                # When LLM returns the original_query, it should be the raw user query string.
                original_query_from_llm = params.get('original_query', query)
                return f"Hmm, I'm not quite sure if you want me to write some new code or explain some existing code regarding: '{original_query_from_llm.replace("'", "\\'")}'. Could you clarify a bit?"
            else:
                debug_print(f"CodeAgent: Unknown action from classification: {action}. Falling back to general processing of query.")
                return f"I wasn't sure how to handle your request about '{query}'. If it's code-related, you can ask me to write code or explain it!"

        except json.JSONDecodeError:
            debug_print(f"CodeAgent: Failed to parse JSON from classification: {raw_classification}. Falling back.")
            return f"I had a little trouble understanding the specifics of your code request. Could you try phrasing it differently?"
        except Exception as e:
            debug_print(f"CodeAgent: Error in process method: {e}. Query: {query}")
            return f"I ran into an unexpected issue while trying to process your code request about '{query}'. Details: {str(e)}" 