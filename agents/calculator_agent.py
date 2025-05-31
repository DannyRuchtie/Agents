"""Calculator agent for handling mathematical computations."""
import ast
import operator
import math

from .base_agent import BaseAgent
from config.settings import debug_print

CALCULATOR_SYSTEM_PROMPT = """You are an AI assistant specialized in mathematics. Your primary role is to assist with calculations by first translating natural language queries into evaluable mathematical expressions.

When given a user\'s query:
1.  Analyze the query to identify a mathematical calculation. Handle common operator words (e.g., \'plus\', \'minus\', \'times\', \'divided by\', \'power\').
2.  If the query is a straightforward mathematical expression or can be easily converted into one (e.g., word problems like \'what is two plus three times four\'), your goal is to formulate a standard Python-evaluable mathematical expression string.
    *   Example query: \'what is two plus 2 times five?\' -> Your response: \'2 + 2 * 5\'
    *   Example query: \'10 apples minus 3 apples\' -> Your response: \'10 - 3\'
    *   Example query: \'calculate 5 to the power of 3\' -> Your response: \'5 ** 3\'
3.  If the query involves concepts you cannot reliably turn into a simple arithmetic expression (e.g., \'what is the current US debt divided by the population?\', \'solve for x in x^2 - 4 = 0\', or highly complex word problems requiring multi-step reasoning beyond direct expression formulation), clearly state that you can only handle arithmetic expressions that can be directly evaluated, or ask for the problem to be simplified into an arithmetic expression.
4.  Ensure the generated expression uses standard Python mathematical operators (+, -, *, /, **).
5.  Your response for this step MUST BE ONLY the Python-evaluable mathematical expression string itself, or a concise statement of refusal/clarification if you cannot formulate one. Do not add any conversational fluff, explanations, or solve the expression yourself in this initial response.
"""

# A very restricted set of names/operators for a safer eval context
SAFE_EVAL_GLOBALS = {
    "__builtins__": {}, # Disallow all built-ins
    # Allow specific math functions if needed, e.g.:
    # "abs": abs, "round": round,
    # From math module:
    # "sqrt": math.sqrt, "pow": math.pow, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    # "log": math.log, "log10": math.log10, "exp": math.exp, "pi": math.pi, "e": math.e
}
# For now, let\'s stick to basic arithmetic which doesn\'t need much in globals if using ast.literal_eval
# or a custom parser. If using plain eval with LLM-generated strings, this becomes more important.

# Using a node visitor for safer evaluation of AST
# Supported operations
ALLOWED_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
    ast.UAdd: operator.pos
}
ALLOWED_NODE_TYPES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, # ast.Num is deprecated in 3.8, use ast.Constant
    ast.Constant, # For numbers and potentially True/False/None if allowed
    ast.Call, ast.Name, # If we want to allow functions like sqrt()
    ast.Load # For variable/function name loading
)

class SafeExpressionEvaluator(ast.NodeVisitor):
    def visit_Constant(self, node): # Replaces visit_Num for Python 3.8+
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise TypeError(f"Unsupported constant type: {type(node.value)}")

    def visit_Num(self, node): # For compatibility with Python < 3.8
        if isinstance(node.n, (int, float, complex)):
            return node.n
        raise TypeError(f"Unsupported number type: {type(node.n)}")

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        if op_type in ALLOWED_OPERATORS:
            return ALLOWED_OPERATORS[op_type](left, right)
        raise TypeError(f"Unsupported binary operator: {op_type.__name__}")

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        op_type = type(node.op)
        if op_type in ALLOWED_OPERATORS:
            return ALLOWED_OPERATORS[op_type](operand)
        raise TypeError(f"Unsupported unary operator: {op_type.__name__}")

    def visit_Expression(self, node):
        return self.visit(node.body)

    def generic_visit(self, node):
        # Disallow any node types not explicitly handled
        if not isinstance(node, ALLOWED_NODE_TYPES):
            raise TypeError(f"Unsupported AST node type: {type(node).__name__}")
        super().generic_visit(node) # Should not be reached if all allowed types are handled


def safe_eval_expression(expression_str: str):
    debug_print(f"CalculatorAgent: Attempting to safely evaluate: {expression_str}")
    if not expression_str.strip():
        raise ValueError("Expression is empty")
    try:
        parsed_ast = ast.parse(expression_str, mode='eval')
        evaluator = SafeExpressionEvaluator()
        result = evaluator.visit(parsed_ast)
        debug_print(f"CalculatorAgent: Safe eval result: {result}")
        return result
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError) as e:
        debug_print(f"CalculatorAgent: Error during safe_eval_expression '{expression_str}': {type(e).__name__} - {e}")
        raise # Re-raise the caught specific errors
    except Exception as e: # Catch any other unexpected errors during AST parsing/visiting
        debug_print(f"CalculatorAgent: Unexpected error during safe_eval_expression '{expression_str}': {type(e).__name__} - {e}")
        raise ValueError(f"Invalid or unsupported mathematical expression: {str(e)}")


class CalculatorAgent(BaseAgent):
    """
    Agent for handling mathematical computations.

    Core Functionality:
    The agent takes a natural language query that expresses a mathematical problem.
    It uses an LLM to attempt to convert this query into a Python-evaluable
    mathematical expression. If successful, it then safely evaluates this
    expression and returns the numerical result. If the query is too complex
    or cannot be converted into a direct expression, it may use the LLM
    to attempt a direct solution or indicate its inability to solve.

    Tools:
        - process(query: str) -> str:
            Takes a natural language mathematical query.
            Returns a string representing the numerical answer or an error/clarification message.
            Internally uses:
                - LLM call to translate query to a mathematical expression string.
                - safe_eval_expression: Securely evaluates the formulated expression string.
                - LLM call (fallback) to directly solve the query if expression formulation/evaluation fails.
    """
    def __init__(self):
        super().__init__(
            agent_type="calculator",
            system_prompt=CALCULATOR_SYSTEM_PROMPT
        )

    async def process(self, query: str) -> str:
        debug_print(f"CalculatorAgent received query: {query}")

        expression_from_llm = await super().process(query)
        debug_print(f"CalculatorAgent: LLM formulated expression: '{expression_from_llm}'")

        refusal_phrases = [
            "i cannot formulate", "i can only handle", "cannot turn into a simple",
            "i am unable to", "this query involves concepts"
        ]
        if any(phrase in expression_from_llm.lower() for phrase in refusal_phrases) or len(expression_from_llm) > 100:
            debug_print(f"CalculatorAgent: LLM indicated it cannot formulate an expression, or expression too long. Query: '{query}'. LLM response: '{expression_from_llm}'")
            direct_solve_prompt = f"Solve the following math problem: {query}. Provide only the numerical answer or state if it's unsolvable."
            debug_print(f"CalculatorAgent: Falling back to direct LLM solve for query: {query}")
            try:
                direct_answer = await super().process(direct_solve_prompt)
                debug_print(f"CalculatorAgent: LLM direct solve answer: {direct_answer}")
                return f"I've worked that out for you: {direct_answer}"
            except Exception as e_solve:
                debug_print(f"CalculatorAgent: Error during LLM direct solve: {str(e_solve)}")
                return f"I tried to solve '{query}' directly, but I ran into a little snag: {str(e_solve)}"

        try:
            result = safe_eval_expression(expression_from_llm)
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            final_answer = f"Alright, the answer is {result}."
            debug_print(f"CalculatorAgent: Successfully evaluated. Result: {final_answer}")
            return final_answer
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError) as e:
            error_message = str(e)
            debug_print(f"CalculatorAgent: Error evaluating expression '{expression_from_llm}': {error_message}. Original query: '{query}'")
            if isinstance(e, ZeroDivisionError):
                return "Oops! It looks like that involves dividing by zero, which we can't do."
            
            debug_print(f"CalculatorAgent: Eval failed. Falling back to LLM for direct solution for query: {query}")
            fallback_prompt = f"Please solve the following mathematical problem directly: '{query}'. Provide only the numerical answer or state if it's unsolvable."
            try:
                direct_answer = await super().process(fallback_prompt)
                debug_print(f"CalculatorAgent: LLM fallback direct answer: {direct_answer}")
                return f"I double-checked that for you, and the answer is: {direct_answer}"
            except Exception as e_fallback:
                debug_print(f"CalculatorAgent: Error during LLM fallback solve: {str(e_fallback)}")
                return f"I tried to calculate '{query}', but it seems a bit tricky. Error: {str(e_fallback)}"
        except Exception as e_general:
            debug_print(f"CalculatorAgent: General error processing query '{query}': {str(e_general)}")
            return f"An unexpected hiccup occurred while I was trying to calculate that: {query}. Details: {str(e_general)}"

"""
# Example Usage (for testing locally, not part of the agent file)
# async def main():
#     agent = CalculatorAgent()
#     print(await agent.process("what is 2 plus 3"))
#     print(await agent.process("5 times 10 minus 2"))
#     print(await agent.process("10 divided by 0"))
#     print(await agent.process("what is the square root of 16 plus three")) # Needs more advanced parsing or LLM math
#     print(await agent.process("current US debt divided by population")) # LLM should state cannot formulate

# if __name__ == "__main__":
#    import asyncio # Added import for example usage
#    asyncio.run(main())
""" 