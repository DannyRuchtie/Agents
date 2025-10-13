"""Reflection agent that reviews conversations and suggests improvements."""

from __future__ import annotations

from typing import List, Dict

from agents.base_agent import BaseAgent
from config.settings import MODEL_SELECTOR_SETTINGS, LLM_PROVIDER_SETTINGS


REFLECTION_SYSTEM_PROMPT = """You are a self-improvement analyst for a personal AI assistant.
Your job is to read recent conversation turns and provide:
1. Strengths: what the assistant did well.
2. Issues: mistakes, missed opportunities, or weak answers.
3. Suggestions: concrete, actionable steps to improve future interactions.

Keep the tone constructive and friendly. Focus on helping the assistant
deliver more useful, personal, and proactive support next time."""


class ReflectionAgent(BaseAgent):
    """Analyzes conversation history and produces improvement suggestions."""

    def __init__(self) -> None:
        super().__init__(agent_type="reflection", system_prompt=REFLECTION_SYSTEM_PROMPT, max_history=0)

    @staticmethod
    def _format_conversation(transcript: List[Dict[str, str]]) -> str:
        formatted_lines = []
        for turn in transcript:
            role = turn.get("role", "user").capitalize()
            content = turn.get("content", "").strip()
            if not content:
                continue
            formatted_lines.append(f"{role}: {content}")
        return "\n".join(formatted_lines)

    async def analyze(self, transcript: List[Dict[str, str]]) -> str:
        """Produce a reflection report for the provided transcript."""
        if not transcript:
            return "I need at least one exchange to reflect on. Try again after a short conversation."

        conversation_text = self._format_conversation(transcript)
        prompt = (
            "Review the conversation below and provide a short self-improvement report. "
            "Format the response using headings (Strengths, Issues, Suggestions) and bullets.\n\n"
            f"Conversation:\n{conversation_text}"
        )
        preferred_model = MODEL_SELECTOR_SETTINGS.get("moderate_model") or LLM_PROVIDER_SETTINGS.get("openai_default_model")
        return await super().process(prompt, model=preferred_model, temperature=0.7)
