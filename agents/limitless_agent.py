import requests
import os
import json
from typing import Optional, List, Dict
from agents.base_agent import BaseAgent
from config.settings import is_debug_mode, debug_print

class LimitlessAgent(BaseAgent):
    BASE_URL = "https://api.limitless.ai/v1/lifelogs"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(agent_type="limitless")
        self.api_key = api_key or os.getenv("LIMITLESS_API_KEY")
        if not self.api_key:
            debug_print("Limitless API key not found. Please set LIMITLESS_API_KEY.")

    def get_lifelogs(self, date=None, start=None, end=None, timezone=None, limit=3) -> List[Dict]:
        if not self.api_key:
            debug_print("LimitlessAgent: Cannot fetch lifelogs, API key missing.")
            return []
        
        headers = {"X-API-Key": self.api_key}
        params = {
            "limit": limit,
            "includeMarkdown": "true",
            "includeHeadings": "true"
        }
        if date:
            params["date"] = date
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if timezone:
            params["timezone"] = timezone

        try:
            response = requests.get(self.BASE_URL, headers=headers, params=params)
            response.raise_for_status()
            return response.json().get("data", {}).get("lifelogs", [])
        except requests.exceptions.RequestException as e:
            debug_print(f"LimitlessAgent: Error during API request: {e}")
            return []
        except json.JSONDecodeError as e:
            debug_print(f"LimitlessAgent: Error decoding JSON from API response: {e}")
            return []

    async def process(self, query: str) -> str:
        if not self.api_key:
            return "I can't access Limitless lifelogs because the API key is not configured."

        if is_debug_mode():
            debug_print(f"LimitlessAgent received query: {query}")

        lifelogs_data = self.get_lifelogs(limit=3)

        if not lifelogs_data:
            return "I couldn't find any recent lifelogs for you from Limitless."

        summary_content = "Here are the titles and key points from your recent lifelogs:\n\n"
        for i, log in enumerate(lifelogs_data):
            title = log.get("title", "Untitled Log")
            markdown_content = log.get("markdown", "No detailed content.")
            snippet = "\n".join(markdown_content.split('\n')[:5])
            if len(snippet) > 250:
                snippet = snippet[:250] + "..."
            summary_content += f"{i+1}. {title}\n   - Snippet: {snippet}\n\n"
        
        summarization_prompt = (
            "You are an AI assistant who was present with the user throughout their day, listening to their conversations, meetings, and personal reflections. "
            "When the user asks about their lifelogs, ONLY summarize and reference information that is actually present in the lifelog data below. "
            "Do NOT invent, embellish, or hallucinate any details or events. If something is not in the lifelog, do not mention it. "
            "Make your answer personal and natural, but strictly based on the provided lifelog content. "
            "If the user asks about a specific event, meeting, or moment, only share what is in the lifelog about that. "
            "If the user wants a summary, give a warm, friendly recap of the main moments and feelings you noticed, but only from the lifelog data. "
            "Start your answer directly with the summary or relevant content, without any formal announcement or boilerplate. "
            "Here are the lifelogs:\n\n"
            f"{summary_content}\n\nUser's question: {query}"
        )
        
        if is_debug_mode():
            debug_print(f"LimitlessAgent: Sending to LLM for summarization: {summarization_prompt[:200]}...")

        try:
            final_summary = await super().process(input_text=summarization_prompt)
            return final_summary
        except Exception as e:
            if is_debug_mode():
                debug_print(f"LimitlessAgent: Error during LLM summarization: {e}")
            return "I found your recent lifelogs, but I had trouble summarizing them. Here are the titles: " + ", ".join([log.get("title", "Untitled") for log in lifelogs_data]) 